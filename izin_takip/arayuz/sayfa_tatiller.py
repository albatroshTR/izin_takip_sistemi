# -*- coding: utf-8 -*-
"""Resmi tatiller: liste, ekleme / düzenleme, gelecek yılın sabit tarihli tatillerini ekleme."""
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QDialog, QFormLayout, QHBoxLayout, QLineEdit, QVBoxLayout

from . import tema as T
from .bilesenler import ListeModeli, RozetDelegate, Sutun, TarihKutusu, dugme, etiket, hata, secili_satir, soru, tablo, tablo_karti
from .sayfa import Sayfa
from ..veritabani import VeriHatasi
from ..yardimci import GUN_ADLARI, tarih_yaz

SABIT = [((1, 1), 'Yılbaşı', 'tam'), ((4, 23), 'Ulusal Egemenlik ve Çocuk Bayramı', 'tam'), ((5, 1), 'Emek ve Dayanışma Günü', 'tam'),
         ((5, 19), "Atatürk'ü Anma, Gençlik ve Spor Bayramı", 'tam'), ((7, 15), 'Demokrasi ve Millî Birlik Günü', 'tam'),
         ((8, 30), 'Zafer Bayramı', 'tam'), ((10, 28), 'Cumhuriyet Bayramı arifesi (13:00 sonrası)', 'yarim'),
         ((10, 29), 'Cumhuriyet Bayramı', 'tam')]


class TatilDialog(QDialog):
    def __init__(self, baglam, tatil=None, parent=None):
        super().__init__(parent)
        self.b = baglam
        self.t = tatil
        self.setWindowTitle('Tatili düzenle' if tatil else 'Tatil ekle')
        self.setMinimumWidth(480)
        d = QVBoxLayout(self)
        d.setContentsMargins(24, 20, 24, 18)
        d.setSpacing(12)
        d.addWidget(etiket('Tatili düzenle' if tatil else 'Tatil ekle', 'SayfaBaslik'))
        f = QFormLayout()
        f.setVerticalSpacing(10)
        self.tarih = TarihKutusu(bos_olabilir=False)
        self.ad = QLineEdit()
        self.ad.setPlaceholderText('ör. Ramazan Bayramı 1. gün')
        self.tur = QComboBox()
        self.tur.addItem('Tam gün (izinden düşülmez)', 'tam')
        self.tur.addItem('Yarım gün — arife, 28 Ekim (yarım gün düşülür)', 'yarim')
        f.addRow('Tarih', self.tarih)
        f.addRow('Tatil adı', self.ad)
        f.addRow('Tür', self.tur)
        d.addLayout(f)
        if tatil:
            self.tarih.setTarih(tatil['tarih'])
            self.ad.setText(tatil['ad'] or '')
            self.tur.setCurrentIndex(self.tur.findData(tatil['tur']))
        alt = QHBoxLayout()
        alt.addStretch(1)
        v = dugme('Vazgeç')
        v.clicked.connect(self.reject)
        k = dugme('Kaydet', 'onay', 'Vurgu')
        k.clicked.connect(self._kaydet)
        alt.addWidget(v)
        alt.addWidget(k)
        d.addLayout(alt)

    def _kaydet(self):
        try:
            self.b.db.tatil_kaydet({'tarih': self.tarih.tarih(), 'ad': self.ad.text().strip(), 'tur': self.tur.currentData()},
                                   self.t['id'] if self.t else None)
        except (VeriHatasi, ValueError) as e:
            hata(self, str(e) if isinstance(e, VeriHatasi) else 'Tarih anlaşılamadı (gün.ay.yıl).')
            return
        self.accept()


class TatillerSayfa(Sayfa):
    baslik = 'Resmi Tatiller'
    alt_baslik = 'Pazar ve resmi tatiller yıllık izinden düşülmez; arife ve 28 Ekim yarım gün düşülür. Her yıl gelecek yılın tatillerini ekleyin.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        self.sabit = dugme('', 'takvim', ipucu='Yılbaşı, 23 Nisan, 1 Mayıs, 19 Mayıs, 15 Temmuz, 30 Ağustos, 28–29 Ekim')
        self.sabit.clicked.connect(self._sabit_ekle)
        sil = dugme('Sil', 'sil', 'Tehlike')
        sil.clicked.connect(self._sil)
        ekle = dugme('Tatil ekle', 'arti', 'Vurgu')
        ekle.clicked.connect(lambda: self._duzenle(None))
        for w in (self.sabit, sil, ekle):
            self.ust.ekle(w)
        ust = QHBoxLayout()
        self.yil = QComboBox()
        self.yil.currentIndexChanged.connect(self._filtre)
        ust.addWidget(etiket('Yıl:', 'Soluk'))
        ust.addWidget(self.yil)
        ust.addStretch(1)
        self.duzen.addLayout(ust)
        self.model = ListeModeli([
            Sutun('Tarih', lambda t: tarih_yaz(t['tarih']), sirala=lambda t: t['tarih'], genislik=120, hiza='orta', kalin=True),
            Sutun('Gün', lambda t: GUN_ADLARI[t['tarih'].weekday()], genislik=120,
                  renk=lambda t: T.SOLUK_2 if t['tarih'].weekday() == 6 else None),
            Sutun('Tatil', lambda t: t['ad'] or '', genislik=420),
            Sutun('Tür', lambda t: 'Tam gün' if t['tur'] == 'tam' else 'Yarım gün', tur='rozet'),
        ])
        self.tv, self.proxy = tablo(self.model)
        self.tv.setItemDelegateForColumn(3, RozetDelegate(lambda m, r: ('#FDE7D8', '#B4501A') if m == 'Tam gün' else ('#FEF3EA', '#C0763F'),
                                                          parent=self.tv))
        self.tv.doubleClicked.connect(lambda idx: self._duzenle(idx.data(Qt.UserRole + 1)))
        self.duzen.addWidget(tablo_karti(self.tv), 1)
        self.duzen.addWidget(etiket('Ramazan ve Kurban Bayramı tarihleri her yıl değişir: Diyanet\'in "Dini Günler" takviminden ekleyin '
                                    '(arife yarım gün, bayram günleri tam gün). Pazara denk gelen tatil zaten düşülmez.', 'SolukKucuk', True))

    def _duzenle(self, t):
        if TatilDialog(self.b, t, self.window()).exec():
            self.b.yenile('Tatil kaydedildi')

    def _sil(self):
        t = secili_satir(self.tv)
        if not t:
            return
        if soru(self, 'Tatili sil', f'{tarih_yaz(t["tarih"])} {t["ad"]} silinsin mi?', 'Sil', tehlikeli=True):
            self.b.db.tatil_sil(t['id'])
            self.b.yenile('Tatil silindi')

    def _sabit_yili(self):
        yillar = {t['tarih'].year for t in self.b.veri['tatiller']}
        return (max(yillar) + 1) if yillar else datetime.date.today().year

    def _sabit_ekle(self):
        y = self._sabit_yili()
        if not soru(self, 'Sabit tatilleri ekle', f'{y} yılının sabit tarihli tatilleri eklensin mi?\n\n'
                                                  + '\n'.join(f'• {d:02d}.{a:02d}.{y}  {ad}' for (a, d), ad, _ in SABIT) +
                    '\n\nRamazan ve Kurban Bayramı günlerini ayrıca elle ekleyin.', 'Ekle'):
            return
        n = 0
        for (a, d), ad, tur in SABIT:
            try:
                self.b.db.tatil_kaydet({'tarih': datetime.date(y, a, d), 'ad': ad, 'tur': tur})
                n += 1
            except VeriHatasi:
                pass
        self.b.yenile(f'{y} yılı için {n} tatil eklendi')

    def _filtre(self):
        y = self.yil.currentData()
        self.proxy.filtre_ayarla(lambda t: y is None or t['tarih'].year == y)

    def yenile(self):
        tatiller = self.b.veri['tatiller']
        self.model.doldur(tatiller)
        yillar = sorted({t['tarih'].year for t in tatiller})
        secili = self.yil.currentData() if self.yil.count() else datetime.date.today().year
        self.yil.blockSignals(True)
        self.yil.clear()
        self.yil.addItem('Tüm yıllar', None)
        for y in yillar:
            self.yil.addItem(str(y), y)
        i = self.yil.findData(secili)
        self.yil.setCurrentIndex(i if i >= 0 else 0)
        self.yil.blockSignals(False)
        self.sabit.setText(f'{self._sabit_yili()} sabit tatillerini ekle')
        self._filtre()
