"""Modal'daki Muse Glimmer sunucusu için istemci (OpenAI uyumlu, kimlik doğrulamalı)."""
import json
import os
import re
import time
import uuid
from pathlib import Path

import requests

URL = os.environ.get("USTA_GLIMMER_URL", "https://egenksban10--usta-glimmer-glimmer.us-east.modal.run")
MODEL = "muse-glimmer"
KOK = Path(__file__).resolve().parent.parent


def _anahtar() -> str:
    if os.environ.get("USTA_GLIMMER_TOKEN"):
        return os.environ["USTA_GLIMMER_TOKEN"]
    for satir in (KOK / ".env").read_text(encoding="utf-8").splitlines():
        if satir.startswith("USTA_GLIMMER_TOKEN="):
            return satir.split("=", 1)[1].strip()
    raise RuntimeError(".env içinde USTA_GLIMMER_TOKEN yok")


def hazir_bekle(azami_sn: int = 2400, bildir=print) -> None:
    """Soğuk başlatmada (ağırlık yükleme + derleme ~3-6 dk) sunucu yanıt verene kadar bekler."""
    bas = time.time()
    while time.time() - bas < azami_sn:
        try:
            r = requests.get(f"{URL}/v1/models", headers={"Authorization": f"Bearer {_anahtar()}"}, timeout=60)
            if r.status_code == 200:
                return
        except requests.RequestException:
            pass
        bildir(f"Glimmer açılıyor... ({time.time() - bas:.0f} sn)")
        time.sleep(15)
    raise TimeoutError("Glimmer sunucusu açılmadı")


def ayristir_metin_cagrilari(icerik: str) -> list:
    """Sunucu ayrıştırıcısı tool_calls üretmezse içerikte kalan çağrıları yakalar (yedek yol)."""
    cagrilar = []
    for m in re.finditer(r"<atem:invoke\s+name=\"([^\"]+)\">(.*?)</atem:invoke>", icerik or "", re.S):
        arg = {p.group(1): p.group(2).strip("\n")
               for p in re.finditer(r"<atem:parameter\s+name=\"([^\"]+)\">(.*?)</atem:parameter>", m.group(2), re.S)}
        cagrilar.append({"id": f"call_{uuid.uuid4().hex[:12]}", "type": "function",
                         "function": {"name": m.group(1), "arguments": json.dumps(arg, ensure_ascii=False)}})
    return cagrilar


def sohbet(messages: list, tools: list | None = None, max_tokens: int = 4096, temperature: float = 0.2,
           tekrar: int = 3) -> dict:
    """Mesaj sözlüğünü döndürür; tool_calls her zaman liste olur (yedek ayrıştırma dahil)."""
    govde = {"model": MODEL, "messages": messages, "max_tokens": max_tokens, "temperature": temperature}
    if tools:
        govde["tools"] = tools
        govde["tool_choice"] = "auto"
    basliklar = {"Authorization": f"Bearer {_anahtar()}"}
    for i in range(tekrar):
        try:
            r = requests.post(f"{URL}/v1/chat/completions", headers=basliklar, json=govde, timeout=900)
            if r.status_code >= 500 and i < tekrar - 1:
                time.sleep(5 * (i + 1))
                continue
            r.raise_for_status()
            break
        except requests.RequestException:
            if i == tekrar - 1:
                raise
            time.sleep(5 * (i + 1))
    veri = r.json()
    secim = veri["choices"][0]
    mesaj = secim["message"]
    mesaj["tool_calls"] = mesaj.get("tool_calls") or []
    if tools and not mesaj["tool_calls"] and "<atem:" in (mesaj.get("content") or ""):
        mesaj["tool_calls"] = ayristir_metin_cagrilari(mesaj["content"])
        mesaj["content"] = re.sub(r"<atem:function_calls>.*?(</atem:function_calls>|$)", "", mesaj["content"], flags=re.S).strip()
        mesaj["_yedek_ayristirma"] = True
    mesaj["_usage"] = veri.get("usage") or {}
    mesaj["_finish"] = secim.get("finish_reason")
    return mesaj
