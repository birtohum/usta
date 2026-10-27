"""Araç çalıştırıcısı ve web arayüzü için saldırı testleri (kötü niyetli ya da hatalı model çıktısı).

Kurallar: YerelCalisma ve WslCalisma (usta-kum dağıtımı varsa), yalnızca geçici klasörler; ağ yok, Modal yok. Yükler zararsızdır:
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
from usta.arac import CIKTI_SINIRI, AracHatasi, WslCalisma, YerelCalisma, guvenli_yol, komut_denetle

NOBETCI = "USTA-SAHTE-ANAHTAR-7f3a9c"   # gerçek anahtar değil; sızıp sızmadığını izlemek için


def bulgu(no: str, neden: str):
    return pytest.mark.xfail(strict=True, reason=f"{no}: {neden}")


def _wsl_var() -> bool:
    if os.name != "nt":
        return False
    try:
        r = subprocess.run(["wsl.exe", "-l", "-q"], capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return arac.WSL_DAGITIM in r.stdout.replace(b"\0", b"").decode("utf-8", "ignore").split()


WSL_VAR = _wsl_var()
wsl_gerekli = pytest.mark.skipif(not WSL_VAR, reason=f"WSL dağıtımı '{arac.WSL_DAGITIM}' kurulu değil")


@pytest.fixture
def yerel_kafes(tmp_path, monkeypatch):
    """YerelCalisma'yı tmp_path/dis altında açar; böylece 'üst klasör' de geçici ve gözlenebilir olur."""
    dis = tmp_path / "dis"
    dis.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(dis))
    monkeypatch.setattr(arac, "KOMUT_SURESI", 5)
    with YerelCalisma() as c:
        assert c.kok.parent == dis
        yield c, dis


@pytest.fixture(params=["yerel", pytest.param("wsl", marks=wsl_gerekli)])
def kafes(request, tmp_path, monkeypatch):
    """Her iki çalıştırıcı. 'dis', Windows tarafında sırların durduğu yeri temsil eder (WSL'de çalışma klasörü
    dağıtımın içindedir; yerelde dis'in altındadır)."""
    if request.param == "yerel":
        yield request.getfixturevalue("yerel_kafes")
        return
    dis = tmp_path / "dis"
    dis.mkdir()
    monkeypatch.setattr(arac, "KOMUT_SURESI", 5)
    with WslCalisma() as c:
        yield c, dis


def _icerde(c, isim: str):
    """Çalışma klasöründe ikili dosya ve klasör hazırlar (filtreyi atlayarak, iki çalıştırıcıda da aynı yolla)."""
    c._calistir(f"printf '\\211PNG\\377\\376\\000\\201' > {isim}; mkdir -p klasor", 10)


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
    yeni = [p for p in sonra - once if not isinstance(c.kok, Path) or (c.kok not in p.parents and p != c.kok)]
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


def test_sembolik_bag_klasor_ile_kacis_engellenir(yerel_kafes):
    c, dis = yerel_kafes
    (dis / "gizli.txt").write_text(NOBETCI, encoding="utf-8")
    _bag_kur(dis, c.kok / "bag", klasor=True)
    assert c.arac_calistir("Read", {"path": "bag/gizli.txt"}).startswith("HATA")
    assert c.arac_calistir("Write", {"path": "bag/yeni.txt", "content": "x"}).startswith("HATA")
    assert c.arac_calistir("Edit", {"path": "bag/gizli.txt", "old_string": NOBETCI, "new_string": "x"}).startswith("HATA")
    assert not (dis / "yeni.txt").exists()
    assert (dis / "gizli.txt").read_text(encoding="utf-8") == NOBETCI


def test_sembolik_bag_dosya_ile_kacis_engellenir(yerel_kafes):
    c, dis = yerel_kafes
    (dis / "gizli.txt").write_text(NOBETCI, encoding="utf-8")
    _bag_kur(dis / "gizli.txt", c.kok / "masum.py", klasor=False)
    assert NOBETCI not in c.arac_calistir("Read", {"path": "masum.py"})
    assert c.arac_calistir("Write", {"path": "masum.py", "content": "x"}).startswith("HATA")
    assert (dis / "gizli.txt").read_text(encoding="utf-8") == NOBETCI


def test_dosyalar_sembolik_bagi_izlemez(yerel_kafes):
    """Sonuç ekranına giden dosyalar() dışarıdaki dosyayı içeriğiyle sızdırmamalı."""
    c, dis = yerel_kafes
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
    _icerde(c, "ikili.bin")
    sonuc = c.arac_calistir(ad, arg)   # istisna fırlatmamalı
    assert sonuc.startswith("HATA")


def test_ajan_ikili_dosya_okumasinda_cokmez(kafes, monkeypatch):
    from usta import ajan, glimmer
    c, _ = kafes
    _icerde(c, "resim.png")
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

    def sahte_yurut(is_id, *_):   # Modal/Glimmer açmadan görev yaşam döngüsünü taklit eder
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


# ---------------------------------------------------------------- 8. Yanlış kabuk (WSL) seçimi — B-9, main 17551c0'da düzeltildi
# PATH'teki 'bash' Windows'ta çoğu zaman WindowsApps\bash.exe (WSL) olur; WSL komutları çalışma klasöründe değil
# Linux ev dizininde çalıştırır. Bu testler WSL'i hiç başlatmaz.

WSL_YOLLARI = [r"C:\Windows\System32\bash.exe",
               str(Path(os.environ.get("LOCALAPPDATA", r"C:\Users\x\AppData\Local")) / "Microsoft" / "WindowsApps" / "bash.exe")]
yalniz_windows = pytest.mark.skipif(os.name != "nt", reason="WSL bash seçimi yalnızca Windows'ta anlamlı")


@yalniz_windows
def test_path_yalnizca_wsl_iken_kabuk_calisma_klasorunde_acilir(monkeypatch):
    """PATH'te yalnızca System32 ve WindowsApps varken ya Git Bash bulunur ve pwd çalışma klasörüdür, ya da açılış reddedilir."""
    monkeypatch.setenv("PATH", os.pathsep.join(str(Path(y).parent) for y in WSL_YOLLARI))
    monkeypatch.delenv("USTA_BASH", raising=False)
    try:
        c = YerelCalisma()
    except RuntimeError:
        return   # Git Bash bulunamadı: hiçbir komut çalışmadan reddedildi (kabul edilebilir)
    with c:
        assert not any(k in c.bash.lower() for k in ("system32", "windowsapps")), c.bash
        assert c.arac_calistir("Bash", {"command": "pwd"}).strip().endswith(c.kok.name)


@yalniz_windows
@pytest.mark.parametrize("wsl", WSL_YOLLARI)
def test_usta_bash_wsl_gosterse_de_kullanilmaz(monkeypatch, wsl):
    monkeypatch.setenv("USTA_BASH", wsl)
    try:
        b = arac._bash_bul()
    except RuntimeError:
        return
    assert b.lower() != wsl.lower() and "windowsapps" not in b.lower() and "system32" not in b.lower()


def test_kabuk_baska_klasorde_acilirsa_calisma_reddedilir(monkeypatch, tmp_path):
    """pwd çalışma klasörünü göstermiyorsa (WSL'deki /home/... gibi) YerelCalisma açılmamalı ve klasörü silmeli."""
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    monkeypatch.setattr(YerelCalisma, "_calistir", lambda self, komut, sure: (0, "/home/kullanici\n"))
    with pytest.raises(RuntimeError):
        YerelCalisma()
    assert not list(tmp_path.glob("usta_*")), "reddedilen çalışma klasörü silinmedi"


# ---------------------------------------------------------------- 9. Mutlak yolu gizleyerek klasör dışı okuma — B-10
# calisma_ac() varsayılanı "yerel" olduğundan (main 5f75d83) web arayüzü de bu kipte çalışır. Yol filtreleri yalnızca
# komut metnine bakar; yol hex/chr ile kurulursa hiçbir kalıp eşleşmez.

def _gizli_okuma_komutlari(gizli: Path) -> list[str]:
    wsl_yolu = "/mnt/" + gizli.drive[0].lower() + gizli.as_posix()[2:] if gizli.drive else gizli.as_posix()
    return [f"python -c \"print(open(bytes.fromhex('{y.encode().hex()}').decode()).read())\""
            for y in (str(gizli), wsl_yolu)]


@bulgu("B-10", "yerel kipte mutlak yol hex ile gizlenince klasör dışındaki dosya (ör. ~/.pflow-anahtarlar.env) okunabiliyor")
def test_gizlenmis_mutlak_yol_ile_disari_okunamaz_yerel(yerel_kafes):
    c, dis = yerel_kafes
    gizli = dis / "anahtarlar.env"
    gizli.write_text(f"META_MODEL_API_KEY={NOBETCI}\n", encoding="utf-8")
    komut = _gizli_okuma_komutlari(gizli)[0]
    komut_denetle(komut)   # filtreden geçtiğini ayrıca göster
    assert NOBETCI not in c.arac_calistir("Bash", {"command": komut})


@wsl_gerekli
def test_gizlenmis_mutlak_yol_ile_disari_okunamaz_wsl(tmp_path):
    """B-10 düzeltmesi: WslCalisma'da Windows dosya sistemi hiç bağlı değil."""
    gizli = tmp_path / "anahtarlar.env"
    gizli.write_text(f"META_MODEL_API_KEY={NOBETCI}\n", encoding="utf-8")
    with WslCalisma() as c:
        for komut in _gizli_okuma_komutlari(gizli):
            komut_denetle(komut)
            assert NOBETCI not in c.arac_calistir("Bash", {"command": komut})
            assert NOBETCI not in c._calistir(komut, 20)[1]   # filtre hiç olmasa da


@wsl_gerekli
def test_wsl_icinden_windows_ve_ag_erisilemez():
    """Filtreyi atlayarak (_calistir) dener: Windows sürücüleri, .exe'ler, ağ ve root yetkisi yok.
    Gerçek anahtar dosyalarına dokunmaz: yalnızca bağlama noktalarını ve çalıştırılabilirleri yoklar."""
    with WslCalisma() as c:
        kod, cikti = c._calistir("id -u; ls -A /mnt/c | wc -l; ls /mnt/c/Windows 2>&1 | head -1", 20)
        satir = cikti.splitlines()
        assert satir[0] != "0" and satir[1] == "0" and "No such file" in satir[2], cikti
        for exe in ["cmd.exe /c ver", "/mnt/c/Windows/System32/cmd.exe /c ver", "powershell.exe -c 1", "wsl.exe -l",
                    "explorer.exe ."]:
            kod, cikti = c._calistir(exe, 20)
            assert kod != 0 and ("not found" in cikti or "No such file" in cikti), (exe, cikti)
        # yalnızca salt okunur GPU sürücü klasörü (/usr/lib/wsl/drivers) bağlı; Windows sürücüsü (drvfs) yok
        kod, cikti = c._calistir("mount | grep -i -E 'drvfs|9p' | grep -v /usr/lib/wsl/drivers | wc -l", 20)
        assert cikti.split()[-1] == "0", cikti
        kod, cikti = c._calistir("python -c \"import socket; socket.create_connection(('1.1.1.1', 53), 3)\"", 20)
        assert kod != 0 and "unreachable" in cikti.lower(), cikti
        kod, cikti = c._calistir("sudo -n true", 20)
        assert kod != 0


@wsl_gerekli
def test_wsl_sembolik_bag_ile_kacis_engellenir():
    with WslCalisma() as c:
        c._calistir("ln -s /etc bag; ln -s /etc/passwd masum.txt", 10)
        assert c.arac_calistir("Read", {"path": "bag/passwd"}).startswith("HATA")
        assert c.arac_calistir("Read", {"path": "masum.txt"}).startswith("HATA")
        assert c.arac_calistir("Write", {"path": "bag/yeni", "content": "x"}).startswith("HATA")
        assert "root:" not in "".join(c.dosyalar().values())


def test_calisma_ac_varsayilani_wsl_yerel_yalniz_acikca(monkeypatch, capsys):
    monkeypatch.delenv("USTA_CALISMA", raising=False)
    monkeypatch.setattr(arac, "WslCalisma", lambda: "wsl")
    assert arac.calisma_ac() == "wsl"
    monkeypatch.setenv("USTA_CALISMA", "yerel")
    with arac.calisma_ac() as c:
        assert isinstance(c, YerelCalisma)
    assert "UYARI" in capsys.readouterr().err
