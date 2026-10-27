"""Bağımsız doğrulayıcı: Muse Spark, görev metninden (ajanın kodunu görmeden) arayüz sözleşmesi ve pytest kabul testleri yazar.

Yazan (Glimmer) ile doğrulayan (Spark) ayrı modellerdir. Glimmer sözleşmeyi görür, testleri çalışırken görmez;
testler ajan Done dedikten sonra çalışma alanına (her seferinde yeniden) yazılıp koşturulur.
"""
import json
import re

from usta import spark
from usta.arac import guvenli_yol

KABUL_DOSYASI = ".usta_kabul/test_kabul.py"

SOZLESME_ISTEMI = """Aşağıdaki Türkçe yazılım görevi bir kodlama ajanına verilecek. Sen işi dışarıdan doğrulayacaksın;
önce ajanın uyması gereken kısa bir arayüz sözleşmesi yaz (Türkçe karakterlerle düzgün Türkçe): dosya adları,
fonksiyon/sınıf adları ve imzaları, dönüş türleri, hata durumlarında ne olacağı. Görev bunları zaten belirtiyorsa aynen
koru; belirtmiyorsa makul ve basit seçimler yap. Görevde olmayan yeni gereksinim ekleme. Python 3.12 standart
kütüphanesi dışında bağımlılık yok.

GÖREV:
{gorev}

Yalnızca şu JSON'u döndür: {{"arayuz": "..."}}"""

TEST_ISTEMI = """Bir kodlama ajanı aşağıdaki görevi yapıyor. Ajanın kodunu görmeyeceksin; işi dışarıdan doğrulayacak testler yaz.

GÖREV:
{gorev}

ARAYÜZ SÖZLEŞMESİ (ajan buna uyacak):
{arayuz}

İki şey üret:
1. "testler": pytest kabul testleri (tek dosya). Kurallar:
   - Dosya çalışma klasörünün alt klasöründe (.usta_kabul/) duracak; en başta şunu koy:
     import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
   - Yalnızca görevin açıkça istediği ya da sözleşmede yazan davranışı test et; belirsiz ayrıntıyı test etme.
   - Normal durumlar + görevde geçen uç durumlar; 5-12 test. Her test kısa ve tek şeyi denesin.
   - Komut satırı programıysa subprocess ile sys.executable kullanarak çalıştır, cwd çalışma klasörü olsun.
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
            return {"arayuz": _json_ayikla(m.get("content"))["arayuz"].strip(), "maliyet": maliyet}
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
            kabul = {"testler": testler, "maliyet": maliyet, "iptal": []}
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
    from usta.arac import ModalCalisma
    with ModalCalisma(zaman_asimi=600) as c:
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
