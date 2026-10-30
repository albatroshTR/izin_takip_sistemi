# -*- coding: utf-8 -*-
"""Uygulama bağlamı: veritabanı + son hesap sonucu. Bir veri değişince yeniden hesaplar ve sayfalara 'degisti' sinyali gönderir."""
from PySide6.QtCore import QObject, Signal

from .. import motor


class Baglam(QObject):
    degisti = Signal()
    bildir = Signal(str, str)       # metin, tür ('bilgi' | 'hata')
    git = Signal(str, object)       # sayfa adı, parametre (ör. ('kart', personel_id))
    kilit_iste = Signal()           # oturumu kilitle (Ctrl+L, kenar çubuğu)
    cikis_iste = Signal()           # oturumu kapat

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.veri = None
        self.sonuc = None
        self.ozet = None
        self.bugun = None
        self.tarih_elle = False
        self.hesapla()

    def hesapla(self):
        self.bugun, self.tarih_elle = self.db.hesap_tarihi()
        self.veri = self.db.veri()
        self.sonuc = motor.hesapla_hepsi(self.veri, self.bugun)
        self.ozet = motor.ozet(self.sonuc, self.veri)

    def yenile(self, mesaj=None):
        self.hesapla()
        self.degisti.emit()
        if mesaj:
            self.bildir.emit(mesaj, 'bilgi')

    # kısayollar
    def kisi(self, pid):
        return self.sonuc.kisi.get(pid)

    def kayit(self, kid):
        return self.sonuc.kayit.get(kid)

    def izin(self, kid):
        return next((k for k in self.veri['izinler'] if k['id'] == kid), None)

    def personel(self, pid):
        return next((p for p in self.veri['personel'] if p['id'] == pid), None)

    @property
    def yonetici(self):
        return self.db.yonetici_mi()

    def sirket(self):
        return self.db.ayar('sirket') or 'Şirket'
