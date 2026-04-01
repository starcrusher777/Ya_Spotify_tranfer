@echo off
setlocal
cd /d "%~dp0"
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt
pyinstaller --noconfirm SpotifyYandexTransfer.spec
echo.
echo Output: dist\SpotifyYandexTransfer.exe
endlocal
