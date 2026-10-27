"""Bağımsız doğrulayıcı: Muse Spark, görev metninden (ajanın kodunu görmeden) arayüz sözleşmesi ve pytest kabul testleri yazar.

Yazan (Glimmer) ile doğrulayan (Spark) ayrı modellerdir. Glimmer sözleşmeyi görür, testleri çalışırken görmez;
testler ajan Done dedikten sonra çalışma alanına (her seferinde yeniden) yazılıp koşturulur.
"""
import json
import re

from usta import spark
from usta.arac import guvenli_yol

KABUL_DOSYASI = ".usta_kabul/test_kabul.py"

SOZLESME_ISTEMI = """Aşağıdaki Türkçe yazılım görevi bir kodlama ajanına verilecek; işi sonra dışarıdan testle doğrulayacağız.
Testlerin ajanın koduna bağlanabilmesi için ADLANDIRMA sözleşmesi gerekiyor: dosya adları, fonksiyon/sınıf/metot adları
ve imzaları (komut satırı programıysa çağrı biçimi).

Kurallar:
- Görev bunların hepsini zaten açıkça belirtiyorsa sözleşme gereksizdir: {{"arayuz": ""}} döndür.
- Eksik olanları en basit, en olağan biçimde seç. Davranış kuralı, hata türü, biçim ya da uç durum EKLEME ve görevdeki
  davranışı yeniden yazma; davranışı yalnızca görev metni belirler.
- Türkçe karakterlerle kısa yaz.

GÖREV:
{gorev}

Yalnızca şu JSON'u döndür: {{"arayuz": "..."}}"""

TEST_ISTEMI = """Bir kodlama ajanı aşağıdaki görevi yapıyor. Ajanın kodunu görmeyeceksin; işi dışarıdan doğrulayacak testler yaz.

GÖREV:
{gorev}

ADLANDIRMA SÖZLEŞMESİ (ajan buna uyacak; boşsa görevdeki adlar geçerlidir):
{arayuz}

İki şey üret:
1. "testler": pytest kabul testleri (tek dosya). Kurallar:
   - Dosya çalışma klasörünün alt klasöründe (.usta_kabul/) duracak; en başta şunu koy:
     import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
   - Yalnızca GÖREV metninde açıkça yazan davranışı test et. Sözleşme yalnızca adlar içindir; metinde olmayan bir
     ayrıntıyı (hata mesajı metni, belirtilmemiş biçim, varsayılan değer, dönüş türünün iç yapısı) test etme.
   - Önce görev metnindeki gereksinimleri kendi içinde tek tek çıkar (biçim kuralları, sınır değerleri, hata türleri,
     sıralama/eşitlik kuralları, yuvarlama, dosya/çıktı davranışı). HER gereksinim için en az bir test yaz; sınır
     değerlerini iki taraftan dene. Toplam 12-20 test. Her test kısa ve tek şeyi denesin; test adı gereksinimi anlatsın.
   - Komut satırı programıysa subprocess ile sys.executable kullanarak çalıştır, cwd çalışma klasörü olsun; gereken
     girdi dosyalarını tmp_path'e oluştur.
   - Ağ, rastgelelik, zaman ya da dosya sistemi dışına bağımlılık yok.
2. "cozum": Sözleşmeye uyan referans çözüm, dosya adı -> içerik sözlüğü. Ajana gösterilmez; yalnızca testlerindeki
   hatalı beklentileri (ör. yanlış hesaplanmış örnek değer) ayıklamak için testlerin kendisine karşı çalıştırılır.

Yalnızca şu JSON'u döndür (başka metin yok):
{{"testler": "...", "cozum": {{"dosya.py": "..."}}}}"""


def _json_ayikla(metin: str) -> dict:
    metin = (metin or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", metin, re.S)
    if m:
        metin = m.group(1)
    bas, son = metin.find("{"), metin.rfind("}")
    return json.loads(metin[bas:son + 1])


def sozlesme_yaz(gorev: str, deneme: int = 3) -> dict:
    """{'arayuz', 'maliyet'} döndürür. Hızlı olsun diye düşük akıl yürütme düzeyiyle çağrılır."""
    maliyet = 0.0
    for _ in range(deneme):
        m = spark.sohbet([{"role": "user", "content": SOZLESME_ISTEMI.format(gorev=gorev)}],
                         max_tokens=8000, reasoning_effort="low")
        maliyet += m["_maliyet"]
        try:
            return {"arayuz": (_json_ayikla(m.get("content"))["arayuz"] or "").strip(), "maliyet": maliyet}
        except (ValueError, KeyError, AttributeError, json.JSONDecodeError):
            continue
    raise RuntimeError("Spark arayüz sözleşmesi üretemedi")


def kabul_testleri_yaz(gorev: str, arayuz: str, deneme: int = 3, suz: bool = True) -> dict:
    """{'testler', 'iptal', 'maliyet'} döndürür. iptal: referans çözümün de geçemediği (hatalı sayılan) testler."""
    maliyet, son_hata = 0.0, None
    for _ in range(deneme):
        m = spark.sohbet([{"role": "user", "content": TEST_ISTEMI.format(gorev=gorev, arayuz=arayuz)}],
                         max_tokens=16000, reasoning_effort="medium")
        maliyet += m["_maliyet"]
        try:
            veri = _json_ayikla(m.get("content"))
            testler = veri["testler"]
            compile(testler, KABUL_DOSYASI, "exec")
            if "def test_" not in testler:
                raise ValueError("test fonksiyonu yok")
            # cozum yürütücüye asla gösterilmez; yalnızca testleri (ve d kipinde inceleme testlerini) sınamak için tutulur.
            kabul = {"testler": testler, "maliyet": maliyet, "iptal": [], "cozum": veri.get("cozum") or {}}
            if not suz:
                return kabul
            kabul["iptal"], toplam = referansla_suz(testler, veri.get("cozum") or {})
            if toplam and len(kabul["iptal"]) <= toplam // 2:
                return kabul
            son_hata = ValueError(f"referans çözüm testlerin çoğunu geçemedi ({len(kabul['iptal'])}/{toplam})")
        except (ValueError, KeyError, SyntaxError, json.JSONDecodeError) as e:
            son_hata = e
    raise RuntimeError(f"Spark geçerli kabul testi üretemedi: {son_hata}")


def _pytest_komutu(iptal: list) -> str:
    secim = " ".join(f"--deselect {KABUL_DOSYASI}::{t}" for t in iptal)
    return f"python -m pytest -q -rf -p no:cacheprovider {KABUL_DOSYASI} {secim}"


def referansla_suz(testler: str, cozum: dict) -> tuple[list, int]:
    """Testleri Spark'ın referans çözümüne karşı ayrı bir sandbox'ta çalıştırır; kalan test adlarını ve toplamı döndürür."""
    from usta.arac import calisma_ac
    with calisma_ac() as c:
        for yol, icerik in cozum.items():
            c._yaz(guvenli_yol(yol), icerik)
        c._yaz(KABUL_DOSYASI, testler)
        _, cikti = c._calistir(_pytest_komutu([]) + " 2>&1 | tail -n 60", 120)
    kalan = sorted(set(re.findall(r"(?:FAILED|ERROR) \S*::(\w+)", cikti)))
    toplam = sum(int(x) for x in re.findall(r"(\d+) (?:passed|failed|error)", cikti))
    return kalan, toplam


def kabul_testlerini_calistir(calisma, testler: str, iptal: list | None = None) -> dict:
    """Testleri yazıp çalıştırır (iptal edilenler hariç). {'gecti', 'toplam', 'basarili', 'cikti'} döndürür."""
    calisma._yaz(KABUL_DOSYASI, testler)
    kod, cikti = calisma._calistir(_pytest_komutu(iptal or []) + " 2>&1 | tail -n 80", 120)
    gecen = sum(int(x) for x in re.findall(r"(\d+) passed", cikti))
    kalan = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", cikti))
    toplam = gecen + kalan
    return {"gecti": toplam > 0 and kalan == 0, "toplam": toplam, "basarili": gecen, "cikti": cikti}


HAKEM_ISTEMI = """Bir kodlama ajanının işi bağımsız kabul testleriyle denetlendi ve bazı testler kaldı. Kalan testler ajana
"düzelt" diye geri verilecek. Ama testi yazan model görev metnini yanlış ya da tek taraflı yorumlamış olabilir; o zaman
ajanı doğru kodu bozmaya zorlarız. Senin işin hakemlik: her kalan test için görev metnine bak ve karar ver.

GÖREV:
{gorev}

KALAN TESTLERİN KODU:
{test_kodu}

TEST ÇIKTISI:
{cikti}

Her kalan test için karar:
- "gerekli": görev metni bu beklentiyi AÇIKÇA ve tek anlamlı olarak istiyor; ajanın kodu yanlış.
- "belirsiz": görev metni bu ayrıntıyı belirtmiyor ya da birden çok makul okuması var.
- "hatali": testin beklentisi görev metniyle çelişiyor ya da test kendi içinde yanlış.
Emin değilsen "belirsiz" de. Gerekçe tek kısa Türkçe cümle olsun.

Yalnızca JSON döndür: {{"kararlar": [{{"test": "test_adi", "karar": "gerekli|belirsiz|hatali", "gerekce": "..."}}]}}"""


def kalan_testler(cikti: str) -> list:
    return sorted(set(re.findall(r"(?:FAILED|ERROR) \S*::(\w+)", cikti)))


def _test_kaynagi(testler: str, adlar: list) -> str:
    """Kalan test fonksiyonlarının kaynağını (ve yardımcıların tamamını görmek için dosyanın başını) çıkarır."""
    parcalar = [testler.split("\ndef test_", 1)[0][:2500]]
    for ad in adlar:
        m = re.search(rf"^def {ad}\(.*?(?=^def |^class |\Z)", testler, re.S | re.M)
        if m:
            parcalar.append(m.group(0).strip())
    return "\n\n".join(parcalar)


def hakem(gorev: str, testler: str, cikti: str) -> dict:
    """Kalan testleri görev metnine göre sınıflandırır. {'kararlar': [...], 'maliyet'} döndürür.
    Ayrıştırılamazsa her test 'gerekli' sayılır (doğrulamayı gevşetmemek için)."""
    adlar = kalan_testler(cikti)
    if not adlar:
        return {"kararlar": [], "maliyet": 0.0}
    m = spark.sohbet([{"role": "user", "content": HAKEM_ISTEMI.format(
        gorev=gorev, test_kodu=_test_kaynagi(testler, adlar), cikti=cikti[-4000:])}],
        max_tokens=12000, reasoning_effort="medium")
    try:
        kararlar = {k["test"]: k for k in _json_ayikla(m.get("content"))["kararlar"]
                    if k.get("karar") in ("gerekli", "belirsiz", "hatali")}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        kararlar = {}
    sonuc = [kararlar.get(ad, {"test": ad, "karar": "gerekli", "gerekce": "hakem kararı okunamadı"}) for ad in adlar]
    return {"kararlar": sonuc, "maliyet": m["_maliyet"]}


INCELEME_ISTEMI = """Bir kodlama ajanı aşağıdaki görevi yaptı ve bağımsız kabul testlerinin hepsini geçti. Ama kabul testleri
her gereksinimi denemiyor olabilir. Senin işin kanıtlı kod incelemesi.

GÖREV:
{gorev}

AJANIN KODU:
{kod}

ZATEN KOŞAN KABUL TESTLERİNİN ADLARI:
{mevcut}

Görev metnindeki gereksinimleri tek tek kodla karşılaştır. Kodun görev metnini AÇIKÇA ihlal ettiğinden şüphelendiğin
her nokta için (en çok 6) bir pytest testi yaz: test, ihlal varsa kalmalı, görevi doğru yapan bir kodda geçmeli.
Kurallar:
- Yalnızca görev metninde açıkça yazan davranışı test et; üslup, verimlilik ya da metinde olmayan ayrıntı yok.
- Test adları test_inceleme_ ile başlasın. Dosyanın başına şunu koy:
  import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
  ve gereken importları ekle. Komut satırı programları için subprocess + sys.executable, girdi dosyaları tmp_path'e.
- Hiç şüphen yoksa boş döndür.

Yalnızca JSON döndür: {{"testler": "..."}}  (şüphe yoksa {{"testler": ""}})"""

INCELEME_DOSYASI = ".usta_kabul/test_inceleme.py"


def inceleme_testleri(gorev: str, kod: dict, mevcut_adlar: list) -> dict:
    """Spark, görev + ajanın kodunu okuyup şüpheli ihlaller için test yazar. {'testler', 'maliyet'}."""
    metin = "\n\n".join(f"### {yol}\n{icerik[:12000]}" for yol, icerik in kod.items()
                         if not yol.startswith(".usta_kabul/") and not yol.startswith("test_"))[:40000]
    m = spark.sohbet([{"role": "user", "content": INCELEME_ISTEMI.format(
        gorev=gorev, kod=metin or "(dosya yok)", mevcut=", ".join(mevcut_adlar) or "-")}],
        max_tokens=16000, reasoning_effort="medium")
    try:
        testler = (_json_ayikla(m.get("content"))["testler"] or "").strip()
        if testler:
            compile(testler, INCELEME_DOSYASI, "exec")
    except (ValueError, KeyError, SyntaxError, TypeError, json.JSONDecodeError):
        testler = ""
    return {"testler": testler if "def test_" in testler else "", "maliyet": m["_maliyet"]}


def _dosyada_kalanlar(calisma, dosya: str, testler: str) -> tuple[set, set]:
    """Test dosyasını çalıştırır; (kalan, geçen) test adlarını döndürür."""
    calisma._yaz(dosya, testler)
    _, cikti = calisma._calistir(f"python -m pytest -q -rA -p no:cacheprovider {dosya} 2>&1 | tail -n 80", 120)
    kalan = set(re.findall(r"(?:FAILED|ERROR) \S*::(\w+)", cikti))
    gecen = set(re.findall(r"PASSED \S*::(\w+)", cikti))
    return kalan, gecen


def inceleme_testlerini_sina(calisma, testler: str, cozum: dict) -> list:
    """Kanıt şartı: ajanın kodunda KALAN ve referans çözümde GEÇEN inceleme testlerinin adları."""
    from usta.arac import calisma_ac
    ajanda_kalan, _ = _dosyada_kalanlar(calisma, INCELEME_DOSYASI, testler)
    if not ajanda_kalan or not cozum:
        return []
    with calisma_ac() as ref:
        for yol, icerik in cozum.items():
            ref._yaz(guvenli_yol(yol), icerik)
        _, refte_gecen = _dosyada_kalanlar(ref, INCELEME_DOSYASI, testler)
    return sorted(ajanda_kalan & refte_gecen)
