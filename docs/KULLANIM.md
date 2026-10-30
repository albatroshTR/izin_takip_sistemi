# İzin Takip Sistemi — Kullanım kılavuzu

Kim ne kadar yıllık izin hak etti, ne kadarını kullandı, ne kadarı kaldı; izin girişi, izin kartı ve izin formu, aylık takvim,
işten ayrılanların izin ücreti ve otomatik kontroller tek pencerede. Programa kullanıcı adı ve parolayla girilir; veriler şifreli tutulur
(aşağıda [Güvenlik](#güvenlik)).

## Kurulum

**A) Kaynak koddan çalıştırmak.** [python.org](https://www.python.org/downloads/)'dan Python 3.9 – 3.13 kurun, sonra:

```bash
python -m pip install -r gereksinimler.txt
python baslat.py
```

Windows'ta (Python kuruluysa, *Add python.exe to PATH* işaretliyse) `calistir.bat`'a çift tıklamak da yeter; ilk seferde paketleri kurar.

**B) Windows `.exe` derlemek.** `derle.bat`'a çift tıklayın: paketler kurulur, testler çalışır ve `dist\Izin Takip Sistemi.exe` oluşur
(tek dosya; istediğiniz klasöre koyup çift tıklayın). Program imzasız olduğundan Windows ilk açılışta "bilinmeyen yayıncı" uyarısı verebilir
(*Ek bilgi › Yine de çalıştır*). GitHub'daki Actions iş akışı da aynı `.exe`'yi artifact olarak üretir.

## İlk açılış

1. **Yönetici hesabı.** Ad Soyad, kullanıcı adı ve parola istenir (parola en az 8 karakter, harf ve rakam). Veriler bu parolayla şifrelenir.
2. **Kurtarma anahtarı.** Bir kez `XXXX-XXXX-…` biçiminde gösterilir. Yazdırın ya da kâğıda yazıp güvenli bir yerde saklayın: parola
   unutulursa programa yalnız bununla girilir ("Parolamı unuttum").
3. **Başlangıç.** *Örnek veriyle başla* uydurma 12 kişilik bir veri yükler (programı denemek için); *Boş başla* yalnız resmî tatilleri yükler,
   personeli kendiniz girersiniz. Örnek veri gerçek kişi içermez.

## Sayfalar

| Sayfa | Ne var |
|---|---|
| **Genel Durum** | Çalışan sayısı, toplam kalan izin, eksi bakiyeliler, bugün izinde olanlar; yaklaşan izinler ve hak tarihleri; dikkat gerektirenler; herkesin kalan izni (süzgeçli, çift tıklayınca izin kartı). Excel'e aktar, PDF. |
| **Personel** | Çalışanlar / ayrılanlar listesi; yeni personel. Çift tıklayınca **İzin Kartı**: kalan izin, hak kazanma tarihleri ve her haktan kalan, yıllık özet, izin geçmişi, açıklamalar; *İzin kartı (PDF / yazdır)* = yönetmelik md.20 izin kayıt belgesi. |
| **İzin Kayıtları** | Bütün izinler; arama, tür ve yıl süzgeci, uyarılı kayıtlar. **Yeni izin** (her yerde `Ctrl+N`): kişi, tür, tarihler — düşülecek gün, işe dönüş tarihi ve kalan izin yazarken hesaplanır. Seçili izin için *İzin formu*. |
| **Takvim** | Aylık kişi × gün takvimi (renkler izin türü; gri Pazar, turuncu resmî tatil). Bir güne çift tıklayınca o güne izin girilir. PDF. |
| **Ayrılanlar** | İşten ayrılanların ödenmesi gereken izin ücreti (md.59): gün kendiliğinden; son brüt ücret → tutar (gün × ücret ÷ 30), ödeme durumu, zamanaşımı (çıkış + 5 yıl). |
| **Kontroller** | Avans (hak edilmeden kullanılan) izin, çalışma dönemi dışı tarih, çakışan kayıt, Pazar/tatile yazılmış izin, eksik bilgi. Çift tıklayıp düzeltin. |
| **Tatiller** | Resmî tatiller (2019–2030 hazır); gelecek yılın sabit tatillerini tek düğmeyle ekleme. |
| **Ayarlar** | Şirket adı, hesap tarihi (geçmiş/gelecek bir tarihe göre bakiye); hesabım ve güvenlik (parola, kilit, kurtarma anahtarı); kullanıcılar (yönetici); şifreli yedekler; Excel'e aktar; işlem geçmişi; hakkında. |
| **Yardım** | Nasıl yapılır, hesap kuralları. |

İpuçları: vazgeçilen izni silmeyin, **iptal edin** (geçmiş kalır, üstü çizili görünür); "Sil" yalnız yanlışlıkla girilen kayıt içindir.
İşten ayrılanın kaydı silinmez: Personel'de çıkış tarihini yazın. Yeniden işe giren kişiye "Dönem ekle" ile yeni giriş yazın.

## Güvenlik

- **Giriş:** kullanıcı adı + parola. Kullanıcı adında büyük/küçük harf ve Türkçe karakter fark etmez (`Ayşe.Örnek` = `ayse.ornek`).
  Üst üste 5 hatalı denemeden sonra 30 sn beklenir; her yeni hatada süre iki katına çıkar (en çok 15 dk). Hatalı denemeler sonraki
  başarılı girişte işlem geçmişine yazılır ve ekranda gösterilir.
- **Roller:** *Yönetici* kullanıcı ekler / düzenler / siler, parola sıfırlar, otomatik kilit süresini ve kurtarma anahtarını değiştirir,
  yedekten geri döner. *Kullanıcı* personel ve izin işlemlerinin hepsini yapar. Yeni kullanıcı ya da parolası sıfırlanan kişi ilk
  girişte kendi parolasını belirler. Son yönetici silinemez; kimse kendi hesabını silemez. Her işlem, yapanın adıyla işlem geçmişine
  ve izin kayıtlarının "Giren" sütununa yazılır.
- **Kilit:** program boşta kalınca (varsayılan 10 dk; Ayarlar'da 5–60 dk) kilitlenir. Elle kilit: kenar çubuğundaki kilit düğmesi ya da `Ctrl+L`.
- **Şifreleme:** veri dosyası ve yedekler AES-256-GCM ile şifrelidir. Verinin anahtarı her kullanıcı için parolasından (scrypt: her
  deneme ≈0,3 sn ve 64 MB bellek ister) ve bir kez de kurtarma anahtarından türetilen anahtarla saklanır. Dosyada kullanıcı adları da açık
  yazılmaz. Dosyada (ya da yedekte) tek bir bayt değiştirilirse program dosyayı açmaz. Program verileri bellekte açar; diske düz metin yazılmaz.
- Parola değişince, kullanıcı silinince ya da yeni kurtarma anahtarı oluşturulunca yedekler de yeni anahtarlarla yeniden yazılır
  (yalnız programın yedek klasöründekiler; başka yere kopyalanmış eski yedekler eski parolayla açılmaya devam eder).
- Program aynı veri klasöründe ikinci kez açılamaz.
- **Sınırlar:** hiçbir masaüstü programı "kırılamaz" değildir. Korunan şey veridir: parola ya da kurtarma anahtarı olmadan okunamaz ve
  değiştirilemez. Bunlar koruma dışındadır: PDF ve Excel çıktıları şifresizdir (Ayarlar › *Çıktı klasörünü temizle*); program
  açıkken bilgisayara erişen biri ekrandakini görür; `.exe` dosyası incelenebilir. **Parola ve kurtarma anahtarı birlikte kaybolursa veri
  hiçbir şekilde açılamaz.**

## Veriler ve yedek

- Veri dosyası (şifreli): `Belgeler\İzin Takip Sistemi\personel_takip.vt` (Ayarlar › *Klasörü aç*). Başka bir klasör için `--veri <klasör>`
  seçeneği ya da `IZIN_TAKIP_VERI` ortam değişkeni.
- Her gün ilk açılışta `yedekler\personel_takip_YYYY-AA-GG.vt` (şifreli, son 60 gün). *Şimdi yedekle* / *Yedekten geri dön* Ayarlar'da;
  geri dönüşte kullanıcı hesapları ve parolalar değişmez.
- PDF ve Excel çıktıları (şifresiz): `çıktılar` klasörü.
- Klasörü ara sıra bir USB belleğe ya da sunucuya kopyalayın (yedekler şifreli olduğundan kopya da şifrelidir).
- Beklenmeyen bir hata olursa ayrıntısı `hata_gunlugu.txt` dosyasına yazılır (kişi adı içerebilir; paylaşmadan önce temizleyin).

## Komut satırı seçenekleri

```
python baslat.py [--veri <klasör>] [--ornek-veri] [--deneme] [--ekran-goruntusu <klasör>] [--tarih YYYY-MM-DD]
```

`--ornek-veri`, `--deneme` ve `--ekran-goruntusu` pencere açmaz; hesabı `IZIN_TAKIP_KULLANICI` / `IZIN_TAKIP_PAROLA` ortam
değişkenlerinden okur (yalnız otomatik sınama içindir; normal açılış bunlara bakmaz). Veri dosyası yoksa `--ornek-veri` bu hesapla yönetici
oluşturur ve kurtarma anahtarını konsola yazar.

## Geliştirici notları

- Hesap kuralı yalnız `izin_takip/hesapla.py` › `KURAL` sözlüğünden değiştirilir; `docs/hesap-kurallari.md` ile tutarlı tutulur.
- Ad, sürüm ve telif `izin_takip/__init__.py`'dedir; `.exe`'nin Windows dosya özellikleri derlemede bu sabitlerden üretilir (`izin_takip.spec`).
- Logo ve simge `kaynak_uret.py` ile çizilir (marka görseli yok).
- PySide6 6.8.1 kullanılmamalı (PDF bilgi sözlüğünü bozuk yazar); `gereksinimler.txt` 6.9.3'e sabit.
- Testler: `python testler/test_hesapla.py`, `QT_QPA_PLATFORM=offscreen python testler/test_uygulama.py`.
