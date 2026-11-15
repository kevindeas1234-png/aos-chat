@echo off
setlocal
rem AOS chat - local page, works on this PC and on your phone over the LAN.
set "HERE=%~dp0"
set "PYEXE=py"
where py.exe >nul 2>nul
if errorlevel 1 set "PYEXE=python"

rem proof that this launcher ran, and when
>> "%HERE%launcher_log.txt" echo %DATE% %TIME% launch attempt

echo [AOS] starting the chat app...
echo [AOS] the LAN address is printed below - open it on your phone
echo.
"%PYEXE%" -u "%HERE%chat_server.py" %* 2>"%HERE%error.log"
set "RC=%errorlevel%"

>> "%HERE%launcher_log.txt" echo %DATE% %TIME% exited with %RC%
echo.
if not "%RC%"=="0" (
  echo [AOS] chat exited with code %RC% - see error.log
  type "%HERE%error.log"
)
echo [AOS] chat stopped.
pause
endlocal
