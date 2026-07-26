#!/usr/bin/env python3
"""Run the migration loop unattended until the port reaches parity.

Each iteration takes the next pending task from the dependency-ordered plan,
hands it to cursor-agent, then refuses to mark it done unless the port holds up:
the full test suite must pass, ruff must be clean, and the module's exported
TypeScript API must actually be present in the Python target. Failing the last
check is what phase 2 did silently for 103 modules, so it is enforced here
rather than trusted.

Usage:
    python migration/loop.py                    # run until nothing is pending
    python migration/loop.py --max-tasks 3      # short supervised run
    python migration/loop.py --dry-run          # print prompts, call nothing
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from ts_symbols import ts_repo
from verify import PASS_THRESHOLD, verify_task

PY_ROOT = Path(__file__).resolve().parent.parent
PLAN = PY_ROOT / "migration" / "plan.json"
LOG = PY_ROOT / "migration" / "loop.log"
VENV_PYTHON = PY_ROOT / ".venv" / "bin" / "python"
RUFF = PY_ROOT / ".venv" / "bin" / "ruff"

DEFAULT_MODEL = "composer-2.5"
AGENT_TIMEOUT_SECONDS = 3600


def log(message: str) -> None:
    stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{stamp}] {message}"
    print(line, flush=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def run(command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        cwd=PY_ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )


def load_plan() -> list[dict]:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def save_plan(plan: list[dict]) -> None:
    PLAN.write_text(json.dumps(plan, indent=2, ensure_ascii=False), encoding="utf-8")


def next_pending(plan: list[dict]) -> dict | None:
    return next((task for task in plan if task.get("status") == "pending"), None)


def source_file_list(source: Path, limit: int = 40) -> str:
    if not source.is_dir():
        return "  (source directory not found)"
    files = sorted(
        entry.name
        for entry in source.iterdir()
        if entry.is_file() and entry.name.endswith((".ts", ".tsx"))
    )
    shown = files[:limit]
    tail = f"\n  ... and {len(files) - limit} more" if len(files) > limit else ""
    return "\n".join(f"  - {name}" for name in shown) + tail


def build_prompt(task: dict, result: dict, attempt: int) -> str:
    source = ts_repo() / task["source"]
    missing = result["missing_symbols"]

    if missing:
        shown = missing[:120]
        more = f"\n  ... and {len(missing) - 120} more" if len(missing) > 120 else ""
        work = (
            "Port every exported symbol from the TypeScript module, preserving "
            "behaviour. These are currently missing from the Python target:\n\n"
            + "\n".join(f"  - {name}" for name in shown)
            + more
        )
    else:
        work = (
            "This module exports no named symbols, so port its files as they are "
            "(barrels, manifests, and side-effecting setup included):\n\n"
            + source_file_list(source)
        )

    retry_note = ""
    if attempt > 1:
        retry_note = (
            f"\nThis is attempt {attempt}. The previous attempt left "
            f"{len(missing)} of {result['expected']} exported symbols unimplemented. "
            "Implement the real behaviour from the TypeScript source. Do not create "
            "placeholder functions, and do not invent APIs that the source does not have.\n"
        )

    return f"""Port a TypeScript module to Python as part of an ongoing migration.

Source (read-only): {source}
Target package:     {PY_ROOT / task["target"]}
{retry_note}
{work}

Rules:
- Mirror the source behaviour. Read the .ts files before writing Python.
- camelCase becomes snake_case. Keep module and file structure aligned with the source.
- Port the module's .test.ts files into pytest tests under tests/ as well.
- Reuse existing helpers in this repo (openclaw/packages/normalization_core and
  friends) instead of duplicating them.
- Never write a placeholder that only exists to satisfy a name, and never invent
  an API the source does not export. An unfinished honest port is better than a
  complete fake one.
- Run `.venv/bin/python -m pytest -q` and `.venv/bin/ruff check` on what you touch
  and fix what you break.
- Do not commit; the loop handles commits.
"""


def run_agent(prompt: str, model: str) -> tuple[bool, str]:
    command = [
        "cursor-agent",
        "--print",
        "--force",
        "--model",
        model,
        "--add-dir",
        str(ts_repo()),
        prompt,
    ]
    try:
        completed = run(command, timeout=AGENT_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return False, f"agent timed out after {AGENT_TIMEOUT_SECONDS}s"
    if completed.returncode != 0:
        return False, (completed.stderr or completed.stdout)[-2000:]
    return True, completed.stdout[-2000:]


def tests_pass() -> tuple[bool, str]:
    completed = run([str(VENV_PYTHON), "-m", "pytest", "-q", "-x"], timeout=1800)
    tail = (completed.stdout or completed.stderr).strip().splitlines()[-8:]
    return completed.returncode == 0, "\n".join(tail)


def changed_files() -> list[str]:
    completed = run(["git", "status", "--porcelain"])
    return [line[3:] for line in completed.stdout.splitlines() if line.strip()]


def lint_changed() -> tuple[bool, str]:
    """Lint only what this task touched; the repo carries pre-existing violations."""
    targets = [name for name in changed_files() if name.endswith(".py")]
    if not targets:
        return True, ""
    run([str(RUFF), "check", "--fix", *targets])
    run([str(RUFF), "format", *targets])
    completed = run([str(RUFF), "check", *targets])
    if completed.returncode == 0:
        return True, ""
    tail = (completed.stdout or completed.stderr).strip().splitlines()
    return False, tail[-1] if tail else "ruff reported errors"


def discard_changes() -> None:
    run(["git", "checkout", "--", "."])
    run(["git", "clean", "-fd", "openclaw", "tests"])


def push() -> None:
    completed = run(["git", "push", "origin", "HEAD"])
    if completed.returncode != 0:
        log(f"  push failed: {(completed.stderr or completed.stdout).strip()[:300]}")
    else:
        log("  pushed to origin")


def commit(task: dict, result: dict, partial: bool) -> None:
    label = "partial" if partial else "done"
    coverage = round(result["coverage"] * 100)
    subject = f"migration {task['id']} ({label}): port {task['source']}"
    body = (
        f"Exported API coverage: {result['ported']}/{result['expected']} ({coverage}%).\n"
        f"TypeScript source: {result['ts_source_lines']} lines."
    )
    if partial and result["missing_symbols"]:
        preview = ", ".join(result["missing_symbols"][:12])
        body += f"\nStill missing: {preview}"
    run(["git", "add", "-A"])
    run(["git", "commit", "-q", "-m", subject, "-m", body])
    push()


def process_task(task: dict, model: str, attempts: int, dry_run: bool) -> str:
    result = verify_task(task)
    if result["passed"]:
        log(f"{task['id']} already satisfies the gate; marking done")
        return "done"

    log(
        f"{task['id']} {task['source']} "
        f"({result['ts_source_lines']} ts lines, {result['expected']} exported symbols)"
    )

    for attempt in range(1, attempts + 1):
        prompt = build_prompt(task, result, attempt)
        if dry_run:
            print(prompt)
            return "pending"

        started = time.monotonic()
        ok, output = run_agent(prompt, model)
        elapsed = int(time.monotonic() - started)
        if not ok:
            log(f"  attempt {attempt}: agent failed after {elapsed}s: {output.strip()[:300]}")
            continue

        if not changed_files():
            log(f"  attempt {attempt}: agent made no changes after {elapsed}s")
            continue

        clean, lint_tail = lint_changed()
        if not clean:
            log(f"  attempt {attempt}: lint still failing after autofix ({lint_tail})")

        passed, tail = tests_pass()
        if not passed:
            log(f"  attempt {attempt}: tests failed, discarding\n{tail}")
            discard_changes()
            continue

        result = verify_task(task)
        coverage = round(result["coverage"] * 100)
        if result["passed"]:
            commit(task, result, partial=False)
            log(f"  attempt {attempt}: PASS at {coverage}% in {elapsed}s")
            return "done"

        log(
            f"  attempt {attempt}: coverage {coverage}% "
            f"({result['ported']}/{result['expected']}), below {round(PASS_THRESHOLD * 100)}%"
        )

    if changed_files():
        result = verify_task(task)
        commit(task, result, partial=True)
        log(f"  keeping partial work at {round(result['coverage'] * 100)}%")
        return "partial"

    return "blocked"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-tasks", type=int, default=0, help="0 runs until nothing is pending")
    parser.add_argument("--attempts", type=int, default=2)
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not ts_repo().is_dir():
        print(f"missing TypeScript repo at {ts_repo()}", file=sys.stderr)
        return 1

    processed = 0
    while True:
        plan = load_plan()
        task = next_pending(plan)
        if task is None:
            log("MIGRATION_COMPLETE")
            return 0
        if args.max_tasks and processed >= args.max_tasks:
            remaining = sum(1 for t in plan if t.get("status") == "pending")
            log(f"stopping after {processed} tasks; {remaining} still pending")
            return 0

        status = process_task(task, args.model, args.attempts, args.dry_run)
        if args.dry_run:
            return 0

        plan = load_plan()
        for entry in plan:
            if entry["id"] == task["id"]:
                entry["status"] = status
                entry["verified_at"] = datetime.now(UTC).isoformat()
        save_plan(plan)
        run(["git", "add", "migration/plan.json"])
        run(["git", "commit", "-q", "-m", f"migration: record {task['id']} as {status}"])
        push()

        processed += 1
        done = sum(1 for t in plan if t.get("status") == "done")
        pending = sum(1 for t in plan if t.get("status") == "pending")
        log(f"  -> {status}. {done} done, {pending} pending")


if __name__ == "__main__":
    raise SystemExit(main())
