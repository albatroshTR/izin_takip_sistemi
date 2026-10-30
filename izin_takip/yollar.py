# -*- coding: utf-8 -*-
"""Dosya yerleri: program kaynakları (logo, yazı tipi) ve kullanıcı verisi (veritabanı, yedekler, çıktılar).

Veri klasörü varsayılan olarak Belgeler\\İzin Takip Sistemi (her kullanıcıda yazılabilir, yedeklemesi kolay). Başka bir yer
için IZIN_TAKIP_VERI ortam değişkeni ya da programın --veri <klasör> seçeneği kullanılır.
"""
import os
import sys

KLASOR_ADI = 'İzin Takip Sistemi'
_veri_klasoru = None


def kaynak(*parca):
    """Program içindeki kaynak dosya (PyInstaller ile paketlenince geçici açılma klasöründen)."""
    taban = getattr(sys, '_MEIPASS', None)
    if taban:
        return os.path.join(taban, 'izin_takip', 'kaynaklar', *parca)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kaynaklar', *parca)


def belgeler():
    try:
        from PySide6.QtCore import QStandardPaths
        yol = QStandardPaths.writableLocation(QStandardPaths.DocumentsLocation)
        if yol:
            return yol
    except Exception:  # pragma: no cover
        pass
    return os.path.join(os.path.expanduser('~'), 'Documents')


def veri_klasoru_ayarla(yol):
    global _veri_klasoru
    _veri_klasoru = os.path.abspath(yol) if yol else None


def veri_klasoru():
    yol = _veri_klasoru or os.environ.get('IZIN_TAKIP_VERI') or os.path.join(belgeler(), KLASOR_ADI)
    os.makedirs(yol, exist_ok=True)
    return yol


def veritabani_yolu():
    """Şifreli veri dosyası."""
    return os.path.join(veri_klasoru(), 'personel_takip.vt')


def giris_sayaci_yolu():
    return os.path.join(veri_klasoru(), 'giris.json')


def kilit_yolu():
    """Programın aynı veri klasöründe ikinci kez açılmasını önleyen kilit dosyası."""
    return os.path.join(veri_klasoru(), '.kilit')


def yedek_klasoru():
    return os.path.join(veri_klasoru(), 'yedekler')


def cikti_klasoru():
    yol = os.path.join(veri_klasoru(), 'çıktılar')
    os.makedirs(yol, exist_ok=True)
    return yol
