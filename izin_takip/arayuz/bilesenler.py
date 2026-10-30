# -*- coding: utf-8 -*-
"""Ortak arayüz parçaları: kart, gösterge kartı, sayfa başlığı, arama kutusu, tarih kutusu, tablo modeli ve rozetler, bildirim."""
import datetime

from PySide6.QtCore import (QAbstractTableModel, QDate, QEasingCurve, QLocale, QModelIndex, QPoint, QPropertyAnimation, QRectF,
                            QSortFilterProxyModel, QTimer, Qt, Signal)
from PySide6.QtGui import QAction, QColor, QFontMetrics, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QAbstractItemView, QCalendarWidget, QFrame, QGraphicsDropShadowEffect, QGraphicsOpacityEffect,
                               QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QSizePolicy,
                               QStyledItemDelegate, QStyle, QTableView, QVBoxLayout, QWidget)

from . import tema as T
from .ikonlar import ikon, pixmap
from ..yardimci import KOD_AD, KOD_RENK, sayi_yaz, tarih_oku, tarih_yaz

TR = QLocale(QLocale.Turkish, QLocale.Turkey)


def golge(w, bulaniklik=24, y=4, alfa=18):
    e = QGraphicsDropShadowEffect(w)
    e.setBlurRadius(bulaniklik)
    e.setOffset(0, y)
    e.setColor(QColor(20, 20, 90, alfa))
    w.setGraphicsEffect(e)
    return e


def dugme(metin='', ikon_adi=None, tur=None, ipucu=None, renk=None):
    b = QPushButton(metin)
    if tur:
        b.setObjectName(tur)
    if ikon_adi:
        r = renk or {'Birincil': '#FFFFFF', 'Vurgu': '#FFFFFF', 'Tehlike': T.KIRMIZI, 'Duz': T.SOLUK}.get(tur, T.YAZI)
        b.setIcon(ikon(ikon_adi, r, 16))
    if ipucu:
        b.setToolTip(ipucu)
    b.setCursor(Qt.PointingHandCursor)
    return b


def etiket(metin='', ad=None, kelime_kaydir=False):
    lb = QLabel(metin)
    if ad:
        lb.setObjectName(ad)
    if kelime_kaydir:
        lb.setWordWrap(True)
    return lb


class Kart(QFrame):
    def __init__(self, baslik=None, ikon_adi=None, sag=None, ic_bosluk=18, parent=None):
        super().__init__(parent)
        self.setObjectName('Kart')
        self.duzen = QVBoxLayout(self)
        self.duzen.setContentsMargins(ic_bosluk, ic_bosluk - 2, ic_bosluk, ic_bosluk)
        self.duzen.setSpacing(10)
        if baslik:
            ust = QHBoxLayout()
            ust.setSpacing(8)
            if ikon_adi:
                ik = QLabel()
                ik.setPixmap(pixmap(ikon_adi, T.LACI, 18))
                ust.addWidget(ik)
            self.baslik = etiket(baslik, 'BolumBaslik')
            ust.addWidget(self.baslik)
            ust.addStretch(1)
            if sag is not None:
                ust.addWidget(sag)
            self.duzen.addLayout(ust)


class KpiKart(QFrame):
    tiklandi = Signal()

    def __init__(self, etiket_metni, ikon_adi, renk, zemin, parent=None):
        super().__init__(parent)
        self.setObjectName('Kart')
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(104)
        d = QHBoxLayout(self)
        d.setContentsMargins(18, 16, 18, 16)
        d.setSpacing(14)
        ik = QLabel()
        ik.setFixedSize(46, 46)
        ik.setAlignment(Qt.AlignCenter)
        ik.setPixmap(pixmap(ikon_adi, renk, 22))
        ik.setStyleSheet(f'background: {zemin}; border-radius: 13px;')
        d.addWidget(ik, 0, Qt.AlignTop)
        sag = QVBoxLayout()
        sag.setSpacing(0)
        self.etiket = etiket(etiket_metni, 'KpiEtiket')
        self.deger = etiket('—', 'KpiDeger')
        self.alt = etiket('', 'KpiAlt')
        sag.addWidget(self.etiket)
        sag.addWidget(self.deger)
        sag.addWidget(self.alt)
        sag.addStretch(1)
        d.addLayout(sag, 1)

    def ayarla(self, deger, alt='', renk=None):
        self.deger.setText(deger)
        self.deger.setStyleSheet(f'color: {renk};' if renk else '')
        self.alt.setText(alt)
        self.alt.setVisible(bool(alt))

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.tiklandi.emit()
        super().mousePressEvent(e)


class SayfaBasligi(QWidget):
    def __init__(self, baslik, alt='', parent=None):
        super().__init__(parent)
        d = QHBoxLayout(self)
        d.setContentsMargins(0, 0, 0, 0)
        d.setSpacing(10)
        sol = QVBoxLayout()
        sol.setSpacing(2)
        self.baslik = etiket(baslik, 'SayfaBaslik')
        self.alt = etiket(alt, 'SayfaAlt')
        sol.addWidget(self.baslik)
        sol.addWidget(self.alt)
        d.addLayout(sol, 1)
        self.sag = QHBoxLayout()
        self.sag.setSpacing(8)
        d.addLayout(self.sag)

    def ekle(self, w):
        self.sag.addWidget(w)
        return w


class AramaKutusu(QLineEdit):
    def __init__(self, ipucu='Ara…', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(ipucu)
        self.addAction(QAction(ikon('ara', T.SOLUK_2, 16), '', self), QLineEdit.LeadingPosition)
        self.setClearButtonEnabled(True)
        self.setMinimumWidth(240)


class _TakvimAcilir(QFrame):
    secildi = Signal(QDate)

    def __init__(self, parent=None):
        super().__init__(parent, Qt.Popup)
        self.setObjectName('Kart')
        d = QVBoxLayout(self)
        d.setContentsMargins(6, 6, 6, 6)
        self.takvim = QCalendarWidget()
        self.takvim.setLocale(TR)
        self.takvim.setFirstDayOfWeek(Qt.Monday)
        self.takvim.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.takvim.setGridVisible(False)
        self.takvim.setMinimumSize(300, 240)
        self.takvim.clicked.connect(self._sec)
        self.takvim.activated.connect(self._sec)
        d.addWidget(self.takvim)
        alt = QHBoxLayout()
        bugun = dugme('Bugün', tur='Duz')
        bugun.clicked.connect(lambda: self._sec(QDate.currentDate()))
        alt.addWidget(bugun)
        alt.addStretch(1)
        d.addLayout(alt)

    def _sec(self, q):
        self.secildi.emit(q)
        self.hide()


class TarihKutusu(QLineEdit):
    """gg.aa.yyyy yazılan ya da takvimden seçilen tarih; boş bırakılabilir (bos_olabilir)."""
    degisti = Signal()

    def __init__(self, bos_olabilir=True, ipucu='gg.aa.yyyy', parent=None):
        super().__init__(parent)
        self.bos_olabilir = bos_olabilir
        self.setPlaceholderText(ipucu)
        self.setMaximumWidth(170)
        self.setMinimumWidth(140)
        a = QAction(ikon('takvim', T.SOLUK, 16), 'Takvimden seç', self)
        a.triggered.connect(self._ac)
        self.addAction(a, QLineEdit.TrailingPosition)
        self.editingFinished.connect(self._bicimle)
        self.textChanged.connect(self._kontrol)
        self._acilir = None

    def _ac(self):
        if self._acilir is None:
            self._acilir = _TakvimAcilir(self)
            self._acilir.secildi.connect(lambda q: self.setTarih(datetime.date(q.year(), q.month(), q.day())))
        d = self._guvenli() or datetime.date.today()
        self._acilir.takvim.setSelectedDate(QDate(d.year, d.month, d.day))
        self._acilir.adjustSize()
        self._acilir.move(self.mapToGlobal(QPoint(0, self.height() + 4)))
        self._acilir.show()

    def _guvenli(self):
        try:
            return tarih_oku(self.text())
        except ValueError:
            return None

    def _kontrol(self):
        try:
            d = tarih_oku(self.text())
            hata = d is None and not self.bos_olabilir and False
        except ValueError:
            hata = True
        if self.property('hata') != hata:
            self.setProperty('hata', hata)
            self.style().unpolish(self)
            self.style().polish(self)
        self.degisti.emit()

    def _bicimle(self):
        d = self._guvenli()
        if d is not None and self.text() != tarih_yaz(d):
            self.setText(tarih_yaz(d))

    def tarih(self):
        """date | None. Geçersiz metinde ValueError."""
        return tarih_oku(self.text())

    def gecerli(self):
        try:
            d = tarih_oku(self.text())
        except ValueError:
            return False
        return d is not None or self.bos_olabilir

    def setTarih(self, d):
        self.setText(tarih_yaz(d) if d else '')
        self.degisti.emit()


class BosDurum(QWidget):
    def __init__(self, ikon_adi, baslik, aciklama='', parent=None):
        super().__init__(parent)
        d = QVBoxLayout(self)
        d.setAlignment(Qt.AlignCenter)
        d.setSpacing(6)
        ik = QLabel()
        ik.setPixmap(pixmap(ikon_adi, T.SOLUK_2, 40))
        ik.setAlignment(Qt.AlignCenter)
        d.addWidget(ik)
        b = etiket(baslik, 'BolumBaslik')
        b.setAlignment(Qt.AlignCenter)
        d.addWidget(b)
        if aciklama:
            a = etiket(aciklama, 'Soluk', True)
            a.setAlignment(Qt.AlignCenter)
            a.setMaximumWidth(520)
            d.addWidget(a, 0, Qt.AlignCenter)


# ----------------------------------------------------------------------------- tablo
SIRA = Qt.UserRole
SATIR = Qt.UserRole + 1


class Sutun:
    def __init__(self, baslik, deger, hiza='sol', sirala=None, genislik=None, tur='metin', ipucu=None, renk=None, kalin=False,
                 rozet=None, gerilsin=False):
        self.baslik, self.deger, self.sirala, self.genislik, self.tur = baslik, deger, sirala, genislik, tur
        self.hiza = {'sol': Qt.AlignLeft | Qt.AlignVCenter, 'orta': Qt.AlignCenter, 'sag': Qt.AlignRight | Qt.AlignVCenter}[hiza]
        self.ipucu, self.renk, self.kalin, self.rozet, self.gerilsin = ipucu, renk, kalin, rozet, gerilsin


class ListeModeli(QAbstractTableModel):
    def __init__(self, sutunlar, soluk=None, parent=None):
        super().__init__(parent)
        self.sutunlar = sutunlar
        self.satirlar = []
        self.soluk = soluk  # satir -> True: gri ve üstü çizili (iptal edilmiş kayıt)

    def doldur(self, satirlar):
        self.beginResetModel()
        self.satirlar = list(satirlar)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self.satirlar)

    def columnCount(self, parent=QModelIndex()):
        return len(self.sutunlar)

    def headerData(self, i, yon, rol=Qt.DisplayRole):
        if yon == Qt.Horizontal:
            if rol == Qt.DisplayRole:
                return self.sutunlar[i].baslik
            if rol == Qt.TextAlignmentRole:
                return self.sutunlar[i].hiza
        return None

    def data(self, idx, rol=Qt.DisplayRole):
        if not idx.isValid():
            return None
        s = self.sutunlar[idx.column()]
        r = self.satirlar[idx.row()]
        if rol == Qt.DisplayRole:
            v = s.deger(r)
            return '' if v is None else str(v)
        if rol == SIRA:
            return s.sirala(r) if s.sirala else s.deger(r)
        if rol == SATIR:
            return r
        if rol == Qt.TextAlignmentRole:
            return s.hiza
        if rol == Qt.ToolTipRole and s.ipucu:
            return s.ipucu(r)
        if self.soluk and rol in (Qt.ForegroundRole, Qt.FontRole) and self.soluk(r):
            if rol == Qt.ForegroundRole:
                return QColor(T.SOLUK_2)
            f = T.font(10, s.kalin)
            f.setStrikeOut(True)
            return f
        if rol == Qt.ForegroundRole and s.renk:
            c = s.renk(r)
            return QColor(c) if c else None
        if rol == Qt.FontRole and s.kalin:
            return T.font(10, True)
        return None


class FiltreProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.filtre = None
        self.setSortRole(SIRA)

    def filtre_ayarla(self, f):
        self.filtre = f
        self.invalidateFilter()

    def filterAcceptsRow(self, satir, ust):
        if self.filtre is None:
            return True
        return self.filtre(self.sourceModel().satirlar[satir])

    def lessThan(self, a, b):
        x, y = a.data(SIRA), b.data(SIRA)
        if x is None or x == '':
            return False if (y is None or y == '') else (self.sortOrder() == Qt.DescendingOrder)
        if y is None or y == '':
            return self.sortOrder() != Qt.DescendingOrder
        try:
            return x < y
        except TypeError:
            return str(x) < str(y)


def _rozet_ciz(p, rect, metin, zemin, yazi, kalin=True, ortala=False, dolu=True):
    f = T.font(9, kalin)
    p.setFont(f)
    fm = QFontMetrics(f)
    w = fm.horizontalAdvance(metin) + 18
    h = 22
    x = rect.left() + 8 if not ortala else rect.center().x() - w / 2
    r = QRectF(x, rect.center().y() - h / 2 + 0.5, w, h)
    yol = QPainterPath()
    yol.addRoundedRect(r, 11, 11)
    if dolu:
        p.fillPath(yol, QColor(zemin))
    p.setPen(QColor(yazi))
    p.drawText(r, Qt.AlignCenter, metin)


class RozetDelegate(QStyledItemDelegate):
    """Hücreyi yuvarlak rozet olarak çizer. renk(metin, satir) → (zemin, yazı) ya da None (düz metin)."""

    def __init__(self, renk, ortala=False, parent=None):
        super().__init__(parent)
        self.renk = renk
        self.ortala = ortala

    def paint(self, p, opt, idx):
        self.initStyleOption(opt, idx)
        metin = opt.text
        opt.text = ''
        opt.widget.style().drawControl(QStyle.CE_ItemViewItem, opt, p, opt.widget)
        if not metin:
            return
        rk = self.renk(metin, idx.data(SATIR))
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        if rk:
            _rozet_ciz(p, opt.rect, metin, rk[0], rk[1], ortala=self.ortala)
        else:
            p.setPen(QColor(T.YAZI))
            p.setFont(T.font(10))
            p.drawText(opt.rect.adjusted(8, 0, -8, 0), int(Qt.AlignVCenter | (Qt.AlignHCenter if self.ortala else Qt.AlignLeft)), metin)
        p.restore()


KISA_UYARI = [('avans', 'Avans'), ('dönem dışında', 'Dönem dışı'), ('çakışan', 'Çakışma'), ('Pazar/resmi tatil', 'Pazar/tatil'),
              ('md.55/a', 'Rapor sınırı'), ('günden uzun', 'Uzun izin'), ('Başlangıç tarihi', 'Tarih eksik'), ('Bitiş', 'Tarih hatalı'),
              ('Personel', 'Kişi bilgisi')]


def kisa_uyari(uyarilar):
    """Uzun uyarı metinlerinden tablo için kısa etiketler: 'Avans · Dönem dışı'"""
    out = []
    for u in uyarilar:
        for anahtar, ad in KISA_UYARI:
            if anahtar in u:
                if ad not in out:
                    out.append(ad)
                break
        else:
            out.append('Uyarı')
    return ' · '.join(out)


def kalan_renk(v):
    if v is None:
        return None
    if v < 0:
        return (T.KIRMIZI_ACIK, T.KIRMIZI)
    if v > 30:
        return (T.SARI_ACIK, T.SARI)
    return (T.YESIL_ACIK, T.YESIL)


def tur_renk(metin, satir=None):
    for k, ad in KOD_AD.items():
        if metin in (ad, k):
            return KOD_RENK[k]
    return None


def durum_renk(metin, satir=None):
    return {'Çalışıyor': (T.YESIL_ACIK, T.YESIL), 'Ayrıldı': ('#ECEDF2', '#5A5E72'), 'Bilgi hatalı': (T.KIRMIZI_ACIK, T.KIRMIZI),
            'İptal': ('#ECEDF2', '#7A7E92'), 'Teyitli': (T.YESIL_ACIK, T.YESIL), 'Ödendi': (T.YESIL_ACIK, T.YESIL),
            'Ödenmedi': (T.KIRMIZI_ACIK, T.KIRMIZI)}.get(metin, (T.SARI_ACIK, T.SARI) if metin.startswith('Teyit bekliyor') else None)


class KalanDelegate(QStyledItemDelegate):
    def __init__(self, deger, parent=None):
        super().__init__(parent)
        self.deger = deger

    def paint(self, p, opt, idx):
        self.initStyleOption(opt, idx)
        metin = opt.text
        opt.text = ''
        opt.widget.style().drawControl(QStyle.CE_ItemViewItem, opt, p, opt.widget)
        v = self.deger(idx.data(SATIR))
        rk = kalan_renk(v)
        if not metin or rk is None:
            return
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        _rozet_ciz(p, opt.rect, metin, rk[0], rk[1], ortala=True)
        p.restore()


def tablo(model, secim_coklu=False):
    v = QTableView()
    proxy = FiltreProxy(v)
    proxy.setSourceModel(model)
    v.setModel(proxy)
    v.horizontalHeader().setSortIndicator(-1, Qt.AscendingOrder)  # başlangıçta kaynak sırası; başlığa tıklayınca sıralanır
    v.setSortingEnabled(True)
    v.setSelectionBehavior(QAbstractItemView.SelectRows)
    v.setSelectionMode(QAbstractItemView.ExtendedSelection if secim_coklu else QAbstractItemView.SingleSelection)
    v.setEditTriggers(QAbstractItemView.NoEditTriggers)
    v.setShowGrid(False)
    v.setAlternatingRowColors(False)
    v.setWordWrap(False)
    v.setMouseTracking(True)
    v.verticalHeader().setVisible(False)
    v.verticalHeader().setDefaultSectionSize(40)
    v.horizontalHeader().setHighlightSections(False)
    v.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)
    v.horizontalHeader().setMinimumSectionSize(40)
    v.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)
    v.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
    v.setCornerButtonEnabled(False)
    son = len(model.sutunlar) - 1
    for i, s in enumerate(model.sutunlar):
        if s.genislik:
            v.setColumnWidth(i, s.genislik)
        if s.gerilsin and i != son:  # son sütun zaten boşluğu doldurur; ortadaki "gerilen" sütun kalan genişliği alır
            v.horizontalHeader().setSectionResizeMode(i, QHeaderView.Stretch)
    v.horizontalHeader().setStretchLastSection(True)
    return v, proxy


def secili_satir(v):
    idx = v.selectionModel().selectedRows() if v.selectionModel() else []
    if not idx:
        cur = v.currentIndex()
        return cur.data(SATIR) if cur.isValid() else None
    return idx[0].data(SATIR)


def tablo_karti(v, ic_bosluk=0):
    """Tabloyu yuvarlak köşeli beyaz bir kartın içine yerleştirir."""
    k = QFrame()
    k.setObjectName('Kart')
    d = QVBoxLayout(k)
    d.setContentsMargins(1, 1, 1, 1)
    d.addWidget(v)
    return k


# ----------------------------------------------------------------------------- mesajlar
def soru(parent, baslik, metin, evet='Evet', hayir='Vazgeç', tehlikeli=False):
    m = QMessageBox(parent)
    m.setWindowTitle(baslik)
    m.setText(metin)
    m.setIcon(QMessageBox.Warning if tehlikeli else QMessageBox.Question)
    e = m.addButton(evet, QMessageBox.AcceptRole)
    h = m.addButton(hayir, QMessageBox.RejectRole)
    if tehlikeli:
        e.setObjectName('Tehlike')
    else:
        e.setObjectName('Birincil')
    m.setDefaultButton(h if tehlikeli else e)
    m.exec()
    return m.clickedButton() is e


def hata(parent, metin, baslik='Kaydedilemedi'):
    m = QMessageBox(parent)
    m.setWindowTitle(baslik)
    m.setIcon(QMessageBox.Warning)
    m.setText(metin)
    m.addButton('Tamam', QMessageBox.AcceptRole).setObjectName('Birincil')
    m.exec()


def bilgi(parent, metin, baslik='Bilgi', ayrinti=None):
    m = QMessageBox(parent)
    m.setWindowTitle(baslik)
    m.setIcon(QMessageBox.Information)
    m.setText(metin)
    if ayrinti:
        m.setDetailedText(ayrinti)
    m.addButton('Tamam', QMessageBox.AcceptRole).setObjectName('Birincil')
    m.exec()


class Bildirim(QLabel):
    """Pencerenin altında kısa süre görünen bildirim ('Kaydedildi')."""

    def __init__(self, ana):
        super().__init__(ana)
        self.setObjectName('Bildirim')
        self.hide()
        self._etki = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._etki)
        self._anim = QPropertyAnimation(self._etki, b'opacity', self)
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._zaman = QTimer(self)
        self._zaman.setSingleShot(True)
        self._zaman.timeout.connect(self._kaybol)

    def goster(self, metin, tur='bilgi', sure=2600):
        self.setText(('✓  ' if tur == 'bilgi' else '!  ') + metin)
        self.setProperty('tur', tur)
        self.style().unpolish(self)
        self.style().polish(self)
        self.adjustSize()
        ana = self.parentWidget()
        self.move((ana.width() - self.width()) // 2 + 118, ana.height() - self.height() - 28)
        self.raise_()
        self._anim.stop()
        self._etki.setOpacity(1.0)
        self.show()
        self._zaman.start(sure)

    def _kaybol(self):
        self._anim.stop()
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.hide)
        self._anim.start()


def duzen_temizle(d):
    """Düzendeki bütün öğeleri hemen gizleyip siler (deleteLater tek başına bir kare gecikir: eski yazılar üst üste görünür)."""
    while d.count():
        o = d.takeAt(0)
        w = o.widget()
        if w is not None:
            w.hide()
            w.setParent(None)
            w.deleteLater()
        elif o.layout() is not None:
            duzen_temizle(o.layout())


def yatay(*w, bosluk=8, kenar=0):
    d = QHBoxLayout()
    d.setSpacing(bosluk)
    d.setContentsMargins(kenar, kenar, kenar, kenar)
    for x in w:
        if x is None:
            d.addStretch(1)
        elif isinstance(x, int):
            d.addSpacing(x)
        elif isinstance(x, QWidget):
            d.addWidget(x)
        else:
            d.addLayout(x)
    return d


def ayirici():
    f = QFrame()
    f.setFixedHeight(1)
    f.setStyleSheet(f'background: {T.CIZGI};')
    return f
