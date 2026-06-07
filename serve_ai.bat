@echo off
REM 启动带 Ollama 错题分析 API 的本地服务。
setlocal
if "%PORT%"=="" set PORT=8000
if "%OLLAMA_MODEL%"=="" set OLLAMA_MODEL=qwen2.5:7b
if "%OLLAMA_URL%"=="" set OLLAMA_URL=http://127.0.0.1:11434
if "%OLLAMA_TIMEOUT%"=="" set OLLAMA_TIMEOUT=300
python "%~dp0code\problem_analyzer_server.py" --port %PORT% --model %OLLAMA_MODEL% --ollama-url %OLLAMA_URL% --timeout %OLLAMA_TIMEOUT%
