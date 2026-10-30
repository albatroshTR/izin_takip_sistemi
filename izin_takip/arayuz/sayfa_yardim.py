# -*- coding: utf-8 -*-
"""Yardım: nasıl yapılır ve hesap kuralları."""
import html

from PySide6.QtWidgets import QTabWidget, QTextBrowser

from . import tema as T
from .sayfa import Sayfa

NASIL = [
    ('İzin yazmak (yıllık, rapor, mazeret, ücretsiz, idari)', 'İzin Kayıtları › Yeni izin (ya da her yerde Ctrl+N)',
     'Personeli seçin (adını yazmaya başlayın), izin türünü ve tarihleri seçin. Yıllık izinden düşülecek gün, işe dönüş tarihi ve '
     'kalan izin sağda hemen hesaplanır. Tek günlük izinde bitiş tarihini boş bırakın.'),
    ('İzni iptal etmek / düzeltmek', 'İzin Kayıtları › kayda çift tıklayın',
     'Tarihi ya da türü yanlışsa düzeltip kaydedin. Vazgeçilen izin için "İzni iptal et" seçin: hesaptan çıkar, listede üstü çizili kalır. '
     '"Sil" yalnız yanlışlıkla girilen kayıtlar içindir.'),
    ('Kimin ne kadar izni kaldığını görmek', 'Genel Durum',
     'Herkesin kalan izni, sonraki hak tarihi ve uyarıları. Kırmızı = eksi bakiye (avans), sarı = 30 günden fazla birikmiş.'),
    ('Bir kişinin izin kartı (izin kayıt belgesi)', 'Personel › kişiye çift tıklayın',
     'Hak kazanma tarihleri, kalan iznin hangi yıllardan geldiği, yıllara göre kullanım, bütün izinler ve açıklamalar. '
     '"İzin kartı (PDF / yazdır)" ile imzalanacak belgeyi alın.'),
    ('İzin formu yazdırmak', 'İzin Kayıtları › izni seçin › İzin formu', 'İzin talep ve onay formu (işçi, birim amiri, insan kaynakları imzaları).'),
    ('Aylık takvim', 'Takvim', 'Renkler izin türünü gösterir; gri sütun Pazar, turuncu resmi tatil. Bir güne çift tıklayınca o güne izin girilir.'),
    ('Yeni çalışan / işten çıkış / yeniden giriş', 'Personel › Yeni personel ya da kişiyi düzenleyin',
     'Yeni kişide işe giriş ve doğum tarihini yazın (50 yaş kuralı için gerekli). İşten çıkınca çıkış tarihini yazın; kişi "Ayrıldı" olur. '
     'Yeniden işe girerse "Dönem ekle" ile yeni giriş yazın: önceki hizmet kıdeme eklenir.'),
    ('Ayrılanlara ödenecek izin ücreti', 'Ayrılanlar', 'Ödenmesi gereken gün kendiliğinden hesaplanır. Son brüt aylık ücreti yazın → tutar '
     '(gün × ücret ÷ 30); ödeyince "Ödendi", tarih ve tutar. Zamanaşımı çıkıştan itibaren 5 yıl.'),
    ('Uyarıları görmek', 'Kontroller', 'Avans izin, çalışma dönemi dışı tarih, çakışan kayıt, eksik bilgi. Çift tıklayıp düzeltin.'),
    ('Yeni yılın resmi tatilleri', 'Tatiller', 'Sabit tatilleri tek düğmeyle ekleyin; Ramazan ve Kurban Bayramı günlerini Diyanet takviminden girin.'),
    ('Yedek / Excel', 'Ayarlar', 'Program her gün otomatik yedek alır. "Excel\'e aktar" ile bütün listeleri Excel dosyası olarak alabilirsiniz.'),
]

KURALLAR = [
    ('Yasal izin süresi (4857 s. İş Kanunu md.53)', '1–5. hizmet yılı 14 gün, 6–14. yıl 20 gün, 15. yıl ve sonrası 26 gün. Hak kazanılan '
     'tarihte 50 yaş ve üstü veya 18 yaş ve altı olana en az 20 gün.'),
    ('Hak kazanma', 'İşe girişin her yıldönümünde yeni izin hakkı doğar. Aynı işyerinde önceki çalışmalar kıdeme eklenir (md.54). Ücretsiz izin '
     'günleri hak tarihini öteler; md.55/a sınırını (bildirim süresi + 6 hafta) aşan rapor günlerini Ücretsiz izin olarak girin (program uyarır).'),
    ('Düşülen gün (md.56)', 'Pazar ve resmi tatiller izinden düşülmez; Cumartesi iş günüdür. Arife ve 28 Ekim yarım gün düşülür. Rapor, '
     'mazeret, ücretsiz ve idari izin yıllık izinden düşülmez.'),
    ('Kalan izin', 'Bu çalışma döneminde kazanılan − bu dönemde kullanılan (+ varsa elle düzeltme). İleri tarihli izin girildiği anda kalandan '
     'düşülür; eksi bakiye avans ya da ileri tarihli izni gösterir. Önceki çalışma döneminin eksi kalanı yeni döneme taşınır; '
     'çalışma dönemi dışına yazılan yıllık izin en yakın döneme düşülür.'),
    ('Kalanın kaynağı', 'Kullanılan izin önce en eski haktan düşülür. İzin Kartı\'ndaki "Bu haktan kalan" her hak yılından ne kaldığını, '
     'yıllık özetteki "Kalan" her yıl sonundaki bakiyeyi gösterir. İzin çalışırken yanmaz; bu döküm açıklık içindir.'),
    ('Doğum tarihi bilinmiyorsa', 'Kişi 50 yaşın üstündeyse Personel › Ek bilgiler › "50 yaş beyanı"na 50 yaşında olduğu kesin olan ilk tarihi '
     'yazın; o tarihten sonra kazanılan izin en az 20 gün olur. Doğum tarihi yazılınca beyan dikkate alınmaz.'),
    ('İşten ayrılan', 'Kullanılmayan izin ücreti çıkışta ödenmelidir (md.59). Ayrılan kişi silinmez; Ayrılanlar sayfasında ödeme izlenir.'),
    ('"Teyit bekliyor" işareti', 'Bir kişinin giriş/çıkış tarihi gibi bilgileri henüz doğrulanmadıysa Personel › Teyit alanını '
     '"Teyit bekliyor" yapın; kişi izin kartında ve listelerde işaretli görünür.'),
]


class YardimSayfa(Sayfa):
    baslik = 'Yardım'
    alt_baslik = 'Programın kullanımı ve izin hesabının kuralları.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        self.sekme = QTabWidget()
        self.duzen.addWidget(self.sekme, 1)
        self.t_nasil = self._tarayici()
        self.t_kural = self._tarayici()
        self.sekme.addTab(self.t_nasil, 'Nasıl yapılır?')
        self.sekme.addTab(self.t_kural, 'Hesap kuralları')

    def _tarayici(self):
        t = QTextBrowser()
        t.setOpenExternalLinks(True)
        t.setStyleSheet(f'QTextBrowser {{ background: white; border: 1px solid {T.CIZGI}; border-radius: 14px; padding: 18px; }}')
        return t

    def yenile(self):
        e = html.escape
        satir = ''.join(f'<tr><td style="padding:10px 14px 10px 0; vertical-align:top; width:30%"><b>{e(a)}</b></td>'
                        f'<td style="padding:10px 14px; vertical-align:top; color:{T.TURUNCU_2}; width:24%"><b>{e(n)}</b></td>'
                        f'<td style="padding:10px 0; vertical-align:top; color:#3A3D52">{e(h)}</td></tr>'
                        f'<tr><td colspan="3" style="border-bottom:1px solid {T.CIZGI}; font-size:2pt">&nbsp;</td></tr>' for a, n, h in NASIL)
        self.t_nasil.setHtml(f'<div style="font-size:10pt"><table width="100%" cellspacing="0">'
                             f'<tr><td style="color:{T.SOLUK}"><b>NE YAPMAK İSTİYORSUNUZ?</b></td><td style="color:{T.SOLUK}"><b>NEREYE</b></td>'
                             f'<td style="color:{T.SOLUK}"><b>NASIL</b></td></tr>{satir}</table></div>')
        self.t_kural.setHtml('<div style="font-size:10pt; line-height:150%">' + ''.join(
            f'<h3 style="color:{T.LACI}; margin-bottom:2px">{e(a)}</h3><p style="margin-top:2px">{e(m)}</p>' for a, m in KURALLAR) + '</div>')
