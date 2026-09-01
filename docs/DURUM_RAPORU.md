# Durum raporu

*2026-09-01*

---

## Kısaca

Derleyiciye geçmeden önce **derlenecek şeyi düzenli hale getirdim**: koda
dağılmış kurallar `input` / `execution` / `output` olarak ayrılıp ayar
katmanına taşındı, ve her adımda mevcut davranışın değişmediği testlerle
doğrulandı.

Bu aşama tamamlandı. Şimdi derleyici kısmındayım: ayar dosyaları açılışta
bir kez denetlenip hazır bir yürütme planına çevriliyor.

Arada bir engel var ve ilerlemeyi yavaşlatıyor: **dış model sağlayıcısının
aşırı yük (overloaded) sorunu.** Bu, ölçüm yapmayı zorlaştırdığı için
bazı doğrulamalar bekliyor. Aşağıda ölçümüyle birlikte anlatılıyor.

---

## 1 · Aşırı yük sorunu

Sistemde iki doğrulama katmanı var. **Katman A** deterministik, kendi
kodumuz, her zaman çalışıyor. **Katman B** dışarıdan bağımsız bir dil
modeline sonucu inceletiyor ve NVIDIA'nın barındırdığı bir modele HTTP ile
bağlanıyor.

Sorun Katman B'de. Ölçüm:

```
nvidia/nemotron-3-ultra-550b-a55b     000    60.0s   asili kaldi   (3 deneme, 3'u de)
nvidia/nemotron-3-super-120b-a12b     503     0.5s   "Service temporarily overloaded"
nvidia/nemotron-3-super-120b-a12b     200     3.1s   ayni anahtar, 2 saniye sonra
```

Aynı API anahtarı, aynı ağ, saniyeler arayla. Anahtar geçerli, ağ sağlam,
model sağlayıcının kataloğunda kayıtlı. **Yalnızca servis cevap vermiyor.**

### Bizim kodumuz olmadığı nasıl doğrulandı

Şüphe, sunucumuzun her isteğe eklediği sekiz araç şemasının modeli
boğmasıydı. Projeden tamamen bağımsız, düz HTTP ile test edildi:

```
TEST                        HTTP    SURE    ISTEK BOYU
ultra-550b  duz sohbet      000    90.3s      118 bayt   asili kaldi
ultra-550b  8 ARAC SEMALI   000    90.3s    6.651 bayt   asili kaldi
super-120b  duz sohbet      503     0.5s      118 bayt   overloaded
super-120b  8 ARAC SEMALI   200     2.1s    6.651 bayt   arac cagrisi uretti
```

118 baytlık bir *"merhaba"* bile 90 saniye asılı kalıyor. Araç şemalarının
hiçbir etkisi yok — ve aynı şemalar küçük modelde 2 saniyede düzgün bir
araç çağrısı üretiyor. Yani şemalarımız geçerli, sorun sağlayıcıda.

### İki farklı davranış

```
super-120b   yuk altinda 503 donuyor    hizli, durust hata
ultra-550b   hic donmuyor               90 saniye tutup birakiyor
```

Büyük model yük altında cevap yerine bağlantıyı askıda bırakıyor. İstemci
tarafında bu ya *"AI service is temporarily overloaded"* ya da sessizce
*"run aborted"* olarak görünüyor — ikisi aynı arızanın iki yüzü.

### Ölçüme etkisi

Kıyaslama koşumlarında Katman B'nin ulaşılabilirliği:

```
kosum 1    BASARILI 19  ·  BASARISIZ 6  ·  ULASILAMADI 25
```

Denenen 50 incelemenin **yarısı** sağlayıcıya hiç ulaşamadı.

Bu, sonuçların geçerliliğini bozmuyor — geçme ölçütleri Katman B'nin
kararına dayanmıyor, çünkü ulaşılamayan bir hakem kimya hakkında hiçbir şey
söylemez, ve sistem bunu *"onaylanmadı"* değil *"ulaşılamadı"* diye
kaydediyor. Ama iki pratik sonucu var:

**Koşumlar uzuyor.** Her vaka hakemi beklediği için tam kıyaslama 20
dakika yerine saatlere çıkabiliyor.

**Elle ölçüm duruyor.** Sistemin davranışını gerçek sorularla ölçen 200
soruluk havuz, istemci modelin ayakta olmasını gerektiriyor. Model
cevap vermediğinde soru sorulamıyor, dolayısıyla o ölçümler bekliyor.

### Bir yan bulgu

İstemci tarafında model kimliği **çift önekle** gönderiliyordu
(`nvidia/nvidia/nemotron-...`). Ölçüldü:

```
nvidia/nemotron-3-ultra-550b-a55b          200   calisiyor
nvidia/nvidia/nemotron-3-ultra-550b-a55b   404   "page not found"
```

Ayar dosyası (`openclaw.json`) sonradan açılıp kontrol edildi: içindeki
kimlik **tek önekli ve geçerli**. Yani düzeltilecek bir şey yoktu, ve
alınan `404`'ün sebebi henüz belirlenmedi. Ekrandaki çift önek büyük
ihtimalle sağlayıcı adı ile model kimliğinin yan yana basılması.

### Sonuç

Aşırı yük **bizim kodumuzda değil, dış sağlayıcıda** ve düzeltebileceğimiz
bir şey değil. Sistem buna karşı zaten doğru davranıyor: hakem
ulaşılamadığında hesap normal dönüyor ve durum ayrıca kaydediliyor.

Etkisi ölçümün *hızında*, sonucun *doğruluğunda* değil.

---

## 2 · Tamamlanan: kuralların ayrılması

Kurallar koda gömülüydü. Üçe ayrılıp ayar katmanına taşındı ve her birinin
tek cümlelik bir değişmezi var:

```
input.toml       hangi fizik problemi        cevabi DEGISTIREBILIR
execution.toml   nasil, hangi kademeyle      cevabi degistiremez,
                                             ulasilirligi degistirir
output.toml      sonuc nasil toparlanacak    sayilara DOKUNAMAZ
```

Bu ayrım işe yaradı: `stop_rule` bölümünün yanlış dosyada olduğu, `output`
dosyasının *"sayıya dokunamaz"* değişmezine uymadığı için fark edildi —
üç anahtarı da motor çalışmadan önce devreye giriyor ve başka bir hesabın
koşup koşmayacağına karar veriyor, ki bu giriş tarafının riski. Taşınması
bir sonraki turda.

`code` işaretli üç bölüm için bir düzeltme: bunlardan `signals` ve
`policy`'nin dayandığı `_ENGINE_FAILURES` aslında bir **metin listesi** ve
taşınabilir. Gerçekten kodda kalması gereken, Python'un kendi hata
sınıflarına bakan `isinstance` bloğu — o alt sınıfları da yakalıyor ve
metinle eşleştirmek zayıflatır.

**Sayılarla:**

```
21 ayar bolumu       15'i bagli
                      3'u `code` isaretli
                      3'u kalan gercek is  (report, honesty, floor)
preflight.py         351 -> 139 satir, sifir kural
```

Her adımda mevcut davranışın değişmediği doğrulandı: **550 istekli fark
testi**, eski uygulamaya karşı, reddetme davranışı birebir aynı.

---

## 3 · Şu an: derleyici

Ayarlar her istekte tek tek okunuyordu. Bu bir kural motoru, derleyici
değil — ve sessizce bozuluyor. Ölçüldü:

```
saglam dosya                 tek elementli istek -> 1 sikayet
check adinda tek harf hata   YUKLEME HATASI YOK
                             ayni istek -> 0 sikayet
```

Bir harflik yazım hatası kuralı **sessizce siliyordu**.

Derleme aşaması eklendi: üç dosya açılışta bir kez çözülüp doğrulanıyor,
her ad bağlandığı şeye bağlanıyor, ve çalışma anı yalnızca hazır planı
okuyor. Sertlik iki kademeli — bir kuralın sessizce çalışmamasına yol açan
şey sunucuyu **açtırmıyor**, kalanı uyarı olarak yazılıyor.

Aynı iki bozma denemesi tekrarlandı, ikisinde de sunucu açılmadı:

```
check = "min_nonzero_kount"     SettingsError: diye bir yuklem yok
applies = "isothermal_sektion"  SettingsError: diye bir islem yok
```

Derlemenin ortaya çıkardıkları da kapatıldı: dosyada tanımlı olup hiç
üretilmeyen üç not, kodda 13 kopyası bulunan bir varsayılan, iki yerde
tekrar eden bir hakem listesi, ve dört ölü sabit.

---

## 4 · Şu anki durum

```
kurallarin ayrilmasi     tamamlandi
derleme asamasi          tamamlandi
giris/cikis birim ayrimi tamamlandi
fark testi               550 istek, davranis birebir ayni
kiyaslama                86/86        (kolay 30/30 · orta 35/35 · zor 21/21)
```

Kıyaslama koşumu iki kez yeniden başlatıldı, çünkü ikisinde de bu turda
yapılmış bir hata çıktı ve ikisi de yalnızca uçtan uca koşumda göründü:

```
1  arac kaydi     yardimci fonksiyonlar dekorator ile fonksiyon arasina
                  girmis, calculate_equilibrium MCP'ye kaydolmamisti
2  cozumleme      baz donusumu PREFLIGHT'tan ONCE kosuyordu; normalize
   sirasi         edilen bilesim, olcek kuralina gorunmeden geciyordu
```

İkisi de söz dizimi denetiminden, ayar denetiminden ve 550 istekli fark
testinden geçmişti. Birincisi MCP protokolünü, ikincisi kural sırasını
gerektiriyordu. Düzeltildikten sonra koşum **86/86**.

Bu, kıyaslamanın neden ayrı bir katman olduğunun ölçülmüş örneği: statik
kontroller ve birim testleri sistemin çalıştığını göstermiyor.
