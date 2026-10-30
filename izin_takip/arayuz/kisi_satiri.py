# -*- coding: utf-8 -*-
"""Kartlardaki kısa liste satırı: baş harf yuvarlağı + ad + alt bilgi + sağda rozet."""
import zlib

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath
from PySide6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from . import tema as T


class KisaltEtiket(QLabel):
    """Sığmayan metni '…' ile kısaltan etiket (kartların genişliğini zorlamaz); tam metin ipucunda."""

    def __init__(self, metin='', parent=None):
        super().__init__(metin, parent)
        self._tam = metin
        self.setToolTip(metin)
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.setMinimumWidth(40)

    def metin_ayarla(self, metin, ipucu=None):
        self._tam = metin
        self.setToolTip(ipucu or metin)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(self.palette().windowText().color())
        p.setFont(self.font())
        metin = self.fontMetrics().elidedText(self._tam, Qt.ElideRight, self.width())
        p.drawText(self.rect(), int(Qt.AlignLeft | Qt.AlignVCenter), metin)
        p.end()

AVATAR_RENK = [('#E5EEFC', '#2B62C9'), ('#FFF1E9', '#D9581C'), ('#E3F5EA', '#178A4C'), ('#EEEBFC', '#5B4BC4'),
               ('#FDE8EA', '#C22F40'), ('#FFF3D6', '#A86A00'), ('#E2F4F7', '#0F7C8C')]


def bas_harfler(ad):
    p = [x for x in (ad or '').split() if x]
    if not p:
        return '?'
    return (p[0][0] + (p[-1][0] if len(p) > 1 else '')).upper()


class Avatar(QWidget):
    def __init__(self, ad, boyut=34, parent=None):
        super().__init__(parent)
        self.ad = ad
        self.setFixedSize(boyut, boyut)
        self.renk = AVATAR_RENK[zlib.crc32(ad.encode('utf-8')) % len(AVATAR_RENK)]

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        yol = QPainterPath()
        yol.addEllipse(QRectF(0, 0, self.width(), self.height()))
        p.fillPath(yol, QColor(self.renk[0]))
        p.setPen(QColor(self.renk[1]))
        p.setFont(T.font(self.width() / 3.6, True))
        p.drawText(self.rect(), Qt.AlignCenter, bas_harfler(self.ad))


class KisiSatiri(QWidget):
    tiklandi = Signal()

    def __init__(self, ad, alt='', sag='', sag_renk=None, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.PointingHandCursor)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setObjectName('KisiSatiri')
        self.setStyleSheet('#KisiSatiri { border-radius: 10px; } #KisiSatiri:hover { background: #F5F6FB; }')
        d = QHBoxLayout(self)
        d.setContentsMargins(6, 5, 8, 5)
        d.setSpacing(10)
        d.addWidget(Avatar(ad))
        v = QVBoxLayout()
        v.setSpacing(0)
        a = KisaltEtiket(ad)
        a.setStyleSheet('font-weight: 600;')
        v.addWidget(a)
        if alt:
            b = KisaltEtiket(alt)
            b.setObjectName('SolukKucuk')
            v.addWidget(b)
        d.addLayout(v, 1)
        if sag:
            s = QLabel(sag)
            z, y = sag_renk or ('#EEF0F6', T.YAZI)
            s.setStyleSheet(f'background: {z}; color: {y}; border-radius: 10px; padding: 3px 10px; font-weight: 600; font-size: 9pt;')
            d.addWidget(s)

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.tiklandi.emit()
        super().mousePressEvent(e)
