# -*- coding: utf-8 -*-
"""Hak edis motorunun birim testleri (tarihler uydurmadir; 28 yillik takvim dongusu: ayni gunler/haftalar). Calistir (deponun kok klasorunden): python testler/test_hesapla.py"""
import datetime
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from izin_takip import hesapla as H  # noqa: E402

D = datetime.date


def yd(donemler, uz=(), bugun=D(2054, 9, 25)):
    return [(i, t.isoformat(), n) for i, t, n in H._yildonumleri(donemler, set(uz), bugun)]


def test():
    # surekli calisma: giris + n yil
    assert yd([(D(2047, 11, 11), None)])[-1] == (0, '2053-11-11', 6)
    # bugune denk gelen yildonumu dahil
    assert yd([(D(2051, 9, 25), None)])[-1] == (0, '2054-09-25', 3)
    # tam 1 yil calisip ayrilan hak kazanir; 1 gun eksik kazanamaz
    assert yd([(D(2053, 1, 1), D(2053, 12, 31))]) == [(0, '2054-01-01', 1)]
    assert yd([(D(2053, 1, 1), D(2053, 12, 30))]) == []
    # kesintili: onceki donemin tam yildan artan kismi yeni doneme eklenir (md.54, Yonetmelik 4/2)
    assert yd([(D(2052, 10, 4), D(2054, 4, 4)), (D(2054, 6, 8), None)], bugun=D(2055, 6, 1)) == [(0, '2053-10-04', 1), (1, '2054-12-07', 2)]
    # kisa onceki donem (1 yildan az) sonrakine eklenir; sonraki yil onceki hak tarihinden sayilir (md.54/3)
    assert yd([(D(2050, 5, 19), D(2050, 9, 5)), (D(2053, 2, 28), None)], bugun=D(2055, 1, 1)) == [(1, '2053-11-10', 1), (1, '2054-11-10', 2)]
    # ucretsiz izin gunleri hak tarihini oteler ve kayma kalicidir (md.54/2)
    assert yd([(D(2053, 11, 17), None)], uz=[D(2054, 2, 2), D(2054, 2, 3), D(2054, 2, 4), D(2054, 2, 5)], bugun=D(2055, 1, 1)) == [(0, '2054-11-21', 1)]
    assert yd([(D(2053, 11, 17), None)], uz=[D(2054, 2, 2)], bugun=D(2056, 1, 1)) == [(0, '2054-11-18', 1), (0, '2055-11-18', 2)]
    # kidem basamaklari ve yas kurali
    assert H.hak_gunu(1, 30)[0] == 14 and H.hak_gunu(5, 30)[0] == 14 and H.hak_gunu(6, 30)[0] == 20
    assert H.hak_gunu(14, 30)[0] == 20 and H.hak_gunu(15, 30)[0] == 26
    assert H.hak_gunu(1, 50)[0] == 20 and H.hak_gunu(1, 49)[0] == 14 and H.hak_gunu(1, 18)[0] == 20 and H.hak_gunu(1, 19)[0] == 14
    assert H.hak_gunu(15, 55)[0] == 26 and H.hak_gunu(3, None)[0] == 14
    # yas: dogum gunu dahil tamamlanmis yas
    assert H.yas(D(2004, 9, 25), D(2054, 9, 25)) == 50 and H.yas(D(2004, 9, 26), D(2054, 9, 25)) == 49
    # 50 yas beyani: dogum tarihi yoksa beyan baslangicindan itibaren en az 20; dogum tarihi varsa beyan yok sayilir
    assert H.hak_gunu(3, None, True)[0] == 20 and H.hak_gunu(3, None, False)[0] == 14 and H.hak_gunu(3, 40, True)[0] == 14
    assert H.hak_gunu(15, None, True)[0] == 26
    assert H.beyan_var(D(2053, 1, 1), None, D(2053, 1, 1)) and not H.beyan_var(D(2053, 1, 1), None, D(2052, 12, 31))
    assert not H.beyan_var(D(2053, 1, 1), D(1998, 1, 1), D(2054, 1, 1)) and not H.beyan_var(None, None, D(2054, 1, 1))
    hk = H.hak_edisler([(D(2048, 7, 9), None)], None, D(2054, 9, 25), yas50=D(2053, 1, 1))
    assert [x['gun'] for x in hk] == [14, 14, 14, 14, 20, 20]
    hk = H.hak_edisler([(D(2048, 7, 9), None)], D(2018, 1, 1), D(2054, 9, 25), yas50=D(2049, 1, 1))
    assert [x['gun'] for x in hk] == [14, 14, 14, 14, 14, 20]
    assert H.sonraki_hak([(D(2050, 12, 7), None)], None, D(2054, 9, 25), yas50=D(2053, 1, 1))['gun'] == 20
    # onceki donemin cikista odenmeyen arti kalani guncel doneme devreder; eksi kalan devretmez; devir=False iken eklenmez
    bos = {'hareketler': []}
    donemler = [(D(2051, 1, 2), D(2052, 6, 30)), (D(2053, 1, 6), None)]
    r = H.kisi_hesapla(bos, donemler, None, {}, D(2054, 9, 25), {}, devir=True)
    assert r['donem_ozet'][0]['kalan'] == 14 and r['donem_ozet'][0]['devreden'] == 14 and r['devir'] == 14
    assert r['guncel_kalan'] == r['donem_ozet'][-1]['hak'] + 14 and r['donem_ozet'][-1]['devralinan'] == 14
    r0 = H.kisi_hesapla(bos, donemler, None, {}, D(2054, 9, 25), {})
    assert r0['devir'] == 0 and r0['guncel_kalan'] == r0['donem_ozet'][-1]['hak']
    eksi = {'hareketler': [{'tarih': '2051-03-06', 'kod': 'Kİ', 'hucre': 'Mart!H10', 'yil': 2051, 'gecerli_kod': True}]}
    r = H.kisi_hesapla(eksi, [(D(2051, 1, 2), D(2051, 6, 30)), (D(2053, 1, 6), None)], None, {}, D(2054, 9, 25), {}, devir=True)
    assert r['donem_ozet'][0]['kalan'] == -1 and r['devir'] == 0
    test_yil_dokumu()
    test_avans_devri()
    test_donem_disi_dus()
    test_kayit_kalanlari()
    print('TUM TESTLER GECTI')


def test_kayit_kalanlari():
    """Izin kaydi bazinda kalan (avans uyarisi): tarih sirasiyla, siradaki hak ileri tarihli izinde sayilir."""
    B = D(2054, 9, 25)
    g1, g2 = is_gunleri(D(2053, 3, 3), 6), is_gunleri(D(2054, 2, 2), 3)
    g3 = is_gunleri(D(2054, 12, 1), 18)        # 01-21.12.2054: siradaki hak (06.01.2055) sayilmaz
    g4 = is_gunleri(D(2055, 1, 4), 6)          # 04-09.01.2055: siradaki hak (+14) sayilir
    r = H.kisi_hesapla(ki(*(g1 + g2 + g3 + g4)), [(D(2053, 1, 6), None)], None, {}, B, {})
    assert r['sonraki_hak']['tarih'] == D(2055, 1, 6)
    ar = [{'kod': 'Kİ', 'bas': g[0], 'bit': g[-1]} for g in (g2, g1, g3, g4)] + [{'kod': 'İD', 'bas': D(2053, 4, 1), 'bit': D(2053, 4, 1)}]
    k = H.kayit_kalanlari(r, ar)
    assert k[1] == -6 and k[0] == 14 - 9 and k[2] == 5 - 18 and k[3] == 5 - 18 + 14 - 6 and k[4] is None
    # ayni baslangicta satir sirasi; ayrilan (aktif degil) kiside hesaplanmaz
    r2 = H.kisi_hesapla(ki(*g1), [(D(2053, 1, 6), D(2053, 12, 31))], None, {}, B, {})
    assert H.kayit_kalanlari(r2, [{'kod': 'Kİ', 'bas': g1[0], 'bit': g1[-1]}]) == [None]


def test_avans_devri():
    """Onceki donemin eksi kalani sonraki doneme tasinir (KURAL['avans_devri']; zincir); arti kalan yalniz devir kuraliyla."""
    B = D(2054, 9, 25)
    # iki kisa donem (hak yok) -2 ve -1 -> guncel doneme -3 tasinir
    d3 = [(D(2050, 5, 28), D(2050, 6, 20)), (D(2051, 9, 19), D(2052, 4, 25)), (D(2054, 2, 25), None)]
    k = ki(D(2050, 6, 1), D(2050, 6, 2), D(2052, 1, 10), D(2054, 5, 5))
    r = H.kisi_hesapla(k, d3, D(1999, 2, 3), {}, B, {}, avans_devri=True)
    dz = r['donem_ozet']
    assert [x['kalan'] for x in dz[:2]] == [-2, -3] and [x['eksi_devreden'] for x in dz[:2]] == [-2, -3]
    assert dz[2]['eksi_devralinan'] == -3 == r['tasinan_eksi'] and r['guncel_kalan'] == dz[2]['hak'] - 1 - 3
    y = H.yil_dokumu(r, B)
    assert y['tasinan_eksi'] == -3 and y['kalan'] == r['guncel_kalan'] and y['haklar'][0]['kalan'] == dz[2]['hak'] - 1 - 3
    # kapaliyken (kisi_hesapla varsayilani) eksi tasinmaz
    r0 = H.kisi_hesapla(k, d3, D(1999, 2, 3), {}, B, {})
    assert [x['kalan'] for x in r0['donem_ozet']] == [-2, -1, r0['donem_ozet'][2]['hak'] - 1] and r0['tasinan_eksi'] == 0
    assert H.KURAL['avans_devri'] is True and H.KURAL['donem_disi_dus'] is True
    # arti donem araya girerse eksi orada emilir (b_2 = 20 - 3 - 2 >= 0 -> tasinan 0); arti kalan tasinmaz (devir yok)
    d2 = [(D(2047, 1, 7), D(2047, 6, 28)), (D(2047, 9, 2), D(2049, 12, 31)), (D(2051, 3, 1), None)]
    k2 = ki(D(2047, 3, 4), D(2047, 3, 5), D(2048, 8, 3), D(2048, 8, 4), D(2048, 8, 5))
    r = H.kisi_hesapla(k2, d2, D(2009, 7, 1), {}, B, {}, avans_devri=True)
    dz = r['donem_ozet']
    assert dz[0]['kalan'] == -2 and dz[1]['eksi_devralinan'] == -2 and dz[1]['kalan'] == dz[1]['hak'] - 3 - 2 > 0
    assert dz[1]['eksi_devreden'] == 0 and r['tasinan_eksi'] == 0 and r['guncel_kalan'] == dz[2]['hak']
    # devir=True: arti kalan (eksi emildikten sonra) devreder, eksi ayrica tasinmaz -> cift sayim yok
    r = H.kisi_hesapla(k2, d2, D(2009, 7, 1), {}, B, {}, devir=True, avans_devri=True)
    assert r['devir'] == dz[1]['kalan'] and r['guncel_kalan'] == r['donem_ozet'][2]['hak'] + dz[1]['kalan']
    # eksi, sonraki donemin kendi artisindan buyukse zincir devam eder: -5 -> (hak 0, kul 0) -> -5 -> guncel
    d4 = [(D(2049, 1, 4), D(2049, 6, 30)), (D(2050, 1, 3), D(2050, 5, 31)), (D(2051, 1, 2), None)]
    k4 = ki(*is_gunleri(D(2049, 3, 1), 5))
    r = H.kisi_hesapla(k4, d4, None, {}, B, {}, avans_devri=True)
    assert [x['kalan'] for x in r['donem_ozet'][:2]] == [-5, -5] and r['tasinan_eksi'] == -5
    assert r['guncel_kalan'] == r['donem_ozet'][2]['hak'] - 5
    y = H.yil_dokumu(r, B)
    assert y['haklar'][0]['kalan'] == 14 - 5 and y['yil_sonu'][2051] == sum(h['gun'] for h in y['haklar'] if h['tarih'].year == 2051) - 5


def test_donem_disi_dus():
    """Calisma donemi disindaki Ki gunleri en yakin doneme dusulur (KURAL['donem_disi_dus']); hak tarihleri degismez."""
    B = D(2054, 9, 25)
    d3 = [(D(2050, 5, 28), D(2050, 6, 20)), (D(2051, 9, 19), D(2052, 4, 25)), (D(2054, 2, 25), None)]
    # en yakin donem: ilk donemden once -> 0; arada -> yakin olan, esitlikte onceki; kapanmis son donemden sonra -> son
    assert H.en_yakin_donem(D(2050, 1, 1), d3) == 0 and H.en_yakin_donem(D(2050, 6, 25), d3) == 0
    assert H.en_yakin_donem(D(2053, 10, 20), d3) == 2 and H.en_yakin_donem(D(2052, 5, 13), d3) == 1
    ab = [(D(2052, 1, 1), D(2052, 1, 10)), (D(2052, 1, 21), None)]
    assert H.en_yakin_donem(D(2052, 1, 15), ab) == 0 and H.en_yakin_donem(D(2052, 1, 16), ab) == 1
    esit = [(D(2052, 1, 1), D(2052, 1, 10)), (D(2052, 1, 20), None)]
    assert H.en_yakin_donem(D(2052, 1, 15), esit) == 0 and H.en_yakin_donem(D(2052, 1, 16), esit) == 1  # 5 = 5 gun -> onceki
    kapali = [(D(2048, 1, 1), D(2048, 12, 31))]
    assert H.en_yakin_donem(D(2049, 3, 1), kapali) == 0
    # ornek: donem 1 -2 + 21-25.06.2050 (5 gun) = -7; donem 2 -1 + 13-18.05.2052 (6 gun) = -7,
    # tasinan -7 -> -14; donem 3: 20 - 1 - 4 (20.10.2053, 5-6 ve 15.01.2054) - 14 = 1
    gun = [D(2050, 6, 1), D(2050, 6, 2)] + is_gunleri(D(2050, 6, 21), 5) + [D(2052, 1, 10)] + is_gunleri(D(2052, 5, 13), 6) \
        + [D(2053, 10, 20), D(2054, 1, 5), D(2054, 1, 6), D(2054, 1, 15), D(2054, 5, 5)]
    r = H.kisi_hesapla(ki(*gun), d3, D(1999, 2, 3), {}, B, {}, avans_devri=True, donem_disi_dus=True)
    dz = r['donem_ozet']
    assert [x['kalan'] for x in dz] == [-7, -14, 1] and r['tasinan_eksi'] == -14 and r['guncel_kalan'] == 1
    assert not any(k.get('dusum_donem_disi') for k in r['kullanim'])
    atanan = [k for k in r['kullanim'] if k.get('donem_disi_atandi')]
    assert len(atanan) == 15 and all(any(x.startswith('ÇALIŞMA DÖNEMİ DIŞINDA — en yakın döneme') for x in k['durum']) for k in atanan)
    # hak tarihleri kuraldan etkilenmez
    r0 = H.kisi_hesapla(ki(*gun), d3, D(1999, 2, 3), {}, B, {})
    assert r0['hak_edisler'] == r['hak_edisler'] and sum(k.get('dusum_donem_disi', 0) for k in r0['kullanim']) == 15
    # Pazar ve tam gun tatile denk gelen donem disi gun dusulmez; yarim gun 0,5
    tat = {D(2049, 12, 31): {'tur': 'yarim', 'ad': 'x'}, D(2050, 1, 1): {'tur': 'tam', 'ad': 'Yılbaşı'}}
    r = H.kisi_hesapla(ki(D(2049, 12, 31), D(2050, 1, 1), D(2050, 1, 2)), [(D(2050, 1, 3), None)], None, tat, B, {}, donem_disi_dus=True)
    assert r['donem_ozet'][0]['kullanilan'] == 0.5 and [k['donem'] for k in r['kullanim']] == [0, 0, 0]
    # yillik izin disindaki kodlar (idari izin vb.) atanmaz
    k_id = {'hareketler': [{'tarih': '2049-12-30', 'kod': 'İD', 'hucre': 'x', 'yil': 2049, 'gecerli_kod': True}]}
    r = H.kisi_hesapla(k_id, [(D(2050, 1, 3), None)], None, {}, B, {}, donem_disi_dus=True)
    assert r['kullanim'][0]['donem'] is None


def ki(*tarihler):
    """Verilen gunlere Ki kaydi (Pazar olmayan gunler 1 gun duser; tatil sozlugu bos)."""
    return {'hareketler': [{'tarih': t.isoformat(), 'kod': 'Kİ', 'hucre': f'X!{i}', 'yil': t.year, 'gecerli_kod': True,
                            'atama': 'personel_satiri'} for i, t in enumerate(tarihler)]}


def is_gunleri(bas, n):
    """bas'tan itibaren Pazar olmayan n gun."""
    out, t = [], bas
    while len(out) < n:
        if t.weekday() != 6:
            out.append(t)
        t += datetime.timedelta(days=1)
    return out


def test_yil_dokumu():
    B = D(2054, 9, 25)
    # tek donem: 4 hak x 14; 2051'te 20 gun kullanim -> en eski hak (2051) biter, 2052'ten 6 gun duser
    r = H.kisi_hesapla(ki(*is_gunleri(D(2051, 3, 6), 20)), [(D(2050, 1, 3), None)], None, {}, B, {})
    y = H.yil_dokumu(r, B)
    assert [h['kalan'] for h in y['haklar']] == [0, 8, 14, 14] and y['kalan'] == r['guncel_kalan'] == 36
    assert sum(h['kalan'] for h in y['haklar']) == y['kalan'] and not y['avans'] and y['duzeltme_kalan'] == 0
    # yil sonu: 2050 -> 0 (hak yok), 2051 -> 14 - 20 = -6 (avans), 2052 -> 28 - 20, 2053 -> 42 - 20, 2054 (hesap yili) -> guncel kalan
    assert y['yil_sonu'] == {2050: 0, 2051: -6, 2052: 8, 2053: 22, 2054: 36}
    # avans: kullanilan > hak -> butun haklardan kalan 0, kalan eksi
    r = H.kisi_hesapla(ki(*is_gunleri(D(2053, 2, 3), 20)), [(D(2053, 1, 6), None)], None, {}, B, {})
    y = H.yil_dokumu(r, B)
    assert y['avans'] and y['kalan'] == r['guncel_kalan'] == -6 and [h['kalan'] for h in y['haklar']] == [0]
    assert y['yil_sonu'] == {2053: -20, 2054: -6}
    # ileri tarihli izin (hesap tarihinden sonra, ayni yil): kalandan hemen duser; hesap yili satiri = guncel kalan
    r = H.kisi_hesapla(ki(*is_gunleri(D(2054, 11, 2), 3)), [(D(2052, 5, 6), None)], None, {}, B, {})
    y = H.yil_dokumu(r, B)
    assert y['kalan'] == r['guncel_kalan'] == 25 and y['yil_sonu'][2054] == 25 and [h['kalan'] for h in y['haklar']] == [11, 14]
    # arti duzeltme (onceki donemden odenmeyen kalan, devir=True): en eski kova; once o kullanilir
    donemler = [(D(2051, 1, 2), D(2052, 6, 30)), (D(2053, 1, 6), None)]
    r = H.kisi_hesapla(ki(*is_gunleri(D(2053, 3, 3), 5)), donemler, None, {}, B, {}, devir=True)
    y = H.yil_dokumu(r, B)
    assert y['duzeltme'] == 14 and y['duzeltme_kalan'] == 9 and [h['kalan'] for h in y['haklar']] == [14, 14]
    assert y['kalan'] == r['guncel_kalan'] == 37 and y['duzeltme_kalan'] + sum(h['kalan'] for h in y['haklar']) == 37
    # cok donemli: yalniz guncel donemin haklari (onceki donemin 02.01.2052 hakki haric; kidem birlestirildigi icin
    # guncel donemin ilk hakki 10.07.2053) listelenir; yil sonu guncel donemin baslangic yilindan
    assert [h['tarih'] for h in y['haklar']] == [D(2053, 7, 10), D(2054, 7, 10)] and y['donem_baslangic'] == D(2053, 1, 6)
    assert y['yil_sonu'] == {2053: 14 - 5 + 14, 2054: 37}
    # eksi duzeltme (ornek: 2050 oncesi kullanilmis sayilan 14 gun): kullanim gibi en eski haktan duser
    r = H.kisi_hesapla(ki(*is_gunleri(D(2051, 3, 6), 4)), [(D(2048, 7, 9), None)], None, {}, B, {})
    y = H.yil_dokumu(r, B, duzeltme=-14)
    assert [h['kalan'] for h in y['haklar']] == [0, 10, 14, 14, 14, 20] and y['kalan'] == r['guncel_kalan'] - 14 == 72
    assert y['duzeltme_kalan'] == 0 and y['yil_sonu'][2049] == 0 and y['yil_sonu'][2051] == 42 - 4 - 14
    # eksi duzeltme haklardan buyukse: kalan eksi, hepsi 0
    y = H.yil_dokumu(r, B, duzeltme=-100)
    assert y['avans'] and all(h['kalan'] == 0 for h in y['haklar'])
    # yarim gun dusum (arife) FIFO'da ondalik kalir
    tat = {D(2053, 3, 29): {'tur': 'yarim', 'ad': 'arife'}}
    r = H.kisi_hesapla(ki(D(2053, 3, 29)), [(D(2052, 1, 8), None)], None, tat, B, {})
    y = H.yil_dokumu(r, B)
    assert [h['kalan'] for h in y['haklar']] == [13.5, 14] and y['kalan'] == 27.5
    # elle_duzeltme guncel kalana eklenir; yil_dokumu 'duzeltme' = devir + elle
    r = H.kisi_hesapla(ki(*is_gunleri(D(2051, 3, 6), 4)), [(D(2048, 7, 9), None)], None, {}, B, {}, elle_duzeltme=-14)
    assert r['elle_duzeltme'] == -14 and r['duzeltme'] == -14 and r['guncel_kalan'] == 72
    y = H.yil_dokumu(r, B)
    assert y['duzeltme'] == -14 and y['kalan'] == 72 and [h['kalan'] for h in y['haklar']] == [0, 10, 14, 14, 14, 20]
    r = H.kisi_hesapla(ki(*is_gunleri(D(2053, 3, 3), 5)), donemler, None, {}, B, {}, devir=True, elle_duzeltme=-2)
    assert r['devir'] == 14 and r['duzeltme'] == 12 and r['guncel_kalan'] == 35


if __name__ == '__main__':
    test()
