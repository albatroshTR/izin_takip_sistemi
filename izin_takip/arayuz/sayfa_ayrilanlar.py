# -*- coding: utf-8 -*-
"""Ayrılanlar: işten ayrılanların çıkışta ödenmesi gereken izin ücreti (4857 md.59) ve ödeme takibi."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLineEdit, QStackedWidget,
                               QVBoxLayout, QWidget)

from . import tema as T
from .bilesenler import (BosDurum, ListeModeli, RozetDelegate, Sutun, TarihKutusu, dugme, durum_renk, etiket, hata, secili_satir,
                         tablo, tablo_karti)
from .sayfa import Sayfa
from ..motor import H
from ..yardimci import para_yaz, sayi_yaz, tarih_yaz, tr_anahtar


def odeme_satiri(ks, o, bugun):
    """Ayrılan için ödeme hesabı ."""
    o = o or {}
    gun = ks['odenecek'] or 0
    ucret = o.get('ucret')
    tutar = round(gun * ucret / 30, 2) if ucret else None
    odendi = o.get('odendi') or ('—' if gun <= 0 else 'Bilinmiyor')
    borc = None
    if tutar is not None:
        borc = 0.0 if odendi == 'Ödendi' else max(0.0, round(tutar - (o.get('odenen') or 0), 2))
    son_cikis = ks['son_cikis']
    zaman = H.yil_ekle(son_cikis, 5) if son_cikis else None
    uy = []
    if (ks['kalan'] or 0) < 0:
        uy.append(f'Son dönemde {sayi_yaz(-ks["kalan"])} gün hak edilmeden kullanılmış (avans; ücreti geri istenemez)')
    if gun > 0 and odendi != 'Ödendi' and not ucret:
        uy.append('Tutar için son brüt aylık ücreti yazın')
    if odendi == 'Ödendi' and not o.get('odenen'):
        uy.append('Ödendi: ödeme tarihi ve tutarını yazın')
    if zaman:
        if zaman < bugun:
            uy.append('Zamanaşımı doldu')
        elif gun > 0 and odendi != 'Ödendi' and (zaman - bugun).days <= 365:
            uy.append('Zamanaşımına 1 yıldan az kaldı')
    return {'gun': gun, 'ucret': ucret, 'tutar': tutar, 'odendi': odendi, 'odeme_tarihi': o.get('odeme_tarihi'), 'odenen': o.get('odenen'),
            'borc': borc, 'zaman': zaman, 'uyari': uy, 'aciklama': o.get('aciklama')}


class OdemeDialog(QDialog):
    def __init__(self, baglam, satir, parent=None):
        super().__init__(parent)
        self.b = baglam
        self.s = satir
        self.setWindowTitle('İzin ücreti')
        self.setMinimumWidth(520)
        d = QVBoxLayout(self)
        d.setContentsMargins(24, 20, 24, 18)
        d.setSpacing(12)
        d.addWidget(etiket(satir['ad'], 'SayfaBaslik'))
        d.addWidget(etiket(f'Ödenmesi gereken: {sayi_yaz(satir["gun"])} gün · çıkış {tarih_yaz(satir["son_cikis"])} · '
                           f'zamanaşımı {tarih_yaz(satir["zaman"])}', 'SayfaAlt', True))
        f = QFormLayout()
        f.setVerticalSpacing(10)
        f.setHorizontalSpacing(16)
        self.ucret = QDoubleSpinBox()
        self.ucret.setRange(0, 10 ** 7)
        self.ucret.setDecimals(2)
        self.ucret.setGroupSeparatorShown(True)
        self.ucret.setSuffix(' TL')
        self.ucret.setValue(satir['ucret'] or 0)
        f.addRow('Son brüt aylık ücret', self.ucret)
        self.tutar = etiket('')
        self.tutar.setStyleSheet('font-weight: 700;')
        f.addRow('Tutar (gün × ücret ÷ 30)', self.tutar)
        self.durum = QComboBox()
        self.durum.addItems(['Bilinmiyor', 'Ödenmedi', 'Ödendi'])
        self.durum.setCurrentText(satir['odendi'] if satir['odendi'] in ('Ödenmedi', 'Ödendi') else 'Bilinmiyor')
        f.addRow('Ödendi mi?', self.durum)
        self.tarih = TarihKutusu()
        self.tarih.setTarih(satir['odeme_tarihi'])
        f.addRow('Ödeme tarihi', self.tarih)
        self.odenen = QDoubleSpinBox()
        self.odenen.setRange(0, 10 ** 7)
        self.odenen.setDecimals(2)
        self.odenen.setGroupSeparatorShown(True)
        self.odenen.setSuffix(' TL')
        self.odenen.setValue(satir['odenen'] or 0)
        f.addRow('Ödenen tutar', self.odenen)
        self.ack = QLineEdit(satir.get('aciklama') or '')
        f.addRow('Açıklama', self.ack)
        d.addLayout(f)
        d.addWidget(etiket('4857 sayılı Kanun md.59: iş sözleşmesi sona erince kullanılmayan izin günlerinin ücreti son ücret üzerinden ödenir. '
                           'Zamanaşımı çıkıştan itibaren 5 yıldır.', 'SolukKucuk', True))
        alt = QHBoxLayout()
        alt.addStretch(1)
        v = dugme('Vazgeç')
        v.clicked.connect(self.reject)
        k = dugme('Kaydet', 'onay', 'Vurgu')
        k.clicked.connect(self._kaydet)
        alt.addWidget(v)
        alt.addWidget(k)
        d.addLayout(alt)
        self.ucret.valueChanged.connect(self._tutar)
        self._tutar()

    def _tutar(self):
        u = self.ucret.value()
        self.tutar.setText(para_yaz(round(self.s['gun'] * u / 30, 2)) if u else '—')

    def _kaydet(self):
        if not self.tarih.gecerli():
            hata(self, 'Ödeme tarihi anlaşılamadı (gün.ay.yıl).')
            return
        self.b.db.odeme_kaydet(self.s['id'], {'ucret': self.ucret.value() or None, 'odendi': self.durum.currentText(),
                                              'odeme_tarihi': self.tarih.tarih(), 'odenen': self.odenen.value() or None,
                                              'aciklama': self.ack.text().strip() or None})
        self.accept()


class AyrilanlarSayfa(Sayfa):
    baslik = 'Ayrılanlar'
    alt_baslik = 'İşten ayrılanlara çıkışta ödenmesi gereken izin ücreti (md.59). Ücret ve ödeme bilgisini girmek için çift tıklayın.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        self.ozet = etiket('', 'BilgiKutu', True)
        self.ozet.setContentsMargins(12, 9, 12, 9)
        self.duzen.addWidget(self.ozet)
        self.yigin = QStackedWidget()
        self.duzen.addWidget(self.yigin, 1)
        self.bos = BosDurum('ayrilan', 'Şu anda işten ayrılan personel yok',
                            'Bir çalışan ayrıldığında Personel sayfasında çıkış tarihini yazın; kişi burada listelenir ve '
                            'kullanmadığı izin için ödenmesi gereken gün hesaplanır.')
        self.yigin.addWidget(self.bos)
        self.model = ListeModeli([
            Sutun('Ad Soyad', lambda r: r['ad'], sirala=lambda r: tr_anahtar(r['ad']), genislik=210, kalin=True),
            Sutun('Çalıştığı dönem(ler)', lambda r: r['donem'], genislik=230, renk=lambda r: T.SOLUK),
            Sutun('Hak edilen', lambda r: sayi_yaz(r['hak_top']), genislik=90, hiza='orta'),
            Sutun('Kullanılan', lambda r: sayi_yaz(r['kul_top']), genislik=90, hiza='orta'),
            Sutun('Ödenecek gün', lambda r: sayi_yaz(r['gun']), sirala=lambda r: r['gun'], genislik=110, hiza='orta', kalin=True),
            Sutun('Son brüt ücret', lambda r: para_yaz(r['ucret']), sirala=lambda r: r['ucret'] or 0, genislik=130, hiza='sag'),
            Sutun('Tutar', lambda r: para_yaz(r['tutar']), sirala=lambda r: r['tutar'] or 0, genislik=130, hiza='sag', kalin=True),
            Sutun('Ödendi mi?', lambda r: r['odendi'], genislik=110, tur='rozet'),
            Sutun('Ödeme tarihi', lambda r: tarih_yaz(r['odeme_tarihi']), sirala=lambda r: r['odeme_tarihi'], genislik=110, hiza='orta'),
            Sutun('Kalan borç', lambda r: para_yaz(r['borc']), sirala=lambda r: r['borc'] or 0, genislik=120, hiza='sag',
                  renk=lambda r: T.KIRMIZI if (r['borc'] or 0) > 0 else None),
            Sutun('Zamanaşımı', lambda r: tarih_yaz(r['zaman']), sirala=lambda r: r['zaman'], genislik=110, hiza='orta'),
            Sutun('Uyarı', lambda r: '; '.join(r['uyari']), renk=lambda r: T.KIRMIZI, ipucu=lambda r: '\n'.join(r['uyari'])),
        ])
        self.tv, _ = tablo(self.model)
        self.tv.setItemDelegateForColumn(7, RozetDelegate(durum_renk, ortala=False, parent=self.tv))
        self.tv.doubleClicked.connect(self._duzenle)
        self.yigin.addWidget(tablo_karti(self.tv))

    def _duzenle(self, idx):
        r = idx.data(Qt.UserRole + 1)
        if r and OdemeDialog(self.b, r, self.window()).exec():
            self.b.yenile('İzin ücreti bilgisi kaydedildi')

    def yenile(self):
        satirlar = []
        for ks in self.b.sonuc.ayrilanlar():
            r = odeme_satiri(ks, self.b.veri['odemeler'].get(ks['id']), self.b.bugun)
            r.update({'id': ks['id'], 'ad': ks['ad'], 'hak_top': ks['hak_top'], 'kul_top': ks['kul_top'], 'son_cikis': ks['son_cikis'],
                      'donem': '; '.join(f'{tarih_yaz(g)}–{tarih_yaz(c) if c else "devam"}' for g, c in ks['donemler'])})
            satirlar.append(r)
        self.model.doldur(satirlar)
        self.yigin.setCurrentIndex(1 if satirlar else 0)
        acik = [r for r in satirlar if r['gun'] > 0 and r['odendi'] != 'Ödendi']
        tl = sum(r['borc'] or 0 for r in acik)
        self.ozet.setText(f'Ödenmemiş izin ücreti: {len(acik)} kişi, {sayi_yaz(sum(r["gun"] for r in acik))} gün'
                          + (f', {para_yaz(tl)} (ücreti yazılanlar)' if tl else '')
                          + '. Tutar = gün × son brüt aylık ücret ÷ 30. Zamanaşımı = son çıkış + 5 yıl.')
        self.ozet.setVisible(bool(satirlar))
