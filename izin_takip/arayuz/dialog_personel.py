# -*- coding: utf-8 -*-
"""Personel ekleme / düzenleme penceresi (çalışma dönemleri, doğum tarihi, elle düzeltme, notlar)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QLabel,
                               QLineEdit, QPlainTextEdit, QPushButton, QTabWidget, QVBoxLayout, QWidget)

from . import tema as T
from .bilesenler import TarihKutusu, dugme, etiket, hata, soru
from ..veritabani import VeriHatasi
from ..yardimci import TEYIT_SECENEK, tr_buyuk


class DonemSatiri(QWidget):
    def __init__(self, sira, giris=None, cikis=None, sil=None, parent=None):
        super().__init__(parent)
        d = QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(10)
        self.no = etiket(f'{sira}. dönem', 'Soluk')
        self.no.setFixedWidth(70)
        d.addWidget(self.no)
        self.giris = TarihKutusu(bos_olabilir=False, ipucu='İşe giriş')
        self.cikis = TarihKutusu(ipucu='Çıkış (boş: çalışıyor)')
        self.giris.setMinimumWidth(170)
        self.cikis.setMinimumWidth(190)
        self.cikis.setMaximumWidth(200)
        self.giris.setTarih(giris)
        self.cikis.setTarih(cikis)
        d.addWidget(self.giris)
        d.addWidget(etiket('→', 'Soluk'))
        d.addWidget(self.cikis)
        self.sil = dugme('', 'kapat', 'Duz', 'Bu dönemi kaldır')
        if sil:
            self.sil.clicked.connect(lambda: sil(self))
        d.addWidget(self.sil)
        d.addStretch(1)


class PersonelDialog(QDialog):
    def __init__(self, baglam, personel_id=None, parent=None):
        super().__init__(parent)
        self.b = baglam
        self.pid = personel_id
        p = baglam.personel(personel_id) if personel_id else None
        self.setWindowTitle('Personeli düzenle' if p else 'Yeni personel')
        self.setMinimumWidth(720)
        ana = QVBoxLayout(self)
        ana.setContentsMargins(26, 22, 26, 20)
        ana.setSpacing(14)
        ana.addWidget(etiket(p['ad'] if p else 'Yeni personel', 'SayfaBaslik'))
        ana.addWidget(etiket('Yıldızlı (*) alanlar zorunludur. Kalan izin, hak tarihleri ve kıdem bu bilgilerden kendiliğinden hesaplanır.',
                             'SayfaAlt', True))
        sek = QTabWidget()
        ana.addWidget(sek, 1)

        # ---------------- genel
        g = QWidget()
        gd = QVBoxLayout(g)
        gd.setContentsMargins(2, 14, 2, 2)
        gd.setSpacing(10)
        f = QFormLayout()
        f.setLabelAlignment(Qt.AlignLeft)
        f.setHorizontalSpacing(18)
        f.setVerticalSpacing(10)
        self.ad = QLineEdit()
        self.ad.setPlaceholderText('ör. AYŞE ÖRNEK')
        f.addRow('Ad Soyad *', self.ad)
        self.dogum = TarihKutusu()
        f.addRow('Doğum tarihi', self.dogum)
        dn = etiket('50 yaş ve üstüne (ya da 18 yaş ve altına) en az 20 gün izin verilir; doğum tarihini mutlaka yazın.', 'SolukKucuk', True)
        f.addRow('', dn)
        self.teyit = QComboBox()
        self.teyit.addItems([''] + TEYIT_SECENEK)
        self.teyit.setMinimumWidth(260)
        f.addRow('Teyit durumu', self.teyit)
        gd.addLayout(f)
        gd.addSpacing(4)
        gd.addWidget(etiket('Çalışma dönemleri *', 'BolumBaslik'))
        gd.addWidget(etiket('İşten çıkınca "Çıkış" tarihini yazın (kişi "Ayrıldı" olur, ödenecek izin ücreti Ayrılanlar sayfasında görünür). '
                            'Yeniden işe girerse yeni dönem ekleyin: önceki hizmet kıdeme eklenir.', 'SolukKucuk', True))
        self.donem_kutu = QVBoxLayout()
        self.donem_kutu.setSpacing(8)
        gd.addLayout(self.donem_kutu)
        ekle = dugme('Dönem ekle (yeniden işe giriş)', 'arti', 'Duz')
        ekle.clicked.connect(lambda: self._donem_ekle())
        gd.addWidget(ekle, 0, Qt.AlignLeft)
        gd.addStretch(1)
        sek.addTab(g, 'Genel bilgiler')

        # ---------------- ek
        e = QWidget()
        ed = QVBoxLayout(e)
        ed.setContentsMargins(2, 14, 2, 2)
        ed.setSpacing(10)
        f2 = QFormLayout()
        f2.setHorizontalSpacing(18)
        f2.setVerticalSpacing(10)
        self.duz = QDoubleSpinBox()
        self.duz.setRange(-400, 400)
        self.duz.setDecimals(1)
        self.duz.setSingleStep(0.5)
        self.duz.setSuffix(' gün')
        self.duz.setMaximumWidth(140)
        f2.addRow('Elle düzeltme', self.duz)
        f2.addRow('', etiket('Kalana eklenir (+) ya da düşülür (−). Ör. önceki çalışma döneminden çıkışta parası ödenmeyen kalan (+), '
                             '2022 öncesi kullanılmış sayılan izin (−).', 'SolukKucuk', True))
        self.duz_ack = QLineEdit()
        self.duz_ack.setPlaceholderText('Düzeltmenin gerekçesi')
        f2.addRow('Düzeltme açıklaması', self.duz_ack)
        self.yas50 = TarihKutusu()
        f2.addRow('50 yaş beyanı', self.yas50)
        f2.addRow('', etiket('Yalnız doğum tarihi bilinmiyorsa: kişinin 50 yaşında olduğu kesin olan ilk tarih. O tarihten sonra kazanılan izin '
                             'en az 20 gün olur. Doğum tarihi yazılınca dikkate alınmaz.', 'SolukKucuk', True))
        self.onceki = QLineEdit()
        self.onceki.setPlaceholderText('Eski kayıtlarda geçen farklı yazım (ör. AYSE ORNEK)')
        f2.addRow('Önceki ad / diğer yazım', self.onceki)
        self.ozet = QLineEdit()
        self.ozet.setPlaceholderText('Listelerde görünen kısa not')
        f2.addRow('Not özeti', self.ozet)
        ed.addLayout(f2)
        ed.addWidget(etiket('Açıklamalar ve açık sorular (İzin Kartı\'nda görünür)', 'Soluk'))
        self.not_metni = QPlainTextEdit()
        self.not_metni.setMinimumHeight(150)
        ed.addWidget(self.not_metni, 1)
        sek.addTab(e, 'Ek bilgiler ve notlar')

        # ---------------- düğmeler
        alt = QHBoxLayout()
        if p:
            sil = dugme('Personeli sil', 'sil', 'Tehlike', 'Yalnız izin kaydı olmayan (yanlışlıkla eklenmiş) kişi silinebilir.')
            sil.clicked.connect(self._sil)
            alt.addWidget(sil)
        alt.addStretch(1)
        v = dugme('Vazgeç')
        v.clicked.connect(self.reject)
        k = dugme('Kaydet', 'onay', 'Vurgu')
        k.setDefault(True)
        k.clicked.connect(self._kaydet)
        alt.addWidget(v)
        alt.addWidget(k)
        ana.addLayout(alt)

        self.satirlar = []
        if p:
            self.ad.setText(p['ad'])
            self.dogum.setTarih(p['dogum'])
            self.teyit.setCurrentText(p.get('teyit') or '')
            for gi, ci in p['donemler']:
                self._donem_ekle(gi, ci)
            self.duz.setValue(float(p.get('elle_duzeltme') or 0))
            self.duz_ack.setText(p.get('duzeltme_aciklama') or '')
            self.yas50.setTarih(p.get('yas50'))
            self.onceki.setText(p.get('onceki_ad') or '')
            self.ozet.setText(p.get('not_ozet') or '')
            self.not_metni.setPlainText(p.get('not_metni') or '')
        else:
            self.teyit.setCurrentText('Teyitli')
        if not self.satirlar:
            self._donem_ekle()
        self.sonuc_kodu = None

    def _donem_ekle(self, g=None, c=None):
        s = DonemSatiri(len(self.satirlar) + 1, g, c, self._donem_sil)
        self.satirlar.append(s)
        self.donem_kutu.addWidget(s)
        self._numarala()

    def _donem_sil(self, s):
        if len(self.satirlar) == 1:
            return
        self.satirlar.remove(s)
        s.setParent(None)
        s.deleteLater()
        self._numarala()

    def _numarala(self):
        for i, s in enumerate(self.satirlar):
            s.no.setText(f'{i + 1}. dönem')
            s.sil.setVisible(len(self.satirlar) > 1)

    def _kaydet(self):
        try:
            donemler = []
            for i, s in enumerate(self.satirlar):
                g, c = s.giris.tarih(), s.cikis.tarih()
                if g is None and c is None:
                    continue
                if g is None:
                    raise VeriHatasi(f'{i + 1}. dönemin giriş tarihini yazın.')
                donemler.append((g, c))
            p = {'ad': tr_buyuk(' '.join(self.ad.text().split())),
                 'dogum': self.dogum.tarih(), 'yas50': self.yas50.tarih(), 'donemler': donemler,
                 'elle_duzeltme': self.duz.value() or None, 'duzeltme_aciklama': self.duz_ack.text().strip(),
                 'teyit': self.teyit.currentText(), 'onceki_ad': self.onceki.text().strip(), 'not_ozet': self.ozet.text().strip(),
                 'not_metni': self.not_metni.toPlainText().strip()}
            if p['elle_duzeltme'] and not p['duzeltme_aciklama']:
                raise VeriHatasi('Elle düzeltme için kısa bir açıklama yazın (neden eklendi/düşüldü).')
            self.pid = self.b.db.personel_kaydet(p, self.pid)
        except ValueError as e:
            if isinstance(e, VeriHatasi):
                hata(self, str(e))
            else:
                hata(self, 'Tarih anlaşılamadı. Gün.ay.yıl biçiminde yazın (ör. 15.03.1990) ya da takvimden seçin.')
            return
        self.sonuc_kodu = 'kaydedildi'
        self.accept()

    def _sil(self):
        if not soru(self, 'Personeli sil', f'{self.ad.text()} silinsin mi?', 'Sil', tehlikeli=True):
            return
        try:
            self.b.db.personel_sil(self.pid)
        except VeriHatasi as e:
            hata(self, str(e), 'Silinemedi')
            return
        self.sonuc_kodu = 'silindi'
        self.accept()


def personel_penceresi(baglam, parent, personel_id=None):
    d = PersonelDialog(baglam, personel_id, parent)
    if d.exec() and d.sonuc_kodu:
        baglam.yenile('Personel kaydedildi' if d.sonuc_kodu == 'kaydedildi' else 'Personel silindi')
        return d.pid if d.sonuc_kodu == 'kaydedildi' else None
    return None
