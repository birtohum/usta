"""Muse Spark (Meta Model API) istemcisi — harcama sayacıyla.

Her yanıtın `usage` alanından maliyet hesaplanır ve kayitlar/butce.json'a eklenir. Toplam SINIR_USD'ye ulaşınca
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
BUTCE_DOSYASI = KOK / "kayitlar" / "butce.json"
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


def butce() -> dict:
    if BUTCE_DOSYASI.exists():
        return json.loads(BUTCE_DOSYASI.read_text(encoding="utf-8"))
    return {"toplam_usd": 0.0, "istek": 0, "girdi_token": 0, "cikti_token": 0}


def _kaydet(model: str, usage: dict) -> float:
    gf, cf = FIYAT.get(model, FIYAT[MODEL])
    g, c = usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    maliyet = g / 1e6 * gf + c / 1e6 * cf
    with _kilit:
        b = butce()
        b["toplam_usd"] += maliyet
        b["istek"] += 1
        b["girdi_token"] += g
        b["cikti_token"] += c
        BUTCE_DOSYASI.parent.mkdir(exist_ok=True)
        BUTCE_DOSYASI.write_text(json.dumps(b, indent=1), encoding="utf-8")
    return maliyet


def sohbet(messages: list, model: str = MODEL, max_tokens: int = 4096, temperature: float = 0.2,
           tekrar: int = 4, **ek) -> dict:
    """OpenAI uyumlu /chat/completions çağrısı; mesaj sözlüğünü döndürür (+ '_usage', '_maliyet')."""
    if butce()["toplam_usd"] >= SINIR_USD:
        raise ButceAsildi(f"Spark bütçe sınırı ({SINIR_USD} $) doldu")
    govde = {"model": model, "messages": messages, "max_tokens": max_tokens, "temperature": temperature, **ek}
    basliklar = {"Authorization": f"Bearer {_anahtar()}"}
    for i in range(tekrar):
        try:
            r = requests.post(f"{BASE}/chat/completions", headers=basliklar, json=govde, timeout=300)
        except requests.RequestException:
            if i == tekrar - 1:
                raise
            time.sleep(2 ** i * 3)
            continue
        if r.status_code in (429, 500, 502, 503, 504) and i < tekrar - 1:
            time.sleep(2 ** i * 3)
            continue
        r.raise_for_status()
        veri = r.json()
        mesaj = veri["choices"][0]["message"]
        usage = veri.get("usage") or {}
        mesaj["_usage"] = usage
        mesaj["_maliyet"] = _kaydet(model, usage)
        return mesaj
    raise RuntimeError("Spark isteği başarısız")


if __name__ == "__main__":
    m = sohbet([{"role": "user", "content": "Tek cümleyle: Python'da liste ile demet farkı nedir?"}], max_tokens=200)
    print(m.get("content"))
    print(f"maliyet: {m['_maliyet']:.6f} $ | toplam: {butce()['toplam_usd']:.4f} $")
