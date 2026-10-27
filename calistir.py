"""Usta web arayüzünü başlatır: python calistir.py  ->  http://127.0.0.1:8765"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    import uvicorn
    from usta.web import app
    uvicorn.run(app, host="127.0.0.1", port=8765)
