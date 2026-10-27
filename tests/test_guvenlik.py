"""Araç çalıştırıcısı ve web arayüzü için saldırı testleri (kötü niyetli ya da hatalı model çıktısı).

Kurallar: yalnızca YerelCalisma, yalnızca geçici klasörler; ağ yok, Modal yok. Yükler zararsızdır:
gerçek dosya silinmez, gerçek anahtar okunmaz — sahte nöbetçi (sentinel) değerlerle açığın varlığı kanıtlanır.

Açık bulgular `xfail(strict=True)` ile işaretlidir: test GÜVENLİ davranışı ister ve bugün başarısız olur.
Bulgu düzeltildiğinde test XPASS verir ve strict yüzünden kırmızıya döner — o zaman işareti kaldırın.
Ayrıntılar ve önerilen düzeltmeler: tests/GUVENLIK.md
"""
import os
import subprocess
import tempfile
import threading
import time
from pathlib import Path

import pytest

from usta import arac
from usta.arac import CIKTI_SINIRI, AracHatasi, YerelCalisma, guvenli_yol, komut_denetle

NOBETCI = "USTA-SAHTE-ANAHTAR-7f3a9c"   # gerçek anahtar değil; sızıp sızmadığını izlemek için


def bulgu(no: str, neden: str):
    return pytest.mark.xfail(strict=True, reason=f"{no}: {neden}")


@pytest.fixture
def kafes(tmp_path, monkeypatch):
    """Çalışma klasörünü tmp_path/dis altında açar; böylece 'üst klasör' de geçici ve gözlenebilir olur."""
    dis = tmp_path / "dis"
    dis.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(dis))
    monkeypatch.setattr(arac, "KOMUT_SURESI", 5)
    with YerelCalisma() as c:
        assert c.kok.parent == dis
        yield c, dis


# ---------------------------------------------------------------- 1. Yol kaçışı (Write/Read/Edit)

KACAN_YOLLAR = [
    "../x", "..\\x", "a/../../x", "a\\..\\..\\x", "/etc/passwd", "/work/../x", "\\x", "~/x", "~root/x",
    "C:/Windows/win.ini", "C:\\Windows\\win.ini", "c:x", "D:", "\\\\sunucu\\pay\\x", "//sunucu/pay/x",
    "\\\\?\\C:\\x", "\\\\.\\pipe\\x", " ../x", "./../x", "a/./../..", "..", ".", "", "   ",
]


@pytest.mark.parametrize("yol", KACAN_YOLLAR)
def test_kacan_yol_reddedilir(yol):
    with pytest.raises(AracHatasi):
        guvenli_yol(yol)


# guvenli_yol'dan geçen ama "garip" yollar: ikinci savunma hattı (_tam: resolve + parents) dışarı yazdırmamalı.
GARIP_YOLLAR = ["a/../C:/x.txt", "a/..//sunucu/x.txt", "file:///etc/x.txt", "%2e%2e/x.txt", "x/C:/y.txt",
                "a/../~/x.txt", "con.txt", "x.txt:akis", "a" * 200 + "/b.txt"]


@pytest.mark.parametrize("yol", GARIP_YOLLAR)
def test_garip_yol_disari_yazamaz(kafes, yol):
    c, dis = kafes
    once = set(dis.rglob("*"))
    try:
        sonuc = c.arac_calistir("Write", {"path": yol, "content": "zararsız"})
    except (ValueError, OSError):
        sonuc = "HATA (istisna)"   # ayrı bulgu (B-4); burada yalnızca kaçış olmadığını denetliyoruz
    sonra = set(dis.rglob("*"))
    yeni = [p for p in sonra - once if c.kok not in p.parents and p != c.kok]
    assert not yeni, f"{yol!r} çalışma klasörü dışında dosya oluşturdu: {yeni} ({sonuc})"


def _bag_kur(hedef: Path, bag: Path, klasor: bool):
    try:
        os.symlink(hedef, bag, target_is_directory=klasor)
        return
    except (OSError, NotImplementedError):
        pass
    if klasor and os.name == "nt":   # yetkisiz Windows: klasör bağlantı noktası (junction) aynı saldırıyı temsil eder
        subprocess.run(["cmd", "/c", "mklink", "/J", str(bag), str(hedef)], capture_output=True)
        if bag.exists():
            return
    pytest.skip("bu sistemde sembolik bağ kurulamıyor (Windows'ta Geliştirici Modu gerekir)")


def test_sembolik_bag_klasor_ile_kacis_engellenir(kafes):
    c, dis = kafes
    (dis / "gizli.txt").write_text(NOBETCI, encoding="utf-8")
    _bag_kur(dis, c.kok / "bag", klasor=True)
    assert c.arac_calistir("Read", {"path": "bag/gizli.txt"}).startswith("HATA")
    assert c.arac_calistir("Write", {"path": "bag/yeni.txt", "content": "x"}).startswith("HATA")
    assert c.arac_calistir("Edit", {"path": "bag/gizli.txt", "old_string": NOBETCI, "new_string": "x"}).startswith("HATA")
    assert not (dis / "yeni.txt").exists()
    assert (dis / "gizli.txt").read_text(encoding="utf-8") == NOBETCI


def test_sembolik_bag_dosya_ile_kacis_engellenir(kafes):
    c, dis = kafes
    (dis / "gizli.txt").write_text(NOBETCI, encoding="utf-8")
    _bag_kur(dis / "gizli.txt", c.kok / "masum.py", klasor=False)
    assert NOBETCI not in c.arac_calistir("Read", {"path": "masum.py"})
    assert c.arac_calistir("Write", {"path": "masum.py", "content": "x"}).startswith("HATA")
    assert (dis / "gizli.txt").read_text(encoding="utf-8") == NOBETCI


def test_dosyalar_sembolik_bagi_izlemez(kafes):
    """Sonuç ekranına giden dosyalar() dışarıdaki dosyayı içeriğiyle sızdırmamalı."""
    c, dis = kafes
    (dis / "gizli.txt").write_text(NOBETCI, encoding="utf-8")
    _bag_kur(dis / "gizli.txt", c.kok / "masum.txt", klasor=False)
    assert NOBETCI not in "".join(c.dosyalar().values())


# ---------------------------------------------------------------- 2. Bash ile klasör dışına erişim (YerelCalisma)

@pytest.mark.parametrize("komut", [
    "cd ..; cat gizli.env",
    "cd ..&&cat gizli.env",
    "cat ${PWD%/*}/gizli.env",
    "python -c \"import os; print(open(os.path.join(os.pardir, 'gizli.env')).read())\"",
])
def test_bash_ust_klasoru_okuyamaz(kafes, komut):
    c, dis = kafes
    (dis / "gizli.env").write_text(f"USTA_GLIMMER_TOKEN={NOBETCI}\n", encoding="utf-8")
    assert NOBETCI not in c.arac_calistir("Bash", {"command": komut})


def test_bash_ust_klasore_yazamaz(kafes):
    c, dis = kafes
    c.arac_calistir("Bash", {"command": "cd ..; echo zararsiz > kacis.txt"})
    assert not (dis / "kacis.txt").exists()


def test_bash_ev_dizinindeki_anahtar_dosyasini_okuyamaz(kafes, tmp_path, monkeypatch):
    c, _ = kafes
    ev = tmp_path / "ev"
    ev.mkdir()
    (ev / ".pflow-anahtarlar.env").write_text(f"META_MODEL_API_KEY={NOBETCI}\n", encoding="utf-8")
    monkeypatch.setenv("HOME", str(ev))
    assert NOBETCI not in c.arac_calistir("Bash", {"command": "cat $HOME/.pflow-anahtarlar.env"})


# ---------------------------------------------------------------- 3. Ortam değişkenlerinden anahtar sızdırma

@pytest.mark.parametrize("komut", ["env", "printenv", "set",
                                   "python -c \"import os; print(dict(os.environ))\"",
                                   "echo $USTA_GLIMMER_TOKEN $META_MODEL_API_KEY"])
def test_ortamdaki_anahtar_sizmaz(kafes, monkeypatch, komut):
    c, _ = kafes
    monkeypatch.setenv("USTA_GLIMMER_TOKEN", NOBETCI)
    monkeypatch.setenv("META_MODEL_API_KEY", NOBETCI)
    assert NOBETCI not in c.arac_calistir("Bash", {"command": komut})


@pytest.mark.parametrize("komut", ["cat /proc/self/environ", "cat .env/../../.env", "cat ../.env", "cat ~/.env",
                                   "cat /work/../.env"])
def test_bilinen_anahtar_yollari_filtrede_reddedilir(komut):
    with pytest.raises(AracHatasi):
        komut_denetle(komut)


def test_read_araci_env_dosyasina_ulasamaz(kafes):
    c, dis = kafes
    (dis / ".env").write_text(f"USTA_GLIMMER_TOKEN={NOBETCI}\n", encoding="utf-8")
    for yol in ["../.env", "/work/../.env", ".env/../../.env", "..\\.env"]:
        assert NOBETCI not in c.arac_calistir("Read", {"path": yol})


# ---------------------------------------------------------------- 4. komut_denetle'yi atlatma
# Bunlar ÇALIŞTIRILMAZ; yalnızca filtreden geçtikleri gösterilir. Modal'da ağ kapalı olduğundan zararsızdır,
# yerel kipte ise filtre tek savunmadır.

ATLATMALAR = [
    "c''url http://ornek.invalid",                        # tırnak ekleme
    'cu""rl http://ornek.invalid',
    "c\\url http://ornek.invalid",                        # ters bölü kaçışı
    "$(echo Y3VybA== | base64 -d) http://ornek.invalid",  # base64 + alt kabuk
    "echo Y3VybCBodHRwOi8vb3JuZWsuaW52YWxpZA== | base64 -d | sh",
    "`printf 'c%sl' ur` http://ornek.invalid",            # ters tırnak alt kabuğu
    "python -c \"__import__('so'+'cket')\"",               # dinamik içe aktarma
    "python -c \"import ftplib\"", "python -c \"import smtplib\"", "python -c \"import xmlrpc.client\"",
    "python -m http.server 8000",
    "python -c \"import os; os.system('ls ' + chr(47))\"",  # chr(47) == '/'
    "perl -e 'print 1'", "node -e '1'", "powershell -c Get-ChildItem",
    "a=s; b=udo; $a$b ls",                                # değişkenle birleştirme
]


@bulgu("B-3", "kara liste tabanlı komut filtresi kolayca atlatılıyor (yerel kipte tek savunma)")
@pytest.mark.parametrize("komut", ATLATMALAR)
def test_komut_filtresi_atlatilamaz(komut):
    with pytest.raises(AracHatasi):
        komut_denetle(komut)


@pytest.mark.parametrize("komut", ["curl x", "wget x", "nc -l 1", "ssh a@b", "sudo ls", "pip install x",
                                   "python -m pip install x", "npm install x", "rm -rf /", "rm -rf ~", "rm -rf ..",
                                   "cat /etc/passwd", "ls;/bin/ls", "cat x|/bin/sh", ":(){ :|:& };:",
                                   "python -c 'import socket'", "python -c 'import urllib.request'",
                                   "ls //sunucu/pay", "ln -s /etc e", "ln -s .. up", "pushd .."])
def test_dogrudan_tehlikeli_komutlar_reddedilir(komut):
    with pytest.raises(AracHatasi):
        komut_denetle(komut)


# ---------------------------------------------------------------- 5. Hatalı model çıktısı görevi çökertmemeli

@pytest.mark.parametrize("ad,arg", [
    ("Read", {"path": "ikili.bin"}),
    ("Edit", {"path": "ikili.bin", "old_string": "a", "new_string": "b"}),
    ("Read", {"path": "klasor"}),
    ("Write", {"path": "klasor", "content": "x"}),
    ("Write", {"path": "a\x00b.py", "content": "x"}),
])
def test_bozuk_girdi_istisna_firlatmaz(kafes, ad, arg):
    c, _ = kafes
    (c.kok / "ikili.bin").write_bytes(b"\xff\xfe\x00\x81")
    (c.kok / "klasor").mkdir()
    sonuc = c.arac_calistir(ad, arg)   # istisna fırlatmamalı
    assert sonuc.startswith("HATA")


def test_ajan_ikili_dosya_okumasinda_cokmez(kafes, monkeypatch):
    from usta import ajan, glimmer
    c, _ = kafes
    (c.kok / "resim.png").write_bytes(b"\x89PNG\r\n\x1a\n\xff\xff")
    cevaplar = iter([
        {"content": "", "tool_calls": [{"id": "1", "function": {"name": "Read", "arguments": '{"path": "resim.png"}'}}],
         "_usage": {}, "_finish": "tool_calls"},
        {"content": "", "tool_calls": [{"id": "2", "function": {"name": "Done", "arguments": '{"summary": "tamam"}'}}],
         "_usage": {}, "_finish": "tool_calls"},
    ])
    monkeypatch.setattr(glimmer, "sohbet", lambda *a, **k: next(cevaplar))
    assert ajan.calistir("resmi oku", c)["bitti"]


def test_arguman_tipi_bozuksa_hata_metni_doner(kafes):
    c, _ = kafes
    for ad, arg in [("Write", {}), ("Write", {"path": None, "content": "x"}), ("Read", {"path": ["a"]}),
                    ("Edit", {"path": "a", "old_string": 1, "new_string": 2}), ("Bash", {"command": ""}),
                    ("Bash", {"command": None}), ("Sil", {"path": "a"}), ("Write", {"path": "a", "content": None})]:
        assert c.arac_calistir(ad, arg).startswith("HATA"), (ad, arg)


# ---------------------------------------------------------------- 6. Çıktı boyutu ve zaman sınırı

def test_buyuk_bash_ciktisi_kirpilir(kafes):
    c, _ = kafes
    sonuc = c.arac_calistir("Bash", {"command": "python -c \"print('x' * 3_000_000)\""})
    assert len(sonuc) < CIKTI_SINIRI + 200 and "kırpıldı" in sonuc


def test_buyuk_dosya_okumasi_kirpilir(kafes):
    c, _ = kafes
    c.arac_calistir("Write", {"path": "buyuk.txt", "content": "y" * 1_000_000})
    assert len(c.arac_calistir("Read", {"path": "buyuk.txt"})) < CIKTI_SINIRI + 200


def test_kabuk_ici_sonsuz_dongu_zaman_asimiyla_kesilir(kafes, monkeypatch):
    c, _ = kafes
    monkeypatch.setattr(arac, "KOMUT_SURESI", 1)
    bas = time.monotonic()
    sonuc = c.arac_calistir("Bash", {"command": "while :; do :; done"})
    assert "zaman aşımı" in sonuc and time.monotonic() - bas < 5


# DİKKAT: buradaki yükler kasıtlı olarak 6-8 sn ile SINIRLIDIR. Gerçek bir 'while True: pass' kullanmayın:
# bash öldürüldükten sonra python yetim kalır, sonsuza dek CPU yer ve arac_calistir hiç dönmez (elle denendi).
@pytest.mark.parametrize("komut", [
    "python -c \"import time; time.sleep(8)\"; echo son",     # bash çatallanır, python alt süreç olur
    "python -c \"import time; time.sleep(8)\" & echo arka",   # arka plan süreci boruyu açık tutar
    "python -c \"import time\nt = time.time()\nwhile time.time() - t < 6: pass\"; echo son",  # sınırlı meşgul döngü
])
def test_zaman_asimi_torun_surecleri_de_keser(kafes, monkeypatch, komut):
    c, _ = kafes
    monkeypatch.setattr(arac, "KOMUT_SURESI", 1)
    bas = time.monotonic()
    c.arac_calistir("Bash", {"command": komut})
    assert time.monotonic() - bas < 4


def test_write_boyut_siniri(kafes):
    c, _ = kafes
    assert c.arac_calistir("Write", {"path": "dev.txt", "content": "z" * 50_000_000}).startswith("HATA")


# ---------------------------------------------------------------- 7. Web arayüzü: girdi sınırları ve eşzamanlılık

@pytest.fixture
def istemci(monkeypatch):
    pytest.importorskip("fastapi")
    pytest.importorskip("httpx")
    pytest.importorskip("websockets")   # usta.web -> usta.ses
    from fastapi.testclient import TestClient
    from usta import web

    serbest = threading.Event()
    baslayan = []

    def sahte_yurut(is_id, gorev, kip):   # Modal/Glimmer açmadan görev yaşam döngüsünü taklit eder
        baslayan.append(is_id)
        web.ISLER[is_id].put({"tur": "asama", "veri": "sahte"})
        serbest.wait(10)
        web.ISLER[is_id].put(None)

    monkeypatch.setattr(web, "_yurut", sahte_yurut)
    monkeypatch.setattr(web, "ISLER", {})
    with TestClient(web.app, base_url="http://127.0.0.1:8765") as tc:
        yield tc, web, baslayan, serbest
    serbest.set()


@pytest.mark.parametrize("govde,kod", [
    ({"gorev": ""}, 400), ({"gorev": "   \n\t"}, 400), ({"gorev": "x" * 4001}, 400),
    ({"gorev": "x", "kip": "d"}, 400), ({"gorev": "x", "kip": "c; rm -rf /"}, 400),
    ({"gorev": 5}, 422), ({"gorev": None}, 422), ({"gorev": ["a"]}, 422), ({}, 422),
    ({"gorev": "x" * 2_000_000}, 400),
])
def test_web_gorev_girdisi_dogrulanir(istemci, govde, kod):
    tc, _, baslayan, _ = istemci
    assert tc.post("/api/gorev", json=govde).status_code == kod
    assert not baslayan


def test_web_gecerli_gorev_ve_akis(istemci):
    tc, web, _, serbest = istemci
    r = tc.post("/api/gorev", json={"gorev": "ç" * 4000, "kip": "a"})   # sınır karakter sayısı (8000 bayt)
    assert r.status_code == 200
    serbest.set()
    akis = tc.get(f"/api/olaylar/{r.json()['id']}").text
    assert "sahte" in akis and "event: son" in akis
    assert r.json()["id"] not in web.ISLER


@pytest.mark.parametrize("is_id", ["yok", "../../etc", "%2e%2e", "a" * 500])
def test_web_bilinmeyen_is_404(istemci, is_id):
    tc, *_ = istemci
    assert tc.get(f"/api/olaylar/{is_id}").status_code == 404


@pytest.mark.parametrize("tur", ["text/plain", "application/x-www-form-urlencoded", "multipart/form-data"])
def test_web_basit_capraz_kaynak_istegi_gorev_baslatamaz(istemci, tur):
    """Başka bir sitenin ön uçuşsuz (CORS 'simple request') formu görev açıp bütçe harcatamamalı."""
    tc, _, baslayan, _ = istemci
    r = tc.post("/api/gorev", content=b'{"gorev": "x", "kip": "c"}', headers={"content-type": tur})
    assert r.status_code == 422 and not baslayan


def test_web_yabanci_host_reddedilir(istemci):
    tc, *_ = istemci
    r = tc.post("/api/gorev", json={"gorev": "x"}, headers={"host": "kotu.example:8765"})
    assert r.status_code in (400, 403, 421)


def test_web_eszamanli_gorev_siniri(istemci):
    tc, _, baslayan, serbest = istemci
    kodlar = [tc.post("/api/gorev", json={"gorev": f"görev {i}"}).status_code for i in range(25)]
    serbest.set()
    assert 429 in kodlar or 503 in kodlar, f"{len(baslayan)} görev aynı anda başladı"


@bulgu("B-8", "olay akışına hiç bağlanılmayan işler ISLER sözlüğünde sonsuza dek kalıyor")
def test_web_sahipsiz_is_temizlenir(istemci):
    tc, web, _, serbest = istemci
    serbest.set()
    tc.post("/api/gorev", json={"gorev": "kimse dinlemiyor"})
    time.sleep(0.5)
    assert not web.ISLER


def test_web_ses_boyut_siniri(istemci, monkeypatch):
    tc, web, *_ = istemci
    monkeypatch.setattr(web.ses, "yaziya_cevir", lambda veri: "çağrılmamalıydı")
    r = tc.post("/api/ses", files={"dosya": ("a.wav", b"\0" * (10 * 1024 * 1024 + 1), "audio/wav")})
    assert r.status_code == 400


def test_web_arayuzu_model_ciktisini_html_olarak_yorumlamaz():
    """index.html model/dosya içeriğini yalnızca textContent ile basmalı (XSS yok)."""
    html = (Path(__file__).resolve().parent.parent / "usta" / "statik" / "index.html").read_text(encoding="utf-8")
    import re
    atamalar = re.findall(r"(innerHTML|outerHTML)\s*=\s*([^;]+);", html)
    assert all(deger.strip() in ('""', "''") for _, deger in atamalar), atamalar
    assert "insertAdjacentHTML" not in html and "document.write" not in html and "eval(" not in html
