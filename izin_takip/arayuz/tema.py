# -*- coding: utf-8 -*-
"""Renkler, yazı tipi ve Qt stil sayfası (QSS). Ana renkler: lacivert #14145A, turuncu #F37A41."""
import os

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

from ..yollar import kaynak

LACI = '#14145A'
LACI_2 = '#22227A'
LACI_3 = '#2E2E8F'
TURUNCU = '#F37A41'
TURUNCU_2 = '#E2632A'
TURUNCU_ACIK = '#FFF1E9'
ZEMIN = '#F4F5FA'
KART = '#FFFFFF'
CIZGI = '#E6E8F0'
CIZGI_2 = '#D5D8E3'
YAZI = '#1B1D3A'
SOLUK = '#6B6F86'
SOLUK_2 = '#9A9EB2'
YESIL, YESIL_ACIK = '#178A4C', '#E3F5EA'
KIRMIZI, KIRMIZI_ACIK = '#D23545', '#FDE8EA'
SARI, SARI_ACIK = '#A86A00', '#FFF3D6'
MAVI, MAVI_ACIK = '#2B62C9', '#E5EEFC'
MOR, MOR_ACIK = '#5B4BC4', '#EEEBFC'
SECIM = '#EEF0FB'

YAZI_TIPI = 'Inter'


def yazi_tiplerini_yukle():
    """Program içindeki Inter yazı tipini yükler (SIL Open Font License); yoksa Segoe UI."""
    global YAZI_TIPI
    klasor = kaynak('yazitipi')
    yuklendi = False
    if os.path.isdir(klasor):
        for f in sorted(os.listdir(klasor)):
            if f.lower().endswith(('.otf', '.ttf')):
                if QFontDatabase.addApplicationFont(os.path.join(klasor, f)) >= 0:
                    yuklendi = True
    if not yuklendi:
        YAZI_TIPI = 'Segoe UI'
    return YAZI_TIPI


def font(boyut=10, kalin=False, agirlik=None):
    f = QFont(YAZI_TIPI)
    f.setPointSizeF(boyut)
    if agirlik is not None:
        f.setWeight(agirlik)
    elif kalin:
        f.setWeight(QFont.DemiBold)
    return f


def palet():
    p = QPalette()
    p.setColor(QPalette.Window, QColor(ZEMIN))
    p.setColor(QPalette.Base, QColor(KART))
    p.setColor(QPalette.AlternateBase, QColor('#FAFBFD'))
    p.setColor(QPalette.Text, QColor(YAZI))
    p.setColor(QPalette.WindowText, QColor(YAZI))
    p.setColor(QPalette.ButtonText, QColor(YAZI))
    p.setColor(QPalette.Button, QColor(KART))
    p.setColor(QPalette.Highlight, QColor(SECIM))
    p.setColor(QPalette.HighlightedText, QColor(YAZI))
    p.setColor(QPalette.PlaceholderText, QColor(SOLUK_2))
    p.setColor(QPalette.ToolTipBase, QColor(LACI))
    p.setColor(QPalette.ToolTipText, QColor('#FFFFFF'))
    return p


def qss():
    return f"""
* {{ font-family: "{YAZI_TIPI}"; }}
QWidget {{ color: {YAZI}; font-size: 10pt; }}
QMainWindow, QDialog, #Icerik {{ background: {ZEMIN}; }}
QToolTip {{ background: {LACI}; color: white; border: none; padding: 6px 9px; border-radius: 6px; font-size: 9pt; }}

/* ---------------- kenar çubuğu */
#Kenar {{ background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 {LACI}, stop:1 #0D0D45); border: none; }}
#Kenar QLabel {{ color: rgba(255,255,255,0.72); }}
#KenarBolum {{ color: rgba(255,255,255,0.42); font-size: 8pt; font-weight: 600; letter-spacing: 1px; padding-left: 14px; }}
QPushButton#Gezinti {{
    background: transparent; color: rgba(255,255,255,0.78); border: none; border-radius: 10px;
    text-align: left; padding: 10px 14px; font-size: 10.5pt; font-weight: 500;
}}
QPushButton#Gezinti:hover {{ background: rgba(255,255,255,0.07); color: white; }}
QPushButton#Gezinti:checked {{ background: rgba(255,255,255,0.12); color: white; font-weight: 600; }}
#KenarAlt {{ background: rgba(255,255,255,0.06); border-radius: 12px; }}
#KenarAlt QLabel {{ color: rgba(255,255,255,0.85); }}
#TarihUyari {{ background: {TURUNCU}; color: white; border-radius: 8px; padding: 6px 8px; font-weight: 600; }}
QPushButton#KenarDugme {{ background: rgba(255,255,255,0.08); border: none; border-radius: 8px; padding: 5px; }}
QPushButton#KenarDugme:hover {{ background: rgba(255,255,255,0.18); }}
#KenarCizgi {{ background: rgba(255,255,255,0.10); }}

/* ---------------- giriş ve kilit ekranı */
#GirisSol {{ background: qlineargradient(x1:0, y1:0, x2:0.4, y2:1, stop:0 {LACI}, stop:1 #0B0B3E); }}
#GirisSol QLabel {{ color: rgba(255,255,255,0.74); }}
#GirisUst {{ color: {TURUNCU}; font-weight: 700; letter-spacing: 3px; font-size: 9pt; }}
#GirisAd {{ color: white; font-size: 19pt; font-weight: 700; }}
#GirisTelif {{ color: rgba(255,255,255,0.52); font-size: 8.5pt; }}
#GirisSag {{ background: {KART}; }}
#AlanEtiket {{ color: {SOLUK}; font-size: 9pt; font-weight: 600; }}
#GirisMesaj {{ background: {KIRMIZI_ACIK}; border: 1px solid #F3B7BE; border-radius: 9px; color: #8E1C28; padding: 8px 12px; font-weight: 600; }}
#KurtarmaAnahtari {{ font-family: "Consolas", "Cascadia Mono", monospace; font-size: 16pt; font-weight: 700; color: {LACI};
    background: #F8F9FD; border: 1.5px dashed {CIZGI_2}; border-radius: 12px; padding: 16px 18px; }}

/* ---------------- sayfa başlığı */
#SayfaBaslik {{ font-size: 19pt; font-weight: 700; color: {YAZI}; }}
#SayfaAlt {{ color: {SOLUK}; font-size: 10pt; }}
#BolumBaslik {{ font-size: 11.5pt; font-weight: 650; color: {YAZI}; }}
#Soluk {{ color: {SOLUK}; }}
#SolukKucuk {{ color: {SOLUK}; font-size: 9pt; }}
#Uyari {{ color: {KIRMIZI}; }}
#ElleTarih {{ background: {TURUNCU_ACIK}; color: {TURUNCU_2}; border: 1px solid #F9C9AE; border-radius: 10px; padding: 8px 12px; font-weight: 600; }}

/* ---------------- kartlar */
#Kart {{ background: {KART}; border: 1px solid {CIZGI}; border-radius: 14px; }}
#KpiDeger {{ font-size: 22pt; font-weight: 700; color: {YAZI}; }}
#KpiEtiket {{ color: {SOLUK}; font-size: 9.5pt; font-weight: 500; }}
#KpiAlt {{ color: {SOLUK_2}; font-size: 8.5pt; }}
#BuyukKalan {{ font-size: 30pt; font-weight: 800; }}

/* ---------------- düğmeler */
QPushButton {{
    background: {KART}; color: {YAZI}; border: 1px solid {CIZGI_2}; border-radius: 9px;
    padding: 7px 14px; font-weight: 600;
}}
QPushButton:hover {{ background: #F7F8FC; border-color: #C3C7D6; }}
QPushButton:pressed {{ background: #EEF0F6; }}
QPushButton:disabled {{ color: {SOLUK_2}; background: #F6F7FA; border-color: {CIZGI}; }}
QPushButton#Birincil {{ background: {LACI}; color: white; border: 1px solid {LACI}; }}
QPushButton#Birincil:hover {{ background: {LACI_2}; border-color: {LACI_2}; }}
QPushButton#Birincil:pressed {{ background: #0E0E44; }}
QPushButton#Vurgu {{ background: {TURUNCU}; color: white; border: 1px solid {TURUNCU}; }}
QPushButton#Vurgu:hover {{ background: {TURUNCU_2}; border-color: {TURUNCU_2}; }}
QPushButton#Tehlike {{ color: {KIRMIZI}; }}
QPushButton#Tehlike:hover {{ background: {KIRMIZI_ACIK}; border-color: #F3B7BE; }}
QPushButton#Duz {{ background: transparent; border: none; color: {SOLUK}; padding: 6px 8px; }}
QPushButton#Duz:hover {{ color: {YAZI}; background: #ECEEF5; }}
QPushButton#Bag {{ background: transparent; border: none; color: {MAVI}; padding: 2px 0; font-weight: 600; text-align: left; }}
QPushButton#Bag:hover {{ color: {LACI}; text-decoration: underline; }}
QPushButton#Secmeli {{ border-radius: 16px; padding: 6px 14px; font-weight: 600; color: {SOLUK}; }}
QPushButton#Secmeli:checked {{ background: {LACI}; color: white; border-color: {LACI}; }}

/* ---------------- giriş kutuları */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QPlainTextEdit, QTextEdit {{
    background: {KART}; border: 1px solid {CIZGI_2}; border-radius: 9px; padding: 6px 10px;
    selection-background-color: {TURUNCU}; selection-color: white;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus, QPlainTextEdit:focus, QTextEdit:focus {{ border: 1.5px solid {TURUNCU}; }}
QLineEdit:disabled, QComboBox:disabled {{ background: #F6F7FA; color: {SOLUK}; }}
QLineEdit[hata="true"] {{ border: 1.5px solid {KIRMIZI}; background: #FFF8F8; }}
QComboBox {{ padding-right: 26px; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url("{kaynak('asagi.svg').replace(os.sep, '/')}"); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {KART}; border: 1px solid {CIZGI_2}; border-radius: 8px; padding: 4px; outline: none;
    selection-background-color: {SECIM}; selection-color: {YAZI};
}}
QSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{ width: 0; border: none; }}
QCheckBox {{ spacing: 8px; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 5px; border: 1.5px solid {CIZGI_2}; background: white; }}
QCheckBox::indicator:checked {{ background: {LACI}; border-color: {LACI}; image: url("{kaynak('onay.svg').replace(os.sep, '/')}"); }}
QRadioButton::indicator {{ width: 16px; height: 16px; }}

/* ---------------- tablolar */
QTableView, QTreeView, QListView {{
    background: {KART}; border: none; gridline-color: transparent; outline: none;
    selection-background-color: {SECIM}; selection-color: {YAZI};
}}
QTableView::item {{ padding: 0 8px; border-bottom: 1px solid #F0F1F6; }}
QTableView::item:selected {{ background: {SECIM}; color: {YAZI}; }}
QTableView::item:hover {{ background: #F8F9FD; }}
QHeaderView {{ background: transparent; border: none; }}
QHeaderView::section {{
    background: #FAFBFD; color: {SOLUK}; border: none; border-bottom: 1px solid {CIZGI};
    padding: 9px 8px; font-size: 8.5pt; font-weight: 650; text-transform: uppercase;
}}
QHeaderView::section:vertical {{ text-transform: none; font-size: 9.5pt; color: {YAZI}; font-weight: 500;
    background: {KART}; border-bottom: 1px solid #F0F1F6; border-right: 1px solid {CIZGI}; padding: 0 10px; }}
QTableCornerButton::section {{ background: #FAFBFD; border: none; border-bottom: 1px solid {CIZGI}; border-right: 1px solid {CIZGI}; }}

/* ---------------- kaydırma çubukları */
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 11px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #CDD1DE; border-radius: 4px; min-height: 36px; }}
QScrollBar::handle:vertical:hover {{ background: #AEB3C6; }}
QScrollBar:horizontal {{ background: transparent; height: 11px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: #CDD1DE; border-radius: 4px; min-width: 36px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---------------- sekmeler */
QTabWidget::pane {{ border: none; }}
QTabBar::tab {{
    background: transparent; color: {SOLUK}; padding: 8px 16px; margin-right: 4px; border: none;
    border-bottom: 2px solid transparent; font-weight: 600;
}}
QTabBar::tab:selected {{ color: {LACI}; border-bottom: 2px solid {TURUNCU}; }}
QTabBar::tab:hover {{ color: {YAZI}; }}

/* ---------------- takvim açılır penceresi */
QCalendarWidget QWidget#qt_calendar_navigationbar {{ background: {LACI}; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
QCalendarWidget QToolButton {{ color: white; background: transparent; font-weight: 600; padding: 4px 8px; border: none; }}
QCalendarWidget QToolButton:hover {{ background: rgba(255,255,255,0.12); border-radius: 6px; }}
QCalendarWidget QMenu {{ background: white; }}
QCalendarWidget QSpinBox {{ color: white; background: transparent; border: none; selection-background-color: {TURUNCU}; }}
QCalendarWidget QAbstractItemView:enabled {{ selection-background-color: {TURUNCU}; selection-color: white; color: {YAZI}; }}

QMenu {{ background: white; border: 1px solid {CIZGI_2}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px; border-radius: 6px; }}
QMenu::item:selected {{ background: {SECIM}; color: {YAZI}; }}
QMenu::separator {{ height: 1px; background: {CIZGI}; margin: 4px 8px; }}
QMessageBox QLabel {{ font-size: 10pt; }}
#Bildirim {{ background: {LACI}; color: white; border-radius: 12px; padding: 12px 18px; font-weight: 600; }}
#Bildirim[tur="hata"] {{ background: {KIRMIZI}; }}
#OnizlemeKutu {{ background: #F8F9FD; border: 1px solid {CIZGI}; border-radius: 12px; }}
#UyariKutu {{ background: {SARI_ACIK}; border: 1px solid #F5DDA0; border-radius: 10px; color: #7A4E00; }}
#HataKutu {{ background: {KIRMIZI_ACIK}; border: 1px solid #F3B7BE; border-radius: 10px; color: #8E1C28; }}
#BilgiKutu {{ background: {MAVI_ACIK}; border: 1px solid #C5D7F6; border-radius: 10px; color: #1C3F84; }}
"""
