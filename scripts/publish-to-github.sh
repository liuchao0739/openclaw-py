#!/usr/bin/env bash
# One-shot: login (if needed), create repo, push main.
set -euo pipefail
cd "$(dirname "$0")/.."

REMOTE="https://github.com/liuchao0739/openclaw-py.git"

if ! gh auth status &>/dev/null; then
  echo ">>> GitHub CLI 未登录，请先完成交互登录（浏览器或 token）"
  gh auth login
fi

if ! gh repo view liuchao0739/openclaw-py &>/dev/null; then
  echo ">>> 创建远程仓库 liuchao0739/openclaw-py"
  gh repo create liuchao0739/openclaw-py --private --description "Python port of OpenClaw — multi-channel AI gateway" --source=. --remote=origin --push
else
  git remote get-url origin &>/dev/null || git remote add origin "$REMOTE"
  git push -u origin main
fi

echo ">>> 完成: https://github.com/liuchao0739/openclaw-py"