# -*- coding: utf-8 -*-
"""
Uydurma örnek veri: programı denemek, ekran görüntüsü almak ve sınamalar için. Gerçek kişi ya da işyeri verisi içermez;
adlar, tarihler ve izinler tamamen kurgusaldır (aynı tohumla her çalıştırmada aynı veri üretilir).

uret() → veritabani.Veritabani.veri_yukle() biçiminde {'personel', 'izinler', 'tatiller', 'odemeler', 'ayar'}.
Kapsadığı durumlar: yeni ve kıdemli çalışanlar, 50 yaş üstü (en az 20 gün), kesintili çalışma (iki dönem), işten ayrılan ve ödenmemiş
izin ücreti, hak edilmeden kullanılan (avans) izin, rapor / mazeret / ücretsiz / idari izin, iptal edilmiş kayıt.
"""
import datetime
import json
import random

from .yardimci import tr_buyuk
from .yollar import kaynak

D = datetime.date

# (ad, doğum, [(giriş, çıkış)], not)
KISILER = [
    ('Ayşe Örnek', D(1985, 4, 12), [(D(2012, 3, 5), None)], None),
    ('Mehmet Deneme', D(1972, 9, 30), [(D(2008, 9, 1), None)], 'Kıdemli çalışan: 15. hizmet yılından sonra 26 gün hak eder.'),
    ('Fatma Sınama', D(1990, 1, 20), [(D(2019, 6, 3), None)], None),
    ('Ali Demo', D(1974, 11, 8), [(D(2016, 2, 15), None)], '50 yaşını doldurdu: bu tarihten sonra kazanılan hak en az 20 gündür.'),
    ('Zeynep Kurgu', D(1998, 7, 2), [(D(2022, 9, 12), None)], None),
    ('Hasan Taslak', D(1988, 12, 25), [(D(2014, 4, 1), D(2017, 8, 31)), (D(2021, 3, 1), None)],
     'Kesintili çalışma: önceki dönem kıdeme eklenir, her dönemin kalanı ayrı izlenir.'),
    ('Elif Yapay', D(1995, 5, 17), [(D(2020, 10, 19), None)], None),
    ('Mustafa Deneysel', D(1980, 3, 9), [(D(2010, 1, 11), None)], None),
    ('Merve Simülasyon', D(2001, 8, 21), [(D(2025, 3, 11), None)], 'Yeni başladı; hak edilmeden kullanılan (avans) izin örneği.'),
    ('Burak Numune', D(1993, 10, 4), [(D(2018, 5, 14), D(2025, 11, 28))], 'İşten ayrılan örneği: çıkışta kullanılmayan izin ücreti ödenir (md.59).'),
    ('Selin Prototip', D(1999, 2, 14), [(D(2023, 1, 16), None)], None),
    ('Kemal Örnekoğlu', D(1968, 6, 28), [(D(2005, 7, 4), None)], 'Hizmet süresi uzun, 50 yaş üstü.'),
]
SIRKET = 'Örnek Şirket A.Ş.'


def _is_gunleri(bas, adet):
    """bas'tan başlayıp Pazar'ı atlayarak `adet` günlük (Pazartesi–Cumartesi) bir aralığın bitişini verir."""
    t, kalan = bas, adet - 1
    while kalan > 0:
        t += datetime.timedelta(days=1)
        if t.weekday() != 6:
            kalan -= 1
    return t


def _pazartesi(t):
    return t + datetime.timedelta(days=(7 - t.weekday()) % 7)


def _hak(hizmet_yili):
    return 14 if hizmet_yili <= 5 else 20 if hizmet_yili <= 14 else 26


def uret(son_tarih=D(2026, 10, 20)):
    rng = random.Random(2026)
    personel, izinler = [], []
    no = 0
    for pid, (ad, dogum, donemler, not_) in enumerate(KISILER, start=1):
        personel.append({'id': pid, 'ad': tr_buyuk(ad), 'dogum': dogum, 'donemler': donemler,
                         'not_ozet': not_, 'not_metni': not_})
        if pid == 9:   # avans örneği: izinleri aşağıda elle yazılı
            continue
        for giris, cikis in donemler:
            son = cikis or son_tarih
            for yil in range(giris.year + 1, son.year + 1):
                if cikis and yil == cikis.year:   # ayrılan kişinin son yılının hakkı kullanılmadı: çıkışta ücret olarak ödenir
                    continue
                hak_tarihi = D(yil, giris.month, min(giris.day, 28))
                kullanilacak = _hak(yil - giris.year) - rng.choice([0, 0, 2, 4])
                bloklar = [kullanilacak] if kullanilacak <= 10 else [kullanilacak // 2, kullanilacak - kullanilacak // 2]
                sinir = min(son, D(yil, 12, 15))
                for i, gun in enumerate(bloklar):
                    bas = _pazartesi(hak_tarihi + datetime.timedelta(days=21 + 75 * i + rng.randint(0, 40)))
                    bit = _is_gunleri(bas, gun)
                    if bit > sinir:
                        continue
                    no += 1
                    izinler.append({'id': no, 'no': no, 'personel_id': pid, 'tur': 'Kİ', 'bas': bas, 'bit': bit,
                                    'aciklama': 'Örnek yıllık izin', 'giren': 'örnek veri',
                                    'yazildigi': bas - datetime.timedelta(days=10)})
    ek = [  # (kişi, tür, başlangıç, bitiş, açıklama, iptal)
        (1, 'RP', D(2026, 2, 16), D(2026, 2, 20), 'Örnek istirahat raporu', False),
        (3, 'MZ', D(2025, 4, 14), D(2025, 4, 16), 'Örnek mazeret izni (evlilik)', False),
        (5, 'ÜZ', D(2025, 6, 9), D(2025, 6, 13), 'Örnek ücretsiz izin: hak tarihini öteler', False),
        (7, 'İD', D(2025, 12, 31), None, 'Örnek idari izin (yıllık izinden düşülmez)', False),
        (8, 'Kİ', D(2026, 9, 21), D(2026, 9, 26), 'Vazgeçildi', True),
        (9, 'Kİ', D(2026, 6, 15), D(2026, 7, 4), 'Avans izin örneği: hak edilmeden kullanıldı', False),
    ]
    for kisi, tur, bas, bit, aciklama, iptal in ek:
        no += 1
        izinler.append({'id': no, 'no': no, 'personel_id': kisi, 'tur': tur, 'bas': bas, 'bit': bit, 'aciklama': aciklama,
                        'giren': 'örnek veri', 'yazildigi': bas - datetime.timedelta(days=7), 'iptal': iptal})
    with open(kaynak('tatiller.json'), encoding='utf-8') as f:
        tatiller = [{'tarih': D.fromisoformat(t['tarih']), 'ad': t['ad'], 'tur': t['tur']} for t in json.load(f)]
    odemeler = [{'personel_id': 10, 'ucret': 30000.0, 'odendi': 'Ödenmedi', 'odeme_tarihi': None, 'odenen': None}]
    return {'personel': personel, 'izinler': izinler, 'tatiller': tatiller, 'odemeler': odemeler, 'ayar': {'sirket': SIRKET}}


def resmi_tatiller():
    """Pakete konan resmî tatil listesi (2019–2030): boş başlayan kurulumda da yüklenir."""
    with open(kaynak('tatiller.json'), encoding='utf-8') as f:
        return [{'tarih': D.fromisoformat(t['tarih']), 'ad': t['ad'], 'tur': t['tur']} for t in json.load(f)]
