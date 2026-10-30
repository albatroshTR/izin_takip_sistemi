# -*- coding: utf-8 -*-
"""
Veri dosyasının şifrelenmesi, kullanıcı parolaları ve kurtarma anahtarı.

Dosya biçimi (personel_takip.vt ve yedekleri):
  SIHIR (5 bayt) | başlık uzunluğu (4 bayt) | başlık (JSON) | nonce (12 bayt) | AES-256-GCM(DEK, zlib(SQL dökümü), aad = SIHIR + başlık)
Başlık şifreli gövdenin doğrulanan parçasıdır: başlıkta ya da gövdede değişen tek bayt dosyayı açılmaz yapar.

Anahtarlar: verinin anahtarı (DEK) rastgele 32 bayttır; dosyada yalnız sarılmış (şifrelenmiş) hâli durur. DEK her kullanıcı için
parolasından scrypt ile türetilen anahtarla, bir kez de kurtarma anahtarıyla ayrı ayrı sarılır. Başlıkta kullanıcı adı yazılmaz
(anahtar kimliği = sha256(dosyanın tuzu + kullanıcı adı)); kullanıcının adı, rolü ve durumu şifreli veritabanındadır.
"""
import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import struct
import time
import unicodedata
import zlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .yardimci import VeriHatasi

SIHIR = b'IZTS\x01'
KDF = {'ad': 'scrypt', 'n': 2 ** 16, 'r': 8, 'p': 1}   # ≈0,3 sn, 64 MB: parola denemelerini pahalı kılar
KURTARMA = 'kurtarma'
HATALI_GIRIS = 'Kullanıcı adı ya da parola hatalı.'


class ParolaHatasi(VeriHatasi):
    """Hatalı kullanıcı adı / parola / kurtarma anahtarı."""


class DosyaHatasi(VeriHatasi):
    """Dosya bu programın veri dosyası değil, bozulmuş ya da değiştirilmiş."""


# ----------------------------------------------------------------------------- kullanıcı adı ve parola kuralları
_TR = str.maketrans('çğıöşü', 'cgiosu')


def kullanici_adi_normal(s):
    """Girişte büyük/küçük harf ve Türkçe karakter farkı gözetilmez: ' Ayşe.Örnek ' → 'ayse.ornek', 'Şükrü' → 'sukru'."""
    s = (s or '').strip().replace('İ', 'i').replace('I', 'ı').lower()
    return unicodedata.normalize('NFC', s).translate(_TR)


def kullanici_adi_kontrol(s):
    ad = kullanici_adi_normal(s)
    if not re.fullmatch(r'[a-z0-9._-]{3,32}', ad):
        raise VeriHatasi('Kullanıcı adı 3–32 karakter olmalı; yalnız harf (Türkçe harfler İngilizce karşılığına çevrilir), rakam, '
                         'nokta, alt çizgi ve tire kullanın. Örnek: ayse.ornek')
    return ad


def parola_normal(p):
    return unicodedata.normalize('NFC', p or '')


def parola_kontrol(parola, kullanici_adi=''):
    p = parola_normal(parola)
    if len(p) < 8:
        raise VeriHatasi('Parola en az 8 karakter olmalı.')
    if not any(c.isalpha() for c in p) or not any(c.isdigit() for c in p):
        raise VeriHatasi('Parolada en az bir harf ve bir rakam olmalı.')
    if kullanici_adi and kullanici_adi_normal(p) == kullanici_adi_normal(kullanici_adi):
        raise VeriHatasi('Parola kullanıcı adıyla aynı olamaz.')
    return p


# ----------------------------------------------------------------------------- kurtarma anahtarı
def kurtarma_uret():
    """20 rastgele bayt (160 bit), 8 gruplu base32: 'K7QM-2XAV-…'."""
    s = base64.b32encode(secrets.token_bytes(20)).decode('ascii')
    return '-'.join(s[i:i + 4] for i in range(0, 32, 4))


def kurtarma_normal(s):
    """Büyük/küçük harf, tire ve boşluk fark etmez; base32'de olmayan 0/1/8 → O/I/B."""
    s = ''.join(c for c in (s or '').upper() if c.isalnum())
    return s.translate(str.maketrans('018', 'OIB'))


# ----------------------------------------------------------------------------- anahtar türetme ve sarma
def _b64(b):
    return base64.b64encode(b).decode('ascii')


def _b64c(s):
    return base64.b64decode(s.encode('ascii'))


def _turet(sir, tuz, kdf):
    if kdf.get('ad') != 'scrypt':
        raise DosyaHatasi('Dosya bu programın tanımadığı bir anahtar türetme yöntemi kullanıyor (daha yeni bir sürümle kaydedilmiş olabilir).')
    return hashlib.scrypt(sir.encode('utf-8'), salt=tuz, n=kdf['n'], r=kdf['r'], p=kdf['p'], maxmem=2 ** 27, dklen=32)


def _sar(anahtar, dek, kimlik):
    n = os.urandom(12)
    return n + AESGCM(anahtar).encrypt(n, dek, kimlik.encode('ascii'))


def _ac(anahtar, sarili, kimlik):
    return AESGCM(anahtar).decrypt(sarili[:12], sarili[12:], kimlik.encode('ascii'))


class Kasa:
    """Çözülmüş veri anahtarı (DEK) ve dosya başlığı (sarılmış anahtarlar). Yalnız bellekte durur."""

    def __init__(self, dek, baslik):
        self.dek = dek
        self.baslik = baslik

    @classmethod
    def yeni(cls, kullanici_adi, parola):
        """Yeni veri anahtarı; ilk kullanıcı ve kurtarma anahtarı eklenir. Dönüş: (kasa, kurtarma anahtarı)."""
        k = cls(secrets.token_bytes(32), {'surum': 1, 'kdf': dict(KDF), 'tuz': _b64(secrets.token_bytes(16)), 'anahtarlar': {}})
        k.parola_ayarla(kullanici_adi, parola)
        return k, k.kurtarma_yenile()

    # anahtar kimlikleri
    def kimlik(self, kullanici_adi):
        return 'k' + hashlib.sha256(_b64c(self.baslik['tuz']) + kullanici_adi_normal(kullanici_adi).encode('utf-8')).hexdigest()[:32]

    def _ekle(self, kimlik, sir):
        tuz = secrets.token_bytes(16)
        anahtar = _turet(sir, tuz, self.baslik['kdf'])
        self.baslik['anahtarlar'][kimlik] = {'tuz': _b64(tuz), 'sarili': _b64(_sar(anahtar, self.dek, kimlik))}

    def parola_ayarla(self, kullanici_adi, parola):
        self._ekle(self.kimlik(kullanici_adi), parola_normal(parola))

    def kullanici_sil(self, kullanici_adi):
        self.baslik['anahtarlar'].pop(self.kimlik(kullanici_adi), None)

    def kullanici_var(self, kullanici_adi):
        return self.kimlik(kullanici_adi) in self.baslik['anahtarlar']

    def kurtarma_yenile(self):
        anahtar = kurtarma_uret()
        self._ekle(KURTARMA, kurtarma_normal(anahtar))
        return anahtar

    def parola_dogru(self, kullanici_adi, parola):
        try:
            dek = anahtar_coz(self.baslik, kullanici_adi=kullanici_adi, parola=parola)
        except ParolaHatasi:
            return False
        return hmac.compare_digest(dek, self.dek)


def anahtar_coz(baslik, kullanici_adi=None, parola=None, kurtarma=None):
    """Başlıktaki sarılmış anahtarı parola ya da kurtarma anahtarıyla çözer (DEK). Hatalıysa ParolaHatasi."""
    kdf = baslik['kdf']
    if kurtarma is not None:
        kimlik, sir, mesaj = KURTARMA, kurtarma_normal(kurtarma), 'Kurtarma anahtarı hatalı.'
    else:
        kimlik = Kasa(None, baslik).kimlik(kullanici_adi or '')
        sir, mesaj = parola_normal(parola), HATALI_GIRIS
    g = baslik['anahtarlar'].get(kimlik)
    if g is None:
        _turet(sir, b'\0' * 16, kdf)   # bilinmeyen kullanıcı adı da aynı süreyi harcar (zamanlamadan ad tahmin edilemesin)
        raise ParolaHatasi(mesaj)
    try:
        return _ac(_turet(sir, _b64c(g['tuz']), kdf), _b64c(g['sarili']), kimlik)
    except InvalidTag:
        raise ParolaHatasi(mesaj) from None


# ----------------------------------------------------------------------------- dosya
def paketle(kasa, govde):
    """Düz metin gövdeyi (bayt) şifreli dosya baytlarına çevirir."""
    bas = json.dumps(kasa.baslik, sort_keys=True, separators=(',', ':')).encode('utf-8')
    n = os.urandom(12)
    return SIHIR + struct.pack('>I', len(bas)) + bas + n + AESGCM(kasa.dek).encrypt(n, zlib.compress(govde, 6), SIHIR + bas)


def ayir(veri):
    """Dosya baytları → (başlık sözlüğü, başlık baytları, nonce, şifreli gövde)."""
    if not veri.startswith(SIHIR) or len(veri) < len(SIHIR) + 4:
        raise DosyaHatasi('Bu dosya programın veri dosyası değil.')
    i = len(SIHIR)
    (n,) = struct.unpack('>I', veri[i:i + 4])
    bas = veri[i + 4:i + 4 + n]
    try:
        baslik = json.loads(bas.decode('utf-8'))
        if not all(k in baslik for k in ('kdf', 'tuz', 'anahtarlar')):
            raise ValueError
    except (ValueError, TypeError):
        raise DosyaHatasi('Veri dosyası bozulmuş ya da değiştirilmiş (başlık okunamadı).') from None
    govde = veri[i + 4 + n:]
    return baslik, bas, govde[:12], govde[12:]


def govde_coz(veri, dek):
    """Dosya baytlarını verilen DEK ile çözer → düz metin gövde (bayt). Anahtar uymazsa ya da dosya değiştirilmişse DosyaHatasi."""
    _, bas, n, sif = ayir(veri)
    try:
        return zlib.decompress(AESGCM(dek).decrypt(n, sif, SIHIR + bas))
    except (InvalidTag, ValueError, zlib.error):
        raise DosyaHatasi('Veri dosyası bozulmuş ya da program dışında değiştirilmiş; açılamıyor. Yedekten geri dönün '
                          '(Ayarlar › Yedekten geri dön).') from None


def dosya_ac(veri, kullanici_adi=None, parola=None, kurtarma=None):
    """Dosya baytları + parola (ya da kurtarma anahtarı) → (Kasa, düz metin gövde)."""
    baslik, _, _, _ = ayir(veri)
    dek = anahtar_coz(baslik, kullanici_adi, parola, kurtarma)
    return Kasa(dek, baslik), govde_coz(veri, dek)


def oku(yol):
    with open(yol, 'rb') as f:
        return f.read()


def guvenli_yaz(yol, veri):
    """Yarım kalmış yazma dosyayı bozmasın: geçici dosyaya yaz, diske işlet, sonra tek adımda yerine koy."""
    gecici = yol + '.yaziliyor'
    with open(gecici, 'wb') as f:
        f.write(veri)
        f.flush()
        os.fsync(f.fileno())
    for i in range(10):   # Windows'ta virüs tarayıcısı / yedekleme programı dosyayı kısa süre kilitleyebilir
        try:
            os.replace(gecici, yol)
            return yol
        except PermissionError:
            if i == 9:
                raise
            time.sleep(0.1 * (i + 1))


def guvenli_sil(yol):
    """Dosyanın üzerine rastgele bayt yazıp siler (eski şifresiz dosyalar için; SSD'de üzerine yazma garanti değildir)."""
    try:
        boyut = os.path.getsize(yol)
        with open(yol, 'r+b') as f:
            kalan = boyut
            while kalan > 0:
                parca = min(kalan, 1 << 20)
                f.write(os.urandom(parca))
                kalan -= parca
            f.flush()
            os.fsync(f.fileno())
    except OSError:
        pass
    os.remove(yol)


# ----------------------------------------------------------------------------- hatalı giriş sayacı
class GirisSayaci:
    """Üst üste hatalı girişten sonra bekleme: 5. hatadan sonra 30 sn, her yeni hatada iki katı, en çok 15 dk.
    Sayaç veri klasöründeki giris.json'da (kullanıcı adı yazılmaz). Asıl koruma şifrelemedir; bu yalnız tahmin denemelerini yavaşlatır."""
    ESIK, ILK, EN_COK = 5, 30, 900

    def __init__(self, yol, saat=time.time):
        self.yol = yol
        self.saat = saat
        try:
            with open(yol, encoding='utf-8') as f:
                v = json.load(f)
            self.hatali, self.son = int(v.get('hatali', 0)), float(v.get('son', 0))
        except (OSError, ValueError, TypeError, AttributeError):
            self.hatali, self.son = 0, 0.0

    def _yaz(self):
        try:
            with open(self.yol, 'w', encoding='utf-8') as f:
                json.dump({'hatali': self.hatali, 'son': self.son}, f)
        except OSError:
            pass

    def bekleme(self):
        """Yeni denemeden önce beklenecek saniye (0 = bekleme yok)."""
        if self.hatali < self.ESIK:
            return 0
        sure = min(self.ILK * 2 ** (self.hatali - self.ESIK), self.EN_COK)
        return max(0, min(sure, self.son + sure - self.saat()))   # saat geri alınmışsa da en çok `sure`

    def hata(self):
        self.hatali += 1
        self.son = self.saat()
        self._yaz()

    def basari(self):
        """Sayaç sıfırlanır. Dönüş: (önceki hatalı deneme sayısı, son hatalı denemenin zamanı)."""
        once = (self.hatali, self.son)
        if self.hatali:
            self.hatali, self.son = 0, 0.0
            self._yaz()
        return once
