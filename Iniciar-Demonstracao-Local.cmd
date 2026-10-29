@echo off
setlocal
call npm.cmd --prefix "%~dp0frontend" run demo:local
if errorlevel 1 pause
endlocal
