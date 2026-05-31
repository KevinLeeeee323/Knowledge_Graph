#!/usr/bin/env bash
# 起一个最小本地静态服务器，浏览器访问 http://127.0.0.1:8000/viewer/
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
echo "知识图谱浏览器: http://127.0.0.1:${PORT}/viewer/"
echo "按 Ctrl+C 退出"
cd "$ROOT"
exec python3 -m http.server "$PORT"
