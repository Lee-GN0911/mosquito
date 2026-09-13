@echo off
cd /d "%~dp0"
python -u collect_weather.py
if errorlevel 1 py -u collect_weather.py
echo.
pause
