# OpenClaw Python

Python port of [OpenClaw](https://github.com/openclaw/openclaw).

## Status

Migration in progress. Specs and task lists live in the TypeScript repo under
`migration/`. Set `OPENCLAW_TS_REPO` to point at that checkout (defaults to
`/Users/liuchao/openclaw-ts`); tests that read from it skip when it is absent.

## Quick start

```bash
pip install -e ".[dev]"
openclaw-py --help
pytest
```

## Migration loop

Agent reads the next pending task from the phase progress file, ports the
module with tests, marks it done, commits, repeats.

```bash
python scripts/migration_next_task.py --phase 3 --count 5
```
