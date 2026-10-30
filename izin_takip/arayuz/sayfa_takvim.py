# -*- coding: utf-8 -*-
"""Aylık izin takvimi: kişi × gün, izin türüne göre renkli; Pazar ve resmi tatiller gölgeli. Çift tıklayınca izin açılır / girilir."""
import datetime

from PySide6.QtCore import QAbstractTableModel, QModelIndex, QRect, QRectF, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel, QStyle, QStyledItemDelegate, QTableView)

from . import tema as T
from .bilesenler import AramaKutusu, dugme, etiket, tablo_karti
from .dialog_izin import izin_penceresi
from .sayfa import Sayfa
from .. import motor
from ..yardimci import AYLAR, GUN_ADLARI, GUN_KISA, KOD_AD, KOD_RENK, ara_eslesir, sayi_yaz, tarih_yaz

OZET = [('Kİ', 'Yıllık'), ('kalan', 'Kalan')]
PAZAR, TATIL, YARIM = '#ECEEF4', '#FDE7D8', '#FEF3EA'


class TakvimModeli(QAbstractTableModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.gunler, self.satirlar, self.tatil, self.bugun, self.izin = [], [], {}, None, {}

    def doldur(self, gunler, satirlar, tatil, bugun, izin):
        self.beginResetModel()
        self.gunler, self.satirlar, self.tatil, self.bugun, self.izin = gunler, satirlar, tatil, bugun, izin
        self.endResetModel()

    def rowCount(self, p=QModelIndex()):
        return len(self.satirlar)

    def columnCount(self, p=QModelIndex()):
        return len(self.gunler) + len(OZET)

    def gun(self, c):
        return self.gunler[c] if c < len(self.gunler) else None

    def headerData(self, i, yon, rol=Qt.DisplayRole):
        if yon == Qt.Vertical:
            if rol == Qt.DisplayRole:
                return self.satirlar[i]['kisi']['ad']
            if rol == Qt.ToolTipRole:
                k = self.satirlar[i]['kisi']
                return f'{k["ad"]} — kalan {sayi_yaz(k["kalan"])} gün'
            return None
        if rol == Qt.ToolTipRole:
            g = self.gun(i)
            if g is None:
                return {'Kİ': 'Bu ay yıllık izinden düşülen gün (Pazar/tatil hariç)', 'kalan': 'Kalan yıllık izin (hesap tarihinde)'}.get(
                    OZET[i - len(self.gunler)][0], 'Bu ay takvim günü')
            t = self.tatil.get(g)
            n = sum(1 for s in self.satirlar if s['hucre'][i] == 'Kİ')
            return f'{GUN_ADLARI[g.weekday()]} {tarih_yaz(g)}' + (f'\n{t["ad"]} ({"yarım gün" if t["tur"] == "yarim" else "resmi tatil"})' if t else '') + \
                (f'\n{n} kişi yıllık izinde' if n else '')
        return None

    def data(self, idx, rol=Qt.DisplayRole):
        if not idx.isValid():
            return None
        s = self.satirlar[idx.row()]
        c = idx.column()
        g = self.gun(c)
        if rol == Qt.DisplayRole:
            if g is not None:
                return s['hucre'][c]
            a = OZET[c - len(self.gunler)][0]
            if a == 'kalan':
                return sayi_yaz(s['kisi']['kalan'])
            return sayi_yaz(s['ozet'].get(a)) if s['ozet'].get(a) else ''
        if rol == Qt.ToolTipRole and g is not None:
            k = s['hucre'][c]
            metin = f'{s["kisi"]["ad"]}\n{GUN_ADLARI[g.weekday()]} {tarih_yaz(g)}'
            kid = s['kayit'][c]
            if kid:
                r = self.izin.get(kid)
                if r:
                    metin += f'\n{"Aynı güne iki kayıt! " if k == "!!" else ""}{motor.kayit_metni(r)} (No {r["no"]})'
                    if r.get('aciklama'):
                        metin += f'\n{r["aciklama"]}'
            elif k == '–':
                metin += '\nÇalışma dönemi dışında'
            t = self.tatil.get(g)
            if t:
                metin += f'\n{t["ad"]}'
            return metin
        return None


class TakvimBaslik(QHeaderView):
    def __init__(self, model, parent=None):
        super().__init__(Qt.Horizontal, parent)
        self.m = model
        self.setSectionsClickable(False)
        self.setMinimumHeight(46)
        self.setDefaultAlignment(Qt.AlignCenter)

    def sizeHint(self):
        s = super().sizeHint()
        return QSize(s.width(), 48)

    def paintSection(self, p, rect, i):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        g = self.m.gun(i)
        zemin = '#FAFBFD'
        if g is not None:
            t = self.m.tatil.get(g)
            if g.weekday() == 6:
                zemin = PAZAR
            elif t and t['tur'] == 'tam':
                zemin = TATIL
            elif t:
                zemin = YARIM
        p.fillRect(rect, QColor(zemin))
        p.setPen(QPen(QColor(T.CIZGI), 1))
        p.drawLine(rect.bottomLeft(), rect.bottomRight())
        if g is None:
            p.setPen(QColor(T.SOLUK))
            p.setFont(T.font(8, True))
            p.drawText(rect, Qt.AlignCenter, OZET[i - len(self.m.gunler)][1].upper())
        else:
            bugun = g == self.m.bugun
            ust = QRect(rect.left(), rect.top() + 5, rect.width(), 20)
            if bugun:
                r = QRectF(rect.center().x() - 12, rect.top() + 3, 24, 24)
                yol = QPainterPath()
                yol.addEllipse(r)
                p.fillPath(yol, QColor(T.TURUNCU))
                p.setPen(QColor('white'))
            else:
                p.setPen(QColor(T.YAZI))
            p.setFont(T.font(9.5, True))
            p.drawText(ust if not bugun else QRect(int(r.left()), int(r.top()), 24, 24), Qt.AlignCenter, str(g.day))
            p.setPen(QColor(T.TURUNCU_2 if self.m.tatil.get(g) else T.SOLUK))
            p.setFont(T.font(7.5, False))
            p.drawText(QRect(rect.left(), rect.top() + 27, rect.width(), 16), Qt.AlignCenter, GUN_KISA[g.weekday()])
        p.restore()


class TakvimDelegate(QStyledItemDelegate):
    def __init__(self, model, parent=None):
        super().__init__(parent)
        self.m = model

    def paint(self, p, opt, idx):
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        c = idx.column()
        g = self.m.gun(c)
        rect = opt.rect
        if g is None:
            p.fillRect(rect, QColor('#FAFBFD'))
            metin = idx.data()
            a = OZET[c - len(self.m.gunler)][0]
            if a == 'kalan':
                v = self.m.satirlar[idx.row()]['kisi']['kalan']
                p.setPen(QColor(T.KIRMIZI if (v or 0) < 0 else T.YAZI))
                p.setFont(T.font(9.5, True))
            else:
                p.setPen(QColor(T.YAZI))
                p.setFont(T.font(9.5))
            p.drawText(rect, Qt.AlignCenter, metin or '')
        else:
            t = self.m.tatil.get(g)
            zemin = PAZAR if g.weekday() == 6 else (TATIL if t and t['tur'] == 'tam' else (YARIM if t else '#FFFFFF'))
            p.fillRect(rect, QColor(zemin))
            k = idx.data()
            ic = QRectF(rect).adjusted(2.5, 3.5, -2.5, -3.5)
            yol = QPainterPath()
            yol.addRoundedRect(ic, 6, 6)
            if k in KOD_RENK:
                z, y = KOD_RENK[k]
                p.fillPath(yol, QColor(z))
                p.setPen(QPen(QColor(y), 1))
                p.drawPath(yol)
                p.setPen(QColor(y))
                p.setFont(T.font(7.5, True))
                p.drawText(ic, Qt.AlignCenter, k)
            elif k == '!!':
                p.fillPath(yol, QColor(T.KIRMIZI))
                p.setPen(QColor('white'))
                p.setFont(T.font(8, True))
                p.drawText(ic, Qt.AlignCenter, '!!')
            elif k == '–':
                p.fillPath(yol, QColor('#F1F2F6'))
            if g == self.m.bugun:
                p.setPen(QPen(QColor(T.TURUNCU), 1.4))
                p.drawLine(rect.topLeft(), rect.bottomLeft())
                p.drawLine(rect.topRight(), rect.bottomRight())
            if opt.state & QStyle.State_MouseOver:
                p.setPen(QPen(QColor(T.LACI_3), 1.2))
                p.drawRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 5, 5)
        p.setPen(QPen(QColor('#F0F1F6'), 1))
        p.drawLine(rect.bottomLeft(), rect.bottomRight())
        p.restore()


class TakvimSayfa(Sayfa):
    baslik = 'Takvim'
    alt_baslik = 'Kim hangi gün izinli. Bir güne çift tıklayın: izin varsa açılır, yoksa o gün için yeni izin girilir.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        pdf = dugme('Yazdır / PDF', 'yazdir', ipucu='Bu ayın takvimini A4 yatay PDF olarak kaydeder ya da yazdırır')
        pdf.clicked.connect(lambda: self.b.git.emit('pdf_takvim', (self.yil, self.ay)))
        yeni = dugme('Yeni izin', 'arti', 'Vurgu')
        yeni.clicked.connect(lambda: izin_penceresi(self.b, self.window()))
        self.ust.ekle(pdf)
        self.ust.ekle(yeni)
        bugun = datetime.date.today()
        self.yil, self.ay = bugun.year, bugun.month

        ust = QHBoxLayout()
        ust.setSpacing(8)
        geri = dugme('', 'sol', ipucu='Önceki ay')
        geri.clicked.connect(lambda: self._kaydir(-1))
        ileri = dugme('', 'sag', ipucu='Sonraki ay')
        ileri.clicked.connect(lambda: self._kaydir(1))
        self.ay_etiket = etiket('', 'BolumBaslik')
        self.ay_etiket.setMinimumWidth(150)
        self.ay_etiket.setAlignment(Qt.AlignCenter)
        bu_ay = dugme('Bu ay')
        bu_ay.clicked.connect(self._bu_ay)
        for w in (geri, self.ay_etiket, ileri, bu_ay):
            ust.addWidget(w)
        ust.addStretch(1)
        self.arama = AramaKutusu('Ad ara…')
        self.arama.setMaximumWidth(260)
        self.arama.textChanged.connect(self._filtre)
        ust.addWidget(self.arama)
        self.duzen.addLayout(ust)
        lej = QHBoxLayout()
        lej.setSpacing(6)
        for k in ('Kİ', 'RP', 'MZ', 'ÜZ', 'İD'):
            z, y = KOD_RENK[k]
            lb = QLabel(f' {k} ')
            lb.setStyleSheet(f'background: {z}; color: {y}; border: 1px solid {y}; border-radius: 6px; font-weight: 700; font-size: 8pt; padding: 1px 3px;')
            lej.addWidget(lb)
            lej.addWidget(etiket(KOD_AD[k], 'SolukKucuk'))
            lej.addSpacing(8)
        for renk, ad in ((PAZAR, 'Pazar'), (TATIL, 'Resmi tatil'), ('#F1F2F6', 'Çalışmıyor')):
            lb = QLabel()
            lb.setFixedSize(16, 16)
            lb.setStyleSheet(f'background: {renk}; border-radius: 4px; border: 1px solid {T.CIZGI};')
            lej.addWidget(lb)
            lej.addWidget(etiket(ad, 'SolukKucuk'))
            lej.addSpacing(8)
        lej.addStretch(1)
        self.duzen.addLayout(lej)

        self.model = TakvimModeli(self)
        self.tv = QTableView()
        self.tv.setModel(self.model)
        self.tv.setHorizontalHeader(TakvimBaslik(self.model, self.tv))
        self.tv.setItemDelegate(TakvimDelegate(self.model, self.tv))
        self.tv.setShowGrid(False)
        self.tv.setMouseTracking(True)
        self.tv.setSelectionMode(QAbstractItemView.NoSelection)
        self.tv.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tv.verticalHeader().setDefaultSectionSize(34)
        self.tv.verticalHeader().setFixedWidth(196)
        self.tv.verticalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.tv.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.tv.horizontalHeader().setMinimumSectionSize(20)
        self.tv.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.tv.doubleClicked.connect(self._cift)
        self.duzen.addWidget(tablo_karti(self.tv), 1)
        self.alt = etiket('', 'SolukKucuk')
        self.duzen.addWidget(self.alt)

    def _genislik(self):
        n = len(self.model.gunler)
        if not n:
            return
        bos = (self.tv.width() - self.tv.verticalHeader().width() - 18) if self.tv.width() > 400 else (self.width() - 320)
        g = max(23, int((bos - 60 * len(OZET)) / n))
        for c in range(n):
            self.tv.setColumnWidth(c, g)
        for j in range(len(OZET)):
            self.tv.setColumnWidth(n + j, 60)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._genislik()

    def showEvent(self, e):
        super().showEvent(e)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, self._genislik)

    def _kaydir(self, n):
        m = self.yil * 12 + (self.ay - 1) + n
        self.yil, self.ay = divmod(m, 12)
        self.ay += 1
        self.yenile()

    def _bu_ay(self):
        self.yil, self.ay = self.b.bugun.year, self.b.bugun.month
        self.yenile()

    def _cift(self, idx):
        if not idx.isValid():
            return
        s = self.model.satirlar[idx.row()]
        g = self.model.gun(idx.column())
        if g is None:
            self.b.git.emit('kart', s['kisi']['id'])
            return
        kid = s['kayit'][idx.column()]
        if kid:
            izin_penceresi(self.b, self.window(), kayit_id=kid)
        else:
            izin_penceresi(self.b, self.window(), personel_id=s['kisi']['id'], tarih=g)

    def _filtre(self):
        q = self.arama.text()
        for i, s in enumerate(self.model.satirlar):
            self.tv.setRowHidden(i, not ara_eslesir(q, s['kisi']['ad']))

    def yenile(self):
        gunler, satirlar = motor.takvim(self.b.sonuc, self.b.veri, self.yil, self.ay)
        izin = {k['id']: k for k in self.b.veri['izinler']}
        self.model.doldur(gunler, satirlar, self.b.sonuc.tatil, self.b.bugun, izin)
        self.ay_etiket.setText(f'{AYLAR[self.ay - 1]} {self.yil}')
        self._genislik()
        self._filtre()
        izinli = sum(1 for s in satirlar if any(h in KOD_RENK or h == '!!' for h in s['hucre']))
        dus = sum(s['ozet'].get('Kİ', 0) for s in satirlar)
        tatiller = [f'{g.day} {AYLAR[g.month - 1]} {self.b.sonuc.tatil[g]["ad"]}' for g in gunler if g in self.b.sonuc.tatil]
        self.alt.setText(f'{len(satirlar)} kişi · bu ay {izinli} kişi izin kullandı · yıllık izinden düşülen toplam {sayi_yaz(dus)} gün'
                         + (f' · Tatiller: {"; ".join(tatiller)}' if tatiller else ''))
