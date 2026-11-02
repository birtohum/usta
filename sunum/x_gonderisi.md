# X gönderisi taslakları

Kullanıcı kendisi atar. Kurallarda topluluk oyu ve "most viral project" gibi ek ödüller geçiyor. Videonun 30–60 sn'lik
kesitini doğrudan X'e yükle (bağlantıdan çok daha fazla izlenir). `#MetaHackathon` tahmindir; Discord'daki resmî
etiketi kullan. Sayılar README'deki zor3 tablosundan (2 Kas'ta dolduruldu); `{repo_url}` depo açılınca doldurulur.

---

## 1. Ana gönderi (İngilizce)

> Can an LLM check another LLM's code?
>
> I built Usta 🇹🇷, a Turkish coding agent where Muse Spark writes tests without seeing the code — then measured it
> on 1,026 runs with hidden tests.
>
> Alone: 60% · Usta: 58%. No gain. Here's why 🧵
>
> {repo_url} #MetaHackathon

**Zincir:**

> 2/ The loop works: voice task (Muse Voice Transcribe) → executor writes & runs code offline → Spark's independent
> tests → referee → repair rounds. Faulty LLM tests are dropped if Spark's own reference solution fails them.

> 3/ But the executor's mistakes were misreadings of the task, and a verifier from the same model family reads the task
> the same way. Our tests killed 94% of code mutants and still missed those.

> 4/ Usta's "verified" was right 60% of the time; the executor's own "done" 63%. Coverage, not repair, is the
> bottleneck. Every task, hidden test and log is open.

---

## 2. Türkçe gönderi

> Bir yapay zekâ, başka bir yapay zekânın kodunu denetleyebilir mi?
>
> Usta'yı yaptım: Türkçe görev veriyorsunuz, ajan kodu yazıyor, Muse Spark kodu görmeden test yazıyor, kalan test
> varsa ajan düzeltiyor. Sonra gizli testlerle 1.026 koşuda ölçtüm.
>
> Tek başına %60, Usta %58. Kazanç yok — nedeni ve bütün veriler depoda 👇
> {repo_url} #MetaHackathon

---

## Kontrol

- [ ] Gösterilen her sayı ve rozet gerçek bir koşudan; kayıtlı koşuysa "recorded run" yaz
- [ ] Görüntülerde API anahtarı, `.env`, gerçek TC/IBAN yok
- [ ] Bağlantı herkese açık depoya gidiyor
