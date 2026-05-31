@echo off
REM 起一个最小本地静态服务器，浏览器访问 http://127.0.0.1:8000/viewer/
setlocal
if "%PORT%"=="" set PORT=8000
echo 知识图谱浏览器: http://127.0.0.1:%PORT%/viewer/
echo 按 Ctrl+C 退出
cd /d "%~dp0"
python -m http.server %PORT%
