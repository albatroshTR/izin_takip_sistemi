# -*- coding: utf-8 -*-
"""Oturum: boşta kalınca otomatik kilit, elle kilit (Ctrl+L) ve oturumu kapatma.

Kilitlenince bütün pencereler gizlenir, kilit ekranı açılır; doğru parolayla pencereler geri gelir. "Farklı kullanıcıyla giriş" ve
"Oturumu kapat" programı kapatıp giriş ekranıyla yeniden açar (açık pencerelerdeki yarım işler güvenle kapanır; kaydedilmiş her şey
zaten diskte şifreli).
"""
import time

from PySide6.QtCore import QEvent, QObject, QTimer
from PySide6.QtWidgets import QApplication, QFileDialog

from .bilesenler import soru
from .giris import GirisPenceresi

ETKINLIK = {QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.KeyPress, QEvent.Wheel, QEvent.TouchBegin}
KILIT_SECENEK = [5, 10, 15, 30, 60]   # dakika


class Oturum(QObject):
    def __init__(self, app, baglam, pencere, sayac):
        super().__init__(pencere)
        self.app, self.b, self.pencere, self.sayac = app, baglam, pencere, sayac
        self.son = time.monotonic()
        self.kilitli = False
        self.yeniden_baslat = False
        app.installEventFilter(self)
        self.zaman = QTimer(self)
        self.zaman.setInterval(15000)
        self.zaman.timeout.connect(self._kontrol)
        self.zaman.start()
        baglam.kilit_iste.connect(self.kilitle)
        baglam.cikis_iste.connect(self.cikis)

    def eventFilter(self, nesne, olay):
        if olay.type() in ETKINLIK:
            self.son = time.monotonic()
        return False

    def sure(self):
        try:
            return max(1, int(self.b.db.ayar('kilit_dakika') or 10)) * 60
        except ValueError:
            return 600

    def _kontrol(self):
        if self.kilitli or time.monotonic() - self.son < self.sure():
            return
        if isinstance(QApplication.activeModalWidget(), QFileDialog):   # Windows'un dosya penceresi gizlenemez: kapanınca kilitlenir
            return
        self.kilitle()

    def kilitle(self):
        if self.kilitli:
            return
        self.kilitli = True
        gizli = [w for w in QApplication.topLevelWidgets() if w.isVisible() and w.isWindow()]
        for w in gizli:
            w.hide()
        k = GirisPenceresi(self.b.db.yol, self.sayac, db=self.b.db)
        self.kilit_penceresi = k
        k.exec()
        self.kilit_penceresi = None
        self.kilitli = False
        self.son = time.monotonic()
        if k.secim == 'acildi':
            for w in gizli:
                w.show()
            self.pencere.raise_()
            self.pencere.activateWindow()
            if self.app.activeModalWidget():
                self.app.activeModalWidget().raise_()
        elif k.secim == 'farkli':
            self.cikis(sor=False)
        else:
            self.app.exit(0)

    def cikis(self, sor=True):
        if sor and not soru(self.pencere, 'Oturumu kapat', 'Oturum kapatılsın mı? Program kapanıp giriş ekranıyla yeniden açılır.',
                            'Oturumu kapat'):
            return
        self.yeniden_baslat = True
        self.app.exit(0)
