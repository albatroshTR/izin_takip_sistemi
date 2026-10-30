# -*- coding: utf-8 -*-
"""İzin Kayıtları: tüm izinler; arama, tür / yıl süzgeci, düzenleme, iptal ve izin formu."""
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QMenu

from . import tema as T
from .bilesenler import (AramaKutusu, ListeModeli, RozetDelegate, Sutun, dugme, etiket, kisa_uyari, secili_satir, tablo, tablo_karti,
                         tur_renk)
from .dialog_izin import izin_penceresi
from .sayfa import Sayfa
from ..yardimci import KOD_AD, KODLAR, ara_eslesir, sayi_yaz, tarih_yaz, tr_anahtar


def _tur_rozet(m, r):
    if r and r.get('iptal'):
        return ('#ECEDF2', '#7A7E92')
    return tur_renk(m)


class IzinlerSayfa(Sayfa):
    baslik = 'İzin Kayıtları'
    alt_baslik = 'Bütün izinler. Düzenlemek için çift tıklayın; vazgeçilen izni silmek yerine iptal edin.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        self.d_form = dugme('İzin formu', 'yazdir', ipucu='Seçili izin için imzalanacak izin talep ve onay formu (PDF / yazdır)')
        self.d_form.clicked.connect(self._form)
        yeni = dugme('Yeni izin', 'arti', 'Vurgu', 'Yeni izin kaydı (Ctrl+N)')
        yeni.clicked.connect(lambda: izin_penceresi(self.b, self.window()))
        self.ust.ekle(self.d_form)
        self.ust.ekle(yeni)

        ust = QHBoxLayout()
        ust.setSpacing(10)
        self.arama = AramaKutusu('Personel, açıklama ya da kayıt no ara…')
        self.arama.setMinimumWidth(320)
        self.arama.textChanged.connect(self._filtre)
        ust.addWidget(self.arama)
        self.tur = QComboBox()
        self.tur.addItem('Tüm izin türleri', None)
        for k in KODLAR:
            self.tur.addItem(KOD_AD[k], k)
        self.tur.currentIndexChanged.connect(self._filtre)
        ust.addWidget(self.tur)
        self.yil = QComboBox()
        self.yil.currentIndexChanged.connect(self._filtre)
        ust.addWidget(self.yil)
        self.uyarili = QCheckBox('Yalnız uyarılı')
        self.uyarili.toggled.connect(self._filtre)
        ust.addWidget(self.uyarili)
        self.iptaller = QCheckBox('İptal edilenler')
        self.iptaller.setChecked(True)
        self.iptaller.toggled.connect(self._filtre)
        ust.addWidget(self.iptaller)
        ust.addStretch(1)
        self.duzen.addLayout(ust)

        self.model = ListeModeli([
            Sutun('No', lambda r: r['no'], genislik=64, hiza='orta'),
            Sutun('Personel', lambda r: r['ad'], sirala=lambda r: tr_anahtar(r['ad']), genislik=196, kalin=True),
            Sutun('İzin türü', lambda r: KOD_AD[r['tur']] if not r['iptal'] else f'{KOD_AD[r["tur"]]} (iptal)', genislik=150, tur='rozet'),
            Sutun('Başlangıç', lambda r: tarih_yaz(r['bas']) or '—', sirala=lambda r: r['bas'], genislik=94, hiza='orta'),
            Sutun('Bitiş', lambda r: tarih_yaz(r['bit']), sirala=lambda r: r['bit'], genislik=94, hiza='orta'),
            Sutun('Gün', lambda r: r['takvim_gunu'] or '', genislik=50, hiza='orta', ipucu=lambda r: 'Takvim günü'),
            Sutun('Düşülen', lambda r: sayi_yaz(r['dusulen']) if r['dusulen'] is not None else '', sirala=lambda r: r['dusulen'] or 0,
                  genislik=74, hiza='orta', kalin=True, ipucu=lambda r: 'Yıllık izinden düşülen gün (Pazar ve resmi tatil hariç)'),
            Sutun('İşe dönüş', lambda r: tarih_yaz(r['isbasi']), sirala=lambda r: r['isbasi'], genislik=94, hiza='orta'),
            Sutun('Uyarı', lambda r: kisa_uyari(r['uyarilar']), genislik=150, renk=lambda r: T.KIRMIZI, ipucu=lambda r: '\n'.join(r['uyarilar'])),
            Sutun('Açıklama', lambda r: r['aciklama'] or '', genislik=200, renk=lambda r: T.SOLUK, gerilsin=True,
                  ipucu=lambda r: (r['aciklama'] or '') + f'\n\nGiren: {r["giren"] or "—"} · {tarih_yaz(r["yazildigi"])}'),
        ], soluk=lambda r: r['iptal'])
        self.tv, self.proxy = tablo(self.model)
        self.tv.setItemDelegateForColumn(2, RozetDelegate(_tur_rozet, parent=self.tv))
        self.tv.doubleClicked.connect(self._duzenle)
        self.tv.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tv.customContextMenuRequested.connect(self._menu)
        self.duzen.addWidget(tablo_karti(self.tv), 1)
        self.sayac = etiket('', 'SolukKucuk')
        self.duzen.addWidget(self.sayac)

    def _duzenle(self, idx=None):
        r = idx.data(Qt.UserRole + 1) if idx is not None else secili_satir(self.tv)
        if r:
            izin_penceresi(self.b, self.window(), kayit_id=r['id'])

    def _form(self):
        r = secili_satir(self.tv)
        if not r:
            self.b.bildir.emit('Önce listeden bir izin seçin', 'hata')
            return
        self.b.git.emit('pdf_form', r['id'])

    def _menu(self, poz):
        r = secili_satir(self.tv)
        if not r:
            return
        m = QMenu(self)
        m.addAction('Düzenle', lambda: izin_penceresi(self.b, self.window(), kayit_id=r['id']))
        m.addAction('İzin formu (PDF / yazdır)', lambda: self.b.git.emit('pdf_form', r['id']))
        m.addAction('Kişinin izin kartı', lambda: self.b.git.emit('kart', r['personel_id']))
        m.addSeparator()
        if r['iptal']:
            m.addAction('İptali geri al', lambda: self._iptal(r, False))
        else:
            m.addAction('İzni iptal et', lambda: self._iptal(r, True))
        m.exec(self.tv.viewport().mapToGlobal(poz))

    def _iptal(self, r, iptal):
        from .bilesenler import soru
        if iptal and not soru(self, 'İzni iptal et', f'Kayıt No {r["no"]} ({r["ad"]}) iptal edilsin mi?\n\n'
                                                     'İptal edilen izin hesaptan çıkar; kayıt listede üstü çizili kalır.', 'İptal et'):
            return
        self.b.db.izin_iptal(r['id'], iptal)
        self.b.yenile('İzin iptal edildi' if iptal else 'İptal geri alındı')

    def _filtre(self):
        q = self.arama.text().strip()
        tur = self.tur.currentData()
        yil = self.yil.currentData()
        uy, ip = self.uyarili.isChecked(), self.iptaller.isChecked()

        def f(r):
            if tur and r['tur'] != tur:
                return False
            if yil and not (r['bas'] and r['bas'].year <= yil <= (r['bit'] or r['bas']).year):
                return False
            if uy and not r['uyarilar']:
                return False
            if not ip and r['iptal']:
                return False
            if q and not (q.isdigit() and str(r['no']) == q) and not ara_eslesir(q, r['ad'], r['aciklama'], r['giren']):
                return False
            return True
        self.proxy.filtre_ayarla(f)
        n = self.proxy.rowCount()
        gun = sum(self.proxy.index(i, 0).data(Qt.UserRole + 1)['dusulen'] or 0 for i in range(n))
        self.sayac.setText(f'{n} kayıt · gösterilen kayıtlarda yıllık izinden düşülen toplam {sayi_yaz(gun)} gün')

    def yenile(self):
        ad = {p['id']: p['ad'] for p in self.b.veri['personel']}
        satirlar = []
        for k in self.b.veri['izinler']:
            r = dict(self.b.kayit(k['id']))
            r.update({'ad': ad.get(k['personel_id'], '?'), 'personel_id': k['personel_id'], 'aciklama': k.get('aciklama'),
                      'giren': k.get('giren'), 'yazildigi': k.get('yazildigi')})
            satirlar.append(r)
        satirlar.sort(key=lambda r: (r['bas'] or datetime.date.max, r['no']), reverse=True)
        self.model.doldur(satirlar)
        yillar = sorted({r['bas'].year for r in satirlar if r['bas']}, reverse=True)
        secili = self.yil.currentData()
        self.yil.blockSignals(True)
        self.yil.clear()
        self.yil.addItem('Tüm yıllar', None)
        for y in yillar:
            self.yil.addItem(str(y), y)
        i = self.yil.findData(secili)
        self.yil.setCurrentIndex(max(i, 0))
        self.yil.blockSignals(False)
        self._filtre()

    def ac(self, parametre):
        if parametre == 'uyarili':
            self.uyarili.setChecked(True)
