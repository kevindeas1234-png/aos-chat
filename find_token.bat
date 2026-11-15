@echo off
setlocal
rem List the LM Studio tokens registered on this machine, and check or install one.
rem The passkey is stored by LM Studio only as a hash, so it cannot be read back -
rem this script verifies a pasted key instead of guessing at one.
rem
rem   double-click            list the registered tokens (ids only)
rem   find_token.bat --check  <token>    verify a key
rem   find_token.bat --apply  <token>    verify, then write it into config.json
rem
rem The key itself is never printed, only its client id and a masked form.
set "HERE=%~dp0"
set "PYEXE=py"
where py.exe >nul 2>nul
if errorlevel 1 set "PYEXE=python"

echo [AOS] checking LM Studio's token store...
echo.
"%PYEXE%" "%HERE%find_token.py" %*
echo.
pause
endlocal
