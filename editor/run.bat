@echo off
REM Запуск Editor из исходников

echo Запуск Editor...
python main.py %*

if errorlevel 1 (
    echo.
    echo Ошибка запуска приложения!
    echo Убедитесь, что установлены все зависимости:
    echo   pip install -r requirements.txt
    pause
)
