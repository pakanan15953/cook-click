@echo off
title Cookie Run Relic Button OCR Test (396, 361)
cd /d "%~dp0"
echo ===================================================
echo   Cookie Run Relic Button OCR Tester (X:396, Y:361)
echo ===================================================
echo.
.venv\Scripts\python.exe test_relic_ocr.py
echo.
pause
