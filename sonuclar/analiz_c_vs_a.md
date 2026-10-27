# Neden (c) Usta, (a) Glimmer-tek-başına'yı geçemedi? — 34 zor görev (g07–g40), Glimmer yürütücü

Kaynak: `sonuclar/zor/{a,c}_gNN.json`. Her kip görev başına 1 koşu.
(c)'nin kaldığı 16 görev aşağıdaki gibi sınıflandırıldı. (a)'nın kalıp (c)'nin geçtiği görev yok.

| Sınıf | Görev sayısı | Görevler | Ne oldu |
|---|---|---|---|
| **1. Kabul testleri gereksinimi kapsamadı** | 12 | g07 g09 g11 g14 g18 g24 g26 g28 g29 g30 g32 g40 | Spark'ın kabul testleri (çoğu ilk turda) tamamen geçti; gizli testler (a)'nın da kaldığı **aynı** gereksinimlerde kaldı (g11'de c daha az testte kaldı). Hata görünmeyince düzeltme döngüsü hiç devreye girmedi. |
| **2. Tek koşu oynaklığı** | 2 | g10 g38 | Kabul testleri geçti, düzeltme turu yok; (c)'nin Glimmer koşusu (a)'nın geçtiği bir ayrıntıyı kaçırdı (g10: çıktı dosyasının üst klasörünü oluşturmamak; g38: bir sınır değeri). Bu da kapsama boşluğu: o ayrıntıyı deneyen kabul testi yoktu. |
| **3. Düzeltme turu doğru kodu bozdu** | 1 | g25 | Hakem 1 testi "gerekli" saydı; iki düzeltme turunda kabul testleri 11/12 → 12/12 oldu, ama gizli testler 9/17'den (a) 3/17'ye düştü: Glimmer dosyayı yeniden yazarken posta kodu ve doğrulama kısımlarını bozdu. Bu kısımları kabul testleri denemediği için gerileme görülmedi. |
| **4. Ajan dosyayı hiç oluşturamadı** | 1 | g22 | Üç kipte de `adisyon.py` yok, Done yok (a 4 adım). Gizli testler toplanamadı. Glimmer tarafında bir kesinti (muhtemelen istek reddi ya da boş yanıtlar); yöntemle ilgisi yok. |

Spark'ın kendi hatalı testleri bu sette **neden değil**: referans süzgeci bu 34 görevde hiç test iptal etmedi; hakem 5 görevde
(g07, g10, g24, g25, g29) toplam 8 kalan testi "belirsiz" sayıp dayatmadı. Hakemin "gerekli" dediği testler (g19, g21, g26, g32)
düzeltildikten sonra gizli sonuç (a)'nınkinden kötü olmadı; tek istisna g25.

## Sonuç

(c)'nin tavanı kabul testlerinin kapsamıyla sınırlı. Testler bir gereksinimi denemezse Usta, Glimmer'ın tek başına yaptığından
fazlasını yapamıyor; üstelik ek koşu sayısı oynaklığı artırıyor. İlk turda koşan kabul testi sayısı ortalama ~12, gizli testler
16–19. Düzeltme döngüsü yalnızca 7 görevde tetiklendi; bunların 6'sında sonuç (a) ile aynı ya da daha iyi, 1'inde (g25) kötü.

## Önerilen düzeltmeler (uygulandı, bkz. git geçmişi)

1. **Gereksinim bazlı kabul testleri:** Spark önce görevdeki gereksinimleri tek tek listeler, her gereksinim için en az bir test
   yazar (12–20 test). Gizli test yazarıyla aynı model, ama ayrı çağrı ve birbirini görmeden.
2. **Gerileme koruması:** Her düzeltme turundan önce çalışma alanının anlık görüntüsü alınır. Tur sonunda kabul testlerinde
   geçen sayı düşerse ya da ajanın kendi testlerinden önceden geçenler kalırsa dosyalar geri alınır.
3. g22 tipi kesintiler için: boş yanıtlar ve istek hataları rapora "ajan bitiremedi" olarak yazılır (yöntemin başarısı sayılmaz).
