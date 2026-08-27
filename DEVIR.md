# OpenCalphad MCP · Devir Notu

**Hazırlandı:** 24 Ağustos 2026
**Devredilen oturum:** `226e6bf2-4abf-4d0c-a6be-7afd80239f1e` — "OpenCalphad'ı yapay zekâ ile entegre etmek"
**Süre:** 23 Temmuz – 24 Ağustos 2026 · 13.373 kayıt · 5 kez sıkıştırıldı · ~272k token bağlam
**Neden devredildi:** Bağlam 272k'ya çıktı; 24 Ağustos 08:01–08:16 arasında dört denemenin hepsi `API Error: 529 Overloaded` ile tükendi (her denemede ~10 retry). Aynı dakikalarda 73k'lık küçük bir oturum sorunsuz çalıştı.

---

## 1. NEREDE KALDIK — devam edilecek iş

**Kategori 3 kıyaslaması elle koşuluyor. 30 sorudan 3'ü sorulmuş, 27'si duruyor.**

Dosya: `benchmark/KATEGORI3.md` (21 Ağustos'ta yazıldı, son commit)

Kategori 1 ve 2 makineyle koşuluyor. Kategori 3 koşulamıyor, çünkü ölçtüğü şey bir sayı değil **anlatı**: sistem gerçekte ne olduğunu söylüyor mu. Aynı hesap iki şekilde raporlanabilir — biri doğru, biri yanlış, ikisi de aynı sayıları içerir. Deterministik koşucu ikisini ayırt edemez.

### Sorulanlar

| Soru | Metin | Oturum | Sonuç |
|---|---|---|---|
| S1.1 | 1000 K'de %1 karbon içeren çelikte hangi fazlar var? | `mcp-test71` | ferrit + grafit döndü |
| S1.2 | %60 gümüş %40 bakır alaşımı 1100 K'de sıvı mı katı mı? | — | LIQUID döndü |
| S1.3 | Yarı yarıya alüminyum-nikel alaşımı 1500 K'de kaç fazlı? | `mcp-test72` | BCC4 tek faz, −132.4 kJ/mol |

Üçü de sayısal olarak doğru. **Ama KATEGORI3.md'nin sonundaki sonuç tablosu hâlâ boş** — GEÇTİ/KISMİ/KALDI işaretleri girilmemiş. İlk iş bu üçünü işaretlemek olmalı.

### Kalan gruplar

| Grup | Soru | Ne ölçüyor |
|---|---|---|
| S1 Doğal dil çevirisi | 5 (2 kaldı) | günlük cümle → doğru araç çağrısı |
| S2 Dolaylı istek | 4 | hesap adı verilmemiş; hangi hesap olduğuna model karar veriyor |
| S3 Eksik bilgi | 5 | bilgi kasıtlı eksik; uydurmak yerine soruyor mu |
| S4 Yanlış öncül | 4 | sorunun içindeki hatalı varsayımı düzeltiyor mu |
| S5 Dürüst raporlama | 6 | hangi motor, hangi doğrulama, neyin eksik olduğunu söylüyor mu |
| S6 Ezber tuzağı | 3 | cevabı hesaptan mı veriyor, ezberden mi |
| S7 Kapsam dışı | 3 | Scheil / MAP / parametre uydurma — açıkça reddediyor mu |

### Koşma kuralları (KATEGORI3.md'den, atlanmamalı)

- **Her soru temiz bir oturumda sorulacak.** Aynı oturumda arka arkaya sormak modelin kendi önceki cevabını görmesine yol açar; o zaman ölçülen şey sistem değil konuşma olur. OpenClaw'da `exit` yazıp yeniden gir.
- Soru **olduğu gibi** yapıştırılacak. Eksik bırakılan şeyler kasıtlı.
- Termodinamik bilmek gerekmiyor. Ölçüt: **anlatı araç çıktısıyla uyuşuyor mu.** Model hangi aracı çağırdığını ve ne döndüğünü ekranda gösteriyor; bakılacak şey altındaki cümlelerin o çıktıyla aynı şeyi söyleyip söylemediği.
- Bir soru KALDI aldıysa **cevabın tamamı kaydedilecek.** Kategori 3'te değerli olan sayı değil, hangi cümlenin çıktıyla çeliştiği — düzeltme oradan çıkıyor.

---

## 2. Sistem — çalışır durumda, bugün doğrulandı

| | |
|---|---|
| Kod | `/root/projects/oc-mcp` (WSL Ubuntu, `root` kullanıcısı) |
| Dal / durum | `main`, çalışma ağacı temiz, son commit `14b0cbf` (21 Ağustos) |
| Motor | `/root/projects/opencalphad` — kendi derlememiz, OCASI/pyOC, 6.120 |
| Python | `/root/projects/ocvenv/bin/python` (3.11, numpy<2.0) |
| Yedekler | `oc-mcp.backup-before-native-retry`, `opencalphad.backup-before-native-retry` |

### 24 Ağustos'ta yapılan canlı sınama

```
[0.5s] initialize OK
[0.5s] TOOLS: list_databases, inspect_database, calculate_equilibrium,
              compare_alloys, calculate_property_diagram, calculate_isothermal_section
[0.6s] list_databases -> AlFe-4SLBF.TDB (AL, FE)
[56.0s] calculate_equilibrium(AlFe-4SLBF, Al 0.2/Fe 0.8, 1000 K)
        -> BCC_4SL tek faz, G = -59870.539 J, backend_used = ocasi,
           verification: VERIFY_A+B passed
```

İstemci MCP loglarında (son bağlantı 21 Ağustos) tek hata yok — sunucu bağlanıyor, altı aracı listeliyor.

### Süre dağılımı — dikkat edilecek nokta

| Aşama | Süre |
|---|---|
| OpenCalphad motoru (OCASI, gerçek hesap) | **0.1 s** |
| VERIFY B — NVIDIA reviewer modeli | **37–56 s** |

Sürenin %99'u AI denetim adımı. `NVIDIA_API_KEY` olmadan aynı hesap 0.1 saniyede dönüyor. En kötü durum daha kötü: `semantic_check.py:100` `timeout_s=60`, `retries=(0,4)`, 2 modelli zincir; üstüne `server.py:291` `_retry_review` bir tur daha ekliyor — NVIDIA yavaşladığında tek araç çağrısı 4 dakikayı aşabilir ve MCP istemcisi zaman aşımına düşer.

---

## 3. Kod makaleden ileri gitti — makale güncellenmeli

Makale (`OpenCalphad_MCP_Paper_FINAL_Aug7.pdf`) 7 Ağustos tarihli. Kod 14–21 Ağustos arasında önemli ölçüde ilerledi. Makalede yazılanla koddaki durum artık ayrışıyor:

| Makale ne diyor | Kod ne durumda |
|---|---|
| "The server declares **five** tools" (Tablo 2, §5.2) | **Altı** araç var — `calculate_isothermal_section` eklendi (commit `5f2b6ba`, "Add a composition axis: isothermal sections") |
| §11.3 gelecek iş: bileşim ekseni yok | Bileşim ekseni **yapıldı** ve kıyaslamaya girdi (`af324ef`) |
| Sonuç alanları: `backend_used`, `fallback_reason`, `verification` | Ek olarak `driving_force_RT` (her faz için oluşma eğilimi), `phase_notes`, `element_distribution` |
| — | "sonuç isteği cevaplıyor mu" kontrolü (`9ef5e8d`) |
| — | istenmemiş element bildirimi (`a8ef47a`) |
| — | adıyla içeriği çelişen fazı işaretleme (`113e103`) |
| §7.5: 20 doğal dil sorusu | `benchmark/` altında **78 vaka** (A–H + R grupları) + 30 soruluk Kategori 3 |

**Makalede güncellenecek yerler:** Tablo 2, §5.2 (araç yüzeyi), §8 (sonuçlar), §11.3 (gelecek iş — artık yapıldı), Tablo 4 (satır sayıları).

---

## 4. Ölçüm mirası

| Dosya | Tarih | İçerik |
|---|---|---|
| `benchmark/RAPOR.md` | 19 Ağustos | Ölçüm raporu. Bölüm 1: altı soruluk batarya. Bölüm 2: ölçüm sırasında yapılan düzeltmeler (kaybolan hakem HTTP 410, `max_tokens`, yarışan iki zaman aşımı). Bölüm 3: üç aşamalı yinelemeli ölçüm — 15 koşum, `element_distribution` → `phase_notes` → `phase_notes` yeniden yazımı |
| `benchmark/SORULAR.md` | 21 Ağustos | 78 vaka, 9 grup: A tek fazlı denge, B çok fazlı + element paylaşımı, C faz geçişleri, D bileşim kümeleri/karışmazlık boşluğu, E yarı kararlı (faz kapatma), F iki bileşim karşılaştırma, G çelik dışı (oksit/tuz/gaz), H bileşim ekseni, R doğru red |
| `benchmark/KATEGORI3.md` | 21 Ağustos | 30 soruluk elle koşulan anlatı sınaması — **devam eden iş** |
| `verification/results/*.json` | 1–3 Ağustos | Regresyon döngüsü raporları (6 senaryo, 5/6 geçti) |
| `ablation_results.json` | 14 Ağustos | 18 vaka × 5 konfigürasyon = 90 koşum |

---

## 5. Açık kalan sorunlar

1. **VERIFY B gecikmesi.** Her hesaba 37–56 s ekliyor. Öneri: `calculate_equilibrium`'a `verify: bool = False` parametresi; denetimi ayrı bir araç yap; `timeout_s` 60 → 20; `_retry_review`'ü kaldır. Karar verilmedi.
2. **İki farklı 529'u karıştırmamak.** (a) Sohbette görülen `API Error: 529 Overloaded` → istemci sağlayıcısının sunucu tarafı. (b) `semantic_check.py:64`'te kendi yorumumuzun yazdığı 529 → NVIDIA ücretsiz katmanının kapasite sinyali. Aynı kod, farklı kaynak.
3. **`alni-4slx` yakınsama sorunu çözülmedi.** Al(0.75)Ni(0.25), 800–1700 K taramasında 30 noktanın 7'si (%23) yakınsamıyor — hep aynı sıcaklıklarda: 893.1 / 1420.7 / 1544.8 / 1575.9 / 1606.9 / 1669.0 / 1700.0 K. Tespit ediliyor ve sayısal olarak raporlanıyor, giderilmiyor.
4. **Katman C (görsel denetim) varsayılan yolda değil.** `OC_ENABLE_VISION_CHECK=1` ile açılıyor. Okuma yeteneği ölçüldü (3/3 doğru); karar kuralı — "modelden gözlem iste, yargı değil" — tasarlandı, yazılmadı.
5. **Kapsam dışı:** MAP (iki boyutlu faz diyagramı), Scheil–Gulliver katılaşma, para-denge.
6. **`suspended_phases` kısıtı:** native STEP yolunda desteklenmiyor; parametre verilince sistem zorunlu olarak son kademeye (Python döngüsü) düşüyor ve STEP'in çözünürlük avantajını kaybediyor. Dördüncü motor kademesi bu yüzden kıyaslamada hiç sınanmadı.

---

## 6. Son oturumda düzeltilen yanlış anlama

Sürücü kuvveti özelliğinin çalışmadığı sanılmıştı — iki kez yanlış alana bakılmış. **Doğru alan `driving_force_RT` ve çalışıyor:**

```
LIQUID#1 0.0   LIQUID_AUTO#2 -2.6e-09
FCC_A1  -0.047   HCP_A3 -0.158   BCC_A2 -0.355
```

Model bu sayıları çıktıdan okumuş — üstelik yeni açılan alandan. Pozitif değer fazın oluşmak istediği anlamına geliyor (`server.py:442`).

---

## 7. Komutlar

```bash
# MCP sunucusu (istemciler bunu çağırıyor)
/root/projects/oc-mcp/run_server.sh

# Regresyon döngüsü — 6 sabit senaryo, zaman damgalı JSON rapor
cd /root/projects/oc-mcp && python3 verification/run_loop.py

# Kıyaslama — hepsi, ya da grup/vaka adıyla seçerek
python3 benchmark/run.py                 # hepsi
python3 benchmark/run.py A B             # sadece A ve B grupları
python3 benchmark/run.py --hizli         # VERIFY B kapalı (çok daha hızlı)

# OpenClaw TUI (Kategori 3 için — her soru öncesi exit/yeniden gir)
openclaw
```

**Ortam değişkenleri:** `OC_BUILD_DIR`, `OC_BINARY`, `NVIDIA_API_KEY` (Katman B için), `OC_SEMANTIC_CHECK=0` (Katman B kapat), `OC_VALIDATOR_MODEL` (tek modele sabitle), `OC_ENABLE_VISION_CHECK=1`, `LD_PRELOAD` (launch script kuruyor).

**İstemciler:** OpenClaw TUI (model `nvidia/nemotron-3-ultra-550b-a55b`). Sunucu kodunda istemciye özgü hiçbir şey yok.
