# Usta: güvenlik denemesi bulguları

Kapsam: `usta/arac.py` (araç çalıştırıcısı) ve `usta/web.py` (web arayüzü), kötü niyetli ya da hatalı model
çıktısına karşı. Testler: [`test_guvenlik.py`](test_guvenlik.py). Testler yalnızca `YerelCalisma` ve geçici
klasörlerle çalışır, ağ ve Modal kullanmaz. Gerçek anahtar yerine sahte bir nöbetçi değer (`USTA-SAHTE-ANAHTAR-7f3a9c`)
kullanılır.

Açık bulgular `xfail(strict=True)` ile işaretli. Testler güvenli davranışı ister, bugün başarısız olur. Bulgu
düzeltilince test XPASS verir ve strict olduğu için kırmızıya döner; o zaman işareti kaldırın.

```bash
python -m pip install pytest==8.3.3 fastapi httpx python-multipart websockets
python -m pytest -q tests/ -rxX
```

**Durum:** Düzeltme diff'i ([`guvenlik_duzeltme.diff`](guvenlik_duzeltme.diff)) main'e 69d9baa commit'iyle uygulandı.
B-1, B-2, B-4, B-5, B-6, B-7 ve B-8'in eşzamanlılık bölümü kapandı; bu bulgulara ait 23 testin xfail işareti
kaldırıldı. Açık kalanlar: B-3 ve B-8'in sahipsiz iş bölümü.

B-9 (WSL bash) main'de 17551c0 commit'iyle düzeltildi ve regresyon testleri eklendi. **B-10 açık ve şu an en
önemli bulgu:** `calisma_ac()` varsayılanı artık "yerel" olduğundan web arayüzü de etkileniyor.

Main a95c4ed ile sonuç (Windows 11, Git Bash, Python 3.12): **142 geçti, 2 atlandı, 18 xfail** (16 tanesi B-3,
1 tanesi B-8, 1 tanesi B-10). Atlanan 2 test, dosyaya sembolik bağ kurmak için Geliştirici
Modu gerektiriyor. Klasör bağı (junction) üzerinden yapılan saldırı testi geçiyor.

Düzeltme öncesindeki sonuç 113 geçti, 2 atlandı, 40 xfail idi. Aşağıdaki "Bulgular" bölümü kodun düzeltme öncesi
halini anlatır.

## Bağlam: tehdit modeli

* **Web arayüzü `ModalCalisma` kullanır.** Ağı kapalı bir Sandbox içinde çalışır, içinde sır yoktur. B-1, B-2, B-3
  ve B-5 orada büyük ölçüde etkisizdir.
* **`python -m usta.ajan "..."` varsayılan olarak `yerel` kipte çalışır** (`ajan.py:90`). Bu kipte modelin yazdığı
  komutlar geliştiricinin bilgisayarında, geliştiricinin ortamı ve yetkileriyle çalışır. Kaçışları önleyen tek şey
  `komut_denetle` adlı kara listedir.

## Sonradan eklenen bulgular

### B-10 · YÜKSEK (açık) · Yerel kipte gizlenmiş mutlak yolla klasör dışındaki dosyalar okunabiliyor

Main 5f75d83'ten beri `calisma_ac()` varsayılanı `USTA_CALISMA` değişkeninden geliyor ve verilmezse "yerel"
kullanılıyor. Bu yüzden **web arayüzü de model komutlarını geliştirici bilgisayarında, aynı kullanıcı yetkisiyle**
çalıştırıyor.

Yol filtreleri yalnızca komut metnine bakıyor. Yolu `bytes.fromhex(...)`, `chr(92)` ya da base64 ile kuran bir
komut hiçbir kalıba takılmıyor. Böylece `~/.pflow-anahtarlar.env` (Spark anahtarı) ve depo kökündeki `.env`
(Glimmer anahtarı) okunabiliyor. B-2 düzeltmesi yalnızca ortam değişkenlerini kapatıyor, dosyaları değil.

Yeniden üretme: `test_gizlenmis_mutlak_yol_ile_disari_okunamaz`. Test, nöbetçi değeri içeren geçici bir dosyayı okur;
nöbetçi değerin okunduğu `--runxfail` ile doğrulandı.

```python
komut = "python -c \"print(open(bytes.fromhex('<mutlak yolun hex hali>').decode()).read())\""
komut_denetle(komut)                              # geçer
YerelCalisma().arac_calistir("Bash", {"command": komut})   # dosya içeriği döner
```

Düzeltme: düzenli ifadeyle çözülemez (B-3'le aynı kök neden). Seçenekler, önerilen sırayla:

1. **Web arayüzü için varsayılanı "modal" yapmak.** Yerel kip açıkça istendiğinde arayüzde uyarı gösterilmeli.
   ```diff
   -    tur = tur or os.environ.get("USTA_CALISMA", "yerel")
   +    tur = tur or os.environ.get("USTA_CALISMA", "modal")
   ```
2. Modal kapalı tutulacaksa yerel kip bir kapsayıcı içinde çalıştırılmalı:
   `docker run --rm --network none -v <kok>:/work -w /work python:3.12-slim bash -c ...`.
   Bunun için `YerelCalisma._calistir` çağrısını `docker`'a sarmak yeterli.
3. En azından anahtar dosyaları ajanın çalıştığı kullanıcının okuyamayacağı bir yere taşınmalı. Sunucu ayrı bir
   Windows kullanıcısıyla da çalıştırılabilir.

### B-9 · YÜKSEK · Windows'ta `bash` WSL'e çözülüyordu (ana oturum buldu, 17551c0'da düzeltildi)

`shutil.which("bash")` sonucu `WindowsApps\bash.exe` yani WSL oluyordu. Bu durumda komutlar çalışma klasöründe değil
WSL'in Linux ev dizininde çalışıyordu. Düzeltmeyle Windows'ta yalnızca Git Bash kabul ediliyor ve açılışta `pwd`
denetleniyor.

Regresyon testleri: `test_path_yalnizca_wsl_iken_kabuk_calisma_klasorunde_acilir`,
`test_usta_bash_wsl_gosterse_de_kullanilmaz`, `test_kabuk_baska_klasorde_acilirsa_calisma_reddedilir`. Bu testler WSL'i
hiç başlatmıyor.

## Bulgular (önem sırasıyla)

### B-1 · YÜKSEK · Yerel kipte Bash çalışma klasöründen çıkabiliyor (okuma ve yazma)

`..(/|\|$|\s)` kalıbı `cd ..;`, `cd ..&&`, `..)` gibi biçimleri yakalamıyor. `$HOME`, `${PWD%/*}` ve python'daki
`os.pardir` da mutlak yol filtresinin dışında kalıyor. Model şu yollarla sırlara ulaşabiliyor:
`cd ..; cat <dosya>`, `cat $HOME/.pflow-anahtarlar.env` (Spark anahtarı) ve depo kökündeki `.env` (Glimmer anahtarı).

Yeniden üretme: `test_bash_ust_klasoru_okuyamaz`, `test_bash_ust_klasore_yazamaz`,
`test_bash_ev_dizinindeki_anahtar_dosyasini_okuyamaz`.

```python
c = YerelCalisma()
c.arac_calistir("Bash", {"command": "cd ..; ls"})                          # %TEMP% listelenir
c.arac_calistir("Bash", {"command": "cat $HOME/.pflow-anahtarlar.env"})    # filtreden geçer
```

Düzeltme: diff'teki üç yeni `YASAK_KALIPLAR` satırı ve `HOME` değerinin çalışma klasörüne çevrilmesi (B-2'deki
`_ortam`). **Ancak bir kara liste hiçbir zaman tam bir sınır değildir (bkz. B-3).** Gerçek önlem şudur: yerel kip
yalnızca güvenilen testler için kullanılmalı ve `ajan.py`'nin varsayılan kipi `modal` yapılmalı:

```diff
-    tur = sys.argv[2] if len(sys.argv) > 2 else "yerel"
+    tur = sys.argv[2] if len(sys.argv) > 2 else "modal"
```

### B-2 · YÜKSEK · Yerel kipte alt süreç bütün ortamı devralıyor: API anahtarları sızıyor

`subprocess.run` çağrısına `env=` verilmemiş. Model `env`, `printenv`, `set` ya da `os.environ` çalıştırdığında
`USTA_GLIMMER_TOKEN` ve `META_MODEL_API_KEY` araç çıktısına düşüyor. Bu çıktı konuşma geçmişine eklenip Glimmer
sunucusuna geri gönderiliyor ve arayüzde `olay("sonuc")` ile gösteriliyor. `/proc/self/environ` filtreye takılıyor,
`env` takılmıyor.

Yeniden üretme: `test_ortamdaki_anahtar_sizmaz` (5 değişke).

Düzeltme: diff'teki `YerelCalisma._ortam()`. Yalnızca PATH ve sistem değişkenleri aktarılıyor. `HOME`, `USERPROFILE`
ve `TMP` çalışma klasörünü gösteriyor.

### B-4 · ORTA-YÜKSEK · Hatalı araç argümanı bütün görevi çökertiyor

`arac_calistir` yalnızca `AracHatasi`, `KeyError`, `FileNotFoundError`, `TypeError` ve `AttributeError` yakalıyor.
Aşağıdaki durumlar yakalanmıyor:

| Model çağrısı | İstisna |
|---|---|
| `Read`/`Edit` ikili dosya (`.png`, `.pyc`, `.db`) | `UnicodeDecodeError` |
| `Read`/`Write` bir klasör üzerinde | `PermissionError` (Windows) / `IsADirectoryError` |
| `Write` yolu NUL bayt içeriyor | `ValueError` |

`ajan.calistir` içinde `calisma.arac_calistir` bir `try` bloğuna alınmamış. İstisna `surec` katmanından
`web._yurut` katmanına kadar çıkıyor ve görev "hata" ile bitiyor. Bu güvenlik açığından çok **demoda görevi
düşürebilecek bir güvenilirlik sorunu.** Glimmer'ın bir resim ya da `.pyc` dosyasını `Read` ile açması yeterli.

Yeniden üretme: `test_bozuk_girdi_istisna_firlatmaz`, `test_ajan_ikili_dosya_okumasinda_cokmez`.

Düzeltme: diff'teki `except UnicodeDecodeError` / `except (OSError, ValueError)` blokları.

### B-5 · ORTA · Yerel kipte zaman aşımı alt süreçleri öldürmüyor: süreç sonsuza dek asılı kalabiliyor

`subprocess.run(timeout=...)` yalnızca `bash` sürecini öldürüyor. Bash'in başlattığı `python` süreci çıktı borusunu
açık tuttuğu için `communicate()` bu süreç bitene kadar bekliyor. Model `python -c "while True: pass"; echo` gibi
bir komut yazarsa `arac_calistir` **hiç dönmüyor** ve yetim süreç CPU'yu %100 kullanıyor. Bu deneme sırasında
elle gözlendi ve süreç `Stop-Process` ile kapatıldı. Arka plana atılan bir süreç (`... &`) da aynı biçimde bekletiyor.

Yeniden üretme: `test_zaman_asimi_torun_surecleri_de_keser`. Testteki yükler bilerek 6-8 saniyeyle sınırlı: 1 sn'lik
sınıra karşın ~8 sn bekleniyor.

Düzeltme: diff'te çıktı boru yerine geçici dosyaya yazılıyor; zaman aşımında `taskkill /T` (Windows) ya da
`killpg` (POSIX) ile bütün süreç ağacı öldürülüyor; okunan çıktı 4 MB ile sınırlanıyor.

Modal tarafı düşük risk taşıyor: `timeout` komutu (GNU) süreç grubunu öldürüyor, `sb.exec(timeout=sure+15)` de
üst sınır koyuyor.

### B-6 · ORTA · Boyut sınırları eksik (bellek ve arayüz)

* `Write` içeriğine sınır yok. 50 MB'lık bir yazma kabul ediliyor.
* `YerelCalisma._listele` boyuta bakmıyor (Modal tarafında `-size -200k` var). `dosyalar()` her dosyayı tamamen
  belleğe alıp SSE ile arayüze gönderiyor.
* `_calistir` çıktısının tamamı belleğe okunuyor. Kırpma ancak sonradan yapılıyor.
* `_listele` sembolik bağları da izliyor. Bağ dışarıyı gösteriyorsa `_oku` → `_tam` bunu reddediyor; yani savunma
  tutuyor (`test_dosyalar_sembolik_bagi_izlemez`).

Yeniden üretme: `test_write_boyut_siniri`.

Düzeltme: diff'teki `DOSYA_SINIRI`, `_listele` içindeki boyut ve sembolik bağ süzgeci, 4 MB'lık okuma sınırı.

### B-7 · ORTA · Web: `Host` başlığı denetlenmiyor (DNS yeniden bağlama)

Sunucu `127.0.0.1` adresini dinliyor ama `Host: kotu.example` başlığıyla gelen istekleri de kabul ediyor. DNS
yeniden bağlama saldırısında (rebinding) yabancı bir site tarayıcı üzerinden aynı kökenden geliyormuş gibi
`/api/gorev` çağırabilir. Böylece görev başlatıp bütçe harcatabilir ve olay akışını okuyabilir.

Ön uçuşsuz basit CSRF ise **tutuyor**: `text/plain`, form ve multipart gövdeler 422 alıyor
(`test_web_basit_capraz_kaynak_istegi_gorev_baslatamaz`).

Yeniden üretme: `test_web_yabanci_host_reddedilir`.

Düzeltme: diff'teki `TrustedHostMiddleware(allowed_hosts=["127.0.0.1", "localhost"])`.

### B-8 · ORTA · Web: eşzamanlı görev sınırı yok ve sahipsiz işler birikiyor

* Art arda 25 `POST /api/gorev` isteği 25 iş parçacığı açıyor: 25 Modal Sandbox, 25 Glimmer oturumu ve Spark
  harcaması. Yanlışlıkla çift tıklama ya da bir döngü bütçeyi (140 $ sınırı) hızla eritebilir.
* `ISLER[is_id]` kaydı yalnızca olay akışı sonuna kadar okunduğunda siliniyor. Kimse bağlanmazsa kayıt (son rapor
  ve bütün dosyalarla birlikte) süreç kapanana kadar bellekte kalıyor.
* `/api/ses` 10 MB denetimini gövdenin tamamını okuduktan sonra yapıyor (bellek açısından düşük risk).

Yeniden üretme: `test_web_eszamanli_gorev_siniri`, `test_web_sahipsiz_is_temizlenir`.

Düzeltme: diff'teki `AKTIF = BoundedSemaphore(2)` ile fazla istekler 429 alıyor. Sahipsiz işler için öneri:
`_yurut` bittiğinde `threading.Timer(600, ISLER.pop, (is_id, None)).start()`. Bu kısım diff'te yok ve testi xfail
olarak kalıyor.

### B-3 · DÜŞÜK (Modal) / ORTA (yerel) · `komut_denetle` kara listesi atlatılabiliyor

Aşağıdaki 16 komutun hepsi filtreden geçiyor. Hiçbiri çalıştırılmadı; yalnızca `komut_denetle` ile sınandı:
`c''url`, `cu""rl`, `c\url`, `$(echo Y3VybA== | base64 -d)`, `... | base64 -d | sh`, ters tırnak alt kabuğu,
`__import__('so'+'cket')`, `ftplib`, `smtplib`, `xmlrpc.client`, `python -m http.server`, `chr(47)` ile `/`
oluşturma, `perl -e`, `node -e`, `powershell -c` ve `a=s; b=udo; $a$b`.

Yeniden üretme: `test_komut_filtresi_atlatilamaz`.

Düzeltme: düzenli ifadeyle tam bir çözüm yok ve diff bunu düzeltmeye çalışmıyor; testler xfail olarak kalıyor.
Asıl sınır Modal Sandbox (ağ kapalı, sır yok). Yerel kipte B-2 düzeltmesi sayesinde sızacak anahtar kalmıyor.
Daha fazlası gerekirse yerel kip Docker ya da WSL içinde `--network none` ile çalıştırılabilir.

### Tutan savunmalar (yeşil testler)

* `guvenli_yol` şu yolların hepsini reddediyor: `../`, `..\`, mutlak yollar, `C:\`, `c:x`, UNC (`\\sunucu\pay`,
  `//sunucu`), `\\?\`, `\\.\pipe`, `~`, `/work/../` (24 değişke).
* `guvenli_yol`'dan geçen garip yollar (`a/../C:/x`, `file:///…`, `%2e%2e`, `con.txt`, ADS `x.txt:akis`) `_tam`
  içindeki resolve ve parents denetimine takılıyor; dışarıda dosya oluşmuyor.
* Klasör bağı (junction/symlink) üzerinden `Read`/`Write`/`Edit` ile kaçış reddediliyor.
* `Read` aracı `.env` dosyasına ulaşamıyor. `/proc/self/environ`, `../.env` ve `~/.env` filtrede reddediliyor.
* Çıktı kırpılıyor: 3 MB'lık Bash çıktısı ve 1 MB'lık dosya okuması 8000 karakterin altına iniyor. Kabuk içi sonsuz
  döngü 1 sn'de kesiliyor.
* Web: boş, 4000 karakterden uzun, yanlış tipte ve 2 MB'lık görevler 400/422 alıyor; geçersiz `kip` 400 alıyor;
  bilinmeyen iş 404 alıyor; 10 MB'ı aşan ses 400 alıyor.
* `index.html` model ve dosya içeriğini yalnızca `textContent` ile basıyor. `innerHTML` yalnızca `""` ile
  kullanılıyor, yani XSS yok.

### Notlar

* `ModalCalisma._yaz`/`_oku` sembolik bağları çözmüyor. Model Sandbox içinde `/work` dışını gösteren bir bağ
  kurabiliyor, ama Sandbox'ta sır ve ağ olmadığı için risk düşük.
* `web._yurut` istisna metnini (`f"{type(e).__name__}: {e}"`) olduğu gibi arayüze gönderiyor. Bugün bu metinlerde
  anahtar yok, ama `requests` hatalarında URL görünebilir; ileride sorgu dizesinde anahtar taşıyan bir istek
  eklenirse dikkat edilmeli.
