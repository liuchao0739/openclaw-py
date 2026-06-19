# OpenClaw Python

Python port of [OpenClaw](https://github.com/openclaw/openclaw).

## Status

Migration in progress. See `/Users/liuchao/openclaw/migration/` for specs and progress.

## Quick start

```bash
cd /Users/liuchao/openclaw-py
pip install -e ".[dev]"
openclaw-py --help
```

## Migration loop

Agent reads `migration/progress.json`, executes next pending task, commits, repeats.
