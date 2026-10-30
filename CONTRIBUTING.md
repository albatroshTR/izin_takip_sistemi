# Katkı rehberi

Katkılarınız memnuniyetle karşılanır.

1. Bir issue açın ya da var olan bir issue'da konuşun.
2. Dalı çatallayıp değişikliği yapın; **testleri çalıştırın**:
   `python testler/test_hesapla.py` ve `QT_QPA_PLATFORM=offscreen python testler/test_uygulama.py`.
3. Hesap kuralı değişiyorsa yalnız `izin_takip/hesapla.py` › `KURAL` sözlüğünü değiştirin, `docs/hesap-kurallari.md` ile tutarlı tutun
   ve `testler/test_hesapla.py`'ye test ekleyin. Hukuki dayanağı (madde / yönetmelik) PR açıklamasında belirtin.
4. Çekme isteği (PR) açın. Commit mesajları Türkçe ya da İngilizce olabilir.

## Kişisel veri

**Gerçek personel verisi paylaşmayın** — issue, PR, günlük ya da ekran görüntüsü olarak da. Hata bildirirken ad, tarih ve izin kayıtlarını
uydurma değerlerle yeniden üretin (`izin_takip/ornek_veri.py` bir örnektir). Hata günlüklerinde (`hata_gunlugu.txt`) kişi adı olabilir; paylaşmadan önce temizleyin.
