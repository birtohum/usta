"""Muse Voice Transcribe ile Türkçe sesli görevi yazıya çevirir.

Meta bu model için yalnızca gerçek zamanlı WebSocket sunuyor (wss://api.meta.ai/v1/asr/realtime). Kayıt tarayıcıda
alınır; burada 24 kHz PCM16 mono'ya çevrilip gerçek zamana yakın hızda akıtılır, son metin döndürülür.
Ses içeriği Meta'ya gider: kişisel veri içeren kayıt gönderme.
"""
import asyncio
import audioop  # Python 3.12'de mevcut (3.13'te kaldırıldı)
import io
import json
import uuid
import wave

import websockets

from usta.spark import _anahtar

URL = "wss://api.meta.ai/v1/asr/realtime"
HIZ = 24000
CERCEVE = 3840  # 80 ms @ 24 kHz, 16 bit


def wav_to_pcm24k(veri: bytes) -> bytes:
    with wave.open(io.BytesIO(veri)) as w:
        kanal, genislik, hiz = w.getnchannels(), w.getsampwidth(), w.getframerate()
        ham = w.readframes(w.getnframes())
    if genislik != 2:
        ham = audioop.lin2lin(ham, genislik, 2)
    if kanal == 2:
        ham = audioop.tomono(ham, 2, 0.5, 0.5)
    if hiz != HIZ:
        ham, _ = audioop.ratecv(ham, 2, 1, hiz, HIZ, None)
    return ham


async def _yaziya(pcm: bytes, dil: str) -> str:
    async with websockets.connect(f"{URL}?sessionId=usta-{uuid.uuid4()}", max_size=None) as ws:
        el_sikisma = {"authorization": {"accessToken": f"Bearer {_anahtar()}"}, "audioEncoding": "PCM_24KHZ",
                      "model": "muse-voice-transcribe-1.0", "mode": "PUSH_TO_TALK"}
        if dil:
            el_sikisma["languageBias"] = [dil]
        await ws.send(json.dumps(el_sikisma))
        yanit = json.loads(await asyncio.wait_for(ws.recv(), 15))
        if "sessionId" not in yanit:
            raise RuntimeError(f"Voice el sıkışması başarısız: {yanit}")

        sonlar, son_kismi = [], ""

        async def oku():
            nonlocal son_kismi
            async for mesaj in ws:
                if isinstance(mesaj, bytes):
                    continue
                olay = json.loads(mesaj)
                if olay.get("type") == "error":
                    raise RuntimeError(f"Voice hatası: {olay.get('message')}")
                if olay.get("type") == "transcript":
                    if olay.get("final"):
                        sonlar.append(olay.get("transcript", ""))
                        son_kismi = ""
                    else:
                        son_kismi = olay.get("transcript", "")

        okuyucu = asyncio.create_task(oku())
        for i in range(0, len(pcm), CERCEVE):
            await ws.send(pcm[i:i + CERCEVE])
            await asyncio.sleep(0.075)  # gerçek zamandan biraz hızlı; çok hızlı gönderim 1008 ile kapanır
        await ws.send(json.dumps({"type": "endStream"}))
        try:
            await asyncio.wait_for(okuyucu, 30)
        except websockets.ConnectionClosedOK:
            pass
        metin = " ".join(s.strip() for s in sonlar if s.strip())
        return metin or son_kismi.strip()


def yaziya_cevir(wav: bytes, dil: str = "Turkish") -> str:
    return asyncio.run(_yaziya(wav_to_pcm24k(wav), dil))


if __name__ == "__main__":
    import sys
    print(yaziya_cevir(open(sys.argv[1], "rb").read()))
