# -*- coding: utf-8 -*-
"""Ayarlar: şirket adı ve hesap tarihi; hesabım ve güvenlik (parola, otomatik kilit, kurtarma anahtarı); kullanıcılar (yönetici);
veri klasörü ve şifreli yedekler; Excel'e aktarma; işlem geçmişi; hakkında (lisans)."""
import html
import os

from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QButtonGroup, QComboBox, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLineEdit, QPlainTextEdit,
                               QRadioButton, QScrollArea, QVBoxLayout, QWidget)

from . import tema as T
from .bilesenler import (Kart, ListeModeli, RozetDelegate, Sutun, TarihKutusu, bilgi, dugme, etiket, hata, secili_satir, soru, tablo,
                         tablo_karti)
from .giris import (KullaniciPenceresi, KurtarmaAnahtariPenceresi, ParolaDegistirPenceresi, ParolaSifirlaPenceresi,
                    YedekAnahtariPenceresi)
from .oturum import KILIT_SECENEK
from .sayfa import Sayfa
from .. import REPO, SURUM, TELIF, UYGULAMA_ADI, WEB, guvenlik, yollar
from ..veritabani import ROLLER, VeriHatasi, YedekAnahtariGerekli
from ..yardimci import tarih_iso


class AyarlarSayfa(Sayfa):
    baslik = 'Ayarlar'
    alt_baslik = 'Şirket ve hesap tarihi, hesabınız ve güvenlik, kullanıcılar, yedekler ve Excel aktarımı.'

    def __init__(self, baglam, parent=None):
        super().__init__(baglam, parent)
        kay = QScrollArea()
        kay.setWidgetResizable(True)
        ic = QWidget()
        ic.setObjectName('Icerik')
        self.icerik = ic
        d = QVBoxLayout(ic)
        d.setContentsMargins(0, 0, 8, 0)
        d.setSpacing(16)
        kay.setWidget(ic)
        self.duzen.addWidget(kay, 1)

        ust = QHBoxLayout()
        ust.setSpacing(16)
        # genel
        g = Kart('Genel', 'ayar')
        gl = QGridLayout()
        gl.setHorizontalSpacing(14)
        gl.setVerticalSpacing(10)
        self.sirket = QLineEdit()
        self.sirket.setPlaceholderText('İzin kartında ve belgelerde işveren adı')
        gl.addWidget(etiket('Şirket adı', 'Soluk'), 0, 0)
        gl.addWidget(self.sirket, 0, 1)
        g.duzen.addLayout(gl)
        g.duzen.addWidget(etiket('Hesap tarihi', 'BolumBaslik'))
        self.r_bugun = QRadioButton('Bugün (normalde bu seçili kalır)')
        self.r_elle = QRadioButton('Farklı bir tarihe göre hesapla:')
        grup = QButtonGroup(self)
        grup.addButton(self.r_bugun)
        grup.addButton(self.r_elle)
        self.tarih = TarihKutusu()
        g.duzen.addWidget(self.r_bugun)
        g.duzen.addLayout(_yatay(self.r_elle, self.tarih))
        g.duzen.addWidget(etiket('Geçmiş ya da gelecek bir tarihteki bakiyeyi görmek için. İşiniz bitince "Bugün"e dönün; '
                                 'farklı tarih seçiliyken her sayfada turuncu uyarı görünür.', 'SolukKucuk', True))
        g.duzen.addStretch(1)
        kaydet = dugme('Kaydet', 'onay', 'Birincil')
        kaydet.clicked.connect(self._kaydet)
        g.duzen.addWidget(kaydet, 0, Qt.AlignRight)
        ust.addWidget(g, 1)

        # hesabım ve güvenlik
        s = Kart('Hesabım ve güvenlik', 'kalkan')
        self.hesap = etiket('', None, True)
        s.duzen.addWidget(self.hesap)
        s.duzen.addWidget(etiket('Veriler ve yedekler parolalardan türetilen anahtarla AES-256 ile şifrelenir: parola ya da kurtarma anahtarı '
                                 'olmadan veri dosyası açılamaz; program dışında değiştirilirse program dosyayı açmaz. PDF ve Excel '
                                 'çıktıları şifresizdir.', 'SolukKucuk', True))
        parola = dugme('Parolamı değiştir', 'anahtar')
        parola.clicked.connect(self._parola)
        kilit = dugme('Şimdi kilitle', 'kilit')
        kilit.clicked.connect(self.b.kilit_iste.emit)
        s.duzen.addLayout(_yatay(parola, kilit, None))
        self.kilit = QComboBox()
        for dk in KILIT_SECENEK:
            self.kilit.addItem(f'{dk} dakika', dk)
        self.kilit.activated.connect(self._kilit_suresi)
        s.duzen.addLayout(_yatay(etiket('Boşta kalınca otomatik kilit', 'Soluk'), self.kilit, None))
        self.kurtarma = dugme('Yeni kurtarma anahtarı…', 'anahtar')
        self.kurtarma.clicked.connect(self._kurtarma)
        temizle = dugme('Çıktı klasörünü temizle', 'sil')
        temizle.clicked.connect(self._ciktilari_temizle)
        s.duzen.addLayout(_yatay(self.kurtarma, temizle, None))
        s.duzen.addStretch(1)
        ust.addWidget(s, 1)
        d.addLayout(ust)

        # kullanıcılar (yönetici)
        self.k_kart = Kart('Kullanıcılar', 'personel')
        self.k_kart.duzen.addWidget(etiket('Programa girebilecek kişiler. Her işlem işlem geçmişine kimin yaptığıyla yazılır. Yeni kullanıcı '
                                           'ilk girişte geçici parolasını değiştirir. Silinen kullanıcı ne programa ne de yedeklere girebilir.',
                                           'SolukKucuk', True))
        self.m_kullanici = ListeModeli([
            Sutun('Kullanıcı adı', lambda r: r['kullanici_adi'], genislik=190, kalin=True),
            Sutun('Ad Soyad', lambda r: r['ad_soyad'], genislik=220),
            Sutun('Rol', lambda r: ROLLER[r['rol']], genislik=120),
            Sutun('Son giriş', lambda r: _zaman(r['son_giris'] or ''), sirala=lambda r: r['son_giris'] or '', genislik=150),
            Sutun('Durum', lambda r: 'İlk girişte parola değişecek' if r['parola_degismeli'] else '', renk=lambda r: T.TURUNCU_2),
        ])
        self.tv_kullanici, _ = tablo(self.m_kullanici)
        self.tv_kullanici.setItemDelegateForColumn(2, RozetDelegate(
            lambda m, r: (T.MOR_ACIK, T.MOR) if m == ROLLER['yonetici'] else ('#EEF0F6', T.YAZI), parent=self.tv_kullanici))
        self.tv_kullanici.setMinimumHeight(170)
        self.tv_kullanici.doubleClicked.connect(lambda _: self._k_duzenle())
        self.k_kart.duzen.addWidget(tablo_karti(self.tv_kullanici))
        yeni = dugme('Yeni kullanıcı', 'arti', 'Birincil')
        yeni.clicked.connect(self._k_yeni)
        duz = dugme('Düzenle', 'duzenle')
        duz.clicked.connect(self._k_duzenle)
        sifirla = dugme('Parolayı sıfırla', 'anahtar')
        sifirla.clicked.connect(self._k_sifirla)
        sil = dugme('Sil', 'sil', 'Tehlike')
        sil.clicked.connect(self._k_sil)
        self.k_kart.duzen.addLayout(_yatay(yeni, duz, sifirla, None, sil))
        d.addWidget(self.k_kart)

        alt = QHBoxLayout()
        alt.setSpacing(16)
        # veri ve yedek
        v = Kart('Veriler ve yedekler', 'yedek')
        self.klasor = etiket('', 'SolukKucuk', True)
        self.klasor.setTextInteractionFlags(Qt.TextSelectableByMouse)
        v.duzen.addWidget(etiket('Veri dosyası (şifreli)', 'Soluk'))
        v.duzen.addWidget(self.klasor)
        self.son_yedek = etiket('', 'SolukKucuk', True)
        v.duzen.addWidget(self.son_yedek)
        v.duzen.addWidget(etiket('Program her gün ilk açılışta şifreli bir yedek alır (son 60 gün saklanır). Veri klasörünü düzenli olarak '
                                 'bir USB belleğe ya da şirket sunucusuna da kopyalayın; yedekler de şifrelidir.', 'SolukKucuk', True))
        ac = dugme('Klasörü aç', 'klasor')
        ac.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(yollar.veri_klasoru())))
        yedek = dugme('Şimdi yedekle', 'yedek')
        yedek.clicked.connect(self._yedekle)
        self.geri = dugme('Yedekten geri dön…', 'geri_al')
        self.geri.clicked.connect(self._geri_don)
        v.duzen.addLayout(_yatay(ac, yedek, self.geri, None))
        v.duzen.addStretch(1)
        alt.addWidget(v, 1)

        # excel
        e = Kart('Excel', 'excel')
        e.duzen.addWidget(etiket('"Excel\'e aktar" '
                                 'kalan izinleri, izin kayıtlarını, personeli ve tatilleri rapor / arşiv için tek bir Excel dosyasına yazar '
                                 '(dosya programa geri okunmaz ve şifresizdir).', 'SolukKucuk', True))
        e.duzen.addStretch(1)
        dis = dugme('Excel\'e aktar', 'indir', 'Birincil')
        dis.clicked.connect(lambda: self.b.git.emit('excel', None))
        e.duzen.addLayout(_yatay(dis, None))
        alt.addWidget(e, 1)
        d.addLayout(alt)

        # günlük
        gk = Kart('İşlem geçmişi', 'saat')
        gk.duzen.addWidget(etiket('Programda yapılan her değişiklik ve her giriş (kim, ne zaman, ne) burada kaydedilir.', 'SolukKucuk'))
        self.m_gunluk = ListeModeli([
            Sutun('Zaman', lambda r: _zaman(r['zaman']), sirala=lambda r: r['zaman'], genislik=150),
            Sutun('Kullanıcı', lambda r: r['kullanici'] or '', genislik=170),
            Sutun('İşlem', lambda r: r['islem'], genislik=220, kalin=True),
            Sutun('Ayrıntı', lambda r: r['ayrinti'] or '', renk=lambda r: T.SOLUK, ipucu=lambda r: r['ayrinti'] or ''),
        ])
        self.tv_gunluk, _ = tablo(self.m_gunluk)
        self.tv_gunluk.setMinimumHeight(320)
        gk.duzen.addWidget(tablo_karti(self.tv_gunluk))
        d.addWidget(gk)

        # hakkında
        h = Kart('Hakkında', 'bilgi')
        h.duzen.addWidget(etiket(f'<b>{UYGULAMA_ADI}</b> · sürüm {SURUM}', None, True))
        h.duzen.addWidget(etiket(f'<b>{TELIF}</b>', None, True))
        h.duzen.addWidget(etiket('Yıllık izin hakları 4857 sayılı İş Kanunu md.53–60 ve Yıllık Ücretli İzin Yönetmeliği\'ne göre hesaplanır; '
                                 'kurallar Yardım sayfasında. Program "olduğu gibi" sunulur; kesin hukuki sonuçlar için işyerinizin '
                                 'hukuk / mali müşavirlik desteği esastır.', 'Soluk', True))
        web = dugme(WEB.split('//')[1], 'web', 'Bag')
        web.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(WEB)))
        repo = dugme('GitHub', 'web', 'Bag')
        repo.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(REPO)))
        lisans = dugme('Lisans bilgileri', 'dosya', 'Bag')
        lisans.clicked.connect(self._lisans)
        h.duzen.addLayout(_yatay(etiket('Yazar:', 'Soluk'), web, 16, repo, 16, lisans, None))
        d.addWidget(h)
        d.addStretch(1)

    # ------------------------------------------------------------------ genel
    def _kaydet(self):
        db = self.b.db
        if self.r_elle.isChecked():
            try:
                t = self.tarih.tarih()
            except ValueError:
                hata(self, 'Hesap tarihi anlaşılamadı (gün.ay.yıl).')
                return
            if not t:
                hata(self, 'Farklı hesap tarihi için bir tarih yazın ya da "Bugün"ü seçin.')
                return
            db.ayar_yaz('hesap_tarihi', tarih_iso(t))
        else:
            db.ayar_yaz('hesap_tarihi', '')
        db.ayar_yaz('sirket', self.sirket.text().strip() or 'Şirket')
        self.b.yenile('Ayarlar kaydedildi')

    # ------------------------------------------------------------------ güvenlik
    def _parola(self):
        if ParolaDegistirPenceresi(self.b.db, parent=self.window()).exec():
            self.b.yenile('Parola değiştirildi')

    def _kilit_suresi(self):
        try:
            self.b.db._yetki()
        except VeriHatasi as e:
            hata(self, str(e))
            self.yenile()
            return
        self.b.db.ayar_yaz('kilit_dakika', str(self.kilit.currentData()))
        self.b.yenile(f'Otomatik kilit: {self.kilit.currentData()} dakika')

    def _kurtarma(self):
        if not soru(self, 'Yeni kurtarma anahtarı', 'Yeni bir kurtarma anahtarı oluşturulsun mu? Eski anahtar hemen geçersiz olur '
                                                    '(yedekler de yeni anahtarla yeniden şifrelenir).', 'Oluştur'):
            return
        try:
            anahtar = self.b.db.kurtarma_yenile()
        except VeriHatasi as e:
            hata(self, str(e))
            return
        KurtarmaAnahtariPenceresi(anahtar, self.window()).exec()
        self.b.yenile('Yeni kurtarma anahtarı oluşturuldu')

    def _ciktilari_temizle(self):
        klasor = yollar.cikti_klasoru()
        dosyalar = [os.path.join(klasor, f) for f in os.listdir(klasor) if os.path.isfile(os.path.join(klasor, f))]
        if not dosyalar:
            bilgi(self, 'Çıktı klasörü zaten boş.', 'Çıktılar')
            return
        if not soru(self, 'Çıktı klasörünü temizle', f'Program içinden kaydedilen {len(dosyalar)} PDF / Excel dosyası (şifresiz) silinsin mi?\n\n'
                                                     f'{klasor}', 'Sil', tehlikeli=True):
            return
        n = 0
        for f in dosyalar:
            try:
                guvenlik.guvenli_sil(f)
                n += 1
            except OSError:   # açık dosya
                pass
        self.b.bildir.emit(f'{n} dosya silindi' + (f' ({len(dosyalar) - n} dosya açık olduğu için silinemedi)' if n < len(dosyalar) else ''),
                           'bilgi')

    # ------------------------------------------------------------------ kullanıcılar
    def _k_yeni(self):
        if KullaniciPenceresi(self.b.db, parent=self.window()).exec():
            self.b.yenile('Kullanıcı eklendi')

    def _k_duzenle(self):
        k = secili_satir(self.tv_kullanici)
        if k and KullaniciPenceresi(self.b.db, k, parent=self.window()).exec():
            self.b.yenile('Kullanıcı kaydedildi')

    def _k_sifirla(self):
        k = secili_satir(self.tv_kullanici)
        if k and ParolaSifirlaPenceresi(self.b.db, k, parent=self.window()).exec():
            self.b.yenile('Parola sıfırlandı')

    def _k_sil(self):
        k = secili_satir(self.tv_kullanici)
        if not k or not soru(self, 'Kullanıcıyı sil', f'{k["ad_soyad"]} ({k["kullanici_adi"]}) silinsin mi? Bu kişi artık programa ve '
                                                       'yedeklere giremez; yaptığı işlemler geçmişte kalır.', 'Sil', tehlikeli=True):
            return
        try:
            self.b.db.kullanici_sil(k['id'])
        except VeriHatasi as e:
            hata(self, str(e))
            return
        self.b.yenile('Kullanıcı silindi')

    # ------------------------------------------------------------------ yedek
    def _yedekle(self):
        from datetime import datetime
        yol = os.path.join(self.b.db.yedek_klasoru, f'personel_takip_elle_{datetime.now():%Y-%m-%d_%H%M%S}.vt')
        self.b.db.yedekle(yol)
        self.b.bildir.emit('Şifreli yedek alındı', 'bilgi')
        self.yenile()

    def _geri_don(self):
        yol, _ = QFileDialog.getOpenFileName(self, 'Geri dönülecek yedeği seçin', self.b.db.yedek_klasoru,
                                             'Yedek (*.vt);;Önceki sürümün şifresiz yedeği (*.db)')
        if not yol:
            return
        if not soru(self, 'Yedekten geri dön', f'Programdaki bütün veriler seçilen yedekteki hâline döndürülsün mü?\n\n{os.path.basename(yol)}\n\n'
                                               'Şu anki veriler ayrıca saklanır (yedekler klasöründe "geri_donus_oncesi"). Kullanıcı hesapları '
                                               've parolalar değişmez.', 'Geri dön', tehlikeli=True):
            return
        anahtar = {}
        while True:
            try:
                self.b.db.yedekten_don(yol, **anahtar)
                break
            except YedekAnahtariGerekli:
                p = YedekAnahtariPenceresi(self.window())
                if not p.exec():
                    return
                anahtar = p.sonuc
            except VeriHatasi as e:
                hata(self, str(e), 'Geri dönülemedi')
                return
        self.b.yenile('Yedekten geri dönüldü')

    def _lisans(self):
        dl = QDialog(self.window())
        dl.setWindowTitle('Lisans bilgileri')
        dl.resize(760, 560)
        dd = QVBoxLayout(dl)
        t = QPlainTextEdit()
        t.setReadOnly(True)
        try:
            with open(yollar.kaynak('LISANS.txt'), encoding='utf-8') as f:
                t.setPlainText(f.read())
        except OSError:
            t.setPlainText(TELIF)
        dd.addWidget(t)
        kapat = dugme('Kapat', tur='Birincil')
        kapat.clicked.connect(dl.accept)
        dd.addLayout(_yatay(None, kapat))
        dl.exec()

    # ------------------------------------------------------------------ yenile
    def yenile(self):
        db = self.b.db
        yonetici = self.b.yonetici
        self.sirket.setText(db.ayar('sirket') or 'Şirket')
        elle = db.ayar('hesap_tarihi')
        self.r_elle.setChecked(bool(elle))
        self.r_bugun.setChecked(not elle)
        self.tarih.setTarih(self.b.bugun if elle else None)
        o = db.oturum or {}
        once = _zaman(o.get('onceki_giris') or '')
        self.hesap.setText(f'<b>{_e(o.get("ad_soyad", ""))}</b> · {_e(o.get("kullanici_adi", ""))} · {ROLLER.get(o.get("rol"), "")}'
                           + (f'<br><span style="color:{T.SOLUK}">Önceki giriş: {once}</span>' if once else ''))
        i = self.kilit.findData(int(db.ayar('kilit_dakika') or 10))
        self.kilit.setCurrentIndex(i if i >= 0 else 1)
        for w, ipucu in ((self.kilit, 'Yalnız yönetici değiştirir'), (self.kurtarma, 'Yalnız yönetici'), (self.geri, 'Yalnız yönetici')):
            w.setEnabled(yonetici)
            w.setToolTip('' if yonetici else ipucu)
        self.k_kart.setVisible(yonetici)
        if yonetici:
            self.m_kullanici.doldur(db.kullanicilar())
        self.klasor.setText(db.yol)
        try:
            yedekler = sorted(f for f in os.listdir(db.yedek_klasoru) if f.endswith('.vt'))
        except OSError:
            yedekler = []
        self.son_yedek.setText(f'{len(yedekler)} yedek · son: {yedekler[-1]}' if yedekler else 'Henüz yedek yok.')
        self.m_gunluk.doldur(db.gunluk_listesi())


def _e(s):
    return html.escape(s or '')


def _zaman(s):
    if not s:
        return ''
    try:
        g, sa = s.split(' ')
        y, a, gn = g.split('-')
        return f'{gn}.{a}.{y} {sa[:5]}'
    except ValueError:
        return s


def _yatay(*w):
    from .bilesenler import yatay
    return yatay(*w)
