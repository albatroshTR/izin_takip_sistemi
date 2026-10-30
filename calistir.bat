@echo off
rem Izin Takip Sistemi: programi Python ile (derlemeden) calistirir. Ilk calistirmada gerekli paketleri kurar.
chcp 65001 > nul
cd /d "%~dp0"
if not exist .venv (
    echo Ilk calistirma: paketler kuruluyor, birkac dakika surebilir...
    python -m venv .venv || goto hata
    call .venv\Scripts\activate.bat || goto hata
    python -m pip install -r gereksinimler.txt || goto hata
) else (
    call .venv\Scripts\activate.bat || goto hata
)
start "" pythonw baslat.py %*
goto :eof
:hata
echo HATA: Python bulunamadi ya da paketler kurulamadi. python.org'dan Python 3.9+ kurun ("Add python.exe to PATH" isaretli).
pause
exit /b 1
