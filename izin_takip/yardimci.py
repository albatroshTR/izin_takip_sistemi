# -*- coding: utf-8 -*-
"""Arayüz ve hesapta ortak küçük yardımcılar: tarih/sayı biçimi, Türkçe sıralama ve arama."""
import datetime
import re

D = datetime.date
G1 = datetime.timedelta(days=1)


class VeriHatasi(ValueError):
    """Kullanıcıya gösterilecek anlaşılır hata (geçersiz giriş, hatalı parola, açılamayan dosya)."""


AYLAR = ['Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık']
GUN_ADLARI = ['Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar']
GUN_KISA = ['Pt', 'Sa', 'Ça', 'Pe', 'Cu', 'Ct', 'Pz']

KODLAR = ['Kİ', 'RP', 'MZ', 'ÜZ', 'İD']
KOD_AD = {'Kİ': 'Yıllık izin', 'RP': 'Rapor', 'MZ': 'Mazeret izni', 'ÜZ': 'Ücretsiz izin', 'İD': 'İdari izin'}
# (zemin, yazı) takvim ve rozet renkleri
KOD_RENK = {'Kİ': ('#DCF5E3', '#11643A'), 'RP': ('#FDE0E3', '#9C1C2B'), 'MZ': ('#FFF1C9', '#8A5A00'),
            'ÜZ': ('#E7E8EE', '#3A3D4D'), 'İD': ('#DCE9FB', '#1D4F91')}

TEYIT_SECENEK = ['Teyitli', 'Teyit bekliyor', 'Teyit bekliyor (dönem otomatik)']
TR_ALFABE = 'ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVWXYZ'


def tr_buyuk(s):
    return (s or '').replace('i', 'İ').replace('ı', 'I').upper()


def tr_anahtar(s):
    """Türkçe alfabe sırası (ad listeleri için)."""
    return [TR_ALFABE.index(c) if c in TR_ALFABE else 100 + ord(c) for c in tr_buyuk(s)]


_SADE = str.maketrans('çğıöşüâîû', 'cgiosuaiu')


def ara_normal(s):
    """Aramada Türkçe karakter ve büyük/küçük harf farkını yok sayar: 'cagri' → 'ÇAĞRI' ile eşleşir."""
    s = (s or '').replace('İ', 'i').replace('I', 'ı').lower()
    return re.sub(r'\s+', ' ', s.translate(_SADE)).strip()


def ara_eslesir(sorgu, *metinler):
    q = ara_normal(sorgu)
    if not q:
        return True
    hepsi = ' '.join(ara_normal(m) for m in metinler if m)
    return all(parca in hepsi for parca in q.split(' '))


def tarih_yaz(d, bos=''):
    if d is None:
        return bos
    return f'{d.day:02d}.{d.month:02d}.{d.year}'


def tarih_iso(d):
    return d.isoformat() if d else None


def tarih_oku(s):
    """'25.09.2026', '25/9/26', '25092026', '2026-09-25' → date; boş → None; geçersiz → ValueError."""
    if s is None:
        return None
    if isinstance(s, datetime.datetime):
        return s.date()
    if isinstance(s, D):
        return s
    s = str(s).strip()
    if not s:
        return None
    if re.fullmatch(r'\d{4}-\d{2}-\d{2}', s):
        return D.fromisoformat(s)
    if re.fullmatch(r'\d{8}', s):
        g, a, y = int(s[:2]), int(s[2:4]), int(s[4:])
    else:
        m = re.fullmatch(r'(\d{1,2})[.\-/ ](\d{1,2})[.\-/ ](\d{2}|\d{4})', s)
        if not m:
            raise ValueError(f'Tarih anlaşılamadı: {s!r} (gün.ay.yıl yazın, ör. 25.09.2026)')
        g, a, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if y < 100:
            y += 2000 if y < 70 else 1900
    return D(y, a, g)


def iso_oku(s):
    return D.fromisoformat(s) if s else None


def sayi_yaz(x, bos=''):
    """14.0 → '14', 19.5 → '19,5', -3 → '−3' değil '-3'."""
    if x is None or x == '':
        return bos
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    if isinstance(x, float):
        x = round(x, 2)
    return str(x).replace('.', ',')


def gun_yaz(x, bos=''):
    s = sayi_yaz(x, bos)
    return f'{s} gün' if s != bos else bos


def para_yaz(x, bos=''):
    if x is None or x == '':
        return bos
    s = f'{x:,.2f}'
    return s.replace(',', 'X').replace('.', ',').replace('X', '.') + ' TL'


def ay_gunleri(yil, ay):
    ilk = D(yil, ay, 1)
    son = D(yil + (ay == 12), ay % 12 + 1, 1) - G1
    return [ilk + datetime.timedelta(days=i) for i in range((son - ilk).days + 1)]


def gunler(bas, bit):
    t = bas
    while t <= bit:
        yield t
        t += G1
