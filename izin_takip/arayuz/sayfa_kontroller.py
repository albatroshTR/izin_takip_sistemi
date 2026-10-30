# -*- coding: utf-8 -*-
"""Kontroller: uyarılı izin kayıtları ve personel kayıtları; tıklayınca ilgili kayıt açılır."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QTabWidget, QVBoxLayout, QWidget

from . import tema as T
from .bilesenler import AramaKutusu, KpiKart, ListeModeli, RozetDelegate, Sutun, dugme, etiket, tablo, tablo_karti, tur_renk
from .dialog_izin import izin_penceresi
from .dialog_personel import personel_penceresi
from .sayfa import Sayfa
from ..yardimci import KOD_AD, ara_eslesir, tarih_yaz, tr_anahtar

TURLER = [('avans', 'Avans (hak edilmeden kullanılan)', 'Bu izinle kalan'), ('donem', 'Çalışma dönemi dışında', 'Çalışma dönemi dışında'),
          ('cakisma', 'Çakışan kayıt', 'çakışan'), ('tatil', 'Pazar / resmi tatile yazılmış', 'Pazar/resmi tatil'),
          ('eksik', 'Eksik / hatalı kayıt', None)]


def uyari_turu(u):
    for a, _, anahtar in TURLER:
        if anahtar and anahtar in u:
            return a
    return 'eksik'


class KontrollerSayfa(Sayfa):
    baslik = 'Kontroller'
    alt_baslik = 'Otomatik uyarılar. Bir satıra çift tıklayıp kaydı düzeltin; liste kendiliğinden güncellenir.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        kpi = QHBoxLayout()
        kpi.setSpacing(16)
        self.k_kayit = KpiKart('Uyarılı izin kaydı', 'izin', T.SARI, T.SARI_ACIK)
        self.k_avans = KpiKart('Avans uyarısı', 'eksi', T.KIRMIZI, T.KIRMIZI_ACIK)
        self.k_personel = KpiKart('Personel uyarısı', 'kisi', T.MAVI, T.MAVI_ACIK)
        self.k_tatil = KpiKart('Tatil listesi', 'tatil', T.YESIL, T.YESIL_ACIK)
        for k in (self.k_kayit, self.k_avans, self.k_personel, self.k_tatil):
            kpi.addWidget(k)
        self.k_kayit.tiklandi.connect(lambda: self.sekme.setCurrentIndex(0))
        self.k_avans.tiklandi.connect(lambda: (self.sekme.setCurrentIndex(0), self.arama.setText('avans')))
        self.k_personel.tiklandi.connect(lambda: self.sekme.setCurrentIndex(1))
        self.k_tatil.tiklandi.connect(lambda: self.b.git.emit('tatil', None))
        self.duzen.addLayout(kpi)

        self.sekme = QTabWidget()
        self.duzen.addWidget(self.sekme, 1)
        w = QWidget()
        d = QVBoxLayout(w)
        d.setContentsMargins(0, 10, 0, 0)
        d.setSpacing(8)
        ust = QHBoxLayout()
        self.arama = AramaKutusu('Personel ya da uyarı ara…')
        self.arama.textChanged.connect(self._filtre)
        ust.addWidget(self.arama)
        ust.addStretch(1)
        d.addLayout(ust)
        self.m_kayit = ListeModeli([
            Sutun('No', lambda r: r['no'], genislik=64, hiza='orta'),
            Sutun('Personel', lambda r: r['ad'], sirala=lambda r: tr_anahtar(r['ad']), genislik=220, kalin=True),
            Sutun('İzin türü', lambda r: KOD_AD[r['tur']], genislik=140, tur='rozet'),
            Sutun('Başlangıç', lambda r: tarih_yaz(r['bas']) or '—', sirala=lambda r: r['bas'], genislik=100, hiza='orta'),
            Sutun('Bitiş', lambda r: tarih_yaz(r['bit']), sirala=lambda r: r['bit'], genislik=100, hiza='orta'),
            Sutun('Uyarı', lambda r: '; '.join(r['uyarilar']), renk=lambda r: T.KIRMIZI if r['tip'] in ('eksik', 'cakisma') else '#8A5A00',
                  ipucu=lambda r: '\n'.join(r['uyarilar'])),
        ])
        self.tv_kayit, self.px_kayit = tablo(self.m_kayit)
        self.tv_kayit.setItemDelegateForColumn(2, RozetDelegate(tur_renk, parent=self.tv_kayit))
        self.tv_kayit.doubleClicked.connect(lambda idx: izin_penceresi(self.b, self.window(), kayit_id=idx.data(Qt.UserRole + 1)['id']))
        d.addWidget(tablo_karti(self.tv_kayit), 1)
        d.addWidget(etiket('Avans uyarısı engel değildir : bakiyesi yetmeyen birine izin girilebilir; kalan eksiye düşer ve '
                           'sonraki hak tarihlerinde kapanır. Çalışma dönemi dışındaki yıllık izin en yakın döneme düşülür.',
                           'SolukKucuk', True))
        self.sekme.addTab(w, 'İzin kayıtları')
        w2 = QWidget()
        d2 = QVBoxLayout(w2)
        d2.setContentsMargins(0, 10, 0, 0)
        self.m_kisi = ListeModeli([
            Sutun('Ad Soyad', lambda r: r['ad'], sirala=lambda r: tr_anahtar(r['ad']), genislik=240, kalin=True),
            Sutun('Önem', lambda r: 'Hesaplanmıyor' if r['hatalar'] else 'Uyarı', genislik=130, tur='rozet'),
            Sutun('Uyarı', lambda r: '; '.join(r['hatalar'] + r['uyarilar']), renk=lambda r: T.KIRMIZI if r['hatalar'] else '#8A5A00'),
        ])
        self.tv_kisi, _ = tablo(self.m_kisi)
        self.tv_kisi.setItemDelegateForColumn(1, RozetDelegate(lambda m, r: (T.KIRMIZI_ACIK, T.KIRMIZI) if m == 'Hesaplanmıyor'
                                                               else (T.SARI_ACIK, T.SARI), parent=self.tv_kisi))
        self.tv_kisi.doubleClicked.connect(lambda idx: personel_penceresi(self.b, self.window(), idx.data(Qt.UserRole + 1)['id']))
        d2.addWidget(tablo_karti(self.tv_kisi), 1)
        self.sekme.addTab(w2, 'Personel')

    def _filtre(self):
        q = self.arama.text()
        if q.lower() == 'avans':
            self.px_kayit.filtre_ayarla(lambda r: r['tip'] == 'avans' or any('avans' in u for u in r['uyarilar']))
        else:
            self.px_kayit.filtre_ayarla(lambda r: ara_eslesir(q, r['ad'], ' '.join(r['uyarilar'])))

    def yenile(self):
        s, oz = self.b.sonuc, self.b.ozet
        ad = {p['id']: p['ad'] for p in self.b.veri['personel']}
        kayitlar = []
        for k in self.b.veri['izinler']:
            r = s.kayit[k['id']]
            if r['iptal'] or not r['uyarilar']:
                continue
            r = dict(r)
            r['ad'] = ad.get(k['personel_id'], '?')
            r['tip'] = uyari_turu(r['uyarilar'][0])
            kayitlar.append(r)
        kayitlar.sort(key=lambda r: (r['bas'] is not None, r['bas']), reverse=False)
        kayitlar.sort(key=lambda r: 0 if r['tip'] == 'eksik' else 1)
        self.m_kayit.doldur(kayitlar)
        kisiler = [k for k in s.sirali if k['hatalar'] or k['uyarilar']]
        self.m_kisi.doldur(kisiler)
        avans = sum(1 for r in kayitlar if any('avans' in u for u in r['uyarilar']))
        eksik = sum(1 for r in kayitlar if r['tip'] == 'eksik')
        self.k_kayit.ayarla(str(len(kayitlar)), f'{eksik} kayıt eksik/hatalı (hesaba girmiyor)' if eksik else 'hepsi hesaba giriyor',
                            T.KIRMIZI if eksik else None)
        self.k_avans.ayarla(str(avans), 'kayıt kalanı eksiye düşürmüş')
        self.k_personel.ayarla(str(len(kisiler)), 'eksik bilgi yok' if not kisiler else f'{sum(1 for k in kisiler if k["hatalar"])} kişi hesaplanmıyor')
        self.k_tatil.ayarla(str(oz['tatil_son_yil'] or '—'), 'gelecek yılın tatillerini ekleyin' if oz['tatil_eksik'] else 'son yıl hazır',
                            T.KIRMIZI if oz['tatil_eksik'] else None)
        self.sekme.setTabText(0, f'İzin kayıtları ({len(kayitlar)})')
        self.sekme.setTabText(1, f'Personel ({len(kisiler)})')
        self._filtre()
