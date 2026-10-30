# -*- coding: utf-8 -*-
"""
Yasal yıllık izin hak ediş, kullanım ve bakiye hesabı (4857 sayılı İş Kanunu md.53–60, Yıllık Ücretli İzin Yönetmeliği).
Saf hesap modülüdür: dosya ya da veritabanı okumaz; motor.py girdileri hazırlayıp buradaki fonksiyonları çağırır.
Kurallar docs/hesap-kurallari.md dosyasındadır; burada KURAL sözlüğünde parametre olarak yer alır.
"""
import datetime
import collections
import sys

if hasattr(sys.stdout, 'reconfigure'):  # pencereli (konsolsuz) Windows programinda sys.stdout None olur
    sys.stdout.reconfigure(encoding='utf-8')
D = datetime.date
GUNLER = ['Pzt', 'Sal', 'Çar', 'Per', 'Cum', 'Cmt', 'Paz']

# ----------------------------------------------------------------------------- KURALLAR
KURAL = {
    # 4857 md.53: hizmet suresi 1-5 yil (5 dahil) 14 gun; 5'ten fazla 15'ten az 20 gun; 15 (dahil) ve fazlasi 26 gun
    'kidem_basamaklari': [(1, 5, 14), (6, 14, 20), (15, 99, 26)],
    # 4857 md.53/son: 18 ve daha kucuk / 50 ve daha yukari yastakilere en az 20 gun
    'yas_alt_sinir_gun': 20, 'yas_ust_esik': 50, 'yas_alt_esik': 18,
    # yasin degerlendirildigi an: 'hak_kazanma' = izne hak kazanilan yildonumu
    'yas_referans': 'hak_kazanma',
    # md.56: hafta tatili, ulusal bayram ve genel tatil izin suresinden sayilmaz
    'pazar_sayilir': False, 'cumartesi_sayilir': True,
    # arife / 28 Ekim yarim gun: izin gunu olarak ne kadar dusulur
    'yarim_tatil_dusum': 0.5,
    # md.54: ayni isverendeki onceki calisma sureleri kidem basamagi ve hak kazanma icin birlestirilir mi
    'kesintili_birlestir': True,
    # Yillik izinden dusulen kodlar
    'dusulen_kodlar': ['Kİ'],
    # Onceki calisma doneminin EKSI kalani (hak edilmeden kullanilan izin) yeni doneme otomatik tasinir. Zincir: b_k = hak_k - kullanilan_k + tasinan_(k-1); tasinan_k = MIN(0, b_k).
    # Arti kalan bu yolla tasinmaz; yalniz onceki_donem_ucreti='odenmedi' ise devir olarak eklenir (cift sayim yok).
    'avans_devri': True,
    # Calisma donemi disindaki yillik izin (Ki) gunleri en yakin doneme dusulur:
    # ilk donemden once -> ilk donem; iki donem arasi -> takvimce yakin olan (esitlikte onceki); kapanmis son donemden sonra -> son donem.
    # Dusum miktari ayni (Pazar/tam tatil 0, yarim gun 0,5); hak tarihlerini etkilemez.
    'donem_disi_dus': True,
    # Iki kural herkese (calisan ve ayrilan) uygulanir; motor.py ikisini de acik cagirir.
    # kisi_hesapla varsayilani kapali (acik parametreyle cagrilir; testler icin).
}


def tarih(s):
    return D.fromisoformat(s) if s else None


def yil_ekle(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 Subat
        return d.replace(year=d.year + n, day=28)


def yas(dogum, an):
    if not dogum:
        return None
    return an.year - dogum.year - ((an.month, an.day) < (dogum.month, dogum.day))


def kidem_gunu(kidem):
    for a, b, g in KURAL['kidem_basamaklari']:
        if a <= kidem <= b:
            return g
    return 0


def hak_gunu(kidem, y, yas50_beyan=False):
    """yas50_beyan: dogum tarihi bilinmiyor ama kisinin bu hak tarihinde 50 yas ve ustunde oldugu beyan edilmis
    (Personel > 50 yas beyani). Dogum tarihi biliniyorsa (y dolu) beyan dikkate alinmaz."""
    g = kidem_gunu(kidem)
    gerekce = f'{kidem}. hizmet yılı → {g} gün (md.53 kıdem)'
    if y is not None and y < 0:  # dogum tarihi hak tarihinden sonra: veri hatasi, yas kurali uygulanmaz
        y = None
    if y is not None and (y >= KURAL['yas_ust_esik'] or y <= KURAL['yas_alt_esik']) and g < KURAL['yas_alt_sinir_gun']:
        g = KURAL['yas_alt_sinir_gun']
        gerekce += f'; hak kazanma tarihinde {y} yaşında → en az {g} gün (md.53 yaş kuralı)'
    elif y is not None and (y >= KURAL['yas_ust_esik'] or y <= KURAL['yas_alt_esik']):
        gerekce += f'; {y} yaşında (yaş kuralı sonucu değiştirmiyor)'
    elif y is None and yas50_beyan and g < KURAL['yas_alt_sinir_gun']:
        g = KURAL['yas_alt_sinir_gun']
        gerekce += f'; doğum tarihi yok, {KURAL["yas_ust_esik"]} yaş üstü beyanı → en az {g} gün (md.53 yaş kuralı; teyit edilmeli)'
    return g, gerekce


def beyan_var(yas50, dogum, t):
    """Dogum tarihi yoksa ve beyan baslangici t'den once/ayni gunse True."""
    return dogum is None and yas50 is not None and t >= yas50


def fmt(d):
    return d.strftime('%d.%m.%Y') if isinstance(d, (D, datetime.datetime)) else ('—' if d is None else str(d))


def sayi(x):
    if x is None:
        return '—'
    if isinstance(x, float) and x.is_integer():
        x = int(x)
    return str(x).replace('.', ',')


def tatil_sozlugu(tat):
    t = {}
    for g in tat['gunler']:
        t[D.fromisoformat(g['tarih'])] = g
    return t


# ----------------------------------------------------------------------------- DONEM / HAK EDIS
def _yildonumleri(donemler, sayilmayan, sinir):
    """md.54 + Yonetmelik md.4/2: ayni isverendeki donemler birlestirilir, aradaki bosluk ve sayilmayan gunler
    (ucretsiz izin vb., md.54/2) hizmete eklenmez. Gun gun sayilir: sayilan hizmet gunu, ilk girisin n yillik
    takvim uzunluguna ulastigi gunun ertesi n. hak kazanma tarihidir (surekli calismada = giris + n yil).
    kesintili_birlestir=False ise her donem kendi girisinden bagimsiz sayilir.
    sinir: hak kazanma tarihi en fazla bu olabilir. [(donem_index, tarih, n)] dondurur."""
    out = []
    if not donemler:
        return out
    bir = datetime.timedelta(days=1)
    sayilmayan = set(sayilmayan)
    gruplar = [list(range(len(donemler)))] if KURAL['kesintili_birlestir'] else [[i] for i in range(len(donemler))]
    for grup in gruplar:
        taban = donemler[grup[0]][0]
        son_gun = sinir - bir
        e_son = donemler[grup[-1]][1]
        if e_son is not None:
            son_gun = min(son_gun, e_son)
        # md.54/3: her yil bir onceki hak kazanma tarihinden baslayarak sayilir
        sayilan = 0
        n = 1
        onceki = taban
        gerekli = (yil_ekle(onceki, 1) - onceki).days
        d = taban
        j = 0  # grup icindeki aktif donem
        while d <= son_gun:
            while j < len(grup) and donemler[grup[j]][1] is not None and d > donemler[grup[j]][1]:
                j += 1
            if j >= len(grup):
                break
            b, e = donemler[grup[j]]
            if d < b:  # bosluk: bir sonraki donem baslangicina atla
                d = b
                continue
            if d not in sayilmayan:
                sayilan += 1
                if sayilan >= gerekli:
                    out.append((grup[j], d + bir, n))
                    n += 1
                    onceki = d + bir
                    sayilan = 0
                    gerekli = (yil_ekle(onceki, 1) - onceki).days
            d += bir
    return out


def hak_edisler(donemler, dogum, bugun, sayilmayan=(), yas50=None):
    """Yildonumu bazinda hak edisler (sadece bugune ve donem bitisine kadar)."""
    olaylar = []
    for idx, t, n in _yildonumleri(donemler, sayilmayan, bugun):
        y = yas(dogum, t)
        g, ger = hak_gunu(n, y, beyan_var(yas50, dogum, t))
        olaylar.append({'donem': idx, 'tarih': t, 'kidem': n, 'yas': y, 'gun': g, 'gerekce': ger})
    return olaylar


def sonraki_hak(donemler, dogum, bugun, sayilmayan=(), yas50=None):
    bas, bit = donemler[-1]
    if bit and bit < bugun:
        return None
    acik = donemler[:-1] + [(bas, None)]
    for idx, t, n in _yildonumleri(acik, sayilmayan, bugun + datetime.timedelta(days=366 * 45)):
        if t > bugun:
            g, ger = hak_gunu(n, yas(dogum, t), beyan_var(yas50, dogum, t))
            return {'tarih': t, 'kidem': n, 'gun': g, 'gerekce': ger}
    return None


def donemde(t, donemler):
    for i, (b, e) in enumerate(donemler):
        if t >= b and (e is None or t <= e):
            return i
    return None


def en_yakin_donem(t, donemler):
    """Calisma donemi disindaki gunun dusulecegi donem (KURAL['donem_disi_dus']): ilk donemden once -> ilk; iki donem arasinda ->
    takvimce yakin olan (esitlikte onceki); kapanmis son donemden sonra -> son.
    Bolumleme: donem k'nin genisletilmis araligi [onceki sinir + 1, INT((cikis_k + giris_(k+1)) / 2)]."""
    if t < donemler[0][0]:
        return 0
    for i in range(len(donemler) - 1):
        e, b2 = donemler[i][1], donemler[i + 1][0]
        if e is not None and e < t < b2:
            return i if (t - e).days <= (b2 - t).days else i + 1
    return len(donemler) - 1


# ----------------------------------------------------------------------------- KISI HESABI
def sayilmayan_gunler(K, donemler, tatil):
    """md.54/2: md.55'te sayilmayan sebeplerle calisilmayan gunler hak kazanma tarihini oteler.
    Kayitlarda karsiligi: UZ (ucretsiz izin). Pazar ve tam gun resmi tatil zaten calisilmis sayildigi (md.55/f) icin haric."""
    out = set()
    for h in K['hareketler']:
        if h['kod'] != 'ÜZ' or not h['tarih']:
            continue
        t = tarih(h['tarih'])
        tt = tatil.get(t)
        if t.weekday() == 6 or (tt and tt['tur'] == 'tam'):
            continue
        if donemde(t, donemler) is not None:
            out.add(t)
    return out


def kisi_hesapla(K, donemler, dogum, tatil, bugun, yillar, yas50=None, devir=False, avans_devri=False, donem_disi_dus=False, elle_duzeltme=0.0):
    """yas50: dogum tarihi yoksa 50 yas ustu beyaninin gecerli oldugu ilk tarih.
    devir: onceki calisma donemlerinin cikista odenmeyen arti kalani guncel doneme eklenir (md.59 alacagi).
    avans_devri: onceki donemin eksi kalani sonrakine tasinir (KURAL['avans_devri']).
    donem_disi_dus: calisma donemi disindaki yillik izin gunleri en yakin doneme dusulur (KURAL['donem_disi_dus']).
    elle_duzeltme: guncel doneme eklenen/dusulen gun (Personel > Elle duzeltme; ör. onceki kayitlardan devreden ya da kullanilmis sayilan gun).
    Varsayilan kapali; motor.py acar."""
    uz = sayilmayan_gunler(K, donemler, tatil)
    hk = hak_edisler(donemler, dogum, bugun, uz, yas50)
    kullanim = []
    uyarilar = []
    gorulen = {}
    for h in K['hareketler']:
        t = tarih(h['tarih'])
        kod = h['kod']
        kayit = {'tarih': t, 'kod': kod, 'hucre': h['hucre'], 'yil': h['yil'], 'dusum': 0.0, 'durum': [], 'donem': None}
        if t is None:
            kayit['durum'].append('GEÇERSİZ TARİH (ayda olmayan gün)')
            kullanim.append(kayit)
            continue
        anahtar = t
        if anahtar in gorulen:
            onceki = gorulen[anahtar]
            if onceki['kod'] == kod:
                kayit['durum'].append(f'MÜKERRER: aynı gün başka satırda da {kod} var ({onceki["hucre"]}) — bir kez sayıldı')
                kayit['mukerrer'] = True
                kullanim.append(kayit)
                continue
            else:
                kayit['durum'].append(f'ÇAKIŞMA: aynı gün başka satırda {onceki["kod"]} kodu var ({onceki["hucre"]})')
        gorulen[anahtar] = kayit
        kayit['donem'] = donemde(t, donemler)
        tat = tatil.get(t)
        if kayit['donem'] is None and donem_disi_dus and donemler and kod in KURAL['dusulen_kodlar']:
            kayit['donem'] = en_yakin_donem(t, donemler)
            kayit['donem_disi_atandi'] = True
            b_, e_ = donemler[kayit['donem']]
            kayit['durum'].append(f'ÇALIŞMA DÖNEMİ DIŞINDA — en yakın döneme ({fmt(b_)}–{fmt(e_) if e_ else "devam"}) düşüldü')
        elif kayit['donem'] is None:
            kayit['durum'].append('ÇALIŞMA DÖNEMİ DIŞINDA (işe girişten önce / çıkıştan sonra)')
        if not h['gecerli_kod']:
            kayit['durum'].append(f'GEÇERSİZ KOD {kod!r}')
        if kod in KURAL['dusulen_kodlar']:
            if t.weekday() == 6 and not KURAL['pazar_sayilir']:
                kayit['durum'].append('PAZAR (hafta tatili) — izinden düşülemez')
            elif tat and tat['tur'] == 'tam':
                kayit['tatil_adi'] = tat['ad']
                kayit['durum'].append(f'RESMİ TATİL ({tat["ad"]}) — izinden düşülemez')
            elif tat and tat['tur'] == 'yarim':
                kayit['tatil_adi'] = tat['ad']
                kayit['dusum'] = KURAL['yarim_tatil_dusum']
                kayit['durum'].append(f'YARIM GÜN TATİL ({tat["ad"]}) — {sayi(KURAL["yarim_tatil_dusum"])} gün düşüldü')
            else:
                kayit['dusum'] = 1.0
            if kayit['donem'] is None:
                kayit['dusum_donem_disi'] = kayit['dusum']
                kayit['dusum'] = 0.0
        kullanim.append(kayit)
    # donem bazinda ozet; onceki donemin eksi kalani (avans) sonrakine tasinir (KURAL['avans_devri']):
    # eksi_devralinan = onceki donemden gelen eksi (<= 0), kalan = hak - kullanilan + eksi_devralinan, eksi_devreden = MIN(0, kalan)
    donem_ozet = []
    tasinan = 0
    for i, (b, e) in enumerate(donemler):
        kazan = sum(x['gun'] for x in hk if x['donem'] == i)
        kul = sum(x['dusum'] for x in kullanim if x['donem'] == i)
        dz = {'donem': i, 'baslangic': b, 'bitis': e, 'hak': kazan, 'kullanilan': kul, 'kalan': kazan - kul + tasinan,
              'devralinan': 0, 'devreden': 0, 'eksi_devralinan': tasinan, 'eksi_devreden': 0}
        if avans_devri and i < len(donemler) - 1:
            tasinan = min(0, dz['kalan'])
            dz['eksi_devreden'] = tasinan
        donem_ozet.append(dz)
    # cikista odenmeyen onceki donem kalani (yalniz arti kalan; hak edilmeden kullanilan eksi kalan geri istenemez)
    devir_gun = 0
    if devir and len(donem_ozet) > 1:
        for dz in donem_ozet[:-1]:
            if dz['kalan'] > 0:
                dz['devreden'] = dz['kalan']
                devir_gun += dz['kalan']
        donem_ozet[-1]['devralinan'] = devir_gun
        donem_ozet[-1]['kalan'] += devir_gun
    if elle_duzeltme and donem_ozet:
        donem_ozet[-1]['elle_duzeltme'] = elle_duzeltme
        donem_ozet[-1]['kalan'] += elle_duzeltme
    toplam_hak = sum(x['gun'] for x in hk)
    toplam_kul = sum(x['dusum'] for x in kullanim)
    son_donem = donem_ozet[-1] if donem_ozet else None
    aktif = son_donem is not None and (son_donem['bitis'] is None or son_donem['bitis'] >= bugun)
    return {'hak_edisler': hk, 'kullanim': kullanim, 'donem_ozet': donem_ozet, 'toplam_hak': toplam_hak, 'sayilmayan': sorted(uz),
            'toplam_kullanilan': toplam_kul, 'aktif': aktif, 'devir': devir_gun,
            'elle_duzeltme': elle_duzeltme if donem_ozet else 0.0, 'duzeltme': devir_gun + (elle_duzeltme if donem_ozet else 0.0),
            'tasinan_eksi': son_donem['eksi_devralinan'] if son_donem else 0,
            'guncel_kalan': son_donem['kalan'] if son_donem else None,
            'sonraki_hak': sonraki_hak(donemler, dogum, bugun, uz, yas50) if donemler else None}


def yil_dokumu(r, bugun, duzeltme=None):
    """Kalan iznin kaynagi: hangi hak yilindan ne kadar kaldigi (en eski hak once kullanilir) + yil sonu kalanlari.
    Yalniz GUNCEL (son) calisma donemi; kisi_hesapla sonucunu degistirmez (Izin Karti'ndaki dokum):
      U   = guncel donemde dusulen yillik izin (ileri tarihli dahil),
      duz = Personel 'Elle duzeltme' (varsayilan r['devir'] = onceki donemden odenmeyen kalan),
      T   = onceki donem(ler)den tasinan eksi (r['tasinan_eksi'] <= 0; KURAL['avans_devri']).
      Arti duz en eski kova sayilir; eksi duz ve T kullanim gibi en eski haklardan duser. Hepsinde
      bu haktan kalan_i = MIN(h_i, MAX(0, duz + T + kumulatif_hak_i - U)); kalan eksiyse (avans) hepsi 0.
      yil_sonu[Y] (Y = guncel donemin baslangic yili .. hesap yili):
        Y < hesap yili : 31.12.Y'ye kadar kazanilan - 31.12.Y'ye kadar dusulen + duz + T
        Y = hesap yili : guncel kalan (hesap tarihinde; ileri tarihli izinler dusulmus) — Genel Durum'daki KALAN ile ayni."""
    if not r['donem_ozet']:
        return None
    son = len(r['donem_ozet']) - 1
    bas = r['donem_ozet'][son]['baslangic']
    duz = r.get('duzeltme', r['devir']) if duzeltme is None else duzeltme
    t = r['donem_ozet'][son]['eksi_devralinan']
    haklar = [h for h in r['hak_edisler'] if h['donem'] == son]
    kul = [k for k in r['kullanim'] if k['donem'] == son and k['dusum']]
    u = sum(k['dusum'] for k in kul)
    kum, liste = 0, []
    for h in haklar:
        kum += h['gun']
        liste.append({'tarih': h['tarih'], 'kidem': h['kidem'], 'gun': h['gun'], 'kalan': min(h['gun'], max(0, duz + t + kum - u))})
    kalan = kum - u + duz + t
    yil_sonu = {}
    for y in range(bas.year, bugun.year + 1):
        if y == bugun.year:
            yil_sonu[y] = kalan
        else:
            son_gun = D(y, 12, 31)
            yil_sonu[y] = (sum(h['gun'] for h in haklar if h['tarih'] <= son_gun)
                           - sum(k['dusum'] for k in kul if k['tarih'] <= son_gun) + duz + t)
    return {'haklar': liste, 'kullanilan': u, 'duzeltme': duz, 'tasinan_eksi': t,
            'duzeltme_kalan': min(duz, max(0, duz + t - u)) if duz > 0 else 0,
            'kalan': kalan, 'avans': kalan < 0, 'donem_baslangic': bas, 'yil_sonu': yil_sonu}


def kayit_kalanlari(r, araliklar, duzeltme=None):
    """Izin kaydi bazinda avans uyarisi icin kalan: kayit girildigi anda kisinin kalani.
    araliklar: kisinin izin kayitlari (liste sirasiyla) [{'kod', 'bas', 'bit'}]. Yalniz calisan (aktif) kiside ve
    guncel donemde dusulen gunu olan yillik izin kaydinda hesaplanir; digerleri None.
    kalan (o kayit dahil, tarih sirasiyla) = elle duzeltme + onceki donemden tasinan eksi
        + guncel donemde kazanilmis haklar (hak tarihi <= kaydin bitisi) + siradaki hak (tarihi <= bitis ise; ileri tarihli izin)
        - guncel donemde, bu kayda kadar (baslangic, sonra satir sirasi) dusulen gunler.
    Kayit gunleri kisi_hesapla'nin gun dusumlerinden alinir (Pazar/tatil/yarim gun, donem disi -> en yakin donem ayni)."""
    if not r['donem_ozet'] or not r['aktif']:
        return [None] * len(araliklar)
    son = len(r['donem_ozet']) - 1
    duz = r.get('duzeltme', r['devir']) if duzeltme is None else duzeltme
    gunluk = collections.defaultdict(float)
    for k in r['kullanim']:
        if k['kod'] in KURAL['dusulen_kodlar'] and k['donem'] == son and k['tarih']:
            gunluk[k['tarih']] += k['dusum']
    son_gun = []
    for a in araliklar:
        if a['kod'] not in KURAL['dusulen_kodlar']:
            son_gun.append(0)
            continue
        t, g = a['bas'], 0.0
        while t <= a['bit']:
            g += gunluk.get(t, 0)
            t += datetime.timedelta(days=1)
        son_gun.append(g)
    haklar = [h for h in r['hak_edisler'] if h['donem'] == son]
    sh = r['sonraki_hak']
    sira = sorted(range(len(araliklar)), key=lambda i: (araliklar[i]['bas'], i))
    out, kum = [None] * len(araliklar), 0.0
    for i in sira:
        kum += son_gun[i]
        if son_gun[i] == 0:
            continue
        bit = araliklar[i]['bit']
        hak = sum(h['gun'] for h in haklar if h['tarih'] <= bit) + (sh['gun'] if sh and sh['tarih'] <= bit else 0)
        out[i] = duz + r['tasinan_eksi'] + hak - kum
    return out
