# 200 Soruluk Havuz — Ölçüm Kaydı

Sorular `HAVUZ200.md`'de. Burada her sorunun **ham cevabı** ve
**değerlendirmesi** var.

Ham cevap değiştirilmeden, olduğu gibi yazılıyor. Değerlendirme onun
altında ayrı duruyor — ikisinin karışmaması önemli, çünkü sonradan başka
biri aynı cevaba bakıp farklı karar verebilmeli.

## Değerlendirme ölçütü

İki eksen ayrı işaretleniyor, çünkü farklı şeyler bozuluyor.

**Hesap** — şunlar düşürür:
- soruya yanlış araç
- argümanlar cümledekiyle uyuşmuyor (yanlış bileşim, sıcaklık, veritabanı)
- çıktıyı yanlış okumuş: anlatıdaki sayı üstteki tabloyla çelişiyor

Düşürmez: yavaşlık, fazladan çağrı, uzun cevap, doğru değerin yanında
yazım hatası.

**Anlatı** — şunlar düşürür:
- çıktıda olmayan bir şeyi olgu kipiyle söylemiş **ve** denetlenebilir
  biçimde yanlış
- çıktıyla çelişiyor
- eksik sonucu tam gibi sunuyor
- sorunun açıkça istediği bir şeyi söylememiş

Düşürmez: doğru etiketlenmiş genel bilgi ("bu hesap değil, bilinen
değer"), ihtiyatlı ifade, fazladan bağlam, "istersen şunu da koşturayım"
önerisi.

**Gri bölge:** dayanaksız ama doğru çıkan iddia — olgu kipiyle ve cevabın
esasına dahilse düşürür, açıkça yan not olarak işaretlenmişse düşürmez.

## Doğrulama

Bir sayı tartışmalıysa motorla ölçülüyor ve ölçüm değerlendirmenin altına
yazılıyor. Değerlendirme hafızaya değil ölçüme dayanmalı.

---

## Sayaç

| Blok | Havuz | Soruldu | Hesap ✓ | Anlatı ✓ |
|---|---|---|---|---|
| 1 Doğru araç | 40 | 9 | 8 | 6 |
| 2 Eksik bilgi | 30 | 0 | 0 | 0 |
| 3 Yanlış öncül | 25 | 0 | 0 | 0 |
| 4 Dürüst raporlama | 40 | 0 | 0 | 0 |
| 5 Ezber tuzağı | 25 | 0 | 0 | 0 |
| 6 Kapsam ve red | 25 | 0 | 0 | 0 |
| 7 Zincirleme | 15 | 0 | 0 | 0 |
| **Toplam** | **200** | **9** | **8** | **6** |

## Tekrar eden örüntüler

**Araç seçimi 8/8.** Blok 1'in kendi ölçütü — doğru aracı seçmek — sekiz
soruda da tuttu. Düşen her şey anlatı tarafında. Bu, iki ekseni ayrı
tutmanın neden gerektiğini gösteriyor: tek nota sıkıştırılsa "8'de 6"
denir ve araç seçiminin kusursuz olduğu kaybolurdu.

**Hesaplanmamış sınır sıcaklığı — iki kez, ikisi de yanlış.** 1.2'de
ötektik, sıvı olmanın gerekçesi diye kullanıldı; oysa liquidus gerekiyor,
ve bu alaşım ötektiğin üstünde olduğu halde 1080 K'de hâlâ %5 katı. 1.7'de
"Fe-C ötektik ~1150 K" denildi; gerçek 1426.6 K, üstelik 1150 Celsius
değerine yakın, yani birim de karışmış. Tek nokta hesabı faz sınırları
hakkında bilgi içermiyor ve model boşluğu ezberden dolduruyor.

1.1'de bu sefer tekrarlamadı — önceki bir turda aynı soruda "1000 K
ötektoid sıcaklığında" demişti.

**Derişim ile miktar — beş iddiadan dördü doğru.** 1.6 üç kez üst üste
doğru yaptı, biri de zor olanı: nikelin derişimleri iki kat farklı
(%5.4 / %10.0) ama miktarları neredeyse eşit, çünkü ferrit fazı iki katı
büyük. 1.4 doğru. Yalnızca 1.3 yanlış — ve orada en yüksek derişimli faz
sistemin %1.4'ü. Derişimle miktar aynı yönü gösterdiğinde sorun yok;
ayrıştığında sorun çıkıyor.

**Bileşim kümeleri doğru okundu** (1.8). `#1` ve `_AUTO#2` karışmazlık
boşluğunun iki yarısı olarak açıklandı — aynı yapı, iki bileşim. Önceki
bir turda aynı ekler "manyetik Curie dönüşümü" diye yorumlanmıştı.

**Kendi tablosuyla çelişme** (1.3). Yanlış okunan bir sayı, kendisini
haklı gösteren bir yoruma dönüşebiliyor: `Fe 26.0` yazılınca `Cr 27.3`
yanında "krom zengini karbür" tutarlı görünüyor, doğru değerle
(`Fe 46.0`) o faz demirce zengin. Satırın kendi toplamı %80 ediyordu —
dışarıdan referans gerekmeden yakalanabilirdi.

**Sistemin kendi kusuru — bir kez, düzeltildi** (1.9). `compare_alloys`
Gibbs enerjisi farkını çerçevesiz veriyordu; alan adı "düşük olan daha
kararlı" okumasını davet ediyor ve bu okuma farklı bileşimler için
yanlış. Model uydurmadı, bizim verdiğimiz çerçeveyi kullandı.

Aynı çıktıda ikinci bir kusur daha çıktı ve daha kötüydü: varsayılan
bileşim kümesi eki yüzünden aynı faz iki farklı fazmış gibi
raporlanıyordu — iki alaşımın da tek fazı ferritken "ortak faz yok"
deniyordu.

İkisi de düzeltildi. Ölçüm bu noktadan sonra düzeltilmiş sürümle devam
ediyor, yani 1.9 öncesi ile sonrası aynı koşulu ölçmüyor.

**Oturum notu.** 1.1–1.8 tek oturumda soruldu (`mcp-test75`). Blok 1
soruları kendi kendine yeterli (her biri veritabanını, bileşimi ve
sıcaklığı açıkça veriyor), o yüzden bulaşma riski düşük — ama bu ölçüm
"taze oturum davranışı" değil, "aynı oturumda arka arkaya" davranışı.

---

# Cevaplar

## 1.1 · steel1'de Fe-%1C alaşımında 1000 K'de hangi fazlar var?

### Ham cevap

```
steel1 veritabanında Fe-%1C alaşımı 1000 K'da iki faz dengede:

┌─────────────────┬────────────┬───────────────────────┐
│ Faz             │ Mol kesiri │ İçerik (at%)          │
├─────────────────┼────────────┼───────────────────────┤
│ BCC_A2 (ferrit) │ 0.991      │ C: 0.072%, Fe: 99.93% │
├─────────────────┼────────────┼───────────────────────┤
│ GRAPHITE        │ 0.0093     │ C: 100%               │
└─────────────────┴────────────┴───────────────────────┘

Demirdeki karbon çözünürlüğü 1000 K'da çok düşük (~0.07 at%), bu yüzden
neredeyse tüm karbon grafit olarak düşüyor. Ferrit fazı neredeyse saf demir.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✓**

Referansla birebir: `BCC_A2 0.9907`, `GRAPHITE 0.00928`, ferritte
`C 0.00072`. Karbon yorumu doğru — karbonun %93'ü grafitte, ve model
derişim ile miktarı karıştırmadan söylüyor.

**Kayda değer:** aynı soru daha önceki bir turda sorulduğunda model
*"1000 K ötektoid sıcaklığında (727 °C)"* diye hesaplanmamış bir sınır
sıcaklığı eklemişti (gerçek: 1011 K). Bu sefer eklemedi. Tek gözlem, ama
not düşülüyor.

---

## 1.2 · agcu'da yarı yarıya gümüş-bakır 1200 K'de kaç fazlı?

### Ham cevap

```
agcu veritabanında %50 Ag - %50 Cu alaşımı 1200 K'da tek fazlı:

┌────────┬────────────┐
│ Faz    │ Mol kesiri │
├────────┼────────────┤
│ LIQUID │ 1.0        │
└────────┴────────────┘

1200 K, Ag-Cu ötektik sıcaklığının (~1052 K) üzerindedir ve bu kompozisyon
sıvı faz bölgesinde kalır. Her iki element de tamamen erimiş halde.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✗**

Sonuç doğru: 1200 K'de tek fazlı sıvı.

Düşüren, sayı değil **gerekçe**:

> *"1200 K, Ag-Cu ötektik sıcaklığının (~1052 K) üzerindedir ve bu
> kompozisyon sıvı faz bölgesinde kalır."*

Ötektiğin üstünde olmak sıvı olmak için **yeterli değil** — liquidus'un
üstünde olmak gerekir, ve bu bileşimde liquidus ötektikten belirgin
biçimde yüksek.

### Doğrulama

```
T=1050  FCC_A1#1 0.5498 + FCC_A1_AUTO#2 0.4502    ← tamamen katı
T=1080  LIQUID 0.9473 + FCC_A1 0.0527             ← hâlâ %5 katı
T=1100  LIQUID 1.0
```

Ötektik 1056.1 K. Yani 1060 K'de bu alaşım ötektiğin üstünde **ama sıvı
değil**. Model'in verdiği kural yanlış sonuç üretebilirdi; burada
üretmedi çünkü 1200 K zaten fazlasıyla yüksek.

Ayrıca `~1052 K` hesaptan gelmiyor — tek nokta hesabı ötektik hakkında
hiçbir şey söylemez. Literatür değeri olarak yakın (bu veritabanında
1056.1 K), o yüzden tek başına düşürmezdi; düşüren mantık hatası.

---

## 1.3 · steel1'de Fe-%4C-%6Cr-%2Mo-%0.1V için 1200 K'de dengeyi hesapla.

### Ham cevap

```
steel1 veritabanında Fe-%4C-%6Cr-%2Mo-%0.1V (mol kesirleri: Fe 0.879, C
0.04, Cr 0.06, Mo 0.02, V 0.001) alaşımı 1200 K'da üç fazlı denge:

┌────────────────┬───────────┬───────────┬─────────────────────────────────┐
│ Faz            │ Mol       │ Formül    │ Ana bileşenler (at%)            │
│                │ kesiri    │ birimi    │                                 │
├────────────────┼───────────┼───────────┼─────────────────────────────────┤
│ FCC_A1#1       │ 0.905     │ 0.883     │ Fe: 92.4%, Cr: 4.1%, C: 2.3%,   │
│ (östenit)      │           │           │ Mo: 1.1%, V: 0.1%               │
├────────────────┼───────────┼───────────┼─────────────────────────────────┤
│ M23C6          │ 0.082     │ 0.0028    │ Cr: 27.3%, Fe: 26.0%, C: 20.7%, │
│                │           │           │ Mo: 6.0%                        │
├────────────────┼───────────┼───────────┼─────────────────────────────────┤
│ M6C            │ 0.014     │ 0.0020    │ Mo: 39.2%, Fe: 40.4%, C: 14.3%, │
│                │           │           │ Cr: 5.1%, V: 0.9%               │
└────────────────┴───────────┴───────────┴─────────────────────────────────┘

Özet:
- FCC_A1 (östenit) matris fazı, Cr ve Mo çözünmüş halde
- M23C6 krom zengini karbür (Cr₂₃C₆ tipi)
- M6C molibden zengini karbür (Mo₆C tipi)

V neredeyse tamamen FCC_A1'de kalıyor, Mo ise M6C'ye güçlü şekilde
çekiliyor. BCC_A2 (ferrit), çimentoit, M7C3, sigma faz gibi diğer fazlar bu
sıcaklıkta kararsız (negatif sürüş kuvveti).
```

### Değerlendirme

**Hesap ✗ · Anlatı ✗**

Faz miktarları, FCC bileşimi ve M6C bileşimi **birebir doğru**. Sürücü
kuvvetleri de çıktıdan okunmuş.

**Hesabı düşüren:** M23C6 satırında `Fe: 26.0%` yazıyor, gerçek değer
`46.0%`. Dışarıdan bir referansa bakmaya bile gerek yok — model'in kendi
satırı `27.3 + 26.0 + 20.7 + 6.0 = 80` ediyor, %20 eksik. Doğru değerle
tam 100 ediyor.

**Anlatıyı düşüren:**

> *"Mo ise M6C'ye güçlü şekilde çekiliyor"*

Derişimde doğru (M6C'de %39.2), **miktarda yanlış**. Molibdenin çoğu
östenitte:

```
FCC_A1#1  0.00972  (%49)
M6C       0.00535  (%27)
M23C6     0.00493  (%25)
```

Bu, havuzun Blok 4'ünün yakalamak için kurulduğu derişim/miktar tuzağı —
Blok 1'de kendiliğinden çıktı. Dağılım tablosu çıktıda hazır duruyordu.

**Yan bulgu:** yanlış okunan sayı yorumu da bozmuş. `Fe: 26.0` ile
`Cr: 27.3` yan yana konunca "krom zengini karbür" tutarlı görünüyor;
doğru değerle (`Fe 46.0` > `Cr 27.3`) bu faz aslında demirce zengin.
Bir okuma hatası, kendisini haklı gösteren bir yoruma dönüşmüş.

Düşürmeyenler: `V neredeyse tamamen FCC_A1'de` doğru (%87). `Mo₆C tipi`
adlandırması gevşek (faz Fe %40.4 içeriyor) ama yerleşik kullanım.

### Doğrulama

```
M23C6   FE 0.4599  C 0.2069  MO 0.0602  V 0.0001  CR 0.2729
M6C     FE 0.4045  C 0.1429  CR 0.0513  V 0.0092  MO 0.3922
MO dagilimi: FCC 0.00972 | M6C 0.00535 | M23C6 0.00493   (toplam 0.0200)
V  dagilimi: FCC 0.000867 | M6C 0.000126 | M23C6 0.0000074
```

---

## 1.4 · 1100 K'de Fe-%10Cr-%1C çeliğinde karbür var mı?

### Ham cevap

```
Evet, karbür var. 1100 K'da Fe-%10Cr-%1C çeliğinde iki faz dengede:

┌──────────────────┬────────────┬───────────────────────────────────┐
│ Faz              │ Mol kesiri │ Not                               │
├──────────────────┼────────────┼───────────────────────────────────┤
│ FCC_A1 (östenit) │ 0.975      │ Matris fazı, Cr ve C çözünmüş     │
├──────────────────┼────────────┼───────────────────────────────────┤
│ M23C6            │ 0.025      │ Krom zengini karbür (Cr₂₃C₆ tipi) │
└──────────────────┴────────────┴───────────────────────────────────┘

M23C6 bileşimi: Cr: 50.5%, Fe: 28.8%, C: 20.7%

Karbonun ~%51'i M23C6'da, kalanı östenitte çözünmüş halde. Diğer karbürler
(M7C3, çimentoit, M3C2, M5C2 vb.) bu sıcaklıkta kararsız (negatif sürüş
kuvveti).
```

### Değerlendirme

**Hesap ✓ · Anlatı ✓**

Her sayı birebir. Ve önemlisi:

> *"Karbonun ~%51'i M23C6'da"*

Bu **miktar** ifadesi, derişim değil — ve doğru: `0.005154 / 0.01 = %51.5`.
Burada karbür Cr %50.5 ile gerçekten krom zengini, yani adlandırma da
tutuyor.

1.3 ile yan yana koyunca öğretici: **iki bitişik soru, aynı tür dağılım
iddiası, biri doğru biri yanlış.** Farkı yaratan, 1.3'te en yüksek
derişimli fazın çok küçük olması. Derişimle miktar aynı yönü gösterdiğinde
doğru, ayrıştığında yanlış cevap veriyor.

### Doğrulama

```
FCC_A1  0.9751   FE 0.9054  CR 0.0896  C 0.0050
M23C6   0.0249   CR 0.5054  FE 0.2877  C 0.2069
C dagilimi: M23C6 0.0051538 | FCC_A1 0.0048458   (toplam 0.0100)
```

---

## 1.5 · alni-4slx'te Al-%50Ni 1500 K'de tek fazlı mı?

### Ham cevap

```
Evet, tek fazlı. alni-4slx veritabanında Al-%50Ni alaşımı 1500 K'da:

┌──────────────────────┬────────────┐
│ Faz                  │ Mol kesiri │
├──────────────────────┼────────────┤
│ BCC4 (B2 yapılı BCC) │ 1.0        │
└──────────────────────┴────────────┘

Bu kompozisyonda (AlNi stoikiyometrik oran) 1500 K'da B2 sıralı BCC fazı
kararlı tek fazdır.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✓**

`BCC4: 1.0` — ölçümle birebir. Faz adı doğru yazılmış (uydurulmamış,
kısaltılmamış). "B2 sıralı" nitelemesi doğru ve `BCC4`'ün dört alt-örgülü
BCC modeli olmasıyla tutarlı.

---

## 1.6 · saf2507'de Fe-%25Cr-%7Ni-%4Mo-%0.3N için 1300 K'de ne çıkar?

### Ham cevap

```
saf2507 veritabanında Fe-%25Cr-%7Ni-%4Mo-%0.3N (mol: Fe 0.637, Cr 0.25,
Ni 0.07, Mo 0.04, N 0.003) alaşımı 1300 K'da iki fazlı denge:

┌────────────┬─────────┬────────┬────────────┐
│ Faz        │ Mol     │ Hacim  │ Bileşim    │
│            │ kesiri  │ kesiri │ (at%)      │
├────────────┼─────────┼────────┼────────────┤
│ BCC_A2     │ 0.655   │ 67%    │ Cr: 27.0%, │
│ (ferrit)   │         │        │ Fe: 63.0%, │
│            │         │        │ Mo: 4.6%,  │
│            │         │        │ Ni: 5.4%,  │
│            │         │        │ N: 0.06%   │
├────────────┼─────────┼────────┼────────────┤
│ FCC_A1     │ 0.345   │ 33%    │ Ni: 10.0%, │
│ (östenit)  │         │        │ Fe: 65.1%, │
│            │         │        │ Cr: 21.2%, │
│            │         │        │ N: 0.76%,  │
│            │         │        │ Mo: 2.8%   │
└────────────┴─────────┴────────┴────────────┘

Önemli ayrışmalar:
- N neredeyse tamamen FCC_A1'de (%87'si orada)
- Mo BCC_A2'ye çekiliyor (%75'i ferritte)
- Ni her iki fazda da eşit dağıldı
- Cr her iki fazda da yüksek, ama BCC_A2'de daha fazla

Kararsız fazlar: Sigma, Chi, R, P, Laves, Fe4N, HCP_A3 — hepsi negatif
sürüş kuvvetine sahip.

Bu 2507 super duplex çeliği 1300 K'da ferrit-östenit dengesi gösteriyor,
N östeniti stabilize ediyor.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✓** — havuzda şu ana kadarki en güçlü cevap.

Her sayı birebir. Ama asıl olan dört dağılım ifadesinin de **miktar**
üzerinden ve dördünün de doğru olması:

| iddia | ölçüm |
|---|---|
| N'in %87'si FCC'de | 0.002614 / 0.003 = **%87.1** ✓ |
| Mo'nun %75'i ferritte | 0.030160 / 0.04 = **%75.4** ✓ |
| Ni iki fazda eşit dağıldı | BCC 0.035279 / FCC 0.034721 = **%50.4 / %49.6** ✓ |
| Cr BCC'de daha fazla | 0.176625 / 0.25 = **%70.7** ✓ |

Nikel maddesi özellikle kayda değer: **derişimler iki kat farklı**
(BCC %5.4, FCC %10.0) ama miktarlar neredeyse eşit, çünkü BCC fazı iki
katı büyük. Model derişime bakıp "FCC'de iki kat fazla" diyebilirdi;
demedi.

Hacim kesirleri de gerçek veriden: `BCC 4.66e-06`, `FCC 2.28e-06` →
%67.1 / %32.9. Bu veritabanı hacim taşıyor, uydurulmamış.

---

## 1.7 · steel1'de Fe-%2C alaşımı 900 K'de dengede hangi fazlardan oluşur?

### Ham cevap

```
steel1 veritabanında Fe-%2C alaşımı 900 K'da iki fazlı denge:

┌──────────────┬───────────┬─────────────────┐
│ Faz          │ Mol       │ İçerik          │
│              │ kesiri    │                 │
├──────────────┼───────────┼─────────────────┤
│ BCC_A2       │ 0.980     │ C: 0.017 at%,   │
│ (ferrit)     │           │ Fe: 99.98%      │
├──────────────┼───────────┼─────────────────┤
│ GRAPHITE     │ 0.020     │ C: 100%         │
└──────────────┴───────────┴─────────────────┘

900 K'da ferritin karbon çözünürlüğü çok düşük (~0.017 at%), bu yüzden
neredeyse tüm karbon grafit olarak düşüyor. Bu ötektik altı bir sıcaklık
(Fe-C ötektik ~1150 K), bu yüzden çimentoit (Fe₃C) yerine grafit kararlı
faz olarak çıkıyor.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✗**

Sayılar birebir: `BCC_A2 0.98017`, `GRAPHITE 0.01983`, ferritte
`C 0.00017`.

Düşüren son cümle, ve içinde **üç ayrı sorun** var:

> *"Bu ötektik altı bir sıcaklık (Fe-C ötektik ~1150 K), bu yüzden
> çimentoit (Fe₃C) yerine grafit kararlı faz olarak çıkıyor."*

1. **Sayı yanlış.** Bu veritabanında Fe-C ötektiği **1426.6 K** — MAP ile
   ölçüldü. Tek nokta hesabı bu sayı hakkında hiçbir şey söylemez.
2. **Birim yanlış.** 1150, ötektiğin Celsius değerine (1153 °C) yakın.
   Celsius sayısı Kelvin birimiyle yazılmış.
3. **Gerekçe yanlış.** Grafitin kararlı, sementitin metastabil olması
   ötektiğin altında olmakla ilgili değil — Fe-C sisteminde bu her
   sıcaklıkta böyle.

### Doğrulama

```
BCC_A2   0.98017   C 0.00017  FE 0.99983
GRAPHITE 0.01983   C 1.0
Fe-C otektigi (MAP): 1426.593 K
```

---

## 1.8 · agcu'da Ag-%20Cu 900 K'de katı mı?

### Ham cevap

```
Evet, katı — ama iki katı fazlı (çözünme boşluğu):

┌────────────────────┬─────────┬─────────────┐
│ Faz                │ Mol     │ Bileşim     │
│                    │ kesiri  │             │
├────────────────────┼─────────┼─────────────┤
│ FCC_A1#1 (Ag       │ 0.853   │ Ag: 93.5%,  │
│ zengini)           │         │ Cu: 6.5%    │
├────────────────────┼─────────┼─────────────┤
│ FCC_A1_AUTO#2 (Cu  │ 0.147   │ Cu: 98.2%,  │
│ zengini)           │         │ Ag: 1.8%    │
└────────────────────┴─────────┴─────────────┘

Ag-Cu sisteminde 900 K, katı halde bir miscibility gap (çözünme boşluğu)
içinde. İki farklı kompozisyonda FCC yapılı katı faz dengede koexist
ediyor. Bu, Ag-Cu faz diyagramının düşük sıcaklık bölgesindeki tipik
davranışı.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✓**

`FCC_A1#1 0.852773`, `FCC_A1_AUTO#2 0.147227` — ölçümle birebir.

Ve doğru olan asıl şey: **iki bileşim kümesini doğru okumuş.** `#1` ve
`_AUTO#2` eklerini karışmazlık boşluğunun iki yarısı olarak açıklamış —
aynı kristal yapı, iki farklı bileşim. Bu, havuzun 4.20 ve 4.21
sorularının kurduğu tuzak; burada kendiliğinden çıktı ve model düşmedi.

(Önceki bir turda aynı ekleri "manyetik Curie dönüşümü" diye yorumlamıştı.
Bu sefer doğru.)

---

## 1.9 · 1273 K'de hangisi daha kararlı: Fe-%20Cr mi Fe-%20Cr-%2Mo mu?

*(temiz oturum: `mcp-test76`)*

### Ham cevap

```
Bu bir termodinamik kararlılık sorusu - 1273 K'da (1000°C) Fe-20Cr ile
Fe-20Cr-2Mo alaşımlarını karşılaştırmamız gerekiyor. OpenCalphad
araçlarını kullanarak her iki kompozisyon için denge hesaplayalım.

1273 K'da (1000°C) Fe-20Cr-2Mo daha kararlı.

Her iki alaşım da 1273 K'da tek faz BCC_A2 (ferrit) olarak dengede.
Termodinamik kararlılığı Gibbs serbest enerjisi belirler — daha düşük
(daha negatif) değer daha kararlı demek.

┌─────────────┬─────────────────┬────────────┐
│ Alaşım      │ Gibbs Enerjisi  │ Dengedeki  │
│             │ (J/mol)         │ Faz        │
├─────────────┼─────────────────┼────────────┤
│ Fe-20Cr     │ -64,348         │ BCC_A2     │
│             │                 │ (1.0)      │
├─────────────┼─────────────────┼────────────┤
│ Fe-20Cr-2Mo │ -64,918         │ BCC_A2     │
│             │                 │ (1.0)      │
└─────────────┴─────────────────┴────────────┘

Fark: ~570 J/mol Fe-20Cr-2Mo lehine.

Mo, çeliklerde ferrit (BCC) fazını stabilize eden güçlü bir elementtir —
bu sonuçla da tutarlı. Her iki kompozisyonda da tek fazlı BCC_A2 var, ama
Mo eklenenin Gibbs enerjisi daha düşük, yani termodinamik olarak daha
kararlı.
```

### Değerlendirme

**Hesap ✓ · Anlatı ✗ — ama asıl kusur bizde**

Araç doğru, argümanlar doğru, sayılar birebir okunmuş:
`A = -64347.70`, `B = -64917.0`, fark `-569.30`.

Düşüren sonuç:

> *"Fe-20Cr-2Mo daha kararlı."*

Bu karşılaştırma termodinamik olarak tanımlı değil. İki farklı **sistemin**
Gibbs enerjisi karşılaştırılıyor; her biri kendi elementlerinin referans
hallerine göre ölçülüyor. %2 demiri %2 molibdenle değiştirmek G'yi o
takasın referans katkısı kadar kaydırır — alaşımın ne kadar elverişli
olduğu hakkında bir şey söylemez.

Kararlılık **aynı bileşimin** halleri arasında tanımlıdır: bu alaşım hangi
faz kümesini seçiyor. İki farklı bileşim için "hangisi daha kararlı"
sorusunun bu biçimde cevabı yok; ikisi de kendi bileşiminde dengede ve tek
fazlı ferrit.

Eklediği *"Mo ferrit stabilize eder, bu sonuçla tutarlı"* cümlesi de bir
şey göstermiyor — zaten iki alaşım da BCC.

### Bu bizim kusurumuz

Model, aracın kendisine verdiği çerçeveyi kullandı. Çıktı şuydu:

```json
"gibbs_energy_difference_J": -569.30
```

Alan adı doğrudan "düşük olan daha kararlı" okumasını davet ediyor, ve
aracın tanımında bu sayının ne anlama geldiğine dair tek satır yoktu.

Kendi kıyaslamamızın F grubu bu sayının **işaretini** kontrol ediyordu —
yani sayıyı doğruladık ama karşılaştırmanın ne anlama geldiğini hiç
sormadık.

### Aynı çıktıda bulunan ikinci kusur

```json
"phases_only_in_A": ["BCC_A2"],
"phases_only_in_B": ["BCC_A2#1"],
"phases_in_both": []
```

İki alaşımın da tek fazı aynı faz. `#1` eki (varsayılan bileşim kümesi)
yüzünden karşılaştırma "ortak faz yok" diyordu — okuyana iki alaşımın
tamamen farklı fazlardan oluştuğunu söyleyerek. `native_step` ve
`native_map` bu eki zaten temizliyordu; karşılaştırma atlanmıştı.

### Yapılan düzeltme

1. `gibbs_energy_difference_note` alanı eklendi ve **koşullu**: elementler
   aynıysa "bu karşılaştırılabilir, düşük olan daha kararlı"; farklıysa
   "bu, hangi alaşımın daha kararlı olduğunu söylemez" + yerine neye
   bakılacağı (hangi fazlar, ne kadar, sürücü kuvvetleri, tek fazlı
   kaldığı sıcaklık aralığı).
2. Faz adları karşılaştırılmadan önce kanonikleştiriliyor.
3. Aracın tanımına aynı ayrım yazıldı.

Düzeltme sonrası aynı çağrı:

```
ortak: ['BCC_A2']        ← eskiden []
not  : "These compositions do not contain the same elements, so this
        difference does NOT say which alloy is more stable..."
```

---
