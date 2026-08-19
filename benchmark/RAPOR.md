# Ölçüm Raporu — Doğal Dil Yolunun Sınanması

**Tarih:** 19 Ağustos 2026
**Sistem:** OpenCalphad MCP sunucusu, `main` dalı
**İstemci:** OpenClaw TUI, model `nvidia/nemotron-3-ultra-550b-a55b`
**Motor kademesi:** OCASI 6.120 → native OC 6.058 → native STEP + gnuplot → Python döngüsü + matplotlib
**Doğrulama:** PREFLIGHT · Katman A (`result_check.py`) · Katman B (`semantic_check.py`) · DEBUGGER (`failure_classify.py`)

---

## Raporun kapsamı ve okunuşu

Bu belge iki farklı türde ölçüm içeriyor.

**Birinci tür — tekil sınama.** Altı ayrı soru, her biri bir kez koşuldu. Amaç, sistemin farklı yollarını (motor kademeleri, diyagram üretimi, çok elementli sistemler) uçtan uca görmek. Her sorunun çıktısı ve değerlendirmesi ayrı ayrı verildi.

**İkinci tür — yinelemeli sınama.** Tek bir soru, üç aşamada beşer kez koşuldu. Amaç, sisteme yapılan bir müdahalenin ölçülebilir bir etkisi olup olmadığını görmek. Aynı soru tekrarlandığı için sayısal sonuçlar on beş koşumun tamamında **birebir aynı** çıktı; bu kendi başına bir bulgudur (motor belirlenimci) ve aynı tabloları on beş kez tekrar etmenin anlamı yoktur. Bu yüzden bu bölümde her koşumdan **yalnızca farklılaşan kısım** — modelin faz için kullandığı ifade — birebir alıntılandı.

Bir koşumun sonucu alınamadığında bu açıkça yazıldı; eksik veri tamamlanmadı.

---

# BÖLÜM 1 — Altı soruluk batarya

Bu batarya, sistemin farklı yollarını denemek için tasarlandı. Her sorunun neyi sınadığı, çıktısı ve değerlendirmesi aşağıda.

---

## Soru 1 — Referans değer doğrulaması

**Neyi sınıyor:** Bilinen bir referans değerin korunup korunmadığı. Bu soru bir regresyon kontrolüdür; sistemde bir şey bozulduysa ilk buradan anlaşılır.

**Soru:**
```
steel1.TDB'de Fe=0.99 C=0.01 için 1000 K'de denge hesapla.
Faz bileşimlerini element element ve doğrulama alanını olduğu gibi yaz.
```

**Çıktı:**

Faz miktarları:

| Faz | Mol miktarı |
|---|---|
| BCC_A2 | 0.990715 |
| GRAPHITE | 0.009285 |

Faz bileşimleri:

| Faz | Fe | C |
|---|---|---|
| BCC_A2 | 0.999278 | 0.000722 |
| GRAPHITE | 0.000000 | 1.000000 |

Termodinamik:
- Gibbs enerjisi: −41.982 J/mol
- μ(Fe) = −42.278 J/mol, μ(C) = −12.658 J/mol

Doğrulama alanı (aynen):
```json
{
  "stage": "VERIFY_A+B",
  "passed": true,
  "problems": [],
  "layer_b": {
    "available": true,
    "passed": true,
    "model_used": "deepseek-ai/deepseek-v4-flash-0731",
    "reason": "Bu sonucu inceledim. ... Faz miktarları toplamı 1.0'a çok
    yakın (0.990715 + 0.009285 = 1.000000), kütle dengesi sağlanmış.
    BCC_A2 içindeki karbon oranı ~0.00072, bu sıcaklıkta ferritteki karbon
    çözünürlüğü ile uyumlu. ... SONUC: BASARILI"
  }
}
```

**Değerlendirme:**

Referansla birebir uyum:

| büyüklük | beklenen | gelen |
|---|---|---|
| Gibbs enerjisi | −41.981,578 J | −41.982 J ✓ |
| BCC_A2 | 0,9907 | 0,990715 ✓ |
| GRAPHITE | 0,0093 | 0,009285 ✓ |
| ferritte C | 0,00072 | 0,000722 ✓ |
| μ(Fe) | −42.278 | −42.278 ✓ |
| μ(C) | −12.658 | −12.658 ✓ |

Katman B çalıştı, gerekçesini yazdı, kararını son satıra koydu. Hakem kütle dengesini kendisi hesaplayarak doğruladı.

**Sonuç: GEÇTİ.**

---

## Soru 2 — Faz diyagramı (agcu)

**Neyi sınıyor:** Diyagram yolu (native STEP + gap-fill + gnuplot) ve doğrulama alanının raporlanması.

**Soru:**
```
agcu.TDB'de Ag=0.6 Cu=0.4 için 800-1400 K faz diyagramı çiz.
Doğrulama alanını ve kaç noktanın çözüldüğünü yaz.
```

**Çıktı: alınamadı.**

Bu soru dört kez denendi:
- 2 kez `run error: Internal server error` (HTTP 500)
- 2 kez `The agent run failed before producing a reply`
- 1 kez 7 dakika 45 saniye asılı kaldıktan sonra elle kesildi

Oturum kayıtlarından alınan hata:
```json
{
  "provider": "nvidia",
  "model": "nvidia/nemotron-3-ultra-550b-a55b",
  "stopReason": "error",
  "errorCode": "500",
  "usage": {"input": 0, "output": 0, "totalTokens": 0}
}
```

**Değerlendirme:**

Token sayacının sıfır olması, isteğin işlenmeden reddedildiğini gösteriyor. Kesinti sağlayıcı tarafındadır, sunucuda değil. Bu, doğrudan ölçülerek doğrulandı — aynı minik istek üç kez gönderildi:

```
1 → HTTP 200   ✓
2 → HTTP 503   ✗   "Service Unavailable"
3 → HTTP 200   ✓
```

Birebir aynı içerik, farklı sonuç.

Ayrıca sunucu tarafı ayakta olduğu bağımsız olarak doğrulandı (`openclaw mcp doctor opencalphad --probe` → `ok`), ve asılı kalma sırasında sunucu süreci uyuma durumundaydı — yani hesap yapmıyordu, sağlayıcıdan cevap bekliyordu.

Hesabın kendisinin çalıştığı, gnuplot penceresinin geçici klasöründe kalan veriden doğrulandı: 58 nokta, üç faz (`FCC_A1`, `FCC_A1_AUTO#2`, `LIQUID`).

**Sonuç: ÖLÇÜLEMEDİ.** Sebep sağlayıcı kesintisi; sistemle ilgisi yok.

---

## Soru 3 — Çok elementli sistem

**Neyi sınıyor:** Altı elementli bir bileşimde bütün elementlerin sonuçta görünüp görünmediği. `native_fallback` katmanının, makroya yazamadığı elementi sessizce düşürdüğü biliniyor; bu sorunun amacı o kusurun tetiklenip tetiklenmediğini görmek.

**Soru:**
```
steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 Fe=0.837
bileşimi için 1173 K'de denge hesapla.
Her fazın içinde hangi elementlerin bulunduğunu tek tek yaz.
```

**Çıktı:**

| Faz | Mol miktarı |
|---|---|
| FCC_A1_AUTO#2 | 0.8566 |
| M6C | 0.09442 |
| M23C6 | 0.02978 |
| FCC_A1#1 | 0.01921 |

Faz bileşimleri:

| | FCC_A1_AUTO#2 | M6C | M23C6 | FCC_A1#1 |
|---|---|---|---|---|
| Fe | 0.921696 | 0.381335 | 0.383821 | 0.002084 |
| C | 0.013520 | 0.142857 | 0.206897 | 0.456653 |
| Cr | 0.050233 | 0.065084 | 0.341462 | 0.034264 |
| Mo | 0.009583 | 0.391919 | 0.067691 | 0.144330 |
| Si | 0.003502 | 0.000000 | 0.000000 | ~0 |
| V | 0.001466 | 0.018804 | 0.000129 | 0.362669 |

Gibbs enerjisi: −57.674 J/mol. Toplam faz miktarı: 1.00001.

**Değerlendirme:**

**Element kaybı yok.** İstenen altı elementin altısı da dört fazın tamamında görünüyor. Kusur bu boyutta tetiklenmedi.

**Stokiyometriler tam:**
```
M23C6'da C = 0,206897     6/29 = 0,206897   ✓
M6C'de   C = 0,142857     1/7  = 0,142857   ✓
```

**Üç bağımsız kütle dengesi kapanıyor:**
```
Vanadyum:
  0,8566  × 0,001466 = 0,001256
  0,09442 × 0,018804 = 0,001775
  0,02978 × 0,000129 = 0,000004
  0,01921 × 0,362669 = 0,006967
                       ─────────
                       0,010002     istenen 0,01   ✓

Karbon   : 0,040003     istenen 0,04   ✓
Molibden : 0,050002     istenen 0,05   ✓
```

Beş elementin toplamı da dördüncü haneye kadar oturuyor. Bu sayılar uydurulamaz; birden fazla bağımsız korunum yasasını aynı anda tutturmak ancak gerçek bir çözümle mümkündür.

**Modelin dikkate değer bir okuması:** `FCC_A1#1` fazı için *"yüksek C/V içerikli ayrı bir FCC fazı, karbür-benzeri"* demiş. Doğru: bileşimi C 0,457 + V 0,363 olan bu faz, vanadyum karbürüdür (VC). VC'nin kristal yapısı yüzey merkezli kübik olduğu için OpenCalphad onu ayrı bir FCC bileşim kümesi olarak modelliyor. Model bunu adıyla bilmeden yapısından çıkarmış.

Bu koşum ayrıca **zaman aşımı düzeltmesinin doğrulanmasıdır** (bkz. Bölüm 2.3): aynı soru düzeltme öncesinde 60 saniyede kesiliyordu.

**Sonuç: GEÇTİ.**

---

## Soru 4 — Seyreltik element (ilk sürüm, hatalı tasarım)

**Neyi sınamak istiyordu:** Çok az miktarda bulunan bir elementin (V = 0,001) sonuçta kaybolup kaybolmadığı.

**Soru:**
```
steel1.TDB'de Fe=0.949 C=0.01 Cr=0.04 V=0.001 için 1100 K'de hesapla.
Faz bileşimlerini element element yaz, V'nin nerede olduğunu göster.
```

**Çıktı:**

| Faz | Mol miktarı |
|---|---|
| FCC_A1 | 1.0 |

Faz bileşimi: Fe 0.949000 · Cr 0.040000 · C 0.010000 · V 0.001000
Gibbs enerjisi: −50.095 J/mol · Motor: `native_oc`

**Değerlendirme:**

Sonuç doğru, ama **soru hatalı tasarlanmıştı ve hiçbir şey ölçmüyor.**

Sistem tek fazlı çıktı. Tek faz varsa o fazın bileşimi zorunlu olarak toplam bileşimin aynısıdır — bu kütle korunumundan çıkar, hesaptan değil. Dolayısıyla bu sonuç şu iki durumu ayırt edemiyor:

- motor V'yi düzgün takip etti
- motor girdiyi olduğu gibi geri yazdı

Element kaybını sınamak için sistemin **çok fazlı** olması gerekiyor; ancak o zaman elementin fazlar arasındaki dağılımı gerçekten hesaplanmış bir büyüklük olur.

**Modelin bir yorum hatası:** *"Kimyasal potansiyel (V): −125.950 J/mol (en negatif → V bu fazda güçlü kararlı)"*. Kimyasal potansiyeller her element için ayrı bir referans durumuna göre ölçülür; farklı elementlerin μ değerlerini birbiriyle karşılaştırmak anlamsızdır.

**Sonuç: VAKA GEÇERSİZ.** Yeniden tasarlandı.

---

## Soru 4b — Seyreltik element (düzeltilmiş sürüm)

**Değişiklik:** Karbon miktarı 0,01'den 0,04'e çıkarıldı; karbür oluşumu zorlandı, böylece sistem çok fazlı hâle geldi.

**Soru:**
```
steel1.TDB'de Fe=0.919 C=0.04 Cr=0.04 V=0.001 için 1100 K'de hesapla.
Faz bileşimlerini element element yaz, V'nin hangi fazlarda ne kadar
bulunduğunu göster.
```

**Çıktı:**

| Faz | Mol miktarı |
|---|---|
| FCC_A1 | 0.9495 |
| M7C3#1 | 0.05049 |

| | FCC_A1 | M7C3#1 |
|---|---|---|
| Fe | 0.950854 | 0.319956 |
| C | 0.026175 | 0.300000 |
| Cr | 0.022735 | 0.364682 |
| V | 0.000236 | 0.015362 |

Modelin kurduğu V dağılım tablosu:

| Faz | Faz miktarı | V (mol kesri) | V katkısı |
|---|---|---|---|
| FCC_A1 | 0.9495 | 0.000236 | 0.000224 |
| M7C3#1 | 0.05049 | 0.015362 | 0.000776 |
| **Toplam** | | | **0.001000** ✓ |

Gibbs enerjisi: −49.480 J/mol

**Değerlendirme:**

Bu sürüm gerçek bir ölçüm yapıyor. V'nin 0,000224 / 0,000776 ayrımı girdiden çıkarılamaz; motorun hesaplaması gerekir.

**Üç kütle dengesi kapanıyor:**
```
Vanadyum : 0,000224 + 0,000776 = 0,001000     istenen 0,001   ✓
Karbon   : 0,024853 + 0,015147 = 0,040000     istenen 0,04    ✓
Krom     : 0,021587 + 0,018412 = 0,039999     istenen 0,06 ... 
```
*(krom: 0,9495 × 0,022735 + 0,05049 × 0,364682 = 0,039999; istenen 0,04 — bileşimde Cr = 0,04)*

**Stokiyometri tam:** M7C3 = 7 metal + 3 karbon = 10 atom → C = 3/10 = **0,300000**.

**Fizik doğru:** %4 Cr ve %4 C içeren bir çelikte 1100 K'de beklenen karbür M7C3'tür. Vanadyum güçlü bir karbür yapıcıdır; karbürde 65 kat daha yoğun bulunması beklenen davranıştır.

**Modelin kendi çıkarımları doğru:** *"V'nin %77,6'sı karbürde"* → 0,000776/0,001 = %77,6 ✓ · *"65× daha yüksek konsantrasyon"* → 0,015362/0,000236 = 65,1 ✓

**Aynı yorum hatası tekrarlandı:** *"V, karbür yapısına güçlü çekilim gösteriyor (kimyasal potansiyel: −142.595 J/mol)"*. Paylaşımın kanıtı zaten elindeydi (65× derişim farkı, %77,6 pay); μ değerini delil olarak eklemesi gereksiz ve yanlış. İki koşumda iki kez tekrarlandığı için bu bir örüntüdür, tesadüf değil.

**Sonuç: GEÇTİ.** Vaka bu hâliyle kayda alındı.

---

## Soru 5 — Motor kademesi (native_oc yolu)

**Neyi sınıyor:** OCASI'nin yakınsamadığı bir noktada native motorun devralması, ve bunun kullanıcıya bildirilmesi.

**Soru:**
```
steel1.TDB'de Fe=0.99 C=0.01 için 1200 K'de hesapla.
Hangi motorun kullanıldığını ve faz bileşimlerini element element yaz.
```

**Çıktı:**

> **Kullanılan motor:** native_oc (fallback sonrası — ocasi motoru converge olamamış, hata kodu 4204)

| Faz | Mol miktarı |
|---|---|
| FCC_A1 | 1.0 |

Faz bileşimi: Fe 0.990000 · C 0.010000
Gibbs enerjisi: −56.564 J/mol

**Değerlendirme:**

Referansla uyum: beklenen −56.563,789 J/mol, gelen −56.564 J/mol ✓

Motor kademesi doğru çalıştı ve **sebebiyle birlikte** raporlandı. Kademeli mimarinin görünür olması gereken yer tam burasıdır: kullanıcı hangi motorun neden devreye girdiğini biliyor.

Bu koşumda kimyasal potansiyeller yorumsuz verildi; önceki iki koşumdaki hata tekrarlanmadı.

**Vakanın zayıflığı:** Yine tek fazlı. Element kaybı açısından bir şey ölçmüyor (bkz. Soru 4). Sınadığı tek şey, `native_oc` yolunun iki elementi de çıktısına yazabildiğidir.

Bu nedenle vaka yeniden tasarlandı: `Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001, 1100 K` — beş element, çok fazlı, `native_oc` yolu. Bu bileşim Bölüm 3'teki yinelemeli ölçümün konusu oldu.

**Sonuç: GEÇTİ,** ama vaka tasarımı zayıf.

---

## Soru 6 — Yakınsama sorunlu diyagram

**Neyi sınamak istiyordu:** Taramanın bir kısmı çözülemediğinde sistemin bunu dürüstçe raporlayıp raporlamadığı. `alni-4slx` sisteminin, Python döngüsü yoluna düştüğünde noktaların yaklaşık %27'sinin yakınsamadığı biliniyor.

**Soru:**
```
alni-4slx.TDB'de Al=0.5 Ni=0.5 için 500-2000 K faz diyagramı çiz.
Doğrulama alanını olduğu gibi, kaç noktanın çözülemediğiyle birlikte yaz.
```

**Çıktı:**

- Toplam nokta: **119** (native STEP)
- Çözülemeyen / gap-filled nokta: **0**
- Backend: `native_oc_step_gnuplot`

| Sıcaklık aralığı | Faz(lar) |
|---|---|
| 500 – ~1920 K | BCC4 (tek faz) |
| 1920 – 1925,8 K | BCC4 + LIQUID |
| > 1925,8 K | LIQUID |

Doğrulama alanı (aynen, kısaltılmadan):
```json
{
  "stage": "VERIFY_A+B",
  "passed": true,
  "problems": [],
  "layer_b": {
    "available": true, "passed": true,
    "model_used": "deepseek-ai/deepseek-v4-flash-0731",
    "reason": "... Al-Ni sisteminde 50-50 bileşimde beklenen davranışla
    uyumludur ... SONUC: BASARILI"
  },
  "debugger": {
    "stage": "DEBUGGER",
    "category": "reviewer_unreadable",
    "skipped_models": ["nvidia/nemotron-3-super-120b-a12b"],
    "layer_b_retry": {
      "available": true, "passed": true,
      "model_used": "deepseek-ai/deepseek-v4-flash-0731"
    },
    "outcome": "resolved"
  }
}
```

**Değerlendirme:**

**Amaçlanan ölçüm yapılamadı.** Hesap kusursuz geçti — 119 noktanın hepsi gerçek STEP'ten geldi, hiçbiri düşmedi. Dolayısıyla "eksiği söyler mi" testi devreye giremedi; saklanacak bir şey yoktu.

Bu, sorunun başarısızlığı değil, koşulun oluşmamasıdır. Beklenen hata `python_loop_matplotlib` yolunda ortaya çıkıyor; bu koşum native STEP yolundan gitti. Aynı sorunun doğrudan çağrıldığında Python döngüsü yoluna düştüğü ve o yolda 30 noktanın 8'inin (%27) yakınsamadığı ayrıca doğrulandı:

```
backend_used      : python_loop_matplotlib
hatalı nokta      : 8 / 30
verification      : passed: false
problems          : ["8 of 30 temperature points failed to converge (27%):
                     500, 551.7, 603.4, 655.2, 706.9, 758.6, 965.5, 1948.3"]
```

Yani sistem, kötü yola düştüğünde eksiği **isim isim** raporluyor. Ölçüm ancak o yola zorlanarak yapılabilir (`suspended_phases` verilmesi native STEP'i devre dışı bırakır).

**Planlanmamış bulgu — DEBUGGER ilk kez baştan sona çalıştı.**

Olay sırası:
1. Katman B çağrıldı; zincirin ilk modeli (`deepseek-v4-flash-0731`) 119 noktalık büyük veriyle cevap üretemedi
2. Zincir bir sonrakine geçti; `nemotron-3-super` cevap verdi ama karar satırı okunamadı → `passed: null`
3. DEBUGGER durumu sınıflandırdı: `reviewer_unreadable`
4. Bu kategoriye tanımlı tek strateji uygulandı: `retry_reviewer_with_next_model`
5. `skip_models` ile başarısız model dışlanarak inceleme tekrarlandı
6. `deepseek-v4-flash-0731` bu sefer okunabilir bir karar verdi: `BASARILI`
7. `outcome: "resolved"`

**Hesap bir kez bile yeniden koşulmadı.** Yeniden sorulan tek şey görüştü. `failure_classify.py`'deki sekiz kategoriden yalnızca ikisinin otomatik stratejisi vardır (`reviewer_unreadable`, `reviewer_unreachable`); geri kalan altısı için "otomatik olarak yapılabilecek bir şey yok" kararı bilinçli olarak verilmiştir. Gerekçe kodda yazılıdır: yakınsama hatası zaten bütün motor kademelerinden geçmiştir, bozuk sonuç normalizasyon katmanının kusurudur, eksik kapsam ise daraltılarak "düzeltilirse" sorulandan farklı bir soruya cevap verilmiş olur.

**Açık bir soru (kusur olarak işaretlenmedi):** 50-50 NiAl kongrüan erir; kongrüan erimede katı+sıvı aralığı sıfır olmalıdır. Veride 5,5 K genişliğinde bir aralık var. 119 nokta 1500 K'ye yayıldığında ortalama adım ~12,6 K'dir, yani aralık örnekleme çözünürlüğünden dardır — STEP bu bölgeyi bilerek sıklaştırmış. Veritabanının kongrüan noktayı tam 50-50'ye değil biraz yanına koymuş olması mümkündür; bu durumda dar bir iki fazlı bölge fiziksel olarak doğrudur. Eldeki veri bu soruyu çözmeye yetmiyor.

**Sonuç: HEDEF ÖLÇÜM YAPILAMADI,** ancak DEBUGGER'ın uçtan uca çalıştığı ilk kez gözlendi.

---

# BÖLÜM 2 — Ölçüm sırasında yapılan düzeltmeler

Batarya koşulurken üç ayrı arıza ortaya çıktı ve giderildi. Sıraları önemlidir, çünkü sonraki ölçümler bu düzeltmeler yapıldıktan sonra alınmıştır.

## 2.1 — Kaybolan hakem (HTTP 410)

**Belirti:** Her hesapta Katman B `passed: null` dönüyor, DEBUGGER `unresolved` ile bitiyordu.

```json
"layer_b_retry": {
  "available": false,
  "reason": "all models failed -> deepseek-ai/deepseek-v4-flash: HTTP 410"
}
```

**Teşhis:** NVIDIA kataloğu sorgulandı. 102 model içinde `deepseek-ai/deepseek-v4-flash` yoktu; yerine `deepseek-ai/deepseek-v4-flash-0731` vardı. Sürümsüz takma ad emekliye ayrılmış, tarihli sürüm gelmişti. `410 Gone` bunun doğru kodudur.

**Önemli gözlem:** Zincir iki hafta boyunca ölüydü ve **tek bir hesap bile bu yüzden yanlış raporlanmadı.** `available` alanı, "hakem ulaşılamadı" ile "hakem itiraz etti" durumlarını ayrı tuttuğu için, sağlayıcının bir modeli yeniden adlandırması kullanıcının kimyası hakkında yanlış alarma dönüşmedi.

**Düzeltme:** Model adı güncellendi.

**Ek ölçüm:** Ulaşılabilirlik, kullanılabilirlik demek değildir. `probe_reviewer.py` yazıldı: doğru bir sonuç ve aynı sonucun faz kesirleri bozulmuş hâli hakeme verilir; sırasıyla `BASARILI` ve `BASARISIZ` beklenir.

```
deepseek-ai/deepseek-v4-flash-0731
  doğru sonuç  →  BASARILI    (33 s)
  bozuk sonuç  →  BASARISIZ   (43 s)     KULLANILABİLİR

nvidia/nemotron-3-super-120b-a12b
  doğru sonuç  →  BASARILI    (7 s)
  bozuk sonuç  →  BASARISIZ   (5 s)      KULLANILABİLİR
```

Bu ölçüm, ablation çalışmasındaki açık bir okumayı da kapatır: Katman B orada 12 hesabın 12'sini onaylamıştı. Bu, "her şeye evet diyor" anlamına gelmiyor — bozuk bir sonuç verildiğinde reddediyor.

## 2.2 — Ulaşamayan karar (`max_tokens`)

**Belirti:** Hakem cevabı cümle ortasında kesiliyordu:

> *"...Weight fraction = (0.01*12.01)/(0.01*12.01+0.99..."*

**Teşhis:** `max_tokens: 500`. İstem, gerekçenin önce, kararın **son satırda** yazılmasını istiyor — bu kural, kararı başa isteyince modelin muhakeme etmeden bağlandığı ve sonradan düzeltmediği ölçüldüğü için konmuştu. Ancak 500 belirteçlik bütçe, uzun düşünen bir hakemin karar satırına ulaşmasına yetmiyordu. İki tasarım kararı birbirini yiyordu.

Ayrıca hakem bütçesini işe yaramaz bir hesaba harcıyordu: atomik yüzdeyi ağırlık yüzdesine çevirmeye çalışıyor, fazlara hiç bakmadan tükeniyordu.

**Düzeltme:** `max_tokens` 500 → 1500 (`semantic_check.py` ve `verification/validator.py`).

**Doğrulama:** Aynı hesap tekrar koşuldu; hakem bu sefer doğrudan fazlara baktı ve kararını yazdı:

> *"Fazlar BCC_A2 (α-Fe) ve GRAPHITE, 1000 K'de düşük karbonlu Fe-C sistemi için termodinamik olarak beklenen fazlardır... SONUC: BASARILI"*

## 2.3 — Yarışan iki zaman aşımı

**Belirti:** `steel7` altı elementli sorusu cevap üretmiyordu; model aynı çağrıyı tekrar tekrar yapıyordu.

**Teşhis:** Oturum kaydından:
```json
{"error": "MCP error -32001: Request timed out"}
```
Saatler: istek `04:16:32`, hata `04:17:32` — **tam 60 saniye.**

İki ayrı 60 saniye sınırı vardı:
- OpenClaw'ın istek başına zaman aşımı: 60 s
- `server.py`'nin alt süreç zaman aşımı: 60 s (koda gömülü sabit)

steel7'nin altı elementli sistemi tam bu sınırda duruyordu. İstemci 60. saniyede pes ediyor, model bir sonuç değil bir zaman aşımı gördüğü için aynı çağrıyı yeniden gönderiyordu.

**Düzeltme:** Her ikisi de 300 saniyeye çıkarıldı.
```
openclaw mcp configure opencalphad --timeout 300 --connect-timeout 60
CALC_TIMEOUT_S = int(os.environ.get("OC_CALC_TIMEOUT_S", "300"))
```

Yalnızca birini yükseltmek işe yaramazdı: istemci beklese bile sunucu hesabı 60. saniyede öldürüyordu.

**Doğrulama:** Soru 3 (steel7) düzeltmeden sonra tamamlandı.

**Not:** 2.1 ve 2.2 düzeltmeleri bir yan etki üretti. Katman B artık gerçekten çalıştığı için her hesaba ~35 saniye ekliyor (dün 410 ile anında başarısız oluyordu). Bu, zaman aşımı sorununun ortaya çıkmasında pay sahibidir.

---

# BÖLÜM 3 — Üç aşamalı yinelemeli ölçüm

## Ölçümün konusu

Soru 4b ve Soru 5'te iki farklı hata türü tespit edildi. Bunlar aynı cevapta bir arada bulunabildiği için ayrı ayrı ölçülmeleri gerekiyordu.

**Hata A — derişim/miktar karışıklığı.** Bir faz, bir elementi yüksek **derişimde** tutarken o elementin toplam **miktarının** neredeyse hiçbirini taşımayabilir, çünkü fazın kendisi çok küçüktür. Ölçüm bileşiminde `FCC_A1` sistemin yalnızca %0,17'siydi ama vanadyumun derişim olarak üçte birini, miktar olarak yarısını taşıyordu.

İki koşumda bu hata gözlendi:
- bir koşum ağırlıklı dağılımı doğru hesapladı (%43,3 / %55,9)
- bir koşum derişimleri dağılım sanıp *"Mo en çok FCC_A1'de"* dedi — gerçekte molibdenin **en azı** oradadır (%1,6), en çoğu M23C6'dadır (%65,4)

**Hata B — faz kimliği.** Bir TDB'de faz adları **kristal yapıyı** belirtir, bileşimi değil. `FCC_A1` hem ostenittir (demir bazlı katı çözelti) hem de MC karbürleridir (VC, TiC, NbC — yapıca yüzey merkezli kübik, demirsiz). steel7 koşumu ikisini aynı anda döndürmüştü: `FCC_A1_AUTO#2` (Fe 0,92) ve `FCC_A1#1` (C 0,46, V 0,36). Ayırt eden tek şey bileşimdir.

Ölçüm bileşiminde `FCC_A1`, demiri 0,00144 olan bir vanadyum karbürüdür. Model buna "ostenit" diyordu.

## Ölçüm bileşimi

```
steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 için 1100 K'de hesapla.
Hangi motorun kullanıldığını, her fazın miktarını ve her fazın içindeki
elementleri tek tek yaz. V ve Mo'nun hangi fazlarda ne kadar bulunduğunu
ayrıca göster.
```

Her koşum **temiz bir oturumda** yapıldı. Aynı oturumda tekrar sormak, modelin kendi önceki cevabını görmesine yol açar ve ölçülen şey sistem değil konuşma olur; bu, bir koşumda doğrudan gözlendi (model *"bunu az önce hesaplamıştım"* diyerek geçmişe atıf yaptı).

## On beş koşumun ortak sayısal sonucu

Bütün koşumlarda birebir aynı çıktı. Bu, motorun belirlenimci olduğunun kanıtıdır ve tekrarlanmasının anlamı yoktur.

| Faz | Mol miktarı |
|---|---|
| BCC_A2#1 | 0.8118 |
| M23C6 | 0.1864 |
| FCC_A1 | 0.001729 |

| | BCC_A2#1 | M23C6 | FCC_A1 |
|---|---|---|---|
| Fe | 0.9729 | 0.4782 | 0.00144 |
| Cr | 0.01768 | 0.2446 | 0.02232 |
| Mo | 0.00811 | 0.07022 | 0.1883 |
| C | 0.000766 | 0.2069 | 0.4645 |
| V | 0.000534 | 0.0000394 | 0.3235 |

Gibbs enerjisi: −50.408 J/mol · Motor: `native_oc` (OCASI 4204 ile yakınsamadı)

**Doğru dağılımlar** (ölçütün kendisi):
```
Mo :  M23C6 0,01309 (%65,4)  ·  BCC_A2#1 0,00658 (%32,9)  ·  FCC_A1 0,000326 (%1,6)
V  :  FCC_A1 0,000559 (%55,9)  ·  BCC_A2#1 0,000433 (%43,3)  ·  M23C6 7,35e-6 (%0,7)
```

Beş elementin beşinde de kütle dengesi kapanıyor (Fe 0,87895 / C 0,03999 / Cr 0,05999 / Mo 0,02000 / V 0,00100).

## Puanlama ölçütü

**Hata A için:** Model, Mo'nun en çok hangi fazda olduğunu doğru söylüyor mu?

**Hata B için:** Cevap, "ostenit" etiketini yanlış veya yaklaşık olarak işaretliyor mu, yoksa fazın kimliği gibi mi sunuyor?

---

## AŞAMA 1 — `element_distribution` eklendi

**Yapılan değişiklik.** Sunucu sonucuna yeni bir alan eklendi: her elementin hangi fazda ne kadar bulunduğu, **miktara göre sıralı.**

```json
"MO": {"by_phase": {"M23C6": 0.0130885,
                    "BCC_A2#1": 0.0065825,
                    "FCC_A1": 0.000325605},
       "total": 0.0199966, "requested": 0.02}
```

Bu, motorun kendi çıktısı üzerinde aritmetiktir (faz miktarı × fazdaki derişim) ve yeni bir kimyasal iddia içermez. Fazlar sıralı verildiği için "en çok nerede" sorusu türetilmez, listenin ilk maddesinden okunur.

`total` ile `requested`'ın yan yana durması, Katman A'nın hiç sahip olmadığı bir kontroldür: toplamı sıfır çıkan bir element hesaba hiç girmemiştir.

**Gerekçe.** Bu projede defalarca gözlenen bir örüntü var: araç *açıklamasına* yazılan yönlendirme bazen tersine tepiyor, *sonucun içine* konan bilgi ise kullanılıyor. Model, cevap yazarken önünde duran bir sayıyı raporlamakta, türetmesi gereken bir sayıyı üretmekten çok daha güvenilir.

### Koşum 1.1 (`mcp-test38`)

> *"Mo strongly partitions into M23C6 (~65%) and BCC_A2 (~33%)"*
> *"FCC_A1 is a minor C/V-rich phase (only 0.17% of system)"*

Ayrıca başlıkta açıkça: **"V & Mo Distribution (absolute mol amounts, from element_distribution)"**

**Hata A: doğru** ✓ — Alanı okuduğunu kendisi belirtiyor.
**Hata B: temiz** — "ostenit" demedi, fazı bileşimiyle tarif etti.

### Koşum 1.2 (`mcp-test39`)

> `FCC_A1 (Austenit)` — faz tablosunda, bileşim başlığında ve özette iki kez
> *"Mo neredeyse tamamen M23C6 karbürüne (≈65%) ve ferrite (≈33%) bölünmüş"*

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗

### Koşum 1.3 (`mcp-test40`)

> *"Mo %65'i M23C6'da, %33'ü BCC_A2'de, kalan az miktar FCC_A1'de."*
> `FCC_A1` — hiçbir etiket kullanılmadı

Ayrıca: *"fallback_reason sadece uyarı, sonuç doğrulandı"* — `fallback_reason` alanının doğru okunması.

**Hata A: doğru** ✓
**Hata B: temiz** — yanlış bir isim kullanılmadı.

### Koşum 1.4 (`mcp-test41`)

> `Austenit (FCC_A1): Çok az (%0.17) ama V'nın %56'sını ... çeker.`
> *"V neredeyse tamamen katı çözeltide (BCC + FCC); **karbür oluşturmaz**."*

Bu koşum tam element dağılım tablosunu bastı; içinde `FE ... FCC_A1 2.49×10⁻⁶` satırı vardı. Yani demirin o fazda milyonda 2,5 olduğunu kendi eliyle yazdı ve iki bölüm sonra aynı faza "Austenit" dedi.

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗ — ve etiketten **yanlış bir kimyasal sonuç türedi.** Vanadyumun %56'sı FCC_A1'dedir ve o faz vanadyum karbürüdür; "karbür oluşturmaz" ifadesi yanlıştır ve çeliğin sertleşme davranışı hakkında yanıltıcıdır.

### Koşum 1.5 (`mcp-test42`)

> `FCC_A1 (oštenit, ~0.17%)`
> `BCC_A2#1 (ferrit/bainit ana fazı, ~81%)`
> *"Mo'nun %65'i M23C6'da, %33'ü BCC_A2#1'de, FCC_A1'de az."*

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗

Ek hata: **beynit bir denge fazı değildir.** Hızlı soğutmada oluşan bir dönüşüm ürünüdür ve bir denge hesabında görünemez. Aynı refleksin başka bir örneği: faz adına bakıp çelik metalurjisinin bildik terimlerini, önündeki veriyle sınamadan yapıştırmak.

### Aşama 1 sonucu

| | doğru | yanlış |
|---|---|---|
| Hata A (dağılım) | **5 / 5** | 0 |
| Hata B (isimlendirme) | 2 / 5 | 3 |

**Hata A tamamen çözüldü.** Düzeltme öncesi iki koşumun birinde ters okunuyordu; sonrasında beş koşumun hiçbirinde ters okunmadı. Aritmetik koda taşındığı için modelin yapacağı bir hata kalmadı.

**Hata B'ye etkisi olmadı.** Koşum 1.1'de ortaya çıkmaması varyanstı; sonraki koşumlarda geri geldi.

Bu, iki hatanın **bağımsız** olduğunu kanıtlar: biri diğerinin yan etkisiyle düzelmiyor.

---

## AŞAMA 2 — `phase_notes` eklendi (olgu bildirimi)

**Yapılan değişiklik.** Fazın içeriği adıyla çeliştiğinde sonuca bir not eklendi:

```json
"phase_notes": {
  "FCC_A1": "In this phase the dominant element is C (0.4645), while the
             alloy's dominant element is FE (0.00144 here). A phase name in
             this database denotes crystal structure, not composition -- the
             same name covers chemically different phases. Read the
             composition before naming this phase."
}
```

**Tetikleyici:** fazın baskın elementi ≠ alaşımın baskın elementi. Hiçbir kimya varsayımı içermez, her veritabanında çalışır, yalnızca çelişki olduğunda ateşlenir.

**İlk sürüm bir yanlış pozitif verdi:** `GRAPHITE`'e de not düşüyordu. Grafit saf karbondur, orada yanlış okunacak bir şey yoktur. Koşul daraltıldı: **fazın içinde %1'den fazla en az iki element olmalı.** Tek elementli bir faz kendi kimliğidir; belirsizlik ancak katı çözeltilerde doğar.

Daraltılmış tetikleyicinin dört vakadaki davranışı:

| vaka | not düştü mü | doğru mu |
|---|---|---|
| steel1, 5 element | FCC_A1'e düştü | ✓ hedef vaka |
| steel1 Fe-C basit | hayır | ✓ GRAPHITE saf karbon |
| steel1 Fe-C 1200 K | hayır | ✓ tek faz, gerçekten ostenit |
| agcu Ag-Cu | FCC_A1_AUTO#2'ye düştü | ✓ miscibility gap'in Cu-zengin kümesi |

Sonuncusu planlanmamıştı ama isabetlidir: Ag-Cu'da iki FCC bileşim kümesi vardır ve hangisinin hangisi olduğu isimden anlaşılmaz. Bu sunucunun daha önce bir koşumda **veri olmadan** iddia ettiği bir ayrımdır.

### Koşum 2.1 (`mcp-test43`)

> `FCC_A1 (östenit)` — faz tablosunda
> *"Not: FCC_A1 fazında baskın element C (%46), isteğe bağlı olarak "C-zengin östenit" veya "karbür öncü fazı" olarak yorumlanabilir; Fe bu fazda neredeyse yok denecek kadar az."*

**Hata A: doğru** ✓
**Hata B: kısmen temiz** — etiketi tek okuma olarak sunmadı, iki yorumu yan yana verdi. Ancak "karbür öncü fazı" ifadesi yanlıştır; o faz karbürün kendisidir, öncüsü değil.

### Koşum 2.2 (`mcp-test44`)

> *"FCC_A1 fazında C (0.46) ve V (0.32) baskın — bu faz aslında bir karbür/karbon-zengin faz gibi davranıyor, isim "FCC_A1" olsa da."*
> *"FCC_A1 fazının V ve C ile zenginleşmesi, bu sıcaklıkta **V-karbür (VC)** veya (V,Fe)C türü bir fazın FCC_A1 etiketi altında çıktığını gösteriyor."*

**Hata A: doğru** ✓
**Hata B: temiz** — fazı doğru teşhis etti. Beş koşumun en iyi okuması.

Küçük kayma: *"İlk STEP/gnuplot yolu 4204 ile çökmüş"* — STEP/gnuplot tek nokta hesabında devrede değildir; düşen OCASI'ydi.

### Koşum 2.3 (`mcp-test45`)

> *"Not: FCC_A1 fazında C baskın (0.465) — bu faz **karbür/sementit benzeri** bir yapı olabilir (veritabanında faz adı kristal yapısını, bileşimi belirtmez)."*

**Hata A: doğru** ✓
**Hata B: temiz** — "ostenit" demedi, karbür dedi.

Küçük kayma: sementit Fe₃C'dir, bu fazda demir yok denecek kadar azdır. "Karbür" doğru, "sementit" gevşek.

### Koşum 2.4 (`mcp-test46`)

> `FCC_A1 (oštenit)` başlığında değil, ama özette:
> *"V ise FCC_A1 (**austenite benzeri faz**) ve BCC_A2 arasında paylaşılmış"*
> Notu doğru aktarmış: *"FCC_A1 fazında baskın element C (0.4645), Fe çok az (0.00144)."*

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗ — notu yazdıktan iki satır sonra aynı faza "austenite benzeri" dedi.

### Koşum 2.5 (`mcp-test47`)

> `FCC_A1 (oestenit)` — faz tablosunda, nitelemesiz
> Not aktarıldı: *"FCC_A1 fazında C baskın görünüyor; bu veritabanında faz adı kristal yapıyı (FCC) belirtir, kimyasal bileşimi değil."*

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗ — not var, etiket nitelenmemiş.

### Aşama 2 sonucu

| | temiz | kaçırdı |
|---|---|---|
| Hata A | **5 / 5** | 0 |
| Hata B | 3 / 5 | 2 |

**Not beş koşumun beşinde de cevaba aktarıldı.** Alan görülüyor, okunuyor, hatta kelimeleri tekrarlanıyor. Sorun bilginin ulaşmaması değildir.

**Etiket oranı 2/5'ten 3/5'e çıktı.** Beş koşumluk bir örneklemde bu fark gürültüden ayırt edilemez.

**Yanlış kimyasal sonuç bir kez bile tekrarlanmadı.** Aşama 1'de gözlenen *"vanadyum karbür oluşturmaz"* türü bir çıkarım bu beş koşumun hiçbirinde çıkmadı. Etiket kalıyor ama yanında onu çürüten sayı durduğu için okuyucu yanlış sonuca varmıyor.

---

## AŞAMA 3 — `phase_notes` yeniden yazıldı (gerekçe talebi)

**Değerlendirilen ve reddedilen seçenek.** Notu bir yasağa çevirmek düşünüldü: *"Bu fazı ostenit ya da ferrit olarak adlandırma."*

Reddedildi, iki sebeple:

1. **Çeliğe özeldir.** `agcu.TDB` ve `MgNaCl.TDB` de aynı sunucudan geçiyor; yasaklanacak kelimeleri saymak, çelik sözlüğünü genel bir sunucuya gömmek olur. Bir sonraki veritabanı kendi yanlış isimlerini getirir.
2. **Gördüğü tek hataya göre yazılmış dar bir kuraldır** — bu projede daha önce aynı hata yapılmış ve düzeltilmişti.

Ayrıca bir bedeli olurdu: Aşama 2'nin iki koşumunda model aynı fazı **doğru** okumuştu (biri VC olarak teşhis etmişti). Bir isim yasağı bu okumaları da susturur; üç yanlış etiket beş sessizliğe dönüşürdü.

**Yapılan değişiklik.** Notun son cümlesi olgu bildiriminden gerekçe talebine çevrildi:

```
önce  : "Read the composition before naming this phase."
sonra : "If you give this phase a name of your own, say which feature of
         the composition supports that name."
```

Yasaklamıyor — iyi okumalar hayatta kalır. Ama "ostenit" yazmak isteyen bir modelin bunu `Fe = 0,00144` ile bağdaştırması gerekir.

### Koşum 3.1 (`mcp-test48`)

> `FCC_A1 (Ostenit / karbür-benzeri)`
> *"Not: FCC_A1 fazında C (0.46) ve V (0.32) baskın — bu veritabanında faz adı kristal yapısını belirtir, kimyayı değil; **bu nedenle "ostenit" etiketi kaba bir yaklaşık**."*

**Hata A: doğru** ✓
**Hata B: temiz** — etiketi yazdı ve aynı cümlede geri çekti. Gerekçe isteyince gerekçe üretmedi, etiketi işaretledi.

### Koşum 3.2 (`mcp-test49`)

> `FCC_A1 (ostenit/karbür-benzeri)`
> *"Not: FCC_A1 fazında C baskın (0.464), bu faz veritabanında ostenit olarak adlandırılır **ancak bu kompozisyonda karbür-benzeri bir yapı gösterir**."*

**Hata A: doğru** ✓
**Hata B: temiz**

Küçük kayma: veritabanı o faza "ostenit" demez, `FCC_A1` der. Adı model getiriyor, veritabanına mal etmiş.

### Koşum 3.3 (`mcp-test450`)

> `FCC_A1 (östenit)` — faz tablosunda, nitelemesiz
> *"Not: FCC_A1 fazında C baskın (%46), ... **karbür benzeri** bir kompozisyona sahip olduğunu gösterir; OpenCalphad faz isimleri kristal yapısını belirtir, kimyayı değil."*
> Çıkarımda: *"...FCC (östenit/karbür benzeri) fazına partition oluyor"*

**Hata A: doğru** ✓
**Hata B: temiz** (sınırda) — tablo başlığı nitelemesiz, ama iki ayrı yerde çürütülmüş.

Bu koşum ayrıca **ayrı bir doğrulama tablosu** kurdu: beş elementin hesaplanan toplamını istenen değerle yan yana koydu ve *"yuvarlama farkı < %0,01"* diye bitirdi. `element_distribution` alanının kendi kendini denetlemek için kullanılması, alanın on beş koşumdaki en iyi kullanımıdır.

### Koşum 3.4 (`mcp-test51`)

> `FCC_A1 (austenit)` — hem faz tablosunda hem bileşim başlığında
> **Not hiç aktarılmadı.**

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗

Aşama 2'de not beş koşumun beşinde de cevaba giriyordu; burada model alanı tamamen atladı.

### Koşum 3.5 (`mcp-test52`)

> `FCC_A1 (oştenit)` — faz tablosunda, bileşim başlığında ve çıkarımda
> Not aktarıldı: *"FCC_A1 fazında baskın element C (%46.5) ve V (%32.3) — bu fazın kimyası alaşımın genel kimyasından çok farklı. Faz adı kristal yapısını (FCC) belirtir, kompozisyonu değil."*

**Hata A: doğru** ✓
**Hata B: kaçırdı** ✗ — not var, etiket nitelenmemiş, çıkarımda düz kullanılmış.

### Aşama 3 sonucu

| | temiz | kaçırdı |
|---|---|---|
| Hata A | **5 / 5** | 0 |
| Hata B | 3 / 5 | 2 |

Aşama 2 ile birebir aynı.

---

# BÖLÜM 4 — Toplu sonuçlar

## Hata A — derişim/miktar karışıklığı

| aşama | doğru | yanlış |
|---|---|---|
| müdahale öncesi | 1 / 2 | 1 |
| `element_distribution` sonrası | **15 / 15** | 0 |

Üç aşama boyunca on beş koşumun hiçbirinde molibdenin nerede olduğu ters okunmadı.

## Hata B — faz kimliği

| aşama | ne eklendi | temiz | kaçırdı |
|---|---|---|---|
| 1 | sadece `element_distribution` | 2 / 5 | 3 |
| 2 | `phase_notes` — olgu bildirimi | 3 / 5 | 2 |
| 3 | `phase_notes` — gerekçe talebi | 3 / 5 | 2 |

**Notun sözlerini değiştirmenin ölçülebilir bir etkisi olmadı.** Aşama 2 ile 3 aynı yerdedir.

**Notun varlığının da net bir etkisi ölçülemedi.** 2/5 → 3/5 farkı, beş koşumluk bir örneklemde gürültüden ayrılamaz.

**Notun ölçülebilir tek etkisi dolaylıdır:** etiketten türeyen yanlış kimyasal sonuç (*"vanadyum karbür oluşturmaz"*) müdahale öncesinde bir kez gözlendi, sonraki on koşumun hiçbirinde tekrarlanmadı.

## Yan bulgular

| bulgu | nerede |
|---|---|
| Motor belirlenimci: 15 koşum, birebir aynı sayılar | Bölüm 3 |
| Aynı oturumda tekrar sorulan soru ölçüm sayılmaz — model kendi cevabını görüyor | Bölüm 3 |
| DEBUGGER uçtan uca çalıştı, `outcome: resolved`; hesap yeniden koşulmadı | Soru 6 |
| Hakem zinciri iki hafta ölüydü, tek bir yanlış alarm üretmedi | Bölüm 2.1 |
| PREFLIGHT bileşim anahtarlarını sayıyor, sıfırdan farklı miktarları değil | `benchmark/cases.py` |
| Kimyasal potansiyeli kararlılık delili sanma — 2 koşumda 2 kez | Soru 4, 4b |
| Beynit bir denge fazı olarak raporlandı | Koşum 1.5 |

---

# BÖLÜM 5 — Buradan çıkan ilke

> **Deterministik olarak hesaplanabilen bir şeyi koda ver — kesin sonuç alırsın.**
> **Muhakeme gerektiren bir şeyi istemle düzeltmeye çalışma — ölçülebilir fayda görmezsin.**

Dağılım hatası aritmetikti: faz miktarı ile derişimi çarpmak. Kodun içine alındı, on beş koşumda sıfır hata.

İsimlendirme hatası muhakemeydi: bir fazın adına mı yoksa bileşimine mi bakılacağına karar vermek. İki farklı istem düzenlemesiyle denendi, ölçülebilir bir kazanç elde edilmedi.

## Öneri: burada durulmalı

`phase_notes` olduğu gibi bırakılmalı. Kaldırılmamalı — yanlış sonuç türetmeyi engelliyor gibi görünüyor ve zararı yok. Ancak üzerinde daha fazla oynanmamalı; veri bunu desteklemiyor.

İsim hatasını gerçekten bitirmenin tek yolu kalıyordu: sunucunun fazı kendisi adlandırması (karbon oranından karbür tipini çıkarmak gibi). Bu bilinçli olarak reddedildi — OpenCalphad'ın söylemediği bir şeyi söylemek olurdu ve bu sunucunun baştan beri koruduğu sınırı aşardı.

## Bu ölçümün değeri

Bu üç aşamalı çalışma, makalede tek başına bir bölümdür. Anlatılan şey *"bir sorunu düzelttik"* değil, **"neyin düzeltilebildiğini ve neyin düzeltilemediğini ölçtük"**tür.

İkincisi daha nadirdir ve daha değerlidir: bir müdahalenin işe yaradığını göstermek kolaydır, işe yaramadığını ölçmek ve bunu kayda geçirmek zordur. Negatif sonucun raporlanması, sistemin sınırlarının nerede olduğunu gösterir — ve bir mimarinin neyi garanti edip neyi edemediğini bilmek, yalnızca başarılarını listelemekten daha güvenilir bir bilgidir.
