"""Ajanın araçları ve bunları yalıtılmış bir çalışma alanında yürüten çalıştırıcılar.

İki arka uç:
  ModalCalisma  — her görev için ayrı bir Modal Sandbox (ağ tamamen kapalı, /work klasörü). Varsayılan.
  YerelCalisma  — yerel geçici klasör + alt süreç. Yalnızca geliştirme/test içindir; işletim sistemi düzeyinde
                  yalıtım YOKTUR, yalnızca aşağıdaki yol ve komut denetimleri uygulanır.

Her iki arka uçta da: klasör dışına çıkan yollar reddedilir, ağ/yetki/yıkıcı komut kalıpları reddedilir,
komutlar zaman aşımıyla kesilir ve çıktı kırpılır.
"""
import json
import posixpath
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

CIKTI_SINIRI = 8000
KOMUT_SURESI = 60

ARACLAR = [
    {"type": "function", "function": {
        "name": "Write",
        "description": "Çalışma klasörüne dosya yazar; dosya varsa üzerine yazar. Ara klasörler kendiliğinden oluşur.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Göreli dosya yolu, ör. src/hesap.py"},
            "content": {"type": "string", "description": "Dosyanın tam içeriği"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {
        "name": "Read",
        "description": "Çalışma klasöründeki bir dosyayı okur.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Göreli dosya yolu"}},
            "required": ["path"]}}},
    {"type": "function", "function": {
        "name": "Edit",
        "description": "Dosyada old_string metnini new_string ile değiştirir. old_string dosyada tam olarak bir kez geçmelidir.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"},
            "old_string": {"type": "string"},
            "new_string": {"type": "string"}},
            "required": ["path", "old_string", "new_string"]}}},
    {"type": "function", "function": {
        "name": "Bash",
        "description": f"Çalışma klasöründe bir kabuk komutu çalıştırır (ör. python main.py, pytest -q). "
                       f"İnternet erişimi yoktur; {KOMUT_SURESI} sn sonra kesilir.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}},
            "required": ["command"]}}},
    {"type": "function", "function": {
        "name": "Done",
        "description": "Görev bittiğinde çağır. summary: ne yaptığının kısa Türkçe özeti.",
        "parameters": {"type": "object", "properties": {
            "summary": {"type": "string"}},
            "required": ["summary"]}}},
]

# Ağ, yetki yükseltme, sistem ve klasör dışı yıkıcı işlemler. Sandbox'ta ağ zaten kapalı; bu liste yerel modu da korur.
YASAK_KALIPLAR = [
    r"\b(curl|wget|nc|ncat|netcat|ssh|scp|sftp|ftp|telnet|rsync)\b",
    r"\b(sudo|su|doas|chown|mount|umount|mkfs|dd|shutdown|reboot|systemctl|crontab)\b",
    r"\bpip3?\s+(install|download)\b", r"\b(apt|apt-get|yum|dnf|apk|brew|npm|yarn)\s+(install|add)\b",
    r"\brm\s+(-[a-zA-Z]*\s+)*(/|~|\.\.)",
    r"(^|[\s;&|<>=\"'])(/|~)(?!work\b|dev/null\b|tmp\b)",   # mutlak yol veya ev dizini (/work, /dev/null, /tmp dışında)
    r"\.\.(/|\\|$|\s)",                                      # üst klasöre çıkış
    r"\b(socket|urllib|requests|http\.client|httpx|aiohttp)\b",
    r":\(\)\s*\{",                                            # fork bombası
]


class AracHatasi(Exception):
    pass


def guvenli_yol(yol: str) -> str:
    """Göreli, klasör içinde kalan normalleştirilmiş POSIX yolu döndürür; değilse AracHatasi."""
    if not isinstance(yol, str) or not yol.strip():
        raise AracHatasi("yol boş")
    y = yol.strip().replace("\\", "/")
    if y.startswith("./"):
        y = y[2:]
    if y.startswith("/work/"):
        y = y[len("/work/"):]
    if y.startswith("/") or re.match(r"^[a-zA-Z]:", y) or y.startswith("~"):
        raise AracHatasi(f"mutlak yol reddedildi: {yol}")
    n = posixpath.normpath(y)
    if n == "." or n.startswith("..") or "/../" in f"/{n}/":
        raise AracHatasi(f"çalışma klasörü dışına çıkan yol reddedildi: {yol}")
    return n


def komut_denetle(komut: str) -> None:
    if not isinstance(komut, str) or not komut.strip():
        raise AracHatasi("komut boş")
    for k in YASAK_KALIPLAR:
        if re.search(k, komut):
            raise AracHatasi(f"komut güvenlik kuralı nedeniyle reddedildi (kalıp: {k})")


def _kirp(s: str) -> str:
    if len(s) <= CIKTI_SINIRI:
        return s
    yarim = CIKTI_SINIRI // 2
    return s[:yarim] + f"\n... [{len(s) - CIKTI_SINIRI} karakter kırpıldı] ...\n" + s[-yarim:]


class Calisma:
    """Ortak araç mantığı; alt sınıflar _yaz/_oku/_calistir/_listele/kapat sağlar."""

    def arac_calistir(self, ad: str, arg: dict) -> str:
        try:
            if ad == "Write":
                yol = guvenli_yol(arg["path"])
                icerik = arg.get("content", "")
                if isinstance(icerik, (dict, list)):
                    icerik = json.dumps(icerik, ensure_ascii=False, indent=2)  # model JSON dosyasını nesne olarak verdi
                elif not isinstance(icerik, str):
                    raise AracHatasi("content metin olmalı")
                self._yaz(yol, icerik)
                return f"{yol} yazıldı ({len(icerik)} karakter)."
            if ad == "Read":
                return _kirp(self._oku(guvenli_yol(arg["path"])))
            if ad == "Edit":
                yol = guvenli_yol(arg["path"])
                eski, yeni = arg["old_string"], arg["new_string"]
                if not isinstance(eski, str) or not isinstance(yeni, str) or not eski:
                    raise AracHatasi("old_string ve new_string metin olmalı; old_string boş olamaz")
                metin = self._oku(yol)
                adet = metin.count(eski)
                if adet != 1:
                    raise AracHatasi(f"old_string dosyada {adet} kez geçiyor; tam olarak 1 olmalı")
                self._yaz(yol, metin.replace(eski, yeni, 1))
                return f"{yol} düzenlendi."
            if ad == "Bash":
                komut_denetle(arg["command"])
                kod, cikti = self._calistir(arg["command"], KOMUT_SURESI)
                return _kirp(f"[çıkış kodu {kod}]\n{cikti}")
            raise AracHatasi(f"bilinmeyen araç: {ad}")
        except AracHatasi as e:
            return f"HATA: {e}"
        except KeyError as e:
            return f"HATA: eksik argüman {e}"
        except FileNotFoundError:
            return f"HATA: dosya bulunamadı: {arg.get('path')}"
        except (TypeError, AttributeError) as e:
            return f"HATA: geçersiz argüman ({e})"

    def dosyalar(self) -> dict:
        """Çalışma alanındaki metin dosyalarını {yol: içerik} olarak döndürür (sonuç ekranı ve test için)."""
        sonuc = {}
        for yol in self._listele():
            try:
                sonuc[yol] = self._oku(yol)
            except Exception:
                pass
        return sonuc

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.kapat()


class YerelCalisma(Calisma):
    def __init__(self):
        self.kok = Path(tempfile.mkdtemp(prefix="usta_"))

    def _tam(self, yol: str) -> Path:
        p = (self.kok / yol).resolve()
        if self.kok.resolve() not in p.parents and p != self.kok.resolve():
            raise AracHatasi(f"çalışma klasörü dışına çıkan yol reddedildi: {yol}")
        return p

    def _yaz(self, yol, icerik):
        p = self._tam(yol)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(icerik, encoding="utf-8")

    def _oku(self, yol):
        return self._tam(yol).read_text(encoding="utf-8")

    def _calistir(self, komut, sure):
        bash = shutil.which("bash") or "bash"
        try:
            r = subprocess.run([bash, "-c", komut], cwd=self.kok, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=sure)
            return r.returncode, (r.stdout + r.stderr)
        except subprocess.TimeoutExpired:
            return 124, f"zaman aşımı: {sure} sn"

    def _listele(self):
        return sorted(str(p.relative_to(self.kok)).replace("\\", "/") for p in self.kok.rglob("*")
                      if p.is_file() and "__pycache__" not in p.parts and ".pytest_cache" not in p.parts)

    def kapat(self):
        shutil.rmtree(self.kok, ignore_errors=True)


class ModalCalisma(Calisma):
    """Görev başına bir Modal Sandbox: ağ kapalı, yalnızca /work."""

    def __init__(self, zaman_asimi: int = 3600):
        import modal
        app = modal.App.lookup("usta-calisma", create_if_missing=True)
        imaj = modal.Image.debian_slim(python_version="3.12").pip_install("pytest==8.3.3")
        self.sb = modal.Sandbox.create(app=app, image=imaj, block_network=True, timeout=zaman_asimi,
                                       workdir="/work", cpu=1.0, memory=1024)
        self.sb.filesystem.make_directory("/work")

    def _yaz(self, yol, icerik):
        ust = posixpath.dirname(yol)
        if ust:
            self.sb.filesystem.make_directory(f"/work/{ust}")
        self.sb.filesystem.write_text(icerik, f"/work/{yol}")

    def _oku(self, yol):
        try:
            return self.sb.filesystem.read_text(f"/work/{yol}")
        except Exception as e:
            if "not found" in str(e).lower() or "no such" in str(e).lower():
                raise FileNotFoundError(yol)
            raise

    def _calistir(self, komut, sure):
        p = self.sb.exec("bash", "-c", f"timeout {sure} bash -c {_tirnak(komut)} 2>&1", workdir="/work",
                         timeout=sure + 15)
        cikti = p.stdout.read()
        kod = p.wait()
        if kod == 124:
            cikti += f"\nzaman aşımı: {sure} sn"
        return kod, cikti

    def _listele(self):
        p = self.sb.exec("bash", "-c", "find . -type f -not -path '*/__pycache__/*' -not -path '*/.pytest_cache/*' "
                         "-size -200k | sed 's|^./||' | sort", workdir="/work")
        out = p.stdout.read()
        p.wait()
        return [s for s in out.splitlines() if s]

    def kapat(self):
        try:
            self.sb.terminate()
        except Exception:
            pass


def _tirnak(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


def calisma_ac(tur: str = "modal") -> Calisma:
    return ModalCalisma() if tur == "modal" else YerelCalisma()
