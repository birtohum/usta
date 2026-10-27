"""a/b/c karşılaştırması: her görev her kipte ayrı bir Modal Sandbox'ta çalışır, ardından gizli testler koşturulur.

Gizli testler ajanlara ve Usta'nın kabul testi yazarına hiç gösterilmez; ajan bitirdikten sonra çalışma alanına yazılır.
Sonuçlar kayitlar/degerlendirme/<kip>_<id>.json dosyalarına tek tek yazılır (yarıda kalırsa kaldığı yerden sürer).

    python betikler/degerlendir.py --set zor --kipler a b c --paralel 12
    python betikler/degerlendir.py --set zor --ozet
"""
import argparse
import json
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usta import glimmer, spark, surec  # noqa: E402
from usta.arac import ModalCalisma  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
SETLER = {"kolay": KOK / "veri" / "degerlendirme.jsonl", "zor": KOK / "veri" / "zor.jsonl"}
KAYIT = KOK / "kayitlar" / "degerlendirme"  # main() set adına göre alt klasör seçer
GIZLI_DOSYA = ".gizli/test_gizli.py"


def gizli_testler(calisma, testler: str) -> dict:
    calisma._yaz(GIZLI_DOSYA, testler)
    _, cikti = calisma._calistir(f"python -m pytest -q -p no:cacheprovider {GIZLI_DOSYA} 2>&1 | tail -n 30", 120)
    gecen = sum(int(x) for x in re.findall(r"(\d+) passed", cikti))
    kalan = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", cikti))
    return {"gecti": gecen > 0 and kalan == 0, "gecen": gecen, "toplam": gecen + kalan, "cikti": cikti[-1500:]}


def tek(is_):
    kip, g = is_
    yol = KAYIT / f"{kip}_{g['id']}.json"
    if yol.exists():
        return json.loads(yol.read_text(encoding="utf-8"))
    r = {"id": g["id"], "kip": kip, "kategori": g["kategori"]}
    try:
        with ModalCalisma() as c:
            rapor = surec.gorevi_yap(g["gorev"], c, kip=kip)
            rapor.pop("kabul", None)
            r.update(rapor)
            r["gizli"] = gizli_testler(c, g["gizli_testler"])
    except spark.ButceAsildi:
        raise
    except Exception as e:
        r["hata"] = f"{type(e).__name__}: {e}"
        r["iz"] = traceback.format_exc()[-1500:]
        r["gizli"] = {"gecti": False, "gecen": 0, "toplam": 0}
    yol.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{kip} {g['id']} {'GEÇTİ' if r['gizli']['gecti'] else 'kaldı'} "
          f"{r['gizli']['gecen']}/{r['gizli']['toplam']} adım={r.get('adim')} {r.get('hata', '')[:80]}", flush=True)
    return r


GELISTIRME = {f"g{i:02d}" for i in range(1, 7)}  # yöntem ayarlanırken bakılan görevler; asıl sonuç bunların dışında


def _tablo(sonuclar: list, baslik: str) -> list:
    satirlar = [f"**{baslik}**", "",
                "| Kip | Görev | Tamamen geçen | Gizli test oranı | Ort. adım | Ort. Glimmer token | Spark $ | Hata |",
                "|---|---|---|---|---|---|---|---|"]
    for kip in "abc":
        rs = [r for r in sonuclar if r["kip"] == kip]
        if not rs:
            continue
        n = len(rs)
        tam = sum(r["gizli"]["gecti"] for r in rs)
        gecen = sum(r["gizli"]["gecen"] for r in rs)
        toplam = sum(r["gizli"]["toplam"] for r in rs) or 1
        adim = sum(r.get("adim") or 0 for r in rs) / n
        tok = sum(sum((r.get("glimmer_token") or {}).values()) for r in rs) / n
        usd = sum(r.get("spark_usd") or 0 for r in rs)
        hata = sum("hata" in r for r in rs)
        satirlar.append(f"| {kip} | {n} | {tam}/{n} (%{100 * tam / n:.0f}) | %{100 * gecen / toplam:.0f} | {adim:.1f} | "
                        f"{tok:,.0f} | {usd:.3f} | {hata} |")
    # Eşleştirilmiş: aynı görevde c ile a/b'nin farklı sonuçlandığı durumlar
    gecti = {(r["kip"], r["id"]): r["gizli"]["gecti"] for r in sonuclar}
    for diger in "ab":
        ortak = [i for (k, i) in gecti if k == "c" and (diger, i) in gecti]
        if ortak:
            arti = sum(gecti[("c", i)] and not gecti[(diger, i)] for i in ortak)
            eksi = sum(gecti[(diger, i)] and not gecti[("c", i)] for i in ortak)
            satirlar.append(f"\nc vs {diger} ({len(ortak)} ortak görev): yalnızca c geçti {arti}, yalnızca {diger} geçti {eksi}")
    satirlar.append("")
    return satirlar


def ozet():
    sonuclar = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(KAYIT.glob("*.json"))]
    satirlar = _tablo([r for r in sonuclar if r["id"] not in GELISTIRME], "Değerlendirme görevleri (geliştirmede bakılmayan)")
    satirlar += _tablo([r for r in sonuclar if r["id"] in GELISTIRME], "Geliştirme görevleri (g01–g06)")
    satirlar += _tablo(sonuclar, "Tümü")
    print("\n".join(satirlar))
    return satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kipler", nargs="+", default=["a", "b", "c"])
    ap.add_argument("--paralel", type=int, default=12)
    ap.add_argument("--sinir", type=int, default=0, help="yalnızca ilk N görev (deneme için)")
    ap.add_argument("--ozet", action="store_true")
    ap.add_argument("--set", choices=list(SETLER), default="kolay")
    a = ap.parse_args()
    global KAYIT
    KAYIT = KAYIT / a.set
    if a.ozet:
        ozet()
        return
    gorevler = [json.loads(s) for s in SETLER[a.set].read_text(encoding="utf-8").splitlines() if s.strip()]
    if a.sinir:
        gorevler = gorevler[:a.sinir]
    KAYIT.mkdir(parents=True, exist_ok=True)
    glimmer.hazir_bekle()
    isler = [(k, g) for g in gorevler for k in a.kipler]
    with ThreadPoolExecutor(a.paralel) as ex:
        list(ex.map(tek, isler))
    ozet()
    print(f"Spark toplam harcama (bu depo): {spark.butce()['toplam_usd']:.4f} $")


if __name__ == "__main__":
    main()
