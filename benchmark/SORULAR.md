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

# C · Faz geçişleri (sıcaklık taraması)

*8 soru — kolay 2, orta 4, zor 2*


## C1 · C1_agcu_otektik
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 800-1400 K faz diyagrami ciz
```

**Neyi sınıyor**
Ag-Cu otektigi ~1056 K'de. Tarama kati bolgeden sivi bolgeye gecmeli; her iki uc da ayni veri setinde gorunmeli.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `LIQUID`
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C2 · C2_alni_erime
*zorluk: kolay*

**Soru**
```
alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 500-2000 K faz diyagrami ciz
```

**Neyi sınıyor**
NiAl genis bir araligta tek fazli, sonra ~1920 K'de eriyor. Tarama boyunca hem kati hem sivi faz gorunmeli.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `LIQUID`
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C3 · C3_steel1_genis_tarama
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 300-2000 K faz diyagrami ciz
```

**Neyi sınıyor**
300-2000 K: ferrit+grafit, ostenit, delta-ferrit+sivi ve tam sivi -- dort ayri rejim tek taramada. Bu sunucunun en genis sicaklik araligi.

**Beklenen cevap**
- Çözülemeyen nokta oranı %20'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C4 · C4_steel1_karbur_cozunmesi
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 icin 900-1400 K faz diyagrami ciz
```

**Neyi sınıyor**
Bes elementli celik, 900-1400 K. Sicaklik arttikca karbur cozunup matrise girmeli. B6/B7 ile ayni bilesim -- iki tek nokta ile bir tarama ayni sistemi farkli aciardan gosteriyor.

**Beklenen cevap**
- Çözülemeyen nokta oranı %20'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C5 · C5_agcu_otektik_bilesim
*zorluk: orta*

**Soru**
```
agcu.TDB'de Ag=0.72 Cu=0.28 icin 900-1200 K faz diyagrami ciz
```

**Neyi sınıyor**
Tam otektik bilesimde (%72 Ag) tarama. Otektikte kati->sivi gecisi tek sicaklikta olur; dar bir aralikta olup bitmeli.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `LIQUID`
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C6 · C6_alfe_tarama
*zorluk: orta*

**Soru**
```
AlFe-4SLBF.TDB'de Al=0.2 Fe=0.8 icin 800-1800 K faz diyagrami ciz
```

**Neyi sınıyor**
Dort alt orgulu BCC modeli kullanan bir veritabaninda tarama. A4 ile ayni bilesim, tek nokta yerine aralik.

**Beklenen cevap**
- Çözülemeyen nokta oranı %25'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C7 · C7_alni_yakinsama_zorlugu
*zorluk: zor*

**Soru**
```
alni-4slx.TDB'de Al=0.75 Ni=0.25 icin 800-1700 K faz diyagrami ciz
```

**Neyi sınıyor**
BILINEN ZOR NOKTA. Bu bilesim ve aralik, Python dongusu yoluna dustugunde noktalarin ~%23'u yakinsamiyor. Olculen sey, sistemin eksigi GIZLEMEDEN raporlamasi: her dusen nokta kendi hatasini tasimali ve Katman A orani bildirmeli.

**Beklenen cevap**
- Çözülemeyen nokta oranı %40'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## C8 · C8_steel7_tarama
*zorluk: zor*

**Soru**
```
steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 Fe=0.837 icin 900-1400 K faz diyagrami ciz
```

**Neyi sınıyor**
Alti elementli celik uzerinde tarama. Her nokta ayri bir cok fazli hesap; en pahali vaka. B10/B11'in tarama hali.

**Beklenen cevap**
- Çözülemeyen nokta oranı %30'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


---

# D · Bileşim kümeleri ve karışmazlık boşluğu

*6 soru — kolay 1, orta 3, zor 2*


## D1 · D1_agcu_karismazlik
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 900 K'de denge hesapla
```

**Neyi sınıyor**
Otektik altinda iki FCC katisi bir arada: biri gumusce, digeri bakirca zengin. Ayni faz adi, iki bilesim kumesi.

**Beklenen cevap**
- Toplam **2 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## D2 · D2_agcu_gumus_zengin
*zorluk: orta*

**Soru**
```
agcu.TDB'de Ag=0.9 Cu=0.1 icin 900 K'de denge hesapla
```

**Neyi sınıyor**
Boslugu gumus tarafindan gecmek. Faz miktarlari kolun kaldirac kuralina uymali: gumusce zengin taraf agir basmali.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## D3 · D3_agcu_bakir_zengin
*zorluk: orta*

**Soru**
```
agcu.TDB'de Ag=0.2 Cu=0.8 icin 900 K'de denge hesapla
```

**Neyi sınıyor**
Ayni boslugun oteki ucu. D2 ile birlikte, iki bilesim kumesinin bilesime gore yer degistirdigini gosteriyor.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## D4 · D4_agcu_dusuk_sicaklik
*zorluk: orta*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 700 K'de denge hesapla
```

**Neyi sınıyor**
Sicaklik dustukce bosluk genisler, iki katinin bilesimleri birbirinden uzaklasir. Ayni bilesim, D1'den 200 K asagida.

**Beklenen cevap**
- Toplam **2 faz** olmalı.
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## D5 · D5_steel7_iki_fcc_kumesi
*zorluk: zor*

**Soru**
```
steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 Fe=0.837 icin 1173 K'de hesapla
```

**Neyi sınıyor**
AYNI SONUCTA IKI FCC KUMESI: biri demirce zengin matris (FCC_A1_AUTO#2, Fe 0.92), digeri vanadyum karburu (FCC_A1#1, C 0.46 / V 0.36). Ikisi de FCC_A1 adini tasir ve yalnizca bilesim ayirt eder. Faz adinin kimlik olmadigini gosteren en net vaka.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `FCC_A1_AUTO#2`, `FCC_A1#1`
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## D6 · D6_agcu_otektik_noktasinda
*zorluk: zor*

**Soru**
```
agcu.TDB'de Ag=0.6 Cu=0.4 icin 1056 K'de denge hesapla
```

**Neyi sınıyor**
Tam otektik sicakliginda (1056 K): kati ve sivi bir arada, gecis araligi bir kac Kelvin. Sayisal olarak en hassas nokta; kucuk bir sapma tamamen farkli bir faz kumesi verir.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


---

# E · Yarı kararlı hesap (faz kapatma)

*4 soru — kolay 1, orta 2, zor 1*


## E1 · E1_steel1_grafit_kapali
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K'de GRAPHITE fazini kapatarak hesapla
```

**Neyi sınıyor**
Grafit kapatilinca karbon metalik fazlarda cozunmek zorunda kalir; sistem ferrit+grafitten ferrit+ostenite gecer. Kapatilan faz sonucta gorunmemeli.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## E2 · E2_steel1_grafit_kapali_enerji
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K'de GRAPHITE fazini kapatarak hesapla ve enerjiyi acik haliyle karsilastir
```

**Neyi sınıyor**
TERMODINAMIK BIR ESITSIZLIK. Kararli bir fazi askiya almak Gibbs enerjisini ancak YUKSELTEBILIR, asla dusuremez -- cunku serbest secenekler kumesi daralir. Acikken -41981.6, kapaliyken bundan daha az negatif olmali. Referans gerektirmeyen, dogrudan fizikten gelen bir olcut.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- Gibbs enerjisi **-41,966.000 J** olmalı (± 50.0). Elle doğrulanmış referans.


## E3 · E3_steel1_karbur_kapali
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.79 Cr=0.20 C=0.01 icin 1100 K'de M23C6 fazini kapatarak hesapla
```

**Neyi sınıyor**
Bu sefer kapatilan sey grafit degil bir karbur. B4 ile ayni bilesim: acikken M23C6 olusuyordu, kapaliyken krom ve karbon baska bir yere gitmek zorunda.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## E4 · E4_steel7_iki_faz_kapali
*zorluk: zor*

**Soru**
```
steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 Fe=0.837 icin 1173 K'de M23C6 ve M6C fazlarini kapatarak hesapla
```

**Neyi sınıyor**
Alti elementli sistemde AYNI ANDA IKI karbur kapatiliyor. B10'da dort faz cikiyordu; ikisi engellenince kalan elementlerin baska bir denge bulmasi gerekiyor.

SONUC: hesaplanamiyor, ve bu bir MIMARI SINIRI ortaya cikardi. Faz kapatma yalnizca OCASI'de destekleniyor; native motor kademesi suspended_phases verilen istekler icin hic devreye girmiyor. Yani yari kararli hesaplarda kademeli motorun guvenlik agi YOK -- OCASI yakinsamazsa baska deneyecek bir sey kalmiyor. B12'de iki kademe de denenmisti; burada tek kademe var.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.


---

# F · İki bileşimin karşılaştırılması

*4 soru — kolay 2, orta 1, zor 1*


## F1 · F1_steel1_karbon_farki
*zorluk: kolay*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 ile Fe=0.95 C=0.05 bilesimlerini 1000 K'de karsilastir
```

**Neyi sınıyor**
Ayni celigin iki karbon seviyesi. Ikisinde de ayni fazlar cikmali; degisen sey grafit miktari olmali, ferritin IC bilesimi degil -- ferrit karbonu zaten doymus durumda.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.


## F2 · F2_agcu_bilesim_farki
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag=0.8 Cu=0.2 ile Ag=0.3 Cu=0.7 bilesimlerini 900 K'de karsilastir
```

**Neyi sınıyor**
Karismazlik boslugunun iki yakasi ayni sicaklikta. Fazlar ayni, miktarlar farkli olmali.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.


## F3 · F3_steel1_krom_farki
*zorluk: orta*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 ile Fe=0.79 Cr=0.20 C=0.01 bilesimlerini 1100 K'de karsilastir
```

**Neyi sınıyor**
Krom eklemenin faz kumesini degistirmesi: kromsuz tarafta grafit, kromlu tarafta karbur beklenir. Yani iki alasimin 'yalniz bende olan fazlar' listeleri bos olmamali.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.


## F4 · F4_steel1_iki_motor_kademesi
*zorluk: zor*

**Soru**
```
steel1.TDB'de Fe=0.99 C=0.01 bilesimini 1000 K ile ayni bilesimin 1200 K halini karsilastir
```

**Neyi sınıyor**
Iki taraf farkli motor kademelerine dusuyor: biri OCASI ile cozuluyor, otekinde OCASI yakinsamayip native devraliyor. Karsilastirma ozetinin, farkli motorlardan gelen iki sonucu tutarli bicimde birlestirebilmesi gerekiyor.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.


---

# G · Çelik dışı sistemler (oksit, tuz, gaz)

*5 soru — kolay 2, orta 2, zor 1*


## G1 · G1_mgnacl_tuz
*zorluk: kolay*

**Soru**
```
MgNaCl.TDB'de Na=0.5 Cl=0.5 icin 1100 K'de denge hesapla
```

**Neyi sınıyor**
TUZ SISTEMI -- hic denenmedi. Metalik olmayan, iyonik bir sistem; faz adlari da farkli (SALT, NACL, MGCL2).

Vakayi yazarken iki sey ogrenildi:

1. Ilk yazilista bilesim yuk dengesiz secilmisti (Na + 2Mg = 0.65 ama Cl = 0.5). Iyonik sistemde katyon ve anyon yukleri esitlenmek zorunda. Vaka yazarinin hatasiydi.

2. Yuk dengesi duzeltilince de yakinsamadi. Daraltarak sinir bulundu: SAF NaCl calisiyor, ama bilesimde MAGNEZYUM olan hicbir nokta cozulmuyor (saf MgCl2 dahil, %5 Mg katkisi dahil, 1300 K'de bile). Yani sinir sicaklikta ya da yuk dengesinde degil, Mg iceren fazlarin kendisinde.

Ayrica dikkat: saf NaCl sonucu ayni fazin IKI OZDES bilesim kumesini donduruyor (NACL#1 ve NACL_AUTO#2, her biri 0.5). Kutle korunumu kapaniyor ama gosterim dejenere -- tek bir faz ikiye bolunmus gorunuyor.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## G2 · G2_ou_oksit
*zorluk: kolay*

**Soru**
```
OU.TDB'de U=0.333 O=0.667 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
OKSIT SISTEMI -- hic denenmedi. UO2 stokiyometrisine yakin bir bilesim (U 1 : O 2). Bu veritabaninda cok sayida stokiyometrik bilesik ve bir IONIC_LIQUID fazi var.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## G3 · G3_cho_gaz
*zorluk: orta*

**Soru**
```
CHO-gas.TDB'de C=0.2 H=0.5 O=0.3 icin 1000 K'de denge hesapla
```

**Neyi sınıyor**
GAZ FAZI -- hic denenmedi, ve BIR KUSUR BULDU.

Motor hesabi yapiyor (GAS = 1.0, G = -136100 J) ama ayristirici gaz fazinin bilesimini yanlis okuyor: element kesirleri yerine MOLEKUL TURLERINI dolduruyor --
  H2 0.4339, C1O1 0.3223, C1O2 0.1211, H2O1 0.1138, C1H4 0.0088 ...
ve baslik metninden bir kalinti yakaliyor: 'ARE': 73.0.

Element kutle dengesi bu yuzden asla kapanamaz (C icin 2.5e-30 dondu, 0.2 beklenirken). Kati ve sivi fazlarda bilesenler zaten element oldugu icin kusur bugune kadar gorunmemisti; gaz fazinda bilesenler molekul.

Vaka bilerek acik birakildi: bu bir gerileme degil, belgelenmis bir sinir. Duzeltilirse bayrak kalkar ve vaka normal olcutlerine doner.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.


## G4 · G4_bef_intermetalik
*zorluk: orta*

**Soru**
```
BEF.TDB'de Mo=0.3 Ni=0.5 Re=0.2 icin 1400 K'de denge hesapla
```

**Neyi sınıyor**
Sert intermetalik sistem (Mo-Ni-Re): SIGMA, CHI, MONI_DELTA gibi fazlar. Celiklerde de gorulen ama burada baskin olan faz aileleri. Bu veritabani da hic denenmedi.

**Beklenen cevap**
- Faz miktarları **1'e toplamalı**.
- **Kütle dengesi:** her element için `Σ(faz miktarı × fazdaki derişim)` istenen miktara eşit olmalı.
- İstenen **her element** en az bir fazın bileşiminde görünmeli. Görünmeyen bir element hesaba hiç girmemiştir.


## G5 · G5_ou_tarama
*zorluk: zor*

**Soru**
```
OU.TDB'de U=0.333 O=0.667 icin 1000-2500 K faz diyagrami ciz
```

**Neyi sınıyor**
Oksit sisteminde sicaklik taramasi: hic denenmemis bir veritabani sinifi ile hic denenmemis bir kombinasyon. Hem diyagram yolu hem oksit ayristirmasi ayni anda sinaniyor.

**Beklenen cevap**
- Çözülemeyen nokta oranı %40'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


---

# H · Bileşim ekseni (izotermal kesit)

*4 soru — kolay 0, orta 3, zor 1*


## H1 · H1_krom_taramasi_1100K
*zorluk: orta*

**Soru**
```
steel1.TDB'de 1100 K'de Fe-%20Cr-%1C alasiminda kromu %1'den %30'a cikarirsam hangi fazlar cikar
```

**Neyi sınıyor**
Krom artarken uc sey birden olmali: karbur M7C3'ten M23C6'ya donmeli, matris ostenitten ferrite gecmeli, ve eksenin sonu gercekten hesaplanmali. Son nokta ayrica STEP'in surekliligini sinar -- STEP orada yari kararli FCC+M7C3 veriyordu, kararli cevap BCC+M23C6.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `FCC_A1`, `M7C3`, `M23C6`, `BCC_A2`
- Eksen boyunca `M7C3` **`M23C6`'den önce** görünmeli.
- Eksen boyunca `FCC_A1` **`BCC_A2`'den önce** görünmeli.
- Eksenin başında: `FCC_A1`
- Eksenin sonunda: `BCC_A2`, `M23C6`
- İstenen eksen aralığının **iki ucu da** sonuçta olmalı.
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## H2 · H2_karbon_taramasi
*zorluk: orta*

**Soru**
```
steel1.TDB'de 1100 K'de Fe-%10Cr alasiminda karbonu %0.1'den %5'e cikarirsam ne olur
```

**Neyi sınıyor**
Ayni sistemde bu sefer karbon taraniyor. Dusuk karbonda ferrit+ostenit birlikte; karbon arttikca ostenit kararlanip karbur buyuyor ve M23C6'dan M7C3'e -- yani H1'in TERSI sirada -- gecmeli. Iki vaka birlikte, sıranın ezberlenmis bir cevap olmadigini gosteriyor.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `BCC_A2`, `FCC_A1`, `M23C6`, `M7C3`
- Eksen boyunca `M23C6` **`M7C3`'den önce** görünmeli.
- Eksenin başında: `BCC_A2`, `FCC_A1`
- Eksenin sonunda: `FCC_A1`, `M7C3`
- İstenen eksen aralığının **iki ucu da** sonuçta olmalı.
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## H3 · H3_krom_taramasi_1400K
*zorluk: orta*

**Soru**
```
steel1.TDB'de 1400 K'de Fe-%20Cr-%1C alasiminda kromu %1'den %30'a cikarirsam hangi fazlar cikar
```

**Neyi sınıyor**
H1 ile ayni tarama, 300 K daha sicak. Ostenit cok daha gec birakiyor (1100 K'de ~%11'de, 1400 K'de ~%14'te) ve arada genis bir iki-fazli bolge var. Ayni sorunun sicakliga duyarli oldugunu sinar -- tek bir taramaya bakip 'krom ferrit yapar' demek yeterli degil.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `FCC_A1`, `BCC_A2`, `M23C6`
- Eksen boyunca `FCC_A1` **`BCC_A2`'den önce** görünmeli.
- Eksenin başında: `FCC_A1`
- Eksenin sonunda: `BCC_A2`, `M23C6`
- İstenen eksen aralığının **iki ucu da** sonuçta olmalı.
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


## H4 · H4_molibden_taramasi
*zorluk: zor*

**Soru**
```
steel1.TDB'de 1100 K'de Fe-%10Cr-%3C alasimina molibden eklersem, %15'e kadar, hangi fazlar cikar
```

**Neyi sınıyor**
Tek taramada dort ayri rejim: M7C3, M23C6, M6C ve Laves fazi. Molibden kendi karburunu (M6C) yapar ve yeterince artinca Fe2Mo Laves fazi cikar. Dort elementli sistem, uc farkli karbur -- bu sunucunun en kalabalik kesiti.

**Beklenen cevap**
- Şu faz(lar) sonuçta bulunmalı: `M7C3`, `M23C6`, `M6C`, `LAVES_PHASE`, `BCC_A2`
- Eksen boyunca `M23C6` **`M6C`'den önce** görünmeli.
- Eksen boyunca `M6C` **`LAVES_PHASE`'den önce** görünmeli.
- Eksenin başında: `FCC_A1`, `M7C3`
- Eksenin sonunda: `BCC_A2`, `M6C`, `LAVES_PHASE`
- İstenen eksen aralığının **iki ucu da** sonuçta olmalı.
- Çözülemeyen nokta oranı %10'i geçmemeli.
- Faz miktarları **1'e toplamalı**.


---

# I · Katılaşma (Scheil-Gulliver)

*3 soru — kolay 0, orta 1, zor 2*


## I1 · I1_cost507R_katilasma
*zorluk: orta*

**Soru**
```
cost507R.TDB'de Al-%2Mg-%3Si-%2Zn alasimini 1000 K'den sogutursam katilasma sirasinda segregasyon nasil olur
```

**Neyi sınıyor**
Al-Mg-Si-Zn dokum alasimi. Katilasma sonuna kadar gidiyor ve son sivi %73 cinko -- nominal %2'den otuz kat fazla. Dagitimin kendi ornek makrosu da 'son sivi %70 Zn' diyor, yani bu sayi motorun kendi belgesiyle bagimsiz olarak dogrulanabiliyor.

**Beklenen cevap**
- Katılaşma **sonuna kadar gitmeli** (`completed: true`).
- Sonda kalan sıvı **2.0%'i geçmemeli**.
- Katılaşma sırasında şu faz(lar) oluşmalı: `FCC_A1`, `MG2SI`
- **Segregasyon:** son sıvıda `ZN` nominal 0.02 değerinin üzerine çıkmalı, en az 0.5. Scheil'in ölçtüğü şey bu.
- Sıvı çizgisi (liquidus) bulunmalı.


## I2 · I2_steel1_katilasma_eksik
*zorluk: zor*

**Soru**
```
steel1.TDB'de Fe-%1C celigini 1900 K'den sogutursam katilasma sirasinda karbon nasil dagilir
```

**Neyi sınıyor**
Fe-%1C. Karbon son siviya suruluyor (%1 -> %17) ama katilasma sonuna kadar gitmiyor: cozucu, sivi asirilastikca yakinsamayi birakiyor. Bu vakanin gecme olcutu hesabin tamamlanmasi DEGIL, tamamlanmadigini soylemesi.

**Beklenen cevap**
- Katılaşma bu sistemde sonuna kadar **gitmiyor** — ve ölçüt bunu düzeltmek değil, **doğru söylemek**: `completed: false` dönmeli, kalan sıvı oranı raporlanmalı. Yarım kalmış bir eğriyi tam gibi sunmak bu vakayı düşürür.
- Katılaşma sırasında şu faz(lar) oluşmalı: `BCC_A2`
- **Segregasyon:** son sıvıda `C` nominal 0.01 değerinin üzerine çıkmalı, en az 0.05. Scheil'in ölçtüğü şey bu.
- Sıvı çizgisi (liquidus) bulunmalı.


## I3 · I3_agcu_otektige_yakin
*zorluk: zor*

**Soru**
```
agcu.TDB'de Ag-%20Cu lehimini 1300 K'den sogutursam katilasma nasil ilerler
```

**Neyi sınıyor**
Ag-%20Cu, otektik bilesime yakin. Sivi dogrudan degismez noktaya iniyor -- Scheil icin en zor durum, ve motor %13 sivi kalmisken duruyor. Bakir 0.20'den 0.82'ye zenginlesiyor. I1 ile birlikte: ayni arac hem tamamlanan hem yarim kalan durumu dogru raporlamali.

**Beklenen cevap**
- Katılaşma bu sistemde sonuna kadar **gitmiyor** — ve ölçüt bunu düzeltmek değil, **doğru söylemek**: `completed: false` dönmeli, kalan sıvı oranı raporlanmalı. Yarım kalmış bir eğriyi tam gibi sunmak bu vakayı düşürür.
- Katılaşma sırasında şu faz(lar) oluşmalı: `FCC_A1`
- **Segregasyon:** son sıvıda `CU` nominal 0.2 değerinin üzerine çıkmalı, en az 0.6. Scheil'in ölçtüğü şey bu.
- Sıvı çizgisi (liquidus) bulunmalı.


---

# J · Faz diyagramı (iki eksen, MAP)

*3 soru — kolay 0, orta 1, zor 2*


## J1 · J1_agcu_faz_diyagrami
*zorluk: orta*

**Soru**
```
agcu.TDB icin Ag-Cu faz diyagramini ciz
```

**Neyi sınıyor**
Ag-Cu, klasik otektik diyagram. Tek bir degismez tepkime olmali ~1056 K'de. Bagimsiz kontrol: tek nokta hesaplarinda 1055 K'de sistem tamamen kati, 1060 K'de %99 sivi -- otektik ikisinin arasinda. Ayrica karismazlik boslugunun iki yarisi (FCC_A1 ve FCC_A1_AUTO#2) ayri gorunmeli.

Tohum sicakligi ozellikle veriliyor ve olcumun bir parcasi: MAP tohumdan disari dogru izler. 1000 K iki kati fazin bolgesinde, oradan baslayinca karismazlik boslugu da bulunuyor. Varsayilan orta nokta (1150 K) tek fazli sivida kaliyor ve diyagram daha az sinir iceriyor -- ayni sistem, ayni arac, farkli baslangic, farkli kapsam. Kaydediliyor cunku kullanicinin bilmesi gereken bir davranis.

**Beklenen cevap**
- Diyagramda şu faz(lar) görünmeli: `LIQUID`, `FCC_A1`, `FCC_A1_AUTO#2`
- **1056.1 K** civarında (± 2 K) bir değişmez tepkime bulunmalı — ötektik, ötektoid ya da peritektik.
- En az **4 faz sınırı** izlenmeli.
- Her sınır **en az iki fazlı** olmalı — tanım gereği bir sınır, fazların buluştuğu yerdir.


## J2 · J2_steel1_fe_c_diyagrami
*zorluk: zor*

**Soru**
```
steel1.TDB icin Fe-C faz diyagramini %0-25 karbon, 500-2000 K araliginda ciz
```

**Neyi sınıyor**
Fe-C, kararli (grafit) sistem. UC degismez tepkime birden: peritektik ~1768 K, otektik ~1427 K, otektoid ~1011 K. Ucu de ders kitabi degeri, ve otektoid bu projede ayri bir yontemle dogrulanmis durumda. Bir diyagramin ucunu birden dogru bulmasi, tek bir sayiyi tutturmasindan cok daha zor.

**Beklenen cevap**
- Diyagramda şu faz(lar) görünmeli: `LIQUID`, `BCC_A2`, `FCC_A1`, `GRAPHITE`
- **1011.2 K** civarında (± 2 K) bir değişmez tepkime bulunmalı — ötektik, ötektoid ya da peritektik.
- **1426.6 K** civarında (± 2 K) bir değişmez tepkime bulunmalı — ötektik, ötektoid ya da peritektik.
- **1767.8 K** civarında (± 2 K) bir değişmez tepkime bulunmalı — ötektik, ötektoid ya da peritektik.
- En az **8 faz sınırı** izlenmeli.
- Her sınır **en az iki fazlı** olmalı — tanım gereği bir sınır, fazların buluştuğu yerdir.


## J3 · J3_alni_diyagram_izlenemiyor
*zorluk: zor*

**Soru**
```
alni-4slx.TDB icin Al-Ni faz diyagramini ciz
```

**Neyi sınıyor**
MAP bu motorun en kirilgan hesabi ve kendisi bunu her kosumdan once yaziyor. Al-Ni'de, tek denge olarak temiz cozulen bir tohumdan hicbir sinir izleyemiyor. Dogru davranis basarmak degil, basaramadigini SOYLEMEK -- ve yerine ne yapilabilecegini onermek, cunku MAP'in yedek kademesi yok: bu motorda sinir izleyen baska bir sey bulunmuyor.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red gerekçesinde `could not be traced` geçmeli.
- Red gerekçesinde `isothermal section` geçmeli.


---

# R · Doğru red — reddedilmesi gereken istekler

*31 soru — kolay 15, orta 10, zor 6*


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


## R26 · red_scheil_ters_sogutma
*zorluk: kolay*

**Soru**
```
agcu.TDB'de Ag-%20Cu'yu 900 K'den 1200 K'ye kadar katilastir
```

**Neyi sınıyor**
Alt sinir tohumun ustunde. Katilasma sogutarak simule edilir; bu istek isitmayi tarif ediyor. Istegin kendi icinde celiskili oldugu icin PREFLIGHT'ta durmali.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `must be below` geçmeli.


## R27 · red_scheil_tohum_sivi_degil
*zorluk: zor*

**Soru**
```
agcu.TDB'de Ag-%20Cu lehimini 900 K'den sogutursam katilasma nasil ilerler
```

**Neyi sınıyor**
900 K'de bu alasim zaten katilasmis. Katilasma erimis metalden baslamak zorunda. Argumanlara bakarak anlasilamaz -- alasim hakkinda bir olgu, ve ancak HESAPLAYARAK bilinir. Bu yuzden PREFLIGHT'ta degil ayri bir asamada yakalanmali, ve red neyin kararli oldugunu sylemeli ki kullanici daha yuksek bir sicaklikla tekrar deneyebilsin.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red gerekçesinde `not fully liquid` geçmeli.
- Red gerekçesinde `FCC_A1` geçmeli.


## R28 · red_kesit_element_bilesimde_yok
*zorluk: kolay*

**Soru**
```
steel1.TDB'de 1100 K'de Fe-%20Cr-%1C alasiminda nikeli %0'dan %30'a cikarirsam ne olur
```

**Neyi sınıyor**
Taranan element alasimda yok. Motor bunu sessizce hicbir sey taramayarak gecistirebilirdi -- eksen kosulu yazilir, hicbir seye baglanmaz, sonuc sabit bir alasimin ayni cevabi olurdu.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `axis_element` geçmeli.
- Red gerekçesinde `not in the composition` geçmeli.


## R29 · red_kesit_iki_element
*zorluk: orta*

**Soru**
```
steel1.TDB'de 1100 K'de Fe-C alasiminda karbonu %0'dan %5'e cikarirsam ne olur
```

**Neyi sınıyor**
Iki elementli sistemde bir elementi taramak, geriye makronun bagimli birakacagi tek elementi birakir -- yani sistem asiri kisitlanir. Kulaga tamamen makul gelen bir istek ('Fe-C'de karbonu tara') sistemin yapisi geregi yapilamiyor; reddin gerekcesi bunu soylemeli.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `at least three elements` geçmeli.


## R30 · red_kesit_ters_eksen
*zorluk: kolay*

**Soru**
```
steel1.TDB'de 1100 K'de kromu %30'dan %1'e dusurursem
```

**Neyi sınıyor**
axis_min >= axis_max. R10'un (ters sicaklik araligi) bilesim eksenindeki karsiligi -- ayni hata sinifinin yeni eksende de yakalandigini sinar.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `axis_min` geçmeli.
- Red gerekçesinde `less than` geçmeli.


## R31 · red_kesit_bagimli_elemente_yer_yok
*zorluk: zor*

**Soru**
```
steel1.TDB'de 1100 K'de Fe-%30Cr-%20C alasiminda kromu %85'e kadar cikar
```

**Neyi sınıyor**
Eksenin ucu tek basina gecerli (%85 < 1) ve degerlerin hicbiri araligin disinda degil -- ama sabit kalan diger elementler zaten %20'yi tutuyor, yani ucta bagimli elemente eksi miktar dusuyor. Hicbir alanin tek basina hatali olmadigi, sadece BIRLIKTE imkansiz oldugu bir istek: her alani ayri ayri denetleyen bir kontrol bunu kacirir.

**Beklenen cevap**
- **Hesap yapılmamalı.** İstek reddedilmeli.
- Red, motor çalışmadan önce (PREFLIGHT) olmalı.
- Red gerekçesinde `dependent element` geçmeli.


---

**Toplam: 86 soru.**

