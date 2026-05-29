@echo off
cd /d "%~dp0\.."
py code\annotation_server.py
if errorlevel 1 python code\annotation_server.py
