# Hesap kuralları

Program yıllık izni aşağıdaki kurallara göre hesaplar. Kurallar `izin_takip/hesapla.py` içindeki `KURAL` sözlüğünde parametre olarak durur.
Bu belge bir hukuk görüşü değildir; iş sözleşmeniz, toplu iş sözleşmeniz ya da işyeri uygulamanız kanundan farklı (işçi lehine) olabilir.

## Yasal dayanak

- **4857 sayılı İş Kanunu** md.53 (yıllık ücretli izin hakkı ve süresi), md.54 (izin süresinin hesabında önceki çalışmalar, hizmet süresinin
  hesabı), md.55 (çalışılmış sayılan haller; rapor, askerlik vb.), md.56 (izin süresi ve izne çıkma), md.59 (iş sözleşmesinin sona ermesinde
  kullanılmayan iznin ücreti).
- **Yıllık Ücretli İzin Yönetmeliği** (özellikle md.4, md.10, md.20 izin kayıt belgesi).
- **2429 sayılı Ulusal Bayram ve Genel Tatiller Hakkında Kanun** (resmî tatiller, arife günleri).
- **4857 Ek md.2** (evlenme, ölüm, doğum gibi mazeret izinleri).

## Kurallar

| Konu | Kural |
|---|---|
| Hak doğumu | İşe girişin her **yıldönümünde** yeni yıllık izin hakkı doğar (en az 1 yıl çalışma). |
| Süre (md.53) | 1–5. hizmet yılı **14** gün, 6–14. yıl **20** gün, 15. yıl ve sonrası **26** gün. |
| Yaş | Hak kazanılan tarihte **50 yaş ve üstü** ya da **18 yaş ve altı** olana en az **20** gün. Doğum tarihi bilinmiyor ama 50 üstü olduğu kesinse Personel › *50 yaş beyanı* kullanılır. |
| Önceki çalışmalar (md.54) | Aynı işyerindeki önceki çalışma süreleri kıdeme eklenir; her çalışma döneminin kalanı ayrı izlenir. |
| Ücretsiz izin | Ücretsiz izin günleri hak tarihini öteler (hizmet süresine sayılmaz). md.55/a sınırını aşan rapor günleri de **Ücretsiz izin** olarak girilir (program uyarır). |
| Düşülen günler (md.56) | Yalnızca **Yıllık izin (Kİ)** düşülür. **Pazar** ve **tam gün resmî tatil** düşülmez. **Cumartesi** iş günüdür (6 günlük düzen varsayılır). **Arife** ve **28 Ekim** yarım gündür: 0,5 gün düşülür. Rapor, mazeret, ücretsiz ve idari izin yıllık izinden düşülmez. |
| Kalan | Bu çalışma döneminde kazanılan − bu dönemde kullanılan (+ varsa elle düzeltme). İleri tarihli izin girildiği anda kalandan düşülür; **eksi kalan** hak edilmeden kullanılan (avans) izni gösterir ve sonraki hak tarihlerinde kapanır. |
| Avans devri | Önceki çalışma döneminin **eksi** kalanı yeni döneme taşınır (`KURAL['avans_devri']`). Artı kalan taşınmaz; çıkışta ödenmediyse Personel › *Elle düzeltme* ile eklenir. |
| Dönem dışı izin | Çalışma dönemi dışına yazılmış yıllık izin en yakın döneme düşülür (`KURAL['donem_disi_dus']`); hak tarihlerini etkilemez. |
| Kalanın kaynağı | Kullanılan izin önce **en eski haktan** düşülür. İzin Kartı'ndaki "Bu haktan kalan" ve yıllık özet bu dökümü gösterir. Kullanılmayan izin sözleşme sürdükçe yanmaz, devreder. |
| İşten ayrılan (md.59) | Kullanılmayan yıllık izin ücreti çıkışta ödenir: gün × son brüt aylık ücret ÷ 30. Zamanaşımı çıkıştan itibaren 5 yıl olarak izlenir. |
| Uzun izin uyarıları | 60 günden uzun yıllık izin ve md.55/a rapor sınırı için uyarı verilir (engellemez). |

## Değiştirmek

Kural değişikliği yalnızca `izin_takip/hesapla.py` › `KURAL` sözlüğünden yapılır; `testler/test_hesapla.py`'ye karşılık gelen testi ekleyin.
Mevzuat değişirse (ör. süreler, mazeret izin günleri) bu belgeyi ve `KURAL`'ı birlikte güncelleyin.
