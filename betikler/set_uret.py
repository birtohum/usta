"""Değerlendirme setini üretir: Muse Spark Türkçe görevler, gizli testler ve referans çözümler yazar.

Bir görev sete ancak referans çözüm, ağı kapalı Modal Sandbox'ta gizli testlerin hepsini geçerse girer
(hatalı ya da çelişkili testleri ayıklamak için). Referans çözüm sette saklanmaz; ajanlara hiçbir kip gösterilmez.

    python betikler/set_uret.py --hedef 40                    -> veri/degerlendirme.jsonl (kolay)
    python betikler/set_uret.py --zorluk zor --cikis veri/zor.jsonl
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usta import spark  # noqa: E402
from usta.arac import calisma_ac  # noqa: E402
from usta.dogrulayici import _json_ayikla  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
CIKIS = KOK / "veri" / "degerlendirme.jsonl"
GIZLI_DOSYA = ".gizli/test_gizli.py"

KATEGORILER = [
    "Türkçe metin işleme (Türkçe harfler, büyük/küçük harf, hece, ek, sıralama, sayı/yazı)",
    "küçük işletme hesapları (KDV, fatura, taksit, indirim, stok, kur dönüşümü, yuvarlama)",
    "tarih ve saat (iş günü, resmî tatil listesi parametre olarak verilir, süre hesabı, biçim dönüşümü)",
    "dosya ve komut satırı (CSV/JSON okuma, rapor yazdırma, argümanlar, hata mesajları)",
    "doğrulama ve ayrıştırma (TC kimlik, IBAN, telefon, plaka, e-posta, adres biçimi)",
    "veri yapıları ve algoritmalar (kuyruk, önbellek, arama, gruplama, birleştirme, durum makinesi)",
]

ZORLUK = {
    "kolay": "küçük-orta zorlukta",
    "zor": ("ZOR (güçlü bir kodlama modelinin bile ilk denemede bir ayrıntıyı kaçırabileceği) ve 2-6 cümle yerine 5-10 cümlelik; "
            "her görevde en az 6 ayrı, açıkça yazılmış gereksinim olsun (biçim kuralları, sınır değerler, hata türleri, sıralama ve "
            "eşitlik kuralları, yuvarlama). Tercihen durum tutan bir sınıf, birden çok fonksiyon ya da birden çok bayraklı komut "
            "satırı programı olsun"),
}

GOREV_ISTEMI = """Bir Türkçe kodlama ajanını değerlendirmek için {n} farklı {zorluk} Python görevi yaz.
Kategori: {kategori}

Her görev:
- Türkçe, gerçek bir ihtiyaç gibi (Türkiye'deki geliştirici ya da küçük işletme bağlamı).
- Dosya adını ve fonksiyon/sınıf imzasını AÇIKÇA belirtsin (ör. "fatura.py içinde kdv_ekle(tutar: float, oran: int) -> float");
  komut satırı programıysa çağrı biçimini ve çıktı biçimini tam belirtsin.
- Beklenen davranış ve önemli uç durumlar (geçersiz girdi -> hangi hata ya da değer) açık olsun; yoruma yer bırakma.
- Yalnızca Python 3.12 standart kütüphanesi; ağ, rastgelelik, şimdiki zaman yok.
- Birbirinin kopyası olmasın.

Yalnızca JSON döndür: {{"gorevler": ["...", "..."]}}"""

TEST_ISTEMI = """Aşağıdaki Python görevi için iki şey yaz:
1. "cozum": Görevi eksiksiz yerine getiren referans çözüm. Dosya adı -> içerik sözlüğü (ör. {{"fatura.py": "..."}}).
2. "testler": Gizli değerlendirme testleri, tek pytest dosyası. Kurallar:
   - Dosya çalışma klasörünün alt klasöründe (.gizli/) duracak; en başta şunu koy:
     import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
   - Yalnızca görev metninde AÇIKÇA yazan davranışı test et; metinde olmayan bir ayrıntıyı (mesaj metni, ek alanlar) test etme.
   - {test_sayisi} test: normal durumlar + görevde geçen her uç durum ve gereksinim.
   - Komut satırı programıysa subprocess ile sys.executable kullan, cwd çalışma klasörü; gereken girdi dosyalarını
     testin içinde tmp_path'e oluştur ve yolu argüman olarak ver.

GÖREV:
{gorev}

Yalnızca JSON döndür: {{"cozum": {{"dosya.py": "..."}}, "testler": "..."}}"""


def gorev_listesi(n_kategori: int, zorluk: str) -> list:
    gorevler = []
    for k in KATEGORILER:
        m = spark.sohbet([{"role": "user", "content": GOREV_ISTEMI.format(n=n_kategori, kategori=k, zorluk=ZORLUK[zorluk])}],
                         max_tokens=16000, temperature=0.8, reasoning_effort="medium")
        try:
            gorevler += [(k, g) for g in _json_ayikla(m["content"])["gorevler"]]
        except Exception as e:
            print("görev listesi okunamadı:", k, e)
    return gorevler


def dogrula(kg) -> dict | None:
    kategori, gorev, test_sayisi = kg
    try:
        m = spark.sohbet([{"role": "user", "content": TEST_ISTEMI.format(gorev=gorev, test_sayisi=test_sayisi)}],
                         max_tokens=24000, reasoning_effort="medium")
        veri = _json_ayikla(m["content"])
        compile(veri["testler"], GIZLI_DOSYA, "exec")
        with calisma_ac() as c:
            for yol, icerik in veri["cozum"].items():
                c._yaz(yol, icerik)
            c._yaz(GIZLI_DOSYA, veri["testler"])
            kod, cikti = c._calistir(f"python -m pytest -q -p no:cacheprovider {GIZLI_DOSYA} 2>&1 | tail -n 5", 120)
    except Exception as e:
        print("ELENDİ (hata):", type(e).__name__, gorev[:60])
        return None
    son = cikti.strip().splitlines()[-1] if cikti.strip() else ""
    if "passed" not in son or "failed" in son or "error" in son:
        print("ELENDİ (referans geçmedi):", son, "|", gorev[:60])
        return None
    print("ALINDI:", son, "|", gorev[:60])
    return {"kategori": kategori, "gorev": gorev, "gizli_testler": veri["testler"], "referans_sonuc": son}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hedef", type=int, default=40)
    ap.add_argument("--kategori_basina", type=int, default=9)
    ap.add_argument("--zorluk", choices=list(ZORLUK), default="kolay")
    ap.add_argument("--cikis", default=str(CIKIS))
    a = ap.parse_args()
    test_sayisi = "6-12" if a.zorluk == "kolay" else "12-20"
    adaylar = [(k, g, test_sayisi) for k, g in gorev_listesi(a.kategori_basina, a.zorluk)]
    print(f"{len(adaylar)} aday görev")
    with ThreadPoolExecutor(8) as ex:
        alinan = [r for r in ex.map(dogrula, adaylar) if r]
    # Kategoriler dengeli kalsın: sırayla birer birer seç
    secilen, kovalar = [], {k: [r for r in alinan if r["kategori"] == k] for k in KATEGORILER}
    while len(secilen) < a.hedef and any(kovalar.values()):
        for k in KATEGORILER:
            if kovalar[k] and len(secilen) < a.hedef:
                secilen.append(kovalar[k].pop(0))
    cikis = Path(a.cikis)
    cikis.parent.mkdir(exist_ok=True)
    with cikis.open("w", encoding="utf-8") as f:
        for i, r in enumerate(secilen):
            f.write(json.dumps({"id": f"g{i + 1:02d}", **r}, ensure_ascii=False) + "\n")
    print(f"{len(alinan)}/{len(adaylar)} görev referans süzgecinden geçti; {len(secilen)} görev yazıldı -> {cikis}")
    print(f"Spark toplam: {spark.butce()['toplam_usd']:.4f} $")


if __name__ == "__main__":
    main()
