@echo off
REM Переход в папку с этим BAT-файлом
cd /d %~dp0

REM Запуск скрипта через pythonw (он не открывает консоль)
start "" pythonw "%~dp0black.py" dev
