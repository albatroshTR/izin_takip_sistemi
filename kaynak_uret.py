# -*- coding: utf-8 -*-
"""Program kaynaklarını üretir (bir kez çalıştırılır; çıktılar depoda). Logo ve simge bu betikle çizilir; marka ya da üçüncü taraf
görseli kullanılmaz:
  izin_takip/kaynaklar/logo.png       : açık zemin için logo (lacivert yazı)
  izin_takip/kaynaklar/logo_koyu.png  : koyu (lacivert) zemin için logo (beyaz yazı)
  izin_takip/kaynaklar/simge.png / simge.ico : program simgesi (lacivert kare, turuncu takvim + onay)
Kullanım: python kaynak_uret.py
"""
import os
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter, QPainterPath, QPen

K = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'izin_takip', 'kaynaklar')
LACIVERT, TURUNCU = '#14145A', '#F37A41'


def _takvim(p, s, ox, oy, cerceve, onay):
    """256 birimlik tasarım alanındaki takvim + onay çizimi; (ox, oy) kaydırma, s ölçek."""
    p.setPen(QPen(QColor(cerceve), 16 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    p.drawRoundedRect(QRectF(ox + 58 * s, oy + 70 * s, 140 * s, 128 * s), 22 * s, 22 * s)
    p.drawLine(int(ox + 96 * s), int(oy + 52 * s), int(ox + 96 * s), int(oy + 86 * s))
    p.drawLine(int(ox + 160 * s), int(oy + 52 * s), int(ox + 160 * s), int(oy + 86 * s))
    p.drawLine(int(ox + 60 * s), int(oy + 112 * s), int(ox + 196 * s), int(oy + 112 * s))
    p.setPen(QPen(QColor(onay), 20 * s, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    yol = QPainterPath()
    yol.moveTo(ox + 96 * s, oy + 154 * s)
    yol.lineTo(ox + 118 * s, oy + 174 * s)
    yol.lineTo(ox + 162 * s, oy + 132 * s)
    p.drawPath(yol)


def logo(koyu_zemin, dosya):
    """459 x 92: solda takvim simgesi, sağda "İzin Takip Sistemi" yazısı (Inter)."""
    img = QImage(459, 92, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.TextAntialiasing)
    yazi = '#FFFFFF' if koyu_zemin else LACIVERT
    _takvim(p, 0.34, -8, -4, yazi, TURUNCU)
    f = QFont('Inter')
    f.setPixelSize(38)
    f.setBold(True)
    p.setFont(f)
    p.setPen(QColor(yazi))
    taban = QRectF(84, 0, 370, 92)
    p.drawText(taban, Qt.AlignVCenter | Qt.AlignLeft, 'İzin Takip ')
    genislik = p.fontMetrics().horizontalAdvance('İzin Takip ')
    f.setBold(False)
    p.setFont(f)
    p.setPen(QColor(TURUNCU))
    p.drawText(QRectF(84 + genislik, 0, 370 - genislik, 92), Qt.AlignVCenter | Qt.AlignLeft, 'Sistemi')
    p.end()
    img.save(os.path.join(K, dosya))


def simge(boyut):
    img = QImage(boyut, boyut, QImage.Format_ARGB32)
    img.fill(Qt.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.Antialiasing)
    s = boyut / 256.0
    yol = QPainterPath()
    yol.addRoundedRect(QRectF(8 * s, 8 * s, 240 * s, 240 * s), 56 * s, 56 * s)
    p.fillPath(yol, QColor(LACIVERT))
    _takvim(p, s, 0, 0, '#FFFFFF', TURUNCU)
    p.end()
    return img


if __name__ == '__main__':
    app = QGuiApplication(sys.argv)
    for dosya in sorted(os.listdir(os.path.join(K, 'yazitipi'))):
        if dosya.endswith('.otf'):
            QFontDatabase.addApplicationFont(os.path.join(K, 'yazitipi', dosya))
    logo(False, 'logo.png')
    logo(True, 'logo_koyu.png')
    simge(256).save(os.path.join(K, 'simge.png'))
    simge(256).save(os.path.join(K, 'simge.ico'))  # Qt ico eklentisi; Windows simgesi
    print('tamam:', sorted(f for f in os.listdir(K) if not os.path.isdir(os.path.join(K, f))))
