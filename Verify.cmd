@echo off
setlocal
set "EDII_PY=%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe"
if not exist "%EDII_PY%" set "EDII_PY=python"
"%EDII_PY%" -B -X utf8 "%~dp0run_ed_ii.py" verify
set "EDII_EXIT=%ERRORLEVEL%"
pause
exit /b %EDII_EXIT%
