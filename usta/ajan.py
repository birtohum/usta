"""Glimmer ajan döngüsü: model araç çağırır, çalıştırıcı yürütür, sonuç geri verilir; Done ya da adım sınırına kadar."""
import json

import requests

from usta import glimmer
from usta.arac import ARACLAR, Calisma

SISTEM = """Sen Usta'sın: Türkçe konuşan, dikkatli bir yazılım ajanı.
Görevi bir çalışma klasöründe araçlarla yaparsın: Write, Read, Edit, Bash, Done.
Kurallar:
- Kodu dosyalara yaz; yalnızca göreli yollar kullan. İnternet yok, paket kuramazsın (Python 3.12 standart kütüphanesi ve pytest var).
- Yazdığın kodu Bash ile çalıştırarak dene; hata varsa düzelt.
- Bitirdiğinde Done aracını kısa bir Türkçe özetle çağır."""


def calistir(gorev: str, calisma: Calisma, azami_adim: int = 20, gecmis: list | None = None,
             olay=lambda tur, veri: None, sistem: str = SISTEM) -> dict:
    """Görevi yürütür. gecmis verilirse (düzeltme turu) konuşma oradan sürer.
    olay(tur, veri): arayüz için canlı adım bildirimi ('dusunce', 'arac', 'sonuc', 'bitti')."""
    mesajlar = gecmis if gecmis is not None else [{"role": "system", "content": sistem},
                                                   {"role": "user", "content": gorev}]
    ozet, adim, token = None, 0, {"girdi": 0, "cikti": 0}
    while adim < azami_adim:
        adim += 1
        try:
            m = glimmer.sohbet(mesajlar, tools=ARACLAR)
        except requests.HTTPError as e:
            # 400 çoğunlukla bağlam sınırının (32k token) aşılmasıdır: görevi burada bırak.
            if e.response is not None and e.response.status_code == 400:
                olay("dusunce", f"Glimmer isteği reddetti (bağlam sınırı olabilir): {e.response.text[:200]}")
                break
            raise
        token["girdi"] += m["_usage"].get("prompt_tokens", 0)
        token["cikti"] += m["_usage"].get("completion_tokens", 0)
        asistan = {"role": "assistant", "content": m.get("content") or ""}
        if m["tool_calls"]:
            asistan["tool_calls"] = [{"id": c["id"], "type": "function", "function": c["function"]} for c in m["tool_calls"]]
        mesajlar.append(asistan)
        if m.get("content"):
            olay("dusunce", m["content"])
        if not m["tool_calls"]:
            # Araç çağırmadan durdu: bir kez hatırlat, yine durursa bitmiş say.
            if mesajlar[-2].get("role") == "user" and "Done" in mesajlar[-2].get("content", ""):
                break
            mesajlar.append({"role": "user", "content": "Devam et: araçları kullan, bitince Done çağır."})
            continue
        bitti = False
        for c in m["tool_calls"]:
            ad = c["function"]["name"]
            try:
                arg = json.loads(c["function"]["arguments"] or "{}")
            except json.JSONDecodeError:
                arg, sonuc = {}, "HATA: argümanlar geçerli JSON değil"
            else:
                if ad == "Done":
                    ozet, bitti, sonuc = arg.get("summary", ""), True, "Tamam."
                else:
                    olay("arac", {"ad": ad, "arg": arg})
                    sonuc = calisma.arac_calistir(ad, arg)
                    olay("sonuc", {"ad": ad, "cikti": sonuc})
            mesajlar.append({"role": "tool", "tool_call_id": c["id"], "content": sonuc})
        if bitti:
            break
    olay("bitti", {"ozet": ozet, "adim": adim})
    return {"ozet": ozet, "adim": adim, "bitti": ozet is not None, "mesajlar": mesajlar, "token": token}


if __name__ == "__main__":
    import sys
    from usta.arac import calisma_ac

    gorev = sys.argv[1] if len(sys.argv) > 1 else "asal.py içinde asal_mi(n) fonksiyonu yaz ve birkaç örnekle dene."
    tur = sys.argv[2] if len(sys.argv) > 2 else "yerel"

    def yaz(t, v):
        print(f"[{t}]", json.dumps(v, ensure_ascii=False)[:400])

    with calisma_ac(tur) as c:
        s = calistir(gorev, c, olay=yaz)
        print("\nDOSYALAR:", list(c.dosyalar()))
        print("ADIM:", s["adim"], "TOKEN:", s["token"], "BİTTİ:", s["bitti"])
