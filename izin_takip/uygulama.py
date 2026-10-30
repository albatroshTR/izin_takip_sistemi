# -*- coding: utf-8 -*-
"""Programın giriş noktası.

  python -m izin_takip   (deponun kök klasöründen)  ya da  python baslat.py  ya da  İzin Takip Sistemi.exe
Seçenekler:
  --veri <klasör>          veri dosyası ve yedeklerin klasörü (varsayılan: Belgeler\\İzin Takip Sistemi)
  --ornek-veri             pencere açmadan boş veritabanına uydurma örnek veriyi yükler ve sonucu yazar
  --deneme                 pencere açmadan veri dosyasını açar, hesaplar ve özet yazar (kurulum denemesi; çıkış kodu 0 = sorunsuz)
  --ekran-goruntusu <klasör>  her sayfanın ekran görüntüsünü PNG olarak kaydeder ve kapanır (geliştirme / doğrulama)
Bu kullanımlarda giriş penceresi açılmaz: hesap IZIN_TAKIP_KULLANICI / IZIN_TAKIP_PAROLA ortam değişkenlerinden okunur (yalnız otomatik
sınama içindir; programın normal açılışı bunlara bakmaz, her zaman kullanıcı adı ve parola ister). Veri dosyası yoksa --ornek-veri bu
hesapla yönetici oluşturur.
"""
import argparse
import os
import sys
import traceback


def _argumanlar(argv):
    a = argparse.ArgumentParser(prog='İzin Takip Sistemi', add_help=True)
    a.add_argument('--veri')
    a.add_argument('--ornek-veri', action='store_true')
    a.add_argument('--deneme', action='store_true')
    a.add_argument('--ekran-goruntusu')
    a.add_argument('--tarih', help='hesap tarihi (YYYY-MM-DD; yalnız --ekran-goruntusu / --deneme)')
    return a.parse_known_args(argv)[0]


def _konsol(metin):
    try:
        print(metin)
    except Exception:  # pencereli programda konsol yok
        pass


def _ortamla_ac(olustur=False):
    """Pencere açmayan kullanımlar: hesap ortam değişkenlerinden."""
    from . import yollar
    from .veritabani import Veritabani, VeriHatasi
    ad, parola = os.environ.get('IZIN_TAKIP_KULLANICI'), os.environ.get('IZIN_TAKIP_PAROLA')
    if not ad or not parola:
        raise VeriHatasi('Bu kullanım için IZIN_TAKIP_KULLANICI ve IZIN_TAKIP_PAROLA ortam değişkenleri gerekli.')
    yol = yollar.veritabani_yolu()
    if os.path.exists(yol):
        return Veritabani.ac(yol, ad, parola)
    if not olustur:
        raise VeriHatasi(f'Veri dosyası yok: {yol}')
    db, kurtarma = Veritabani.olustur(yol, ad, os.environ.get('IZIN_TAKIP_AD_SOYAD') or 'Yönetici', parola)
    _konsol(f'Yeni şifreli veri dosyası: {yol}\nKurtarma anahtarı: {kurtarma}')
    return db


def _yeniden_baslat():
    """Oturum kapatılınca / farklı kullanıcıyla girilince program giriş ekranıyla yeniden açılır."""
    from PySide6.QtCore import QProcess
    if getattr(sys, 'frozen', False):
        QProcess.startDetached(sys.executable, sys.argv[1:])
    elif os.path.basename(sys.argv[0]) == '__main__.py':
        QProcess.startDetached(sys.executable, ['-m', 'izin_takip'] + sys.argv[1:], os.getcwd())
    else:
        QProcess.startDetached(sys.executable, [os.path.abspath(sys.argv[0])] + sys.argv[1:], os.getcwd())


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    arg = _argumanlar(argv)
    from . import yollar
    if arg.veri:
        yollar.veri_klasoru_ayarla(arg.veri)

    from .veritabani import VeriHatasi
    if arg.ornek_veri or arg.deneme:
        from . import motor, ornek_veri
        from .yardimci import D, sayi_yaz
        try:
            db = _ortamla_ac(olustur=arg.ornek_veri)
        except VeriHatasi as e:
            _konsol(f'HATA: {e}')
            return 3
        if arg.ornek_veri:
            v = ornek_veri.uret()
            db.veri_yukle(v, 'örnek veri')
            _konsol(f'Örnek veri yüklendi: {len(v["personel"])} personel, {len(v["izinler"])} izin, {len(v["tatiller"])} tatil')
        bugun = D.fromisoformat(arg.tarih) if arg.tarih else db.hesap_tarihi()[0]
        s = motor.hesapla_hepsi(db.veri(), bugun)
        oz = motor.ozet(s, db.veri())
        _konsol(f'Veri dosyası: {db.yol}\nHesap tarihi {bugun:%d.%m.%Y}: {oz["calisan"]} çalışan, toplam kalan {sayi_yaz(oz["toplam_kalan"])} gün, '
                f'eksi {oz["eksi"]}, uyarılı kayıt {oz["uyarili_kayit"]}')
        db.kapat()
        return 0

    from PySide6.QtCore import QLocale, QLockFile
    from PySide6.QtGui import QIcon
    from PySide6.QtWidgets import QApplication, QMessageBox
    from . import UYGULAMA_ADI
    from .arayuz import tema
    if sys.platform == 'win32':  # görev çubuğunda kendi simgesi görünsün
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('IzinTakipSistemi.Uygulama')
        except Exception:
            pass
    QLocale.setDefault(QLocale(QLocale.Turkish, QLocale.Turkey))
    app = QApplication.instance() or QApplication(sys.argv[:1])
    app.setApplicationName(UYGULAMA_ADI)
    app.setOrganizationName('İzin Takip Sistemi')
    app.setStyle('Fusion')
    tema.yazi_tiplerini_yukle()
    app.setFont(tema.font(10))
    app.setPalette(tema.palet())
    app.setStyleSheet(tema.qss())
    app.setWindowIcon(QIcon(yollar.kaynak('simge.png')))

    def beklenmeyen(tur, deger, iz):
        metin = ''.join(traceback.format_exception(tur, deger, iz))
        try:
            with open(os.path.join(yollar.veri_klasoru(), 'hata_gunlugu.txt'), 'a', encoding='utf-8') as f:
                from datetime import datetime
                f.write(f'\n--- {datetime.now():%d.%m.%Y %H:%M:%S}\n{metin}')
        except OSError:
            pass
        m = QMessageBox(QMessageBox.Critical, 'Beklenmeyen hata', 'Beklenmeyen bir hata oluştu. Son işlem kaydedilmemiş olabilir.\n\n'
                        f'Ayrıntı veri klasöründeki hata_gunlugu.txt dosyasına yazıldı.\n\n{deger}')
        m.exec()
    sys.excepthook = beklenmeyen

    # aynı veri klasöründe ikinci bir pencere açılmasın (bellekteki iki kopya birbirinin kaydını ezerdi)
    kilit = QLockFile(yollar.kilit_yolu())
    kilit.setStaleLockTime(0)   # yalnız program hâlâ çalışıyorsa kilitli sayılır (çöken programın kilidi kendiliğinden kalkar)
    if not kilit.tryLock(3000):
        QMessageBox.warning(None, UYGULAMA_ADI, 'Program bu bilgisayarda zaten açık (görev çubuğuna bakın); aynı veri dosyası iki pencerede '
                                                'açılamaz.\n\nProgram kapalı olduğu hâlde bu uyarı çıkıyorsa veri klasöründeki ".kilit" '
                                                f'dosyasını silin:\n{yollar.veri_klasoru()}')
        return 0
    try:
        return _pencereli(app, arg)
    finally:
        kilit.unlock()


def _pencereli(app, arg):
    """Giriş (ya da ilk kurulum / taşıma), ana pencere ve oturum. Dönüş: çıkış kodu."""
    from PySide6.QtWidgets import QMessageBox
    from . import UYGULAMA_ADI, guvenlik, yollar
    from .arayuz import giris
    from .veritabani import VeriHatasi
    try:
        if arg.ekran_goruntusu:
            db, parola = _ortamla_ac(), None
        else:
            db, parola = giris.baslangic()
    except VeriHatasi as e:
        QMessageBox.critical(None, UYGULAMA_ADI, f'Veri dosyası açılamadı:\n{yollar.veritabani_yolu()}\n\n{e}')
        return 2
    if db is None:   # girişten vazgeçildi
        return 0
    if db.oturum.get('parola_degismeli') and not arg.ekran_goruntusu:
        if not giris.ParolaDegistirPenceresi(db, zorunlu_eski=parola or '').exec():
            db.kapat()
            return 0
    parola = None
    try:
        db.gunluk_yedek()
    except OSError:
        pass
    if arg.tarih:
        from .yardimci import D
        db.tarih_ust = D.fromisoformat(arg.tarih)
    from .arayuz.baglam import Baglam
    from .arayuz.ana_pencere import AnaPencere
    from .arayuz.ilk_acilis import IlkAcilis
    from .arayuz.oturum import Oturum
    baglam = Baglam(db)
    if db.bos_mu() and baglam.yonetici and not db.ayar('bos_baslangic') and not arg.ekran_goruntusu:
        IlkAcilis(baglam).exec()
    pencere = AnaPencere(baglam)
    oturum = Oturum(app, baglam, pencere, guvenlik.GirisSayaci(yollar.giris_sayaci_yolu()))
    if arg.ekran_goruntusu:
        from .arayuz.ekran import goruntule
        sonuc = goruntule(app, pencere, baglam, arg.ekran_goruntusu)
        db.kapat()
        return sonuc
    pencere.showMaximized() if sys.platform == 'win32' else pencere.show()
    sonuc = app.exec()
    db.kapat()
    if oturum.yeniden_baslat:
        _yeniden_baslat()
    return sonuc


if __name__ == '__main__':
    sys.exit(main())
