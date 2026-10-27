"""Glimmer sunucusunda yerel araç çağrısının (tool_calls) çalışıp çalışmadığını dener.

    python sunucu/arac_cagrisi_dene.py

Çıktı: kimliksiz isteğin reddedildiği, yanıtta tool_calls olup olmadığı ve ham içerik (ATEM izi aramak için).
"""
import json
import sys
import time
from pathlib import Path

import requests

URL = "https://egenksban10--usta-glimmer-glimmer.us-east.modal.run"
KOK = Path(__file__).resolve().parent.parent


def anahtar() -> str:
    for satir in (KOK / ".env").read_text(encoding="utf-8").splitlines():
        if satir.startswith("USTA_GLIMMER_TOKEN="):
            return satir.split("=", 1)[1].strip()
    sys.exit(".env içinde USTA_GLIMMER_TOKEN yok")


ARACLAR = [{
    "type": "function",
    "function": {
        "name": "Write",
        "description": "Çalışma klasörüne bir dosya yazar (varsa üzerine yazar).",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Göreli dosya yolu"},
                "content": {"type": "string", "description": "Dosyanın tam içeriği"},
            },
            "required": ["path", "content"],
        },
    },
}]


def bekle(basliklar: dict) -> None:
    bas = time.time()
    while time.time() - bas < 2400:
        try:
            r = requests.get(f"{URL}/v1/models", headers=basliklar, timeout=60)
            if r.status_code == 200:
                print(f"hazır ({time.time() - bas:.0f} sn)")
                return
            print(f"bekleniyor: {r.status_code}")
        except requests.RequestException as e:
            print(f"bekleniyor: {type(e).__name__}")
        time.sleep(20)
    sys.exit("sunucu açılmadı")


def main() -> None:
    basliklar = {"Authorization": f"Bearer {anahtar()}"}
    bekle(basliklar)

    r = requests.get(f"{URL}/v1/models", timeout=60)
    print("kimliksiz istek:", r.status_code)

    govde = {
        "model": "muse-glimmer",
        "messages": [
            {"role": "system", "content": "Sen bir yazılım ajanısın. Dosya oluşturmak için araçları kullan."},
            {"role": "user", "content": "selam.py adında, ekrana 'Merhaba dünya' yazan bir Python dosyası oluştur."},
        ],
        "tools": ARACLAR,
        "tool_choice": "auto",
        "max_tokens": 2048,
    }
    for deneme in range(3):
        r = requests.post(f"{URL}/v1/chat/completions", headers=basliklar, json=govde, timeout=600)
        r.raise_for_status()
        mesaj = r.json()["choices"][0]["message"]
        cagrilar = mesaj.get("tool_calls") or []
        print(f"\n--- deneme {deneme + 1}: tool_calls={len(cagrilar)} finish={r.json()['choices'][0]['finish_reason']}")
        for c in cagrilar:
            print(c["function"]["name"], json.loads(c["function"]["arguments"]))
        print("content:", repr((mesaj.get("content") or "")[:800]))
        print("reasoning:", repr((mesaj.get("reasoning_content") or mesaj.get("reasoning") or "")[:300]))
        print("usage:", r.json().get("usage"))


if __name__ == "__main__":
    main()
