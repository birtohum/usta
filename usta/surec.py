"""Usta'nın uçtan uca süreci ve karşılaştırma kipleri.

  a — yürütücü tek başına: yazar, kendi isteğine göre dener.
  b — yürütücü + kendi testleri: kendi pytest testlerini yazıp geçene kadar düzeltmesi istenir.
  c — Usta: b + Spark'ın bağımsız kabul testleri; kalan test çıktısı yürütücüye verilir, geçene ya da tur sınırına kadar.
      Bir düzeltme turu önceden geçen bir testi bozarsa (gerileme) dosyalar tur öncesine geri alınır.
  d — c + kanıtlı kod incelemesi: kabul testleri geçince Spark görevi ve KODU okuyup şüpheli ihlaller için test yazar;
      yalnızca ajanın kodunda kalan ve Spark'ın (ajana gösterilmeyen) referans çözümünde geçen testler dayatılır.
      Bu adımda doğrulayıcı kodu görür; bağımsızlık c'deki kadar değildir.

Yürütücü: "glimmer" (Muse Glimmer, Modal'da vLLM) ya da "spark" (Muse Spark, Meta Model API). Doğrulayıcı her zaman ayrı
Spark çağrılarıdır ve yürütücünün kodunu görmez.
"""
import re
import time
from concurrent.futures import ThreadPoolExecutor

from usta import ajan, dogrulayici

_havuz = ThreadPoolExecutor(8)

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


def _goruntu(calisma) -> dict:
    return {k: v for k, v in calisma.dosyalar().items() if not k.startswith(dogrulayici.KABUL_DOSYASI.split("/")[0])}


def _geri_al(calisma, goruntu: dict) -> None:
    for yol in set(_goruntu(calisma)) - set(goruntu):
        calisma._sil(yol)
    for yol, icerik in goruntu.items():
        calisma._yaz(yol, icerik)


def gorevi_yap(gorev: str, calisma, kip: str = "c", azami_tur: int = 3, azami_adim: int = 20,
               olay=lambda tur, veri: None, kabul: dict | None = None, hakem: bool = True,
               yurutucu: str = "glimmer") -> dict:
    """Görevi seçilen kipte yürütür. kabul verilirse (önceden üretilmiş sözleşme+testler) Spark yeniden çağrılmaz."""
    bas = time.time()
    rapor = {"kip": kip, "yurutucu": yurutucu, "turlar": [], "spark_usd": 0.0}
    ad = "Glimmer" if yurutucu == "glimmer" else "Spark (yürütücü)"
    gorev_metni = gorev

    gelecek = None
    if kip in ("c", "d"):
        if kabul is None:
            olay("asama", "Spark arayüz sözleşmesini yazıyor")
            sozlesme = dogrulayici.sozlesme_yaz(gorev)
            rapor["spark_usd"] += sozlesme["maliyet"]
            arayuz = sozlesme["arayuz"]
            # Testler ve referans süzgeci, yürütücü çalışırken paralelde hazırlanır (yürütücü testleri görmez).
            gelecek = _havuz.submit(dogrulayici.kabul_testleri_yaz, gorev, arayuz)
        else:
            arayuz = kabul["arayuz"]
        rapor["arayuz"] = arayuz
        if arayuz:
            olay("sozlesme", arayuz)
            gorev_metni = f"{gorev}\n\nAdlandırma sözleşmesi (dosya/fonksiyon adları ve imzalar için buna uy):\n{arayuz}"

    sistem = {"a": SISTEM_A, "b": SISTEM_B, "c": SISTEM_B, "d": SISTEM_B}[kip]
    olay("asama", f"{ad} görevi yürütüyor")
    s = ajan.calistir(gorev_metni, calisma, azami_adim=azami_adim, olay=olay, sistem=sistem, yurutucu=yurutucu)
    toplam_adim, token = s["adim"], dict(s["token"])
    yurutucu_usd = s.get("usd", 0.0)

    if kip in ("c", "d"):
        if gelecek is not None:
            olay("asama", "Spark'ın bağımsız kabul testleri bekleniyor")
            try:
                kabul = {"arayuz": arayuz, **gelecek.result()}
            except Exception as e:
                # Doğrulayıcı test üretemezse sonuç "doğrulanamadı" olarak raporlanır; geçti sayılmaz.
                olay("hata", f"Bağımsız testler üretilemedi: {e}")
                rapor.update({"kabul_gecti": False, "dogrulanamadi": True, "ozet": s["ozet"], "adim": toplam_adim,
                              "yurutucu_token": token, "yurutucu_usd": yurutucu_usd,
                              "sure_sn": round(time.time() - bas, 1), "kabul": None})
                return rapor
            rapor["spark_usd"] += kabul["maliyet"]
        olay("kabul", {"testler": dogrulayici.testler_metni(kabul["testler"]), "iptal": kabul["iptal"]})
        iptal = list(kabul.get("iptal", []))
        testler = dogrulayici._dosyalar(kabul["testler"])
        rapor["kabul_yazar"] = kabul.get("yazar")
        rapor["mutasyon"] = kabul.get("mutasyon")
        rapor["hakem"], rapor["geri_alma"], rapor["inceleme"] = [], 0, None
        inceleme_yapildi = kip != "d"
        onceki = None   # (anlık görüntü, kalan test adları) — bir önceki turun sonu
        for tur in range(1, azami_tur + 1):
            olay("asama", f"Kabul testleri çalışıyor (tur {tur})")
            sonuc = dogrulayici.kabul_testlerini_calistir(calisma, testler, iptal)
            kalan = set(dogrulayici.kalan_testler(sonuc["cikti"], testler))
            if onceki is not None and kalan - onceki[1]:
                # Gerileme: düzeltme turu önceden geçen bir testi bozdu -> tur öncesine dön ve dur.
                olay("asama", f"Gerileme: {', '.join(sorted(kalan - onceki[1]))} bozuldu; değişiklikler geri alındı")
                _geri_al(calisma, onceki[0])
                rapor["geri_alma"] += 1
                sonuc = dogrulayici.kabul_testlerini_calistir(calisma, testler, iptal)
                rapor["turlar"].append({k: sonuc[k] for k in ("gecti", "toplam", "basarili")} | {"geri_alindi": True})
                olay("test", {"tur": tur, **sonuc})
                break
            if not sonuc["gecti"] and hakem:
                # Hakem: kalan testlerden yalnızca görev metninin açıkça istediği beklentiler yürütücüye geri gider.
                olay("asama", "Spark hakem kalan testleri görev metnine göre inceliyor")
                h = dogrulayici.hakem(gorev, testler, sonuc["cikti"])
                rapor["spark_usd"] += h["maliyet"]
                rapor["hakem"] += [{**k, "tur": tur} for k in h["kararlar"]]
                olay("hakem", h["kararlar"])
                dusen = [k["test"] for k in h["kararlar"] if k["karar"] != "gerekli"]
                if dusen:
                    iptal += dusen
                    sonuc = dogrulayici.kabul_testlerini_calistir(calisma, testler, iptal)
                    kalan = set(dogrulayici.kalan_testler(sonuc["cikti"], testler))
            if sonuc["gecti"] and not inceleme_yapildi:
                # d kipi: kabul testleri geçti -> kanıtlı kod incelemesi (bir kez).
                inceleme_yapildi = True
                olay("asama", "Spark kodu inceliyor (kanıtlı inceleme)")
                inc = dogrulayici.inceleme_testleri(gorev, _goruntu(calisma), dogrulayici.test_kimlikleri(testler))
                rapor["spark_usd"] += inc["maliyet"]
                kanitli = dogrulayici.inceleme_testlerini_sina(calisma, inc["testler"], kabul.get("cozum") or {}) \
                    if inc["testler"] else []
                rapor["inceleme"] = {"yazilan": len(re.findall(r"def test_", inc["testler"])), "kanitli": kanitli}
                olay("inceleme", rapor["inceleme"])
                if kanitli:
                    # İnceleme dosyası eklenir; kanıtlanmayan inceleme testleri seçim dışı bırakılır.
                    testler[dogrulayici.INCELEME_DOSYASI] = inc["testler"]
                    iptal += [t for t in dogrulayici.test_kimlikleri({dogrulayici.INCELEME_DOSYASI: inc["testler"]})
                              if t not in kanitli]
                    sonuc = dogrulayici.kabul_testlerini_calistir(calisma, testler, iptal)
                    kalan = set(dogrulayici.kalan_testler(sonuc["cikti"], testler))
            rapor["turlar"].append({k: sonuc[k] for k in ("gecti", "toplam", "basarili")})
            olay("test", {"tur": tur, **sonuc})
            if sonuc["gecti"] or tur == azami_tur:
                break
            onceki = (_goruntu(calisma), kalan)
            s["mesajlar"].append({"role": "user", "content": DUZELTME.format(
                basarili=sonuc["basarili"], toplam=sonuc["toplam"], cikti=sonuc["cikti"][-4000:],
                dosya=dogrulayici.KABUL_DOSYASI)})
            olay("asama", f"{ad} düzeltiyor (tur {tur + 1})")
            s = ajan.calistir(gorev_metni, calisma, azami_adim=min(azami_adim, 12), gecmis=s["mesajlar"], olay=olay,
                              yurutucu=yurutucu)
            toplam_adim += s["adim"]
            token["girdi"] += s["token"]["girdi"]
            token["cikti"] += s["token"]["cikti"]
            yurutucu_usd += s.get("usd", 0.0)
        rapor["iptal_edilen_test"] = iptal
        rapor["kabul_test_sayisi"] = len(set(dogrulayici.test_kimlikleri(testler)) - set(iptal))
        kabul = {**kabul, "testler": dogrulayici.testler_metni(testler)}   # arayüzde metin olarak gösterilir
        rapor["kabul_gecti"] = rapor["turlar"][-1]["gecti"]

    rapor.update({"ozet": s["ozet"], "adim": toplam_adim, "yurutucu_token": token, "yurutucu_usd": yurutucu_usd,
                  "bitirdi": s["bitti"], "sure_sn": round(time.time() - bas, 1), "kabul": kabul})
    return rapor
