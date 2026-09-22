@echo off
cd /d "%~dp0.."
python portable\launcher.py
if errorlevel 1 pause
