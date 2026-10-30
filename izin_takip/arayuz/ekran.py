# -*- coding: utf-8 -*-
"""Doğrulama için ekran görüntüleri ve örnek belgeler (--ekran-goruntusu <klasör>). Veriyi değiştirmez."""
import os

from .. import guvenlik, raporlar


def _bekle(app, n=6):
    for _ in range(n):
        app.processEvents()


def goruntule(app, pencere, baglam, klasor):
    os.makedirs(klasor, exist_ok=True)
    pencere.resize(1440, 900)
    pencere.show()
    _bekle(app)

    def kaydet(w, ad):
        _bekle(app)
        w.grab().save(os.path.join(klasor, ad + '.png'))

    for ad in ('genel', 'personel', 'izinler', 'takvim', 'ayrilan', 'kontrol', 'tatil', 'ayar', 'yardim'):
        pencere.git(ad)
        kaydet(pencere, f'sayfa_{ad}')
    s = baglam.sonuc
    # İzin Kartı: kalanı eksi olan ve çok dönemli birer kişi
    ornek = [k for k in s.calisanlar() if len(k['donemler']) > 1][:1] + sorted(s.calisanlar(), key=lambda k: k['kalan'])[:1]
    for i, k in enumerate(ornek):
        baglam.git.emit('kart', k['id'])
        kaydet(pencere, f'kart_{i + 1}')
        for j in range(1, 4):
            pencere.sayfa['personel'].kart.sekme.setCurrentIndex(j)
            kaydet(pencere, f'kart_{i + 1}_sekme{j}')
        pencere.sayfa['personel'].kart.sekme.setCurrentIndex(0)
        raporlar.pdf_kaydet(raporlar.html_kart(baglam, k['id']), os.path.join(klasor, f'kart_{i + 1}.pdf'))
    # izin penceresi (yeni + düzenleme)
    from .dialog_izin import IzinDialog
    from .dialog_personel import PersonelDialog
    k = sorted(s.calisanlar(), key=lambda k: k['kalan'])[-1]
    d = IzinDialog(baglam, personel_id=k['id'], tarih=baglam.bugun)
    d.bit.setTarih(baglam.bugun.replace(day=min(baglam.bugun.day + 6, 28)) if baglam.bugun.day <= 22 else baglam.bugun)
    d.show()
    d._onizle()
    kaydet(d, 'dialog_izin_yeni')
    d.close()
    kayit = sorted((x for x in s.kayit.values() if x['uyarilar'] and x['gecerli']), key=lambda x: x['bas'])[-1]
    d = IzinDialog(baglam, kayit_id=kayit['id'])
    d.show()
    kaydet(d, 'dialog_izin_duzenle')
    d.close()
    d = PersonelDialog(baglam, ornek[0]['id'] if ornek else None)
    d.show()
    kaydet(d, 'dialog_personel')
    d.close()
    raporlar.pdf_kaydet(raporlar.html_form(baglam, kayit['id']), os.path.join(klasor, 'form.pdf'))
    raporlar.pdf_kaydet(raporlar.html_genel(baglam), os.path.join(klasor, 'genel.pdf'), yatay=True)
    raporlar.pdf_kaydet(raporlar.html_takvim(baglam, baglam.bugun.year, baglam.bugun.month), os.path.join(klasor, 'takvim.pdf'), yatay=True)
    from .. import disa_aktar
    disa_aktar.excel_yaz(baglam, os.path.join(klasor, 'disa_aktarim.xlsx'))
    # Ayarlar sayfasının tamamı ve güvenlik pencereleri (yalnız gösterim; veriye dokunmaz, örnek kurtarma anahtarı gerçek değildir)
    pencere.git('ayar')
    kaydet(pencere.sayfa['ayar'].icerik, 'sayfa_ayar_tamami')
    from .giris import (GirisPenceresi, HesapOlusturPenceresi, KullaniciPenceresi, KurtarmaAnahtariPenceresi, KurtarmaPenceresi,
                        ParolaDegistirPenceresi)
    sayac = guvenlik.GirisSayaci(os.path.join(klasor, 'giris_ornek.json'))
    for ad, w in (('giris', GirisPenceresi(baglam.db.yol, sayac)), ('kilit', GirisPenceresi(baglam.db.yol, sayac, db=baglam.db)),
                  ('parolami_unuttum', KurtarmaPenceresi(baglam.db.yol, sayac)),
                  ('hesap_olustur', HesapOlusturPenceresi(os.path.join(klasor, 'ornek.vt'))),
                  ('kurtarma_anahtari', KurtarmaAnahtariPenceresi(guvenlik.kurtarma_uret())),
                  ('parola_degistir', ParolaDegistirPenceresi(baglam.db)), ('kullanici_yeni', KullaniciPenceresi(baglam.db))):
        w.show()
        kaydet(w, f'guvenlik_{ad}')
        w.hide()
    pencere.close()
    return 0
