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
echo [*] Building yolo_bot.exe with PyInstaller (Fast & Safe onedir mode)...
%PY% -m PyInstaller --noconsole --onedir --name "yolo_bot" ^
    --collect-all customtkinter ^
    --collect-all rapidocr_onnxruntime ^
    --collect-all ultralytics ^
    --copy-metadata ultralytics ^
    --copy-metadata rapidocr_onnxruntime ^
    --hidden-import win32gui ^
    --hidden-import win32con ^
    --hidden-import win32ui ^
    --exclude-module nltk ^
    --exclude-module spacy ^
    --exclude-module transformers ^
    --exclude-module tensorboard ^
    --exclude-module IPython ^
    --exclude-module notebook ^
    yolo_bot.py

if errorlevel 1 goto BUILD_FAILED

echo.
echo [*] Packaging distribution folder (Release_Folder)...
if not exist "Release_Folder" mkdir "Release_Folder"

xcopy /s /e /i /y "dist\yolo_bot\*" "Release_Folder\" >nul
if exist "best.onnx" copy /y "best.onnx" "Release_Folder\best.onnx" >nul
if exist "autochangeplayer.png" copy /y "autochangeplayer.png" "Release_Folder\autochangeplayer.png" >nul
if exist "treasure_config.json" copy /y "treasure_config.json" "Release_Folder\treasure_config.json" >nul

if exist "autostart" xcopy /s /e /i /y "autostart" "Release_Folder\autostart" >nul
if exist "templates" xcopy /s /e /i /y "templates" "Release_Folder\templates" >nul
if exist "treasures_db" xcopy /s /e /i /y "treasures_db" "Release_Folder\treasures_db" >nul

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
