# Demo videosu akışı (3 dk)

Kayıttan önce: `modal deploy sunucu/glimmer_modal.py`, sonra bir görevi bir kez çalıştırıp Glimmer'ı ısıt (soğuk başlatma
~3 dk). `python calistir.py` → http://127.0.0.1:8765. Ekran kaydı: Windows'ta Win+Alt+R (Xbox Game Bar) ya da OBS.
Video İngilizce altyazılı Türkçe olabilir; jüri uluslararası.

| Süre | Ekran | Söylenecek (öneri) |
|---|---|---|
| 0:00–0:20 | Başlık sayfası / README üstü | "Türkçe konuşan geliştiriciler ve küçük işletmeler için ajan yok; olanlar da 'bitti' dediğinde kanıt göstermiyor. Usta, işini bağımsız testlerle kanıtlayan Türkçe bir kodlama ajanı." |
| 0:20–0:45 | Arayüz, 🎤 Sesle söyle | Görevi sesle ver (ör. "fatura.py içinde kdv_ekle fonksiyonu yaz, oran bir, on ya da yirmi değilse hata versin"). Muse Voice Transcribe metni kutuya yazar. |
| 0:45–1:45 | Canlı adımlar | Başlat. Anlat: "Muse Spark adlandırma sözleşmesini yazdı. Açık ağırlıklı Muse Glimmer, ağı kapalı bir sandbox'ta dosyayı yazıyor, kendi testlerini çalıştırıyor. Bu arada Spark, Glimmer'ın kodunu görmeden bağımsız kabul testleri yazdı ve onları kendi referans çözümüne karşı sınayıp hatalı olanları ayıkladı." (Uzun bekleme kısımlarını videoda hızlandır.) |
| 1:45–2:15 | Sonuç kartı, rozetler, dosyalar | "Testler kalırsa hata Glimmer'a döner; Spark hakem olarak yalnızca görevin açıkça istediği testleri dayatır. Sonuç: hangi testler kaç turda geçti, maliyet." |
| 2:15–2:50 | README ölçüm tablosu | Dürüst sonuç: a/b/c tablosu. Kazanç varsa göster; yoksa "Glimmer zaten güçlü; Usta'nın değeri kanıt ve hatalı testi ayıklama — sayılar burada" de. |
| 2:50–3:00 | Depo adresi | "Kod, ölçüm betikleri ve görev setleri açık." |

Kayıt sonrası: `modal app stop -y usta-glimmer`.

## X gönderisi taslağı

> Usta: Türkçe görev ver, açık ağırlıklı Muse Glimmer kodu ağı kapalı sandbox'ta yazsın; Muse Spark kodu görmeden
> bağımsız testler yazsın, hatalı testleri referansla ayıklasın, hakemlik etsin. "Bitti" değil, kanıt.
> 40 görevlik ölçüm ve kod açık: <depo adresi> #MetaHackathon
