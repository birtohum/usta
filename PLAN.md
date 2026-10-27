# Usta — Türkçe, kendi işini doğrulayan ajan (Meta Global AI Developer Hackathon)

Teslim: 4 Kasım 21:00 ET = **5 Kasım 04:00 TR**. Indie track. Tema: *Build for Your World* (+ Agentic ve Open-Weight bonusları).
Kural: yalnızca hackathon sırasında (27 Eki – 4 Kas) yazılan kod sunulur. Tohum/S. kodu bu depoya KOPYALANMAZ; oradan öğrenilen
yöntemler sıfırdan yeniden yazılır. Önceden var olan tek şey test verisi olursa README'de "önceden var olan" diye ayrıca belirtilir.

## Sorun
Türkçe konuşan geliştiriciler ve küçük işletmeler için yerel, Türkçe çalışan ajan yok; olanlar da "bitti" dediğinde gerçekten
çalışıp çalışmadığını göstermiyor. Ölçtük: eğitimsiz Muse Glimmer 30B Türkçe kod sınavımızda %88, kısıt testinde %88 — yetenek var,
eksik olan **güvenilirlik**: işi bitirdiğini kanıtlayan bir döngü.

## Fikir
Kullanıcı Türkçe bir görev verir (yazı ya da **sesle**). Usta:
1. **Planlar ve yazar** — Muse Glimmer (açık ağırlık, Modal'da vLLM) yalıtılmış bir klasörde araçlarla (dosya yaz/oku/düzenle, komut) çalışır.
2. **Bağımsız doğrulatır** — Muse Spark görev metninden, ajanın kodunu görmeden **kabul testleri** yazar (yazan ≠ doğrulayan).
3. **Düzeltir** — testler kalırsa hata çıktısı Glimmer'a geri verilir; geçene ya da tur sınırına kadar.
4. **Kanıtlar** — sonuç ekranında hangi testlerin geçtiği, kaç turda bittiği, Türkçe özet.

Meta araçları: Muse Glimmer (yürütücü, açık ağırlık), Muse Spark 1.3 (bağımsız test yazarı + zor adımda danışman),
Muse Voice Transcribe (Türkçe sesli görev). İstersen: Muse Code ile geliştirme.

## Ölçülebilir iddia (demo + README)
Aynı N=40 Türkçe görevde (Muse Spark üretir, insan değil): (a) Glimmer tek başına, (b) Glimmer + kendi testleri, (c) Usta
(bağımsız Spark testleri + düzeltme döngüsü). Gizli değerlendirme testleriyle başarı oranı, tur sayısı, maliyet. Beklenen: (c) > (b) > (a);
olmazsa dürüstçe yazılır.

## Yapılacaklar (gün gün)
| Gün | İş |
|---|---|
| 27–28 Eki | Depo + Modal'da Glimmer sunucusu (vllm muse-glimmer imajı, kimlik doğrulamalı uç nokta) + Spark istemcisi (Contributor modu, bütçe sayacı 140 $'da durur) |
| 28–29 | Yalıtılmış araç çalıştırıcı (yeni yazılır: klasör dışı yol, ağ, tehlikeli komut reddi) + ajan döngüsü (Glimmer yerel tool_calls) |
| 30 | Bağımsız test yazarı (Spark) + düzeltme döngüsü; 5 görevle uçtan uca |
| 31 Eki–1 Kas | Değerlendirme seti (40 görev + gizli testler) ve a/b/c karşılaştırması |
| 2 Kas | Arayüz (basit web sayfası: görev kutusu, mikrofon, canlı adımlar, test rozetleri) + Voice Transcribe |
| 3 Kas | Demo videosu (3 dk), README, X gönderisi taslağı |
| 4 Kas | Son kontroller, teslim (TR saatiyle 5 Kas 04:00'dan önce) |

İsteğe bağlı (zaman kalırsa): Glimmer'ı Spark'ın doğruladığı Türkçe ajan yörüngeleriyle QLoRA (Modal) ve (c) üzerinde önce/sonra.

## Bütçe
Meta API 150 $ (Contributor: 0,10/0,20 $ per 1M → yeterli). Modal: hackathon kredisi (gelirse 100 $) + aylık 30 $; Glimmer H100 ~4 $/sa →
geliştirme + değerlendirme ~10–15 saat. Sunucu yalnızca kullanırken açık, kimlik doğrulamalı.

## Riskler
- vLLM Glimmer desteği resmî sürümde değil (Meta imajı; araç ayrıştırıcı "doğrulanmadı" diyor) → ilk gün araç çağrısı test edilir; olmazsa ATEM biçimini kendimiz ayrıştırırız.
- Rekabet büyük; ödül garantisi yok. Değer: dürüst ölçümlü, çalışan bir demo.
- Kullanıcıdan gerekenler: GitHub hesabı (public repo), demo videosu için ekran kaydı/ses, X hesabı (viral ödül isteğe bağlı).
