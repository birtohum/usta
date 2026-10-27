import pytest

from usta.arac import AracHatasi, YerelCalisma, guvenli_yol, komut_denetle


@pytest.mark.parametrize("yol", ["../x.py", "/etc/passwd", "C:/Windows/x", "a/../../b", "~/.ssh/id", "..", "."])
def test_klasor_disi_yol_reddedilir(yol):
    with pytest.raises(AracHatasi):
        guvenli_yol(yol)


@pytest.mark.parametrize("yol,beklenen", [("a.py", "a.py"), ("./src/b.py", "src/b.py"), ("src\\c.py", "src/c.py"),
                                          ("/work/d.py", "d.py"), ("x/../y.py", "y.py")])
def test_gecerli_yol(yol, beklenen):
    assert guvenli_yol(yol) == beklenen


@pytest.mark.parametrize("komut", ["curl http://x", "pip install requests", "sudo ls", "rm -rf /", "cat /etc/passwd",
                                   "cat ../gizli", "python -c 'import socket'", "ls ~"])
def test_tehlikeli_komut_reddedilir(komut):
    with pytest.raises(AracHatasi):
        komut_denetle(komut)


@pytest.mark.parametrize("komut", ["python main.py", "pytest -q", "ls -la", "python -c 'print(1/2)'",
                                   "echo x > /dev/null", "rm -rf build"])
def test_zararsiz_komut_gecer(komut):
    komut_denetle(komut)


def test_yerel_arac_akisi():
    with YerelCalisma() as c:
        assert "yazıldı" in c.arac_calistir("Write", {"path": "p/a.py", "content": "print('selam')\n"})
        assert "selam" in c.arac_calistir("Read", {"path": "p/a.py"})
        assert "düzenlendi" in c.arac_calistir("Edit", {"path": "p/a.py", "old_string": "selam", "new_string": "merhaba"})
        cikti = c.arac_calistir("Bash", {"command": "python p/a.py"})
        assert "[çıkış kodu 0]" in cikti and "merhaba" in cikti
        assert c.arac_calistir("Write", {"path": "../kacis.py", "content": ""}).startswith("HATA")
        assert c.arac_calistir("Edit", {"path": "p/a.py", "old_string": "yok", "new_string": "x"}).startswith("HATA")
        assert list(c.dosyalar()) == ["p/a.py"]


def test_gecersiz_arguman_gorevi_cokertmez():
    with YerelCalisma() as c:
        assert "yazıldı" in c.arac_calistir("Write", {"path": "a.json", "content": {"x": 1}})
        assert '"x": 1' in c.arac_calistir("Read", {"path": "a.json"})
        assert c.arac_calistir("Write", {"path": "b.py", "content": 5}).startswith("HATA")
        assert c.arac_calistir("Write", {"path": 5, "content": ""}).startswith("HATA")
        assert c.arac_calistir("Edit", {"path": "a.json", "old_string": "", "new_string": "y"}).startswith("HATA")
        assert c.arac_calistir("Bash", {"command": ["ls"]}).startswith("HATA")


def test_geri_alma_yeni_dosyayi_siler_eskileri_geri_yazar():
    from usta.surec import _geri_al, _goruntu
    with YerelCalisma() as c:
        c.arac_calistir("Write", {"path": "a.py", "content": "x = 1\n"})
        goruntu = _goruntu(c)
        c.arac_calistir("Write", {"path": "a.py", "content": "x = 2\n"})
        c.arac_calistir("Write", {"path": "b.py", "content": ""})
        _geri_al(c, goruntu)
        assert c.dosyalar() == {"a.py": "x = 1\n"}


def test_yerel_kabuk_calisma_klasorunde_ve_wsl_degil():
    from usta.arac import _bash_bul
    b = _bash_bul()
    assert "system32" not in b.lower() and "windowsapps" not in b.lower()
    with YerelCalisma() as c:
        assert c.arac_calistir("Bash", {"command": "pwd"}).strip().endswith(c.kok.name)
