@echo off
setlocal
rem Store the model API token in config.json without pasting it into a chat.
set "HERE=%~dp0"
set "PYEXE=py"
where py.exe >nul 2>nul
if errorlevel 1 set "PYEXE=python"

echo [AOS] paste the token when asked - the input is hidden, and it is written
echo [AOS] straight into %HERE%config.json
echo.
"%PYEXE%" "%HERE%chat_server.py" --set-key
echo.
pause
endlocal
