# -*- coding: utf-8 -*-
"""
Hesap motoru: giriş verisinden (personel + çalışma dönemleri, izin kayıtları, tatiller) kalan izin, hak satırları, kayıt başına
düşülen gün ve kontroller.

Kurallar hesapla.py'dedir (tek kaynak; KURAL sözlüğü). Bu modül tarih aralıklarını güne açar, önceki dönemin eksi kalanını taşır
ve dönem dışına yazılmış yıllık izni en yakın döneme düşer, "Elle düzeltme"yi kalana ekler; avans uyarısı hesapla.kayit_kalanlari,
kalanın kaynağı hesapla.yil_dokumu. Kayıt ve personel kontrolleri (eksik bilgi, çakışma, Pazar/tatile yazılmış izin …) de burada.

Aynı kişinin aynı güne iki yıllık izin kaydı varsa gün bir kez düşülür (kayıtta "çakışan kayıt" uyarısı çıkar).

Girdi (sözlükler; veritabani.Veritabani.veri() üretir):
  personel: {'id', 'ad', 'dogum', 'yas50', 'donemler': [(giris, cikis|None)], 'elle_duzeltme', 'onceki_ad', ...}
  izinler : {'id', 'no', 'personel_id', 'tur' (Kİ/RP/MZ/ÜZ/İD), 'bas', 'bit' (None = tek gün), 'iptal', ...}
  tatiller: {'tarih', 'ad', 'tur' ('tam' | 'yarim')}
"""
import collections
import datetime

from . import hesapla as H
from .yardimci import G1, KOD_AD, KODLAR, gunler, sayi_yaz, tarih_yaz, tr_anahtar, tr_buyuk

KURAL = H.KURAL
RAPOR_SINIR = [(182, 56), (548, 70), (1095, 84)]   # md.55/a: kıdem (gün) < eşik → bildirim süresi + 6 hafta (gün); üstü 98
UZUN_IZIN = 60


def tatil_sozlugu(tatiller):
    """{tarih: {'tarih', 'ad', 'tur'}}; aynı güne tam ve yarım varsa tam geçerli (yarım gün tam tatilde sayılmaz)."""
    t = {}
    for g in tatiller:
        d_ = g['tarih']
        if not d_ or g.get('tur') not in ('tam', 'yarim'):
            continue
        if d_ in t and t[d_]['tur'] == 'tam':
            continue
        t[d_] = {'tarih': d_.isoformat(), 'ad': g.get('ad') or '', 'tur': g['tur']}
    return t


def gun_agirligi(t, tatil):
    """Yıllık izinden düşülecek gün: Pazar ve tam gün tatil 0, yarım gün tatil (arife, 28 Ekim) 0,5, diğer 1."""
    if t.weekday() == 6 and not KURAL['pazar_sayilir']:
        return 0.0
    g = tatil.get(t)
    if g and g['tur'] == 'tam':
        return 0.0
    if g and g['tur'] == 'yarim':
        return KURAL['yarim_tatil_dusum']
    return 1.0


def is_basi(bit, tatil):
    """İşe dönüş: bitişten sonraki ilk gün (Pazar ve tam gün tatil değil)."""
    t = bit + G1
    while t.weekday() == 6 or (tatil.get(t) or {}).get('tur') == 'tam':
        t += G1
    return t


def _ad(s):
    return ' '.join(tr_buyuk(s).split())


# ----------------------------------------------------------------------------- personel kontrolleri
def personel_kontrol(p, ad_sayac, eski_sayac, bugun):
    """(hatalar, uyarilar). Hata varsa kişi hesaplanmaz ("Bilgi hatalı")."""
    hata, uyari = [], []
    ad = _ad(p['ad'])
    eski = _ad(p.get('onceki_ad'))
    if ad_sayac[ad] > 1:
        hata.append('Aynı ad iki kez yazılmış')
    if eski_sayac[ad] > 0:
        hata.append('Bu ad başka bir kişinin "Önceki ad"ı olarak da yazılı')
    if eski and ad_sayac[eski] + eski_sayac[eski] > 1:
        hata.append('Önceki ad başka bir kişinin adıyla aynı')
    don = p['donemler']
    if not don:
        hata.append('İşe giriş tarihi yok')
    for i, (g, c) in enumerate(don):
        n = i + 1
        if c is not None and c < g:
            hata.append(f'{n}. çıkış girişten önce')
        if i + 1 < len(don):
            if c is None:
                hata.append(f'{n + 1}. giriş var ama {n}. çıkış yok')
            elif don[i + 1][0] <= c:
                hata.append(f'{n + 1}. giriş {n}. çıkıştan sonra olmalı')
    aktif = bool(don) and (don[-1][1] is None or don[-1][1] >= bugun)
    dog = p.get('dogum')
    if dog is None and aktif:
        uyari.append('Doğum tarihi yok, 50 yaş beyanı kullanılıyor (doğum tarihini öğrenip yazın)' if p.get('yas50')
                     else 'Doğum tarihi yok (50 yaş kuralı için gerekli)')
    if dog is not None and don:
        fark = don[0][0].year - dog.year
        if dog > bugun or fark < 14 or fark > 80:
            uyari.append('Doğum tarihini kontrol edin (gelecekte ya da işe girişte yaş 14–80 dışında)')
    return hata, uyari


# ----------------------------------------------------------------------------- kişi hesabı
def _hak_aciklama(h, yas50_var):
    if h['gun'] > H.kidem_gunu(h['kidem']):
        if h.get('yas') is not None:
            return f'Hak tarihinde {h["yas"]} yaşında → en az {KURAL["yas_alt_sinir_gun"]} gün'
        return f'50 yaş üstü beyanı (doğum tarihi yok) → en az {KURAL["yas_alt_sinir_gun"]} gün'
    return f'Kıdem {h["kidem"]}. yıl → {h["gun"]} gün'


def _donemde_gun(bas, bit, donemler):
    n = 0
    for g, c in donemler:
        a, b = max(bas, g), min(bit, c or bit)
        if b >= a:
            n += (b - a).days + 1
    return n


def kisi_hesapla(p, kayitlar, tatil, bugun, hatalar=(), uyarilar=()):
    """Bir kişinin hesabı. kayitlar: kişinin bütün izin kayıtları (iptaller dahil). (kisi_sonuc, {kayit_id: kayit_sonuc})"""
    don = list(p['donemler'])
    gecerli = bool(don) and not hatalar
    duz = float(p.get('elle_duzeltme') or 0)
    ks = {'id': p['id'], 'ad': p['ad'], 'gecerli': gecerli, 'hatalar': list(hatalar), 'uyarilar': list(uyarilar),
          'aktif': False, 'durum': 'Bilgi hatalı', 'donemler': don, 'dogum': p.get('dogum'), 'yas50': p.get('yas50'),
          'yas': H.yas(p.get('dogum'), bugun), 'duz': duz, 'son_giris': don[-1][0] if don else None,
          'son_cikis': don[-1][1] if don else None, 'kalan': None, 'hak_son': None, 'kul_son': None, 'hak_top': None,
          'kul_top': None, 'kidem': None, 'tasinan_eksi': 0.0, 'sonraki_tarih': None, 'sonraki_gun': None, 'odenecek': None,
          'onceki_donem_kalan': None, 'hak_satirlari': [], 'yil_ozet': [], 'uyarili_kayit': 0, 'sonuc': None, 'yil_dokumu': None}
    kayitlar = sorted(kayitlar, key=lambda k: (k.get('no') or 0, k['id']))
    kr = {}
    gecerli_kayit = []
    for k in kayitlar:
        bas = k.get('bas')
        bit = k.get('bit') or bas
        s = {'id': k['id'], 'no': k.get('no'), 'gecerli': False, 'bas': bas, 'bit': bit, 'tur': k['tur'], 'iptal': bool(k.get('iptal')),
             'takvim_gunu': None, 'dusulen': None, 'dusulen_son': 0.0, 'kalan_sonra': None, 'isbasi': None, 'uyarilar': []}
        kr[k['id']] = s
        if s['iptal']:
            continue
        u = s['uyarilar']
        if not gecerli:
            u.append('Personel bilgisi hatalı/eksik: izin hesaba girmez')
        if k['tur'] not in KODLAR:
            u.append('İzin türü seçin')
        if bas is None:
            u.append('Başlangıç tarihi yazın')
        elif bit < bas:
            u.append('Bitiş başlangıçtan önce')
        if u:
            continue
        s['gecerli'] = True
        s['takvim_gunu'] = (bit - bas).days + 1
        s['isbasi'] = is_basi(bit, tatil)
        gecerli_kayit.append(k)
    if not gecerli:
        ks['uyarili_kayit'] = sum(1 for s in kr.values() if s['uyarilar'])
        return ks, kr

    # aralıklar güne açılır
    hk = []
    for k in gecerli_kayit:
        s = kr[k['id']]
        for t in gunler(s['bas'], s['bit']):
            hk.append({'yil': t.year, 'tarih': t.isoformat(), 'kod': k['tur'], 'gecerli_kod': True, 'hucre': k['id']})
    r = H.kisi_hesapla({'hareketler': hk}, don, p.get('dogum'), tatil, bugun, {}, yas50=p.get('yas50'),
                       avans_devri=KURAL['avans_devri'], donem_disi_dus=KURAL['donem_disi_dus'])
    son_i = len(r['donem_ozet']) - 1
    son = r['donem_ozet'][son_i]
    kalan = r['guncel_kalan'] + duz
    ks.update({'sonuc': r, 'aktif': r['aktif'], 'durum': 'Çalışıyor' if r['aktif'] else 'Ayrıldı', 'kalan': kalan,
               'hak_son': son['hak'], 'kul_son': son['kullanilan'], 'hak_top': r['toplam_hak'], 'kul_top': r['toplam_kullanilan'],
               'kidem': len(r['hak_edisler']), 'tasinan_eksi': r['tasinan_eksi'], 'odenecek': max(0.0, kalan)})
    if r['aktif'] and r['sonraki_hak']:
        ks['sonraki_tarih'] = r['sonraki_hak']['tarih']
        ks['sonraki_gun'] = r['sonraki_hak']['gun']
    if len(don) >= 2:
        ks['onceki_donem_kalan'] = (r['toplam_hak'] - son['hak']) - (r['toplam_kullanilan'] - son['kullanilan'])

    # kayıt başına düşülen gün (hesapla.py'nin gün düşümleri) ve avans uyarısı
    dus, dus_son = collections.defaultdict(float), collections.defaultdict(float)
    for x in r['kullanim']:
        if x['kod'] in KURAL['dusulen_kodlar']:
            dus[x['hucre']] += x['dusum']
            if x['donem'] == son_i:
                dus_son[x['hucre']] += x['dusum']
    kalanlar = H.kayit_kalanlari(r, [{'kod': k['tur'], 'bas': kr[k['id']]['bas'], 'bit': kr[k['id']]['bit']} for k in gecerli_kayit], duz)
    araliklar = [(kr[k['id']]['bas'], kr[k['id']]['bit'], k) for k in gecerli_kayit]
    for (bas, bit, k), kal in zip(araliklar, kalanlar):
        s = kr[k['id']]
        u = s['uyarilar']
        if k['tur'] in KURAL['dusulen_kodlar']:
            s['dusulen'] = dus[k['id']]
            s['dusulen_son'] = dus_son[k['id']]
        s['kalan_sonra'] = kal
        ic = _donemde_gun(bas, bit, don)
        if ic < s['takvim_gunu']:
            u.append('Çalışma dönemi dışında gün var — en yakın döneme düşüldü, tarihi kontrol edin'
                     if k['tur'] in KURAL['dusulen_kodlar'] else 'Çalışma dönemi dışında gün var')
        if any(b2 <= bit and e2 >= bas for b2, e2, k2 in araliklar if k2 is not k):
            u.append('Aynı kişinin tarihleri çakışan başka kaydı var')
        if k['tur'] in KURAL['dusulen_kodlar'] and ic > 0 and sum(gun_agirligi(t, tatil) for t in gunler(bas, bit)) == 0:
            u.append('Pazar/resmi tatil: izinden düşülmedi')
        if s['takvim_gunu'] > UZUN_IZIN:
            u.append(f'{UZUN_IZIN} günden uzun, tarihleri kontrol edin')
        if k['tur'] == 'RP':
            gir = max([g for g, _ in don if g <= bas], default=None)
            kidem_g = (bas - gir).days if gir else 10 ** 6
            sinir = next((g for e, g in RAPOR_SINIR if kidem_g < e), 98)
            if s['takvim_gunu'] > sinir:
                u.append(f'Rapor md.55/a sınırını ({sinir} gün) aşıyor: aşan günler izne hak kazanma tarihini öteler, '
                         f'aşan kısmı ayrı kayıtta Ücretsiz izin (ÜZ) olarak girin')
            if any(k2['tur'] == 'RP' and e2 == bas - G1 for b2, e2, k2 in araliklar if k2 is not k):
                u.append('Önceki gün biten başka rapor var: kesintisiz toplam md.55/a sınırını aşıyorsa aşan günleri ÜZ olarak girin')
        if kal is not None and kal < 0:
            u.append(f'Bu izinle kalan {sayi_yaz(kal)} güne düşüyor: hak edilmeden kullanılan (avans) izin')
    ks['uyarili_kayit'] = sum(1 for s in kr.values() if s['uyarilar'])

    # hak satırları (İzin Kartı) + kalanın kaynağı
    y_dok = H.yil_dokumu(r, bugun, duz)
    ks['yil_dokumu'] = y_dok
    fifo = {h['kidem']: h['kalan'] for h in y_dok['haklar']} if y_dok else {}
    uz = r['sayilmayan']
    onceki = don[0][0]
    for h in r['hak_edisler']:
        ks['hak_satirlari'].append({
            'kidem': h['kidem'], 'onceki': onceki, 'uz_gun': sum(1 for t in uz if onceki <= t < h['tarih']), 'tarih': h['tarih'],
            'yas': h['yas'], 'gun': h['gun'], 'aciklama': _hak_aciklama(h, p.get('yas50')), 'donem': h['donem'] + 1,
            'kalan': fifo.get(h['kidem']) if h['donem'] == son_i else None, 'durum': 'Kazanıldı'})
        onceki = h['tarih']
    if ks['sonraki_tarih']:
        sh = r['sonraki_hak']
        y = H.yas(p.get('dogum'), sh['tarih'])
        ks['hak_satirlari'].append({
            'kidem': sh['kidem'], 'onceki': onceki, 'uz_gun': sum(1 for t in uz if onceki <= t < sh['tarih']), 'tarih': sh['tarih'],
            'yas': y, 'gun': sh['gun'], 'aciklama': _hak_aciklama({'gun': sh['gun'], 'kidem': sh['kidem'], 'yas': y}, p.get('yas50')),
            'donem': son_i + 1, 'kalan': None, 'durum': 'Sonraki hak'})

    # yıllık özet (İzin Kartı): kazanılan, düşülen yıllık izin, diğer türlerin takvim günü, yıl sonu kalan
    ilk_yil = min([don[0][0].year] + [kr[k['id']]['bas'].year for k in gecerli_kayit])
    yillar = range(max(ilk_yil, bugun.year - 9), bugun.year + 2)
    kaz = collections.Counter()
    for h in r['hak_edisler']:
        kaz[h['tarih'].year] += h['gun']
    kul = collections.Counter()
    for x in r['kullanim']:
        if x['kod'] in KURAL['dusulen_kodlar'] and x['tarih']:
            kul[x['tarih'].year] += x['dusum']
    diger = collections.defaultdict(collections.Counter)
    for k in gecerli_kayit:
        if k['tur'] in ('RP', 'MZ', 'ÜZ', 'İD'):
            for t in gunler(kr[k['id']]['bas'], kr[k['id']]['bit']):
                diger[k['tur']][t.year] += 1
    bas_yil = son['baslangic'].year
    for y in yillar:
        if y > bugun.year:
            yk = None
        elif y < bas_yil:
            yk = '—'
        else:
            yk = y_dok['yil_sonu'].get(y) if y_dok else None
        ks['yil_ozet'].append({'yil': y, 'kazanilan': kaz[y], 'kullanilan': kul[y], 'RP': diger['RP'][y], 'MZ': diger['MZ'][y],
                               'ÜZ': diger['ÜZ'][y], 'İD': diger['İD'][y], 'kalan': yk})
    ks['eski_yillar_gizli'] = ilk_yil < bugun.year - 9
    return ks, kr


# ----------------------------------------------------------------------------- tüm veri
class Sonuc:
    """hesapla_hepsi çıktısı: kisi {personel_id: kisi_sonuc}, kayit {izin_id: kayit_sonuc}, sirali (çalışanlar önce, Türkçe alfabe)."""

    def __init__(self, bugun, tatil):
        self.bugun = bugun
        self.tatil = tatil
        self.kisi = {}
        self.kayit = {}
        self.sirali = []

    def calisanlar(self):
        return [k for k in self.sirali if k['aktif']]

    def ayrilanlar(self):
        return [k for k in self.sirali if not k['aktif'] and k['gecerli']]


def hesapla_hepsi(veri, bugun):
    tatil = tatil_sozlugu(veri['tatiller'])
    s = Sonuc(bugun, tatil)
    ad_sayac = collections.Counter(_ad(p['ad']) for p in veri['personel'])
    eski_sayac = collections.Counter(_ad(p.get('onceki_ad')) for p in veri['personel'] if p.get('onceki_ad'))
    kayitlar = collections.defaultdict(list)
    for k in veri['izinler']:
        kayitlar[k['personel_id']].append(k)
    for p in veri['personel']:
        h, u = personel_kontrol(p, ad_sayac, eski_sayac, bugun)
        ks, kr = kisi_hesapla(p, kayitlar.get(p['id'], []), tatil, bugun, h, u)
        s.kisi[p['id']] = ks
        s.kayit.update(kr)
    for k in veri['izinler']:  # kişisi olmayan kayıt (olmamalı; veritabanı engeller)
        if k['id'] not in s.kayit:
            s.kayit[k['id']] = {'id': k['id'], 'no': k.get('no'), 'gecerli': False, 'uyarilar': ['Personel listesinde yok'],
                                'bas': k.get('bas'), 'bit': k.get('bit') or k.get('bas'), 'tur': k['tur'], 'iptal': bool(k.get('iptal')),
                                'takvim_gunu': None, 'dusulen': None, 'dusulen_son': 0.0, 'kalan_sonra': None, 'isbasi': None}
    s.sirali = sorted(s.kisi.values(), key=lambda k: (0 if k['aktif'] else 1, tr_anahtar(k['ad'])))
    return s


def tek_kisi(veri, personel_id, bugun, ek_kayit=None, cikar_id=None):
    """İzin girerken canlı önizleme: yalnız bir kişinin hesabı; ek_kayit (henüz kaydedilmemiş) eklenir, cikar_id (düzenlenen kaydın
    eski hâli) çıkarılır. (kisi_sonuc, kayit_sonuclari)"""
    tatil = tatil_sozlugu(veri['tatiller'])
    p = next(x for x in veri['personel'] if x['id'] == personel_id)
    ad_sayac = collections.Counter(_ad(x['ad']) for x in veri['personel'])
    eski_sayac = collections.Counter(_ad(x.get('onceki_ad')) for x in veri['personel'] if x.get('onceki_ad'))
    h, u = personel_kontrol(p, ad_sayac, eski_sayac, bugun)
    kayitlar = [k for k in veri['izinler'] if k['personel_id'] == personel_id and k['id'] != cikar_id]
    if ek_kayit:
        kayitlar.append(ek_kayit)
    return kisi_hesapla(p, kayitlar, tatil, bugun, h, u)


# ----------------------------------------------------------------------------- görünümler
def ozet(s, veri):
    cal = s.calisanlar()
    bugun = s.bugun
    son_tatil = max((t['tarih'] for t in veri['tatiller']), default=None)
    uyarili = [k for k in s.kayit.values() if k['uyarilar'] and not k['iptal']]
    return {
        'calisan': len(cal),
        'toplam_kalan': sum(k['kalan'] for k in cal if k['kalan'] is not None),
        'eksi': sum(1 for k in cal if (k['kalan'] or 0) < 0),
        'birikmis': sum(1 for k in cal if (k['kalan'] or 0) > 30),
        'dogum_eksik': sum(1 for k in cal if k['dogum'] is None),
        'teyit_bekleyen': sum(1 for p in veri['personel'] if (p.get('teyit') or '').startswith('Teyit bekliyor')),
        'uyarili_kayit': len(uyarili),
        'personel_uyari': sum(1 for k in s.kisi.values() if k['hatalar'] or k['uyarilar']),
        'ayrilan': len(s.ayrilanlar()),
        'tatil_son_yil': son_tatil.year if son_tatil else None,
        'tatil_eksik': son_tatil is None or son_tatil.year < bugun.year + 1,
    }


def izindekiler(s, veri, bas, bit):
    """[bas, bit] aralığında izinde olan çalışanlar: [(kayit_sonuc, kisi_sonuc)] başlangıca göre."""
    out = []
    for k in veri['izinler']:
        r = s.kayit.get(k['id'])
        if not r or not r['gecerli']:
            continue
        if r['bas'] <= bit and r['bit'] >= bas:
            ks = s.kisi.get(k['personel_id'])
            if ks and ks['aktif']:
                out.append((r, ks))
    return sorted(out, key=lambda x: (x[0]['bas'], tr_anahtar(x[1]['ad'])))


def yaklasan_haklar(s, gun=60):
    son = s.bugun + datetime.timedelta(days=gun)
    out = [k for k in s.calisanlar() if k['sonraki_tarih'] and k['sonraki_tarih'] <= son]
    return sorted(out, key=lambda k: (k['sonraki_tarih'], tr_anahtar(k['ad'])))


def takvim(s, veri, yil, ay):
    """Aylık takvim: (gunler, satirlar). satir = {'kisi', 'hucre': [kod | '–' (çalışmıyor) | '!!' (aynı güne 2 kayıt) | ''],
    'kayit': [kayit_id | None], 'ozet': {Kİ: düşülen gün, RP.., İD..}}. Ayda en az bir gün çalışan geçerli kişiler."""
    from .yardimci import ay_gunleri
    gl = ay_gunleri(yil, ay)
    ilk, son = gl[0], gl[-1]
    gun_kayit = collections.defaultdict(lambda: collections.defaultdict(list))
    for k in veri['izinler']:
        r = s.kayit.get(k['id'])
        if not r or not r['gecerli'] or r['bit'] < ilk or r['bas'] > son:
            continue
        for t in gunler(max(r['bas'], ilk), min(r['bit'], son)):
            gun_kayit[k['personel_id']][t].append((k['tur'], k['id']))
    satirlar = []
    for ks in s.sirali:
        if not ks['gecerli']:
            continue
        don = ks['donemler']
        if not any(g <= son and (c is None or c >= ilk) for g, c in don):
            continue
        hucre, kayit = [], []
        oz = collections.Counter()
        for t in gl:
            lst = gun_kayit[ks['id']].get(t, [])
            calisiyor = any(g <= t and (c is None or t <= c) for g, c in don)
            if not lst:
                hucre.append('' if calisiyor else '–')
                kayit.append(None)
            elif len(lst) > 1:
                hucre.append('!!')
                kayit.append(lst[0][1])
            else:
                hucre.append(lst[0][0])
                kayit.append(lst[0][1])
                if lst[0][0] == 'Kİ':
                    oz['Kİ'] += gun_agirligi(t, s.tatil)
                else:
                    oz[lst[0][0]] += 1
        satirlar.append({'kisi': ks, 'hucre': hucre, 'kayit': kayit, 'ozet': oz})
    return gl, satirlar


def kayit_metni(k, ks=None):
    """Kısa açıklama: 'Yıllık izin · 12.05.2026–16.05.2026'"""
    bas, bit = k.get('bas'), k.get('bit') or k.get('bas')
    ara = tarih_yaz(bas) if bas == bit else f'{tarih_yaz(bas)}–{tarih_yaz(bit)}'
    return f'{KOD_AD.get(k["tur"], k["tur"])} · {ara}'
