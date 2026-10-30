@echo off
rem Izin Takip Sistemi: Windows programini (.exe) derler.
rem Gerekli: Python 3.9 veya ustu (python.org; kurulumda "Add python.exe to PATH" isaretli).
rem Cikti: dist\Izin Takip Sistemi.exe  (bu tek dosyayi istediginiz yere kopyalayip cift tiklayin)
chcp 65001 > nul
cd /d "%~dp0"
if not exist .venv (
    echo Sanal ortam hazirlaniyor...
    python -m venv .venv || goto hata
)
call .venv\Scripts\activate.bat || goto hata
python -m pip install --upgrade pip > nul
python -m pip install -r gereksinimler.txt pyinstaller || goto hata
echo Testler calisiyor...
set QT_QPA_PLATFORM=offscreen
python testler\test_uygulama.py || goto hata
set QT_QPA_PLATFORM=
echo Program derleniyor...
pyinstaller --noconfirm --clean izin_takip.spec || goto hata
echo.
echo TAMAM: dist\Izin Takip Sistemi.exe
explorer dist
goto :eof
:hata
echo.
echo HATA: derleme tamamlanamadi. Yukaridaki mesaja bakin.
pause
exit /b 1
