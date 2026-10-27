# X gönderisi taslakları

Kullanıcı kendisi atar. Kurallarda "most viral project" ve "community vote" gibi ek ödüller geçiyor; en iyi saat
genelde videonun yayınlandığı gün, ABD doğu sabahı (TR 16:00–18:00). Her gönderiye **videonun kendisini** (bağlantı
değil, X'e yüklenmiş 30–60 sn kesit) ekle — X'te gömülü video bağlantıdan çok daha fazla izlenir.
`{…}` yer tutucuları README'deki gerçek sayılarla doldur; dolmazsa o cümleyi sil. Etiketleri etkinliğin resmî
etiketine göre güncelle (Discord/duyurularda hangisi kullanılıyorsa); aşağıda `#MetaHackathon` tahmindir.

---

## 1. Ana gönderi (İngilizce, jüri ve geniş kitle) — video kesitiyle

> Coding agents say "done". Mine has to prove it.
>
> Usta 🇹🇷 — a Turkish coding agent:
> • Muse Glimmer (open weights) writes code in an offline sandbox
> • Muse Spark writes tests without seeing the code
> • failing tests → repair loop → evidence on screen
>
> Round 1: 6/14 ❌ → Round 2: 14/14 ✅
>
> {repo_url} #MetaHackathon

(~270 karakter; 280'i aşarsa ilk satırı kısalt.) Ek: rozetlerin kırmızıdan yeşile döndüğü 20–40 sn'lik kesit.

**Zincir (yanıt olarak, isteğe bağlı):**

> 2/ Why a second model? LLM-written tests can be wrong. During development Spark called an invalid IBAN "valid".
> Now Spark also writes a reference solution and any test the reference fails is dropped before it reaches the agent.

> 3/ Measured on {n_gorev} Turkish tasks with hidden tests nobody in the loop saw:
> Glimmer alone {a_basari} · with its own tests {b_basari} · Usta {c_basari}.
> Task sets + scripts are open, including where it didn't help.

---

## 2. Türkçe gönderi (Türk geliştirici topluluğu, paylaşım için)

> Türkçe görev veriyorsunuz — yazıyla ya da sesle — ajan kodu yazıyor, ama "bitti" demesi yetmiyor:
>
> 🧠 Muse Glimmer (açık ağırlık) kodu ağı kapalı sandbox'ta yazıyor
> 🔍 Muse Spark, kodu görmeden bağımsız testler yazıyor
> 🔁 Kalan test varsa hata ajana dönüyor
>
> TC kimlik, IBAN, KDV, resmî tatilli vade… Usta 👇
> {repo_url} #MetaHackathon

Ek: sesle görev verme anı (Voice Transcribe metni kutuya yazıyor) + yeşil rozet.

---

## 3. "Türk I" kancalı kısa gönderi (merak uyandıran, teknik kitle)

> "Ilgaz".lower() in Python → "ilgaz". In Turkish it should be "ılgaz".
>
> Small bugs like this are why I built Usta: a Turkish coding agent where an independent model writes the tests
> and the agent has to pass them before it can say "done".
>
> Open weights (Muse Glimmer) + Muse Spark as verifier. {repo_url}

Ek: senaryo 6'nın (turkce.py) rozet ekranının ekran görüntüsü — **yalnızca gerçekten koşulduysa** ve gösterilen
sonuç gerçekse.

---

## Kontrol

- [ ] Gösterilen her sayı ve rozet gerçek bir koşudan; kayıtlı koşuysa "from our evaluation run" demek yeterli
- [ ] Görüntülerde API anahtarı, `.env`, Modal panosu, gerçek TC/IBAN yok
- [ ] Bağlantı herkese açık depoya gidiyor
