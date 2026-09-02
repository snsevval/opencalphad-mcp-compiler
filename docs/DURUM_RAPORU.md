# OpenCalphad MCP — durum raporu

*2026-09-01. Projeyi bilmeyen bir okuyucu için yazıldı.*

---

# 0 · Bu proje ne yapıyor

Bir yapay zekâ asistanının **termodinamik hesap yapabilmesini** sağlıyor.

Arkada OpenCalphad var: metalurjide alaşımların hangi sıcaklıkta hangi
fazlara ayrıldığını hesaplayan, otuz yıllık, Fortran'la yazılmış bir motor.
Girdi olarak bir bileşim ve sıcaklık alır; çıktı olarak *"bu alaşımda %92
östenit, %7 ferrit, %1 karbür var"* der.

Sorun şu: bu motor doğal dil anlamaz. Kullanıcı *"paslanmaz çelikte nikeli
artırırsam ne olur"* diye sorar; motor `set condition x(NI)=0.08` bekler.

Arada duran şey bu proje. Üç işi var:

```
1  dogal dili motorun anladigi cagriya cevirmek
2  motoru calistirip cevabi almak
3  cevabin DOGRU oldugunu ve SORULAN sorunun cevabi oldugunu dogrulamak
```

Üçüncüsü projenin asıl iddiası. Bir dil modeli motoru çalıştırabilir ama
sonucu yanlış okuyabilir, ya da hiç hesaplamadığı bir sayıyı ezberinden
söyleyebilir. Bu katman onu yakalamak için var.

---

# 1 · Temel mimari — dört değişmez

Sistem bir derleyici gibi kurulmuş. Kurallar koda gömülü değil, **üç ayar
dosyasında** yaşıyor, ve her dosyanın tek cümlelik bir **değişmezi** var:

```
input.toml       cevabi DEGISTIREBILIR
                 ne hesaplanacak, hangi istek reddedilecek

execution.toml   cevabi DEGISTIREMEZ
                 ama sonuca ulasilip ulasilamayacagini degistirir
                 hangi motor, hangi sirayla, ne kadar bekleyerek

output.toml      sayilara DOKUNAMAZ
                 sonuc nasil dogrulanir ve nasil sunulur

kod              aritmetik, tip kontrolu, makro uretimi, metin ayristirma
                 bunlar kural degil IS
```

**Bu ayrımın pratik faydası:** bir dosyayı açan kişi ne tür bir riske
baktığını bilir. `output.toml`'da bir şey değiştirirken eli titremez,
`input.toml`'da titrer.

Ve ayrım işe yaradı — bugün bir bölümün yanlış dosyada olduğunu **bu kural
sayesinde** kanıtladık (bkz. bölüm 4).

---

# 2 · Boru hattı — on aşama

```
KULLANICI
   │  dogal dil sorusu
   ▼
MODEL (OpenClaw'da, bizim disimizda)
   │  soruyu tipli arac cagrisina cevirir
   ▼
┌──────────────────────────────────────────────────┐
│  BIZIM SUNUCU                                    │
│                                                  │
│  ❶ PREFLIGHT      istek gecerli mi (24 kural)    │
│  ❷ PRECONDITION   bir hesaba mal olan kontrol    │
│  ❸ GIRIS BAZI     birimleri kanonige cevir       │
│  ❹ EXECUTE        motor kademelerini dene        │
│  ❺ FAZ ADI        tek yazima getir               │
│  ❻ CIKIS BAZI     sayinin neyin kesri oldugunu   │
│                   soyle                          │
│  ❼ KATMAN A       8 kontrol -- KARAR BURADA      │
│  ❽ KATMAN B       ikinci model -- DANISMAN       │
│  ❾ OZET           satirlar arasi soruları cevapla│
│  ❿ DEGISMEZLER    biz soyledigimiz gibi mi       │
│                   davrandik                      │
└──────────────────────────────────────────────────┘
   │
   ▼
MODEL  sonucu dogal dile cevirir  →  KULLANICI
```

**Üstünde bir de derleme aşaması var:** sunucu açılırken üç TOML dosyası
bir kez okunur, doğrulanır ve `CompiledPolicy` nesnesine çevrilir. Çalışma
anı ham dosyayı hiç okumaz.

Neden önemli — ölçülmüş bir örnekle: bir kural adında tek harf hata
(`min_nonzero_count` yerine `min_nonzero_kount`) yazdığımızda eski sistem
**hiçbir şey söylemeden** o kuralı devre dışı bırakıyordu. Geçersiz bir
istek 1 şikâyet yerine 0 şikâyet alıyordu. Şimdi sunucu **açılmıyor**.

---

# 3 · İki doğrulama katmanı

**Katman A** deterministik, bizim kodumuz. Sekiz kontrol yapıyor ve ikisi
farklı soru soruyor:

```
"Bu duzgun bir termodinamik sonuc mu?"
   faz kesirleri 1'e topluyor mu · NaN var mi
   donen noktalarin kaci hata verdi

"Bu, SORDUGUM sorunun cevabi mi?"
   istedigim elementler var mi, ISTEMEDIGIM var mi
   her elementin miktari tuttu mu
   askiya aldigim faz gercekten yok mu
   istenen tarama noktalarinin kaci HIC gelmedi
   motor BENIM kosullarimi mi kullandi
   serbestlik derecesi 0 mi
```

İkinci grubun varlık sebebi ölçülmüş bir olay: PREFLIGHT kapalıyken
`Fe-%0.1Ni` istendi, **saf demir** geri geldi — yapısal olarak kusursuz,
kesirler tam, NaN yok. Makro yazamadığı elementi sessizce düşürmüştü.
Birinci grup bunu yakalayamaz.

**Katman B** ikinci bir dil modeline sonucu inceletiyor. **Karar vermiyor**
— çünkü karar verdiğinde yanlış yaptı: `x(C)=0.01`'i ağırlıkça %1 okuyup
doğru bir sonucu reddettirdi. İtirazı *başka bir alaşım için* doğruydu.
Şimdi ipucu veriyor, hüküm vermiyor.

---

# 4 · Bugün ne yapıldı — sekiz düzeltme

## 4.1 · Derleyici

Ayarlar her istekte tek tek okunuyordu — bu bir *kural motoru*, derleyici
değil. Ve sessizce bozuluyordu.

Artık açılışta bir kez çözülüyor. Sertlik iki kademeli:

```
DURDURUR   bir kuralin sessizce KOSMAMASINA yol acacaksa
UYARIR     davranisi bozmayan tutarsizlik
```

## 4.2 · Giriş bazı — en ciddi bulgu

Çelik bileşimleri **ağırlıkça** yazılır (`%18 Cr`), motor ise **mol
kesriyle** çalışır. Dönüşüm birinin işi.

Ölçtük: SAF 2507 sorusunda model ağırlıkça yüzdeyi 100'e bölüp mol kesri
diye gönderdi.

```
element   agirlikca%   MODEL gonderdi   DOGRUSU
CR            25.00         0.25000      0.26655
MO             4.00         0.04000      0.02311
N              0.30         0.00300      0.01187   <- DORT KAT
```

Duplex paslanmazda azot doğrudan östenit oranını belirler. **Başka bir
alaşım hesaplandı**, ve dönen her sayı o yanlış alaşım için tutarlıydı.

Çözüm: `composition_basis` artık **zorunlu**. Verilmezse motor çalışmadan
reddediliyor. Ölçek tahmini yapılmıyor — `x(Cr)=0.25` gayet meşru bir mol
kesri, ve sayıların büyüklüğünden baz çıkarmaya çalışan bir sistem kimsenin
göremeyeceği bir şekilde yanılırdı.

## 4.3 · Çıkış bazı

`phase_molar_amounts` alanı **iki farklı nicelik** taşıyordu: tek nokta
hesabında gerçekten molar miktar, taramada **kütle kesri**. İkisi bir
keresinde %26 ayrışmış ve fark fiziksel etki sanılmıştı.

Artık her sonuç bazını, her nokta kaynağını söylüyor.

## 4.4 · Katman A beyan edildi

Sekiz kontrol elle yazılmış bir çağrı dizisiydi. Biri o diziden düşse
hiçbir şey fark etmezdi — testler geçer, sonuç *"doğrulandı"* döner.

Bu tam olarak yaşandı: `preflight.py`'de dokuz kural aylarca **çağıran
olmadan** durdu.

Şimdi kontroller `output.toml`'da beyan ediliyor, yüklemler kodda kalıyor.
Bir kontrolün kaybolması ya sunucuyu açtırmıyor ya da sayılabilir hale
geliyor. **Kapatma bayrağı eklenmedi.**

## 4.5 · `stop_rule` doğru katmana

`output.toml`'daydı ve *"sayılara dokunamaz"* değişmezini çiğniyordu — bir
sayıya dokunmuyor ama **başka bir hesabın koşup koşmayacağına** karar
veriyor. `input.toml`'a taşındı. Üretilen metin birebir aynı (966 karakter).

## 4.6 · Altı çıktı değişmezi

Dosyada altı ilke yazılıydı ama kimse okumuyordu: *sınırlar aralık olarak
verilir, tek noktada görülen faz "genişliği bilinmiyor" diye işaretlenir,
başarısız sonuç gizlenmez, ulaşılamayan hakem onaylamama sayılmaz, nokta
uydurulmaz, hakem karar vermez.*

Bunları **anahtar** yapmak yanlış olurdu — anahtar bir soru sorar, ve bu
soruların cevabı *"hayır, sistem dürüst davranmasın"* olamaz.

Onun yerine **kontrol** oldular: yükün son hâlinde koşuyor ve ihlal
edilirse rapor ediliyor. Kimyadan ayrı tutuluyor, çünkü buradaki ihlal
**bizim hatamız**, kullanıcının alaşımı hakkında bir yorum değil.

## 4.7 · Faz adı tek yazım

Motor aynı fazı yoldan yola farklı yazıyor: `LIQUID` / `LIQUID#1`,
`FCC-A1-AUTO#2` / `FCC_A1_AUTO#2`. Kayıtlarda **3.400 kez** `#1` sızmış ve
bir kıyaslama vakası bu yüzden düşmüştü.

İnce nokta: `#1` bir fazın *varsayılan* bileşim kümesi ve silinmeli. `#2`
ve üstü **gerçekten ayrı** kümeler — `FCC_A1_AUTO#2` Ag-Cu karışmazlık
boşluğunun bakırca zengin yarısı — ve korunmalı. Dokuz birim vakası bunu
sınıyor.

## 4.8 · Politika sabitleri dosyaya

Zaman aşımları (12/15/20/180/240 s), toleranslar (1e-6…1e-3), yeniden
deneme HTTP kodları, Scheil adım merdiveni, motor tercihi — hepsi
`execution.toml`'a.

**Taşınmayanlar da kasıtlı:** ayrıştırıcı sözlükler ve sembol tanımları
kodda kaldı. Büyük harfle yazılmış olmak taşınma sebebi değil.

---

# 5 · Aylardır bilinmeyen yavaşlamanın sebebi

Kıyaslama koşumu bazen dakikalar, bazen saatler sürüyordu. Not defterinde
şöyle yazıyordu: *"elendi: pencere, artık süreç, bellek, yük, kademe kodu,
ayar motoru. Sebep bilinmiyor."*

Koşucuya aşama zamanlaması eklendi. Sonuç:

```
--hizli (Katman B kapali)     141.1 s
tam     (Katman B acik)      2915.8 s
oran                          20.7 kat
```

Ve aşama kırılımı doğrudan gösterdi:

```
S2_ozet_erime_araligi   115.88 s   verify_b = 90.726 ms   %78
C3_steel1_genis_tarama  111.63 s   verify_b = 89.289 ms   %80
H1_krom_taramasi        104.02 s   verify_b = 90.698 ms   %87
```

Her birinde **tam 90 saniye** — hakem için konan üst sınır. Hesabın kendisi
saniyeler sürüyor.

Üç ihtimal vardı, ölçüm ikisini eledi:

```
A  vakalar giderek yavasliyor      HAYIR -- her arka uc "sabit"
B  cagrilar ARASINDA bekleme       HAYIR -- %0
C  bir ASAMA pahali                EVET  -- Katman B
```

`Katman B: BASARILI 35 · BASARISIZ 3 · ulasilamadi 12`. Ulaşamayan her
deneme 90 saniye tuttu — **koşumun %37'si ulaşılamayan bir hakemi
beklemekte** geçti.

Bu, sistemin kusuru değil: sağlayıcı (NVIDIA'nın ücretsiz katmanı) yük
altında cevap vermiyor. Sistem doğru davranıyor — hakem ulaşılamadığında
hesap normal dönüyor ve durum *"onaylanmadı"* değil *"ulaşılamadı"* diye
kaydediliyor.

---

# 6 · Bugün yapılan dört hata

Bunları yazmamın sebebi: **hepsi ölçümle bulundu, hiçbiri okumayla.**

```
1  dekorator kaymasi     yardimci fonksiyonlar dekorator ile fonksiyon
                         arasina girdi; calculate_equilibrium MCP'ye
                         hic kaydolmadi                      -> 35/86

2  cozumleme sirasi      baz donusumu kural denetiminden ONCE kosuyordu;
                         normalize edilen bilesim, olcek kuralina
                         gorunmeden geciyordu                -> 83/86

3  floor yanlis asamada  kontrol, dogrulama alani yazilmadan once
                         onu zorunlu tutuyordu               -> her hesap
                                                                passed=false

4  sessiz yedek          iki fonksiyon ayar motorunu bulamiyor,
                         sessizce varsayilana dusuyordu      -> uyari hic
                                                                cikmadi
```

Dördü de söz dizimi denetiminden, ayar denetiminden ve fark testinden
geçmişti. İlk üçü yalnızca **uçtan uca koşumda** göründü.

Dördüncüsü en sinsisi: `_transient_http` **doğru görünüyordu**, çünkü
yedeği dosyadaki değerin aynısıydı. Ayarı hiç okumadan doğru cevap
veriyordu. Yanlış cevap fark edilir; işi yapmadan gelen doğru cevap
edilmez.

Buna karşı denetime **dördüncü yön** eklendi: *"okuduğunu iddia eden
gerçekten okuyor mu?"* Dosyadaki değeri değiştir, cevap takip ediyor mu
bak. Bugünkü hatayı geri koyup test ettim — yakalıyor.

---

# 7 · `server.py` — ayrıntılı

Bu, listedeki son madde ve **bilerek sona bırakıldı**.

## Ölçüm

```
1.933 satir · 33 fonksiyon · 8 MCP araci

fonksiyon                        toplam  belge   kod
calculate_property_diagram          261     54   207
calculate_isothermal_section        259     56   203
calculate_phase_diagram             180     48   132
calculate_scheil_solidification     168     57   111
compare_alloys                      166     54   112
calculate_equilibrium               120     62    58
_attach_verification                107     13    94
```

**Uzunluğun üçte biri belge.** Her araç açıklamasına `stop_rule` metni
gömülüyor (966 karakter) — çünkü modelin okuduğu tek yer orası. Yani
`calculate_equilibrium` 120 satır görünüyor ama 58 satır kod.

## Asıl sorun: iki paralel fonksiyon

`calculate_property_diagram` ve `calculate_isothermal_section` neredeyse
aynı şeyi yapıyor — biri **sıcaklık** ekseninde tarıyor, öbürü **bileşim**
ekseninde. Blok yapıları:

```
property_diagram (261)          isothermal_section (259)
   docstring          55           docstring          57
   3 x kontrol/atama               3 x kontrol/atama
   _diagram_args       9           _section_args      10
   if blogu           70           _shape (ic fonk)   32
   dongu              24           try/except         42
   try/except         33           dongu              35
   data sozlugu       10           data sozlugu       10
   6 x _attach_*                   2 x _attach_*
   return                          return
```

İkisi de aynı sırayı izliyor: **kontrol → argüman topla → kademeleri dene →
grafik üret → yükü kur → `_attach_*` dizisini çalıştır → döndür.**

## Bunun bugün bana maliyeti

Üç kez aynı şeyi üç ayrı yere eklemem gerekti:

```
_attach_basis            uc farkli girintiye
_canonical_phases        uc farkli girintiye
_attach_mixed_basis_note uc farkli girintiye
```

Ve bir kez **girinti tuzağına düştüm**: 8 boşluklu desen 12 boşluklu satırın
içinde de eşleşiyordu, kör bir arama-değiştirme kodu bozdu.

## Refactor ne olurdu

```
server.py
├── tools/equilibrium.py           58 satir kod
├── tools/compare.py              112
├── tools/property_diagram.py
├── tools/isothermal_section.py
├── tools/scheil.py
├── tools/phase_diagram.py
└── series/scan_common.py          iki taramanin ORTAK govdesi
```

Kazanç: bir `_attach_*` adımı eklemek **bir yere** eklemek olur.

## Neden sona bırakıldı

```
davranis degistirme riski   YUKSEK
   bugunku dort hatanin ikisi tam bu tur duzenlemeden cikti

gorunur kazanc              YOK
   kullanici hicbir fark gormez

performans kazanci          YOK
   yavasligin sebebi olculdu ve server.py degil
```

Son madde önemli: **refactor'a önce girilseydi performans sorunu
çözülmezdi**, çünkü sebep Katman B'nin bekleme süresiydi. Sebebi ölçmeden
büyük bir dosyayı parçalamak, yanlış yerde çalışmak olurdu.

## Şimdi girilebilir mi

Evet, ve şartlar bugünkünden iyi:

```
86/86 kiyaslama          taban saglam
550 istekli fark testi   red davranisi kilitli
728 sonuclu Katman A     dogrulama kilitli
dort yonlu denetim       kopuk bag yakalanir
derleyici                bilinmeyen ad sunucuyu actirmaz
```

Bir şey bozulursa **hemen** görünür. Bugün üç kez öyle oldu.

---

# 8 · Doğrulama durumu

```
kiyaslama          86/86    (kolay 30/30 · orta 35/35 · zor 21/21)
fark testi         160 istek, kural AYNI yerlerde tetikleniyor
Katman A farki     728 gercek sonuc, sifir fark
ayar denetimi      DORT yonlu, temiz
derleme            temiz -- her ad bagli, okunmayan anahtar yok
arac kaydi         8/8
```

---

# 9 · Kalanlar

**Kod:**

```
server.py refactor    bakim kolayligi, davranis degismemeli
_MALFORMED_MARKS      failure_classify bizim kendi kontrol MESAJLARIMIZI
                      esliyor; ifade degisirse siniflandirma sessizce
                      kor olur -- bugun iki kez yakaladigimiz sinif
E4                    askiya alinmis faz + yedek motor
G3                    gaz fazi element yerine MOLEKUL turu olarak geliyor
```

**Bekleyen:**

```
push                  14 commit yerel
iki olcum kaydi       1.29 ve 1.6 sonuc dosyasina islenmedi
dil                   iki cevap Ingilizce geldi, sebebi olculmedi
```

**Asıl iş — ölçüm:**

```
Blok 1     6 soru kaldi
Blok 2-7   160 soru, HIC sorulmadi
```

Bugün eklenen her şey — zorunlu baz, `floor`, altı değişmez, faz adı
birleştirmesi — **Blok 4'ün** (dürüst raporlama) ölçtüğü şeyler için
eklendi. İki soru soruldu ve ikisi de olumlu çıktı: ağırlıkça hatası
kapandı, faz adı düzeldi. Ama 40 sorunun 38'i sorulmadı.

**Kod hazır; işe yarayıp yaramadığını ancak sorarak öğreniriz.**
