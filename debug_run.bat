@echo off
cd /d "%~dp0"
echo Running fab_compressor.py directly...
echo.
python fab_compressor.py
echo.
echo Exit code: %errorlevel%
echo.
pause
