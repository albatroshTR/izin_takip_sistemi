# -*- coding: utf-8 -*-
"""İlk açılış (veritabanı boş): örnek veriyle başla ya da boş başla. Her iki durumda da resmî tatil listesi yüklenir."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QVBoxLayout

from .bilesenler import bilgi, dugme, etiket, hata
from .. import UYGULAMA_ADI, ornek_veri, yollar
from ..veritabani import VeriHatasi


def ornek_yukle(baglam, parent):
    """Uydurma örnek veriyi (kişiler, izinler, resmî tatiller) boş veritabanına yükler."""
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
        v = ornek_veri.uret()
        baglam.db.veri_yukle(v, 'örnek veri')
        baglam.hesapla()
    except (VeriHatasi, ValueError, KeyError, OSError) as e:
        QApplication.restoreOverrideCursor()
        hata(parent, f'Örnek veri yüklenemedi:\n\n{e}', 'Örnek veri')
        return False
    finally:
        if QApplication.overrideCursor():
            QApplication.restoreOverrideCursor()
    baglam.yenile()
    bilgi(parent, f'<b>{len(v["personel"])} uydurma personel, {len(v["izinler"])} izin kaydı, {len(v["tatiller"])} resmî tatil</b> yüklendi.<br><br>'
                  'Bunlar yalnız programı denemek içindir. Gerçek verinize geçmeye hazır olunca Personel sayfasından kişileri silip '
                  '(izin kaydı olanların önce izinlerini silin) ya da yeni bir veri klasörüyle (--veri) temiz başlayın.', 'Örnek veri yüklendi')
    return True


def bos_baslat(baglam, parent):
    """Yalnız resmî tatilleri yükler; personeli ve izinleri kullanıcı girer."""
    try:
        baglam.db.veri_yukle({'personel': [], 'izinler': [], 'tatiller': ornek_veri.resmi_tatiller()}, 'resmî tatiller')
    except (VeriHatasi, OSError) as e:
        hata(parent, f'Resmî tatiller yüklenemedi:\n\n{e}', 'Boş başla')
        return False
    baglam.db.ayar_yaz('bos_baslangic', '1', gunluk=False)
    baglam.yenile()
    return True


class IlkAcilis(QDialog):
    def __init__(self, baglam, parent=None):
        super().__init__(parent)
        self.b = baglam
        self.setWindowTitle(f'{UYGULAMA_ADI} — hoş geldiniz')
        self.setMinimumWidth(620)
        d = QVBoxLayout(self)
        d.setContentsMargins(40, 34, 40, 30)
        d.setSpacing(14)
        logo = QLabel()
        px = QPixmap(yollar.kaynak('logo.png'))
        if not px.isNull():
            px.setDevicePixelRatio(2.0)
            logo.setPixmap(px.scaledToWidth(560, Qt.SmoothTransformation))
        d.addWidget(logo, 0, Qt.AlignLeft)
        d.addSpacing(8)
        d.addWidget(etiket('İzin takibine hoş geldiniz', 'SayfaBaslik'))
        d.addWidget(etiket('Programı denemek için uydurma örnek veriyle başlayabilir ya da boş başlayıp personelinizi kendiniz girebilirsiniz. '
                           'İki durumda da 2019–2030 resmî tatil listesi yüklenir.', 'SayfaAlt', True))
        d.addWidget(etiket(f'Veriler şu klasörde şifreli saklanır: {yollar.veri_klasoru()}', 'SolukKucuk', True))
        d.addSpacing(10)
        ornek = dugme('Örnek veriyle başla (denemek için)', 'yukle', 'Vurgu')
        ornek.setMinimumHeight(44)
        ornek.clicked.connect(self._ornek)
        d.addWidget(ornek)
        bos = dugme('Boş başla (personeli elle gireceğim)', tur='Duz')
        bos.clicked.connect(self._bos)
        d.addWidget(bos, 0, Qt.AlignCenter)

    def _ornek(self):
        if ornek_yukle(self.b, self):
            self.accept()

    def _bos(self):
        if bos_baslat(self.b, self):
            self.accept()
