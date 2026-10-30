# -*- coding: utf-8 -*-
"""Giriş, kilit ekranı, ilk kurulumda yönetici hesabı, kurtarma anahtarı, parola değiştirme ve kullanıcı hesabı pencereleri."""
import datetime
import html
import os

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QGuiApplication, QIcon, QPixmap
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QDialog, QFrame, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
                               QWidget)

from . import tema as T
from .bilesenler import bilgi, dugme, etiket, yatay
from .ikonlar import ikon, pixmap
from .. import SURUM, TELIF, TELIF_KISA, UYGULAMA_ADI, WEB, guvenlik, yollar
from ..veritabani import ROLLER, Veritabani, VeriHatasi


class ParolaKutusu(QLineEdit):
    """Parola alanı; sağdaki göz simgesiyle yazılanı gösterir / gizler."""

    def __init__(self, ipucu='', parent=None):
        super().__init__(parent)
        self.setEchoMode(QLineEdit.Password)
        self.setPlaceholderText(ipucu)
        self.setMinimumHeight(40)
        self._goz = QAction(ikon('goz', T.SOLUK, 16), 'Parolayı göster', self)
        self._goz.triggered.connect(self._degistir)
        self.addAction(self._goz, QLineEdit.TrailingPosition)

    def _degistir(self):
        gizli = self.echoMode() == QLineEdit.Password
        self.setEchoMode(QLineEdit.Normal if gizli else QLineEdit.Password)
        self._goz.setIcon(ikon('goz_kapali' if gizli else 'goz', T.SOLUK, 16))
        self._goz.setText('Parolayı gizle' if gizli else 'Parolayı göster')


def _kutu(ipucu=''):
    k = QLineEdit()
    k.setPlaceholderText(ipucu)
    k.setMinimumHeight(40)
    return k


def iletisim_html(renk):
    return (f'{html.escape(TELIF_KISA)}<br>{html.escape(TELIF)}<br>'
            f'<a href="{WEB}" style="color:{renk}; text-decoration:none">{WEB.split("//")[1]}</a>')


class GirisCercevesi(QDialog):
    """İki bölmeli pencere: solda lacivert tanıtım (logo, program adı, telif), sağda form."""

    def __init__(self, baslik, alt, parent=None):
        super().__init__(parent)
        self.setWindowTitle(UYGULAMA_ADI)
        self.setWindowIcon(QIcon(yollar.kaynak('simge.png')))
        self.setMinimumSize(900, 560)
        ana = QHBoxLayout(self)
        ana.setContentsMargins(0, 0, 0, 0)
        ana.setSpacing(0)

        sol = QFrame()
        sol.setObjectName('GirisSol')
        sol.setFixedWidth(340)
        sd = QVBoxLayout(sol)
        sd.setContentsMargins(34, 40, 30, 26)
        sd.setSpacing(6)
        logo = QLabel()
        px = QPixmap(yollar.kaynak('logo_koyu.png'))
        if not px.isNull():
            px.setDevicePixelRatio(2.0)
            logo.setPixmap(px.scaledToWidth(250 * 2, Qt.SmoothTransformation))
        sd.addWidget(logo)
        sd.addSpacing(34)
        sd.addWidget(etiket('PERSONEL TAKİP', 'GirisUst'))
        sd.addWidget(etiket(UYGULAMA_ADI, 'GirisAd', True))
        sd.addSpacing(6)
        sd.addWidget(etiket('Yıllık izin hakları, izin kayıtları ve kalan izinler; 4857 sayılı İş Kanunu\'na göre hesaplanır.', None, True))
        sd.addStretch(1)
        guv = QHBoxLayout()
        guv.setSpacing(8)
        ik = QLabel()
        ik.setPixmap(pixmap('kalkan', T.TURUNCU, 18))
        guv.addWidget(ik, 0, Qt.AlignTop)
        guv.addWidget(etiket('Veriler parolayla şifrelenir (AES-256). Parola olmadan veri dosyası okunamaz ve değiştirilemez.', None, True), 1)
        sd.addLayout(guv)
        sd.addSpacing(14)
        telif = QLabel(iletisim_html('rgba(255,255,255,0.75)') + f'<br>Sürüm {SURUM}')
        telif.setObjectName('GirisTelif')
        telif.setWordWrap(True)
        telif.setOpenExternalLinks(True)
        sd.addWidget(telif)
        ana.addWidget(sol)

        sag = QWidget()
        sag.setObjectName('GirisSag')
        self.form = QVBoxLayout(sag)
        self.form.setContentsMargins(48, 46, 48, 34)
        self.form.setSpacing(8)
        self.baslik = etiket(baslik, 'SayfaBaslik')
        self.form.addWidget(self.baslik)
        self.alt = etiket(alt, 'SayfaAlt', True)
        self.form.addWidget(self.alt)
        self.form.addSpacing(14)
        ana.addWidget(sag, 1)
        self.mesaj = etiket('', 'GirisMesaj', True)
        self.mesaj.hide()

    def alan(self, metin, w):
        self.form.addWidget(etiket(metin, 'AlanEtiket'))
        self.form.addWidget(w)
        self.form.addSpacing(4)
        return w

    def hata_goster(self, metin):
        self.mesaj.setText(metin)
        self.mesaj.setVisible(bool(metin))


def _bekle_imleci(f):
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        return f()
    finally:
        QApplication.restoreOverrideCursor()


# ----------------------------------------------------------------------------- giriş / kilit
class GirisPenceresi(GirisCercevesi):
    """Kullanıcı adı + parola ile giriş. db verilirse kilit ekranı: yalnız oturumdaki kullanıcının parolası sorulur.
    Sonuç: self.sonuc (açılan Veritabani; giriş), self.secim ('acildi' | 'farkli' | 'kapat'; kilit)."""

    def __init__(self, yol, sayac, db=None, parent=None):
        self.kilit = db is not None
        if self.kilit:
            super().__init__('Oturum kilitli', f'{db.oturum["ad_soyad"]} oturumu kilitlendi. Devam etmek için parolanızı yazın.', parent)
        else:
            super().__init__('Giriş', 'Kullanıcı adınızı ve parolanızı yazın.', parent)
        self.yol, self.sayac, self.db = yol, sayac, db
        self.sonuc = None
        self.secim = None
        self.parola_metni = None   # zorunlu parola değiştirmede "mevcut parola" olarak kullanılır, sonra silinir
        self.kullanici = self.alan('Kullanıcı adı', _kutu('ör. ayse.ornek'))
        if self.kilit:
            self.kullanici.setText(db.oturum['kullanici_adi'])
            self.kullanici.setEnabled(False)
        self.parola = self.alan('Parola', ParolaKutusu())
        self.form.addWidget(self.mesaj)
        self.form.addSpacing(6)
        self.giris = dugme('Kilidi aç' if self.kilit else 'Giriş yap', None, 'Birincil')
        self.giris.setMinimumHeight(44)
        self.giris.setDefault(True)
        self.giris.clicked.connect(self._giris)
        self.form.addWidget(self.giris)
        self.form.addSpacing(6)
        if self.kilit:
            farkli = dugme('Farklı kullanıcıyla giriş', 'kisi', 'Bag')
            farkli.clicked.connect(lambda: self._bitir('farkli'))
            kapat = dugme('Programı kapat', 'cikis', 'Bag')
            kapat.clicked.connect(lambda: self._bitir('kapat'))
            self.form.addLayout(yatay(farkli, None, kapat))
        else:
            unuttum = dugme('Parolamı unuttum', 'anahtar', 'Bag')
            unuttum.clicked.connect(self._unuttum)
            self.form.addLayout(yatay(unuttum, None))
        self.form.addStretch(1)
        self.kullanici.returnPressed.connect(self.parola.setFocus)
        self.parola.returnPressed.connect(self._giris)
        (self.parola if self.kilit else self.kullanici).setFocus()
        self._sayac_zamani = QTimer(self)
        self._sayac_zamani.setInterval(1000)
        self._sayac_zamani.timeout.connect(self._bekleme)
        self._bekleme()

    def _bekleme(self):
        kalan = self.sayac.bekleme()
        if kalan > 0:
            self.giris.setEnabled(False)
            self.hata_goster(f'Çok fazla hatalı deneme. {int(kalan) + 1} saniye sonra yeniden deneyin.')
            if not self._sayac_zamani.isActive():
                self._sayac_zamani.start()
        else:
            if self._sayac_zamani.isActive():
                self._sayac_zamani.stop()
                self.hata_goster('')
            self.giris.setEnabled(True)
        return kalan

    def _giris(self):
        if self._bekleme() > 0:
            return
        ad, p = self.kullanici.text(), self.parola.text()
        if not ad.strip() or not p:
            self.hata_goster('Kullanıcı adını ve parolayı yazın.')
            return
        hatali = (self.sayac.hatali, self.sayac.son)
        try:
            if self.kilit:
                if not _bekle_imleci(lambda: self.db.parola_dogru(p)):
                    raise guvenlik.ParolaHatasi('Parola hatalı.')
                self.db.hatali_denemeleri_yaz(hatali)
            else:
                self.sonuc = _bekle_imleci(lambda: Veritabani.ac(self.yol, ad, p, hatali=hatali))
        except guvenlik.ParolaHatasi as e:
            self.sayac.hata()
            self.parola.clear()
            self.parola.setFocus()
            self.hata_goster(str(e))
            self._bekleme()
            return
        except VeriHatasi as e:   # dosya bozuk / değiştirilmiş
            self.hata_goster(str(e))
            return
        self.sayac.basari()
        self.parola_metni = p
        self._bitir('acildi')

    def _unuttum(self):
        k = KurtarmaPenceresi(self.yol, self.sayac, self)
        if k.exec():
            self.sonuc = k.sonuc
            self.parola_metni = None
            self._bitir('acildi')

    def _bitir(self, secim):
        self.secim = secim
        self.accept()

    def reject(self):
        if not self.kilit:   # kilit ekranı Esc ile kapanmaz
            super().reject()

    def closeEvent(self, e):
        if self.kilit and self.secim is None:
            e.ignore()
        else:
            super().closeEvent(e)


class KurtarmaPenceresi(GirisCercevesi):
    """Parolası unutulan hesaba kurtarma anahtarıyla yeni parola."""

    def __init__(self, yol, sayac, parent=None):
        super().__init__('Parolamı unuttum', 'Kullanıcıysanız yöneticinizden parolanızı sıfırlamasını isteyin. Yöneticiyseniz kurulumda '
                         'verilen kurtarma anahtarıyla yeni bir parola belirleyin.', parent)
        self.yol, self.sayac = yol, sayac
        self.sonuc = None
        self.anahtar = self.alan('Kurtarma anahtarı', _kutu('XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX-XXXX'))
        self.kullanici = self.alan('Kullanıcı adı', _kutu())
        self.yeni = self.alan('Yeni parola', ParolaKutusu('en az 8 karakter; harf ve rakam'))
        self.tekrar = self.alan('Yeni parola (tekrar)', ParolaKutusu())
        self.form.addWidget(self.mesaj)
        tamam = dugme('Parolayı yenile ve giriş yap', None, 'Birincil')
        tamam.setMinimumHeight(42)
        tamam.setDefault(True)
        tamam.clicked.connect(self._tamam)
        geri = dugme('Geri', 'geri', 'Duz')
        geri.clicked.connect(self.reject)
        self.form.addLayout(yatay(geri, None, tamam))
        self.form.addStretch(1)

    def _tamam(self):
        if self.sayac.bekleme() > 0:
            self.hata_goster(f'Çok fazla hatalı deneme. {int(self.sayac.bekleme()) + 1} saniye sonra yeniden deneyin.')
            return
        ad = self.kullanici.text()
        try:
            if self.yeni.text() != self.tekrar.text():
                raise VeriHatasi('Yeni parola ile tekrarı aynı değil.')
            guvenlik.parola_kontrol(self.yeni.text(), ad)
            hatali = (self.sayac.hatali, self.sayac.son)
            try:
                db = _bekle_imleci(lambda: Veritabani.kurtarma_ile_ac(self.yol, self.anahtar.text()))
            except guvenlik.ParolaHatasi:
                self.sayac.hata()
                raise
            try:
                _bekle_imleci(lambda: db.parola_kurtar(ad, self.yeni.text()))
                db.oturum_ac(ad, hatali)
            except VeriHatasi:
                db.kapat()
                raise
        except VeriHatasi as e:
            self.hata_goster(str(e))
            return
        self.sayac.basari()
        self.sonuc = db
        bilgi(self, 'Parolanız yenilendi. Bundan sonra yeni parolanızla girin.', 'Parola yenilendi')
        self.accept()


# ----------------------------------------------------------------------------- ilk kurulum
class HesapOlusturPenceresi(GirisCercevesi):
    """İlk açılış: yönetici hesabı."""

    def __init__(self, yol, parent=None):
        super().__init__('Yönetici hesabı oluşturun', 'Programa bu hesapla girilir. Veriler bu parolayla şifrelenir: parola olmadan veri '
                         'dosyası açılamaz. Diğer kullanıcıları sonra Ayarlar › Kullanıcılar\'dan eklersiniz.', parent)
        self.yol = yol
        self.sonuc = self.kurtarma = None
        self.ad_soyad = self.alan('Ad Soyad', _kutu('ör. Ayşe Örnek'))
        self.kullanici = self.alan('Kullanıcı adı', _kutu('ör. ayse.ornek'))
        self.parola = self.alan('Parola', ParolaKutusu('en az 8 karakter; harf ve rakam'))
        self.tekrar = self.alan('Parola (tekrar)', ParolaKutusu())
        self.form.addWidget(self.mesaj)
        tamam = dugme('Hesabı oluştur', None, 'Birincil')
        tamam.setMinimumHeight(42)
        tamam.setDefault(True)
        tamam.clicked.connect(self._tamam)
        vazgec = dugme('Vazgeç', tur='Duz')
        vazgec.clicked.connect(self.reject)
        self.form.addLayout(yatay(vazgec, None, tamam))
        self.form.addStretch(1)
        self.ad_soyad.setFocus()

    def _tamam(self):
        try:
            if self.parola.text() != self.tekrar.text():
                raise VeriHatasi('Parola ile tekrarı aynı değil.')
            ad = guvenlik.kullanici_adi_kontrol(self.kullanici.text())
            guvenlik.parola_kontrol(self.parola.text(), ad)
            self.sonuc, self.kurtarma = _bekle_imleci(lambda: Veritabani.olustur(self.yol, ad, self.ad_soyad.text(), self.parola.text()))
        except VeriHatasi as e:
            self.hata_goster(str(e))
            return
        self.accept()


class KurtarmaAnahtariPenceresi(QDialog):
    """Kurtarma anahtarını bir kez gösterir; saklandığı onaylanmadan kapanmaz."""

    def __init__(self, anahtar, parent=None):
        super().__init__(parent)
        self.anahtar = anahtar
        self.setWindowTitle('Kurtarma anahtarı')
        self.setMinimumWidth(640)
        d = QVBoxLayout(self)
        d.setContentsMargins(30, 26, 30, 24)
        d.setSpacing(12)
        ust = QHBoxLayout()
        ik = QLabel()
        ik.setPixmap(pixmap('anahtar', T.TURUNCU, 26))
        ust.addWidget(ik)
        ust.addWidget(etiket('Kurtarma anahtarınız', 'SayfaBaslik'), 1)
        d.addLayout(ust)
        d.addWidget(etiket('Parolanızı unutursanız programa yalnız bu anahtarla girebilirsiniz. Yazdırın ya da bir kâğıda yazıp güvenli bir '
                           'yerde (kasa, kilitli dolap) saklayın. Bilgisayarda dosya olarak saklamayın: anahtarı bilen biri bütün verilere '
                           'ulaşabilir. Bu anahtar bir daha gösterilmez; kaybederseniz yönetici Ayarlar\'dan yenisini oluşturabilir.',
                           'SayfaAlt', True))
        a = etiket(anahtar, 'KurtarmaAnahtari')
        a.setAlignment(Qt.AlignCenter)
        a.setTextInteractionFlags(Qt.TextSelectableByMouse)
        d.addWidget(a)
        yaz = dugme('Yazdır', 'yazdir')
        yaz.clicked.connect(self._yazdir)
        kop = dugme('Kopyala', 'kopyala')
        kop.clicked.connect(lambda: (QGuiApplication.clipboard().setText(anahtar), kop.setText('Kopyalandı')))
        d.addLayout(yatay(yaz, kop, None))
        self.onay = QCheckBox('Kurtarma anahtarını güvenli bir yere yazdım / sakladım')
        d.addWidget(self.onay)
        self.devam = dugme('Devam', None, 'Birincil')
        self.devam.setEnabled(False)
        self.devam.clicked.connect(self.accept)
        self.onay.toggled.connect(self.devam.setEnabled)
        d.addLayout(yatay(None, self.devam))

    def _yazdir(self):
        from .. import raporlar
        raporlar.yazdir(kurtarma_html(self.anahtar), self)

    def reject(self):
        if self.onay.isChecked():
            super().reject()


def kurtarma_html(anahtar):
    return (f'<html><body style="font-family: Inter, sans-serif"><img src="logo" width="215" height="43"><h2>{html.escape(UYGULAMA_ADI)}</h2>'
            f'<p>Kurtarma anahtarı ({datetime.datetime.now():%d.%m.%Y %H:%M}):</p>'
            f'<p style="font-size:20pt; font-family: Consolas, monospace"><b>{html.escape(anahtar)}</b></p>'
            f'<p>Parola unutulursa programa bu anahtarla girilir (Giriş › Parolamı unuttum). Güvenli bir yerde saklayın; anahtarı bilen '
            f'biri bütün verilere ulaşabilir. Yeni anahtar oluşturulursa bu anahtar geçersiz olur.</p></body></html>')


# ----------------------------------------------------------------------------- parola ve hesap pencereleri
class _Form(QDialog):
    def __init__(self, baslik, aciklama, parent=None):
        super().__init__(parent)
        self.setWindowTitle(baslik)
        self.setMinimumWidth(480)
        self.d = QVBoxLayout(self)
        self.d.setContentsMargins(28, 24, 28, 22)
        self.d.setSpacing(8)
        self.d.addWidget(etiket(baslik, 'SayfaBaslik'))
        if aciklama:
            self.d.addWidget(etiket(aciklama, 'SayfaAlt', True))
        self.d.addSpacing(8)
        self.mesaj = etiket('', 'GirisMesaj', True)
        self.mesaj.hide()

    def alan(self, metin, w):
        self.d.addWidget(etiket(metin, 'AlanEtiket'))
        self.d.addWidget(w)
        return w

    def dugmeler(self, metin, f):
        self.d.addWidget(self.mesaj)
        self.d.addSpacing(6)
        tamam = dugme(metin, None, 'Birincil')
        tamam.setDefault(True)
        tamam.clicked.connect(f)
        vazgec = dugme('Vazgeç', tur='Duz')
        vazgec.clicked.connect(self.reject)
        self.d.addLayout(yatay(None, vazgec, tamam))

    def hata_goster(self, metin):
        self.mesaj.setText(metin)
        self.mesaj.setVisible(bool(metin))


class ParolaDegistirPenceresi(_Form):
    """Oturumdaki kullanıcının parolası. zorunlu_eski verilirse (yönetici sıfırlamış) mevcut parola sorulmaz."""

    def __init__(self, db, zorunlu_eski=None, parent=None):
        super().__init__('Parolanızı değiştirin' if zorunlu_eski is not None else 'Parolamı değiştir',
                         'Parolanız yönetici tarafından belirlendi; devam etmek için yalnız sizin bildiğiniz yeni bir parola yazın.'
                         if zorunlu_eski is not None else 'En az 8 karakter; harf ve rakam içersin.', parent)
        self.db, self.zorunlu_eski = db, zorunlu_eski
        self.eski = None if zorunlu_eski is not None else self.alan('Mevcut parola', ParolaKutusu())
        self.yeni = self.alan('Yeni parola', ParolaKutusu())
        self.tekrar = self.alan('Yeni parola (tekrar)', ParolaKutusu())
        self.dugmeler('Parolayı değiştir', self._tamam)

    def _tamam(self):
        try:
            if self.yeni.text() != self.tekrar.text():
                raise VeriHatasi('Yeni parola ile tekrarı aynı değil.')
            eski = self.zorunlu_eski if self.zorunlu_eski is not None else self.eski.text()
            _bekle_imleci(lambda: self.db.parola_degistir(eski, self.yeni.text()))
        except VeriHatasi as e:
            self.hata_goster(str(e))
            return
        self.accept()


class KullaniciPenceresi(_Form):
    """Yönetici: yeni kullanıcı (geçici parolayla) ya da ad / rol düzenleme."""

    def __init__(self, db, hesap=None, parent=None):
        super().__init__('Kullanıcıyı düzenle' if hesap else 'Yeni kullanıcı',
                         None if hesap else 'Kullanıcı ilk girişte bu geçici parolayı kendi parolasıyla değiştirir.', parent)
        self.db, self.hesap = db, hesap
        self.ad_soyad = self.alan('Ad Soyad', _kutu('İzin kayıtlarına "Giren" olarak yazılır'))
        self.kullanici = self.alan('Kullanıcı adı', _kutu('ör. sukru.kurgu'))
        self.rol = QComboBox()
        for k, v in ROLLER.items():
            self.rol.addItem(v, k)
        self.alan('Rol', self.rol)
        self.d.addWidget(etiket('Yönetici: kullanıcıları yönetir, yedekten geri döner, güvenlik ayarlarını değiştirir. Kullanıcı: personel ve '
                                'izin işlemlerinin hepsini yapar.', 'SolukKucuk', True))
        if hesap:
            self.ad_soyad.setText(hesap['ad_soyad'])
            self.kullanici.setText(hesap['kullanici_adi'])
            self.kullanici.setEnabled(False)
            self.rol.setCurrentIndex(self.rol.findData(hesap['rol']))
            self.parola = self.tekrar = None
        else:
            self.rol.setCurrentIndex(self.rol.findData('kullanici'))
            self.parola = self.alan('Geçici parola', ParolaKutusu('en az 8 karakter; harf ve rakam'))
            self.tekrar = self.alan('Geçici parola (tekrar)', ParolaKutusu())
        self.dugmeler('Kaydet', self._tamam)

    def _tamam(self):
        try:
            if self.hesap:
                self.db.kullanici_duzenle(self.hesap['id'], self.ad_soyad.text(), self.rol.currentData())
            else:
                if self.parola.text() != self.tekrar.text():
                    raise VeriHatasi('Geçici parola ile tekrarı aynı değil.')
                _bekle_imleci(lambda: self.db.kullanici_ekle(self.kullanici.text(), self.ad_soyad.text(), self.rol.currentData(),
                                                             self.parola.text()))
        except VeriHatasi as e:
            self.hata_goster(str(e))
            return
        self.accept()


class ParolaSifirlaPenceresi(_Form):
    def __init__(self, db, hesap, parent=None):
        super().__init__('Parolayı sıfırla', f'{hesap["ad_soyad"]} ({hesap["kullanici_adi"]}) için geçici bir parola yazın; kullanıcı ilk '
                         'girişte kendi parolasını belirler.', parent)
        self.db, self.hesap = db, hesap
        self.parola = self.alan('Geçici parola', ParolaKutusu('en az 8 karakter; harf ve rakam'))
        self.tekrar = self.alan('Geçici parola (tekrar)', ParolaKutusu())
        self.dugmeler('Parolayı sıfırla', self._tamam)

    def _tamam(self):
        try:
            if self.parola.text() != self.tekrar.text():
                raise VeriHatasi('Geçici parola ile tekrarı aynı değil.')
            _bekle_imleci(lambda: self.db.parola_sifirla(self.hesap['id'], self.parola.text()))
        except VeriHatasi as e:
            self.hata_goster(str(e))
            return
        self.accept()


class YedekAnahtariPenceresi(_Form):
    """Başka bir kurulumda alınmış yedek için o yedeğin kullanıcı adı + parolası ya da kurtarma anahtarı."""

    def __init__(self, parent=None):
        super().__init__('Yedeğin anahtarı', 'Bu yedek başka bir veri dosyasıyla (başka bir kurulumda) alınmış. O kurulumdaki kullanıcı adı '
                         've parolayı ya da o kurulumun kurtarma anahtarını yazın.', parent)
        self.kullanici = self.alan('Kullanıcı adı', _kutu())
        self.parola = self.alan('Parola', ParolaKutusu())
        self.anahtar = self.alan('ya da kurtarma anahtarı', _kutu('XXXX-XXXX-…'))
        self.dugmeler('Devam', self._tamam)
        self.sonuc = None

    def _tamam(self):
        if self.anahtar.text().strip():
            self.sonuc = {'kurtarma': self.anahtar.text()}
        elif self.kullanici.text().strip() and self.parola.text():
            self.sonuc = {'kullanici_adi': self.kullanici.text(), 'parola': self.parola.text()}
        else:
            self.hata_goster('Kullanıcı adı ve parola ya da kurtarma anahtarı yazın.')
            return
        self.accept()


# ----------------------------------------------------------------------------- açılış akışı
def baslangic(parent=None):
    """Veri dosyası varsa giriş; yoksa yeni yönetici hesabı.
    Dönüş: (db, girişte yazılan parola) ya da (None, None) — vazgeçildi."""
    yol = yollar.veritabani_yolu()
    sayac = guvenlik.GirisSayaci(yollar.giris_sayaci_yolu())
    if os.path.exists(yol):
        g = GirisPenceresi(yol, sayac, parent=parent)
        if not g.exec():
            return None, None
        return g.sonuc, g.parola_metni
    h = HesapOlusturPenceresi(yol, parent)
    if not h.exec():
        return None, None
    KurtarmaAnahtariPenceresi(h.kurtarma, parent).exec()
    return h.sonuc, None
