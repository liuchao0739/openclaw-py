from __future__ import annotations

from typing import Any

from openclaw.commands.doctor.cron_jobs import list_cron_jobs, validate_cron_expression
from openclaw.commands.doctor.doctor_fix import run_doctor_fix, run_doctor_scan


async def doctor_command(
    opts: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    options = opts or {}
    json_output = options.get("json", False)

    if options.get("fix"):
        result = await run_doctor_fix(options["fix"], runtime=rt)
        return result

    if options.get("scan"):
        issues = await run_doctor_scan(runtime=rt)
        if json_output:
            if rt.get("writeJson"):
                rt["writeJson"](rt, {"issues": issues})
            return {"issues": issues}

        if rt.get("log"):
            if not issues:
                rt["log"]("No issues found.")
            else:
                rt["log"](f"Found {len(issues)} issue(s):")
                for issue in issues:
                    rt["log"](f"  [{issue.get('code', 'unknown')}] {issue.get('message', '')}")
                    if issue.get("fix"):
                        rt["log"](f"    Fix: {issue['fix']}")
        return {"issues": issues}

    cron = options.get("cron")
    if cron is not None:
        validation = validate_cron_expression(str(cron))
        if json_output:
            if rt.get("writeJson"):
                rt["writeJson"](rt, validation)
            return validation
        if rt.get("log"):
            if validation.get("valid"):
                rt["log"](f"Cron expression '{cron}' is valid.")
            else:
                rt["error"](f"Invalid cron expression: {validation.get('error', '')}")
        return validation

    return {"ok": True}
