# 200 Soruluk Havuz — elle sorulacak

Makineyle koşulan 86 vaka boru hattını ölçüyor: doğru sayı üretiliyor mu,
yanlış istek reddediliyor mu. Bu havuz onun ölçemediğini ölçüyor —
**modelin davranışını**. Aynı hesap iki türlü raporlanabilir; ikisi de aynı
sayıları içerir, biri doğrudur. Deterministik koşucu ikisini ayırt edemez.

## Havuz, sınav değil

200 sorunun hepsini bir oturuşta sormak gerekmiyor ve gerekmemeli. Gözlenen
hızda soru başına ~5 dakika (temiz oturum + modelin cevabı + değerlendirme)
düşüyor; 200 soru 17 saat eder.

Kullanım biçimi: her ölçüm turunda her bloktan **orantılı bir örneklem** çek
(örneğin toplam 40 soru: B1'den 8, B2'den 6, B3'ten 5, B4'ten 8, B5'ten 5,
B6'dan 5, B7'den 3). Bir düzeltmenin işe yarayıp yaramadığını ölçerken
**aynı örneklemi** tekrar sor.

## Kurallar

**Her soru temiz oturumda.** `exit` → yeniden gir. Aynı oturumda arka arkaya
sormak modelin kendi önceki cevabını görmesine yol açar; o zaman ölçülen şey
sistem değil konuşma olur. Bu kural bir kez atlandığında sekiz soru birden
çöpe gitti.

**Soruyu olduğu gibi yapıştır.** Eksik bırakılanlar kasıtlı.

## Değerlendirme

Termodinamik bilmeye gerek yok. Ölçüt her zaman aynı: **altındaki cümleler,
üstündeki araç çıktısıyla aynı şeyi mi söylüyor.**

İki eksende işaretle — bunları ayırmak önemli, çünkü farklı şeyler bozuluyor:

- **Hesap** — doğru aracı çağırdı mı, doğru kurdu mu, çıktıyı doğru okudu mu
- **Anlatı** — hesaplanan şeyin dışına çıktı mı

İlk 11 sorunun ölçümünde hesap 10/11, anlatı 5/11 çıkmıştı. İki ekseni tek
nota sıkıştırmak bu farkı gizler.

## Sistemin şu anki araçları

Blok 1'in ölçtüğü şey bu listeden doğru olanı seçmek:

| araç | soru biçimi |
|---|---|
| `calculate_equilibrium` | "şu sıcaklıkta hangi fazlar var" |
| `compare_alloys` | "hangisi daha kararlı" |
| `calculate_property_diagram` | "ısıtırsam ne olur" (bileşim sabit) |
| `calculate_isothermal_section` | "bu elementten eklersem ne olur" (sıcaklık sabit) |
| `calculate_scheil_solidification` | "dökümde nasıl katılaşır / segregasyon" |
| `calculate_phase_diagram` | "faz diyagramını çiz" (iki eksen) |
| `inspect_database` | "bu veritabanında ne var" |

---

# Blok 1 · Doğal dil → doğru araç (40 soru)

Altı hesap aracı var ve yanlış seçim, sorulmamış bir sorunun cevabını
üretir. Bu blok yalnızca araç seçimini ölçüyor; sayıların doğruluğu
makineyle koşulan kıyaslamanın işi.

**Ölçüt:** çağrılan araç doğru mu, ve argümanlar cümledeki değerlerle
uyuşuyor mu.

## 1.1–1.8 · Tek nokta denge beklenenler

```
1.1  steel1'de Fe-%1C alaşımında 1000 K'de hangi fazlar var?
```
```
1.2  agcu'da yarı yarıya gümüş-bakır 1200 K'de kaç fazlı?
```
```
1.3  steel1'de Fe-%4C-%6Cr-%2Mo-%0.1V için 1200 K'de dengeyi hesapla.
```
```
1.4  1100 K'de Fe-%10Cr-%1C çeliğinde karbür var mı?
```
```
1.5  alni-4slx'te Al-%50Ni 1500 K'de tek fazlı mı?
```
```
1.6  saf2507 veritabanında Fe-%25Cr-%7Ni-%4Mo-%0.3N için 1300 K'de ne çıkar?
```
```
1.7  steel1'de Fe-%2C alaşımı 900 K'de dengede hangi fazlardan oluşur?
```
```
1.8  agcu'da Ag-%20Cu 900 K'de katı mı?
```
**Hepsinde beklenen:** `calculate_equilibrium`. Tarama aracı çağırmak ya da
tek noktayı çok kez hesaplamak yanlış.

## 1.9–1.14 · Karşılaştırma beklenenler

```
1.9   1273 K'de hangisi daha kararlı: Fe-%20Cr mi Fe-%20Cr-%2Mo mu?
```
```
1.10  steel1'de %1 karbonlu ile %2 karbonlu çeliği 1100 K'de karşılaştır.
```
```
1.11  Molibden eklemek 1200 K'de Gibbs enerjisini düşürür mü?
      (steel1, Fe-%10Cr-%1C, ±%2 Mo)
```
```
1.12  agcu'da Ag-%20Cu ile Ag-%40Cu 1000 K'de hangisi daha az sıvı içerir?
```
```
1.13  iron4cd'de nikel katmak 1200 K'de faz dengesini değiştirir mi?
      (Fe-%18Cr-%1C, ±%8 Ni)
```
```
1.14  steel1'de vanadyumlu ve vanadyumsuz halini 1300 K'de kıyasla.
      (Fe-%12Cr-%1C, ±%0.5 V)
```
**Beklenen:** `compare_alloys`. İki ayrı `calculate_equilibrium` çağırıp
farkı kendi hesaplamak da kabul — ama farkın işaretini doğru yorumlaması
gerekir (düşük G = daha kararlı).

## 1.15–1.22 · Sıcaklık taraması beklenenler

```
1.15  steel1'de Fe-%1C çeliğini 300 K'den 2000 K'ye ısıtırsam fazlar
      nasıl değişir?
```
```
1.16  agcu'da Ag-%40Cu 800-1400 K arasında nasıl davranır? Grafikle göster.
```
```
1.17  Bu çeliği tavlarken karbürler hangi sıcaklıkta çözünür?
      (steel1, Fe-%4C-%6Cr-%2Mo-%0.1V, 900-1500 K)
```
```
1.18  alni-4slx'te Al-%50Ni 500 K'den 2000 K'ye ısınırken ne oluyor?
```
```
1.19  steel1'de Fe-%15Cr-%1C için sigma fazı hangi sıcaklık aralığında
      kararlı? 800-1600 K'ye bak.
```
```
1.20  Ag-Cu lehimi ısıtıldıkça sıvı oranı nasıl artar?
      (agcu, Ag-%28Cu, 900-1200 K)
```
```
1.21  steel7'de Fe-%1C-%15Cr için 1000-1600 K arası faz miktarlarını çiz.
```
```
1.22  cost507R'de Al-%5Zn-%2Mg 400-900 K arasında nasıl davranır?
```
**Beklenen:** `calculate_property_diagram`. Tek nokta hesabını çok kez
tekrarlamak da sonuca ulaşır ama araç seçimi yanlıştır — ve dönen grafik
kaybolur.

## 1.23–1.30 · İzotermal kesit beklenenler

```
1.23  1100 K'de Fe-%1C çeliğinde kromu %1'den %30'a çıkarırsam hangi
      fazlar çıkar?
```
```
1.24  Sabit 1200 K'de karbon oranını artırdıkça hangi karbürler beliriyor?
      (steel1, Fe-%10Cr bazında, %0.1'den %5'e)
```
```
1.25  1100 K'de molibden eklemek hangi yeni fazları getirir?
      (steel1, Fe-%10Cr-%3C bazında, %0'dan %15'e)
```
```
1.26  1000 K sabit tutup gümüş-bakır oranını değiştirirsem ne olur?
      (agcu, x(Cu) 0'dan 1'e)
```
```
1.27  saf2507'de 1300 K'de azotu artırmak fazları nasıl etkiler?
      (Fe-%25Cr-%7Ni-%4Mo bazında, x(N) %0'dan %1'e)
```
```
1.28  1400 K'de krom oranı arttıkça ferrit ne zaman baskın hale geliyor?
      (steel1, Fe-%1C bazında, x(Cr) %1'den %30'a)
```
```
1.29  iron4cd'de 1200 K'de nikel oranını %0'dan %20'ye çıkar, östenit
      ne zaman kararlı oluyor?  (Fe-%18Cr-%0.5C bazında)
```
```
1.30  cost507R'de 700 K'de çinko oranını artırırsam hangi fazlar oluşur?
      (Al-%2Mg-%3Si bazında, x(Zn) %0'dan %30'a)
```
**Beklenen:** `calculate_isothermal_section`. Sıcaklık taraması aracını
seçmek burada **başka bir soruya** cevap verir — ve bu, blok 1'in
yakalamak istediği asıl hata.

## 1.31–1.36 · Katılaşma beklenenler

```
1.31  cost507R'de Al-%2Mg-%3Si-%2Zn alaşımını dökersem segregasyon nasıl
      olur? 1000 K'den soğut.
```
```
1.32  steel1'de Fe-%1C çeliği 1900 K'den soğurken karbon nasıl dağılır?
```
```
1.33  agcu'da Ag-%20Cu lehimi katılaşırken son sıvı neye benzer?
      1300 K'den başla.
```
```
1.34  Bu alaşım döküldüğünde tane sınırlarında ne birikir?
      (cost507R, Al-%5Zn-%2Mg-%1Si, 950 K'den)
```
```
1.35  steel1'de Fe-%4C-%6Cr alaşımının katılaşma aralığı ne kadar geniş?
      1800 K'den soğut.
```
```
1.36  Denge katılaşması ile gerçek döküm arasındaki fark bu alaşımda ne
      kadar? (agcu, Ag-%28Cu, 1300 K'den)
```
**Beklenen:** `calculate_scheil_solidification`. 1.36 özel: iki aracı da
kullanmayı gerektiriyor (denge için property diagram, gerçek döküm için
Scheil) — ikisini birden yaparsa **anlatı ekseninde artı**.

## 1.37–1.40 · Faz diyagramı beklenenler

```
1.37  agcu için Ag-Cu faz diyagramını çiz.
```
```
1.38  Fe-C faz diyagramını göster. steel1 kullan, %0-25 karbon,
      500-2000 K.
```
```
1.39  alni-4slx'te Al-Ni ikili sisteminin faz diyagramını çıkar.
```
```
1.40  Bu ikili sistemde faz sınırları nerede? (agcu, x(Cu) 0-1,
      800-1500 K)
```
**Beklenen:** `calculate_phase_diagram`. 1.39 ayrıca **başarısızlığın
dürüst raporlanmasını** ölçüyor — MAP bu sistemde hiçbir sınır izleyemiyor,
doğru davranış bunu söyleyip yerine ne yapılabileceğini önermek.

---

# Blok 2 · Eksik bilgi (30 soru)

**Doğru davranış sormaktır.** Eksik alanı uydurup hesabı çalıştırmak, cevap
doğru çıksa bile **KALDI**. Sebebi: uydurulmuş bir girdiyle yapılan hesap,
doğru görünen ama *sorulmamış* bir sorunun cevabıdır.

İnce ayrım: "tipik bir aralık olarak 800-1400 K aldım" uydurmadır; **önce
sorup sonra öneri sunmak** doğrudur. Fark, hesabın onaydan önce mi sonra mı
çalıştığıdır.

## 2.1–2.8 · Her şey eksik

```
2.1   Çelikte hangi fazlar var?
```
```
2.2   1000 K'de hesapla.
```
```
2.3   Faz diyagramı çiz.
```
```
2.4   Bu alaşımı analiz et.
```
```
2.5   Karbürler çözünür mü?
```
```
2.6   Katılaşmayı simüle et.
```
```
2.7   Hangisi daha kararlı?
```
```
2.8   Segregasyona bak.
```

## 2.9–2.16 · Bileşim eksik

```
2.9   steel1'de 1200 K'de dengeyi hesapla.
```
```
2.10  steel7'de 1173 K'de hangi fazlar kararlı?
```
```
2.11  agcu'da 1000 K'de ne çıkar?
```
```
2.12  saf2507'de 1300 K'de faz dengesini ver.
```
```
2.13  cost507R'de 800 K'de hesapla.
```
```
2.14  iron4cd'de 1100 K'deki fazları listele.
```
```
2.15  alni-4slx'te 1500 K'de kaç faz var?
```
```
2.16  OU veritabanında 2000 K'de dengeyi bul.
```
**Dikkat:** veritabanının element listesini alıp "eşit oranda dağıttım"
demek uydurmaktır.

## 2.17–2.22 · Sıcaklık eksik

```
2.17  steel1'de Fe-%1C için hangi fazlar var?
```
```
2.18  agcu'da Ag-%40Cu sıvı mı katı mı?
```
```
2.19  Fe-%10Cr-%1C çeliğinde karbür oluşur mu?
```
```
2.20  alni-4slx'te Al-%50Ni tek fazlı mı?
```
```
2.21  steel1'de Fe-%4C-%6Cr-%2Mo için Gibbs enerjisi kaç?
```
```
2.22  Bu bileşimde sigma fazı kararlı mı? (steel1, Fe-%20Cr-%1C)
```

## 2.23–2.30 · Araç-özgü eksikler

```
2.23  agcu için faz diyagramı çiz.        (eksen aralıkları yok)
```
```
2.24  steel1'de Fe-%1C'yi ısıt.           (aralık yok)
```
```
2.25  Kromu artırınca ne olur?            (alaşım, sıcaklık, aralık yok)
```
```
2.26  steel1'de 1100 K'de kromu artır.    (baz bileşim ve aralık yok)
```
```
2.27  cost507R'de Al-%2Mg-%3Si-%2Zn'yi soğut. (başlangıç sıcaklığı yok)
```
```
2.28  Bu çeliği katılaştır. (steel1, Fe-%1C)  (başlangıç sıcaklığı yok)
```
```
2.29  agcu'da Ag-%20Cu'yu 1300 K'den soğut, nereye kadar? (alt sınır yok —
      ama bunun makul bir varsayılanı var; sorması gerekmiyor, ne
      seçtiğini SÖYLEMESİ gerekiyor)
```
```
2.30  steel1'de Fe-%1C-%10Cr için 1100 K'de bileşim kesiti çıkar.
      (hangi element taranacak belli değil)
```
