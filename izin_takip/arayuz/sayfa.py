# -*- coding: utf-8 -*-
"""Sayfa temeli: veri değişince görünür sayfa hemen, gizli sayfa gösterildiğinde yenilenir."""
from PySide6.QtWidgets import QVBoxLayout, QWidget

from .bilesenler import SayfaBasligi


class Sayfa(QWidget):
    baslik = ''
    alt_baslik = ''

    def __init__(self, baglam, parent=None):
        super().__init__(parent)
        self.setObjectName('Icerik')
        self.b = baglam
        self._kirli = True
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(30, 26, 30, 24)
        self.duzen.setSpacing(16)
        self.ust = SayfaBasligi(self.baslik, self.alt_baslik)
        self.duzen.addWidget(self.ust)
        baglam.degisti.connect(self._degisti)

    def _degisti(self):
        if self.isVisible():
            self.yenile()
            self._kirli = False
        else:
            self._kirli = True

    def showEvent(self, e):
        super().showEvent(e)
        if self._kirli:
            self.yenile()
            self._kirli = False

    def yenile(self):  # alt sınıflar doldurur
        pass

    def ac(self, parametre):  # başka sayfadan yönlendirme (ör. kişi kartı)
        pass
