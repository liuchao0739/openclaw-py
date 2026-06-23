# Phase-2 全量迁移（P2-0001 → P2-0231）

## 目标

将 `/Users/liuchao/openclaw` 中 `src/`、`packages/`、前 50 个 `extensions/` 按
`migration/progress-phase2.json` **完整移植**到 `openclaw-py`（不缩水：逻辑与 TS 测试对齐，Python 侧补 pytest）。

## 现实边界

- **231 个任务**，合计 **上万** TS 源文件；无法在**单次**对话里全部写完。
- **可以**在多轮会话里持续推进直到 `MIGRATION_COMPLETE`；每轮尽量多 batch、每批跑满 pytest 再 commit/push。

## 每轮循环（与 `migration/LOOP.md` 一致）

1. `python scripts/phase2_next_task.py` — 看下一个 `pending` 任务 id 与路径。
2. 对照 TS 实现 + 现有 `.test.ts` → Python 模块 + `tests/`。
3. `cd openclaw-py && .venv/bin/python -m pytest -q`
4. 更新 `openclaw/migration/progress-phase2.json` 对应任务 `status: done`（在 openclaw 仓或同步到本仓 notes）。
5. `git commit` + `git push origin main`
6. 对用户说「继续」即重复 1–5。

## 进度真相源

- 清单：`/Users/liuchao/openclaw/migration/progress-phase2.json`
- 本仓 git log：`migration P2-xxxx` 提交与官方 id 可能不完全一一对应；以 JSON + pytest 为准。

## 大任务拆分原则（不缩水）

| 类型 | 做法 |
|------|------|
| 纯逻辑（policy、schema、path） | 全函数移植 + 单测 |
| IO（docker、gateway、channels） | 先 types + 纯函数 + 可 mock 的接口层，再接集成 |
| extensions / plugin-sdk | 按扩展目录任务 id 逐扩展移植 manifest + runtime |
| UI/TUI/React | 保留协议与类型；CLI 用 typer/文本替代时可注明 parity 点 |

## 当前会话策略

优先 **agents** 未完成任务（P2-0008 harness 余量、P2-0015 sandbox、P2-0017–0020 sessions），再 **auto-reply**、**gateway**、**config/sessions**，最后 **extensions** P2-0182+。