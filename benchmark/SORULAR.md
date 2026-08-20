# Kıyaslama Soruları

Her soru için üç şey var: **soru metni**, **neyi sınadığı** ve **beklenen cevap**.

Beklenen cevabın her maddesi hesap makinesiyle kontrol edilebilir. Termodinamik bilgisi gerektiren tek bir ölçüt yok — kütle korunumu ve stokiyometri, motorun kendi çıktısından bağımsız iki bağımsız denetimdir.

Zorluk, cümlenin kulağa nasıl geldiğine göre değil, sistemin başına ne geldiğine göre belirlendi:

- **kolay** — tek araç, motor ilk denemede yakınsıyor
- **orta** — biri var: motor kademe atlıyor, faz geçişi var, önce arama gerekiyor, ya da istek reddedilmeli
- **zor** — ikisi ya da fazlası var: motor kısmen başarısız, bileşim kümeleri, hiç denenmemiş sistem sınıfı

Her soruyu **temiz bir oturumda** sor. Aynı oturumda arka arkaya sormak, modelin kendi önceki cevabını görmesine yol açar; o zaman ölçülen şey sistem değil konuşma olur.


---

# A · Tek fazlı denge

*6 soru — kolay 4, orta 2, zor 0*


## A1 · A1_alni_bcc4_1200K
*zorluk: kolay*

**Soru**
```
alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 1200 K'de denge hesapla
```

**Neyi sınıyor**
Al-Ni 50-50 bilesimi genis bir araligta tek fazli B2/BCC4 olarak kararli. Motorun tek faz durumunu bozmadan dondurmesi.

**Beklenen cevap**
- Toplam **1 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## A2 · A2_alni_sivi_1950K
*zorluk: kolay*

**Soru**
```
alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 1950 K'de denge hesapla
```

**Neyi sınıyor**
Ayni bilesim erime noktasinin ustunde: tek fazli sivi. A1 ile birlikte, ayni sistemin iki ucunu kapsiyor.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `LIQUID`
- Toplam **1 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## A3 · A3_agcu_sivi_1200K
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 1200 K'de denge hesapla
```

**Neyi sınıyor**
Ag-Cu otektik sicakliginin (~1056 K) uzerinde tamamen sivi. Ayni veritabani D grubunda karismazlik boslugu icin de kullaniliyor; burada sadelestirilmis ucu.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `LIQUID`
- Toplam **1 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## A4 · A4_alfe_1000K
*zorluk: kolay*

**Soru**
```
AlFe-4SLBF.TDB'de Al=0.2 Fe=0.8 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
Bu projede elle dogrulanmis bir referans deger. Dort alt orgulu BCC modeli kullanan bir veritabani -- steel1'den tamamen farkli bir model ailesi.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- Gibbs enerjisi **-59,870.500 J** olmalı (± 5.0). Elle doğrulanmış referans.


## A5 · A5_steel1_1200K_native
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1200 K'de denge hesapla
```

**Neyi sınıyor**
OCASI bu noktada hata 4204 ile yakinsamiyor; native motor devraliyor. Kademeli motorun calistiginin en net kaniti, ve referans degeri elle dogrulanmis.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `FCC_A1`
- Toplam **1 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- Gibbs enerjisi **-56,563.789 J** olmalı (± 2.0). Elle doğrulanmış referans.
- Kullanılan motor `native_oc` olmalı.


## A6 · A6_steel1_dort_element_tek_faz
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.949 C=0.01 Cr=0.04 V=0.001 icin 1100 K'de denge hesapla
```

**Neyi sınıyor**
Dort element, yine tek faz. Seyreltik V (0.001) sonucta gorunuyor mu -- ama tek fazli oldugu icin bu bir kutle korunumu ozdesligidir, olcum degildir. B grubundaki cok fazli surumuyle bilincli olarak eslestirildi.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `FCC_A1`
- Toplam **1 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


---

# B · Çok fazlı denge ve element paylaşımı

*12 soru — kolay 3, orta 6, zor 3*


## B1 · B1_steel1_FeC_1000K
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
Projenin en cok dogrulanmis referans noktasi. Ferrit +/ grafit dengesi; karbonun neredeyse tamami grafite gidiyor.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `BCC_A2`, `GRAPHITE`
- Toplam **2 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- Gibbs enerjisi **-41,981.578 J** olmalı (± 2.0). Elle doğrulanmış referans.
- Kullanılan motor `ocasi` olmalı.


## B2 · B2_steel1_FeC_yuksek_karbon
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.95 C=0.05 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
Ayni sistem, bes kat karbon. Ferritin karbon cozme kapasitesi doymus oldugu icin fazla karbon grafite gitmeli; yani grafit miktari artmali, ferritin IC bilesimi degismemeli.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `BCC_A2`, `GRAPHITE`
- Toplam **2 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## B3 · B3_steel1_FeC_dusuk_karbon
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.98 C=0.02 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
Ayni sistemin ucuncu noktasi. B1/B2/B3 birlikte, tek bir ekseni tarayarak motorun tutarli davrandigini gosteriyor.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `BCC_A2`, `GRAPHITE`
- Toplam **2 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## B4 · B4_steel1_M23C6
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.79 Cr=0.20 C=0.01 icin 1100 K'de hesapla
```

**Neyi sınıyor**
Krom karburu olusuyor. Karbonun neredeyse tamami karbure girdigi icin karbur miktari 0.01/0.2069 ~ 0.048 civari olmali -- stokiyometriden onceden hesaplanabilir bir sayi.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `BCC_A2`, `M23C6`
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- `M23C6` fazının karbon oranı **6/29 = 0.2069** olmalı (formülden gelir, motordan değil).


## B5 · B5_steel1_M7C3_seyreltik_V
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.919 C=0.04 Cr=0.04 V=0.001 icin 1100 K'de hesapla
```

**Neyi sınıyor**
A6'nin cok fazli esdegeri: ayni seyreltik V (0.001), ama karbon artirilarak sistem iki fazli hale getirildi. Artik V'nin fazlar arasindaki paylasimi gercek bir olcum -- tek fazli surumde bu imkansizdi.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `FCC_A1`, `M7C3#1`
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- `M7C3#1` fazının karbon oranı **3/10 = 0.3000** olmalı (formülden gelir, motordan değil).


## B6 · B6_steel1_bes_element_uc_faz
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 icin 1100 K'de hesapla
```

**Neyi sınıyor**
Bes element, uc faz, iki seyreltik element (V ve Mo) paylasiliyor. Bes bagimsiz kutle dengesi ayni anda kapanmali. Bu vaka uc asamali yinelemeli olcumun de konusuydu (bkz. RAPOR.md, Bolum 3).

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `BCC_A2#1`, `M23C6`, `FCC_A1`
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- `M23C6` fazının karbon oranı **6/29 = 0.2069** olmalı (formülden gelir, motordan değil).
- Kullanılan motor `native_oc` olmalı.


## B7 · B7_steel1_dusuk_sicaklik
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 icin 900 K'de hesapla
```

**Neyi sınıyor**
B6 ile ayni bilesim, 200 K asagida. Dusuk sicaklikta karbur miktari artmali. Ayni bilesimin iki sicakligi, motorun sicaklik bagimliligini tutarli isledigini gosteriyor.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## B8 · B8_saf2507_dubleks
*zorluk: orta*

**Soru**
```
saf2507.TDB'de Fe=0.62 Cr=0.25 Ni=0.07 Mo=0.04 Mn=0.01 N=0.01 icin 1200 K'de hesapla
```

**Neyi sınıyor**
Karbonsuz bir paslanmaz celik veritabani (Cr, Fe, Mn, Mo, N, Ni). Cift fazli paslanmaz celikler ferrit + ostenit dengesindedir. Karburlerin hic olmadigi bir cok fazli sistem -- B grubunun geri kalanindan farkli bir kimya.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## B9 · B9_iron4cd_FeNiC
*zorluk: orta*

**Soru**
```
iron4cd.TDB'de Fe=0.85 Ni=0.10 C=0.05 icin 1100 K'de hesapla
```

**Neyi sınıyor**
En buyuk veritabani (13 element, 124 faz). Nikel iceren tek celik dosyasi; karbon eklenerek cok fazli hale getirildi. 124 faz arasindan dogru olanlari secmesi gerekiyor.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## B10 · B10_steel7_alti_element
*zorluk: zor*

**Soru**
```
steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 Fe=0.837 icin 1173 K'de hesapla
```

**Neyi sınıyor**
Alti element, dort faz, iki farkli karbur (M23C6 ve M6C) artikMC tipi bir dorduncu faz. Uc bagimsiz stokiyometri ve alti kutle dengesi ayni anda tutmali. Bu vaka zaman asimi duzeltmesinin de dogrulamasiydi.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.
- `M23C6` fazının karbon oranı **6/29 = 0.2069** olmalı (formülden gelir, motordan değil).
- `M6C` fazının karbon oranı **1/7 = 0.1429** olmalı (formülden gelir, motordan değil).


## B11 · B11_steel7_dusuk_sicaklik
*zorluk: zor*

**Soru**
```
steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 Fe=0.837 icin 1000 K'de hesapla
```

**Neyi sınıyor**
B10 ile ayni alti elementli bilesim, 1000 K'de. Faz kumesi degismesi bekleniyor; hangi karburlerin cikacagi onceden bilinmiyor, olcut kutle korunumu ve element varligi.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## B12 · B12_iron4cd_yedi_element
*zorluk: zor*

**Soru**
```
iron4cd.TDB'de Fe=0.70 Cr=0.16 Ni=0.08 Mo=0.02 Mn=0.02 Si=0.01 C=0.01 icin 1100 K'de hesapla
```

**Neyi sınıyor**
MOTOR SINIRI. Yedi element birden: OCASI hata 4204 ile yakinsamiyor, native motor da cozemiyor. Vaka bilerek birakildi -- olculen sey artik dogru sayi degil, DOGRU BASARISIZLIK: sistem cokmeden, uydurma bir sayi uretmeden, iki kademeyi de denedigini soyleyerek duruyor mu? Bu projede ayni durum bir zamanlar segfault veriyordu.

**Beklenen cevap**
- **Hesaplanamamalı** — ve bu doğru davranıştır. Sistem çökmeden, uydurma bir sayı vermeden, iki motor kademesini de denediğini söyleyerek durmalı.


---

# R · Doğru red — reddedilmesi gereken istekler

*25 soru — kolay 12, orta 9, zor 4*


## R1 · red_olmayan_dosya
*zorluk: kolay*

**Soru**
```
olmayan_bir_dosya.TDB'de Fe=0.9 C=0.1 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
Var olmayan bir veritabani dosyasi motora gitmeden yakalaniyor mu

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `Database not found` geçmeli.


## R2 · red_olmayan_element_ni
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.9 Ni=0.1 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
steel1'de nikel yok; motor yine de bir sayi uretebiliyor (saf demir icin), o yuzden red motordan ONCE olmali

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `NI` geçmeli.


## R3 · red_tek_element_fe
*zorluk: kolay*

**Soru**
```
steel1.TDB'de saf demir icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
Tek elementli bilesim motorun kosul sistemini bozup segfault'a goturuyordu; PREFLIGHT bunu temiz hataya cevirir

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `At least two elements` geçmeli.


## R4 · red_negatif_sicaklik
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin -500 K'de denge hesapla
```

**Neyi sınıyor**
Kelvin negatif olamaz

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `Temperature must be positive` geçmeli.


## R5 · red_sifir_sicaklik
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 0 K'de denge hesapla
```

**Neyi sınıyor**
Sinir degeri: 0 K de reddedilmeli, sadece negatif degil

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `Temperature must be positive` geçmeli.


## R6 · red_negatif_basinc
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K, -100000 Pa'da hesapla
```

**Neyi sınıyor**
Basinc pozitif olmali

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `Pressure must be positive` geçmeli.


## R7 · red_sifir_basinc
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K, 0 Pa'da hesapla
```

**Neyi sınıyor**
Sinir degeri: 0 Pa da reddedilmeli

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `Pressure must be positive` geçmeli.


## R8 · red_negatif_bilesim
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=1.01 C=-0.01 icin 1000 K'de hesapla
```

**Neyi sınıyor**
Negatif mol miktari; normalize edilirse sessizce anlamsiz bir bilesime donusurdu

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `negative` geçmeli.


## R9 · red_ters_sicaklik_araligi
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 1500 K'den 800 K'e diyagram ciz
```

**Neyi sınıyor**
Diyagramda alt sinir ust sinirdan buyuk

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `must be less than` geçmeli.


## R10 · red_agcu_graphite_askiya
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 1000 K'de GRAPHITE fazini kapatarak hesapla
```

**Neyi sınıyor**
agcu'da GRAPHITE yok. Motor bu istegi SESSIZCE yutuyordu ve kararli dengeyi donduruyordu -- istemci de grafitin bastirildigini raporluyordu. Canli olarak gorulen vaka.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `GRAPHITE` geçmeli.


## R11 · red_bilesim_sifir
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0 C=0 icin 1000 K'de hesapla
```

**Neyi sınıyor**
Toplami sifir olan bilesim normalize edilemez (sifira bolme)

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `sum to zero` geçmeli.


## R12 · red_diyagram_negatif_tmin
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin -200 K'den 1400 K'e diyagram ciz
```

**Neyi sınıyor**
Diyagramin alt sinirinin kendisi gecersiz

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `temperature_min_K must be positive` geçmeli.


## R13 · red_saf2507_karbon
*zorluk: orta*

**Soru**
```
saf2507.TDB'de Fe=0.6 Cr=0.25 Ni=0.07 Mo=0.04 C=0.04 icin 1200 K'de hesapla
```

**Neyi sınıyor**
Bir paslanmaz celik veritabaninda karbon istemek son derece makul gorunur; saf2507 karbon icermez (Cr, Fe, Mn, Mo, N, Ni). Istegin kendisi degil, hedefin icerigi karar veriyor.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `C` geçmeli.


## R14 · red_bef_demir
*zorluk: orta*

**Soru**
```
BEF.TDB'de Fe=0.7 Ni=0.3 icin 1400 K'de denge hesapla
```

**Neyi sınıyor**
Isim tuzagi: BEF.TDB demir icermez (Mo, Ni, Re). Ismin cagristirdigi seyle icerigi ayri.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `FE` geçmeli.


## R15 · red_alni_bcc_a2_askiya
*zorluk: orta*

**Soru**
```
alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 1200 K'de BCC_A2 fazini kapatarak hesapla
```

**Neyi sınıyor**
alni-4slx'te BCC_A2 yok -- 'A2' ve 'BCC4' var. Cok yaygin bir faz adi baska bir veritabaninda baska yazilmis olabiliyor.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `BCC_A2` geçmeli.


## R16 · red_alfe_fcc_a1_askiya
*zorluk: orta*

**Soru**
```
AlFe-4SLBF.TDB'de Al=0.2 Fe=0.8 icin 1000 K'de FCC_A1 fazini kapatarak hesapla
```

**Neyi sınıyor**
AlFe-4SLBF'de FCC_A1 degil 'A1_FCC' var -- ayni iki parca, ters sirada. Yazim degil, siralama tuzagi.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `FCC_A1` geçmeli.


## R17 · red_austenite_askiya
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1200 K'de ostenit fazini kapatarak hesapla
```

**Neyi sınıyor**
'AUSTENITE' gercek bir metalurji terimi ama TDB'nin faz adi degil (FCC_A1). Alan bilgisi ile veritabani sozlugunun ayrimi.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `AUSTENITE` geçmeli.


## R18 · red_bilesim_yuzde
*zorluk: orta*

**Soru**
```
steel1.TDB'de %99 Fe ve %1 C icin 1000 K'de hesapla
```

**Neyi sınıyor**
Yuzde olarak yazilmis bilesim (toplam 100). Kod yorumu 'yine de normalize edilir' diyor ama problems listesine girdigi icin istek REDDEDILIYOR -- niyet ile davranis ayrisiyor.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `sum to` geçmeli.


## R19 · red_bilesim_cok_kucuk
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.099 C=0.001 icin 1000 K'de hesapla
```

**Neyi sınıyor**
Toplam 0.1 -- olcek hatasinin ters yonu

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `sum to` geçmeli.


## R20 · red_mgnacl_potasyum
*zorluk: orta*

**Soru**
```
MgNaCl.TDB'de K=0.3 Cl=0.7 icin 1100 K'de denge hesapla
```

**Neyi sınıyor**
Ayni grup elementi (Na yerine K) -- kimyasal olarak yakin, veritabani icin tamamen yabanci

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `K` geçmeli.


## R21 · red_iki_hata_birden
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.9 Ni=0.1 icin -300 K'de hesapla
```

**Neyi sınıyor**
Iki bagimsiz hata ayni istekte. Ikisinin de raporlanmasi gerekir -- ilkinde durup otekini gizlemek, kullaniciyi iki tur dondurur (derleyicilerdeki hata kurtarma ilkesi).

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.
- Red gerekçesinde `Temperature must be positive` geçmeli.


## R22 · red_ikinci_element_sifir
*zorluk: zor*

**Soru**
```
steel1.TDB'de Fe=1.0 C=0.0 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
BILINEN BOSLUK. PREFLIGHT 'en az iki element' derken sozluk ANAHTARLARINI sayiyor, sifirdan farkli miktarlari degil -- kendi hata metni 'nonzero amount' dese de. Bu istek PREFLIGHT'tan GECER ve motor katmaninda reddedilir. Beklenen: yine de hicbir sayi donmemesi, ama redde asamanin PREFLIGHT olmamasi.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red PREFLIGHT'ta **değil**, bir alt katmanda olmalı — asıl ölçülen bu.


## R23 · red_bilesim_kumesi_ekli_faz
*zorluk: zor*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 1000 K'de GRAPHITE#1 fazini kapatarak hesapla
```

**Neyi sınıyor**
'GRAPHITE#1' -- '#1' bir calisma zamani bilesim kumesi eki, TDB yalnizca taban adi bildirir. PREFLIGHT eki soyup taban adi aramali; agcu'da GRAPHITE olmadigi icin yine reddetmeli.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `not declared` geçmeli.


## R24 · red_diyagram_esit_sinir
*zorluk: zor*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 1000 K'den 1000 K'e diyagram ciz
```

**Neyi sınıyor**
T_min == T_max. Ters degil, esit -- '>' degil '>=' ile kontrol edilmis olmasi gerekiyor. Sifir genislikte bir tarama diyagram degildir.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `must be less than` geçmeli.


## R25 · red_olcek_sinirinin_hemen_disi
*zorluk: zor*

**Soru**
```
steel1.TDB'de Fe=2.475 C=0.025 icin 1000 K'de hesapla
```

**Neyi sınıyor**
Toplam 2.5 -- kabul araligi [0.5, 2.0]'in hemen disi. Kasitli bir olcek secimi gibi gorunur (iki mollik bir sistem?), ama esik disinda. Esigin kendisinin bir TERCIH oldugunu, degismez bir kural olmadigini gosteren vaka.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `sum to` geçmeli.


---

**Toplam: 43 soru.**

