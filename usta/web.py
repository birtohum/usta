"""Usta'nın web arayüzü: görev (yazı ya da ses) alır, adımları canlı akıtır (SSE).

    python -m usta.web            -> http://127.0.0.1:8765
"""
import asyncio
import json
import queue
import threading
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from usta import glimmer, ses, surec
from usta.arac import calisma_ac

app = FastAPI(title="Usta")
STATIK = Path(__file__).resolve().parent / "statik"
ISLER: dict[str, queue.Queue] = {}


class Gorev(BaseModel):
    gorev: str
    kip: str = "c"


def _yurut(is_id: str, gorev: str, kip: str):
    q = ISLER[is_id]

    def olay(tur, veri):
        q.put({"tur": tur, "veri": veri})

    try:
        glimmer.hazir_bekle(bildir=lambda m: olay("asama", m))
        with calisma_ac("modal") as c:
            rapor = surec.gorevi_yap(gorev, c, kip=kip, olay=olay)
            dosyalar = {k: v for k, v in c.dosyalar().items() if not k.startswith(".usta_kabul/")}
        kabul = rapor.pop("kabul", None) or {}
        rapor["kabul_testleri"] = kabul.get("testler")
        olay("rapor", {**rapor, "dosyalar": dosyalar})
    except Exception as e:
        olay("hata", f"{type(e).__name__}: {e}")
    finally:
        q.put(None)


@app.get("/")
def ana_sayfa():
    return FileResponse(STATIK / "index.html")


@app.post("/api/gorev")
def gorev_baslat(g: Gorev):
    if not g.gorev.strip() or len(g.gorev) > 4000:
        raise HTTPException(400, "görev boş ya da çok uzun")
    if g.kip not in ("a", "b", "c"):
        raise HTTPException(400, "kip a, b ya da c olmalı")
    is_id = uuid.uuid4().hex[:10]
    ISLER[is_id] = queue.Queue()
    threading.Thread(target=_yurut, args=(is_id, g.gorev.strip(), g.kip), daemon=True).start()
    return {"id": is_id}


@app.get("/api/olaylar/{is_id}")
async def olaylar(is_id: str, request: Request):
    q = ISLER.get(is_id)
    if q is None:
        raise HTTPException(404, "iş yok")

    async def akis():
        while True:
            if await request.is_disconnected():
                break
            try:
                o = q.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.3)
                continue
            if o is None:
                yield "event: son\ndata: {}\n\n"
                ISLER.pop(is_id, None)
                break
            yield f"data: {json.dumps(o, ensure_ascii=False)}\n\n"

    return StreamingResponse(akis(), media_type="text/event-stream")


@app.post("/api/ses")
async def ses_yaziya(dosya: UploadFile):
    veri = await dosya.read()
    if len(veri) > 10 * 1024 * 1024:
        raise HTTPException(400, "ses kaydı çok uzun")
    try:
        metin = await asyncio.to_thread(ses.yaziya_cevir, veri)
    except Exception as e:
        raise HTTPException(502, f"yazıya çevrilemedi: {e}")
    return {"metin": metin}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
