@echo off
title Cookie Run AI Bot EXE Builder
cd /d "%~dp0"
echo ===================================================
echo   Cookie Run AI Bot - Automatic EXE Builder
echo ===================================================
echo.

set PY=.venv\Scripts\python.exe
if not exist "%PY%" set PY=python

echo [*] Checking PyInstaller...
%PY% -m PyInstaller --version >nul 2>&1
if errorlevel 1 %PY% -m pip install pyinstaller

echo.
echo [*] Building yolo_bot.exe with PyInstaller...
%PY% -m PyInstaller --noconsole --onefile --name "yolo_bot" yolo_bot.py

if errorlevel 1 goto BUILD_FAILED

echo.
echo [*] Packaging distribution folder (Release_Folder)...
if not exist "Release_Folder" mkdir "Release_Folder"

copy /y "dist\yolo_bot.exe" "Release_Folder\yolo_bot.exe" >nul
if exist "best.onnx" copy /y "best.onnx" "Release_Folder\best.onnx" >nul
if exist "autochangeplayer.png" copy /y "autochangeplayer.png" "Release_Folder\autochangeplayer.png" >nul

if exist "autostart" xcopy /s /e /i /y "autostart" "Release_Folder\autostart" >nul

echo.
echo ===================================================
echo   BUILD SUCCESSFUL!
echo   All distribution files are ready in: Release_Folder
echo ===================================================
echo.
goto END

:BUILD_FAILED
echo.
echo [!] Build Failed! Please check the output above for errors.
echo.

:END
pause
