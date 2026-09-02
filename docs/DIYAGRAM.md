# Mevcut durum — tek diyagram

*2026-09-01 akşamı. Her kutu dosyalardan okundu, hiçbiri hafızadan yazılmadı.*

---

## Okuma anahtarı

| | anlamı |
|---|---|
| **düz ok** `-->` | çalışma anındaki akış |
| **kesik ok** `-.->` | okuma / danışma — karar taşımaz |
| 🟦 mavi | kural **ayar dosyasında**, açılışta derlenmiş |
| 🟨 sarı | **kodda**, kasıtlı — aritmetik, tip, ayrıştırma |
| ⬜ gri | danışman — oy kullanmaz |
| 🟧 turuncu | **açık** — kusur, borç ya da ölçülmemiş |

---

```mermaid
flowchart TD

%% ══════════ DERLEME ══════════
subgraph DERLE["⚙ DERLEME · sunucu acilirken BIR KEZ"]
  direction LR
  D1["PARSE<br/>uc TOML"]
  D2["CHECK<br/>her ad baglanabiliyor mu<br/>baglanamiyorsa SUNUCU ACILMAZ"]
  D3["RESOLVE<br/>kural adi ➜ yuklem"]
  DP["CompiledPolicy<br/>InputPolicy · ExecutionPlan · OutputPlan"]
  D1 --> D2 --> D3 --> DP
end

INP -.-> D1
EXE -.-> D1
OUT -.-> D1

%% ══════════ AKIS ══════════
U(["KULLANICI · dogal dil"]) --> MOD["MODEL · OpenClaw'da<br/>soruyu tipli arac cagrisina cevirir"]
MOD --> LOG1[/"call_log acilir"/]
LOG1 --> REQ["ISTEK<br/>database · composition · composition_basis<br/>conditions · axis · suspend"]

REQ --> PF{"❶ PREFLIGHT<br/>preflight.py · 156 satir · SIFIR kural"}
DP -.->|"calisma ani YALNIZCA bunu okur"| PF
PF -->|"gecmedi"| RED["RED<br/>stop_rule ile cerceve<br/>+ route varsa ALTERNATIF"]
PF -->|"gecti"| PC{"❷ PRECONDITION<br/>bir hesaba mal olur"}
PC -->|"gecmedi"| RED
PC -->|"gecti"| IB["❸ GIRIS BAZI<br/>beyan edilen baz ➜ kanonik mol kesri<br/>basis ZORUNLU · elle donusum YOK"]

IB --> EX{"❹ EXECUTE<br/>run_cascade()"}
EX -.->|"kademe · zaman asimi · tolerans"| DP
EX --> RES["HAM SONUC"]

RES --> CP["❺ FAZ ADI<br/>tek yazim · #1 silinir · #2 KORUNUR"]
CP --> OB["❻ CIKIS BAZI<br/>basis + source her sonuca"]
OB --> KA{"❼ KATMAN A<br/>8 kontrol · KARARI BU VERIR"}
KA -.-> LA
KA --> PASS["verification.passed<br/>◆ TEK KARAR NOKTASI ◆"]

PASS --> KB["❽ KATMAN B<br/>bagimsiz model · advisory_only<br/>vaka basi 90 s tavan"]
PASS --> OUTP{"❾ OZET + NOTLAR"}
OUTP -.-> DP
OUTP --> INV{"❿ CIKTI DEGISMEZLERI<br/>biz soyledigimiz gibi mi davrandik"}
INV -.-> HON
INV --> LOG2[/"call_log · tam yuk + asama sureleri"/]
RED --> LOG2
LOG2 --> ANS(["CEVAP"])

%% ══════════ INPUT ══════════
subgraph INP["🟦 input.toml · 22.650 bayt · 5/5 BAGLI · cevabi DEGISTIREBILIR"]
  direction TB
  IA["accept · operations · defaults · composition.basis"]
  IR["reject · 24 kural<br/>veritabani · bildirim · bilesim · ortam<br/>sicaklik · eksen · scheil<br/>+ composition-basis-required"]
  IRT["route · 3<br/>uc-element · saf-uc · bagimliya-yer"]
  ISR["stop_rule · 3<br/>reddin cevabi -- motor calismadan"]
  IPC["precondition · 1 · scheil tohumu sivi mi"]
end

%% ══════════ EXECUTION ══════════
subgraph EXE["🟦 execution.toml · 19.707 bayt · 14/16 BAGLI · cevabi DEGISTIREMEZ"]
  direction TB
  C1["cascade · 6 islem<br/>ocasi ➜ native · step ➜ gap_fill ➜ python_loop"]
  SIG["signals · engine_failures<br/>hangi ariza kademe ilerletir"]
  TMO["timeouts · 6<br/>5 · 12 · 15 · 30 · 180 · 240 s"]
  TOL["tolerances · 4<br/>1e-6 · 1e-5 · 1e-4 · 1e-3"]
  SCH["scheil · merdiven 5 ➜ 2 ➜ 1 K"]
  BIN["binary · 6058 ➜ 6120"]
  RB["reviewer · budget · retry · independence<br/>validator_reviewer · vision_reviewer"]
  EXC["🟨 policy · reviewer_note · status=code<br/>kural tip listesinin kendisi"]
end

%% ══════════ KATMAN A ══════════
subgraph LA["🟨 result_check.py · YUKLEMLER KODDA · beyan output.toml'da"]
  direction TB
  V1["verify_result() · bu duzgun bir sonuc mu"]
  V1a["phase_fraction_sums 1e-3 · failed_points %10"]
  V2["verify_correspondence() · SORDUGUM sorunun cevabi mi"]
  V2a["requested_elements · mass_balance 2e-4"]
  V2b["suspended_phases · requested_positions %90"]
  V2c["reported_conditions · degrees_of_freedom<br/>ikisi de MEVCUTLUK bildirir"]
  V1 --- V1a
  V2 --- V2a --- V2b --- V2c
end

%% ══════════ OUTPUT ══════════
subgraph OUT["🟦 output.toml · 26.639 bayt · 7/7 BAGLI · sayilara DOKUNAMAZ"]
  direction TB
  OV["verify · 8 kontrol · Katman A'nin beyani"]
  OD["derive · 5 turetme<br/>bolge · gecis · baskinlik · erime · yetersiz"]
  NOTE["note · 7 metin"]
  OF["floor · zorunlu alanlar<br/>verification.passed · backend_used · basis<br/>+ nokta basina source"]
  OCV["conversion · axis_position BAGLI<br/>units · rounding · phase_amounts planned"]
  ORP["report.basis · as_computed · label_per_point"]
end

%% ══════════ DEGISMEZLER ══════════
subgraph HON["🟦 [honesty] · 7 DEGISMEZ · anahtar DEGIL kontrol"]
  direction TB
  H1["floor_fields_present"]
  H2["boundaries_are_brackets · sinir tek sayi degil"]
  H3["single_point_regions_flagged"]
  H4["flagged_results_not_hidden"]
  H5["review_does_not_decide<br/>absent_review_not_disapproval"]
  H6["points_have_provenance<br/>KAYNAKTAN, sayimdan degil"]
end

%% ══════════ ACIK ══════════
subgraph ACIK["🟧 ACIKTA KALANLAR"]
  direction TB
  A1["BORC · server.py 1.933 satir<br/>iki tarama fonksiyonu PARALEL (207 + 203)"]
  A2["KUSUR E4 · askiya alinmis faz + yedek motor<br/>KUSUR G3 · gaz fazi MOLEKUL turu"]
  A3["KIRILGAN · _MALFORMED_MARKS<br/>kendi kontrol MESAJLARIMIZI esliyor"]
  A4["ACIK · dil -- iki cevap Ingilizce geldi, olculmedi"]
  A5["OLCUM · Blok 1'de 6 soru<br/>Blok 2-7: 160 soru SORULMADI"]
  A6["push · 14 commit yerel"]
end

classDef yeni fill:#dbeafe,stroke:#2563eb,stroke-width:2px,color:#000
classDef kod  fill:#fef3c7,stroke:#d97706,stroke-width:2px,color:#000
classDef acik fill:#ffedd5,stroke:#ea580c,stroke-width:2px,color:#000
classDef gri  fill:#f3f4f6,stroke:#9ca3af,color:#000
classDef uc   fill:#dcfce7,stroke:#16a34a,stroke-width:3px,color:#000
classDef karar fill:#fde68a,stroke:#b45309,stroke-width:4px,color:#000

class DERLE,D1,D2,D3,DP,IB,OB,CP,INV yeni
class INP,IA,IR,IRT,ISR,IPC yeni
class EXE,C1,SIG,TMO,TOL,SCH,BIN,RB yeni
class OUT,OV,OD,NOTE,OF,OCV,ORP yeni
class HON,H1,H2,H3,H4,H5,H6 yeni
class LA,V1,V1a,V2,V2a,V2b,V2c,KA,EXC kod
class PASS karar
class KB gri
class ACIK,A1,A2,A3,A4,A5,A6 acik
class U,ANS uc
```

---

## Sayılarla

| | bağlı | açık | toplam |
|---|---|---|---|
| `input.toml` | **5** | 0 | 5 |
| `execution.toml` | **14** | 2 | 16 |
| `output.toml` | **7** | 0 | 7 |
| **toplam** | **26** | **2** | **28** |

Açık kalan iki bölüm `status = "code"`: `policy`'nin kuralı tip listesinin kendisi, `reviewer_note` bağlanacak davranışı olmayan bir operatör notu.

| | |
|---|---|
| Python | **14 modül · 8.158 satır** |
| TOML | **3 dosya · 68.996 bayt** |
| Ayar bölümü | **28 · 26'sı bağlı** |
| Katman A kontrolü | **8** — beyan dosyada, yüklem kodda |
| Çıktı değişmezi | **7** — anahtar değil kontrol |
| MCP aracı | **8** |
| Kıyaslama | **86/86** *(kolay 30/30 · orta 35/35 · zor 21/21)* — havuz 88, ikisi belgelenmiş kusur |
| Denetim | **dört yönlü**, temiz |
| Commit | **60** — bugün 13 |

---

## Dört değişmez

```
input.toml       cevabi DEGISTIREBILIR
                 ne hesaplanacak + reddedilirse ne yapilacak

execution.toml   cevabi DEGISTIREMEZ, ulasilirligi degistirir
                 hangi motor, hangi sirayla, ne kadar bekleyerek

output.toml      sayilara DOKUNAMAZ
                 [verify] dogru mu · [derive] ne turetilir
                 [floor] ne hep bulunur · [honesty] biz nasil davraniriz

kod              aritmetik, tip kontrolu, makro uretimi, ayristirma
                 kural degil IS
```

---

## Denetim — dört yön

```
1  dosyada var, kodda okuyan var mi
2  kodda kural govdesi kalmis mi
3  yurutucunun actigi her sey cagriliyor mu
4  okudugunu IDDIA EDEN gercekten okuyor mu     <- bugun eklendi
```

Dördüncüsü bugün iki sessiz düşüş yakaladı. Biri **doğru görünüyordu**: yedeği dosyadaki değerin aynısıydı, yani ayarı hiç okumadan doğru cevap veriyordu.

---

## Yavaşlamanın sebebi — ölçüldü

```
--hizli    141.1 s     Katman B kapali
tam       2915.8 s     Katman B acik

S2_ozet_erime_araligi   115.88 s   verify_b = 90.726 ms   %78
C3_steel1_genis_tarama  111.63 s   verify_b = 89.289 ms   %80
H1_krom_taramasi        104.02 s   verify_b = 90.698 ms   %87
```

Her birinde **tam 90 saniye** — `stage_deadline_s` tavanı. Hesap saniyeler, hakem 90 saniye.

```
zamanin %100'u   cagrilarin ICINDE
cagrilar arasi   %0
her arka uc      "sabit" -- zaman icinde bozulma YOK
```

Aylardır *"sebep bilinmiyor"* diye taşınan şeyin adı: **ulaşılamayan bir hakemi beklemek.** Koşumun %37'si.
