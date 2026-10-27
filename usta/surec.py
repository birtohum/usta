"""Usta'nın uçtan uca süreci ve karşılaştırma kipleri.

  a — Glimmer tek başına: yazar, kendi isteğine göre dener.
  b — Glimmer + kendi testleri: kendi pytest testlerini yazıp geçene kadar düzeltmesi istenir.
  c — Usta: b + Spark'ın bağımsız kabul testleri; kalan test çıktısı Glimmer'a verilir, geçene ya da tur sınırına kadar.
"""
import time

from usta import ajan, dogrulayici

SISTEM_A = """Sen Türkçe konuşan bir yazılım ajanısın. Görevi bir çalışma klasöründe araçlarla yaparsın: Write, Read, Edit, Bash, Done.
Yalnızca göreli yollar kullan. İnternet yok, paket kuramazsın (Python 3.12 standart kütüphanesi var).
Bitirdiğinde Done aracını kısa bir Türkçe özetle çağır."""

SISTEM_B = ajan.SISTEM + """
- Görevin istediği davranış için kendi pytest testlerini test_*.py dosyalarına yaz, `python -m pytest -q` ile çalıştır
  ve hepsi geçene kadar kodu düzelt. Done'ı ancak testlerin geçtiğini gördükten sonra çağır."""

DUZELTME = """Bağımsız kabul testleri (görev metninden ayrı bir model tarafından, senin kodunu görmeden yazıldı) çalıştırıldı:
{basarili}/{toplam} test geçti.

Çıktı:
{cikti}

Kodu düzelt. Test dosyasını değiştirme: {dosya} her çalıştırmada yeniden yazılır (okuyabilirsin).
Bir test görev metniyle açıkça çelişiyorsa görev metnine uy ve bunu Done özetinde belirt. Bitince Done çağır."""


def gorevi_yap(gorev: str, calisma, kip: str = "c", azami_tur: int = 3, azami_adim: int = 20,
               olay=lambda tur, veri: None, kabul: dict | None = None) -> dict:
    """Görevi seçilen kipte yürütür. kabul verilirse (önceden üretilmiş sözleşme+testler) Spark yeniden çağrılmaz."""
    bas = time.time()
    rapor = {"kip": kip, "turlar": [], "spark_usd": 0.0}
    gorev_metni = gorev

    if kip == "c":
        if kabul is None:
            olay("asama", "Spark arayüz sözleşmesi ve kabul testlerini yazıyor")
            kabul = dogrulayici.kabul_testleri_yaz(gorev)
            rapor["spark_usd"] += kabul["maliyet"]
        rapor["arayuz"] = kabul["arayuz"]
        rapor["iptal_edilen_test"] = kabul.get("iptal", [])
        olay("sozlesme", kabul["arayuz"])
        gorev_metni = f"{gorev}\n\nArayüz sözleşmesi (buna uy):\n{kabul['arayuz']}"

    sistem = {"a": SISTEM_A, "b": SISTEM_B, "c": SISTEM_B}[kip]
    olay("asama", "Glimmer görevi yürütüyor")
    s = ajan.calistir(gorev_metni, calisma, azami_adim=azami_adim, olay=olay, sistem=sistem)
    toplam_adim, token = s["adim"], dict(s["token"])

    if kip == "c":
        for tur in range(1, azami_tur + 1):
            olay("asama", f"Kabul testleri çalışıyor (tur {tur})")
            sonuc = dogrulayici.kabul_testlerini_calistir(calisma, kabul["testler"], kabul.get("iptal"))
            rapor["turlar"].append({k: sonuc[k] for k in ("gecti", "toplam", "basarili")})
            olay("test", {"tur": tur, **sonuc})
            if sonuc["gecti"] or tur == azami_tur:
                break
            s["mesajlar"].append({"role": "user", "content": DUZELTME.format(
                basarili=sonuc["basarili"], toplam=sonuc["toplam"], cikti=sonuc["cikti"][-4000:],
                dosya=dogrulayici.KABUL_DOSYASI)})
            olay("asama", f"Glimmer düzeltiyor (tur {tur + 1})")
            s = ajan.calistir(gorev_metni, calisma, azami_adim=min(azami_adim, 12), gecmis=s["mesajlar"], olay=olay)
            toplam_adim += s["adim"]
            token["girdi"] += s["token"]["girdi"]
            token["cikti"] += s["token"]["cikti"]
        rapor["kabul_gecti"] = rapor["turlar"][-1]["gecti"]

    rapor.update({"ozet": s["ozet"], "adim": toplam_adim, "glimmer_token": token, "sure_sn": round(time.time() - bas, 1),
                  "kabul": kabul})
    return rapor
