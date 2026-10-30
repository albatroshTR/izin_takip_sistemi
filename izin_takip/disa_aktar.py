# -*- coding: utf-8 -*-
"""Excel'e aktarma (rapor / arşiv): kalan izinler, izin kayıtları, personel, tatiller ve ayrılanlar tek .xlsx dosyasında.
Hesaplanmış değerler yazılır (formül yok); dosya programa geri okunmaz."""
import datetime

from . import SURUM, TELIF, UYGULAMA_ADI
from .yardimci import KOD_AD, sayi_yaz, tarih_yaz

LACI = '14145A'


def _sayi(x):
    if x is None or x == '':
        return None
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def excel_yaz(baglam, yol):
    import openpyxl
    from openpyxl.formatting.rule import CellIsRule
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    s, veri = baglam.sonuc, baglam.veri
    pmap = {p['id']: p for p in veri['personel']}
    wb = openpyxl.Workbook()
    wb.properties.creator = f'{UYGULAMA_ADI} {SURUM}'
    wb.properties.description = f'{UYGULAMA_ADI} · {TELIF}'
    ince = Side(style='thin', color='D5D8E3')

    def sayfa(ws, baslik, alt, basliklar, satirlar, genislik, tarih_sut=(), sayi_sut=(), kalan_sut=None):
        ws['A1'] = baslik
        ws['A1'].font = Font(size=15, bold=True, color=LACI)
        ws['A2'] = alt
        ws['A2'].font = Font(size=9, italic=True, color='6B6F86')
        for j, b in enumerate(basliklar, start=1):
            c = ws.cell(4, j, b)
            c.font = Font(bold=True, color='FFFFFF')
            c.fill = PatternFill('solid', fgColor=LACI)
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
            c.border = Border(left=ince, right=ince, top=ince, bottom=ince)
        ws.row_dimensions[4].height = 32
        for i, r in enumerate(satirlar, start=5):
            for j, v in enumerate(r, start=1):
                c = ws.cell(i, j, v)
                c.border = Border(bottom=ince)
                if j in tarih_sut:
                    c.number_format = 'DD.MM.YYYY'
                    c.alignment = Alignment(horizontal='center')
                elif j in sayi_sut:
                    c.number_format = 'General;[Red]-General;0'
                    c.alignment = Alignment(horizontal='center')
        for j, w in enumerate(genislik, start=1):
            ws.column_dimensions[get_column_letter(j)].width = w
        ws.freeze_panes = 'B5'
        if satirlar:
            ws.auto_filter.ref = f'A4:{get_column_letter(len(basliklar))}{4 + len(satirlar)}'
        if kalan_sut and satirlar:
            h = get_column_letter(kalan_sut)
            alan = f'{h}5:{h}{4 + len(satirlar)}'
            ws.conditional_formatting.add(alan, CellIsRule(operator='lessThan', formula=['0'], fill=PatternFill('solid', fgColor='FDE8EA'),
                                                           font=Font(color='C22F40', bold=True)))
            ws.conditional_formatting.add(alan, CellIsRule(operator='greaterThan', formula=['30'], fill=PatternFill('solid', fgColor='FFF3D6')))
            for i in range(5, 5 + len(satirlar)):
                ws[f'{h}{i}'].font = Font(bold=True)
        ws.page_setup.orientation = 'landscape'
        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0
        ws.sheet_properties.pageSetUpPr.fitToPage = True
        ws.print_title_rows = '4:4'

    alt = f'{baglam.sirket()} · hesap tarihi {tarih_yaz(baglam.bugun)} · {datetime.datetime.now():%d.%m.%Y %H:%M} tarihinde {UYGULAMA_ADI}\'ndan alındı'
    ws = wb.active
    ws.title = 'Genel Durum'
    sayfa(ws, 'Genel durum — yıllık izin bakiyeleri', alt,
          ['Ad Soyad', 'Durum', 'İşe giriş (son)', 'Hizmet yılı', 'Yaş', 'Bu dönem kazanılan', 'Bu dönem kullanılan',
           'Önceki dönemden / elle düzeltme', 'KALAN İZİN', 'Sonraki hak tarihi', 'Sonraki hak (gün)', 'Teyit', 'Uyarılar', 'Not (özet)'],
          [[k['ad'], k['durum'], k['son_giris'], k['kidem'], k['yas'], _sayi(k['hak_son']), _sayi(k['kul_son']),
            _sayi((k['duz'] or 0) + (k['tasinan_eksi'] or 0)) or None, _sayi(k['kalan']), k['sonraki_tarih'], k['sonraki_gun'],
            pmap[k['id']].get('teyit'), '; '.join(k['hatalar'] + k['uyarilar'] + ([f'{k["uyarili_kayit"]} izin kaydında uyarı'] if k['uyarili_kayit'] else [])),
            pmap[k['id']].get('not_ozet')] for k in s.sirali],
          [28, 12, 13, 9, 7, 11, 11, 13, 11, 13, 10, 16, 45, 60], tarih_sut=(3, 10), sayi_sut=(4, 5, 6, 7, 8, 9, 11), kalan_sut=9)

    ws = wb.create_sheet('İzin Kayıtları')
    satirlar = []
    for k in sorted(veri['izinler'], key=lambda k: k['no']):
        r = s.kayit[k['id']]
        satirlar.append([k['no'], pmap[k['personel_id']]['ad'], KOD_AD[k['tur']], k['bas'], k['bit'] or k['bas'], r['takvim_gunu'],
                         _sayi(r['dusulen']) if not k['iptal'] else None, r['isbasi'], k.get('aciklama'), k.get('giren'), k.get('yazildigi'),
                         'İptal' if k['iptal'] else None, '; '.join(r['uyarilar'])])
    sayfa(ws, 'İzin kayıtları', alt, ['No', 'Personel', 'İzin türü', 'Başlangıç', 'Bitiş', 'Takvim günü', 'Yıllık izinden düşülen gün',
                                      'İşe dönüş', 'Açıklama', 'Giren', 'Yazıldığı tarih', 'İptal', 'Kontrol'],
          satirlar, [7, 28, 16, 12, 12, 9, 12, 12, 40, 18, 12, 8, 60], tarih_sut=(4, 5, 8, 11), sayi_sut=(1, 6, 7))

    ws = wb.create_sheet('Personel')
    satirlar = []
    for k in s.sirali:
        p = pmap[k['id']]
        don = p['donemler'] + [(None, None)] * (3 - len(p['donemler']))
        satir = [p['ad'], p['dogum']]
        for g, c in don[:3]:
            satir += [g, c]
        satir += ['; '.join(f'{tarih_yaz(g)}–{tarih_yaz(c)}' for g, c in p['donemler'][3:]) or None,
                  _sayi(p.get('elle_duzeltme')), p.get('duzeltme_aciklama'), p.get('teyit'), p.get('yas50'), p.get('onceki_ad'), p.get('not_metni')]
        satirlar.append(satir)
    sayfa(ws, 'Personel', alt, ['Ad Soyad', 'Doğum tarihi', '1. giriş', '1. çıkış', '2. giriş', '2. çıkış', '3. giriş', '3. çıkış',
                                'Diğer dönemler', 'Elle düzeltme (gün)', 'Düzeltme açıklaması', 'Teyit durumu', '50 yaş beyanı', 'Önceki ad',
                                'Not / dayanak'],
          satirlar, [28, 12, 12, 12, 12, 12, 12, 12, 20, 11, 30, 16, 12, 22, 80], tarih_sut=(2, 3, 4, 5, 6, 7, 8, 13), sayi_sut=(10,))

    ws = wb.create_sheet('Tatiller')
    sayfa(ws, 'Resmi tatiller', alt, ['Tarih', 'Tatil', 'Tür'],
          [[t['tarih'], t['ad'], 'tam' if t['tur'] == 'tam' else 'yarım'] for t in veri['tatiller']], [13, 50, 9], tarih_sut=(1,))

    ayr = s.ayrilanlar()
    if ayr:
        from .arayuz.sayfa_ayrilanlar import odeme_satiri
        ws = wb.create_sheet('Ayrılanlar')
        satirlar = []
        for k in ayr:
            o = odeme_satiri(k, veri['odemeler'].get(k['id']), baglam.bugun)
            satirlar.append([k['ad'], '; '.join(f'{tarih_yaz(g)}–{tarih_yaz(c)}' for g, c in k['donemler']), _sayi(k['hak_top']), _sayi(k['kul_top']),
                             _sayi(o['gun']), o['ucret'], o['tutar'], o['odendi'], o['odeme_tarihi'], o['odenen'], o['borc'], o['zaman'],
                             '; '.join(o['uyari'])])
        sayfa(ws, 'Ayrılanlar — ödenmesi gereken izin ücreti (md.59)', alt,
              ['Ad Soyad', 'Çalıştığı dönem(ler)', 'Hak edilen', 'Kullanılan', 'Ödenecek gün', 'Son brüt aylık ücret', 'Tutar', 'Ödendi mi?',
               'Ödeme tarihi', 'Ödenen tutar', 'Kalan borç', 'Zamanaşımı', 'Uyarı'],
              satirlar, [26, 30, 10, 10, 11, 14, 14, 11, 12, 14, 14, 12, 50], tarih_sut=(9, 12), sayi_sut=(3, 4, 5))
        for r in range(5, 5 + len(satirlar)):
            for c in (6, 7, 10, 11):
                ws.cell(r, c).number_format = '#,##0.00'
    wb.save(yol)
    return yol
