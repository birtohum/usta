"""5 görevle Usta'yı (kip c) uçtan uca dener; sonuçları kayitlar/uctan_uca.json'a yazar.

    python betikler/uctan_uca.py
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usta import glimmer, spark, surec  # noqa: E402
from usta.arac import calisma_ac  # noqa: E402

GOREVLER = [
    "tckn.py içinde gecerli_tckn(no: str) -> bool yaz: 11 haneli T.C. kimlik numarasının resmî algoritmaya "
    "(ilk hane 0 olamaz, 10. ve 11. hane kontrol basamakları) uygunluğunu denetlesin.",
    "iban.py içinde tr_iban_gecerli_mi(iban: str) -> bool yaz: boşlukları yok sayan, TR ile başlayan 26 karakterlik "
    "IBAN'ı mod-97 kuralıyla doğrulasın.",
    "yazi.py içinde sayiyi_yaziya(n: int) -> str yaz: 0 ile 999999 arasındaki sayıyı Türkçe yazıya çevirsin "
    "(ör. 1234 -> 'bin iki yüz otuz dört', 1000 -> 'bin', 0 -> 'sıfır'). Kelimeler tek boşlukla ayrılsın.",
    "rapor.py adında komut satırı programı yaz: `python rapor.py satislar.csv` ile tarih,urun,tutar sütunlu CSV'yi "
    "okuyup her ay (YYYY-AA) için toplam tutarı, aylar sıralı biçimde 'YYYY-AA: toplam' satırları olarak yazdırsın. "
    "Tutarlar iki ondalıklı gösterilsin.",
    "sirala.py içinde turkce_sirala(kelimeler: list[str]) -> list[str] yaz: kelimeleri Türk alfabesine göre "
    "(a b c ç d e f g ğ h ı i j k l m n o ö p r s ş t u ü v y z) büyük/küçük harf duyarsız sıralasın.",
]


def tek(gorev: str) -> dict:
    with calisma_ac() as c:
        try:
            r = surec.gorevi_yap(gorev, c, kip="c")
            r["dosyalar"] = list(c.dosyalar())
        except Exception as e:
            r = {"hata": f"{type(e).__name__}: {e}"}
    r["gorev"] = gorev
    print(f"{'GEÇTİ' if r.get('kabul_gecti') else 'KALDI'} | turlar={r.get('turlar')} | adım={r.get('adim')} | {gorev[:50]}",
          flush=True)
    return r


def main():
    glimmer.hazir_bekle()
    with ThreadPoolExecutor(5) as ex:
        sonuclar = list(ex.map(tek, GOREVLER))
    cikis = Path(__file__).resolve().parent.parent / "kayitlar" / "uctan_uca.json"
    cikis.parent.mkdir(exist_ok=True)
    cikis.write_text(json.dumps(sonuclar, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"geçen: {sum(bool(r.get('kabul_gecti')) for r in sonuclar)}/{len(sonuclar)} | "
          f"Spark toplam: {spark.butce()['toplam_usd']:.4f} $")


if __name__ == "__main__":
    main()
