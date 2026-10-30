# -*- coding: utf-8 -*-
"""Aranabilir personel seçici: yazdıkça (Türkçe karakter / büyük-küçük harf fark etmeden) süzülen açılır liste."""
from PySide6.QtCore import QSortFilterProxyModel, QStringListModel, Qt, Signal
from PySide6.QtWidgets import QComboBox, QCompleter

from ..yardimci import ara_eslesir


class _Suzgec(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sorgu = ''

    def filterAcceptsRow(self, satir, ust):
        return ara_eslesir(self.sorgu, self.sourceModel().index(satir, 0, ust).data())


class KisiSecici(QComboBox):
    secildi = Signal(object)   # personel id ya da None

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.NoInsert)
        self.lineEdit().setPlaceholderText('Personel adı yazın ya da listeden seçin…')
        self._kaynak = QStringListModel(self)
        self._suzgec = _Suzgec(self)
        self._suzgec.setSourceModel(self._kaynak)
        self._tamam = QCompleter(self._suzgec, self)
        self._tamam.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self._tamam.setCaseSensitivity(Qt.CaseInsensitive)
        self._tamam.popup().setObjectName('Liste')
        self.setCompleter(self._tamam)
        self.lineEdit().textEdited.connect(self._yazildi)
        self._tamam.activated[str].connect(self._tamamdan)
        self.currentIndexChanged.connect(self._degisti)
        self._idler = []
        self.setMinimumWidth(320)
        self.setMaxVisibleItems(14)

    def doldur(self, kisiler):
        """kisiler: [(id, etiket)]"""
        self.blockSignals(True)
        self.clear()
        self._idler = [k for k, _ in kisiler]
        for k, e in kisiler:
            self.addItem(e, k)
        self._kaynak.setStringList([e for _, e in kisiler])
        self.setCurrentIndex(-1)
        self.lineEdit().clear()
        self.blockSignals(False)

    def _yazildi(self, metin):
        self._suzgec.sorgu = metin
        self._suzgec.invalidateFilter()
        if metin:
            self._tamam.complete()

    def _tamamdan(self, metin):
        i = self.findText(metin)
        if i >= 0:
            self.setCurrentIndex(i)

    def _degisti(self, i):
        self.secildi.emit(self.itemData(i) if i >= 0 else None)

    def secili(self):
        i = self.currentIndex()
        if i < 0 or self.itemText(i) != self.lineEdit().text():
            i = self.findText(self.lineEdit().text())
        return self.itemData(i) if i >= 0 else None

    def sec(self, pid):
        i = self.findData(pid)
        self.setCurrentIndex(i)
