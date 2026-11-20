@echo off
setlocal
rem Copy the model API key in LM Studio, then double-click this.
rem The key is read from the clipboard, verified against LM Studio's stored hash,
rem and written to config.json - it is never typed, printed or pasted anywhere.
set "HERE=%~dp0"
set "PYEXE=py"
where py.exe >nul 2>nul
if errorlevel 1 set "PYEXE=python"

echo [AOS] copy the API key in LM Studio first, then continue.
echo.
"%PYEXE%" "%HERE%tools\set_key_from_clipboard.py" %*
echo.
pause
endlocal
