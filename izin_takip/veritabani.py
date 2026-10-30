# -*- coding: utf-8 -*-
"""
Veritabanı: personel + çalışma dönemleri, izin kayıtları, tatiller, ayrılanların izin ücreti ödemeleri, ayarlar, kullanıcı hesapları,
işlem günlüğü (kim, ne zaman, ne yaptı) ve salt okunur belgeler (Yöntem Kararları).

Veriler diskte yalnız şifreli durur (personel_takip.vt; biçim ve anahtarlar guvenlik.py'de). Program dosyayı kullanıcının parolasıyla
çözer ve SQLite veritabanını bellekte açar; diske düz metin yazılmaz. Her değişiklik tek bir işlemde (transaction) yapılır, günlüğe
yazılır ve işlem biter bitmez dosya yeniden şifrelenip yerine konur. Tarihler ISO metni (YYYY-MM-DD) olarak saklanır.
Program her gün ilk açılışta şifreli bir yedek alır (yedekler/ klasörü, son 60 gün).
"""
import contextlib
import datetime
import getpass
import json
import os
import re
import sqlite3

from . import guvenlik
from .yardimci import D, VeriHatasi, iso_oku, tarih_iso, tarih_yaz, KOD_AD

SEMA_SURUM = 2
SEMA = """
CREATE TABLE IF NOT EXISTS ayar (anahtar TEXT PRIMARY KEY, deger TEXT);
CREATE TABLE IF NOT EXISTS personel (
    id INTEGER PRIMARY KEY,
    ad TEXT NOT NULL,
    dogum TEXT,
    yas50 TEXT,
    elle_duzeltme REAL,
    duzeltme_aciklama TEXT,
    teyit TEXT,
    onceki_ad TEXT,
    not_ozet TEXT,
    not_metni TEXT,
    olusturma TEXT,
    guncelleme TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS personel_ad ON personel(ad);
CREATE TABLE IF NOT EXISTS donem (
    id INTEGER PRIMARY KEY,
    personel_id INTEGER NOT NULL REFERENCES personel(id) ON DELETE CASCADE,
    giris TEXT NOT NULL,
    cikis TEXT
);
CREATE INDEX IF NOT EXISTS donem_p ON donem(personel_id);
CREATE TABLE IF NOT EXISTS izin (
    id INTEGER PRIMARY KEY,
    no INTEGER NOT NULL UNIQUE,
    personel_id INTEGER NOT NULL REFERENCES personel(id),
    tur TEXT NOT NULL CHECK (tur IN ('Kİ', 'RP', 'MZ', 'ÜZ', 'İD')),
    baslangic TEXT,
    bitis TEXT,
    aciklama TEXT,
    giren TEXT,
    yazildigi TEXT,
    iptal INTEGER NOT NULL DEFAULT 0,
    guncelleme TEXT
);
CREATE INDEX IF NOT EXISTS izin_p ON izin(personel_id);
CREATE TABLE IF NOT EXISTS tatil (
    id INTEGER PRIMARY KEY,
    tarih TEXT NOT NULL UNIQUE,
    ad TEXT,
    tur TEXT NOT NULL CHECK (tur IN ('tam', 'yarim'))
);
CREATE TABLE IF NOT EXISTS odeme (
    personel_id INTEGER PRIMARY KEY REFERENCES personel(id) ON DELETE CASCADE,
    ucret REAL,
    odendi TEXT,
    odeme_tarihi TEXT,
    odenen REAL,
    aciklama TEXT
);
CREATE TABLE IF NOT EXISTS gunluk (
    id INTEGER PRIMARY KEY,
    zaman TEXT NOT NULL,
    kullanici TEXT,
    islem TEXT NOT NULL,
    ayrinti TEXT
);
CREATE TABLE IF NOT EXISTS belge (anahtar TEXT PRIMARY KEY, icerik TEXT);
CREATE TABLE IF NOT EXISTS kullanici (
    id INTEGER PRIMARY KEY,
    kullanici_adi TEXT NOT NULL UNIQUE,
    ad_soyad TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('yonetici', 'kullanici')),
    parola_degismeli INTEGER NOT NULL DEFAULT 0,
    olusturma TEXT,
    son_giris TEXT
);
"""

VARSAYILAN_AYAR = {'sirket': 'Şirket', 'hesap_tarihi': '', 'kilit_dakika': '10'}
ROLLER = {'yonetici': 'Yönetici', 'kullanici': 'Kullanıcı'}
YEDEK_ON = 'personel_takip_'
KULLANICI_SUTUN = ('id', 'kullanici_adi', 'ad_soyad', 'rol', 'parola_degismeli', 'olusturma', 'son_giris')
_IZINLI_ISARET = " .'’-"


def simdi():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def varsayilan_kullanici():
    try:
        return getpass.getuser()
    except Exception:  # pragma: no cover
        return 'İK'


def _ad_soyad_kontrol(s, alan='Ad Soyad'):
    s = ' '.join((s or '').split())
    if not s:
        raise VeriHatasi(f'{alan} boş olamaz.')
    if len(s) > 80 or any(not (c.isalpha() or c in _IZINLI_ISARET) for c in s):
        raise VeriHatasi(f'{alan} yalnız harf, boşluk, nokta, kesme işareti ve tire içerebilir.')
    return s


def _bellek(govde=None):
    """Bellekte SQLite veritabanı; govde (SQL dökümü) verilirse onunla doldurulur. Şema eksikse tamamlanır."""
    db = sqlite3.connect(':memory:')
    db.row_factory = sqlite3.Row
    if govde:
        try:
            db.executescript(govde.decode('utf-8') if isinstance(govde, bytes) else govde)
        except sqlite3.DatabaseError as e:
            db.close()
            raise VeriHatasi(f'Veri okunamadı: {e}') from None
    db.execute('PRAGMA foreign_keys = ON')
    db.executescript(SEMA)
    with db:
        db.execute("INSERT OR REPLACE INTO ayar VALUES ('sema_surum', ?)", (str(SEMA_SURUM),))
    return db


class YedekAnahtariGerekli(VeriHatasi):
    """Seçilen yedek başka bir kurulumun anahtarıyla şifrelenmiş: o yedeğin kullanıcı adı + parolası ya da kurtarma anahtarı gerekir."""


class Veritabani:
    """Şifreli veri dosyasının bellekte açılmış hâli. Açmak için Veritabani.ac / olustur / kurtarma_ile_ac."""

    def __init__(self, yol, kasa, govde=None):
        self.yol = yol
        self.kasa = kasa
        self.oturum = None   # giriş yapan kullanıcı (kullanici tablosunun satırı)
        self.yedek_klasoru = os.path.join(os.path.dirname(os.path.abspath(yol)), 'yedekler')
        self.db = _bellek(govde)
        self._onbellek = None

    # ------------------------------------------------------------------ açma / kaydetme
    @classmethod
    def olustur(cls, yol, kullanici_adi, ad_soyad, parola, govde=None):
        """Yeni şifreli veri dosyası ve ilk (yönetici) hesap. govde: dışarıdan verilen SQL dökümü (sınamalar). Dönüş: (db, kurtarma anahtarı)."""
        if os.path.exists(yol):
            raise VeriHatasi(f'Veri dosyası zaten var: {yol}')
        ad = guvenlik.kullanici_adi_kontrol(kullanici_adi)
        ad_soyad = _ad_soyad_kontrol(ad_soyad)
        guvenlik.parola_kontrol(parola, ad)
        os.makedirs(os.path.dirname(os.path.abspath(yol)), exist_ok=True)
        kasa, kurtarma = guvenlik.Kasa.yeni(ad, parola)
        db = cls(yol, kasa, govde)
        with db._yaz():
            db.db.execute('DELETE FROM kullanici')
            db.db.execute('INSERT INTO kullanici (kullanici_adi, ad_soyad, rol, olusturma) VALUES (?, ?, ?, ?)',
                          (ad, ad_soyad, 'yonetici', simdi()))
            db.db.execute("INSERT INTO gunluk (zaman, kullanici, islem, ayrinti) VALUES (?, ?, 'Şifreli veri dosyası oluşturuldu', ?)",
                          (simdi(), ad_soyad, f'yönetici hesabı: {ad}'))
        db.oturum_ac(ad)
        return db, kurtarma

    @classmethod
    def ac(cls, yol, kullanici_adi, parola, hatali=None):
        """Kullanıcı adı + parolayla açar ve oturumu başlatır. Hatalıysa guvenlik.ParolaHatasi; dosya bozuksa guvenlik.DosyaHatasi.
        hatali: GirisSayaci.basari() çıktısı (işlem geçmişine yazılır)."""
        kasa, govde = guvenlik.dosya_ac(guvenlik.oku(yol), kullanici_adi=kullanici_adi, parola=parola)
        db = cls(yol, kasa, govde)
        db.oturum_ac(kullanici_adi, hatali)
        return db

    @classmethod
    def kurtarma_ile_ac(cls, yol, anahtar):
        """Kurtarma anahtarıyla açar (oturum yok); ardından parola_kurtar + oturum_ac."""
        kasa, govde = guvenlik.dosya_ac(guvenlik.oku(yol), kurtarma=anahtar)
        return cls(yol, kasa, govde)

    def oturum_ac(self, kullanici_adi, hatali=None):
        ad = guvenlik.kullanici_adi_normal(kullanici_adi)
        r = self.db.execute('SELECT * FROM kullanici WHERE kullanici_adi = ?', (ad,)).fetchone()
        if r is None or not self.kasa.kullanici_var(ad):
            raise guvenlik.ParolaHatasi(guvenlik.HATALI_GIRIS)
        self.oturum = dict(r)
        self.oturum['onceki_giris'] = r['son_giris']
        with self._yaz():
            self.db.execute('UPDATE kullanici SET son_giris = ? WHERE id = ?', (simdi(), r['id']))
            self._gunluk('Giriş', f'{ad} ({ROLLER[r["rol"]]})')
            self._hatali_yaz(hatali)

    def _hatali_yaz(self, hatali):
        if hatali and hatali[0]:
            self._gunluk('Hatalı giriş denemesi', f'son başarılı girişten bu yana {hatali[0]} hatalı deneme; sonuncusu '
                                                  f'{datetime.datetime.fromtimestamp(hatali[1]):%d.%m.%Y %H:%M}')

    def hatali_denemeleri_yaz(self, hatali):
        """Kilit ekranında açılınca: o ana kadarki hatalı denemeler işlem geçmişine."""
        if hatali and hatali[0]:
            with self._yaz():
                self._hatali_yaz(hatali)

    @contextlib.contextmanager
    def _yaz(self):
        """Tek işlem: hata olursa geri alınır; başarılıysa dosya yeniden şifrelenip yazılır."""
        with self.db:
            yield
        self._onbellek = None
        self.kaydet()

    def _govde(self):
        return '\n'.join(self.db.iterdump()).encode('utf-8')

    def kaydet(self):
        guvenlik.guvenli_yaz(self.yol, guvenlik.paketle(self.kasa, self._govde()))

    def kapat(self):
        self.db.close()
        self.kasa = None

    # ------------------------------------------------------------------ ayarlar
    def ayar(self, anahtar):
        r = self.db.execute('SELECT deger FROM ayar WHERE anahtar = ?', (anahtar,)).fetchone()
        if r is None:
            return VARSAYILAN_AYAR.get(anahtar, '')
        return r['deger']

    def ayar_yaz(self, anahtar, deger, gunluk=True):
        eski = self.ayar(anahtar)
        if str(eski or '') == str(deger or ''):
            return
        with self._yaz():
            self.db.execute('INSERT OR REPLACE INTO ayar VALUES (?, ?)', (anahtar, deger))
            if gunluk:
                self._gunluk('Ayar değişti', f'{anahtar}: {eski or "(boş)"} → {deger or "(boş)"}')

    def kullanici(self):
        """İzin kayıtlarına "Giren", işlem geçmişine "Kullanıcı" olarak yazılan ad: giriş yapan kişinin Ad Soyad'ı."""
        return self.oturum['ad_soyad'] if self.oturum else varsayilan_kullanici()

    def yonetici_mi(self):
        return self.oturum is None or self.oturum['rol'] == 'yonetici'

    def _yetki(self):
        if not self.yonetici_mi():
            raise VeriHatasi('Bu işlem için yönetici yetkisi gerekir.')

    def hesap_tarihi(self):
        """Ayarlarda elle tarih varsa o, yoksa bugün. (tarih, elle_mi)"""
        if getattr(self, 'tarih_ust', None):  # yalnız komut satırı (--tarih; doğrulama), kaydedilmez
            return self.tarih_ust, False
        s = self.ayar('hesap_tarihi')
        if s:
            try:
                return D.fromisoformat(s), True
            except ValueError:
                pass
        return D.today(), False

    def bos_mu(self):
        return self.db.execute('SELECT COUNT(*) FROM personel').fetchone()[0] == 0

    # ------------------------------------------------------------------ günlük
    def _gunluk(self, islem, ayrinti='', kullanici=None):
        self.db.execute('INSERT INTO gunluk (zaman, kullanici, islem, ayrinti) VALUES (?, ?, ?, ?)',
                        (simdi(), kullanici or self.kullanici(), islem, ayrinti))
        self._onbellek = None

    def gunluk_listesi(self, limit=500):
        return [dict(r) for r in self.db.execute('SELECT * FROM gunluk ORDER BY id DESC LIMIT ?', (limit,))]

    # ------------------------------------------------------------------ okuma (motor biçimi)
    def veri(self):
        """motor.py girdisi: {'personel', 'izinler', 'tatiller', 'odemeler'} (önbellekli; her yazmada sıfırlanır)."""
        if self._onbellek is not None:
            return self._onbellek
        donem = {}
        for r in self.db.execute('SELECT * FROM donem ORDER BY personel_id, giris'):
            donem.setdefault(r['personel_id'], []).append((iso_oku(r['giris']), iso_oku(r['cikis'])))
        personel = []
        for r in self.db.execute('SELECT * FROM personel ORDER BY id'):
            p = dict(r)
            p['dogum'] = iso_oku(p['dogum'])
            p['yas50'] = iso_oku(p['yas50'])
            p['donemler'] = donem.get(p['id'], [])
            personel.append(p)
        izinler = []
        for r in self.db.execute('SELECT * FROM izin ORDER BY no'):
            k = dict(r)
            k['bas'] = iso_oku(k.pop('baslangic'))
            k['bit'] = iso_oku(k.pop('bitis'))
            k['yazildigi'] = iso_oku(k['yazildigi'])
            k['iptal'] = bool(k['iptal'])
            izinler.append(k)
        tatiller = [{'id': r['id'], 'tarih': iso_oku(r['tarih']), 'ad': r['ad'], 'tur': r['tur']}
                    for r in self.db.execute('SELECT * FROM tatil ORDER BY tarih')]
        odemeler = {}
        for r in self.db.execute('SELECT * FROM odeme'):
            o = dict(r)
            o['odeme_tarihi'] = iso_oku(o['odeme_tarihi'])
            odemeler[o['personel_id']] = o
        self._onbellek = {'personel': personel, 'izinler': izinler, 'tatiller': tatiller, 'odemeler': odemeler}
        return self._onbellek

    def personel_adi(self, pid):
        r = self.db.execute('SELECT ad FROM personel WHERE id = ?', (pid,)).fetchone()
        return r['ad'] if r else '?'

    # ------------------------------------------------------------------ personel
    @staticmethod
    def _donem_kontrol(donemler):
        don = sorted(donemler, key=lambda x: x[0])
        if not don:
            raise VeriHatasi('En az bir işe giriş tarihi yazın.')
        for i, (g, c) in enumerate(don):
            if g is None:
                raise VeriHatasi('Her çalışma döneminin giriş tarihi olmalı.')
            if c is not None and c < g:
                raise VeriHatasi(f'{i + 1}. dönemde çıkış tarihi ({tarih_yaz(c)}) girişten ({tarih_yaz(g)}) önce.')
            if i + 1 < len(don):
                if c is None:
                    raise VeriHatasi(f'{i + 1}. dönemin çıkış tarihi yok; ancak son dönemin çıkışı boş kalabilir.')
                if don[i + 1][0] <= c:
                    raise VeriHatasi(f'{i + 2}. dönemin girişi ({tarih_yaz(don[i + 1][0])}) önceki çıkıştan ({tarih_yaz(c)}) sonra olmalı.')
        return don

    def _ad_kontrol(self, ad, pid):
        ad = _ad_soyad_kontrol(ad)
        r = self.db.execute('SELECT id FROM personel WHERE ad = ? COLLATE NOCASE AND id IS NOT ?', (ad, pid)).fetchone()
        if r:
            raise VeriHatasi(f'"{ad}" adlı başka bir personel var.')
        return ad

    def personel_kaydet(self, p, pid=None, gunluk=True):
        """p: {'ad', 'dogum', 'yas50', 'donemler', 'elle_duzeltme', 'duzeltme_aciklama', 'teyit', 'onceki_ad', 'not_ozet', 'not_metni'}.
        pid None ise yeni kişi. Dönüş: id."""
        ad = self._ad_kontrol(p.get('ad'), pid)
        don = self._donem_kontrol(p.get('donemler') or [])
        alanlar = {'ad': ad, 'dogum': tarih_iso(p.get('dogum')), 'yas50': tarih_iso(p.get('yas50')),
                   'elle_duzeltme': p.get('elle_duzeltme') or None, 'duzeltme_aciklama': p.get('duzeltme_aciklama') or None,
                   'teyit': p.get('teyit') or None, 'onceki_ad': p.get('onceki_ad') or None, 'not_ozet': p.get('not_ozet') or None,
                   'not_metni': p.get('not_metni') or None}
        with self._yaz():
            if pid is None:
                cur = self.db.execute(
                    'INSERT INTO personel (ad, dogum, yas50, elle_duzeltme, duzeltme_aciklama, teyit, onceki_ad, not_ozet, not_metni, '
                    'olusturma, guncelleme) VALUES (:ad, :dogum, :yas50, :elle_duzeltme, :duzeltme_aciklama, :teyit, :onceki_ad, '
                    ':not_ozet, :not_metni, :zaman, :zaman)', dict(alanlar, zaman=simdi()))
                pid = cur.lastrowid
                if gunluk:
                    self._gunluk('Personel eklendi', ad)
            else:
                eski = dict(self.db.execute('SELECT * FROM personel WHERE id = ?', (pid,)).fetchone())
                eski_don = [(r['giris'], r['cikis']) for r in self.db.execute('SELECT * FROM donem WHERE personel_id = ? ORDER BY giris', (pid,))]
                self.db.execute(
                    'UPDATE personel SET ad = :ad, dogum = :dogum, yas50 = :yas50, elle_duzeltme = :elle_duzeltme, '
                    'duzeltme_aciklama = :duzeltme_aciklama, teyit = :teyit, onceki_ad = :onceki_ad, not_ozet = :not_ozet, '
                    'not_metni = :not_metni, guncelleme = :zaman WHERE id = :id', dict(alanlar, zaman=simdi(), id=pid))
                if gunluk:
                    deg = [k for k, v in alanlar.items() if (eski.get(k) or None) != (v or None)]
                    yeni_don = [(tarih_iso(g), tarih_iso(c)) for g, c in don]
                    if yeni_don != eski_don:
                        deg.append('çalışma dönemleri')
                    if deg:
                        self._gunluk('Personel düzenlendi', f'{ad}: ' + ', '.join(deg))
            self.db.execute('DELETE FROM donem WHERE personel_id = ?', (pid,))
            for g, c in don:
                self.db.execute('INSERT INTO donem (personel_id, giris, cikis) VALUES (?, ?, ?)', (pid, tarih_iso(g), tarih_iso(c)))
        self._onbellek = None
        return pid

    def personel_sil(self, pid):
        n = self.db.execute('SELECT COUNT(*) FROM izin WHERE personel_id = ?', (pid,)).fetchone()[0]
        if n:
            raise VeriHatasi(f'Bu kişinin {n} izin kaydı var; silinemez. İşten ayrıldıysa çıkış tarihini yazın (kişi "Ayrıldı" olur, '
                             f'kayıtları ve ödenecek izin ücreti korunur).')
        ad = self.personel_adi(pid)
        with self._yaz():
            self.db.execute('DELETE FROM personel WHERE id = ?', (pid,))
            self._gunluk('Personel silindi', ad)

    # ------------------------------------------------------------------ izin kayıtları
    def sonraki_no(self):
        return (self.db.execute('SELECT MAX(no) FROM izin').fetchone()[0] or 0) + 1

    @staticmethod
    def _izin_kontrol(k):
        if k.get('tur') not in KOD_AD:
            raise VeriHatasi('İzin türünü seçin.')
        if not k.get('personel_id'):
            raise VeriHatasi('Personeli seçin.')
        bas, bit = k.get('bas'), k.get('bit')
        if bas is None:
            raise VeriHatasi('Başlangıç tarihini yazın.')
        if bit is not None and bit < bas:
            raise VeriHatasi('Bitiş tarihi başlangıçtan önce olamaz.')

    def izin_kaydet(self, k, kid=None, gunluk=True):
        """k: {'personel_id', 'tur', 'bas', 'bit' (None/bas = tek gün), 'aciklama', 'giren', 'yazildigi', 'iptal', 'no'}. Dönüş: id."""
        self._izin_kontrol(k)
        bit = k.get('bit')
        if bit == k['bas']:
            bit = None
        alan = {'personel_id': k['personel_id'], 'tur': k['tur'], 'baslangic': tarih_iso(k['bas']), 'bitis': tarih_iso(bit),
                'aciklama': k.get('aciklama') or None, 'iptal': int(bool(k.get('iptal'))), 'zaman': simdi()}
        ozet = f'{self.personel_adi(k["personel_id"])} · {KOD_AD[k["tur"]]} · {tarih_yaz(k["bas"])}' + (f'–{tarih_yaz(bit)}' if bit else '')
        with self._yaz():
            if kid is None:
                alan.update({'no': k.get('no') or self.sonraki_no(), 'giren': k.get('giren') or self.kullanici(),
                             'yazildigi': tarih_iso(k.get('yazildigi') or D.today())})
                cur = self.db.execute(
                    'INSERT INTO izin (no, personel_id, tur, baslangic, bitis, aciklama, giren, yazildigi, iptal, guncelleme) '
                    'VALUES (:no, :personel_id, :tur, :baslangic, :bitis, :aciklama, :giren, :yazildigi, :iptal, :zaman)', alan)
                kid = cur.lastrowid
                if gunluk:
                    self._gunluk('İzin eklendi', f'No {alan["no"]}: {ozet}')
            else:
                no = self.db.execute('SELECT no FROM izin WHERE id = ?', (kid,)).fetchone()['no']
                self.db.execute(
                    'UPDATE izin SET personel_id = :personel_id, tur = :tur, baslangic = :baslangic, bitis = :bitis, '
                    'aciklama = :aciklama, iptal = :iptal, guncelleme = :zaman WHERE id = :id', dict(alan, id=kid))
                if gunluk:
                    self._gunluk('İzin düzenlendi', f'No {no}: {ozet}')
        self._onbellek = None
        return kid

    def izin_iptal(self, kid, iptal=True):
        r = self.db.execute('SELECT no FROM izin WHERE id = ?', (kid,)).fetchone()
        with self._yaz():
            self.db.execute('UPDATE izin SET iptal = ?, guncelleme = ? WHERE id = ?', (int(iptal), simdi(), kid))
            self._gunluk('İzin iptal edildi' if iptal else 'İzin iptali geri alındı', f'No {r["no"]}')

    def izin_sil(self, kid):
        r = self.db.execute('SELECT * FROM izin WHERE id = ?', (kid,)).fetchone()
        with self._yaz():
            self.db.execute('DELETE FROM izin WHERE id = ?', (kid,))
            self._gunluk('İzin silindi', f'No {r["no"]}: {self.personel_adi(r["personel_id"])} · {KOD_AD.get(r["tur"], r["tur"])} · '
                                         f'{r["baslangic"] or ""}{("–" + r["bitis"]) if r["bitis"] else ""}')

    # ------------------------------------------------------------------ tatiller
    def tatil_kaydet(self, t, tid=None):
        if not t.get('tarih'):
            raise VeriHatasi('Tatil tarihini yazın.')
        if t.get('tur') not in ('tam', 'yarim'):
            raise VeriHatasi('Tatil türünü seçin (tam gün / yarım gün).')
        r = self.db.execute('SELECT id FROM tatil WHERE tarih = ? AND id IS NOT ?', (tarih_iso(t['tarih']), tid)).fetchone()
        if r:
            raise VeriHatasi(f'{tarih_yaz(t["tarih"])} için zaten bir tatil kaydı var.')
        with self._yaz():
            if tid is None:
                self.db.execute('INSERT INTO tatil (tarih, ad, tur) VALUES (?, ?, ?)', (tarih_iso(t['tarih']), t.get('ad') or '', t['tur']))
                self._gunluk('Tatil eklendi', f'{tarih_yaz(t["tarih"])} {t.get("ad") or ""} ({t["tur"]})')
            else:
                self.db.execute('UPDATE tatil SET tarih = ?, ad = ?, tur = ? WHERE id = ?', (tarih_iso(t['tarih']), t.get('ad') or '', t['tur'], tid))
                self._gunluk('Tatil düzenlendi', f'{tarih_yaz(t["tarih"])} {t.get("ad") or ""} ({t["tur"]})')

    def tatil_sil(self, tid):
        r = self.db.execute('SELECT * FROM tatil WHERE id = ?', (tid,)).fetchone()
        with self._yaz():
            self.db.execute('DELETE FROM tatil WHERE id = ?', (tid,))
            self._gunluk('Tatil silindi', f'{r["tarih"]} {r["ad"]}')

    # ------------------------------------------------------------------ ayrılan ödemeleri
    def odeme_kaydet(self, pid, o):
        with self._yaz():
            self.db.execute('INSERT OR REPLACE INTO odeme (personel_id, ucret, odendi, odeme_tarihi, odenen, aciklama) VALUES (?, ?, ?, ?, ?, ?)',
                            (pid, o.get('ucret'), o.get('odendi'), tarih_iso(o.get('odeme_tarihi')), o.get('odenen'), o.get('aciklama')))
            self._gunluk('İzin ücreti bilgisi', f'{self.personel_adi(pid)}: ' + ', '.join(
                f'{k}={v}' for k, v in (('ücret', o.get('ucret')), ('durum', o.get('odendi')),
                                        ('tarih', tarih_yaz(o.get('odeme_tarihi'))), ('ödenen', o.get('odenen'))) if v))

    # ------------------------------------------------------------------ belgeler
    def belge(self, anahtar):
        r = self.db.execute('SELECT icerik FROM belge WHERE anahtar = ?', (anahtar,)).fetchone()
        return json.loads(r['icerik']) if r and r['icerik'] else None

    # ------------------------------------------------------------------ toplu veri yükleme (örnek veri, resmî tatiller)
    def veri_yukle(self, v, kaynak):
        """ornek_veri.uret çıktısını BOŞ veritabanına yazar (tek işlem)."""
        self._yetki()
        if not self.bos_mu():
            raise VeriHatasi('Veritabanında kayıt var; örnek veri yalnız boş veritabanına yüklenir.')
        eslem = {}
        with self._yaz():
            for p in v['personel']:
                don = sorted(p['donemler'], key=lambda x: x[0])
                cur = self.db.execute(
                    'INSERT INTO personel (ad, dogum, yas50, elle_duzeltme, duzeltme_aciklama, teyit, onceki_ad, not_ozet, not_metni, '
                    'olusturma, guncelleme) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (p['ad'], tarih_iso(p['dogum']), tarih_iso(p.get('yas50')), p.get('elle_duzeltme'), p.get('duzeltme_aciklama'),
                     p.get('teyit'), p.get('onceki_ad'), p.get('not_ozet'), p.get('not_metni'), simdi(), simdi()))
                eslem[p['id']] = cur.lastrowid
                for g, c in don:
                    self.db.execute('INSERT INTO donem (personel_id, giris, cikis) VALUES (?, ?, ?)', (cur.lastrowid, tarih_iso(g), tarih_iso(c)))
            for k in v['izinler']:
                self.db.execute(
                    'INSERT INTO izin (no, personel_id, tur, baslangic, bitis, aciklama, giren, yazildigi, iptal, guncelleme) '
                    'VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (k['no'], eslem[k['personel_id']], k['tur'], tarih_iso(k['bas']), tarih_iso(k.get('bit')), k.get('aciklama'), k.get('giren'),
                     tarih_iso(k.get('yazildigi')), int(k.get('iptal', False)), simdi()))
            for t in v['tatiller']:
                self.db.execute('INSERT INTO tatil (tarih, ad, tur) VALUES (?, ?, ?)', (tarih_iso(t['tarih']), t['ad'], t['tur']))
            for o in v.get('odemeler', []):
                self.db.execute('INSERT INTO odeme (personel_id, ucret, odendi, odeme_tarihi, odenen) VALUES (?, ?, ?, ?, ?)',
                                (eslem[o['personel_id']], o['ucret'], o['odendi'], tarih_iso(o.get('odeme_tarihi')), o.get('odenen')))
            if v.get('ayar', {}).get('sirket'):
                self.db.execute("INSERT OR REPLACE INTO ayar VALUES ('sirket', ?)", (v['ayar']['sirket'],))
            self._gunluk('Veri yüklendi', f'{kaynak}: {len(v["personel"])} personel, {len(v["izinler"])} izin kaydı, {len(v["tatiller"])} tatil')
        self._onbellek = None

    # ------------------------------------------------------------------ kullanıcı hesapları
    def kullanicilar(self):
        return [dict(r) for r in self.db.execute('SELECT * FROM kullanici ORDER BY kullanici_adi')]

    def _hesap(self, kid):
        r = self.db.execute('SELECT * FROM kullanici WHERE id = ?', (kid,)).fetchone()
        if r is None:
            raise VeriHatasi('Kullanıcı bulunamadı.')
        return dict(r)

    def _son_yonetici(self, kid):
        return not self.db.execute("SELECT COUNT(*) FROM kullanici WHERE rol = 'yonetici' AND id != ?", (kid,)).fetchone()[0]

    def kullanici_ekle(self, kullanici_adi, ad_soyad, rol, parola):
        """Yönetici yeni hesap açar; kullanıcı ilk girişte parolasını değiştirmek zorundadır. Dönüş: id."""
        self._yetki()
        ad = guvenlik.kullanici_adi_kontrol(kullanici_adi)
        ad_soyad = _ad_soyad_kontrol(ad_soyad)
        if rol not in ROLLER:
            raise VeriHatasi('Rolü seçin.')
        if self.db.execute('SELECT 1 FROM kullanici WHERE kullanici_adi = ?', (ad,)).fetchone():
            raise VeriHatasi(f'"{ad}" kullanıcı adı zaten var.')
        guvenlik.parola_kontrol(parola, ad)
        self.kasa.parola_ayarla(ad, parola)
        try:
            with self._yaz():
                cur = self.db.execute('INSERT INTO kullanici (kullanici_adi, ad_soyad, rol, parola_degismeli, olusturma) VALUES (?, ?, ?, 1, ?)',
                                      (ad, ad_soyad, rol, simdi()))
                self._gunluk('Kullanıcı eklendi', f'{ad} ({ad_soyad}, {ROLLER[rol]})')
        except Exception:
            self.kasa.kullanici_sil(ad)
            raise
        return cur.lastrowid

    def kullanici_duzenle(self, kid, ad_soyad, rol):
        self._yetki()
        r = self._hesap(kid)
        ad_soyad = _ad_soyad_kontrol(ad_soyad)
        if rol not in ROLLER:
            raise VeriHatasi('Rolü seçin.')
        if r['rol'] == 'yonetici' and rol != 'yonetici' and self._son_yonetici(kid):
            raise VeriHatasi('En az bir yönetici hesabı kalmalı.')
        with self._yaz():
            self.db.execute('UPDATE kullanici SET ad_soyad = ?, rol = ? WHERE id = ?', (ad_soyad, rol, kid))
            self._gunluk('Kullanıcı düzenlendi', f'{r["kullanici_adi"]}: {ad_soyad}, {ROLLER[rol]}')
        if self.oturum and self.oturum['id'] == kid:
            self.oturum.update(ad_soyad=ad_soyad, rol=rol)

    def kullanici_sil(self, kid):
        """Hesap silinir ve anahtarı dosyadan da yedeklerden de çıkarılır (o kullanıcı artık hiçbir dosyayı açamaz)."""
        self._yetki()
        r = self._hesap(kid)
        if self.oturum and self.oturum['id'] == kid:
            raise VeriHatasi('Kendi hesabınızı silemezsiniz.')
        if r['rol'] == 'yonetici' and self._son_yonetici(kid):
            raise VeriHatasi('En az bir yönetici hesabı kalmalı.')
        self.kasa.kullanici_sil(r['kullanici_adi'])
        with self._yaz():
            self.db.execute('DELETE FROM kullanici WHERE id = ?', (kid,))
            self._gunluk('Kullanıcı silindi', f'{r["kullanici_adi"]} ({r["ad_soyad"]})')
        self.yedekleri_yenile()

    def parola_sifirla(self, kid, gecici_parola):
        """Yönetici bir kullanıcının parolasını geçici bir parolayla değiştirir; ilk girişte değiştirmesi istenir."""
        self._yetki()
        r = self._hesap(kid)
        guvenlik.parola_kontrol(gecici_parola, r['kullanici_adi'])
        self.kasa.parola_ayarla(r['kullanici_adi'], gecici_parola)
        with self._yaz():
            self.db.execute('UPDATE kullanici SET parola_degismeli = 1 WHERE id = ?', (kid,))
            self._gunluk('Parola sıfırlandı', r['kullanici_adi'])
        self.yedekleri_yenile()

    def parola_dogru(self, parola):
        """Oturumdaki kullanıcının parolası mı (kilit ekranı)?"""
        return bool(self.oturum) and self.kasa.parola_dogru(self.oturum['kullanici_adi'], parola)

    def parola_degistir(self, eski, yeni):
        """Oturumdaki kullanıcının parolası. Eski parolalar yedekleri de açamaz (yedekler yeni anahtarla yeniden yazılır)."""
        ad = self.oturum['kullanici_adi']
        if not self.kasa.parola_dogru(ad, eski):
            raise guvenlik.ParolaHatasi('Mevcut parola hatalı.')
        guvenlik.parola_kontrol(yeni, ad)
        if guvenlik.parola_normal(yeni) == guvenlik.parola_normal(eski):
            raise VeriHatasi('Yeni parola eskisiyle aynı olamaz.')
        self.kasa.parola_ayarla(ad, yeni)
        with self._yaz():
            self.db.execute('UPDATE kullanici SET parola_degismeli = 0 WHERE id = ?', (self.oturum['id'],))
            self._gunluk('Parola değiştirildi', ad)
        self.oturum['parola_degismeli'] = 0
        self.yedekleri_yenile()

    def parola_kurtar(self, kullanici_adi, yeni):
        """Kurtarma anahtarıyla açılmış dosyada bir hesabın parolasını yeniler (ardından oturum_ac)."""
        ad = guvenlik.kullanici_adi_normal(kullanici_adi)
        r = self.db.execute('SELECT * FROM kullanici WHERE kullanici_adi = ?', (ad,)).fetchone()
        if r is None:
            raise VeriHatasi(f'"{ad}" adlı kullanıcı yok.')
        guvenlik.parola_kontrol(yeni, ad)
        self.kasa.parola_ayarla(ad, yeni)
        with self._yaz():
            self.db.execute('UPDATE kullanici SET parola_degismeli = 0 WHERE id = ?', (r['id'],))
            self._gunluk('Parola kurtarma anahtarıyla yenilendi', ad, kullanici=r['ad_soyad'])
        self.yedekleri_yenile()

    def kurtarma_yenile(self):
        """Yeni kurtarma anahtarı (eskisi geçersiz olur; yedekler de yeni anahtarla yazılır). Dönüş: yeni anahtar."""
        self._yetki()
        anahtar = self.kasa.kurtarma_yenile()
        with self._yaz():
            self._gunluk('Kurtarma anahtarı yenilendi', 'eski anahtar geçersiz')
        self.yedekleri_yenile()
        return anahtar

    # ------------------------------------------------------------------ yedek
    def yedekle(self, hedef):
        os.makedirs(os.path.dirname(os.path.abspath(hedef)), exist_ok=True)
        return guvenlik.guvenli_yaz(hedef, guvenlik.paketle(self.kasa, self._govde()))

    def gunluk_yedek(self, klasor=None, sakla=60):
        """Bugünün yedeği yoksa alır; en eski yedekleri siler (son `sakla` dosya kalır). Alınan yedeğin yolu ya da None."""
        klasor = klasor or self.yedek_klasoru
        os.makedirs(klasor, exist_ok=True)
        yol = os.path.join(klasor, f'{YEDEK_ON}{D.today():%Y-%m-%d}.vt')
        alindi = None
        if not os.path.exists(yol) and not self.bos_mu():
            alindi = self.yedekle(yol)
        eski = sorted(f for f in os.listdir(klasor) if re.fullmatch(YEDEK_ON + r'\d{4}-\d{2}-\d{2}\.vt', f))
        for f in eski[:-sakla]:
            try:
                os.remove(os.path.join(klasor, f))
            except OSError:
                pass
        return alindi

    def yedekleri_yenile(self):
        """Anahtarlar değişince (parola, kullanıcı silme, kurtarma anahtarı) yedekler yeni başlıkla yeniden şifrelenir: silinen kullanıcı
        ya da eski parola eski yedekleri de açamaz. Başka bir kurulumun yedeklerine dokunulmaz. Dönüş: yenilenen yedek sayısı."""
        try:
            adlar = os.listdir(self.yedek_klasoru)
        except OSError:
            return 0
        n = 0
        for f in adlar:
            yol = os.path.join(self.yedek_klasoru, f)
            if not f.endswith('.vt'):
                continue
            try:
                st = os.stat(yol)
                govde = guvenlik.govde_coz(guvenlik.oku(yol), self.kasa.dek)
            except (OSError, VeriHatasi):
                continue
            guvenlik.guvenli_yaz(yol, guvenlik.paketle(self.kasa, govde))
            os.utime(yol, (st.st_atime, st.st_mtime))
            n += 1
        return n

    def yedek_oku(self, yol, kullanici_adi=None, parola=None, kurtarma=None):
        """Yedek dosyasının SQL dökümü. Bu kurulumun yedeği doğrudan açılır; başka bir kurulumunki için o yedeğin kullanıcı adı +
        parolası ya da kurtarma anahtarı gerekir (yoksa YedekAnahtariGerekli)."""
        veri = guvenlik.oku(yol)
        try:
            return guvenlik.govde_coz(veri, self.kasa.dek).decode('utf-8')
        except guvenlik.DosyaHatasi:
            baslik = guvenlik.ayir(veri)[0]
            if baslik.get('tuz') == self.kasa.baslik.get('tuz'):
                raise   # bu kurulumun yedeği ama açılmıyor: bozulmuş ya da değiştirilmiş
            if parola is None and kurtarma is None:
                raise YedekAnahtariGerekli('Bu yedek başka bir kurulumda (başka bir veri dosyasıyla) alınmış. Açmak için o yedeğin '
                                           'kullanıcı adı ve parolası ya da kurtarma anahtarı gerekir.') from None
            return guvenlik.dosya_ac(veri, kullanici_adi, parola, kurtarma)[1].decode('utf-8')

    def yedekten_don(self, yol, **anahtar):
        """Programdaki verileri seçilen yedekteki hâline döndürür (önce şimdiki hâlin yedeği alınır). Kullanıcı hesapları ve kilit
        ayarı bu kurulumun güvenlik ayarıdır: yedektekiler değil, şimdikiler kalır."""
        self._yetki()
        yeni = _bellek(self.yedek_oku(yol, **anahtar))
        tablolar = {r[0] for r in yeni.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if not {'personel', 'izin', 'tatil'} <= tablolar:
            yeni.close()
            raise VeriHatasi('Seçilen dosya bu programın yedeği değil.')
        sutun = ', '.join(KULLANICI_SUTUN)
        hesaplar = [tuple(r) for r in self.db.execute(f'SELECT {sutun} FROM kullanici')]
        with yeni:
            yeni.execute('DELETE FROM kullanici')
            yeni.executemany(f'INSERT INTO kullanici ({sutun}) VALUES ({", ".join("?" * len(KULLANICI_SUTUN))})', hesaplar)
            yeni.execute("INSERT OR REPLACE INTO ayar VALUES ('kilit_dakika', ?)", (self.ayar('kilit_dakika'),))
        self.yedekle(os.path.join(self.yedek_klasoru, f'{YEDEK_ON}geri_donus_oncesi_{datetime.datetime.now():%Y%m%d_%H%M%S}.vt'))
        eski, self.db = self.db, yeni
        eski.close()
        with self._yaz():
            self._gunluk('Yedekten geri dönüldü', os.path.basename(yol))
