# -*- mode: python ; coding: utf-8 -*-
# PyInstaller tanımı: tek dosyalık, konsolsuz Windows programı (dist/Izin Takip Sistemi.exe).
# Kullanım (deponun kök klasöründe):  pyinstaller --noconfirm izin_takip.spec   — ya da derle.bat
# Windows dosya özellikleri (ürün adı, sürüm, telif) izin_takip/__init__.py'deki sabitlerden build/surum_bilgisi.txt'ye yazılır.
import os
import sys

KOK = os.path.abspath(SPECPATH)
sys.path.insert(0, KOK)
import izin_takip as P  # noqa: E402  (yalnız sabitler)

EXE_ADI = 'Izin Takip Sistemi'
_s = tuple(int(x) for x in P.SURUM.split('.')) + (0,) * (4 - len(P.SURUM.split('.')))
_bilgi = {
    'CompanyName': P.TELIF_SAHIBI,
    'FileDescription': P.UYGULAMA_ADI,
    'FileVersion': P.SURUM,
    'InternalName': 'IzinTakipSistemi',
    'LegalCopyright': f'{P.TELIF_KISA}. {P.TELIF}',
    'OriginalFilename': EXE_ADI + '.exe',
    'ProductName': P.UYGULAMA_ADI,
    'ProductVersion': P.SURUM,
    'Comments': P.WEB,
}
SURUM_DOSYASI = os.path.join(KOK, 'build', 'surum_bilgisi.txt')
os.makedirs(os.path.dirname(SURUM_DOSYASI), exist_ok=True)
with open(SURUM_DOSYASI, 'w', encoding='utf-8') as f:
    f.write(f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={_s}, prodvers={_s}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('041F04B0', [{', '.join(f'StringStruct({k!r}, {v!r})' for k, v in _bilgi.items())}])]),
    VarFileInfo([VarStruct('Translation', [0x041F, 1200])])
  ]
)
""")

a = Analysis(
    [os.path.join(KOK, 'baslat.py')],
    pathex=[KOK],
    binaries=[],
    datas=[(os.path.join(KOK, 'izin_takip', 'kaynaklar'), os.path.join('izin_takip', 'kaynaklar'))],
    hiddenimports=['PySide6.QtSvg', 'PySide6.QtPrintSupport'],
    hookspath=[],
    runtime_hooks=[],
    excludes=['tkinter', 'unittest', 'pydoc_data', 'PySide6.QtNetwork', 'PySide6.QtQml', 'PySide6.QtQuick', 'PySide6.QtOpenGL',
              'PySide6.QtDBus', 'PySide6.QtTest', 'PySide6.QtSql', 'PySide6.QtConcurrent', 'PySide6.QtXml'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXE_ADI,
    icon=os.path.join(KOK, 'izin_takip', 'kaynaklar', 'simge.ico'),
    console=False,
    debug=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    version=SURUM_DOSYASI,
)
