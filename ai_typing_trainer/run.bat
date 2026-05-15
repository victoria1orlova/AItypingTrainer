@echo off
set "DIR=%~dp0"
set "VENV=%DIR%..\\.venv\\Scripts\\activate.bat"
wezterm start -- cmd /k "chcp 65001 >nul && call "%VENV%" && python "%DIR%src\\main.py""
