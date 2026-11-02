# Demo videosu — en fazla 3:00, çekim listesi ve seslendirme

2 Kas'ta nihai ölçüme göre yeniden yazıldı. İki değişiklik:
- **Canlı demoda yürütücü Muse Spark.** Modal kredisi bittiği için Glimmer canlı çalıştırılamıyor. Glimmer'ı
  yalnızca "34 görevde ölçtük" diye anlat; ekranda Glimmer koşuyormuş gibi gösterme.
- **Sonuç kazanç değil.** Videonun ikinci yarısı "neden işe yaramadı" bulgusunu anlatıyor; bu hem dürüst hem
  teknik derinlik puanı için daha güçlü.

Jüri ölçütleri: Demo %25 · Etki %30 · Meta araçları %25 · Teknik derinlik %20. Seslendirme İngilizce (~380 kelime,
~150 kelime/dk); ekran Türkçe kalır, köşeye İngilizce etiket. Bekleme anlarını hızlandır ve köşeye "⏩ 6×" yaz.

## Kayıt öncesi hazırlık

1. `python calistir.py` → http://127.0.0.1:8765, yürütücü **Muse Spark** (varsayılan), tarayıcı %125, bildirimler kapalı.
2. `demo_senaryolari.md` 1 (TC kimlik, sesle) ve 4 (vade.py) görevlerini 2–3 kez koş. Kırmızı → yeşil rozet çıkan
   koşuyu kaydet. Spark'la tur 1'de hepsi geçerse yeşil koşuyu kullan, düzeltme döngüsünü şemayla anlat; sonucu uydurma.
   2 Kas denemesi (Spark, WSL, c kipi, hazır vade.py örneği): 182 sn, tur 1'de **54/54**, düzeltme döngüsü yok.
   Kırmızı → yeşil anı için 5 ya da 6 numaralı görevi dene; çıkmazsa yeşil koşu + şema yeterli.
3. Ekran kaydı: Win+Alt+R ya da OBS (1920×1080, 30 fps). Ses ayrı kaydedilip üstüne konabilir.
4. Gerçek TC/IBAN söyleme ya da gösterme; `.env`, anahtar, terminal geçmişi kadraja girmesin.

## Çekim listesi

| Süre | Ekran | Ekran üstü yazı (EN) |
|---|---|---|
| 0:00–0:08 | "Usta" yazısı, alt satır | *a Turkish coding agent that shows its evidence* |
| 0:08–0:22 | Kolaj: `1.234,50` biçimli fiyat, fatura, takvimde 29 Ekim | *80M+ Turkish speakers · agents say "done" without proof* |
| 0:22–0:40 | Arayüz, 🎤 **Sesle söyle**, TC kimlik görevi; metin kutuya yazılır | *Muse Voice Transcribe → Turkish task* |
| 0:40–1:05 | Başlat; adımlar akar (⏩), kabul testleri kartı, rozet | *Executor writes & runs code, no network · Spark wrote the tests without seeing the code* |
| 1:05–1:40 | Vade görevi; rozetler, hakem satırları, varsa tur 2 | *Referee enforces only what the task says · repair rounds* |
| 1:40–1:55 | Şema: yürütücü ∥ Spark testler + referans → süzgeç → hakem → düzeltme | *Writer ≠ verifier · faulty-test filter · rollback* |
| 1:55–2:40 | README zor3 tablosu: a 60.2 / b 56.7 / c 57.6, "verified" %60 vs "done" %63 | *1,026 runs · hidden tests · no significant gain* |
| 2:40–3:00 | Depo adresi; Muse Glimmer · Muse Spark · Muse Voice Transcribe | *https://github.com/birtohum/usta* |

## Seslendirme

**0:00–0:22.** More than eighty million people speak Turkish. Small businesses here need code for tax-ID checks, VAT
invoices, and payment dates that slide past public holidays. Coding agents can write it, but they say "done" without
showing it works. Usta is a Turkish coding agent that shows its evidence.

**0:22–1:05.** I say the task in Turkish; Muse Voice Transcribe turns it into text. The executor — here Muse Spark;
we also ran Meta's open-weights Muse Glimmer 30B on our own vLLM server — writes and runs the code with native tool
calls, in a workspace with no network. Meanwhile, in separate calls, Spark writes acceptance tests from the task text
alone. It never sees the code, and the executor never sees the tests.

**1:05–1:55.** A harder one: a due-date calculator with holiday chains and strict exit codes. Failing tests go to a
referee that enforces only what the task explicitly asks for, then back to the executor to repair. A test written by a
model can be wrong too — once Spark called an invalid IBAN valid — so Spark also writes a reference solution, and
tests the reference fails are dropped.

**1:55–2:40.** Then we measured it, properly. 114 very hard Turkish tasks, three runs each, over a thousand runs, with
hidden tests nobody in the loop ever saw. Executor alone: 60 percent. With its own tests: 57. Usta: 58. No significant
gain. Usta's "verified" was right 60 percent of the time — the executor's own "done", 63. Why? The mistakes are
misreadings of the task, and a verifier from the same model family reads the task the same way. Our tests caught 94
percent of code mutations, and still missed those.

**2:40–3:00.** So Usta gives you a visible record, not a guarantee — and a measured answer to whether an LLM can
check an LLM. Code, task sets and every log are open.

## Kurgu notları

- Jüri sessiz izleyebilir: ekran yazıları hikâyeyi tek başına anlatmalı.
- Ölçüm tablosunu en az 8 saniye ekranda tut.
- Kayıtlı koşu kullanırsan köşeye *recorded run* yaz.
