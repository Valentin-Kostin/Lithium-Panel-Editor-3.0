@echo off
REM Сборка Editor в Windows приложение

echo ========================================
echo Сборка Editor
echo ========================================
echo.

REM Проверка наличия PyInstaller
python -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo Установка PyInstaller...
    pip install pyinstaller
)

echo.
echo Очистка предыдущей сборки...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
del /q *.spec 2>nul

echo.
echo Сборка приложения (onedir режим - рекомендуется)...
pyinstaller --noconfirm --clean --windowed --name "Editor" ^
    --add-data "config;config" ^
    --add-data "resources;resources" ^
    main.py

if errorlevel 1 (
    echo.
    echo Ошибка сборки!
    pause
    exit /b 1
)

echo.
echo ========================================
echo Сборка завершена успешно!
echo Приложение находится в папке: dist\Editor
echo ========================================
echo.

REM Опциональная сборка в onefile режим
echo Хотите собрать в один exe-файл? (y/n)
set /p answer=
if /i "%answer%"=="y" (
    echo.
    echo Сборка в onefile режиме...
    rmdir /s /q build 2>nul
    del /q *.spec 2>nul
    
    pyinstaller --noconfirm --clean --onefile --windowed --name "Editor" ^
        --add-data "config;config" ^
        --add-data "resources;resources" ^
        main.py
    
    if errorlevel 1 (
        echo.
        echo Ошибка сборки onefile!
    ) else (
        echo.
        echo Onefile версия находится в папке: dist\Editor.exe
    )
)

echo.
pause
