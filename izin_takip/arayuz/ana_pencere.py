# -*- coding: utf-8 -*-
"""Ana pencere: sol kenar çubuğu (gezinme) + sayfalar; belgeler (PDF / yazdır), Excel aktarımı ve sayfalar arası yönlendirme."""
import datetime
import os
import re

from PySide6.QtCore import QRectF, QSize, Qt, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QKeySequence, QPainter, QPainterPath, QPixmap, QShortcut
from PySide6.QtWidgets import (QButtonGroup, QFileDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QVBoxLayout, QWidget)

from . import tema as T
from .bilesenler import Bildirim, hata
from .kisi_satiri import KisaltEtiket
from .dialog_izin import izin_penceresi
from .ikonlar import ikon
from .sayfa_ayarlar import AyarlarSayfa
from .sayfa_ayrilanlar import AyrilanlarSayfa
from .sayfa_genel import GenelSayfa
from .sayfa_izinler import IzinlerSayfa
from .sayfa_kontroller import KontrollerSayfa
from .sayfa_personel import PersonelSayfa
from .sayfa_takvim import TakvimSayfa
from .sayfa_tatiller import TatillerSayfa
from .sayfa_yardim import YardimSayfa
from .. import SURUM, TELIF_KISA, UYGULAMA_ADI, raporlar, yollar
from ..veritabani import ROLLER
from ..yardimci import AYLAR, tarih_yaz

SAYFALAR = [('genel', 'Genel Durum', 'ana', GenelSayfa), ('personel', 'Personel', 'personel', PersonelSayfa),
            ('izinler', 'İzin Kayıtları', 'izin', IzinlerSayfa), ('takvim', 'Takvim', 'takvim', TakvimSayfa),
            ('ayrilan', 'Ayrılanlar', 'ayrilan', AyrilanlarSayfa), ('kontrol', 'Kontroller', 'kontrol', KontrollerSayfa),
            ('tatil', 'Tatiller', 'tatil', TatillerSayfa), ('ayar', 'Ayarlar', 'ayar', AyarlarSayfa), ('yardim', 'Yardım', 'yardim', YardimSayfa)]


class GezintiDugmesi(QPushButton):
    def __init__(self, metin, ikon_adi):
        super().__init__('  ' + metin)
        self.setObjectName('Gezinti')
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setIcon(ikon(ikon_adi, '#B9BAD6', 18, '#FFFFFF'))
        self.setIconSize(QSize(18, 18))
        self.setMinimumHeight(42)
        self.rozet = 0

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.isChecked():
            yol = QPainterPath()
            yol.addRoundedRect(QRectF(0, 10, 4, self.height() - 20), 2, 2)
            p.fillPath(yol, QColor(T.TURUNCU))
        if self.rozet:
            metin = str(self.rozet) if self.rozet < 1000 else '999+'
            p.setFont(T.font(8, True))
            w = max(22, p.fontMetrics().horizontalAdvance(metin) + 12)
            r = QRectF(self.width() - w - 10, (self.height() - 20) / 2, w, 20)
            yol = QPainterPath()
            yol.addRoundedRect(r, 10, 10)
            p.fillPath(yol, QColor(T.TURUNCU))
            p.setPen(QColor('white'))
            p.drawText(r, Qt.AlignCenter, metin)
        p.end()


class AnaPencere(QMainWindow):
    def __init__(self, baglam):
        super().__init__()
        self.b = baglam
        self.setWindowTitle(UYGULAMA_ADI)
        self.setWindowIcon(QIcon(yollar.kaynak('simge.png')))
        self.resize(1440, 900)
        self.setMinimumSize(1120, 700)
        merkez = QWidget()
        self.setCentralWidget(merkez)
        d = QHBoxLayout(merkez)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(0)

        # kenar çubuğu
        kenar = QFrame()
        kenar.setObjectName('Kenar')
        kenar.setFixedWidth(248)
        kd = QVBoxLayout(kenar)
        kd.setContentsMargins(14, 22, 14, 16)
        kd.setSpacing(3)
        logo = QLabel()
        px = QPixmap(yollar.kaynak('logo_koyu.png'))
        if not px.isNull():
            px.setDevicePixelRatio(2.0)
            logo.setPixmap(px.scaledToWidth(210 * 2, Qt.SmoothTransformation))
        logo.setContentsMargins(6, 0, 0, 0)
        kd.addWidget(logo)
        alt_ad = QLabel('PERSONEL TAKİP')
        alt_ad.setStyleSheet(f'color: {T.TURUNCU}; font-weight: 700; letter-spacing: 3px; font-size: 9pt; padding-left: 8px;')
        kd.addWidget(alt_ad)
        kd.addSpacing(18)
        self.gezinti = {}
        grup = QButtonGroup(self)
        grup.setExclusive(True)
        self.yigin = QStackedWidget()
        self.sayfa = {}
        for i, (ad, metin, ik, sinif) in enumerate(SAYFALAR):
            if ad == 'tatil':
                kd.addSpacing(10)
                b = QLabel('DÜZENLEME')
                b.setObjectName('KenarBolum')
                kd.addWidget(b)
                kd.addSpacing(2)
            dg = GezintiDugmesi(metin, ik)
            dg.clicked.connect(lambda _=False, a=ad: self.git(a))
            grup.addButton(dg)
            kd.addWidget(dg)
            self.gezinti[ad] = dg
            s = sinif(baglam)
            self.sayfa[ad] = s
            self.yigin.addWidget(s)
        kd.addStretch(1)
        self.alt_kart = QFrame()
        self.alt_kart.setObjectName('KenarAlt')
        ak = QVBoxLayout(self.alt_kart)
        ak.setContentsMargins(12, 10, 12, 10)
        ak.setSpacing(2)
        self.alt_tarih = QLabel()
        self.alt_tarih.setStyleSheet('font-weight: 600; color: white;')
        self.alt_kisi = QLabel()
        self.alt_kisi.setStyleSheet('font-size: 8.5pt;')
        self.elle = QLabel('Hesap tarihi elle ayarlı')
        self.elle.setObjectName('TarihUyari')
        ak.addWidget(self.alt_tarih)
        ak.addWidget(self.alt_kisi)
        ak.addWidget(self.elle)
        cizgi = QFrame()
        cizgi.setObjectName('KenarCizgi')
        cizgi.setFixedHeight(1)
        ak.addSpacing(6)
        ak.addWidget(cizgi)
        ak.addSpacing(4)
        hesap = QHBoxLayout()
        hesap.setSpacing(6)
        ad = QVBoxLayout()
        ad.setSpacing(0)
        self.alt_hesap = KisaltEtiket()
        self.alt_hesap.setStyleSheet('font-weight: 600; color: white;')
        self.alt_rol = QLabel()
        self.alt_rol.setStyleSheet('font-size: 8pt; color: rgba(255,255,255,0.55);')
        ad.addWidget(self.alt_hesap)
        ad.addWidget(self.alt_rol)
        hesap.addLayout(ad, 1)
        for ik, ipucu, sinyal in (('kilit', 'Kilitle (Ctrl+L)', baglam.kilit_iste), ('cikis', 'Oturumu kapat', baglam.cikis_iste)):
            dg = QPushButton()
            dg.setObjectName('KenarDugme')
            dg.setIcon(ikon(ik, '#D9DAEC', 16))
            dg.setIconSize(QSize(16, 16))
            dg.setFixedSize(32, 32)
            dg.setToolTip(ipucu)
            dg.setCursor(Qt.PointingHandCursor)
            dg.clicked.connect(sinyal.emit)
            hesap.addWidget(dg)
        ak.addLayout(hesap)
        kd.addWidget(self.alt_kart)
        surum = QLabel(f'Sürüm {SURUM} · {TELIF_KISA}')
        surum.setStyleSheet('color: rgba(255,255,255,0.38); font-size: 8pt; padding: 6px 4px 0 4px;')
        kd.addWidget(surum)
        d.addWidget(kenar)
        d.addWidget(self.yigin, 1)

        self.bildirim = Bildirim(self)
        baglam.bildir.connect(self.bildirim.goster)
        baglam.git.connect(self._yonlendir)
        baglam.degisti.connect(self._guncelle)
        QShortcut(QKeySequence('Ctrl+N'), self, activated=lambda: izin_penceresi(self.b, self))
        QShortcut(QKeySequence('Ctrl+F'), self, activated=self._ara)
        QShortcut(QKeySequence('F5'), self, activated=lambda: self.b.yenile('Yenilendi'))
        QShortcut(QKeySequence('Ctrl+L'), self, activated=baglam.kilit_iste.emit)
        self._guncelle()
        self.git('genel')

    def git(self, ad):
        self.gezinti[ad].setChecked(True)
        self.yigin.setCurrentWidget(self.sayfa[ad])
        if ad == 'personel':
            self.sayfa['personel'].ac(None)

    def _ara(self):
        s = self.yigin.currentWidget()
        if hasattr(s, 'arama'):
            s.arama.setFocus()
            s.arama.selectAll()

    def _guncelle(self):
        b = self.b
        self.alt_tarih.setText(f'{tarih_yaz(b.bugun)}')
        self.alt_kisi.setText(f'{b.ozet["calisan"]} çalışan')
        o = b.db.oturum or {}
        self.alt_hesap.metin_ayarla(b.db.kullanici(), f'{b.db.kullanici()} ({o.get("kullanici_adi", "")})')
        self.alt_rol.setText(ROLLER.get(o.get('rol'), ''))
        self.elle.setVisible(b.tarih_elle)
        self.gezinti['kontrol'].rozet = b.ozet['uyarili_kayit'] + b.ozet['personel_uyari']
        self.gezinti['kontrol'].update()
        self.gezinti['ayrilan'].rozet = b.ozet['ayrilan']
        self.gezinti['ayrilan'].update()

    # ------------------------------------------------------------------ yönlendirme
    def _yonlendir(self, ad, parametre):
        if ad == 'kart':
            self.git('personel')
            self.sayfa['personel'].ac(parametre)
        elif ad in self.sayfa:
            self.git(ad)
            if parametre is not None:
                self.sayfa[ad].ac(parametre)
        elif ad == 'excel':
            self._excel()
        elif ad == 'pdf_kart':
            ks = self.b.kisi(parametre)
            tum = not self.sayfa['personel'].kart.sadece_yillik.isChecked()
            self._belge(raporlar.html_kart(self.b, parametre, tum), f'İzin Kartı - {ks["ad"]}')
        elif ad == 'pdf_form':
            k = self.b.izin(parametre)
            self._belge(raporlar.html_form(self.b, parametre), f'İzin Formu - No {k["no"]} - {self.b.kisi(k["personel_id"])["ad"]}')
        elif ad == 'pdf_genel':
            self._belge(raporlar.html_genel(self.b), f'Kalan İzinler - {tarih_yaz(self.b.bugun)}', yatay=True)
        elif ad == 'pdf_takvim':
            yil, ay = parametre
            self._belge(raporlar.html_takvim(self.b, yil, ay), f'İzin Takvimi - {AYLAR[ay - 1]} {yil}', yatay=True)

    def _belge(self, html, ad, yatay=False):
        m = QMessageBox(self)
        m.setWindowTitle('Belge')
        m.setIcon(QMessageBox.Question)
        m.setText(f'<b>{ad}</b><br><br>PDF olarak açılsın mı, yoksa doğrudan yazıcıya mı gönderilsin?')
        pdf = m.addButton('PDF olarak aç', QMessageBox.AcceptRole)
        pdf.setObjectName('Birincil')
        yaz = m.addButton('Yazıcıya gönder', QMessageBox.ActionRole)
        m.addButton('Vazgeç', QMessageBox.RejectRole)
        m.setDefaultButton(pdf)
        m.exec()
        if m.clickedButton() is pdf:
            dosya = re.sub(r'[\\/:*?"<>|]', '-', ad) + '.pdf'
            yol = os.path.join(yollar.cikti_klasoru(), dosya)
            try:
                raporlar.pdf_kaydet(html, yol, yatay)
            except Exception as e:  # dosya açık olabilir
                hata(self, f'PDF kaydedilemedi: {e}\n\nAynı adlı PDF başka bir programda açıksa kapatıp tekrar deneyin.')
                return
            QDesktopServices.openUrl(QUrl.fromLocalFile(yol))
            self.bildirim.goster(f'PDF kaydedildi: çıktılar\\{dosya}')
        elif m.clickedButton() is yaz:
            raporlar.yazdir(html, self, yatay)

    def _excel(self):
        from .. import disa_aktar
        ad = f'Personel Takip - {self.b.bugun:%Y-%m-%d}.xlsx'
        yol, _ = QFileDialog.getSaveFileName(self, 'Excel\'e aktar', os.path.join(yollar.cikti_klasoru(), ad), 'Excel (*.xlsx)')
        if not yol:
            return
        try:
            disa_aktar.excel_yaz(self.b, yol)
        except PermissionError:
            hata(self, 'Dosya kaydedilemedi: aynı adlı dosya Excel\'de açık olabilir. Kapatıp tekrar deneyin.')
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(yol))
        self.bildirim.goster('Excel dosyası kaydedildi')
