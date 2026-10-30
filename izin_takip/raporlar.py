# -*- coding: utf-8 -*-
"""Yazdırılabilir belgeler (HTML → QTextDocument → PDF ya da yazıcı): İzin Kartı (izin kayıt belgesi, Yönetmelik md.20), İzin Formu,
kalan izin listesi (Genel Durum) ve aylık takvim."""
import html
import os

from PySide6.QtCore import QMarginsF, QSizeF, QUrl
from PySide6.QtGui import QFont, QImage, QPageLayout, QPageSize, QPdfWriter, QTextDocument

from . import SURUM, UYGULAMA_ADI, motor
from .yardimci import AYLAR, GUN_ADLARI, GUN_KISA, KOD_AD, KOD_RENK, para_yaz, sayi_yaz, tarih_yaz
from .yollar import kaynak

LACI, TURUNCU, SOLUK, CIZGI = '#14145A', '#E2632A', '#6B6F86', '#C9CCD8'
e = html.escape


def _s(x, bos=''):
    return sayi_yaz(x, bos)


CSS = f"""
body {{ font-family: 'Inter', 'Segoe UI', sans-serif; font-size: 8.6pt; color: #1B1D3A; }}
h1 {{ font-size: 15pt; color: {LACI}; margin: 0; }}
h2 {{ font-size: 10.5pt; color: {LACI}; margin-top: 12px; margin-bottom: 4px; }}
.soluk {{ color: {SOLUK}; }}
.kucuk {{ font-size: 7.4pt; color: {SOLUK}; }}
table.t {{ border-collapse: collapse; border-color: {CIZGI}; }}
table.t th {{ background-color: {LACI}; color: white; font-weight: 600; padding: 4px; font-size: 7.6pt; }}
table.t td {{ padding: 3px 4px; border-color: {CIZGI}; }}
td.e {{ color: {SOLUK}; }}
td.b {{ font-weight: 600; }}
.kirmizi {{ color: #C22F40; }}
"""


def _ust(baglam, baslik, alt=''):
    return (f'<table width="100%" cellspacing="0" cellpadding="0"><tr>'
            f'<td width="40%"><img src="logo" width="215" height="43"></td>'
            f'<td align="right"><h1>{e(baslik)}</h1><span class="soluk">{e(baglam.sirket())} · hesap tarihi {tarih_yaz(baglam.bugun)}</span>'
            f'{"<br><span class=kucuk>" + e(alt) + "</span>" if alt else ""}</td></tr></table>'
            f'<hr style="color:{TURUNCU}; background-color:{TURUNCU}; height:2px; border:none">')


def _tablo(basliklar, satirlar, genislikler=None, hizalar=None):
    th = ''.join(f'<th{" width=" + chr(34) + str(genislikler[i]) + "%" + chr(34) if genislikler else ""}>{e(b)}</th>'
                 for i, b in enumerate(basliklar))
    govde = []
    for s in satirlar:
        tds = []
        for i, v in enumerate(s):
            stil = ''
            if isinstance(v, tuple):
                v, stil = v
            al = (hizalar or {}).get(i, 'left')
            tds.append(f'<td align="{al}" style="{stil}">{v}</td>')
        govde.append('<tr>' + ''.join(tds) + '</tr>')
    return f'<table class="t" width="100%" border="1" cellspacing="0" cellpadding="3"><thead><tr>{th}</tr></thead>{"".join(govde)}</table>'


# ----------------------------------------------------------------------------- İzin Kartı
def html_kart(baglam, pid, tum=True):
    ks = baglam.kisi(pid)
    p = baglam.personel(pid)
    dog = (tarih_yaz(ks['dogum']) + (f' ({ks["yas"]} yaş)' if ks['yas'] is not None else '')) if ks['dogum'] else \
        (f'bilinmiyor — 50 yaş beyanı {tarih_yaz(ks["yas50"])}' if ks['yas50'] else 'bilinmiyor')
    donem = '<br>'.join(f'{i + 1}. dönem: {tarih_yaz(g)} – {tarih_yaz(c) if c else "devam ediyor"}' for i, (g, c) in enumerate(ks['donemler']))
    kalan_renk = '#C22F40' if (ks['kalan'] or 0) < 0 else LACI
    sol = [('Ad Soyad', f'<b style="font-size:11pt">{e(ks["ad"])}</b>'), ('Doğum tarihi', e(dog)), ('Durum', e(ks['durum'])),
           ('Teyit durumu', e(p.get('teyit') or '—')), ('Tamamlanan hizmet yılı', _s(ks['kidem'], '—')), ('Çalışma dönemleri', donem)]
    sag = [('Bu dönemde kazanılan izin', f'{_s(ks["hak_son"], "—")} gün'), ('Bu dönemde kullanılan izin', f'{_s(ks["kul_son"], "—")} gün')]
    if ks['tasinan_eksi']:
        sag.append(('Önceki dönemden taşınan eksi', f'{_s(ks["tasinan_eksi"])} gün'))
    if ks['duz']:
        sag.append(('Elle düzeltme', f'{_s(ks["duz"])} gün' + (f'<br><span class="kucuk">{e(p.get("duzeltme_aciklama") or "")}</span>' if p.get('duzeltme_aciklama') else '')))
    if ks['onceki_donem_kalan'] is not None:
        sag.append(('Önceki dönemlerin kalanı', f'{_s(ks["onceki_donem_kalan"])} gün'))
    sag.append(('KALAN YILLIK İZİN', f'<b style="font-size:14pt; color:{kalan_renk}">{_s(ks["kalan"], "—")} gün</b>'))
    if ks['sonraki_tarih']:
        sag.append(('Sonraki hak', f'{tarih_yaz(ks["sonraki_tarih"])} · +{ks["sonraki_gun"]} gün'))
    bilgi = '<table width="100%" cellspacing="0" cellpadding="3"><tr><td width="52%" valign="top"><table cellpadding="2">' + \
        ''.join(f'<tr><td class="e" width="140">{a}</td><td>{b}</td></tr>' for a, b in sol) + \
        '</table></td><td width="48%" valign="top"><table cellpadding="2" width="100%">' + \
        ''.join(f'<tr><td class="e">{a}</td><td align="right">{b}</td></tr>' for a, b in sag) + '</table></td></tr></table>'
    if p.get('not_ozet'):
        bilgi += f'<p class="kucuk"><b>Not (özet):</b> {e(p["not_ozet"])}</p>'
    if ks['hatalar'] or ks['uyarilar']:
        bilgi += '<p class="kirmizi">' + '<br>'.join(e(u) for u in ks['hatalar'] + ks['uyarilar']) + '</p>'

    yil = _tablo(['Yıl', 'Kazanılan', 'Kullanılan yıllık izin', 'Rapor', 'Mazeret', 'Ücretsiz', 'İdari', 'Kalan (yıl sonu; bu yıl: hesap tarihinde)'],
                 [[str(y['yil']), _s(y['kazanilan'] or None), _s(y['kullanilan'] or None), _s(y['RP'] or None), _s(y['MZ'] or None),
                   _s(y['ÜZ'] or None), _s(y['İD'] or None), (_s(y['kalan']) if isinstance(y['kalan'], (int, float)) else (y['kalan'] or ''), 'font-weight:600')]
                  for y in ks['yil_ozet']], hizalar={i: 'center' for i in range(8)})
    hak = _tablo(['Hizmet yılı', 'Bir önceki hak tarihi', 'Ücretsiz izin (gün)', 'Hak kazandığı tarih', 'Yaş', 'İzin (gün)', 'Açıklama',
                  'Bu haktan kalan', 'Durum'],
                 [[f'{h["kidem"]}.', tarih_yaz(h['onceki']), str(h['uz_gun'] or ''), (tarih_yaz(h['tarih']), 'font-weight:600'),
                   str(h['yas'] if h['yas'] is not None else ''), (str(h['gun']), 'font-weight:600'), f'<span class="kucuk">{e(h["aciklama"])}</span>',
                   _s(h['kalan']) if h['kalan'] is not None else ('önceki dönem' if h['durum'] == 'Kazanıldı' else ''),
                   h['durum'] if h['durum'] == 'Kazanıldı' else f'<i>{h["durum"]}</i>'] for h in ks['hak_satirlari'][-20:]],
                 [7, 12, 9, 12, 5, 7, 26, 10, 12], {0: 'center', 1: 'center', 2: 'center', 3: 'center', 4: 'center', 5: 'center', 7: 'center'})
    izinler = []
    for k in baglam.veri['izinler']:
        if k['personel_id'] != pid or k['iptal'] or (not tum and k['tur'] != 'Kİ'):
            continue
        r = baglam.kayit(k['id'])
        if not r['bas']:
            continue
        izinler.append((r, k))
    izinler.sort(key=lambda x: (x[0]['bas'], x[0]['no']))
    kul = _tablo(['No', 'İzin türü', 'Başlangıç', 'Bitiş', 'İşe dönüş', 'Düşülen', 'Açıklama', 'İşçinin imzası'],
                 [[str(r['no']), KOD_AD[r['tur']], tarih_yaz(r['bas']), tarih_yaz(r['bit']), tarih_yaz(r['isbasi']),
                   (_s(r['dusulen']) if r['dusulen'] is not None else '—', 'font-weight:600'),
                   f'<span class="kucuk">{e(k.get("aciklama") or "")}{("<br><span class=kirmizi>" + e("; ".join(r["uyarilar"])) + "</span>") if r["uyarilar"] else ""}</span>',
                   ''] for r, k in izinler],
                 [6, 12, 10, 10, 10, 8, 30, 14], {0: 'center', 2: 'center', 3: 'center', 4: 'center', 5: 'center'})
    notlar = ''
    y = ks['yil_dokumu']
    if y:
        n = []
        if y['duzeltme'] > 0:
            n.append(f'Önce elle düzeltme ({_s(y["duzeltme"])} gün) kullanılır; ondan kalan {_s(y["duzeltme_kalan"])} gün.')
        if y['tasinan_eksi'] < 0:
            n.append(f'Önceki dönem(ler)den taşınan eksi ({_s(y["tasinan_eksi"])} gün) kullanım gibi en eski haklardan düşüldü.')
        if y['kalan'] < 0:
            n.append(f'Kalan eksi: bütün haklar kullanılmış, {_s(-y["kalan"])} gün hak edilmeden (avans) kullanılmış.')
        notlar = '<p class="kucuk">Kullanılan izin önce en eski haktan düşülür. ' + ' '.join(n) + '</p>'
    aciklama = ''
    if p.get('not_metni'):
        aciklama = f'<h2>Açıklamalar ve açık sorular</h2><p class="kucuk" style="line-height:130%">{e(p["not_metni"]).replace(chr(10), "<br>")}</p>'
    imza = (f'<br><table width="100%" cellspacing="0" cellpadding="6"><tr><td width="50%" style="border-top:1px solid {CIZGI}">'
            f'<b>İşçi</b><br><span class="kucuk">Ad soyad, imza, tarih</span><br><br><br></td>'
            f'<td width="50%" style="border-top:1px solid {CIZGI}"><b>İşveren / yetkili</b><br><span class="kucuk">Ad soyad, imza, tarih</span></td></tr></table>')
    return (f'<html><head><style>{CSS}</style></head><body>'
            + _ust(baglam, 'YILLIK İZİN KAYIT BELGESİ', '4857 sayılı İş Kanunu md.53–56 ve Yıllık Ücretli İzin Yönetmeliği md.20')
            + bilgi + '<h2>Yıllık özet</h2>' + yil + '<h2>İzne hak kazanma tarihleri</h2>' + hak + notlar
            + f'<h2>İzin kullanımları ({"tüm izin türleri" if tum else "yalnız yıllık izin"})</h2>' + (kul if izinler else '<p class="soluk">Kayıt yok.</p>')
            + aciklama + imza + '</body></html>')


# ----------------------------------------------------------------------------- İzin Formu
def html_form(baglam, kid):
    k = baglam.izin(kid)
    r = baglam.kayit(kid)
    ks = baglam.kisi(k['personel_id'])
    gecerli = r['gecerli']
    if r['iptal']:
        dus = '<b class="kirmizi">İPTAL EDİLMİŞ KAYIT</b>'
    elif not gecerli:
        dus = '<b class="kirmizi">Kayıt hatalı — düzeltmeden yazdırmayın</b>'
    elif k['tur'] == 'Kİ':
        dus = f'<b>{_s(r["dusulen"])} gün</b>'
    else:
        dus = 'Düşülmez (yıllık izin değil)'
    once = (ks['kalan'] + (r['dusulen_son'] or 0)) if gecerli and ks['kalan'] is not None and not r['iptal'] else None
    satirlar = [('Kayıt No', str(k['no'])), ('Adı Soyadı', f'<b>{e(ks["ad"])}</b>'), ('İşe giriş tarihi', tarih_yaz(ks['son_giris'])),
                ('Tamamlanan hizmet yılı', _s(ks['kidem'])), ('İzin türü', KOD_AD[k['tur']]), ('İzin başlangıç tarihi', tarih_yaz(r['bas'])),
                ('İzin bitiş tarihi', tarih_yaz(r['bit'])),
                ('İşe başlama (dönüş) tarihi', f'{GUN_ADLARI[r["isbasi"].weekday()]} {tarih_yaz(r["isbasi"])}' if gecerli else ''),
                ('Takvim günü', _s(r['takvim_gunu'])), ('Yıllık izinden düşülecek gün', dus),
                ('Bu izin düşülmeden önce kalan yıllık izin', f'{_s(once)} gün' if once is not None else ''),
                ('Güncel kalan yıllık izin (tüm kayıtlar düşülmüş)', f'{_s(ks["kalan"])} gün' if gecerli and not r['iptal'] else ''),
                ('Açıklama', e(k.get('aciklama') or '')), ('Yol izni (gün)', ''), ('İzinde bulunacağı adres / telefon', '<br>')]
    tablo = '<table class="t" width="100%" border="1" cellspacing="0" cellpadding="7">' + ''.join(
        f'<tr><td width="42%" class="e">{a}</td><td>{b}</td></tr>' for a, b in satirlar) + '</table>'
    uyari = f'<p class="kirmizi">Uyarı: {e("; ".join(r["uyarilar"]))}</p>' if r['uyarilar'] and not r['iptal'] else ''
    imza = '<table width="100%" cellspacing="8" cellpadding="8"><tr>' + ''.join(
        f'<td width="33%" valign="top" style="border:1px solid {CIZGI}"><b style="color:{LACI}">{t}</b><br><br>Ad Soyad:<br><br>Tarih:<br><br>İmza:<br><br></td>'
        for t in ('İzni talep eden işçi', 'Birim amiri', 'İnsan Kaynakları / İşveren')) + '</tr></table>'
    return (f'<html><head><style>{CSS} body {{ font-size: 10pt; }}</style></head><body>'
            + _ust(baglam, 'İZİN TALEP VE ONAY FORMU') + '<br>' + tablo + uyari + '<br>' + imza
            + '<p class="kucuk">Pazar günleri ile ulusal bayram ve genel tatil günleri izin süresinden sayılmaz (4857 s. İş Kanunu md.56). '
              'Arife ve 28 Ekim yarım gün sayılır.</p></body></html>')


# ----------------------------------------------------------------------------- Genel durum
def html_genel(baglam):
    s, oz = baglam.sonuc, baglam.ozet
    pmap = {p['id']: p for p in baglam.veri['personel']}
    satirlar = []
    for k in s.sirali:
        renk = 'color:#C22F40; font-weight:700' if (k['kalan'] or 0) < 0 else 'font-weight:700'
        satirlar.append([e(k['ad']), k['durum'], tarih_yaz(k['son_giris']), _s(k['kidem']), _s(k['yas']), _s(k['hak_son']), _s(k['kul_son']),
                         _s((k['duz'] or 0) + (k['tasinan_eksi'] or 0) or None), (_s(k['kalan']), renk),
                         f'{tarih_yaz(k["sonraki_tarih"])} (+{k["sonraki_gun"]})' if k['sonraki_tarih'] else '',
                         f'<span class="kucuk">{e(pmap[k["id"]].get("not_ozet") or "")}</span>'])
    ozet = (f'<p>Çalışan: <b>{oz["calisan"]}</b> · toplam kalan izin: <b>{_s(oz["toplam_kalan"])} gün</b> · kalanı eksi: <b>{oz["eksi"]}</b> · '
            f'30 günden fazla birikmiş: <b>{oz["birikmis"]}</b> · uyarılı izin kaydı: <b>{oz["uyarili_kayit"]}</b></p>')
    return (f'<html><head><style>{CSS}</style></head><body>' + _ust(baglam, 'KALAN YILLIK İZİNLER') + ozet
            + _tablo(['Ad Soyad', 'Durum', 'İşe giriş', 'Hizmet yılı', 'Yaş', 'Bu dönem kazanılan', 'Bu dönem kullanılan', 'Düzeltme',
                      'KALAN', 'Sonraki hak', 'Not'], satirlar, [17, 8, 8, 5, 4, 7, 7, 6, 6, 11, 21],
                     {i: 'center' for i in range(1, 10)}) + '</body></html>')


# ----------------------------------------------------------------------------- Takvim
def html_takvim(baglam, yil, ay):
    gunler, satirlar = motor.takvim(baglam.sonuc, baglam.veri, yil, ay)
    tatil = baglam.sonuc.tatil

    def zemin(g):
        t = tatil.get(g)
        return '#E3E5EC' if g.weekday() == 6 else ('#F8CBAD' if t and t['tur'] == 'tam' else ('#FCE4D6' if t else '#FFFFFF'))
    bas = '<tr><th width="150" style="white-space:nowrap">Personel</th>' + ''.join(
        f'<th style="background-color:{"#3A3A80" if g.weekday() == 6 else LACI}; font-size:6.4pt">{g.day}<br>{GUN_KISA[g.weekday()]}</th>' for g in gunler) + \
        '<th style="font-size:6.4pt">Yıllık</th><th style="font-size:6.4pt">Kalan</th></tr>'
    govde = []
    for s in satirlar:
        tds = [f'<td style="font-size:7pt; white-space:nowrap"><b>{e(s["kisi"]["ad"])}</b></td>']
        for g, h in zip(gunler, s['hucre']):
            if h in KOD_RENK:
                z, y = KOD_RENK[h]
                tds.append(f'<td align="center" style="background-color:{z}; color:{y}; font-size:6pt; font-weight:700">{h}</td>')
            elif h == '!!':
                tds.append('<td align="center" style="background-color:#C22F40; color:white; font-size:6pt; font-weight:700">!!</td>')
            elif h == '–':
                tds.append('<td style="background-color:#EDEEF2"></td>')
            else:
                tds.append(f'<td style="background-color:{zemin(g)}"></td>')
        tds.append(f'<td align="center" style="font-size:7pt">{_s(s["ozet"].get("Kİ")) if s["ozet"].get("Kİ") else ""}</td>')
        renk = '#C22F40' if (s['kisi']['kalan'] or 0) < 0 else '#1B1D3A'
        tds.append(f'<td align="center" style="font-size:7pt; color:{renk}; font-weight:700">{_s(s["kisi"]["kalan"])}</td>')
        govde.append('<tr>' + ''.join(tds) + '</tr>')
    lejant = ' &nbsp; '.join(f'<span style="background-color:{KOD_RENK[k][0]}; color:{KOD_RENK[k][1]}"><b>&nbsp;{k}&nbsp;</b></span> {KOD_AD[k]}' for k in KOD_RENK)
    tatiller = '; '.join(f'{g.day} {AYLAR[g.month - 1]}: {tatil[g]["ad"]}' for g in gunler if g in tatil)
    return (f'<html><head><style>{CSS}</style></head><body>' + _ust(baglam, f'İZİN TAKVİMİ — {AYLAR[ay - 1].upper()} {yil}')
            + f'<p class="kucuk">{lejant} &nbsp; · &nbsp; gri: Pazar · turuncu: resmi tatil · koyu gri: çalışma dönemi dışında</p>'
            + f'<table class="t" width="100%" border="1" cellspacing="0" cellpadding="1"><thead>{bas}</thead>{"".join(govde)}</table>'
            + (f'<p class="kucuk">Tatiller: {e(tatiller)}</p>' if tatiller else '') + '</body></html>')


# ----------------------------------------------------------------------------- çıktı
# Belgeler 96 dpi mantıksal çözünürlükte dizilir (HTML'deki px ölçüleri ekrandaki gibi; yazılar vektör kalır, logo tam çözünürlükle gömülür).
def belge(html_metni):
    doc = QTextDocument()
    f = QFont('Inter')
    f.setPointSizeF(8.6)
    doc.setDefaultFont(f)
    doc.setDocumentMargin(0)
    doc.addResource(QTextDocument.ImageResource, QUrl('logo'), QImage(kaynak('logo.png')))
    doc.setHtml(html_metni)
    return doc


def _duzen(yatay):
    return QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Landscape if yatay else QPageLayout.Portrait,
                       QMarginsF(11, 11, 11, 12), QPageLayout.Millimeter)


def _bas(doc, cihaz):
    doc.documentLayout().setPaintDevice(cihaz)
    r = cihaz.pageLayout().paintRectPixels(cihaz.resolution())
    doc.setPageSize(QSizeF(r.width(), r.height()))
    doc.print_(cihaz)


def pdf_kaydet(html_metni, yol, yatay=False):
    w = QPdfWriter(yol)
    w.setResolution(96)
    w.setPageLayout(_duzen(yatay))
    w.setTitle(os.path.splitext(os.path.basename(yol))[0])
    w.setCreator(f'{UYGULAMA_ADI} {SURUM}')
    _bas(belge(html_metni), w)
    del w
    return yol


def yazdir(html_metni, parent=None, yatay=False):
    from PySide6.QtPrintSupport import QPrintDialog, QPrinter
    pr = QPrinter(QPrinter.ScreenResolution)
    pr.setPageLayout(_duzen(yatay))
    dlg = QPrintDialog(pr, parent)
    dlg.setWindowTitle('Yazdır')
    if dlg.exec():
        _bas(belge(html_metni), pr)
        return True
    return False
