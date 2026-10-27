# Demo videosu — 3:00, çekim listesi ve seslendirme

Hedef: jüri ölçütlerine birebir oynamak — **Demo %25** (çalışan ürün, canlı ekran), **Etki %30** (kim için, neden),
**Meta araçları %25** (Glimmer açık ağırlık + Spark + Voice, sıradan entegrasyonun ötesi), **Teknik derinlik %20**
(yazan ≠ doğrulayan, hatalı test süzgeci, hakem, ağsız sandbox, gizli testlerle ölçüm).

- **Seslendirme İngilizce** (jüri uluslararası). Ekrandaki arayüz ve görevler Türkçe kalır; Türkçe ekran öğelerine
  İngilizce **alt yazı/etiket** eklenir (ör. "Tur 1: 6/14" → *Round 1: 6/14 passed*).
- İsteğe bağlı: Türkçe seslendirme ve İngilizce alt yazılı ikinci bir sürüm (X için). Türkçe metin aşağıda her
  satırın altında.
- Konuşma hızı ~150 kelime/dk → 3 dakikada en fazla ~420 kelime. Aşağıdaki İngilizce metin ~400 kelime.
- Bekleme anlarını (Glimmer'ın adımları, Spark'ın test yazması) 4–8× hızlandır; ekranın köşesine "⏩ 6×" yaz —
  dürüstlük jüriye iyi görünür.
- Sayılar `{yer_tutucu}` biçiminde; değerlendirme bitince README'deki gerçek tablodan doldur. Sayı uydurma.

## Kayıt öncesi hazırlık

1. `modal deploy sunucu/glimmer_modal.py`, bir görevle ısıt (soğuk başlatma ~3 dk).
2. `python calistir.py` → http://127.0.0.1:8765, tarayıcı %125 yakınlaştırma, karanlık/aydınlık tek tema, bildirimleri kapat.
3. `demo_senaryolari.md` 4 numarayı (vade.py) 2–3 kez koş; kırmızı→yeşil olanı kaydet. 1 numarayı sesle kaydet.
4. Ekran kaydı: OBS (1920×1080, 30 fps) ya da Win+Alt+R. Mikrofonu ayrı kaydet, sonra üstüne koy.
5. Bitince `modal app stop -y usta-glimmer`.

---

## Çekim listesi

| Süre | Ekran (görüntü) | Ekran üstü yazı (EN) |
|---|---|---|
| 0:00–0:08 | Siyah zemin, "Usta" logosu/yazısı, alt satır: *a Turkish coding agent that proves its own work* | — |
| 0:08–0:22 | Hızlı kolaj: Excel'de `1.234,50` biçimli stok dosyası, bir fatura, takvimde 29 Ekim işaretli | *80M+ Turkish speakers · agents say "done" without proof* |
| 0:22–0:40 | Usta arayüzü. 🎤 **Sesle söyle** basılır, TC kimlik görevi (senaryo 1) söylenir; Muse Voice Transcribe metni kutuya yazar | *Muse Voice Transcribe → Turkish task* |
| 0:40–0:55 | Başlat. Sözleşme kartı açılır; adımlar akar: GLIMMER `tckn.py dosyasını yazıyor`, `$ python -m pytest -q` (⏩ 6×) | *Muse Glimmer 30B (open weights) · sandbox, network disabled* |
| 0:55–1:05 | Kabul testleri kartı (Spark'ın yazdığı testler kayar), yeşil rozet `Tur 1: N/N` | *Muse Spark wrote these tests without seeing the code* |
| 1:05–1:15 | Geçiş: ana gösteri görevi (senaryo 4, vade.py) metni kutuda, Başlat | *Harder: due-date calculator with holidays, 14 tests* |
| 1:15–1:40 | Adımlar (⏩ 8×). Rozet satırında **kırmızı** `Tur 1: 6/14`. Hakem satırları: "görev açıkça istiyor → düzeltilecek" | *Round 1: 6/14 · Spark as referee: only what the task explicitly asks* |
| 1:40–1:58 | "Glimmer düzeltiyor (tur 2)" aşaması, `Edit` adımı (diff görünür), sonra **yeşil** `Tur 2: 14/14`. Rozete yakınlaştır | *Failing output → Glimmer fixes → Round 2: 14/14* |
| 1:58–2:10 | Dosya sekmesinde `vade.py`; ölçüm satırı (adım, süre, Spark maliyeti) | *Evidence, not "done"* |
| 2:10–2:25 | Basit şema (README'deki akış): Spark sözleşme → Glimmer yazar ∥ Spark test + referans çözüm → süzgeç → test → hakem → düzeltme | *Writer ≠ verifier · faulty-test filter · referee* |
| 2:25–2:48 | README ölçüm tablosu: a / b / c, gizli testler | *40 tasks · hidden tests never seen by the agent* |
| 2:48–3:00 | GitHub depo adresi, "Apache 2.0", Meta araç logoları değil — yazıyla: Muse Glimmer · Muse Spark · Muse Voice Transcribe | *github.com/{kullanici}/usta* |

---

## Seslendirme metni

### 0:00–0:22 — Sorun

**EN:** More than eighty million people speak Turkish. Small businesses here deal with things like tax-ID checks, VAT
invoices and payment dates that slide past public holidays. Coding agents can write that code — but they say "done"
without showing that it actually works. Usta is a Turkish coding agent that proves its own work.

**TR:** Seksen milyondan fazla kişi Türkçe konuşuyor. Buradaki küçük işletmeler TC kimlik kontrolü, KDV'li fatura, resmî
tatile kayan vade tarihleri gibi işlerle uğraşıyor. Kod ajanları bu kodu yazabiliyor ama "bitti" dediklerinde gerçekten
çalıştığını göstermiyorlar. Usta, işini kanıtlayan Türkçe bir kodlama ajanı.

### 0:22–0:55 — Ses → Glimmer

**EN:** I just say the task in Turkish. Muse Voice Transcribe turns it into text. Muse Spark first writes a short
naming contract, and then Muse Glimmer — Meta's open-weights 30B model, which we serve ourselves with vLLM — writes
and runs the code with native tool calls, inside a sandbox where networking is completely disabled.

**TR:** Görevi Türkçe söylüyorum; Muse Voice Transcribe metne çeviriyor. Muse Spark önce kısa bir adlandırma
sözleşmesi yazıyor, sonra Meta'nın açık ağırlıklı 30 milyar parametreli modeli Muse Glimmer — kendi vLLM sunucumuzda —
kodu yerel araç çağrılarıyla, ağı tamamen kapalı bir sandbox'ta yazıp çalıştırıyor.

### 0:55–1:05 — Bağımsız testler

**EN:** Meanwhile, Spark writes acceptance tests from the task text alone. It never sees Glimmer's code, and Glimmer
never sees the tests. The writer is not the verifier.

**TR:** Bu sırada Spark, yalnızca görev metninden kabul testleri yazıyor. Glimmer'ın kodunu hiç görmüyor; Glimmer da
testleri görmüyor. Yazan, doğrulayan değil.

### 1:05–1:58 — Düzeltme döngüsü (zirve)

**EN:** Now a harder one: a due-date calculator for a supplier in Bursa — weekends, holiday chains, strict exit
codes. First round: six of fourteen tests pass. Before sending failures back, Spark acts as a referee: it keeps only
the expectations the task explicitly asks for, so the agent is never forced to break correct code. Glimmer reads
the failing output and fixes it. Round two: fourteen out of fourteen.

**TR:** Şimdi daha zor bir görev: Bursa'daki bir tedarikçi için vade hesaplayıcı — hafta sonu, zincirleme tatiller,
katı çıkış kodları. İlk tur: on dört testten altısı geçti. Hataları geri göndermeden önce Spark hakemlik yapıyor:
yalnızca görevin açıkça istediği beklentileri tutuyor, böylece ajan doğru kodu bozmaya zorlanmıyor. Glimmer hata
çıktısını okuyup düzeltiyor. İkinci tur: on dörtte on dört.

### 1:58–2:25 — Neden güvenilir

**EN:** A test written by a model can be wrong too. During development Spark claimed an invalid IBAN was valid. So
Spark also writes a reference solution, and any test that the reference fails is dropped. The test file is rewritten
before every run, so the agent can't edit its way to green.

**TR:** Modelin yazdığı test de yanlış olabilir; geliştirirken Spark, geçersiz bir IBAN'ı geçerli sanmıştı. Bu yüzden
Spark bir referans çözüm de yazıyor ve referansın geçemediği testler ayıklanıyor. Test dosyası her çalıştırmadan önce
yeniden yazılıyor; ajan testi değiştirerek yeşile ulaşamıyor.

### 2:25–2:48 — Ölçüm (yer tutucular)

**EN:** We measured it on {n_gorev} Turkish tasks with hidden tests that neither the agent nor Usta's test writer
ever saw. Glimmer alone: {a_basari}. Glimmer with its own tests: {b_basari}. Usta: {c_basari}. Everything —
the task sets and the evaluation scripts — is in the repo, including where it didn't help.

**TR:** Ajanın da Usta'nın test yazarının da hiç görmediği gizli testlerle {n_gorev} Türkçe görevde ölçtük. Glimmer tek
başına: {a_basari}. Kendi testleriyle: {b_basari}. Usta: {c_basari}. Görev setleri ve ölçüm betikleri depoda —
işe yaramadığı yerler dâhil.

> Eğer c, a/b'den belirgin şekilde iyi değilse bu bölümü şöyle değiştir (dürüstlük, uydurmadan iyidir):
> **EN:** "Glimmer is already strong on its own — {a_basari}. What Usta adds is evidence: every result comes with
> independent tests, and faulty tests are caught before they reach the agent."

### 2:48–3:00 — Kapanış

**EN:** Usta. Open weights, Turkish first, and proof instead of "done". Code, data and measurements are open.

**TR:** Usta. Açık ağırlık, önce Türkçe, "bitti" yerine kanıt. Kod, veri ve ölçümler açık.

---

## Kurgu notları

- Rozet geçişini (kırmızı → yeşil) yavaşlat ve yakınlaştır; videonun tek "vay" anı bu.
- Alt yazılar: Türkçe ekran öğelerinin yanına küçük İngilizce etiket (*Round*, *passed*, *referee: task explicitly
  requires → will be fixed*).
- Müzik çok alçak; konuşma anlaşılır olsun. Jüri videoyu sessiz de izleyebilir → ekran yazıları tek başına hikâyeyi
  anlatmalı.
- Kişisel veri yok: gerçek TC/IBAN söyleme ve gösterme; API anahtarları, `.env` ve Modal panosu kadraja girmesin.
- Kayıtlı koşu kullanırsan (canlı değilse) köşeye *recorded run from evaluation* yaz.
