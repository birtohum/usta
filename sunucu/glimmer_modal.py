"""Muse Glimmer 30B'yi Modal'da (H100) kimlik doğrulamalı, OpenAI uyumlu bir uç nokta olarak çalıştırır.

Kullanım (depo kökünden):
    modal deploy sunucu/glimmer_modal.py      # kalıcı adres; boşta 5 dk sonra GPU kapanır
    modal app stop -y usta-glimmer            # tamamen durdur

Erişim anahtarı yerel .env dosyasındaki USTA_GLIMMER_TOKEN'dır; dağıtım sırasında Modal'a gizli değer olarak geçer.
İstekler `Authorization: Bearer <anahtar>` başlığı olmadan 401 alır (vLLM --api-key).
"""
import os
import subprocess
from pathlib import Path

import modal

MODEL = "meta-models/Muse-Glimmer-30B"
PORT = 8000


def _yerel_anahtar() -> dict:
    # Yalnızca dağıtım yapan makinede okunur; konteyner içinde değer gizli değerden gelir.
    env = Path(__file__).resolve().parent.parent / ".env"
    if not env.exists():
        return {}
    for satir in env.read_text(encoding="utf-8").splitlines():
        if satir.startswith("USTA_GLIMMER_TOKEN="):
            return {"USTA_GLIMMER_TOKEN": satir.split("=", 1)[1].strip()}
    return {}


# Yayımlanmış vLLM sürümleri Glimmer'ı henüz tanımıyor; Meta'nın etiketli imajı gerekli.
# Modal imajdaki Python'u kullanamadığı için kendi Python'unu ekliyoruz.
imaj = modal.Image.from_registry("vllm/vllm-openai:muse-glimmer", add_python="3.12").entrypoint([])
agirliklar = modal.Volume.from_name("glimmer-hf", create_if_missing=True)
app = modal.App("usta-glimmer")


@app.function(
    image=imaj,
    gpu="H100",
    volumes={"/root/.cache/huggingface": agirliklar},
    secrets=[modal.Secret.from_dict(_yerel_anahtar())],
    timeout=6 * 3600,
    scaledown_window=300,
    # Büyük değerlendirmede USTA_GPU_SAYISI=3 ile birden çok H100 açılabilir (her biri ~4 $/sa).
    max_containers=int(os.environ.get("USTA_GPU_SAYISI", "1")),
)
@modal.concurrent(max_inputs=48)
@modal.web_server(port=PORT, startup_timeout=2400)
def glimmer():
    anahtar = os.environ.get("USTA_GLIMMER_TOKEN")
    if not anahtar:
        raise RuntimeError("USTA_GLIMMER_TOKEN yok: kimlik doğrulamasız sunucu açılmaz")
    subprocess.Popen([
        "vllm", "serve", MODEL,
        "--served-model-name", "muse-glimmer",
        "--api-key", anahtar,
        "--enable-auto-tool-choice",
        "--tool-call-parser", "muse_glimmer",
        "--reasoning-parser", "muse_glimmer",
        "--generation-config", "auto",
        "--max-model-len", "32768",
        "--host", "0.0.0.0", "--port", str(PORT),
    ])
