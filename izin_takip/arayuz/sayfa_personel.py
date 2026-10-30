# -*- coding: utf-8 -*-
"""Personel listesi ve kişinin İzin Kartı (hak kazanma, izin geçmişi, yıllık özet, açıklamalar)."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QMenu, QStackedWidget,
                               QTabWidget, QTextBrowser, QVBoxLayout, QWidget)

from . import tema as T
from .bilesenler import (AramaKutusu, Kart, KalanDelegate, ListeModeli, RozetDelegate, Sutun, dugme, durum_renk, etiket,
                         kalan_renk, kisa_uyari, secili_satir, tablo, tablo_karti, tur_renk, duzen_temizle)
from .dialog_izin import izin_penceresi
from .dialog_personel import personel_penceresi
from .kisi_satiri import Avatar
from .sayfa import Sayfa
from ..yardimci import KOD_AD, ara_eslesir, sayi_yaz, tarih_yaz, tr_anahtar


def _metin_html(s):
    import html
    return html.escape(s or '').replace('\n', '<br>')


class KartGorunumu(QWidget):
    """Bir kişinin izin kartı (ekranda)."""

    def __init__(self, baglam, geri, parent=None):
        super().__init__(parent)
        self.b = baglam
        self.pid = None
        d = QVBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(14)
        ust = QHBoxLayout()
        g = dugme('Personel listesi', 'geri', 'Duz')
        g.clicked.connect(geri)
        ust.addWidget(g)
        ust.addStretch(1)
        self.d_duzenle = dugme('Bilgileri düzenle', 'duzenle')
        self.d_duzenle.clicked.connect(self._duzenle)
        self.d_pdf = dugme('İzin kartı (PDF / yazdır)', 'yazdir')
        self.d_pdf.clicked.connect(lambda: self.b.git.emit('pdf_kart', self.pid))
        self.d_izin = dugme('Yeni izin', 'arti', 'Vurgu')
        self.d_izin.clicked.connect(lambda: izin_penceresi(self.b, self.window(), personel_id=self.pid))
        for w in (self.d_duzenle, self.d_pdf, self.d_izin):
            ust.addWidget(w)
        d.addLayout(ust)

        # üst kart
        self.ust_kart = QFrame()
        self.ust_kart.setObjectName('Kart')
        uk = QHBoxLayout(self.ust_kart)
        uk.setContentsMargins(22, 20, 22, 20)
        uk.setSpacing(18)
        self.avatar_yer = QVBoxLayout()
        uk.addLayout(self.avatar_yer)
        orta = QVBoxLayout()
        orta.setSpacing(6)
        ad_satir = QHBoxLayout()
        self.ad = etiket('', 'SayfaBaslik')
        ad_satir.addWidget(self.ad)
        self.rozetler = QHBoxLayout()
        self.rozetler.setSpacing(6)
        ad_satir.addLayout(self.rozetler)
        ad_satir.addStretch(1)
        orta.addLayout(ad_satir)
        self.bilgi = QGridLayout()
        self.bilgi.setHorizontalSpacing(28)
        self.bilgi.setVerticalSpacing(4)
        orta.addLayout(self.bilgi)
        orta.addStretch(1)
        uk.addLayout(orta, 1)
        sag = QVBoxLayout()
        sag.setSpacing(0)
        sag.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.kalan = etiket('', 'BuyukKalan')
        self.kalan.setAlignment(Qt.AlignRight)
        sag.addWidget(etiket('KALAN YILLIK İZİN', 'KpiEtiket'), 0, Qt.AlignRight)
        sag.addWidget(self.kalan, 0, Qt.AlignRight)
        self.sonraki = etiket('', 'Soluk')
        self.sonraki.setAlignment(Qt.AlignRight)
        sag.addWidget(self.sonraki, 0, Qt.AlignRight)
        uk.addLayout(sag)
        d.addWidget(self.ust_kart)

        self.uyari = QLabel()
        self.uyari.setObjectName('UyariKutu')
        self.uyari.setWordWrap(True)
        self.uyari.setContentsMargins(12, 9, 12, 9)
        d.addWidget(self.uyari)

        # mini göstergeler
        mini = QHBoxLayout()
        mini.setSpacing(12)
        self.mini = {}
        for a, e in (('hak', 'Bu dönem kazanılan'), ('kul', 'Bu dönem kullanılan'), ('tas', 'Önceki dönemden taşınan eksi'),
                     ('duz', 'Elle düzeltme'), ('onceki', 'Önceki dönemlerin kalanı')):
            f = QFrame()
            f.setObjectName('Kart')
            fl = QVBoxLayout(f)
            fl.setContentsMargins(16, 10, 16, 10)
            fl.setSpacing(0)
            fl.addWidget(etiket(e, 'KpiEtiket'))
            v = etiket('—')
            v.setStyleSheet('font-size: 15pt; font-weight: 700;')
            fl.addWidget(v)
            mini.addWidget(f, 1)
            self.mini[a] = (f, v)
        d.addLayout(mini)

        # sekmeler
        self.sekme = QTabWidget()
        d.addWidget(self.sekme, 1)
        # izin geçmişi
        w1 = QWidget()
        l1 = QVBoxLayout(w1)
        l1.setContentsMargins(0, 10, 0, 0)
        l1.setSpacing(8)
        ust1 = QHBoxLayout()
        self.sadece_yillik = QCheckBox('Yalnız yıllık izinler')
        self.sadece_yillik.toggled.connect(self._izin_filtre)
        self.iptaller = QCheckBox('İptal edilenleri göster')
        self.iptaller.setChecked(True)
        self.iptaller.toggled.connect(self._izin_filtre)
        ust1.addWidget(self.sadece_yillik)
        ust1.addWidget(self.iptaller)
        ust1.addStretch(1)
        ust1.addWidget(etiket('Düzenlemek için çift tıklayın', 'SolukKucuk'))
        l1.addLayout(ust1)
        self.m_izin = ListeModeli([
            Sutun('No', lambda r: r['no'], genislik=60, hiza='orta'),
            Sutun('İzin türü', lambda r: ('İptal' if r['iptal'] else KOD_AD[r['tur']]), genislik=130, tur='rozet'),
            Sutun('Başlangıç', lambda r: tarih_yaz(r['bas']), sirala=lambda r: r['bas'], genislik=100, hiza='orta'),
            Sutun('Bitiş', lambda r: tarih_yaz(r['bit']), sirala=lambda r: r['bit'], genislik=100, hiza='orta'),
            Sutun('Gün', lambda r: r['takvim_gunu'] or '', genislik=60, hiza='orta', ipucu=lambda r: 'Takvim günü'),
            Sutun('Düşülen', lambda r: sayi_yaz(r['dusulen']) if r['dusulen'] is not None else ('—' if not r['iptal'] else ''),
                  sirala=lambda r: r['dusulen'] or 0, genislik=80, hiza='orta', kalin=True, ipucu=lambda r: 'Yıllık izinden düşülen gün'),
            Sutun('İşe dönüş', lambda r: tarih_yaz(r['isbasi']), sirala=lambda r: r['isbasi'], genislik=100, hiza='orta'),
            Sutun('Uyarı', lambda r: kisa_uyari(r['uyarilar']), genislik=170, renk=lambda r: T.KIRMIZI, ipucu=lambda r: '\n'.join(r['uyarilar'])),
            Sutun('Açıklama', lambda r: r['aciklama'] or '', genislik=200, renk=lambda r: T.SOLUK, ipucu=lambda r: r['aciklama'] or '', gerilsin=True),
        ], soluk=lambda r: r['iptal'])
        self.tv_izin, self.px_izin = tablo(self.m_izin)
        self.tv_izin.setItemDelegateForColumn(1, RozetDelegate(tur_renk_iptal, parent=self.tv_izin))
        self.tv_izin.doubleClicked.connect(self._izin_ac)
        l1.addWidget(tablo_karti(self.tv_izin), 1)
        self.sekme.addTab(w1, 'İzin geçmişi')
        # hak kazanma
        w2 = QWidget()
        l2 = QVBoxLayout(w2)
        l2.setContentsMargins(0, 10, 0, 0)
        self.m_hak = ListeModeli([
            Sutun('Hizmet yılı', lambda h: f'{h["kidem"]}.', genislik=90, hiza='orta'),
            Sutun('Önceki hak tarihi', lambda h: tarih_yaz(h['onceki']), genislik=130, hiza='orta'),
            Sutun('Ücretsiz izin', lambda h: h['uz_gun'] or '', genislik=100, hiza='orta', ipucu=lambda h: 'Hak tarihini öteleyen çalışılmayan gün'),
            Sutun('Hak tarihi', lambda h: tarih_yaz(h['tarih']), genislik=110, hiza='orta', kalin=True),
            Sutun('Yaş', lambda h: h['yas'] if h['yas'] is not None else '', genislik=60, hiza='orta'),
            Sutun('İzin (gün)', lambda h: h['gun'], genislik=90, hiza='orta', kalin=True),
            Sutun('Bu haktan kalan', lambda h: sayi_yaz(h['kalan']) if h['kalan'] is not None else ('önceki dönem' if h['durum'] == 'Kazanıldı' else ''),
                  genislik=130, hiza='orta', ipucu=lambda h: 'En eski hak önce kullanılır'),
            Sutun('Durum', lambda h: h['durum'], genislik=130, tur='rozet'),
            Sutun('Açıklama', lambda h: h['aciklama'], genislik=260, renk=lambda h: T.SOLUK, gerilsin=True),
        ])
        self.tv_hak, _ = tablo(self.m_hak)
        self.tv_hak.setSortingEnabled(False)
        self.tv_hak.setItemDelegateForColumn(7, RozetDelegate(lambda m, r: (T.YESIL_ACIK, T.YESIL) if m == 'Kazanıldı' else (T.MAVI_ACIK, T.MAVI),
                                                              parent=self.tv_hak))
        l2.addWidget(tablo_karti(self.tv_hak), 1)
        self.hak_not = etiket('', 'SolukKucuk', True)
        l2.addWidget(self.hak_not)
        self.sekme.addTab(w2, 'Hak kazanma')
        # yıllık özet
        w3 = QWidget()
        l3 = QVBoxLayout(w3)
        l3.setContentsMargins(0, 10, 0, 0)
        self.m_yil = ListeModeli([
            Sutun('Yıl', lambda y: y['yil'], genislik=70, hiza='orta', kalin=True),
            Sutun('Kazanılan', lambda y: sayi_yaz(y['kazanilan']) or '', genislik=100, hiza='orta'),
            Sutun('Kullanılan yıllık izin', lambda y: sayi_yaz(y['kullanilan']) or '', genislik=160, hiza='orta'),
            Sutun('Rapor', lambda y: y['RP'] or '', genislik=80, hiza='orta'),
            Sutun('Mazeret', lambda y: y['MZ'] or '', genislik=80, hiza='orta'),
            Sutun('Ücretsiz', lambda y: y['ÜZ'] or '', genislik=80, hiza='orta'),
            Sutun('İdari', lambda y: y['İD'] or '', genislik=80, hiza='orta'),
            Sutun('Kalan (yıl sonunda; bu yıl: bugün)', lambda y: sayi_yaz(y['kalan']) if isinstance(y['kalan'], (int, float)) else (y['kalan'] or ''),
                  hiza='orta', kalin=True),
        ])
        self.tv_yil, _ = tablo(self.m_yil)
        self.tv_yil.setSortingEnabled(False)
        l3.addWidget(tablo_karti(self.tv_yil), 1)
        l3.addWidget(etiket('Rapor, mazeret, ücretsiz ve idari izin takvim günü olarak gösterilir. Yıllık izinde Pazar ve resmi tatiller düşülmez.',
                            'SolukKucuk', True))
        self.sekme.addTab(w3, 'Yıllık özet')
        # notlar
        self.notlar = QTextBrowser()
        self.notlar.setOpenExternalLinks(False)
        self.notlar.setStyleSheet(f'QTextBrowser {{ background: white; border: 1px solid {T.CIZGI}; border-radius: 14px; padding: 14px; }}')
        self.sekme.addTab(self.notlar, 'Açıklamalar ve notlar')

    def goster(self, pid):
        self.pid = pid
        self.yenile()

    def yenile(self):
        ks = self.b.kisi(self.pid)
        p = self.b.personel(self.pid)
        if not ks or not p:
            return
        duzen_temizle(self.avatar_yer)
        self.avatar_yer.addWidget(Avatar(ks['ad'], 64))
        self.avatar_yer.addStretch(1)
        self.ad.setText(ks['ad'])
        duzen_temizle(self.rozetler)
        for m in [ks['durum'], p.get('teyit') or '']:
            if not m:
                continue
            z, y = durum_renk(m) or ('#EEF0F6', T.YAZI)
            lb = QLabel(m)
            lb.setStyleSheet(f'background: {z}; color: {y}; border-radius: 11px; padding: 3px 11px; font-weight: 600; font-size: 9pt;')
            self.rozetler.addWidget(lb)
        duzen_temizle(self.bilgi)
        dog = tarih_yaz(ks['dogum']) + (f'  ({ks["yas"]} yaş)' if ks['yas'] is not None else '') if ks['dogum'] else \
            (f'bilinmiyor — 50 yaş beyanı {tarih_yaz(ks["yas50"])}' if ks['yas50'] else 'bilinmiyor')
        donemler = '; '.join(f'{tarih_yaz(g)} – {tarih_yaz(c) if c else "devam ediyor"}' for g, c in ks['donemler']) or '—'
        bilgiler = [('Doğum tarihi', dog), ('Tamamlanan hizmet yılı', str(ks['kidem']) if ks['kidem'] is not None else '—'),
                    ('Çalışma dönemleri', donemler), ('Hesap tarihi', tarih_yaz(self.b.bugun))]
        for i, (e, v) in enumerate(bilgiler):
            a = etiket(e, 'SolukKucuk')
            b = etiket(v)
            b.setStyleSheet('font-weight: 600;')
            self.bilgi.addWidget(a, (i // 2) * 2, i % 2)
            self.bilgi.addWidget(b, (i // 2) * 2 + 1, i % 2)
        rk = kalan_renk(ks['kalan']) or ('', T.SOLUK)
        self.kalan.setText(f'{sayi_yaz(ks["kalan"])} gün' if ks['kalan'] is not None else '—')
        self.kalan.setStyleSheet(f'color: {rk[1]};')
        self.sonraki.setText(f'Sonraki hak: {tarih_yaz(ks["sonraki_tarih"])} · +{ks["sonraki_gun"]} gün' if ks['sonraki_tarih'] else
                             ('Ayrıldı — ödenmesi gereken: ' + sayi_yaz(ks['odenecek']) + ' gün' if not ks['aktif'] and ks['gecerli'] else ''))
        uy = ks['hatalar'] + ks['uyarilar']
        self.uyari.setText('\n'.join('• ' + u for u in uy))
        self.uyari.setObjectName('HataKutu' if ks['hatalar'] else 'UyariKutu')
        self.uyari.style().unpolish(self.uyari)
        self.uyari.style().polish(self.uyari)
        self.uyari.setVisible(bool(uy))
        dg = {'hak': ks['hak_son'], 'kul': ks['kul_son'], 'tas': ks['tasinan_eksi'] or None, 'duz': ks['duz'] or None,
              'onceki': ks['onceki_donem_kalan']}
        for a, (f, v) in self.mini.items():
            x = dg[a]
            v.setText(sayi_yaz(x) if x is not None else '—')
            f.setVisible(a in ('hak', 'kul') or x is not None)
        # izinler
        izinler = []
        for k in self.b.veri['izinler']:
            if k['personel_id'] != self.pid:
                continue
            r = dict(self.b.kayit(k['id']))
            r['aciklama'] = k.get('aciklama')
            izinler.append(r)
        izinler.sort(key=lambda r: (r['bas'] or __import__('datetime').date.min, r['no'] or 0), reverse=True)
        self.m_izin.doldur(izinler)
        self._izin_filtre()
        self.sekme.setTabText(0, f'İzin geçmişi ({sum(1 for r in izinler if not r["iptal"])})')
        self.m_hak.doldur(ks['hak_satirlari'])
        notlar = []
        if ks['yil_dokumu']:
            y = ks['yil_dokumu']
            if y['duzeltme'] > 0:
                notlar.append(f'Önce elle düzeltme ({sayi_yaz(y["duzeltme"])} gün) kullanılır; ondan kalan {sayi_yaz(y["duzeltme_kalan"])} gün.')
            elif y['duzeltme'] < 0:
                notlar.append(f'Elle düzeltme ({sayi_yaz(y["duzeltme"])} gün) kullanım gibi en eski haklardan düşüldü.')
            if y['tasinan_eksi'] < 0:
                notlar.append(f'Önceki dönem(ler)den taşınan eksi ({sayi_yaz(y["tasinan_eksi"])} gün) kullanım gibi en eski haklardan düşüldü.')
            if y['kalan'] < 0:
                notlar.append(f'Kalan eksi: bütün haklar kullanılmış, {sayi_yaz(-y["kalan"])} gün hak edilmeden (avans) kullanılmış.')
        self.hak_not.setText('Kullanılan izin önce en eski haktan düşülür. ' + ' '.join(notlar))
        self.m_yil.doldur(ks['yil_ozet'])
        html = [f'<h3 style="color:{T.LACI}">Not özeti</h3><p>{_metin_html(p.get("not_ozet")) or "<i>—</i>"}</p>']
        if p.get('duzeltme_aciklama') or ks['duz']:
            html.append(f'<h3 style="color:{T.LACI}">Elle düzeltme</h3><p><b>{sayi_yaz(ks["duz"])} gün</b> — {_metin_html(p.get("duzeltme_aciklama"))}</p>')
        if p.get('onceki_ad'):
            html.append(f'<h3 style="color:{T.LACI}">Önceki ad / diğer yazım</h3><p>{_metin_html(p["onceki_ad"])}</p>')
        html.append(f'<h3 style="color:{T.LACI}">Açıklamalar ve açık sorular</h3><p>{_metin_html(p.get("not_metni")) or "<i>—</i>"}</p>')
        self.notlar.setHtml('<div style="font-size:10pt; line-height:150%">' + ''.join(html) + '</div>')

    def _izin_filtre(self):
        yillik, iptal = self.sadece_yillik.isChecked(), self.iptaller.isChecked()
        self.px_izin.filtre_ayarla(lambda r: (not yillik or r['tur'] == 'Kİ') and (iptal or not r['iptal']))

    def _izin_ac(self, idx):
        r = idx.data(Qt.UserRole + 1)
        if r:
            izin_penceresi(self.b, self.window(), kayit_id=r['id'])

    def _duzenle(self):
        personel_penceresi(self.b, self.window(), self.pid)


def tur_renk_iptal(m, r):
    if m == 'İptal':
        return ('#ECEDF2', '#7A7E92')
    return tur_renk(m)


class PersonelSayfa(Sayfa):
    baslik = 'Personel'
    alt_baslik = 'Çalışanlar ve işten ayrılanlar. Kişinin izin kartını açmak için çift tıklayın.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        yeni = dugme('Yeni personel', 'arti', 'Vurgu')
        yeni.clicked.connect(self._yeni)
        self.ust.ekle(yeni)
        self.yigin = QStackedWidget()
        self.duzen.addWidget(self.yigin, 1)

        liste = QWidget()
        ld = QVBoxLayout(liste)
        ld.setContentsMargins(0, 0, 0, 0)
        ld.setSpacing(12)
        ust = QHBoxLayout()
        ust.setSpacing(6)
        self.grup = QButtonGroup(self)
        for ad, metin in (('calisan', 'Çalışanlar'), ('ayrilan', 'Ayrılanlar'), ('hepsi', 'Tümü')):
            b = dugme(metin, tur='Secmeli')
            b.setCheckable(True)
            b.setProperty('ad', ad)
            self.grup.addButton(b)
            ust.addWidget(b)
            if ad == 'calisan':
                b.setChecked(True)
        self.grup.buttonClicked.connect(lambda _: self._filtre())
        ust.addStretch(1)
        self.arama = AramaKutusu('Ad ara…')
        self.arama.textChanged.connect(self._filtre)
        ust.addWidget(self.arama)
        ld.addLayout(ust)
        self.model = ListeModeli([
            Sutun('Ad Soyad', lambda k: k['ad'], sirala=lambda k: tr_anahtar(k['ad']), genislik=230, kalin=True),
            Sutun('Durum', lambda k: k['durum'], genislik=110, tur='rozet'),
            Sutun('Doğum tarihi', lambda k: tarih_yaz(k['dogum']) if k['dogum'] else ('50+ beyanı' if k['yas50'] else '—'),
                  sirala=lambda k: k['dogum'], genislik=104, hiza='orta'),
            Sutun('Yaş', lambda k: k['yas'] if k['yas'] is not None else '', genislik=50, hiza='orta'),
            Sutun('İşe giriş', lambda k: tarih_yaz(k['son_giris']), sirala=lambda k: k['son_giris'], genislik=100, hiza='orta'),
            Sutun('Çıkış', lambda k: tarih_yaz(k['son_cikis']), sirala=lambda k: k['son_cikis'], genislik=96, hiza='orta'),
            Sutun('Hizmet yılı', lambda k: k['kidem'] if k['kidem'] is not None else '', genislik=84, hiza='orta'),
            Sutun('Teyit', lambda k: k.get('teyit') or '', genislik=150, tur='rozet'),
            Sutun('Kalan', lambda k: sayi_yaz(k['kalan']), sirala=lambda k: k['kalan'] if k['kalan'] is not None else -10 ** 6,
                  genislik=90, hiza='orta', tur='kalan'),
            Sutun('Sonraki hak', lambda k: (f'{tarih_yaz(k["sonraki_tarih"])}  (+{k["sonraki_gun"]})' if k['sonraki_tarih'] else ''),
                  sirala=lambda k: k['sonraki_tarih'], genislik=150, hiza='orta', gerilsin=True),
        ])
        self.tv, self.proxy = tablo(self.model)
        for i, s in enumerate(self.model.sutunlar):
            if s.tur == 'rozet':
                self.tv.setItemDelegateForColumn(i, RozetDelegate(durum_renk, parent=self.tv))
            elif s.tur == 'kalan':
                self.tv.setItemDelegateForColumn(i, KalanDelegate(lambda k: k['kalan'], parent=self.tv))
        self.tv.doubleClicked.connect(lambda idx: self.ac(idx.data(Qt.UserRole + 1)['id']))
        self.tv.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tv.customContextMenuRequested.connect(self._menu)
        ld.addWidget(tablo_karti(self.tv), 1)
        self.sayac = etiket('', 'SolukKucuk')
        ld.addWidget(self.sayac)
        self.yigin.addWidget(liste)
        self.kart = KartGorunumu(baglam, self._listeye)
        self.yigin.addWidget(self.kart)

    def _listeye(self):
        self.yigin.setCurrentIndex(0)
        self.ust.show()

    def ac(self, pid):
        if pid is None:
            self._listeye()
            return
        self.kart.goster(pid)
        self.yigin.setCurrentIndex(1)
        self.ust.hide()

    def _yeni(self):
        pid = personel_penceresi(self.b, self.window())
        if pid:
            self.ac(pid)

    def _menu(self, poz):
        k = secili_satir(self.tv)
        if not k:
            return
        m = QMenu(self)
        m.addAction('İzin kartını aç', lambda: self.ac(k['id']))
        m.addAction('Bilgileri düzenle', lambda: personel_penceresi(self.b, self.window(), k['id']))
        m.addAction('Yeni izin', lambda: izin_penceresi(self.b, self.window(), personel_id=k['id']))
        m.addSeparator()
        m.addAction('İzin kartı (PDF / yazdır)', lambda: self.b.git.emit('pdf_kart', k['id']))
        m.exec(self.tv.viewport().mapToGlobal(poz))

    def _filtre(self):
        b = self.grup.checkedButton()
        ad = b.property('ad') if b else 'hepsi'
        q = self.arama.text()
        self.proxy.filtre_ayarla(lambda k: ara_eslesir(q, k['ad'], k.get('onceki_ad')) and
                                 (ad == 'hepsi' or (ad == 'calisan') == bool(k['aktif'] or not k['gecerli'])))
        self.tv.setColumnHidden(5, ad == 'calisan')  # Çıkış: çalışanlarda boş
        self.sayac.setText(f'{self.proxy.rowCount()} kişi gösteriliyor')

    def yenile(self):
        pmap = {p['id']: p for p in self.b.veri['personel']}
        satirlar = []
        for k in self.b.sonuc.sirali:
            k = dict(k)
            k['teyit'] = pmap[k['id']].get('teyit')
            k['onceki_ad'] = pmap[k['id']].get('onceki_ad')
            satirlar.append(k)
        self.model.doldur(satirlar)
        self._filtre()
        if self.yigin.currentIndex() == 1 and self.kart.pid:
            if self.b.kisi(self.kart.pid):
                self.kart.yenile()
            else:
                self._listeye()
