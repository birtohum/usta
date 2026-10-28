"""Bağımsız doğrulayıcı: Muse Spark, görev metninden (ajanın kodunu görmeden) adlandırma sözleşmesi ve pytest kabul testleri yazar.

Yazan (yürütücü) ile doğrulayan (ayrı Spark çağrıları) birbirinin içeriğini görmez; testler ajan Done dedikten sonra
çalışma alanına (her seferinde yeniden) yazılıp koşturulur.

Kabul testleri:
  1. Üç bağımsız yazar (uç durum / gereksinim / Türkçe-yerel kural odaklı) ayrı dosyalara test ve birer referans çözüm yazar.
  2. Bir test, üç referans çözümün en az ikisinde geçerse tutulur (hatalı beklentiler ayıklanır).
  3. Mutasyon: Spark referans çözümde görevin açık bir gereksinimini çiğneyen küçük değişiklikler (mutantlar) üretir;
     testler bunları öldürmeli. Sağ kalan mutantlar için hedefli test eklenir (en çok MUTASYON_TURU tur).
Test kimlikleri pytest düğüm kimliğidir: ".usta_kabul/test_kabul_1.py::test_ad".
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor

from usta import spark
from usta.arac import guvenli_yol

KABUL_KLASORU = ".usta_kabul"
KABUL_DOSYASI = KABUL_KLASORU  # geriye uyum: düzeltme mesajında gösterilen yol
INCELEME_DOSYASI = f"{KABUL_KLASORU}/test_inceleme.py"
MUTASYON_TURU = 2
BASLIK = "import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))"

SOZLESME_ISTEMI = """Aşağıdaki Türkçe yazılım görevi bir kodlama ajanına verilecek; işi sonra dışarıdan testle doğrulayacağız.
Testlerin ajanın koduna bağlanabilmesi için ADLANDIRMA sözleşmesi gerekiyor: dosya adları, fonksiyon/sınıf/metot adları
ve imzaları (komut satırı programıysa çağrı biçimi).

Kurallar:
- Görev bunların hepsini zaten açıkça belirtiyorsa sözleşme gereksizdir: {{"arayuz": ""}} döndür.
- Eksik olanları en basit, en olağan biçimde seç. Davranış kuralı, hata türü, biçim ya da uç durum EKLEME ve görevdeki
  davranışı yeniden yazma; davranışı yalnızca görev metni belirler.
- Türkçe karakterlerle kısa yaz.

GÖREV:
{gorev}

Yalnızca şu JSON'u döndür: {{"arayuz": "..."}}"""

ODAKLAR = [
    "UÇ DURUMLAR: sınırda eşitlik, boş/tek elemanlı girdi, en küçük/en büyük değerler, geçersiz girdide hangi hatanın "
    "(ve hangi sırayla) yükseldiği, yuvarlama yönü",
    "GEREKSİNİMLER: görev metnindeki her gereksinimi tek tek, normal kullanım senaryolarıyla; çıktı biçimi ve sıralama",
    "TÜRKÇE VE YEREL KURALLAR: İ/i ve I/ı dönüşümü, Türk alfabesiyle sıralama, Decimal ile kuruş yuvarlama, Türkçe gün/ay "
    "adları ve tarih biçimleri, Türkiye'ye özgü numara/kimlik kuralları; görevde bunlar yoksa biçim ve hata kuralları",
]

TEST_ISTEMI = """Bir kodlama ajanı aşağıdaki görevi yapıyor. Ajanın kodunu görmeyeceksin; işi dışarıdan doğrulayacak testler yaz.

GÖREV:
{gorev}

ADLANDIRMA SÖZLEŞMESİ (ajan buna uyacak; boşsa görevdeki adlar geçerlidir):
{arayuz}

Bu testlerde ağırlık: {odak}

İki şey üret:
1. "testler": pytest kabul testleri (tek dosya). Kurallar:
   - Dosya çalışma klasörünün alt klasöründe (.usta_kabul/) duracak; en başta şunu koy:
     {baslik}
   - Yalnızca GÖREV metninde açıkça yazan davranışı test et. Sözleşme yalnızca adlar içindir; metinde olmayan bir
     ayrıntıyı (hata mesajı metni, belirtilmemiş biçim, varsayılan değer, dönüş türünün iç yapısı) test etme.
   - Gereksinimleri kendi içinde tek tek çıkar, her biri için en az bir test yaz; sınır değerlerini iki taraftan dene.
     Toplam 10-18 test. Her test kısa ve tek şeyi denesin; test adı gereksinimi anlatsın.
   - Komut satırı programıysa subprocess ile sys.executable kullanarak çalıştır, cwd çalışma klasörü olsun; gereken
     girdi dosyalarını tmp_path'e oluştur.
   - Ağ, rastgelelik, zaman ya da dosya sistemi dışına bağımlılık yok.
2. "cozum": Sözleşmeye uyan, görevi eksiksiz yapan referans çözüm, dosya adı -> içerik sözlüğü. Ajana gösterilmez;
   testlerdeki hatalı beklentileri ayıklamak ve mutasyon testi için kullanılır.

Yalnızca şu JSON'u döndür (başka metin yok):
{{"testler": "...", "cozum": {{"dosya.py": "..."}}}}"""

MUTANT_ISTEMI = """Aşağıda bir görev ve onu doğru yapan bir referans çözüm var. Testlerimizin gücünü ölçmek için bu çözümün
12-16 adet HATALI varyantını (mutant) üret.

GÖREV:
{gorev}

REFERANS ÇÖZÜM:
{cozum}

Her mutant:
- Tek, küçük bir metin değişikliği olsun: "eski" parçası ilgili dosyada TAM OLARAK BİR KEZ geçmeli, "yeni" onun yerine gelir.
- Görev metninde AÇIKÇA yazan bir gereksinimi çiğnesin (ör. sınırda < yerine <=, yanlış yuvarlama yönü, Türkçe harf
  dönüşümünü atlama, yanlış hata türü, sıralamada eşitlik kuralını bozma, bir uç durumu yok sayma). Görevin belirtmediği
  bir ayrıntıyı değiştiren ya da davranışı değiştirmeyen (eşdeğer) mutant üretme.
- Sözdizimi geçerli Python kalsın; mutantlar farklı gereksinimlere dağılsın.

Yalnızca JSON döndür: {{"mutantlar": [{{"dosya": "x.py", "eski": "...", "yeni": "...", "aciklama": "hangi gereksinim"}}]}}"""

GUCLENDIR_ISTEMI = """Bir görev için kabul testlerimiz var ama aşağıdaki hatalı varyantlar (mutantlar) testlerden sağ çıktı:
testlerin hiçbiri bu hataları yakalamadı.

GÖREV:
{gorev}

ADLANDIRMA SÖZLEŞMESİ:
{arayuz}

SAĞ KALAN MUTANTLAR (referans çözümde yapılan değişiklik ve çiğnediği gereksinim):
{mutantlar}

Bu hataları yakalayan yeni pytest testleri yaz (tek dosya, en çok 10 test). Kurallar:
- Her test görev metninde AÇIKÇA yazan bir davranışı denesin; doğru bir çözümde geçmeli, ilgili mutantta kalmalı.
- Mutant görevin belirtmediği bir ayrıntıyı değiştiriyorsa ona test yazma.
- Dosyanın başına şunu koy: {baslik}
  ve gereken importları ekle. Komut satırı programları için subprocess + sys.executable, girdi dosyaları tmp_path'e.

Yalnızca JSON döndür: {{"testler": "..."}}"""


def _json_ayikla(metin: str) -> dict:
    metin = (metin or "").strip()
    m = re.search(r"```(?:json)?\s*(\{.*\})\s*```", metin, re.S)
    if m:
        metin = m.group(1)
    bas, son = metin.find("{"), metin.rfind("}")
    return json.loads(metin[bas:son + 1])


def _dosyalar(testler) -> dict:
    """Test kümesini {yol: kaynak} biçimine getirir (eski tek-metin biçimini de kabul eder)."""
    return {f"{KABUL_KLASORU}/test_kabul.py": testler} if isinstance(testler, str) else dict(testler)


def testler_metni(testler) -> str:
    """Arayüz ve hakem için tüm test dosyalarının birleşik görünümü."""
    return "\n\n".join(f"# === {yol} ===\n{kaynak}" for yol, kaynak in _dosyalar(testler).items())


def test_kimlikleri(testler) -> list:
    return [f"{yol}::{ad}" for yol, kaynak in _dosyalar(testler).items() for ad in re.findall(r"^def (test_\w+)", kaynak, re.M)]


def sozlesme_yaz(gorev: str, deneme: int = 3) -> dict:
    """{'arayuz', 'maliyet'} döndürür. Hızlı olsun diye düşük akıl yürütme düzeyiyle çağrılır."""
    maliyet = 0.0
    for _ in range(deneme):
        m = spark.sohbet([{"role": "user", "content": SOZLESME_ISTEMI.format(gorev=gorev)}],
                         max_tokens=8000, reasoning_effort="low")
        maliyet += m["_maliyet"]
        try:
            return {"arayuz": (_json_ayikla(m.get("content"))["arayuz"] or "").strip(), "maliyet": maliyet}
        except (ValueError, KeyError, AttributeError, json.JSONDecodeError):
            continue
    raise RuntimeError("Spark arayüz sözleşmesi üretemedi")


def _bir_yazar(gorev: str, arayuz: str, odak: str, deneme: int = 3) -> dict | None:
    maliyet = 0.0
    for _ in range(deneme):
        m = spark.sohbet([{"role": "user", "content": TEST_ISTEMI.format(gorev=gorev, arayuz=arayuz, odak=odak,
                                                                         baslik=BASLIK)}],
                         max_tokens=16000, reasoning_effort="medium", temperature=0.4)
        maliyet += m["_maliyet"]
        try:
            veri = _json_ayikla(m.get("content"))
            compile(veri["testler"], "test.py", "exec")
            for yol, kod in (veri.get("cozum") or {}).items():
                compile(kod, yol, "exec")   # derlenmeyen referans (ör. kaçışlı Unicode satırı) kabul edilmez
            if "def test_" in veri["testler"] and isinstance(veri.get("cozum"), dict) and veri["cozum"]:
                return {"testler": veri["testler"], "cozum": veri["cozum"], "maliyet": maliyet}
        except (ValueError, KeyError, SyntaxError, TypeError, json.JSONDecodeError):
            continue
    return {"testler": None, "cozum": None, "maliyet": maliyet}


def _pytest(hedef: str, iptal: list, ek: str = "-rf") -> str:
    secim = " ".join(f"--deselect {t}" for t in iptal)
    return f"python -m pytest -q {ek} -p no:cacheprovider {hedef} {secim}"


def _referansta_kalanlar(testler: dict, cozum: dict) -> tuple[set, int]:
    """Testleri bir referans çözüme karşı ayrı bir çalışma alanında koşturur; (kalan kimlikler, toplam) döndürür."""
    from usta.arac import calisma_ac
    with calisma_ac() as c:
        for yol, icerik in cozum.items():
            c._yaz(guvenli_yol(yol), icerik)
        for yol, kaynak in testler.items():
            c._yaz(yol, kaynak)
        _, cikti = c._calistir(_pytest(KABUL_KLASORU, []) + " 2>&1 | tail -n 120", 300)
    return set(kalan_testler(cikti, testler)), sum(int(x) for x in re.findall(r"(\d+) (?:passed|failed|error)", cikti))


def _mutant_dosyasi(cozum: dict, dosya) -> str | None:
    """Mutantın dosya adını çözümdeki anahtara eşler ('./x.py', 'src/x.py' ya da yalnızca 'x.py' yazılmış olabilir)."""
    if not isinstance(dosya, str):
        return None
    if dosya in cozum:
        return dosya
    ad = dosya.replace("\\", "/").lstrip("./").split("/")[-1]
    adaylar = [k for k in cozum if k.replace("\\", "/").split("/")[-1] == ad]
    if len(adaylar) == 1:
        return adaylar[0]
    return next(iter(cozum)) if len(cozum) == 1 else None


def _mutant_uygula(cozum: dict, mutant: dict) -> dict | None:
    dosya = _mutant_dosyasi(cozum, mutant.get("dosya"))
    eski, yeni = mutant.get("eski"), mutant.get("yeni")
    if dosya is None or not isinstance(eski, str) or not isinstance(yeni, str) or eski == yeni:
        return None
    if cozum[dosya].count(eski) != 1:
        return None
    yeni_kod = cozum[dosya].replace(eski, yeni, 1)
    try:
        compile(yeni_kod, dosya, "exec")
    except SyntaxError:
        return None
    return {**cozum, dosya: yeni_kod}


def mutantlar_uret(gorev: str, cozum: dict, deneme: int = 3) -> dict:
    """Geçerli (uygulanabilir, derlenen) mutantlar; hiç çıkmazsa (kesilmiş/bozuk yanıt) yeniden dener."""
    metin = "\n\n".join(f"### {y}\n{k}" for y, k in cozum.items())[:30000]
    maliyet, ham = 0.0, 0
    for _ in range(deneme):
        m = spark.sohbet([{"role": "user", "content": MUTANT_ISTEMI.format(gorev=gorev, cozum=metin)}],
                         max_tokens=24000, reasoning_effort="medium", temperature=0.5)
        maliyet += m["_maliyet"]
        try:
            liste = _json_ayikla(m.get("content"))["mutantlar"]
        except (ValueError, KeyError, TypeError, json.JSONDecodeError):
            liste = []
        ham = len(liste)
        gecerli = [mu for mu in liste if isinstance(mu, dict) and _mutant_uygula(cozum, mu) is not None]
        if gecerli:
            return {"mutantlar": gecerli, "ham": ham, "maliyet": maliyet}
    return {"mutantlar": [], "ham": ham, "maliyet": maliyet}


def mutasyon_calistir(testler: dict, cozum: dict, mutantlar: list, iptal: list) -> list:
    """Her mutant için testleri çalıştırır; öldürülme durumlarını (True/False) mutant sırasıyla döndürür.
    Tek çalışma alanında, her mutant kendi alt klasöründe; tek kabuk çağrısı."""
    from usta.arac import calisma_ac
    if not mutantlar:
        return []
    with calisma_ac() as c:
        for i, mu in enumerate(mutantlar):
            for yol, icerik in _mutant_uygula(cozum, mu).items():
                c._yaz(f"m{i:02d}/{guvenli_yol(yol)}", icerik)
            for yol, kaynak in testler.items():
                c._yaz(f"m{i:02d}/{yol}", kaynak)
        komut = (f"for d in m*/; do (cd \"$d\" && timeout 60 {_pytest(KABUL_KLASORU, iptal, '-x')} >/dev/null 2>&1; "
                 f"echo \"SONUC ${{d%/}} $?\"); done")
        _, cikti = c._calistir(komut, 60 * len(mutantlar) + 60)
    kodlar = {m.group(1): int(m.group(2)) for m in re.finditer(r"SONUC (m\d+) (\d+)", cikti)}
    # 0 = bütün testler geçti -> mutant sağ kaldı; 5 = hiç test seçilmedi -> sağ sayılır; diğerleri öldürüldü
    return [kodlar.get(f"m{i:02d}", 0) not in (0, 5) for i in range(len(mutantlar))]


def kabul_testleri_yaz(gorev: str, arayuz: str, suz: bool = True, mutasyon: bool = True) -> dict:
    """{'testler': {yol: kaynak}, 'iptal': [kimlik], 'cozum': {...}, 'mutasyon': {...}, 'maliyet'} döndürür."""
    with ThreadPoolExecutor(len(ODAKLAR)) as ex:
        yazarlar = list(ex.map(lambda o: _bir_yazar(gorev, arayuz, o), ODAKLAR))
    maliyet = sum(y["maliyet"] for y in yazarlar)
    iyi = [(i, y) for i, y in enumerate(yazarlar) if y["testler"]]
    if not iyi:
        raise RuntimeError("Spark geçerli kabul testi üretemedi")
    testler = {f"{KABUL_KLASORU}/test_kabul_{i + 1}.py": y["testler"] for i, y in iyi}
    cozumler = [y["cozum"] for _, y in iyi]
    kabul = {"testler": testler, "iptal": [], "cozum": cozumler[0], "maliyet": maliyet,
             "yazar": len(iyi), "mutasyon": None}
    if not suz:
        return kabul

    # Çoğunluk süzgeci: test, referansların en az yarısından fazlasında (3'te 2) geçmeli.
    with ThreadPoolExecutor(len(cozumler)) as ex:
        sonuclar = list(ex.map(lambda cz: _referansta_kalanlar(testler, cz), cozumler))
    kimlikler = test_kimlikleri(testler)
    gerek = len(cozumler) // 2 + 1
    kabul["iptal"] = sorted(t for t in kimlikler if sum(t not in kalan for kalan, _ in sonuclar) < gerek)
    # Mutasyon için en çok testi geçen referansı seç
    en_iyi = min(range(len(cozumler)), key=lambda i: len(sonuclar[i][0]))
    kabul["cozum"] = cozumler[en_iyi]
    if len(kabul["iptal"]) > len(kimlikler) // 2:
        raise RuntimeError(f"referanslar testlerin çoğunu geçemedi ({len(kabul['iptal'])}/{len(kimlikler)})")
    if mutasyon:
        kabul["mutasyon"] = _mutasyon_dongusu(gorev, arayuz, kabul)
        kabul["maliyet"] += kabul["mutasyon"].pop("maliyet")
    return kabul


def _mutasyon_dongusu(gorev: str, arayuz: str, kabul: dict) -> dict:
    cozum = kabul["cozum"]
    mu = mutantlar_uret(gorev, cozum)
    maliyet, mutantlar = mu["maliyet"], mu["mutantlar"]
    kayit = {"mutant": len(mutantlar), "ham_mutant": mu["ham"], "turlar": [], "hayatta": [], "maliyet": 0.0}
    if not mutantlar:
        kayit["maliyet"] = maliyet
        return kayit
    for tur in range(MUTASYON_TURU + 1):
        olu = mutasyon_calistir(kabul["testler"], cozum, mutantlar, kabul["iptal"])
        kayit["turlar"].append({"oldurulen": sum(olu), "toplam": len(olu)})
        sag = [m for m, o in zip(mutantlar, olu) if not o]
        if not sag or tur == MUTASYON_TURU:
            kayit["hayatta"] = [m.get("aciklama", "") for m in sag]
            break
        ozet = "\n".join(f"- {m['dosya']}: «{m['eski'][:200]}» -> «{m['yeni'][:200]}» ({m.get('aciklama', '')})" for m in sag)
        g = spark.sohbet([{"role": "user", "content": GUCLENDIR_ISTEMI.format(
            gorev=gorev, arayuz=arayuz or "(görevdeki adlar)", mutantlar=ozet, baslik=BASLIK)}],
            max_tokens=16000, reasoning_effort="medium")
        maliyet += g["_maliyet"]
        try:
            yeni = _json_ayikla(g.get("content"))["testler"]
            compile(yeni, "test.py", "exec")
        except (ValueError, KeyError, SyntaxError, TypeError, json.JSONDecodeError):
            continue
        if "def test_" not in yeni:
            continue
        yol = f"{KABUL_KLASORU}/test_kabul_m{tur + 1}.py"
        # Yeni testler de referans süzgecinden geçer: referansta kalan yeni test iptal.
        kalan, _ = _referansta_kalanlar({yol: yeni}, cozum)
        kabul["testler"][yol] = yeni
        kabul["iptal"] += sorted(t for t in test_kimlikleri({yol: yeni}) if t in kalan)
    kayit["maliyet"] = maliyet
    return kayit


def kabul_testlerini_calistir(calisma, testler, iptal: list | None = None) -> dict:
    """Testleri yazıp çalıştırır (iptal edilenler hariç). {'gecti', 'toplam', 'basarili', 'cikti'} döndürür."""
    for yol, kaynak in _dosyalar(testler).items():
        calisma._yaz(yol, kaynak)
    kod, cikti = calisma._calistir(_pytest(KABUL_KLASORU, iptal or []) + " 2>&1 | tail -n 80", 300)
    gecen = sum(int(x) for x in re.findall(r"(\d+) passed", cikti))
    kalan = sum(int(x) for x in re.findall(r"(\d+) (?:failed|error)", cikti))
    toplam = gecen + kalan
    return {"gecti": toplam > 0 and kalan == 0, "toplam": toplam, "basarili": gecen, "cikti": cikti}


HAKEM_ISTEMI = """Bir kodlama ajanının işi bağımsız kabul testleriyle denetlendi ve bazı testler kaldı. Kalan testler ajana
"düzelt" diye geri verilecek. Ama testi yazan model görev metnini yanlış ya da tek taraflı yorumlamış olabilir; o zaman
ajanı doğru kodu bozmaya zorlarız. Senin işin hakemlik: her kalan test için görev metnine bak ve karar ver.

GÖREV:
{gorev}

KALAN TESTLERİN KODU:
{test_kodu}

TEST ÇIKTISI:
{cikti}

Her kalan test için karar:
- "gerekli": görev metni bu beklentiyi AÇIKÇA ve tek anlamlı olarak istiyor; ajanın kodu yanlış.
- "belirsiz": görev metni bu ayrıntıyı belirtmiyor ya da birden çok makul okuması var.
- "hatali": testin beklentisi görev metniyle çelişiyor ya da test kendi içinde yanlış.
Emin değilsen "belirsiz" de. Gerekçe tek kısa Türkçe cümle olsun. "test" alanına aşağıdaki kimliği AYNEN yaz.

KALAN TEST KİMLİKLERİ:
{kimlikler}

Yalnızca JSON döndür: {{"kararlar": [{{"test": "kimlik", "karar": "gerekli|belirsiz|hatali", "gerekce": "..."}}]}}"""


def kalan_testler(cikti: str, testler=None) -> list:
    """pytest -rf çıktısından kalan testlerin düğüm kimlikleri.
    Dosya düzeyindeki toplama hataları ("ERROR x.py", ör. içe aktarılan kod derlenmiyor) test adı içermez; testler
    verilirse o dosyadaki bütün testler kalmış sayılır — yoksa bozuk kod 'hiç test kalmadı' gibi görünür."""
    kalan = set(re.findall(r"(?:FAILED|ERROR) (\S+::\w+)", cikti))
    if testler is not None:
        for yol in re.findall(r"^ERROR (\S+\.py)(?:\s|$)", cikti, re.M):
            kalan |= {k for k in test_kimlikleri(testler) if k.startswith(f"{yol}::")}
    return sorted(kalan)


def _test_kaynagi(testler, kimlikler: list) -> str:
    """Kalan test fonksiyonlarının kaynağı, her dosyanın başlığıyla (importlar, yardımcılar)."""
    dosyalar, parcalar, gosterilen = _dosyalar(testler), [], set()
    for kimlik in kimlikler:
        yol, ad = kimlik.split("::", 1)
        kaynak = dosyalar.get(yol, "")
        if yol not in gosterilen:
            parcalar.append(f"# === {yol} (başlık) ===\n" + kaynak.split("\ndef test_", 1)[0][:2500])
            gosterilen.add(yol)
        m = re.search(rf"^def {ad}\(.*?(?=^def |^class |\Z)", kaynak, re.S | re.M)
        if m:
            parcalar.append(f"# {kimlik}\n" + m.group(0).strip())
    return "\n\n".join(parcalar)


def hakem(gorev: str, testler, cikti: str) -> dict:
    """Kalan testleri görev metnine göre sınıflandırır. {'kararlar': [...], 'maliyet'} döndürür.
    Ayrıştırılamazsa her test 'gerekli' sayılır (doğrulamayı gevşetmemek için)."""
    kimlikler = kalan_testler(cikti, testler)
    if not kimlikler:
        return {"kararlar": [], "maliyet": 0.0}
    m = spark.sohbet([{"role": "user", "content": HAKEM_ISTEMI.format(
        gorev=gorev, test_kodu=_test_kaynagi(testler, kimlikler), cikti=cikti[-4000:],
        kimlikler="\n".join(kimlikler))}],
        max_tokens=12000, reasoning_effort="medium")
    try:
        kararlar = {k["test"]: k for k in _json_ayikla(m.get("content"))["kararlar"]
                    if k.get("karar") in ("gerekli", "belirsiz", "hatali")}
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        kararlar = {}
    sonuc = [kararlar.get(k, {"test": k, "karar": "gerekli", "gerekce": "hakem kararı okunamadı"}) for k in kimlikler]
    return {"kararlar": sonuc, "maliyet": m["_maliyet"]}


INCELEME_ISTEMI = """Bir kodlama ajanı aşağıdaki görevi yaptı ve bağımsız kabul testlerinin hepsini geçti. Ama kabul testleri
her gereksinimi denemiyor olabilir. Senin işin kanıtlı kod incelemesi.

GÖREV:
{gorev}

AJANIN KODU:
{kod}

ZATEN KOŞAN KABUL TESTLERİNİN ADLARI:
{mevcut}

Görev metnindeki gereksinimleri tek tek kodla karşılaştır. Kodun görev metnini AÇIKÇA ihlal ettiğinden şüphelendiğin
her nokta için (en çok 6) bir pytest testi yaz: test, ihlal varsa kalmalı, görevi doğru yapan bir kodda geçmeli.
Kurallar:
- Yalnızca görev metninde açıkça yazan davranışı test et; üslup, verimlilik ya da metinde olmayan ayrıntı yok.
- Test adları test_inceleme_ ile başlasın. Dosyanın başına şunu koy:
  {baslik}
  ve gereken importları ekle. Komut satırı programları için subprocess + sys.executable, girdi dosyaları tmp_path'e.
- Hiç şüphen yoksa boş döndür.

Yalnızca JSON döndür: {{"testler": "..."}}  (şüphe yoksa {{"testler": ""}})"""


def inceleme_testleri(gorev: str, kod: dict, mevcut_adlar: list) -> dict:
    """Spark, görev + ajanın kodunu okuyup şüpheli ihlaller için test yazar. {'testler', 'maliyet'}."""
    metin = "\n\n".join(f"### {yol}\n{icerik[:12000]}" for yol, icerik in kod.items()
                         if not yol.startswith(KABUL_KLASORU) and not yol.startswith("test_"))[:40000]
    m = spark.sohbet([{"role": "user", "content": INCELEME_ISTEMI.format(
        gorev=gorev, kod=metin or "(dosya yok)", mevcut=", ".join(mevcut_adlar) or "-", baslik=BASLIK)}],
        max_tokens=16000, reasoning_effort="medium")
    try:
        testler = (_json_ayikla(m.get("content"))["testler"] or "").strip()
        if testler:
            compile(testler, INCELEME_DOSYASI, "exec")
    except (ValueError, KeyError, SyntaxError, TypeError, json.JSONDecodeError):
        testler = ""
    return {"testler": testler if "def test_" in testler else "", "maliyet": m["_maliyet"]}


def _dosyada_kalanlar(calisma, dosya: str, testler: str) -> tuple[set, set]:
    """Tek test dosyasını çalıştırır; (kalan, geçen) düğüm kimliklerini döndürür."""
    calisma._yaz(dosya, testler)
    _, cikti = calisma._calistir(_pytest(dosya, [], "-rA") + " 2>&1 | tail -n 80", 120)
    return set(kalan_testler(cikti, {dosya: testler})), set(re.findall(r"PASSED (\S+::\w+)", cikti))


def inceleme_testlerini_sina(calisma, testler: str, cozum: dict) -> list:
    """Kanıt şartı: ajanın kodunda KALAN ve referans çözümde GEÇEN inceleme testlerinin kimlikleri."""
    from usta.arac import calisma_ac
    ajanda_kalan, _ = _dosyada_kalanlar(calisma, INCELEME_DOSYASI, testler)
    if not ajanda_kalan or not cozum:
        return []
    with calisma_ac() as ref:
        for yol, icerik in cozum.items():
            ref._yaz(guvenli_yol(yol), icerik)
        _, refte_gecen = _dosyada_kalanlar(ref, INCELEME_DOSYASI, testler)
    return sorted(ajanda_kalan & refte_gecen)
