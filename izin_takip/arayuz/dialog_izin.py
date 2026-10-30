# -*- coding: utf-8 -*-
"""İzin ekleme / düzenleme penceresi: yazarken düşülecek gün, işe dönüş ve kalan izin canlı hesaplanır."""
import datetime

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QButtonGroup, QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
                               QVBoxLayout, QWidget)

from . import tema as T
from .bilesenler import TarihKutusu, ayirici, dugme, etiket, hata, soru
from .ikonlar import pixmap
from .secici import KisiSecici
from .. import motor
from ..veritabani import VeriHatasi
from ..yardimci import GUN_ADLARI, KOD_AD, KOD_RENK, KODLAR, gunler, sayi_yaz, tarih_yaz, tr_anahtar


class IzinDialog(QDialog):
    def __init__(self, baglam, kayit_id=None, personel_id=None, tarih=None, parent=None):
        super().__init__(parent)
        self.b = baglam
        self.kid = kayit_id
        self.kayit = baglam.izin(kayit_id) if kayit_id else None
        self.setWindowTitle('İzni düzenle' if self.kayit else 'Yeni izin')
        self.setModal(True)
        self.setMinimumWidth(860)
        self.sonuc_kodu = None

        ana = QVBoxLayout(self)
        ana.setContentsMargins(26, 22, 26, 20)
        ana.setSpacing(16)
        baslik = etiket('İzni düzenle' if self.kayit else 'Yeni izin kaydı', 'SayfaBaslik')
        alt = etiket(f'Kayıt No {self.kayit["no"]} · giren: {self.kayit.get("giren") or "—"} · '
                     f'{tarih_yaz(self.kayit.get("yazildigi")) or ""}' if self.kayit else
                     'Personeli, izin türünü ve tarihleri seçin; düşülecek gün ve kalan izin sağda hemen hesaplanır.', 'SayfaAlt')
        ana.addWidget(baslik)
        ana.addWidget(alt)

        govde = QHBoxLayout()
        govde.setSpacing(20)
        ana.addLayout(govde, 1)

        # ---------------- form
        form = QVBoxLayout()
        form.setSpacing(8)
        govde.addLayout(form, 3)
        form.addWidget(etiket('Personel', 'BolumBaslik'))
        self.kisi = KisiSecici()
        kisiler = sorted(baglam.sonuc.kisi.values(), key=lambda k: (0 if k['aktif'] else 1, tr_anahtar(k['ad'])))
        self.kisi.doldur([(k['id'], k['ad'] + ('' if k['aktif'] else '  (ayrıldı)')) for k in kisiler])
        form.addWidget(self.kisi)
        self.kisi_bilgi = etiket('', 'SolukKucuk')
        form.addWidget(self.kisi_bilgi)
        form.addSpacing(6)

        form.addWidget(etiket('İzin türü', 'BolumBaslik'))
        turler = QHBoxLayout()
        turler.setSpacing(6)
        self.tur_grup = QButtonGroup(self)
        self.tur_grup.setExclusive(True)
        for k in KODLAR:
            b = QPushButton(KOD_AD[k])
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            z, y = KOD_RENK[k]
            b.setStyleSheet(f'QPushButton {{ border-radius: 16px; padding: 7px 12px; color: {T.SOLUK}; }}'
                            f'QPushButton:checked {{ background: {z}; color: {y}; border: 1.5px solid {y}; }}')
            b.setProperty('kod', k)
            self.tur_grup.addButton(b)
            turler.addWidget(b)
        turler.addStretch(1)
        form.addLayout(turler)
        self.tur_aciklama = etiket('', 'SolukKucuk', True)
        form.addWidget(self.tur_aciklama)
        form.addSpacing(6)

        form.addWidget(etiket('Tarihler', 'BolumBaslik'))
        tg = QGridLayout()
        tg.setHorizontalSpacing(12)
        tg.setVerticalSpacing(4)
        tg.addWidget(etiket('Başlangıç', 'SolukKucuk'), 0, 0)
        tg.addWidget(etiket('Bitiş (tek günlük izinde boş bırakın)', 'SolukKucuk'), 0, 1)
        self.bas = TarihKutusu(bos_olabilir=False)
        self.bit = TarihKutusu()
        self.bas.setMaximumWidth(190)
        self.bit.setMaximumWidth(190)
        tg.addWidget(self.bas, 1, 0)
        tg.addWidget(self.bit, 1, 1)
        tg.setColumnStretch(2, 1)
        form.addLayout(tg)
        form.addSpacing(6)
        form.addWidget(etiket('Açıklama (isteğe bağlı)', 'BolumBaslik'))
        self.aciklama = QLineEdit()
        self.aciklama.setPlaceholderText('ör. Bayram öncesi, yol izni dahil değil…')
        form.addWidget(self.aciklama)
        form.addStretch(1)

        # ---------------- önizleme
        oz = QFrame()
        oz.setObjectName('OnizlemeKutu')
        oz.setMinimumWidth(320)
        od = QVBoxLayout(oz)
        od.setContentsMargins(18, 16, 18, 16)
        od.setSpacing(6)
        od.addWidget(etiket('ÖZET', 'KpiEtiket'))
        self.o_buyuk = etiket('—', 'KpiDeger')
        self.o_buyuk_alt = etiket('Yıllık izinden düşülecek', 'SolukKucuk')
        od.addWidget(self.o_buyuk)
        od.addWidget(self.o_buyuk_alt)
        od.addSpacing(6)
        od.addWidget(ayirici())
        self.o_satirlar = {}
        for anahtar, e in (('takvim', 'Takvim günü'), ('isbasi', 'İşe dönüş'),
                           ('once', 'Bu izin olmadan kalan' if self.kayit else 'Şu anki kalan izin'), ('sonra', 'Bu izinle kalan')):
            sat = QHBoxLayout()
            sat.addWidget(etiket(e, 'Soluk'))
            sat.addStretch(1)
            v = etiket('—')
            v.setStyleSheet('font-weight: 600;')
            sat.addWidget(v)
            od.addLayout(sat)
            self.o_satirlar[anahtar] = v
        od.addSpacing(4)
        self.o_uyari = QLabel()
        self.o_uyari.setObjectName('UyariKutu')
        self.o_uyari.setWordWrap(True)
        self.o_uyari.setContentsMargins(10, 8, 10, 8)
        self.o_uyari.hide()
        od.addWidget(self.o_uyari)
        od.addStretch(1)
        govde.addWidget(oz, 2)

        # ---------------- düğmeler
        alt_d = QHBoxLayout()
        alt_d.setSpacing(8)
        if self.kayit:
            self.iptal_d = dugme('İptali geri al' if self.kayit['iptal'] else 'İzni iptal et', 'geri_al' if self.kayit['iptal'] else 'iptal',
                                 ipucu='İptal edilen izin hesaptan çıkar ama geçmişte üstü çizili görünür.')
            self.iptal_d.clicked.connect(self._iptal)
            alt_d.addWidget(self.iptal_d)
            sil = dugme('Sil', 'sil', 'Tehlike', 'Yanlışlıkla girilen kaydı tamamen siler.')
            sil.clicked.connect(self._sil)
            alt_d.addWidget(sil)
        alt_d.addStretch(1)
        vazgec = dugme('Vazgeç')
        vazgec.clicked.connect(self.reject)
        self.kaydet_d = dugme('Kaydet', 'onay', 'Vurgu')
        self.kaydet_d.setDefault(True)
        self.kaydet_d.clicked.connect(self._kaydet)
        alt_d.addWidget(vazgec)
        alt_d.addWidget(self.kaydet_d)
        ana.addLayout(alt_d)

        # ---------------- doldur
        self._zaman = QTimer(self)
        self._zaman.setSingleShot(True)
        self._zaman.setInterval(120)
        self._zaman.timeout.connect(self._onizle)
        k = self.kayit
        if k:
            self.kisi.sec(k['personel_id'])
            self._tur_sec(k['tur'])
            self.bas.setTarih(k['bas'])
            self.bit.setTarih(k['bit'])
            self.aciklama.setText(k.get('aciklama') or '')
        else:
            if personel_id:
                self.kisi.sec(personel_id)
            self._tur_sec('Kİ')
            if tarih:
                self.bas.setTarih(tarih)
        self.kisi.secildi.connect(lambda _: self._zaman.start())
        self.kisi.lineEdit().textChanged.connect(lambda _: self._zaman.start())
        self.tur_grup.buttonClicked.connect(lambda _: self._zaman.start())
        self.bas.degisti.connect(self._zaman.start)
        self.bit.degisti.connect(self._zaman.start)
        self._onizle()
        if not personel_id and not k:
            self.kisi.setFocus()
        else:
            self.bas.setFocus()

    # ------------------------------------------------------------------ yardımcılar
    def _tur_sec(self, kod):
        for b in self.tur_grup.buttons():
            b.setChecked(b.property('kod') == kod)

    def _tur(self):
        b = self.tur_grup.checkedButton()
        return b.property('kod') if b else None

    def _taslak(self):
        try:
            bas, bit = self.bas.tarih(), self.bit.tarih()
        except ValueError:
            return None
        return {'id': -1 if not self.kid else self.kid, 'no': (self.kayit or {}).get('no') or 10 ** 9, 'personel_id': self.kisi.secili(),
                'tur': self._tur(), 'bas': bas, 'bit': bit if bit and bit != bas else None, 'iptal': False,
                'aciklama': self.aciklama.text().strip()}

    def _onizle(self):
        tur = self._tur()
        aciklama = {'Kİ': 'Yıllık izinden düşülür. Pazar ve resmi tatiller sayılmaz; arife ve 28 Ekim yarım gün.',
                    'RP': 'Yıllık izinden düşülmez. Uzun raporda md.55/a sınırı kontrol edilir.',
                    'MZ': 'Yıllık izinden düşülmez.',
                    'ÜZ': 'Yıllık izinden düşülmez; izne hak kazanma tarihini öteler (md.55).',
                    'İD': 'Yıllık izinden düşülmez (şirketin verdiği bayram/köprü izni).'}.get(tur, '')
        self.tur_aciklama.setText(aciklama)
        pid = self.kisi.secili()
        ks = self.b.kisi(pid) if pid else None
        if ks:
            bilgi = [ks['durum']]
            if ks['son_giris']:
                bilgi.append(f'işe giriş {tarih_yaz(ks["son_giris"])}')
            if ks['kalan'] is not None:
                bilgi.append(f'kalan {sayi_yaz(ks["kalan"])} gün')
            if ks['sonraki_tarih']:
                bilgi.append(f'sonraki hak {tarih_yaz(ks["sonraki_tarih"])} (+{ks["sonraki_gun"]})')
            self.kisi_bilgi.setText(' · '.join(bilgi))
        else:
            self.kisi_bilgi.setText('')
        t = self._taslak()
        s = self.o_satirlar
        if not t or not t['bas'] or not tur:
            self.o_buyuk.setText('—')
            self.o_buyuk.setStyleSheet('')
            for v in s.values():
                v.setText('—')
            self.o_uyari.hide()
            self.o_buyuk_alt.setText('Yıllık izinden düşülecek')
            return
        bit = t['bit'] or t['bas']
        if bit < t['bas']:
            self._uyari(['Bitiş tarihi başlangıçtan önce.'], hata_mi=True)
            self.o_buyuk.setText('—')
            return
        tatil = self.b.sonuc.tatil
        pazar = sum(1 for g in gunler(t['bas'], bit) if g.weekday() == 6)
        resmi = sum(1 for g in gunler(t['bas'], bit) if (tatil.get(g) or {}).get('tur') == 'tam' and g.weekday() != 6)
        yarim = sum(1 for g in gunler(t['bas'], bit) if (tatil.get(g) or {}).get('tur') == 'yarim' and g.weekday() != 6)
        ek = []
        if pazar:
            ek.append(f'{pazar} Pazar')
        if resmi:
            ek.append(f'{resmi} resmi tatil')
        if yarim:
            ek.append(f'{yarim} yarım gün')
        takvim_g = (bit - t['bas']).days + 1
        s['takvim'].setText(f'{takvim_g} gün' + (f'  ({", ".join(ek)})' if ek else ''))
        donus = motor.is_basi(bit, tatil)
        s['isbasi'].setText(f'{GUN_ADLARI[donus.weekday()]} {tarih_yaz(donus)}')
        if not pid:
            dus = sum(motor.gun_agirligi(g, tatil) for g in gunler(t['bas'], bit))
            self.o_buyuk.setText(f'{sayi_yaz(dus)} gün' if tur == 'Kİ' else 'Düşülmez')
            self.o_buyuk.setStyleSheet('')
            s['once'].setText('—')
            s['sonra'].setText('—')
            self._uyari(['Personeli seçin.'])
            return
        once_ks, _ = motor.tek_kisi(self.b.veri, pid, self.b.bugun, cikar_id=self.kid)
        sonra_ks, kr = motor.tek_kisi(self.b.veri, pid, self.b.bugun, ek_kayit=t, cikar_id=self.kid)
        r = kr.get(t['id'])
        if tur == 'Kİ':
            dus = r['dusulen'] if r and r['dusulen'] is not None else sum(motor.gun_agirligi(g, tatil) for g in gunler(t['bas'], bit))
            self.o_buyuk.setText(f'{sayi_yaz(dus)} gün')
            self.o_buyuk.setStyleSheet(f'color: {T.LACI};')
            self.o_buyuk_alt.setText('Yıllık izinden düşülecek')
        else:
            self.o_buyuk.setText('Düşülmez')
            self.o_buyuk.setStyleSheet(f'color: {T.SOLUK};')
            self.o_buyuk_alt.setText(f'{KOD_AD[tur]} yıllık izinden düşülmez')
        s['once'].setText(f'{sayi_yaz(once_ks["kalan"])} gün' if once_ks['kalan'] is not None else '—')
        sk = sonra_ks['kalan']
        s['sonra'].setText(f'{sayi_yaz(sk)} gün' if sk is not None else '—')
        s['sonra'].setStyleSheet(f'font-weight: 700; color: {T.KIRMIZI if (sk or 0) < 0 else T.YESIL};')
        uy = list(r['uyarilar']) if r else []
        if once_ks['hatalar']:
            uy.insert(0, 'Personel bilgisi eksik/hatalı: ' + '; '.join(once_ks['hatalar']))
        if t['bas'] > self.b.bugun and tur == 'Kİ':
            uy.append('İleri tarihli izin: girildiği anda kalandan düşülür.')
        self._uyari(uy)

    def _uyari(self, uy, hata_mi=False):
        if not uy:
            self.o_uyari.hide()
            return
        self.o_uyari.setObjectName('HataKutu' if hata_mi else 'UyariKutu')
        self.o_uyari.style().unpolish(self.o_uyari)
        self.o_uyari.style().polish(self.o_uyari)
        self.o_uyari.setText('\n'.join('• ' + u for u in uy))
        self.o_uyari.show()

    # ------------------------------------------------------------------ işlemler
    def _kaydet(self):
        if not self.bas.gecerli() or not self.bit.gecerli():
            hata(self, 'Tarih anlaşılamadı. Gün.ay.yıl biçiminde yazın (ör. 25.09.2026) ya da takvimden seçin.')
            return
        t = self._taslak()
        if not t['personel_id']:
            hata(self, 'Listeden bir personel seçin.')
            return
        try:
            yeni = dict(t)
            yeni.pop('id')
            if not self.kid:
                yeni.pop('no')
            else:
                yeni['iptal'] = self.kayit['iptal']
            self.b.db.izin_kaydet(yeni, self.kid)
        except VeriHatasi as e:
            hata(self, str(e))
            return
        self.sonuc_kodu = 'kaydedildi'
        self.accept()

    def _iptal(self):
        iptal = not self.kayit['iptal']
        if iptal and not soru(self, 'İzni iptal et', 'Bu izin iptal edilsin mi?\n\nİptal edilen izin hesaptan çıkar; kayıt silinmez, '
                                                     'listede üstü çizili görünür ve istenirse geri alınabilir.', 'İptal et'):
            return
        self.b.db.izin_iptal(self.kid, iptal)
        self.sonuc_kodu = 'iptal' if iptal else 'iptal_geri'
        self.accept()

    def _sil(self):
        if not soru(self, 'Kaydı sil', f'Kayıt No {self.kayit["no"]} tamamen silinsin mi?\n\nYalnız yanlışlıkla girilen kayıtlar için '
                                       f'kullanın. Vazgeçilen izinler için "İzni iptal et" daha doğrudur (geçmiş korunur).',
                    'Sil', tehlikeli=True):
            return
        self.b.db.izin_sil(self.kid)
        self.sonuc_kodu = 'silindi'
        self.accept()


def izin_penceresi(baglam, parent, kayit_id=None, personel_id=None, tarih=None):
    d = IzinDialog(baglam, kayit_id, personel_id, tarih, parent)
    if d.exec() and d.sonuc_kodu:
        baglam.yenile({'kaydedildi': 'İzin kaydedildi', 'iptal': 'İzin iptal edildi', 'iptal_geri': 'İptal geri alındı',
                       'silindi': 'Kayıt silindi'}[d.sonuc_kodu])
        return True
    return False
