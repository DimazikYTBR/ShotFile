@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul || (echo Python не найден. Установите его с python.org и отметьте Add Python to PATH. & pause & exit /b 1)
python -m pip install -r requirements.txt pyinstaller || (pause & exit /b 1)
python prebuild.py
python shotfile.py --make-icon
python -m PyInstaller --noconfirm --onedir --windowed --noupx --hidden-import pystray._win32 --name ShotFile --icon icon.ico --version-file version.txt shotfile.py || (pause & exit /b 1)
echo.
echo Готово: dist\ShotFile\ShotFile.exe
pause
