@echo off
setlocal
rem Probe for a local model endpoint and write the result where the agent can read it.
set "OUT=D:\AOS-chat\endpoint_report.txt"

>  "%OUT%" echo AOS endpoint probe
>> "%OUT%" echo %DATE% %TIME%
>> "%OUT%" echo.
>> "%OUT%" echo --- port 1234 (LM Studio) ---
curl -s -m 4 http://127.0.0.1:1234/v1/models >> "%OUT%" 2>&1
if errorlevel 1 >> "%OUT%" echo [failed, curl exit %errorlevel%]
>> "%OUT%" echo.
>> "%OUT%" echo --- port 11434 (Ollama) ---
curl -s -m 4 http://127.0.0.1:11434/v1/models >> "%OUT%" 2>&1
if errorlevel 1 >> "%OUT%" echo [failed, curl exit %errorlevel%]
>> "%OUT%" echo.
>> "%OUT%" echo --- done ---

type "%OUT%"
echo.
echo [AOS] written to %OUT%
pause
endlocal
