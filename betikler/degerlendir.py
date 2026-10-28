"""a/b/c karşılaştırması: her görev her kipte ayrı bir Modal Sandbox'ta çalışır, ardından gizli testler koşturulur.

Gizli testler ajanlara ve Usta'nın kabul testi yazarına hiç gösterilmez; ajan bitirdikten sonra çalışma alanına yazılır.
Sonuçlar kayitlar/degerlendirme/<kip>_<id>.json dosyalarına tek tek yazılır (yarıda kalırsa kaldığı yerden sürer).

    python betikler/degerlendir.py --set zor --kipler a b c --paralel 12
    python betikler/degerlendir.py --set zor --ozet
"""
import argparse
import json
import math
import random
import re
import sys
import traceback
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from usta import glimmer, spark, surec  # noqa: E402
from usta.arac import calisma_ac  # noqa: E402

KOK = Path(__file__).resolve().parent.parent
SETLER = {"kolay": KOK / "veri" / "degerlendirme.jsonl", "zor": KOK / "veri" / "zor.jsonl",
          "zor2": KOK / "veri" / "zor2.jsonl", "aday3": KOK / "veri" / "aday3.jsonl",
          "zor3": KOK / "veri" / "zor3.jsonl"}
KAYIT = KOK / "kayitlar" / "degerlendirme"  # main() set ve yürütücü adına göre alt klasör seçer
YURUTUCU = "glimmer"
GIZLI_DOSYA = ".gizli/test_gizli.py"


def gizli_testler(calisma, testler: str) -> dict:
    calisma._yaz(GIZLI_DOSYA, testler)
    _, cikti = calisma._calistir(f"python -m pytest -q -p no:cacheprovider {GIZLI_DOSYA} 2>&1 | tail -n 30", 120)
    gecen = sum(int(x) for x in re.findall(r"(\d+) passed", cikti))
    kalan = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", cikti))
    return {"gecti": gecen > 0 and kalan == 0, "gecen": gecen, "toplam": gecen + kalan, "cikti": cikti[-1500:]}


def tek(is_):
    kip, g, t = is_
    yol = KAYIT / (f"{kip}_{g['id']}.json" if t == 1 else f"{kip}_{g['id']}_t{t}.json")
    if yol.exists():
        return json.loads(yol.read_text(encoding="utf-8"))
    r = {"id": g["id"], "kip": kip, "tekrar": t, "kategori": g["kategori"]}
    try:
        with calisma_ac() as c:
            rapor = surec.gorevi_yap(g["gorev"], c, kip=kip, yurutucu=YURUTUCU)
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
    print(f"{kip} {g['id']} t{t} {'GEÇTİ' if r['gizli']['gecti'] else 'kaldı'} "
          f"{r['gizli']['gecen']}/{r['gizli']['toplam']} adım={r.get('adim')} {r.get('hata', '')[:80]}", flush=True)
    return r


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Oran için %95 Wilson güven aralığı."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    merkez = (p + z * z / (2 * n)) / (1 + z * z / n)
    yari = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, merkez - yari), min(1.0, merkez + yari)


def eslesmis_fark(x: list, y: list, tekrar: int = 10000) -> tuple[float, float, float]:
    """Aynı görevlerde başarı oranı farkı (x - y) ve görev düzeyinde bootstrap %95 aralığı."""
    n = len(x)
    farklar = [int(a) - int(b) for a, b in zip(x, y)]
    rng = random.Random(0)
    ornekler = sorted(sum(rng.choice(farklar) for _ in range(n)) / n for _ in range(tekrar))
    return sum(farklar) / n, ornekler[int(0.025 * tekrar)], ornekler[int(0.975 * tekrar) - 1]


GELISTIRME = {f"g{i:02d}" for i in range(1, 7)}  # yöntem ayarlanırken bakılan görevler; asıl sonuç bunların dışında


def _bootstrap(degerler: list, tekrar: int = 10000) -> tuple[float, float]:
    rng = random.Random(0)
    n = len(degerler)
    ornek = sorted(sum(rng.choice(degerler) for _ in range(n)) / n for _ in range(tekrar))
    return ornek[int(0.025 * tekrar)], ornek[int(0.975 * tekrar) - 1]


def _gorev_ortalamalari(sonuclar: list) -> dict:
    """{kip: {görev: o görevdeki koşuların geçme oranı}} — tekrarlar görev içinde ortalanır."""
    tablo: dict = {}
    for r in sonuclar:
        tablo.setdefault(r["kip"], {}).setdefault(r["id"], []).append(float(r["gizli"]["gecti"]))
    return {k: {i: sum(v) / len(v) for i, v in g.items()} for k, g in tablo.items()}


def _hukum(r: dict) -> bool:
    """Sistemin 'iş tamam' hükmü: c/d'de son kabul turu geçti mi; a/b'de ajan Done dedi mi."""
    if r["kip"] in ("c", "d"):
        return bool(r.get("turlar")) and r["turlar"][-1]["gecti"]
    return bool(r.get("bitirdi", r.get("ozet") is not None))


def _tablo(sonuclar: list, baslik: str) -> list:
    ort = _gorev_ortalamalari(sonuclar)
    tekrar = max((r.get("tekrar", 1) for r in sonuclar), default=1)
    satirlar = [f"**{baslik}** (görev başına en çok {tekrar} koşu; aralıklar görev düzeyinde bootstrap %95)", "",
                "| Kip | Görev | Koşu | Geçme oranı | %95 GA | Gizli test oranı | Ort. adım | Ort. yürütücü token | Meta API $ | Hata |",
                "|---|---|---|---|---|---|---|---|---|---|"]
    for kip in "abcd":
        rs = [r for r in sonuclar if r["kip"] == kip]
        if not rs:
            continue
        n = len(rs)
        oran = list(ort[kip].values())
        alt, ust = _bootstrap(oran)
        gecen = sum(r["gizli"]["gecen"] for r in rs)
        toplam = sum(r["gizli"]["toplam"] for r in rs) or 1
        adim = sum(r.get("adim") or 0 for r in rs) / n
        tok = sum(sum((r.get("yurutucu_token") or r.get("glimmer_token") or {}).values()) for r in rs) / n
        usd = sum((r.get("spark_usd") or 0) + (r.get("yurutucu_usd") or 0) for r in rs)
        hata = sum("hata" in r for r in rs)
        satirlar.append(f"| {kip} | {len(oran)} | {n} | %{100 * sum(oran) / len(oran):.1f} | %{100 * alt:.0f}–{100 * ust:.0f} | "
                        f"%{100 * gecen / toplam:.0f} | {adim:.1f} | {tok:,.0f} | {usd:.3f} | {hata} |")
    for bu, diger in (("c", "a"), ("c", "b"), ("d", "a"), ("d", "c"), ("b", "a")):
        if bu in ort and diger in ort:
            ortak = sorted(set(ort[bu]) & set(ort[diger]))
            if ortak:
                farklar = [ort[bu][i] - ort[diger][i] for i in ortak]
                alt, ust = _bootstrap(farklar)
                satirlar.append(f"\n{bu} − {diger} ({len(ortak)} ortak görev): {100 * sum(farklar) / len(farklar):+.1f} puan "
                                f"(%95 GA {100 * alt:+.1f} … {100 * ust:+.1f})")
    # Ayırt edicilik: sistemin 'tamam' hükmü gizli testlerle ne kadar uyuşuyor?
    satirlar += ["", "| Kip | 'Tamam' hükmü | Hükmü doğru çıkan (kesinlik) | Gizli testte kalan iş | Bunların işaretlenen kısmı |",
                 "|---|---|---|---|---|"]
    for kip in "abcd":
        rs = [r for r in sonuclar if r["kip"] == kip and "hata" not in r]
        if not rs:
            continue
        tamam = [r for r in rs if _hukum(r)]
        dogru = sum(r["gizli"]["gecti"] for r in tamam)
        kalan = [r for r in rs if not r["gizli"]["gecti"]]
        isaret = sum(not _hukum(r) for r in kalan)
        kes = f"{dogru}/{len(tamam)} (%{100 * dogru / len(tamam):.0f})" if tamam else "-"
        isr = f"{isaret}/{len(kalan)} (%{100 * isaret / len(kalan):.0f})" if kalan else "-"
        satirlar.append(f"| {kip} | {len(tamam)}/{len(rs)} | {kes} | {len(kalan)} | {isr} |")
    satirlar.append("")
    return satirlar


def ozet():
    sonuclar = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(KAYIT.glob("*.json"))]
    satirlar = _tablo([r for r in sonuclar if r["id"] not in GELISTIRME], "Değerlendirme görevleri (geliştirmede bakılmayan)")
    if any(r["id"] in GELISTIRME for r in sonuclar):
        satirlar += _tablo([r for r in sonuclar if r["id"] in GELISTIRME], "Geliştirme görevleri (g01–g06)")
    print("\n".join(satirlar))
    return satirlar


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kipler", nargs="+", default=["a", "b", "c"])
    ap.add_argument("--paralel", type=int, default=12)
    ap.add_argument("--sinir", type=int, default=0, help="yalnızca ilk N görev (deneme için)")
    ap.add_argument("--ozet", action="store_true")
    ap.add_argument("--set", choices=list(SETLER), default="kolay")
    ap.add_argument("--yurutucu", choices=["glimmer", "spark"], default="glimmer")
    ap.add_argument("--aralik", default="", help="görev kimliği aralığı, ör. g07-g40")
    ap.add_argument("--tekrar", type=int, default=1, help="her görev ve kip için koşu sayısı")
    a = ap.parse_args()
    global KAYIT, YURUTUCU
    YURUTUCU = a.yurutucu
    KAYIT = KAYIT / (a.set if a.yurutucu == "glimmer" else f"{a.set}_{a.yurutucu}")
    if a.ozet:
        ozet()
        return
    gorevler = [json.loads(s) for s in SETLER[a.set].read_text(encoding="utf-8").splitlines() if s.strip()]
    if a.sinir:
        gorevler = gorevler[:a.sinir]
    if a.aralik:
        bas, son = a.aralik.split("-")
        gorevler = [g for g in gorevler if bas <= g["id"] <= son]
    KAYIT.mkdir(parents=True, exist_ok=True)
    if YURUTUCU == "glimmer":
        glimmer.hazir_bekle()
    # Tekrarlar dışta: önce her görevin 1. koşusu biter, yarıda kesilse bile dengeli bir ara sonuç olur.
    isler = [(k, g, t) for t in range(1, a.tekrar + 1) for g in gorevler for k in a.kipler]
    with ThreadPoolExecutor(a.paralel) as ex:
        list(ex.map(tek, isler))
    ozet()
    print(f"Meta API toplam harcama (bu depo): {spark.butce()['toplam_usd']:.4f} $")


if __name__ == "__main__":
    main()
