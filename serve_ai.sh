#!/usr/bin/env bash
# 启动带 Ollama 错题分析 API 的本地服务。
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-8000}"
MODEL="${OLLAMA_MODEL:-qwen2.5:7b}"
OLLAMA_URL="${OLLAMA_URL:-http://127.0.0.1:11434}"
OLLAMA_TIMEOUT="${OLLAMA_TIMEOUT:-300}"
exec python3 "$ROOT/code/problem_analyzer_server.py" \
  --port "$PORT" \
  --model "$MODEL" \
  --ollama-url "$OLLAMA_URL" \
  --timeout "$OLLAMA_TIMEOUT"
