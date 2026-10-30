# -*- coding: utf-8 -*-
"""Genel Durum: göstergeler, izindekiler, yaklaşan hak tarihleri, dikkat gerektirenler ve herkesin kalan izni."""
import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QButtonGroup, QGridLayout, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget

from . import tema as T
from .bilesenler import (duzen_temizle, AramaKutusu, BosDurum, Kart, KalanDelegate, KpiKart, ListeModeli, RozetDelegate, Sutun, dugme, durum_renk,
                         etiket, secili_satir, tablo, tablo_karti, yatay, kalan_renk)
from .dialog_izin import izin_penceresi
from .kisi_satiri import KisiSatiri
from .sayfa import Sayfa
from .. import motor
from ..yardimci import GUN_KISA, KOD_AD, KOD_RENK, ara_eslesir, sayi_yaz, tarih_yaz, tr_anahtar


def bakiye_sutunlari():
    return [
        Sutun('Ad Soyad', lambda k: k['ad'], sirala=lambda k: tr_anahtar(k['ad']), genislik=215, kalin=True),
        Sutun('Durum', lambda k: k['durum'], genislik=120, tur='rozet'),
        Sutun('İşe giriş', lambda k: tarih_yaz(k['son_giris']), sirala=lambda k: k['son_giris'], genislik=96, hiza='orta'),
        Sutun('Hizmet yılı', lambda k: k['kidem'], genislik=84, hiza='orta'),
        Sutun('Kazanılan', lambda k: sayi_yaz(k['hak_son']), sirala=lambda k: k['hak_son'], genislik=88, hiza='orta',
              ipucu=lambda k: 'Bu çalışma döneminde kazanılan izin (gün)'),
        Sutun('Kullanılan', lambda k: sayi_yaz(k['kul_son']), sirala=lambda k: k['kul_son'], genislik=88, hiza='orta',
              ipucu=lambda k: 'Bu çalışma döneminde kullanılan yıllık izin (gün; ileri tarihli izinler dahil)'),
        Sutun('Düzeltme', lambda k: sayi_yaz((k['duz'] or 0) + (k['tasinan_eksi'] or 0)) if (k['duz'] or 0) + (k['tasinan_eksi'] or 0) else '',
              sirala=lambda k: (k['duz'] or 0) + (k['tasinan_eksi'] or 0), genislik=84, hiza='orta',
              ipucu=lambda k: 'Elle düzeltme + önceki dönemden taşınan eksi'),
        Sutun('Kalan', lambda k: sayi_yaz(k['kalan']), sirala=lambda k: k['kalan'] if k['kalan'] is not None else -10 ** 6,
              genislik=80, hiza='orta', tur='kalan'),
        Sutun('Sonraki hak', lambda k: (f'{tarih_yaz(k["sonraki_tarih"])}  (+{k["sonraki_gun"]})' if k['sonraki_tarih'] else ''),
              sirala=lambda k: k['sonraki_tarih'], genislik=140, hiza='orta'),
        Sutun('Uyarı', lambda k: (f'{k["uyarili_kayit"]} kayıt' if k['uyarili_kayit'] else '') +
              (' · ' if k['uyarili_kayit'] and (k['hatalar'] or k['uyarilar']) else '') + ('kişi bilgisi' if k['hatalar'] or k['uyarilar'] else ''),
              sirala=lambda k: k['uyarili_kayit'] + 100 * bool(k['hatalar'] or k['uyarilar']), genislik=120,
              renk=lambda k: T.KIRMIZI if k['hatalar'] else T.SARI,
              ipucu=lambda k: '\n'.join(k['hatalar'] + k['uyarilar']) or (f'{k["uyarili_kayit"]} izin kaydında uyarı var' if k['uyarili_kayit'] else '')),
        Sutun('Not', lambda k: k.get('not_ozet') or '', genislik=160, renk=lambda k: T.SOLUK, ipucu=lambda k: k.get('not_ozet') or '', gerilsin=True),
    ]


def bakiye_tablosu(model):
    v, proxy = tablo(model)
    for i, s in enumerate(model.sutunlar):
        if s.tur == 'rozet':
            v.setItemDelegateForColumn(i, RozetDelegate(durum_renk, parent=v))
        elif s.tur == 'kalan':
            v.setItemDelegateForColumn(i, KalanDelegate(lambda k: k['kalan'], parent=v))
    return v, proxy


class GenelSayfa(Sayfa):
    baslik = 'Genel Durum'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        excel = dugme('Excel\'e aktar', 'excel', ipucu='Genel durum, izin kayıtları ve personel listesini Excel dosyası olarak kaydeder')
        excel.clicked.connect(lambda: self.b.git.emit('excel', None))
        pdf = dugme('Yazdır / PDF', 'yazdir', ipucu='Kalan izin listesini PDF olarak kaydeder ya da yazdırır')
        pdf.clicked.connect(lambda: self.b.git.emit('pdf_genel', None))
        yeni = dugme('Yeni izin', 'arti', 'Vurgu', 'Yeni izin kaydı (Ctrl+N)')
        yeni.clicked.connect(lambda: izin_penceresi(self.b, self.window()))
        self.ust.ekle(excel)
        self.ust.ekle(pdf)
        self.ust.ekle(yeni)

        # sayfanın tamamı kayar (pano)
        self.duzen.removeWidget(self.ust)
        kay = QScrollArea()
        kay.setWidgetResizable(True)
        kay.setFrameShape(QScrollArea.NoFrame)
        kay.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        ic = QWidget()
        ic.setObjectName('Icerik')
        self.ic = QVBoxLayout(ic)
        self.ic.setContentsMargins(30, 26, 30, 30)
        self.ic.setSpacing(16)
        self.ic.addWidget(self.ust)
        kay.setWidget(ic)
        self.duzen.setContentsMargins(0, 0, 0, 0)
        self.duzen.addWidget(kay)

        self.elle = etiket('', 'ElleTarih', True)
        self.ic.addWidget(self.elle)

        kpi = QHBoxLayout()
        kpi.setSpacing(16)
        self.k_calisan = KpiKart('Çalışan', 'personel', T.MAVI, T.MAVI_ACIK)
        self.k_kalan = KpiKart('Toplam kalan izin', 'katman', T.YESIL, T.YESIL_ACIK)
        self.k_eksi = KpiKart('Kalanı eksi olan', 'eksi', T.KIRMIZI, T.KIRMIZI_ACIK)
        self.k_izinde = KpiKart('Bugün izinde', 'ucak', T.TURUNCU_2, T.TURUNCU_ACIK)
        for k in (self.k_calisan, self.k_kalan, self.k_eksi, self.k_izinde):
            kpi.addWidget(k)
        self.k_calisan.tiklandi.connect(lambda: self.b.git.emit('personel', None))
        self.k_kalan.tiklandi.connect(lambda: self._suz('hepsi'))
        self.k_eksi.tiklandi.connect(lambda: self._suz('eksi'))
        self.k_izinde.tiklandi.connect(lambda: self.b.git.emit('takvim', None))
        self.ic.addLayout(kpi)

        orta = QHBoxLayout()
        orta.setSpacing(16)
        self.c_izin = Kart('İzindekiler ve yaklaşan izinler', 'ucak')
        self.c_hak = Kart('Yaklaşan hak tarihleri', 'hediye')
        self.c_dikkat = Kart('Dikkat gerektirenler', 'kontrol')
        for c in (self.c_izin, self.c_hak, self.c_dikkat):
            c.setMinimumHeight(300)
            c.liste = QVBoxLayout()
            c.liste.setSpacing(2)
            c.duzen.addLayout(c.liste)
            c.duzen.addStretch(1)
            orta.addWidget(c, 1)
        self.ic.addLayout(orta)

        self.tablo_kart = Kart('Kalan izinler', 'katman')
        self.arama = AramaKutusu('Ad ara…')
        self.arama.setMaximumWidth(280)
        self.arama.textChanged.connect(self._filtre)
        self.filtre_grup = QButtonGroup(self)
        ust = QHBoxLayout()
        ust.setSpacing(6)
        for ad, metin in (('hepsi', 'Tümü'), ('eksi', 'Eksi bakiye'), ('birikmis', '30 günden fazla'), ('uyari', 'Uyarılı')):
            b = dugme(metin, tur='Secmeli')
            b.setCheckable(True)
            b.setProperty('ad', ad)
            self.filtre_grup.addButton(b)
            ust.addWidget(b)
            if ad == 'hepsi':
                b.setChecked(True)
        self.filtre_grup.buttonClicked.connect(lambda _: self._filtre())
        ust.addStretch(1)
        ust.addWidget(self.arama)
        self.tablo_kart.duzen.addLayout(ust)
        self.model = ListeModeli(bakiye_sutunlari())
        self.tv, self.proxy = bakiye_tablosu(self.model)
        self.tv.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.tv.setMinimumWidth(200)
        self.tv.doubleClicked.connect(self._ac)
        self.tv.setToolTip('Kişinin izin kartını açmak için çift tıklayın')
        self.tablo_kart.duzen.addWidget(self.tv)
        self.ic.addWidget(self.tablo_kart)

    # ------------------------------------------------------------------
    def _suz(self, ad):
        for b in self.filtre_grup.buttons():
            b.setChecked(b.property('ad') == ad)
        self._filtre()
        self.tablo_kart.setFocus()

    def _filtre(self):
        b = self.filtre_grup.checkedButton()
        ad = b.property('ad') if b else 'hepsi'
        q = self.arama.text()

        def f(k):
            if not ara_eslesir(q, k['ad'], k.get('onceki_ad')):
                return False
            if ad == 'eksi':
                return (k['kalan'] or 0) < 0
            if ad == 'birikmis':
                return (k['kalan'] or 0) > 30
            if ad == 'uyari':
                return bool(k['uyarili_kayit'] or k['hatalar'] or k['uyarilar'])
            return True
        self.proxy.filtre_ayarla(f)
        self._yukseklik()

    def _yukseklik(self):
        n = self.proxy.rowCount()
        self.tv.setFixedHeight(42 + max(n, 1) * 40 + 4)

    def _ac(self, idx):
        k = idx.data(Qt.UserRole + 1)
        if k:
            self.b.git.emit('kart', k['id'])

    def _liste_temizle(self, kart):
        duzen_temizle(kart.liste)

    def yenile(self):
        b, s, oz = self.b, self.b.sonuc, self.b.ozet
        bugun = b.bugun
        self.ust.alt.setText(f'{b.sirket()} · hesap tarihi {tarih_yaz(bugun)} · {oz["calisan"]} çalışan')
        self.elle.setText(f'Hesap tarihi elle {tarih_yaz(bugun)} olarak ayarlı — bugünün durumu değil. Ayarlar sayfasından "Bugün"e çevirin.')
        self.elle.setVisible(b.tarih_elle)
        cal = s.calisanlar()
        self.k_calisan.ayarla(str(oz['calisan']), f'{oz["teyit_bekleyen"]} kişinin bilgisi teyit bekliyor' if oz['teyit_bekleyen'] else 'hepsi teyitli')
        ort = oz['toplam_kalan'] / oz['calisan'] if oz['calisan'] else 0
        self.k_kalan.ayarla(f'{sayi_yaz(oz["toplam_kalan"])} gün', f'kişi başı ortalama {sayi_yaz(round(ort, 1))} gün')
        self.k_eksi.ayarla(str(oz['eksi']), 'hak edilmeden kullanılan (avans)' if oz['eksi'] else 'eksi bakiye yok',
                           T.KIRMIZI if oz['eksi'] else None)
        bugunku = motor.izindekiler(s, b.veri, bugun, bugun)
        hafta_son = bugun + datetime.timedelta(days=6 - bugun.weekday())
        hafta = motor.izindekiler(s, b.veri, bugun, hafta_son)
        self.k_izinde.ayarla(str(len({x[1]['id'] for x in bugunku})), f'bu hafta {len({x[1]["id"] for x in hafta})} kişi izinli')

        # izindekiler ve yaklaşan (14 gün)
        self._liste_temizle(self.c_izin)
        yak = motor.izindekiler(s, b.veri, bugun, bugun + datetime.timedelta(days=14))
        if not yak:
            self.c_izin.liste.addWidget(etiket('Önümüzdeki 14 günde izinli çalışan yok.', 'Soluk'))
            son = sorted((k for k in b.veri['izinler'] if not k['iptal'] and s.kayit[k['id']]['gecerli']),
                         key=lambda k: (k.get('yazildigi') or datetime.date.min, k['no']), reverse=True)[:5]
            if son:
                self.c_izin.liste.addSpacing(6)
                self.c_izin.liste.addWidget(etiket('SON GİRİLEN İZİNLER', 'KpiEtiket'))
            for k in son:
                r, ks = s.kayit[k['id']], s.kisi[k['personel_id']]
                ara = tarih_yaz(r['bas']) if r['bas'] == r['bit'] else f'{tarih_yaz(r["bas"])} – {tarih_yaz(r["bit"])}'
                satir = KisiSatiri(ks['ad'], f'{ara} · girildi {tarih_yaz(k.get("yazildigi"))}', KOD_AD[r['tur']], KOD_RENK[r['tur']])
                satir.tiklandi.connect(lambda kid=k['id']: izin_penceresi(self.b, self.window(), kayit_id=kid))
                self.c_izin.liste.addWidget(satir)
        for r, ks in yak[:6]:
            ara = tarih_yaz(r['bas']) if r['bas'] == r['bit'] else f'{tarih_yaz(r["bas"])} – {tarih_yaz(r["bit"])}'
            durum = 'şu an izinde' if r['bas'] <= bugun <= r['bit'] else f'{(r["bas"] - bugun).days} gün sonra'
            satir = KisiSatiri(ks['ad'], f'{ara} · {durum}', KOD_AD[r['tur']], KOD_RENK[r['tur']])
            satir.tiklandi.connect(lambda kid=r['id']: izin_penceresi(self.b, self.window(), kayit_id=kid))
            self.c_izin.liste.addWidget(satir)
        if len(yak) > 6:
            d = dugme(f'+{len(yak) - 6} izin daha — takvimde gör', tur='Bag')
            d.clicked.connect(lambda: self.b.git.emit('takvim', None))
            self.c_izin.liste.addWidget(d)

        # yaklaşan hak tarihleri (60 gün)
        self._liste_temizle(self.c_hak)
        hak = motor.yaklasan_haklar(s, 60)
        if not hak:
            self.c_hak.liste.addWidget(etiket('Önümüzdeki 60 günde yeni izin hakkı doğmuyor.', 'Soluk'))
        for ks in hak[:6]:
            gun = (ks['sonraki_tarih'] - bugun).days
            satir = KisiSatiri(ks['ad'], f'{tarih_yaz(ks["sonraki_tarih"])} · {"bugün" if gun == 0 else f"{gun} gün sonra"}',
                               f'+{ks["sonraki_gun"]} gün', (T.YESIL_ACIK, T.YESIL))
            satir.tiklandi.connect(lambda pid=ks['id']: self.b.git.emit('kart', pid))
            self.c_hak.liste.addWidget(satir)
        if len(hak) > 6:
            self.c_hak.liste.addWidget(etiket(f'+{len(hak) - 6} kişi daha (tabloda "Sonraki hak" sütununa göre sıralayın)', 'SolukKucuk'))

        # dikkat
        self._liste_temizle(self.c_dikkat)
        maddeler = []
        if oz['eksi']:
            enler = sorted([k for k in cal if (k['kalan'] or 0) < 0], key=lambda k: k['kalan'])[:3]
            maddeler.append((f'{oz["eksi"]} çalışanın kalanı eksi', ', '.join(f'{k["ad"]} ({sayi_yaz(k["kalan"])})' for k in enler),
                             (T.KIRMIZI_ACIK, T.KIRMIZI), lambda: self._suz('eksi')))
        if oz['birikmis']:
            maddeler.append((f'{oz["birikmis"]} çalışanda 30 günden fazla izin birikmiş', 'Yıllık iznin kullandırılması planlanmalı',
                             (T.SARI_ACIK, T.SARI), lambda: self._suz('birikmis')))
        if oz['uyarili_kayit']:
            maddeler.append((f'{oz["uyarili_kayit"]} izin kaydında uyarı', 'Avans izin, dönem dışı tarih, çakışma vb.',
                             (T.SARI_ACIK, T.SARI), lambda: self.b.git.emit('kontrol', None)))
        if oz['personel_uyari']:
            maddeler.append((f'{oz["personel_uyari"]} personel kaydında eksik/uyarı', 'Doğum tarihi, çalışma dönemi vb.',
                             (T.KIRMIZI_ACIK, T.KIRMIZI), lambda: self.b.git.emit('kontrol', None)))
        if oz['tatil_eksik']:
            maddeler.append(('Gelecek yılın resmi tatilleri eksik', f'Tatil listesi {oz["tatil_son_yil"] or "—"} yılında bitiyor',
                             (T.SARI_ACIK, T.SARI), lambda: self.b.git.emit('tatil', None)))
        if oz['ayrilan']:
            odenmemis = [k for k in s.ayrilanlar() if (k['odenecek'] or 0) > 0 and (b.veri['odemeler'].get(k['id']) or {}).get('odendi') != 'Ödendi']
            if odenmemis:
                maddeler.append((f'{len(odenmemis)} ayrılana izin ücreti ödenmemiş', 'Ayrılanlar sayfasında ödemeyi işleyin',
                                 (T.KIRMIZI_ACIK, T.KIRMIZI), lambda: self.b.git.emit('ayrilan', None)))
        if not maddeler:
            self.c_dikkat.liste.addWidget(etiket('Her şey yolunda görünüyor.', 'Soluk'))
        for baslik, alt, renk, eylem in maddeler[:6]:
            w = QWidget()
            w.setCursor(Qt.PointingHandCursor)
            w.setObjectName('KisiSatiri')
            w.setAttribute(Qt.WA_StyledBackground, True)
            w.setStyleSheet('#KisiSatiri { border-radius: 10px; } #KisiSatiri:hover { background: #F5F6FB; }')
            h = QHBoxLayout(w)
            h.setContentsMargins(6, 6, 8, 6)
            nokta = QLabel()
            nokta.setFixedSize(10, 10)
            nokta.setStyleSheet(f'background: {renk[1]}; border-radius: 5px;')
            h.addWidget(nokta, 0, Qt.AlignTop)
            v = QVBoxLayout()
            v.setSpacing(0)
            a = QLabel(baslik)
            a.setStyleSheet('font-weight: 600;')
            v.addWidget(a)
            al = QLabel(alt)
            al.setObjectName('SolukKucuk')
            al.setWordWrap(True)
            v.addWidget(al)
            h.addLayout(v, 1)
            w.mousePressEvent = lambda e, f=eylem: f()
            self.c_dikkat.liste.addWidget(w)

        # tablo
        satirlar = []
        pmap = {p['id']: p for p in b.veri['personel']}
        for k in s.sirali:
            k = dict(k)
            k['not_ozet'] = pmap[k['id']].get('not_ozet')
            k['onceki_ad'] = pmap[k['id']].get('onceki_ad')
            satirlar.append(k)
        self.model.doldur(satirlar)
        self.tv.setColumnHidden(1, not s.ayrilanlar())
        self._filtre()
