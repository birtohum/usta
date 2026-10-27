# Demo senaryoları — Türkiye'ye özgü görevler

Jüri ölçütleri (resmî kurallar, cerebralvalley.ai etkinlik feragat sayfası): **Etki %30**, **Meta araçlarının kullanımı %25**,
**Teknik derinlik ve uygulama %20**, **Demo %25** (çalışan, etkileyici demo; canlıda dayanıyor mu; video kalitesi).
Indie track ayrıca "yaratıcılık, teknik iddia ve çalışıyor mu" diye değerlendiriliyor.

Bu yüzden senaryolar şunu göstermeli: (1) gerçek bir Türk işletmesinin/geliştiricisinin derdi, (2) jenerik bir ajanın
kolayca yanlış yaptığı yerel bir ayrıntı (İ/ı, kuruş yuvarlama, mod-97, resmî tatil), (3) Usta'nın kanıt ekranı —
tercihen bir kez **kırmızı rozet → yeşil rozet**.

> Bu görevler henüz Usta'da çalıştırılmadı (yalnızca 4 numara, değerlendirme setinden gerçek kayda dayanıyor).
> Ana oturuma "demo için bunları dene" diye önerildi. Model çıktıları rastgeledir: kayıttan önce her görevi 2–3 kez
> çalıştırıp videoya en okunaklı koşuyu al; düzeltme döngüsü görünmüyorsa 4 numaraya geç.

| # | Görev | Yerel tuzak | Düzeltme döngüsü olasılığı | Videoda |
|---|---|---|---|---|
| 1 | TC kimlik no doğrulama | 10. ve 11. hane algoritması, ilk hane 0 olamaz | düşük | evet (sesle) |
| 2 | TR IBAN doğrulama ve biçimlendirme | mod-97, harf→sayı, 26 karakter | orta — **hatalı test süzgeci** hikâyesi | kısa |
| 3 | KDV'li fatura toplamı | %1/%10/%20, Decimal, kuruşa yuvarlama, satır bazında mı toplamda mı | orta | yedek |
| 4 | Vade tarihi (hafta sonu + resmî tatil öteleme) | zincirleme tatil, çıkış kodu 2, stdout'ta tek satır | **yüksek — kayıtlı: tur 1 6/14 → tur 2 14/14** | **evet (ana gösteri)** |
| 5 | E-ticaret stok CSV raporu | `1.234,50` ondalık virgül, `;` ayırıcı, Türkçe ürün adları, UTF-8 BOM | yüksek | yedek |
| 6 | Türkçe büyük/küçük harf ve sıralama | `"I".lower()` → `i` değil `ı`; `"i".upper()` → `İ`; ç/ğ/ö/ş/ü alfabe sırası | yüksek | kısa |

---

## 1. TC kimlik numarası doğrulayıcı (sesle verilecek açılış görevi)

**Görev metni (sesle okunabilecek kadar kısa):**

> `tckn.py` içinde `tckn_dogrula(no: str) -> bool` yaz. Numara 11 haneli ve yalnızca rakam olmalı, ilk hane 0 olamaz.
> 1, 3, 5, 7 ve 9. hanelerin toplamının 7 katından 2, 4, 6 ve 8. hanelerin toplamı çıkarılır; sonucun 10'a bölümünden
> kalan 10. haneye eşit olmalı. İlk 10 hanenin toplamının 10'a bölümünden kalan 11. haneye eşit olmalı.
> Kurallara uymayan her girdi için False döndür; str olmayan girdi için TypeError yükselt.

**Neden etkileyici:** Türkiye'de her kayıt formunda, her e-fatura ve kargo sisteminde bulunan bir kontrol; jüri
"Build for Your World"ü tek cümlede anlar. Sesle verilmesi Muse Voice Transcribe'ı doğal biçimde gösterir.
**Not:** Gerçek bir kişinin TC numarasını ekranda gösterme; testler algoritmayla üretilmiş numaralar kullanır.
Videoda ses kaydında gerçek numara söyleme (README: ses Meta'ya gider).

**Beklenen kanıt ekranı:** Sözleşme kartı (dosya/fonksiyon adı zaten görevde olduğu için muhtemelen "sözleşme
gereksiz"), Glimmer'ın `tckn.py`'yi yazıp kendi testlerini koşturduğu adımlar, Spark'ın 6–14 kabul testi,
yeşil rozet `Tur 1: N/N`. Kısa ve temiz bir "ilk tur" örneği.

---

## 2. TR IBAN doğrulama ve biçimlendirme

**Görev metni:**

> `iban.py` içinde iki fonksiyon yaz. `iban_dogrula(iban: str) -> bool`: boşlukları yok sayar, büyük/küçük harf
> duyarsızdır; Türkiye IBAN'ı "TR" ile başlar, toplam 26 karakterdir, "TR"den sonraki 24 karakterin hepsi rakamdır
> ve 10. karakter (5 haneli banka kodundan sonraki rezerv hane) 0'dır; ISO 13616 mod-97 kontrolü (ilk dört karakter sona alınır,
> harfler A=10 … Z=35 olarak sayıya çevrilir, sonuç 97'ye bölündüğünde kalan 1 olmalı) geçmelidir.
> `iban_bicimle(iban: str) -> str`: geçerli IBAN'ı büyük harfle, dörder karakterlik gruplar hâlinde tek boşlukla
> ayırarak döndürür; geçersizse ValueError yükseltir. str olmayan girdi için iki fonksiyon da TypeError yükseltir.

**Neden etkileyici:** Her Türk e-ticaret ve muhasebe uygulamasında var. Asıl hikâye Usta'nın **hatalı test
süzgeci**: geliştirme sırasında Spark, mod-97 toplamı aslında geçersiz olan bir IBAN'ı "geçerli" diye test etmiş,
Glimmer'ın doğru kodu 3 tur boyunca bu yüzden kalmıştı (README'de anlatılıyor). Artık Spark bir referans çözüm de
yazıyor; referansın da geçemediği test ayıklanıyor. Bu, "LLM'in yazdığı teste körü körüne güvenmiyoruz" demenin
somut kanıtı — Teknik derinlik puanı için iyi.

**Beklenen kanıt ekranı:** Kabul testleri kartında, varsa referansla iptal edilen test(ler); yeşil rozet. İptal
yoksa sorun değil: anlatımda geliştirme sırasındaki olayı README'deki cümleyle söyle, ekranda süzgeç kodunu
(`usta/dogrulayici.py` → `referansla_suz`) 2 saniye göster.

---

## 3. KDV'li fatura toplamı

**Görev metni:**

> `fatura.py` içinde `fatura_hesapla(satirlar: list[dict]) -> dict` yaz. Her satır `{"urun": str, "adet": int,
> "birim_fiyat": str, "kdv": int}` biçimindedir; birim_fiyat "149.90" gibi ondalık noktalı bir metindir.
> KDV oranı yalnızca 1, 10 ya da 20 olabilir, değilse ValueError. Adet pozitif tam sayı olmalı, değilse ValueError.
> Para hesabında float kullanma, Decimal kullan. Her satırın matrahı adet × birim_fiyat; satır KDV'si matrah ×
> oran / 100 olup satır bazında kuruşa (2 ondalık, yarım yukarı) yuvarlanır. Sonuç `{"matrah": Decimal,
> "kdv_toplam": Decimal, "kdv_oranlara_gore": {oran: Decimal}, "genel_toplam": Decimal}` olur; yalnızca faturada
> geçen oranlar sözlükte yer alır. Boş liste için tüm toplamlar Decimal("0.00") ve sözlük boş olur.

**Neden etkileyici:** Küçük işletmenin her gün yaptığı iş; 2023'teki %8→%10, %18→%20 değişikliğini bilen her
Türk izleyici hemen tanır. Kuruş yuvarlama (satır bazında, yarım yukarı) ajanların sık şaştığı yer — kırmızı rozet
çıkma olasılığı var.

**Beklenen kanıt ekranı:** Dosya sekmesinde `fatura.py` (Decimal ve `ROUND_HALF_UP` görünür), kabul testlerinde
`%1 + %10 + %20` karışık fatura örneği, yeşil rozet; şanslıysak `Tur 1: 9/11 → Tur 2: 11/11`.

---

## 4. Vade tarihi hesaplayıcı — ANA GÖSTERİ (düzeltme döngüsü kayıtlı)

**Görev metni:** `veri/zor.jsonl` içindeki **g21** görevini aynen kullan (Bursa'daki tedarikçi için
`python vade.py --fatura-tarihi … --vade-gun … --tatiller … --hafta-sonu-oteleme ileri|geri --cikti-formati …`).
Arayüzde örnek olarak hazır bulunması için ana oturuma eklemesi önerildi.

Videoda kısaltılmış sözlü özet: *"Bursa'da bir tedarikçi; fatura tarihine vade gününü ekle, hafta sonuna ya da
resmî tatile denk gelirse ileri ya da geri ötele; tatil zinciri varsa sonuna kadar çöz; hatalı girdide çıkış kodu 2."*

**Neden etkileyici:** Türkiye'de 29 Ekim, bayram arifeleri ve köprü günleri yüzünden ödemeler sürekli kayar; muhasebeci
bunu elle yapar. Görev uzun ve çok kurallı (14 kabul testi, 19 gizli test) — "basit oyuncak görev" eleştirisini
önler. Ve **kayıtlı gerçek koşuda** (Usta, c kipi, `kayitlar/degerlendirme/zor/c_g21.json`):

- Tur 1: **6/14** kabul testi geçti (kırmızı rozet).
- Spark hakemi kalan testleri görev metnine göre inceledi; ör. `test_haftasonu_ileri`, `test_cikti_dd_mm_yyyy` →
  "görev açıkça istiyor → düzeltilecek".
- Glimmer hata çıktısıyla düzeltti → Tur 2: **14/14** (yeşil rozet).
- Usta'nın hiç görmediği **gizli testler: 19/19**.
- Toplam 16 adım, ~589 sn (videoda hızlandır).

**Beklenen kanıt ekranı:** Rozet satırı `Tur 1: 6/14` (kırmızı) `Tur 2: 14/14` (yeşil); hakem satırları
("görev açıkça istiyor → düzeltilecek"); dosya sekmesinde `vade.py`. Bu, videonun **zirve anı**.

**Risk:** Canlı koşuda ilk turda hepsi geçebilir ya da 3 turda bitmeyebilir. Kayıttan önce 2–3 kez koş; döngü
çıkmazsa aynı görevi farklı koşuyla dene, ya da 5/6 numaraya geç. Hiçbiri olmazsa kayıtlı `c_g21.json`'u dürüstçe
"değerlendirmeden gerçek koşu" diye göster — canlıymış gibi sunma.

**Kayıtlı koşu güncel kodla mı?** Evet: `c_g21.json` içinde `hakem` alanı var (8 karar). Hakem adımı ve
yalnızca adlandırmaya indirilmiş sözleşme aynı commit'te (695d8af) geldiği için bu koşu yeni kodla yapılmış.
Depodaki kopyası `sonuclar/zor/c_g21.json`.

**Kırmızıyla başlayan diğer kayıtlı c koşuları** (hepsinde `hakem` alanı var):

| Görev | Turlar | Gizli testler | Demoya uygun mu |
|---|---|---|---|
| g21 vade.py | 6/14 → 14/14 | 19/19 | **evet, ana gösteri** |
| g19 SlugUretici (Türkçe slug, I→ı→i) | 11/12 → 12/12 | 16/16 | **evet, yedek**: Türkçe harf konusu, kısa |
| g17 PlakaKayit (Bursa otopark) | 0/2 → 12/12 | 18/18 | zayıf: tur 1'de yalnızca 2 test sayıldı (büyük olasılıkla toplama/içe aktarma hatası); "6/14" kadar okunaklı değil |
| g26, g32 | 12/13 → 13/13, 11/12 → 12/12 | 15/17 | hayır: kabul testleri geçti ama gizli testler kaldı |
| g25 | 11/12 → 11/12 → 12/12 | 3/17 | hayır |
| g22 | 0/2 üç tur | 0/2 | hayır |

g26/g32/g25 sonuçları videoda değil, ama dürüstlük bölümünde işe yarar: "kabul testlerini geçmek, gizli testleri
geçmeyi garanti etmiyor".

**GPU durumu (ana oturumun bildirdiği):** Modal kredisi bitti; Glimmer kullanıcı karar verene kadar kapalı. GPU
açılmazsa video kayıtlı koşularla (g21 ana gösteri, g19 yedek) çekilir. Bu durumda ekranda "recorded run from our
evaluation" yazar. Sesle açılış (senaryo 1) için yalnızca Voice Transcribe adımı canlı gösterilebilir; bunun için
Glimmer gerekmez.

---

## 5. E-ticaret stok CSV raporu

**Görev metni:**

> `stok_raporu.py` adlı komut satırı programını `python stok_raporu.py stok.csv --esik 5` biçiminde yaz.
> Girdi, Türkiye'deki tablolama programlarının verdiği biçimde: UTF-8 (başında BOM olabilir), ayırıcı noktalı
> virgül, başlık satırı `urun_kodu;urun_adi;adet;birim_fiyat`; fiyatlar `1.234,50` gibi binlik ayırıcı nokta,
> ondalık ayırıcı virgüldür. Adet negatif ya da tam sayı değilse o satırı atla ve stderr'e `satir N atlandi`
> yaz (N başlık hariç 1'den başlar). stdout'a üç satır yaz: `toplam_stok_degeri: 12.345,67` (aynı Türkçe biçimde,
> kuruşa yuvarlanmış), `kritik_urunler: ` ardından adedi eşikten küçük ürünlerin adları Türk alfabesine göre
> sıralanmış ve virgül+boşlukla ayrılmış hâlde, `atlanan_satir: K`. Dosya yoksa çıkış kodu 1.

**Neden etkileyici:** Trendyol/Hepsiburada satıcısının Excel'den aldığı gerçek dosya biçimi. Ondalık virgül, BOM ve
Türkçe sıralama üçü birden: jenerik bir ajanın ilk denemede kaçırması çok olası → düzeltme döngüsü için iyi aday.

**Beklenen kanıt ekranı:** Kabul testlerinin `tmp_path`'e CSV yazıp programı subprocess ile koşturduğu görülür;
olası kırmızı rozet (ör. `ŞAPKA` / `Çanta` sırası ya da BOM), ardından yeşil.

---

## 6. Türkçe büyük/küçük harf ve alfabetik sıralama

**Görev metni:**

> `turkce.py` içinde üç fonksiyon yaz. `kucult(s: str) -> str` ve `buyut(s: str) -> str` Türkçe kurallarla harf
> dönüştürür: I↔ı ve İ↔i; diğer harfler için Python'un kendi dönüşümü kullanılır. `turkce_sirala(kelimeler:
> list[str]) -> list[str]` kelimeleri Türk alfabesine göre (a b c ç d e f g ğ h ı i j k l m n o ö p r s ş t u ü v y z),
> büyük/küçük harf duyarsız sıralar; eşit olanlar özgün sırasını korur. str olmayan girdi için TypeError.
> Örnek: `buyut("istanbul ılık")` → `"İSTANBUL ILIK"`, `turkce_sirala(["şeker", "Zeytin", "çay", "Ilgaz", "incir"])`
> → `["çay", "Ilgaz", "incir", "şeker", "Zeytin"]`.

**Neden etkileyici:** Dünyaca ünlü "Turkish I problem": `"I".lower()` Python'da `i` verir, Türkçede `ı` olmalı.
Uluslararası jüri bu hatayı tanır; Türk izleyici için de "bizim dertlerimizi anlayan ajan" mesajı. Kısa bir görev,
ama ilk turda kırmızı rozet görme olasılığı yüksek.

**Beklenen kanıt ekranı:** Kabul testlerinde `"Ilgaz"` → `"ılgaz"` gibi bir beklenti; olası `Tur 1: 7/9 → Tur 2: 9/9`.
Ekranda `turkce.py` içinde `str.maketrans("Iİ", "ıi")` benzeri satır vurgulanabilir.

---

## Kayıt sırası önerisi

1. Glimmer'ı ısıt (soğuk başlatma ~3 dk), 4 numarayı 2–3 kez koş, en iyi kırmızı→yeşil koşuyu ekran kaydına al.
2. 1 numarayı sesle ver ve kaydet (açılış).
3. 6 ya da 2'yi yedek olarak kaydet.
4. `modal app stop -y usta-glimmer`.
