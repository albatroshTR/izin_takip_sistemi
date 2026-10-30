# -*- coding: utf-8 -*-
"""
Programın uçtan uca sınaması (pencere görünmeden; QT_QPA_PLATFORM=offscreen): örnek veri yükleme, personel ve izin işlemleri
pencereler üzerinden, kalanın değişimi, kontroller, iptal / silme, tatil, ayrılan ödemesi, şifreli yedek ve geri dönüş, PDF ve Excel
çıktıları; güvenlik: şifreli veri dosyası, parola / kurtarma anahtarı, değiştirilmiş dosya, kullanıcılar ve roller, hatalı giriş
sayacı, kilit ekranı, tek örnek kilidi. Veri tamamen uydurmadır (izin_takip/ornek_veri.py); gerçek veri klasörüne dokunmaz (geçici klasör).

Kullanım (deponun kök klasöründen): python testler/test_uygulama.py
"""
import datetime
import os
import shutil
import sys
import tempfile

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, KOK)

from izin_takip import guvenlik, motor, ornek_veri, yollar  # noqa: E402
from izin_takip.veritabani import Veritabani, VeriHatasi, YedekAnahtariGerekli  # noqa: E402

D = datetime.date
BUGUN = D(2026, 10, 25)
PAROLA, PAROLA2 = 'Sinama-parola1', 'Yeni-parola-22'
sonuclar = []


def kontrol(ad, kosul, ayrinti=''):
    sonuclar.append((ad, bool(kosul), ayrinti))
    print(('  ✓ ' if kosul else '  ✗ ') + ad + (f' — {ayrinti}' if ayrinti and not kosul else ''))


def _acilir(yol, **anahtar):
    try:
        guvenlik.dosya_ac(guvenlik.oku(yol), **anahtar)
        return True
    except VeriHatasi:
        return False


def _reddedilir(f, tur=VeriHatasi):
    try:
        f()
        return False
    except tur:
        return True


def guvenlik_sinamasi(app, db, b, pencere, kurtarma, gecici, uyarilar):
    print('Güvenlik: şifreli veri dosyası')
    yol = db.yol
    ham = guvenlik.oku(yol)
    adlar = [p['ad'] for p in db.veri()['personel']]
    kontrol('veri dosyasında düz metin yok (SQLite başlığı, tablo adı, personel adları)',
            ham.startswith(guvenlik.SIHIR) and b'SQLite format' not in ham and b'personel' not in ham
            and not any(a.encode('utf-8') in ham for a in adlar))
    kontrol('doğru parola açar (kullanıcı adında büyük harf / Türkçe İ fark etmez)', _acilir(yol, kullanici_adi='AYŞE.ÖRNEK', parola=PAROLA))
    m1 = m2 = None
    try:
        guvenlik.dosya_ac(ham, 'ayse.ornek', 'yanlis-parola1')
    except guvenlik.ParolaHatasi as e:
        m1 = str(e)
    try:
        guvenlik.dosya_ac(ham, 'olmayan.kisi', PAROLA)
    except guvenlik.ParolaHatasi as e:
        m2 = str(e)
    kontrol('yanlış parola ve bilinmeyen kullanıcı adı aynı mesajla reddedilir', m1 and m1 == m2, f'{m1} / {m2}')
    kontrol('kurtarma anahtarı açar (küçük harf, tiresiz, boşluklu)', _acilir(yol, kurtarma=kurtarma.lower().replace('-', ' ')))
    kontrol('yanlış kurtarma anahtarı açmaz', not _acilir(yol, kurtarma='A' * 32))
    bozuk = []
    for konum in (12, 60, len(ham) // 2, len(ham) - 3):
        x = bytearray(ham)
        x[konum] ^= 0x01
        bozuk.append(_reddedilir(lambda: guvenlik.dosya_ac(bytes(x), 'ayse.ornek', PAROLA)))
    kontrol('başlığında ya da gövdesinde tek bayt değişen dosya açılmaz', all(bozuk), str(bozuk))
    kontrol('personel adında HTML işareti kabul edilmez', _reddedilir(lambda: db.personel_kaydet(
        {'ad': '<img src=x>', 'donemler': [(D(2020, 1, 1), None)]})))

    print('Güvenlik: kullanıcılar ve roller')
    kid = db.kullanici_ekle('Şükrü.Kurgu', 'Şükrü Kurgu', 'kullanici', 'Gecici-parola1')
    kontrol('kullanıcı adı sadeleştirilir (Şükrü.Kurgu → sukru.kurgu), geçici parolayla açar',
            any(k['kullanici_adi'] == 'sukru.kurgu' for k in db.kullanicilar()) and _acilir(yol, kullanici_adi='sukru.kurgu', parola='Gecici-parola1'))
    kontrol('aynı kullanıcı adı, geçersiz ad ve zayıf parolalar reddedilir', all(_reddedilir(f) for f in (
        lambda: db.kullanici_ekle('sukru.kurgu', 'Başka', 'kullanici', 'Gecici-parola1'),
        lambda: db.kullanici_ekle('a b', 'X', 'kullanici', 'Gecici-parola1'),
        lambda: db.kullanici_ekle('mehmet', 'Mehmet', 'kullanici', 'kisa1'),
        lambda: db.kullanici_ekle('mehmet', 'Mehmet', 'kullanici', 'sadeceharfler'),
        lambda: db.kullanici_ekle('mehmet1234', 'Mehmet', 'kullanici', 'Mehmet1234'))))
    yedek_ayse = db.yedekle(os.path.join(db.yedek_klasoru, 'personel_takip_elle_sinama.vt'))
    kopya = os.path.join(gecici, 'kopya', 'personel_takip.vt')
    os.makedirs(os.path.dirname(kopya))
    shutil.copy(yol, kopya)
    da = Veritabani.ac(kopya, 'sukru.kurgu', 'Gecici-parola1')
    kontrol('yeni kullanıcı ilk girişte parolasını değiştirmeli', da.oturum['parola_degismeli'] == 1 and da.oturum['rol'] == 'kullanici')
    kontrol('Kullanıcı rolü yönetici işlerini yapamaz (kullanıcı ekleme, sıfırlama, kurtarma anahtarı, geri dönüş)', all(_reddedilir(f) for f in (
        lambda: da.kullanici_ekle('zeki', 'Zeki', 'kullanici', 'Gecici-parola1'), lambda: da.parola_sifirla(kid, 'Gecici-parola2'),
        lambda: da.kurtarma_yenile(), lambda: da.yedekten_don(yedek_ayse))))
    da.parola_degistir('Gecici-parola1', 'Ayse-kendi-1')
    k_ayse = da.izin_kaydet({'personel_id': da.veri()['personel'][0]['id'], 'tur': 'MZ', 'bas': D(2026, 10, 21)})
    kontrol('parolasını değiştirir; izin kaydında "Giren" giriş yapan kişidir',
            da.oturum['parola_degismeli'] == 0 and next(k for k in da.veri()['izinler'] if k['id'] == k_ayse)['giren'] == 'Şükrü Kurgu')
    da.kapat()
    kontrol('son yönetici rolünü kaybedemez, kişi kendi hesabını silemez', _reddedilir(
        lambda: db.kullanici_duzenle(db.oturum['id'], 'Ayşe Örnek', 'kullanici')) and _reddedilir(lambda: db.kullanici_sil(db.oturum['id'])))
    db.parola_sifirla(kid, 'Sifirlandi-22')
    kontrol('yönetici parolayı sıfırlar: geçici parola açar, değiştirme zorunlu',
            _acilir(yol, kullanici_adi='sukru.kurgu', parola='Sifirlandi-22') and next(k for k in db.kullanicilar() if k['id'] == kid)['parola_degismeli'])
    kontrol('kullanıcının anahtarı yedekte de var (silmeden önce)', _acilir(yedek_ayse, kullanici_adi='sukru.kurgu', parola='Sifirlandi-22'))
    db.kullanici_sil(kid)
    kontrol('silinen kullanıcı ne veri dosyasını ne yedekleri açabilir', not _acilir(yol, kullanici_adi='sukru.kurgu', parola='Sifirlandi-22')
            and not _acilir(yedek_ayse, kullanici_adi='sukru.kurgu', parola='Sifirlandi-22'))

    print('Güvenlik: parola ve kurtarma anahtarı')
    kontrol('mevcut parola yanlışsa değiştirilemez', _reddedilir(lambda: db.parola_degistir('yanlis-parola1', PAROLA2), guvenlik.ParolaHatasi))
    db.parola_degistir(PAROLA, PAROLA2)
    yedekler = [os.path.join(db.yedek_klasoru, f) for f in os.listdir(db.yedek_klasoru) if f.endswith('.vt')]
    kontrol('parola değişince eski parola ne dosyayı ne yedekleri açar; yenisi hepsini açar',
            not _acilir(yol, kullanici_adi='ayse.ornek', parola=PAROLA) and _acilir(yol, kullanici_adi='ayse.ornek', parola=PAROLA2)
            and not any(_acilir(y, kullanici_adi='ayse.ornek', parola=PAROLA) for y in yedekler)
            and all(_acilir(y, kullanici_adi='ayse.ornek', parola=PAROLA2) for y in yedekler), str(len(yedekler)))
    yeni_kurtarma = db.kurtarma_yenile()
    kontrol('yeni kurtarma anahtarı açar, eskisi geçersiz', _acilir(yol, kurtarma=yeni_kurtarma) and not _acilir(yol, kurtarma=kurtarma))
    shutil.copy(yol, kopya)
    dk = Veritabani.kurtarma_ile_ac(kopya, yeni_kurtarma)
    dk.parola_kurtar('ayse.ornek', 'Kurtarilan-parola1')
    dk.oturum_ac('ayse.ornek')
    dk.kapat()
    kontrol('kurtarma anahtarıyla yeni parola belirlenir', _acilir(kopya, kullanici_adi='ayse.ornek', parola='Kurtarilan-parola1'))

    print('Güvenlik: başka kurulumun yedeği')
    baska = os.path.join(gecici, 'baska', 'personel_takip.vt')
    d3, k3 = Veritabani.olustur(baska, 'baska', 'Başka Kurulum', 'Baska-parola1')
    d3.personel_kaydet({'ad': 'BAŞKA KİŞİ', 'donemler': [(D(2021, 1, 4), None)]})
    d3.kapat()
    yedek_simdi = db.yedekle(os.path.join(db.yedek_klasoru, 'personel_takip_elle_sinama2.vt'))
    kontrol('başka kurulumun yedeği o kurulumun anahtarı olmadan geri yüklenmez', _reddedilir(lambda: db.yedekten_don(baska), YedekAnahtariGerekli))
    db.yedekten_don(baska, kullanici_adi='baska', parola='Baska-parola1')
    kontrol('o kurulumun parolasıyla geri yüklenir; bu kurulumun hesapları ve parolası değişmez',
            [p['ad'] for p in db.veri()['personel']] == ['BAŞKA KİŞİ'] and [k['kullanici_adi'] for k in db.kullanicilar()] == ['ayse.ornek']
            and _acilir(yol, kullanici_adi='ayse.ornek', parola=PAROLA2))
    db.yedekten_don(yedek_simdi)
    b.yenile()

    print('Güvenlik: hatalı giriş sayacı, kilit ekranı, tek örnek')
    saat = [1000.0]
    sayac_yolu = os.path.join(gecici, 'giris.json')
    s = guvenlik.GirisSayaci(sayac_yolu, saat=lambda: saat[0])
    for _ in range(4):
        s.hata()
    b4 = s.bekleme()
    s.hata()
    b5 = s.bekleme()
    s.hata()
    b6 = s.bekleme()
    saat[0] += 61
    kontrol('5. hatalı denemeden sonra 30 sn, sonra iki katı bekleme; süre dolunca yeniden denenir', (b4, b5, b6, s.bekleme()) == (0, 30, 60, 0),
            str((b4, b5, b6, s.bekleme())))
    s2 = guvenlik.GirisSayaci(sayac_yolu)
    kontrol('sayaç dosyada kalır, başarılı girişte sıfırlanır', s2.hatali == 6 and s2.basari()[0] == 6 and guvenlik.GirisSayaci(sayac_yolu).hatali == 0)

    from izin_takip.arayuz.giris import GirisPenceresi
    from izin_takip.arayuz.oturum import Oturum
    oturum = Oturum(app, b, pencere, guvenlik.GirisSayaci(os.path.join(gecici, 'giris2.json')))
    olay = {}

    def sahte_exec(self):   # kilit ekranı beklemesin: önce yanlış, sonra doğru parola
        olay['gorunur'] = pencere.isVisible()
        self.parola.setText('yanlis-parola9')
        self._giris()
        olay['yanlis'] = self.secim
        self.parola.setText(PAROLA2)
        self._giris()
        return 1
    eski_exec = GirisPenceresi.exec
    GirisPenceresi.exec = sahte_exec
    try:
        b.kilit_iste.emit()
        kontrol('kilitlenince pencereler gizlenir; yanlış parola açmaz, doğrusu açar',
                olay.get('gorunur') is False and olay.get('yanlis') is None and pencere.isVisible() and not oturum.kilitli, str(olay))
        olay.clear()
        oturum.son -= oturum.sure() + 1
        oturum._kontrol()
        kontrol('boşta kalınca otomatik kilitlenir', 'gorunur' in olay and pencere.isVisible())
    finally:
        GirisPenceresi.exec = eski_exec
    from PySide6.QtCore import QLockFile
    k1, k2 = QLockFile(yollar.kilit_yolu()), QLockFile(yollar.kilit_yolu())
    k1.setStaleLockTime(0)
    k2.setStaleLockTime(0)
    kontrol('program aynı veri klasöründe ikinci kez açılamaz (kilit dosyası)', k1.tryLock(100) and not k2.tryLock(100))
    k1.unlock()


def calistir():
    gecici = tempfile.mkdtemp(prefix='izin_takip_test_')
    try:
        yollar.veri_klasoru_ayarla(gecici)
        from PySide6.QtWidgets import QApplication, QMessageBox
        from izin_takip.arayuz import tema
        uyarilar = []
        QMessageBox.exec = lambda self: uyarilar.append(self.text()) or 0   # pencere içi uyarılar beklemesin; metni kaydedilir
        app = QApplication.instance() or QApplication(['test'])
        tema.yazi_tiplerini_yukle()
        app.setStyleSheet(tema.qss())
        from izin_takip.arayuz.baglam import Baglam
        from izin_takip.arayuz.ana_pencere import AnaPencere
        from izin_takip.arayuz.dialog_izin import IzinDialog
        from izin_takip.arayuz.dialog_personel import PersonelDialog
        from izin_takip import raporlar, disa_aktar

        db, kurtarma = Veritabani.olustur(yollar.veritabani_yolu(), 'ayse.ornek', 'Ayşe Örnek', PAROLA)
        db.tarih_ust = BUGUN
        print('Örnek veri')
        v = ornek_veri.uret()
        db.veri_yukle(v, 'örnek veri')
        kontrol('örnek veri yüklendi (personel, izin, tatil)', len(db.veri()['personel']) == len(v['personel'])
                and len(db.veri()['izinler']) == len(v['izinler']) and len(db.veri()['tatiller']) == len(v['tatiller']) > 100)
        try:
            db.veri_yukle(v, 'örnek veri')
            kontrol('dolu veritabanına ikinci yükleme engellenir', False)
        except VeriHatasi:
            kontrol('dolu veritabanına ikinci yükleme engellenir', True)
        ks0 = motor.hesapla_hepsi(db.veri(), BUGUN)
        kontrol('örnek veride kıdem, yaş ve avans durumları hesaplandı',
                any(x['kalan'] is not None and x['kalan'] < 0 for x in ks0.kisi.values()) and any(x['kalan'] and x['kalan'] > 20 for x in ks0.kisi.values()))

        b = Baglam(db)
        pencere = AnaPencere(b)
        pencere.resize(1440, 900)
        pencere.show()
        app.processEvents()
        for ad in ('genel', 'personel', 'izinler', 'takvim', 'ayrilan', 'kontrol', 'tatil', 'ayar', 'yardim'):
            pencere.git(ad)
            app.processEvents()
        kontrol('bütün sayfalar açıldı', True)

        print('Personel')
        d = PersonelDialog(b)
        d.ad.setText('test kişi çalışkan')
        d.dogum.setTarih(D(1970, 3, 15))
        d.satirlar[0].giris.setTarih(D(2020, 1, 6))
        d._kaydet()
        pid = d.pid
        kontrol('yeni personel kaydedildi (ad Türkçe büyük harfe çevrildi)', d.sonuc_kodu == 'kaydedildi' and db.personel_adi(pid) == 'TEST KİŞİ ÇALIŞKAN')
        b.yenile()
        ks = b.kisi(pid)
        # 2020-01-06 girişi: 6 hak (2021–2026), 1–5. yıl 14; 6. yıl 20; 50 yaş: 15.03.2020'de 50 → hak tarihlerinde 50+ → en az 20
        kontrol('yeni kişinin hak ve kalanı', ks['hak_son'] == 20 * 6 and ks['kalan'] == 120, f'{ks["hak_son"]} / {ks["kalan"]}')
        d = PersonelDialog(b)
        d.ad.setText('TEST KİŞİ ÇALIŞKAN')
        d.satirlar[0].giris.setTarih(D(2021, 1, 1))
        d._kaydet()
        kontrol('aynı adla ikinci personel engellenir (uyarı gösterilir)', d.sonuc_kodu is None and 'başka bir personel var' in uyarilar[-1], str(uyarilar[-1:]))
        d.close()

        print('İzin')
        d = IzinDialog(b, personel_id=pid)
        d._tur_sec('Kİ')
        d.bas.setTarih(D(2026, 11, 2))   # Pazartesi
        d.bit.setTarih(D(2026, 11, 8))   # Pazar
        d._onizle()
        kontrol('önizleme: 7 takvim günü, 6 gün düşülür (Pazar hariç)', d.o_buyuk.text() == '6 gün' and d.o_satirlar['takvim'].text().startswith('7 gün'),
                d.o_buyuk.text() + ' / ' + d.o_satirlar['takvim'].text())
        kontrol('önizleme: işe dönüş Pazartesi 09.11.2026', d.o_satirlar['isbasi'].text() == 'Pazartesi 09.11.2026', d.o_satirlar['isbasi'].text())
        kontrol('önizleme: kalan 120 → 114', d.o_satirlar['once'].text() == '120 gün' and d.o_satirlar['sonra'].text() == '114 gün',
                d.o_satirlar['once'].text() + ' → ' + d.o_satirlar['sonra'].text())
        d._kaydet()
        b.yenile()
        kid = max(k['id'] for k in b.veri['izinler'])
        kontrol('izin kaydedildi, kalan 114', b.kisi(pid)['kalan'] == 114 and b.kayit(kid)['dusulen'] == 6)
        kontrol('giren ve yazıldığı tarih dolduruldu', b.izin(kid)['giren'] and b.izin(kid)['yazildigi'] == D.today())
        # arife (yarım gün) + bayram: 2026 Ramazan arifesi 19.03.2026 (yarım), 20.03 tam
        d = IzinDialog(b, personel_id=pid)
        d._tur_sec('Kİ')
        d.bas.setTarih(D(2026, 3, 18))
        d.bit.setTarih(D(2026, 3, 21))
        d._onizle()
        kontrol('arife yarım gün, bayram düşülmez (18–21.03.2026 → 1,5 gün)', d.o_buyuk.text() == '1,5 gün', d.o_buyuk.text())
        d.close()
        # avans uyarısı
        d = IzinDialog(b, personel_id=pid)
        d._tur_sec('Kİ')
        d.bas.setTarih(D(2026, 12, 1))
        d.bit.setTarih(D(2027, 5, 31))
        d._onizle()
        kontrol('uzun izinde avans ve 60 gün uyarısı', 'avans' in d.o_uyari.text() and '60 günden uzun' in d.o_uyari.text(), d.o_uyari.text())
        d.close()
        # düzenleme: tarih değiştir
        d = IzinDialog(b, kayit_id=kid)
        d.bit.setTarih(D(2026, 11, 4))
        d._kaydet()
        b.yenile()
        kontrol('izin düzenlendi (3 gün), kalan 117', b.kisi(pid)['kalan'] == 117, str(b.kisi(pid)['kalan']))
        # iptal / geri al
        db.izin_iptal(kid, True)
        b.yenile()
        kontrol('iptal edilen izin hesaptan çıkar', b.kisi(pid)['kalan'] == 120)
        db.izin_iptal(kid, False)
        b.yenile()
        kontrol('iptal geri alınır', b.kisi(pid)['kalan'] == 117)
        try:
            db.personel_sil(pid)
            kontrol('izin kaydı olan personel silinemez', False)
        except VeriHatasi:
            kontrol('izin kaydı olan personel silinemez', True)
        # rapor md.55/a uyarısı: kıdem 5+ yıl → 98 gün sınırı; 100 günlük rapor
        k2 = db.izin_kaydet({'personel_id': pid, 'tur': 'RP', 'bas': D(2026, 1, 1), 'bit': D(2026, 4, 10)})
        b.yenile()
        kontrol('uzun raporda md.55/a uyarısı', any('md.55/a' in u for u in b.kayit(k2)['uyarilar']), str(b.kayit(k2)['uyarilar']))
        db.izin_sil(k2)
        b.yenile()
        kontrol('kayıt silindi', b.kayit(k2) is None)

        print('Ayrılan ve ödeme')
        d = PersonelDialog(b, pid)
        d.satirlar[0].cikis.setTarih(D(2026, 10, 15))
        d._kaydet()
        b.yenile()
        ks = b.kisi(pid)
        kontrol('çıkış yazılınca kişi Ayrıldı olur', ks['durum'] == 'Ayrıldı' and not ks['aktif'])
        kontrol('ödenecek gün = artı kalan', ks['odenecek'] == max(0, ks['kalan']), f'{ks["odenecek"]} / {ks["kalan"]}')
        from izin_takip.arayuz.sayfa_ayrilanlar import odeme_satiri
        db.odeme_kaydet(pid, {'ucret': 30000.0, 'odendi': 'Ödenmedi'})
        b.yenile()
        o = odeme_satiri(b.kisi(pid), b.veri['odemeler'].get(pid), b.bugun)
        kontrol('izin ücreti tutarı = gün × ücret ÷ 30', o['tutar'] == round(ks['odenecek'] * 1000, 2) and o['borc'] == o['tutar'], str(o))
        kontrol('zamanaşımı = çıkış + 5 yıl', o['zaman'] == D(2031, 10, 15))
        pencere.git('ayrilan')
        app.processEvents()
        kontrol('Ayrılanlar sayfasında listelenir (örnek veride 1 ayrılan + bu kişi)', pencere.sayfa['ayrilan'].model.rowCount() == 2)

        print('Tatil')
        n0 = len(b.veri['tatiller'])
        db.tatil_kaydet({'tarih': D(2031, 1, 1), 'ad': 'Yılbaşı', 'tur': 'tam'})
        try:
            db.tatil_kaydet({'tarih': D(2031, 1, 1), 'ad': 'tekrar', 'tur': 'tam'})
            kontrol('aynı güne ikinci tatil engellenir', False)
        except VeriHatasi:
            kontrol('aynı güne ikinci tatil engellenir', True)
        b.yenile()
        kontrol('tatil eklendi', len(b.veri['tatiller']) == n0 + 1)

        print('Çıktılar')
        cikti = os.path.join(gecici, 'cikti')
        os.makedirs(cikti)
        biri = b.sonuc.calisanlar()[0]
        for ad, html, yatay in (('kart', raporlar.html_kart(b, biri['id']), False), ('form', raporlar.html_form(b, kid), False),
                                ('genel', raporlar.html_genel(b), True), ('takvim', raporlar.html_takvim(b, 2026, 9), True)):
            yol = raporlar.pdf_kaydet(html, os.path.join(cikti, ad + '.pdf'), yatay)
            with open(yol, 'rb') as f:
                bas = f.read(5)
            kontrol(f'PDF: {ad}', bas == b'%PDF-' and os.path.getsize(yol) > 5000, str(os.path.getsize(yol)))
        x = disa_aktar.excel_yaz(b, os.path.join(cikti, 'rapor.xlsx'))
        import openpyxl
        wb = openpyxl.load_workbook(x)
        kontrol('Excel çıktısı: sayfalar', wb.sheetnames[:4] == ['Genel Durum', 'İzin Kayıtları', 'Personel', 'Tatiller'] and 'Ayrılanlar' in wb.sheetnames,
                str(wb.sheetnames))
        kontrol('Excel çıktısı: satır sayıları', wb['İzin Kayıtları'].max_row - 4 == len(b.veri['izinler']) and wb['Personel'].max_row - 4 == len(b.veri['personel']))

        print('Yedek')
        y = db.gunluk_yedek()
        kontrol('günlük yedek alındı (şifreli)', y and os.path.exists(y) and guvenlik.oku(y).startswith(guvenlik.SIHIR))
        kontrol('aynı gün ikinci yedek alınmaz', db.gunluk_yedek() is None)
        db.izin_kaydet({'personel_id': biri['id'], 'tur': 'MZ', 'bas': D(2026, 10, 20)})
        n_once = len(db.veri()['izinler'])
        db.yedekten_don(y)
        kontrol('yedekten geri dönülünce son kayıt geri alınmış olur', len(db.veri()['izinler']) == n_once - 1)
        kontrol('işlem günlüğü tutuluyor', len(db.gunluk_listesi()) >= 10, str(len(db.gunluk_listesi())))
        b.yenile()

        guvenlik_sinamasi(app, db, b, pencere, kurtarma, gecici, uyarilar)
        db.kapat()
        pencere.close()
    finally:
        shutil.rmtree(gecici, ignore_errors=True)
    hatali = [s for s in sonuclar if not s[1]]
    print(f'\nSONUÇ: {len(sonuclar) - len(hatali)}/{len(sonuclar)} geçti')
    return 1 if hatali else 0


if __name__ == '__main__':
    sys.exit(calistir())
