"""Muse Spark (Meta Model API) istemcisi — harcama sayacıyla.

Her yanıtın `usage` alanından maliyet hesaplanır ve kayitlar/butce.jsonl defterine bir satır olarak eklenir
(salt-ekleme: aynı anda çalışan iş parçacıkları ve süreçler birbirinin kaydını ezmez). Toplam SINIR_USD'ye ulaşınca
yeni istek atılmaz (ButceAsildi). Sayaç yalnızca bu depodan yapılan istekleri görür; hesabın başka harcamaları dahil değildir.

Contributor modunda gönderilen içerik Meta'nın ürün geliştirmesinde kullanılabilir: kişisel veri gönderme.
"""
import json
import os
import threading
import time
from pathlib import Path

import requests

BASE = "https://api.meta.ai/v1"
MODEL = "muse-spark-1.3-contributor"
# 1M token başına USD (girdi, çıktı)
FIYAT = {"muse-spark-1.3-contributor": (0.10, 0.20)}
SINIR_USD = float(os.environ.get("USTA_BUTCE_SINIRI", "140"))

KOK = Path(__file__).resolve().parent.parent
ESKI_DOSYA = KOK / "kayitlar" / "butce.json"     # 28 Eki'ye kadarki toplam (artık yazılmaz)
DEFTER = KOK / "kayitlar" / "butce.jsonl"
ANAHTAR_DOSYASI = Path.home() / ".pflow-anahtarlar.env"
_kilit = threading.Lock()


class ButceAsildi(RuntimeError):
    pass


def _anahtar() -> str:
    if os.environ.get("META_MODEL_API_KEY"):
        return os.environ["META_MODEL_API_KEY"]
    for satir in ANAHTAR_DOSYASI.read_text(encoding="utf-8").splitlines():
        if satir.startswith("META_MODEL_API_KEY="):
            return satir.split("=", 1)[1].strip()
    raise RuntimeError(f"META_MODEL_API_KEY bulunamadı ({ANAHTAR_DOSYASI})")


BOS = {"toplam_usd": 0.0, "istek": 0, "girdi_token": 0, "cikti_token": 0}


def butce() -> dict:
    """Defterdeki tüm satırların toplamı. Eski tek-dosya sayacı (butce.json) varsa başlangıç değeri olarak eklenir."""
    b = dict(BOS)
    if ESKI_DOSYA.exists():
        try:
            b.update(json.loads(ESKI_DOSYA.read_text(encoding="utf-8")))
        except ValueError:
            pass
    if DEFTER.exists():
        for satir in DEFTER.read_text(encoding="utf-8").splitlines():
            try:
                k = json.loads(satir)
            except ValueError:
                continue   # yazılmakta olan yarım satır
            b["toplam_usd"] += k["usd"]
            b["istek"] += 1
            b["girdi_token"] += k["g"]
            b["cikti_token"] += k["c"]
    return b


def _kaydet(model: str, usage: dict) -> float:
    gf, cf = FIYAT.get(model, FIYAT[MODEL])
    g, c = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    maliyet = g / 1e6 * gf + c / 1e6 * cf
    with _kilit:
        DEFTER.parent.mkdir(exist_ok=True)
        with DEFTER.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"usd": maliyet, "g": g, "c": c, "m": model, "t": round(time.time())}) + "\n")
    return maliyet


class _HizSiniri:
    """Süreç içi kayan pencere: son 60 sn'deki istek sayısı RPM'i aşmasın (Meta contributor sınırı 150/dk)."""

    def __init__(self, rpm: int):
        self.rpm, self.zamanlar, self.kilit = rpm, [], threading.Lock()

    def bekle(self):
        while True:
            with self.kilit:
                simdi = time.time()
                self.zamanlar = [t for t in self.zamanlar if simdi - t < 60]
                if len(self.zamanlar) < self.rpm:
                    self.zamanlar.append(simdi)
                    return
                bekleme = 60 - (simdi - self.zamanlar[0]) + 0.05
            time.sleep(bekleme)


_hiz = _HizSiniri(int(os.environ.get("USTA_RPM", "130")))


def _bekleme(r, i: int) -> float:
    try:
        return min(60.0, float(r.headers.get("Retry-After"))) if r is not None and r.headers.get("Retry-After") else 0.0
    except (TypeError, ValueError):
        return 0.0


def sohbet(messages: list, model: str = MODEL, max_tokens: int = 4096, temperature: float = 0.2,
           tekrar: int = 8, **ek) -> dict:
    """OpenAI uyumlu /chat/completions çağrısı; mesaj sözlüğünü döndürür (+ '_usage', '_maliyet')."""
    if butce()["toplam_usd"] >= SINIR_USD:
        raise ButceAsildi(f"Spark bütçe sınırı ({SINIR_USD} $) doldu")
    govde = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, **ek}
    basliklar = {"Authorization": f"Bearer {_anahtar()}"}
    for i in range(tekrar):
        _hiz.bekle()
        try:
            r = requests.post(f"{BASE}/chat/completions", headers=basliklar, json=govde, timeout=300)
        except requests.RequestException:
            if i == tekrar - 1:
                raise
            time.sleep(min(60, 2 ** i * 3))
            continue
        if r.status_code in (429, 500, 502, 503, 504) and i < tekrar - 1:
            time.sleep(_bekleme(r, i) or min(60, 2 ** i * 3))
            continue
        r.raise_for_status()
        try:
            veri = r.json()
        except ValueError:
            # Nadiren gövdesi boş/JSON olmayan 200 yanıtı geliyor: tekrar dene.
            if i == tekrar - 1:
                raise
            time.sleep(2 ** i * 3)
            continue
        mesaj = veri["choices"][0]["message"]
        mesaj["tool_calls"] = mesaj.get("tool_calls") or []
        mesaj["_finish"] = veri["choices"][0].get("finish_reason")
        usage = veri.get("usage") or {}
        mesaj["_usage"] = usage
        mesaj["_maliyet"] = _kaydet(model, usage)
        return mesaj
    raise RuntimeError("Spark isteği başarısız")


if __name__ == "__main__":
    m = sohbet([{"role": "user", "content": "Tek cümleyle: Python'da liste ile demet farkı nedir?"}], max_tokens=200)
    print(m.get("content"))
    print(f"maliyet: {m['_maliyet']:.6f} $ | toplam: {butce()['toplam_usd']:.4f} $")
