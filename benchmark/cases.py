"""Kiyaslama vaka kaydi: 100 vaka, uc kategori.

Her vaka IKI sekilde kosulabilecek bicimde yaziliyor:

  "arguments" ile  -> boru hattini olcer. Model yok, saglayici yok, hizli
                      ve belirlenimci. Bugun kosulabilir.
  "soru" ile       -> modeli olcer. O zaman "tool"+"arguments" artik
                      DOGRU CEVAP olur: model ayni cagriyi kurabildi mi?

Ayni dosya, iki kosucu. Hangi yolu secersen sec yazilan is bosa gitmez.

ZORLUK, cumlenin kulaga nasil geldigine gore degil, sistemin basina ne
geldigine gore. Bu ayrim onemli: kulaga en basit gelen soru sistem icin
en zoru olabiliyor ("saf demirin ergime sicakligi" uc kelime, ama motor
tek elementli bilesimi hesaplayamiyor).

  kolay : tek arac, belirsizlik yok, motor ilk denemede yakinsiyor
  orta  : sunlardan BIRI var -- once arama gerekiyor, motor kademe
          atliyor, faz gecisi var, ya da istek reddedilmeli
  zor   : sunlardan IKISI ya da fazlasi var -- motor kismen basarisiz,
          miscibility gap, eksik/yanlis onculu istek, sessiz hata tuzagi

KATEGORILER

  1 DOGRU_HESAP  (49)  dogru sayiyi uretiyor mu?      motor + Katman A
  2 DOGRU_RED    (29)  yapmamasi gerekeni reddediyor  PREFLIGHT
                       mu?
  3 DOGRU_RAPOR  ( 0)  gercekte ne oldugunu soyluyor  Katman A/B + anlati
                       mu?                            -- HENUZ YAZILMADI

Uc numaranin bos olmasi bir eksiklik ve oyle duruyor: 30 soruluk anlati
olcumu (dogal dil cevirisi, dolayli istek, eksik bilgi, yanlis oncul,
durust raporlama, ezber tuzagi, kapsam disi istek) elle sorulmasi
gerektigi icin bu dosyada degil. Sayiyi 30 yazip bos birakmak, olculmemis
bir seyi olculmus gostermek olurdu.

Uculu ayni zamanda "neyi nasil kosacagiz" ayrimini da veriyor: 1 ve 2
modelsiz kosulabilir, 3 kosulamaz -- anlatiyi olctugu icin bir modele
ihtiyaci var.

BEKLENEN ALANI

  rejected         True  -> hesap HIC yapilmamali. Bir sonuc donerse kalir.
  stage            beklenen asama etiketi ("PREFLIGHT"), ya da None
  reason_contains  redde mutlaka gecmesi gereken metin parcalari
  olcum            bu vakanin neyi olctugu -- rapora girer

Vaka eklerken: bir sayiyi "referans" diye yazmadan once onun nereden
geldigini bil. Sistemin kendi ciktisini kendine referans yapmak hicbir
sey olcmeyen bir test uretir.
"""

# PREFLIGHT'in gercekte uyguladigi sekiz kural (preflight.py'den okundu,
# tahmin degil):
#   R1  veritabani dosyasi yok
#   R2  element TDB'de tanimli degil
#   R3  ikiden az element
#   R4  askiya alinan faz TDB'de tanimli degil
#   R5  negatif bilesim miktari
#   R6  bilesim toplami <= 0
#   R7  bilesim toplami [0.5, 2.0] araligi disinda
#   R8  basinc <= 0
#   R9  sicaklik <= 0            (denge)
#   R10 T_min >= T_max           (diyagram)
#   R11 T_min ya da T_max <= 0   (diyagram)

DOGRU_RED = [

    # ---- KOLAY (12) -- tek, apacik hata --------------------------------

    {
        "id": "red_olmayan_dosya",
        "zorluk": "kolay",
        "kural": "R1",
        "olcum": "Var olmayan bir veritabani dosyasi motora gitmeden yakalaniyor mu",
        "soru": "olmayan_bir_dosya.TDB'de Fe=0.9 C=0.1 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "olmayan_bir_dosya.TDB",
            "elements_composition": {"FE": 0.9, "C": 0.1},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["Database not found"],
        },
    },
    {
        "id": "red_olmayan_element_ni",
        "zorluk": "kolay",
        "kural": "R2",
        "olcum": "steel1'de nikel yok; motor yine de bir sayi uretebiliyor "
                 "(saf demir icin), o yuzden red motordan ONCE olmali",
        "soru": "steel1.TDB'de Fe=0.9 Ni=0.1 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.9, "NI": 0.1},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "NI"],
        },
    },
    {
        "id": "red_tek_element_fe",
        "zorluk": "kolay",
        "kural": "R3",
        "olcum": "Tek elementli bilesim motorun kosul sistemini bozup "
                 "segfault'a goturuyordu; PREFLIGHT bunu temiz hataya cevirir",
        "soru": "steel1.TDB'de saf demir icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 1.0},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["At least two elements"],
        },
    },
    {
        "id": "red_negatif_sicaklik",
        "zorluk": "kolay",
        "kural": "R9",
        "olcum": "Kelvin negatif olamaz",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin -500 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": -500,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["Temperature must be positive"],
        },
    },
    {
        "id": "red_sifir_sicaklik",
        "zorluk": "kolay",
        "kural": "R9",
        "olcum": "Sinir degeri: 0 K de reddedilmeli, sadece negatif degil",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 0 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 0,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["Temperature must be positive"],
        },
    },
    {
        "id": "red_negatif_basinc",
        "zorluk": "kolay",
        "kural": "R8",
        "olcum": "Basinc pozitif olmali",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K, -100000 Pa'da hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "pressure_Pa": -100000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["Pressure must be positive"],
        },
    },
    {
        "id": "red_sifir_basinc",
        "zorluk": "kolay",
        "kural": "R8",
        "olcum": "Sinir degeri: 0 Pa da reddedilmeli",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K, 0 Pa'da hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "pressure_Pa": 0,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["Pressure must be positive"],
        },
    },
    {
        "id": "red_negatif_bilesim",
        "zorluk": "kolay",
        "kural": "R5",
        "olcum": "Negatif mol miktari; normalize edilirse sessizce anlamsiz "
                 "bir bilesime donusurdu",
        "soru": "steel1.TDB'de Fe=1.01 C=-0.01 icin 1000 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 1.01, "C": -0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["negative"],
        },
    },
    {
        "id": "red_ters_sicaklik_araligi",
        "zorluk": "kolay",
        "kural": "R10",
        "olcum": "Diyagramda alt sinir ust sinirdan buyuk",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 1500 K'den 800 K'e diyagram ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 1500,
            "temperature_max_K": 800,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["must be less than"],
        },
    },
    {
        "id": "red_agcu_graphite_askiya",
        "zorluk": "kolay",
        "kural": "R4",
        "olcum": "agcu'da GRAPHITE yok. Motor bu istegi SESSIZCE yutuyordu ve "
                 "kararli dengeyi donduruyordu -- istemci de grafitin "
                 "bastirildigini raporluyordu. Canli olarak gorulen vaka.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 1000 K'de GRAPHITE fazini "
                "kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "suspended_phases": ["GRAPHITE"],
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "GRAPHITE"],
        },
    },
    {
        "id": "red_bilesim_sifir",
        "zorluk": "kolay",
        "kural": "R6",
        "olcum": "Toplami sifir olan bilesim normalize edilemez (sifira bolme)",
        "soru": "steel1.TDB'de Fe=0 C=0 icin 1000 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.0, "C": 0.0},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["sum to zero"],
        },
    },
    {
        "id": "red_diyagram_negatif_tmin",
        "zorluk": "kolay",
        "kural": "R11",
        "olcum": "Diyagramin alt sinirinin kendisi gecersiz",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin -200 K'den 1400 K'e diyagram ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_min_K": -200,
            "temperature_max_K": 1400,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["temperature_min_K must be positive"],
        },
    },

    # ---- ORTA (9) -- hata var ama bakmak gerekiyor ----------------------

    {
        "id": "red_saf2507_karbon",
        "zorluk": "orta",
        "kural": "R2",
        "olcum": "Bir paslanmaz celik veritabaninda karbon istemek son derece "
                 "makul gorunur; saf2507 karbon icermez (Cr, Fe, Mn, Mo, N, Ni). "
                 "Istegin kendisi degil, hedefin icerigi karar veriyor.",
        "soru": "saf2507.TDB'de Fe=0.6 Cr=0.25 Ni=0.07 Mo=0.04 C=0.04 icin "
                "1200 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "saf2507.TDB",
            "elements_composition": {"FE": 0.6, "CR": 0.25, "NI": 0.07,
                                     "MO": 0.04, "C": 0.04},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "C"],
        },
    },
    {
        "id": "red_bef_demir",
        "zorluk": "orta",
        "kural": "R2",
        "olcum": "Isim tuzagi: BEF.TDB demir icermez (Mo, Ni, Re). Ismin "
                 "cagristirdigi seyle icerigi ayri.",
        "soru": "BEF.TDB'de Fe=0.7 Ni=0.3 icin 1400 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "BEF.TDB",
            "elements_composition": {"FE": 0.7, "NI": 0.3},
            "composition_basis": "mole_fraction",
            "temperature_K": 1400,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "FE"],
        },
    },
    {
        "id": "red_alni_bcc_a2_askiya",
        "zorluk": "orta",
        "kural": "R4",
        "olcum": "alni-4slx'te BCC_A2 yok -- 'A2' ve 'BCC4' var. Cok yaygin bir "
                 "faz adi baska bir veritabaninda baska yazilmis olabiliyor.",
        "soru": "alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 1200 K'de BCC_A2 fazini "
                "kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.5, "NI": 0.5},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
            "suspended_phases": ["BCC_A2"],
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "BCC_A2"],
        },
    },
    {
        "id": "red_alfe_fcc_a1_askiya",
        "zorluk": "orta",
        "kural": "R4",
        "olcum": "AlFe-4SLBF'de FCC_A1 degil 'A1_FCC' var -- ayni iki parca, "
                 "ters sirada. Yazim degil, siralama tuzagi.",
        "soru": "AlFe-4SLBF.TDB'de Al=0.2 Fe=0.8 icin 1000 K'de FCC_A1 fazini "
                "kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "AlFe-4SLBF.TDB",
            "elements_composition": {"AL": 0.2, "FE": 0.8},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "suspended_phases": ["FCC_A1"],
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "FCC_A1"],
        },
    },
    {
        "id": "red_austenite_askiya",
        "zorluk": "orta",
        "kural": "R4",
        "olcum": "'AUSTENITE' gercek bir metalurji terimi ama TDB'nin faz adi "
                 "degil (FCC_A1). Alan bilgisi ile veritabani sozlugunun ayrimi.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1200 K'de ostenit fazini "
                "kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
            "suspended_phases": ["AUSTENITE"],
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "AUSTENITE"],
        },
    },
    {
        "id": "red_bilesim_yuzde",
        "zorluk": "orta",
        "kural": "R7",
        "olcum": "Yuzde olarak yazilmis bilesim (toplam 100). Kod yorumu 'yine "
                 "de normalize edilir' diyor ama problems listesine girdigi "
                 "icin istek REDDEDILIYOR -- niyet ile davranis ayrisiyor.",
        "soru": "steel1.TDB'de %99 Fe ve %1 C icin 1000 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 99, "C": 1},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["sum to"],
        },
    },
    {
        "id": "red_bilesim_cok_kucuk",
        "zorluk": "orta",
        "kural": "R7",
        "olcum": "Toplam 0.1 -- olcek hatasinin ters yonu",
        "soru": "steel1.TDB'de Fe=0.099 C=0.001 icin 1000 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.099, "C": 0.001},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["sum to"],
        },
    },
    {
        "id": "red_mgnacl_potasyum",
        "zorluk": "orta",
        "kural": "R2",
        "olcum": "Ayni grup elementi (Na yerine K) -- kimyasal olarak yakin, "
                 "veritabani icin tamamen yabanci",
        "soru": "MgNaCl.TDB'de K=0.3 Cl=0.7 icin 1100 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "MgNaCl.TDB",
            "elements_composition": {"K": 0.3, "CL": 0.7},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "K"],
        },
    },
    {
        "id": "red_iki_hata_birden",
        "zorluk": "orta",
        "kural": "R2+R9",
        "olcum": "Iki bagimsiz hata ayni istekte. Ikisinin de raporlanmasi "
                 "gerekir -- ilkinde durup otekini gizlemek, kullaniciyi iki "
                 "tur dondurur (derleyicilerdeki hata kurtarma ilkesi).",
        "soru": "steel1.TDB'de Fe=0.9 Ni=0.1 icin -300 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.9, "NI": 0.1},
            "composition_basis": "mole_fraction",
            "temperature_K": -300,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared", "Temperature must be positive"],
        },
    },

    # ---- ZOR (4) -- gecerli gorunuyor ama degil -------------------------

    {
        "id": "red_ikinci_element_sifir",
        "zorluk": "zor",
        "kural": "R3 (bosluk)",
        "olcum": "BILINEN BOSLUK. PREFLIGHT 'en az iki element' derken sozluk "
                 "ANAHTARLARINI sayiyor, sifirdan farkli miktarlari degil -- "
                 "kendi hata metni 'nonzero amount' dese de. Bu istek "
                 "PREFLIGHT'tan GECER ve motor katmaninda reddedilir. "
                 "Beklenen: yine de hicbir sayi donmemesi, ama redde asamanin "
                 "PREFLIGHT olmamasi.",
        "soru": "steel1.TDB'de Fe=1.0 C=0.0 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 1.0, "C": 0.0},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": None,          # PREFLIGHT DEGIL -- olculecek olan bu
            "reason_contains": [],
        },
    },
    {
        "id": "red_bilesim_kumesi_ekli_faz",
        "zorluk": "zor",
        "kural": "R4",
        "olcum": "'GRAPHITE#1' -- '#1' bir calisma zamani bilesim kumesi eki, "
                 "TDB yalnizca taban adi bildirir. PREFLIGHT eki soyup taban "
                 "adi aramali; agcu'da GRAPHITE olmadigi icin yine reddetmeli.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 1000 K'de GRAPHITE#1 fazini "
                "kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "suspended_phases": ["GRAPHITE#1"],
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["not declared"],
        },
    },
    {
        "id": "red_diyagram_esit_sinir",
        "zorluk": "zor",
        "kural": "R10",
        "olcum": "T_min == T_max. Ters degil, esit -- '>' degil '>=' ile "
                 "kontrol edilmis olmasi gerekiyor. Sifir genislikte bir "
                 "tarama diyagram degildir.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 1000 K'den 1000 K'e diyagram ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 1000,
            "temperature_max_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["must be less than"],
        },
    },
    {
        "id": "red_olcek_sinirinin_hemen_disi",
        "zorluk": "zor",
        "kural": "R7",
        "olcum": "Toplam 2.5 -- kabul araligi [0.5, 2.0]'in hemen disi. Kasitli "
                 "bir olcek secimi gibi gorunur (iki mollik bir sistem?), ama "
                 "esik disinda. Esigin kendisinin bir TERCIH oldugunu, degismez "
                 "bir kural olmadigini gosteren vaka.",
        "soru": "steel1.TDB'de Fe=2.475 C=0.025 icin 1000 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 2.475, "C": 0.025},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["sum to"],
        },
    },

    # --- katilasma redleri --------------------------------------------
    # Scheil'in kendi on kosullari. Ikisi farkli asamada yakalaniyor ve bu
    # ayrim kasitli: birincisi istegin kendisinde bir celiski (asla dogru
    # olamaz), ikincisi alasim hakkinda bir olgu (baska sicaklikta dogru
    # olur). Ilki tekrar denenmemeli, ikincisi denenmeli.

    {
        "id": "red_scheil_ters_sogutma",
        "zorluk": "kolay",
        "kural": "eksen",
        "olcum": "Alt sinir tohumun ustunde. Katilasma sogutarak simule "
                 "edilir; bu istek isitmayi tarif ediyor. Istegin kendi "
                 "icinde celiskili oldugu icin PREFLIGHT'ta durmali.",
        "soru": "agcu.TDB'de Ag-%20Cu'yu 900 K'den 1200 K'ye kadar "
                "katilastir",
        "tool": "calculate_scheil_solidification",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.8, "CU": 0.2},
            "composition_basis": "mole_fraction",
            "seed_temperature_K": 900,
            "temperature_min_K": 1200,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["must be below"],
        },
    },
    {
        "id": "red_scheil_tohum_sivi_degil",
        "zorluk": "zor",
        "kural": "on kosul",
        "olcum": "900 K'de bu alasim zaten katilasmis. Katilasma erimis "
                 "metalden baslamak zorunda. Argumanlara bakarak "
                 "anlasilamaz -- alasim hakkinda bir olgu, ve ancak "
                 "HESAPLAYARAK bilinir. Bu yuzden PREFLIGHT'ta degil ayri "
                 "bir asamada yakalanmali, ve red neyin kararli oldugunu "
                 "sylemeli ki kullanici daha yuksek bir sicaklikla "
                 "tekrar deneyebilsin.",
        "soru": "agcu.TDB'de Ag-%20Cu lehimini 900 K'den sogutursam "
                "katilasma nasil ilerler",
        "tool": "calculate_scheil_solidification",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.8, "CU": 0.2},
            "composition_basis": "mole_fraction",
            "seed_temperature_K": 900,
        },
        "expected": {
            "rejected": True,
            "stage": "PRECONDITION",
            "reason_contains": ["not fully liquid", "FCC_A1"],
        },
    },

    # --- bilesim ekseni redleri --------------------------------------
    # Izotermal kesitin kendi kurallari. Ucu de motora hic gitmeden
    # yakalanabilir cinsten: taranan element bilesimde yoksa hicbir sey
    # taranmaz, iki elementli sistemde makronun dengeleyecek elementi
    # kalmaz, ve eksenin ucu bagimli elemente yer birakmiyorsa denklem
    # cozulemez. Ucu de "motor kesfetsin" yerine burada durdurulmali.

    {
        "id": "red_kesit_element_bilesimde_yok",
        "zorluk": "kolay",
        "kural": "eksen",
        "olcum": "Taranan element alasimda yok. Motor bunu sessizce hicbir "
                 "sey taramayarak gecistirebilirdi -- eksen kosulu yazilir, "
                 "hicbir seye baglanmaz, sonuc sabit bir alasimin ayni "
                 "cevabi olurdu.",
        "soru": "steel1.TDB'de 1100 K'de Fe-%20Cr-%1C alasiminda nikeli "
                "%0'dan %30'a cikarirsam ne olur",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "NI", "axis_min": 0.0, "axis_max": 0.30,
            "temperature_K": 1100,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["axis_element", "not in the composition"],
        },
    },
    {
        "id": "red_kesit_iki_element",
        "zorluk": "orta",
        "kural": "eksen",
        "olcum": "Iki elementli sistemde bir elementi taramak, geriye "
                 "makronun bagimli birakacagi tek elementi birakir -- yani "
                 "sistem asiri kisitlanir. Kulaga tamamen makul gelen bir "
                 "istek ('Fe-C'de karbonu tara') sistemin yapisi geregi "
                 "yapilamiyor; reddin gerekcesi bunu soylemeli.",
        "soru": "steel1.TDB'de 1100 K'de Fe-C alasiminda karbonu %0'dan "
                "%5'e cikarirsam ne olur",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "C", "axis_min": 0.0, "axis_max": 0.05,
            "temperature_K": 1100,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["at least three elements"],
        },
    },
    {
        "id": "red_kesit_ters_eksen",
        "zorluk": "kolay",
        "kural": "eksen",
        "olcum": "axis_min >= axis_max. R10'un (ters sicaklik araligi) "
                 "bilesim eksenindeki karsiligi -- ayni hata sinifinin yeni "
                 "eksende de yakalandigini sinar.",
        "soru": "steel1.TDB'de 1100 K'de kromu %30'dan %1'e dusurursem",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "CR", "axis_min": 0.30, "axis_max": 0.01,
            "temperature_K": 1100,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["axis_min", "less than"],
        },
    },
    {
        "id": "red_kesit_bagimli_elemente_yer_yok",
        "zorluk": "zor",
        "kural": "eksen",
        "olcum": "Eksenin ucu tek basina gecerli (%85 < 1) ve degerlerin "
                 "hicbiri araligin disinda degil -- ama sabit kalan diger "
                 "elementler zaten %20'yi tutuyor, yani ucta bagimli "
                 "elemente eksi miktar dusuyor. Hicbir alanin tek basina "
                 "hatali olmadigi, sadece BIRLIKTE imkansiz oldugu bir "
                 "istek: her alani ayri ayri denetleyen bir kontrol bunu "
                 "kacirir.",
        "soru": "steel1.TDB'de 1100 K'de Fe-%30Cr-%20C alasiminda kromu "
                "%85'e kadar cikar",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.5, "CR": 0.3, "C": 0.2},
            "composition_basis": "mole_fraction",
            "axis_element": "CR", "axis_min": 0.3, "axis_max": 0.85,
            "temperature_K": 1100,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["dependent element"],
        },
    },
]


# --- Kategori 1: DOGRU_HESAP -----------------------------------------
# Gruplar olgu turune gore, veritabani adina gore degil: bir okuyucu icin
# "karismazlik boslugu" anlamli bir sinif, "agcu.TDB" degil. Veritabanlari
# gruplara dagiliyor ve her vakanin kendi kaydinda yazili kaliyor.
#
# Gecme olcutleri referans degere DAYANMIYOR. Kutle korunumu sonucun kendi
# icinden, karbur stokiyometrisi formulden cikar -- ikisi de motorun kendi
# ciktisindan bagimsizdir, yani sistemin sayisini kendine referans yapma
# tuzagi yok. Referans deger yalnizca elde gercekten dogrulanmis bir sayi
# varsa yaziliyor (steel1 1000K ve 1200K).

A_TEK_FAZ = [
    # Sistem tek faz veriyor. O fazin bilesimi zorunlu olarak toplam
    # bilesimin aynisidir -- kutle korunumundan cikar, hesaptan degil. Bu
    # yuzden bu grup element kaybini SINAMAZ (bkz. B grubu); sinadigi sey
    # motorun dogru fazi secmesi ve sonucu bozmamasidir.

    {
        "id": "A1_alni_bcc4_1200K",
        "zorluk": "kolay",
        "olcum": "Al-Ni 50-50 bilesimi genis bir araligta tek fazli B2/BCC4 "
                 "olarak kararli. Motorun tek faz durumunu bozmadan dondurmesi.",
        "soru": "alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 1200 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.5, "NI": 0.5},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
        },
        "expected": {
            "phase_count": 1,
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "A2_alni_sivi_1950K",
        "zorluk": "kolay",
        "olcum": "Ayni bilesim erime noktasinin ustunde: tek fazli sivi. "
                 "A1 ile birlikte, ayni sistemin iki ucunu kapsiyor.",
        "soru": "alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 1950 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.5, "NI": 0.5},
            "composition_basis": "mole_fraction",
            "temperature_K": 1950,
        },
        "expected": {
            "phases": ["LIQUID"],
            "phase_count": 1,
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "A3_agcu_sivi_1200K",
        "zorluk": "kolay",
        "olcum": "Ag-Cu otektik sicakliginin (~1056 K) uzerinde tamamen sivi. "
                 "Ayni veritabani D grubunda karismazlik boslugu icin de "
                 "kullaniliyor; burada sadelestirilmis ucu.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 1200 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
        },
        "expected": {
            "phases": ["LIQUID"],
            "phase_count": 1,
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "A4_alfe_1000K",
        "zorluk": "kolay",
        "olcum": "Bu projede elle dogrulanmis bir referans deger. Dort alt "
                 "orgulu BCC modeli kullanan bir veritabani -- steel1'den "
                 "tamamen farkli bir model ailesi.",
        "soru": "AlFe-4SLBF.TDB'de Al=0.2 Fe=0.8 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "AlFe-4SLBF.TDB",
            "elements_composition": {"AL": 0.2, "FE": 0.8},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "gibbs_energy_J": {"value": -59870.5, "tolerance": 5.0},
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "A5_steel1_1200K_native",
        "zorluk": "orta",
        "olcum": "OCASI bu noktada hata 4204 ile yakinsamiyor; native motor "
                 "devraliyor. Kademeli motorun calistiginin en net kaniti, ve "
                 "referans degeri elle dogrulanmis.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1200 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
        },
        "expected": {
            "phases": ["FCC_A1"],
            "phase_count": 1,
            "gibbs_energy_J": {"value": -56563.789, "tolerance": 2.0},
            "backend_used": "native_oc",
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "A6_steel1_dort_element_tek_faz",
        "zorluk": "orta",
        "olcum": "Dort element, yine tek faz. Seyreltik V (0.001) sonucta "
                 "gorunuyor mu -- ama tek fazli oldugu icin bu bir kutle "
                 "korunumu ozdesligidir, olcum degildir. B grubundaki "
                 "cok fazli surumuyle bilincli olarak eslestirildi.",
        "soru": "steel1.TDB'de Fe=0.949 C=0.01 Cr=0.04 V=0.001 icin "
                "1100 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.949, "C": 0.01,
                                     "CR": 0.04, "V": 0.001},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "phases": ["FCC_A1"],
            "phase_count": 1,
            "mass_balance": True,
            "elements_present": True,
        },
    },
]
B_COK_FAZ = [
    # Asil grup. Elementler fazlar arasinda dagiliyor ve bu dagilim gercekten
    # HESAPLANMIS bir buyukluk -- girdiden cikarilamaz. Kutle korunumu burada
    # anlamli bir test haline geliyor: bir motor yanlis cozerse Sigma(faz
    # miktari x derisim) istenen miktara esit cikmaz.
    #
    # Karbur stokiyometrisi ikinci bagimsiz olcut: C orani formulden gelir,
    # motorun ciktisindan degil.
    #   M23C6 -> 6/29   M7C3 -> 3/10   M6C -> 1/7   MC -> 1/2

    # ---- KOLAY (3) -- iki element, iki faz, OCASI ilk denemede -----------

    {
        "id": "B1_steel1_FeC_1000K",
        "zorluk": "kolay",
        "olcum": "Projenin en cok dogrulanmis referans noktasi. Ferrit +/ "
                 "grafit dengesi; karbonun neredeyse tamami grafite gidiyor.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "phases": ["BCC_A2", "GRAPHITE"],
            "phase_count": 2,
            "gibbs_energy_J": {"value": -41981.578, "tolerance": 2.0},
            "backend_used": "ocasi",
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B2_steel1_FeC_yuksek_karbon",
        "zorluk": "kolay",
        "olcum": "Ayni sistem, bes kat karbon. Ferritin karbon cozme "
                 "kapasitesi doymus oldugu icin fazla karbon grafite gitmeli; "
                 "yani grafit miktari artmali, ferritin IC bilesimi degismemeli.",
        "soru": "steel1.TDB'de Fe=0.95 C=0.05 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.95, "C": 0.05},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "phases": ["BCC_A2", "GRAPHITE"],
            "phase_count": 2,
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B3_steel1_FeC_dusuk_karbon",
        "zorluk": "kolay",
        "olcum": "Ayni sistemin ucuncu noktasi. B1/B2/B3 birlikte, tek bir "
                 "ekseni tarayarak motorun tutarli davrandigini gosteriyor.",
        "soru": "steel1.TDB'de Fe=0.98 C=0.02 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.98, "C": 0.02},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "phases": ["BCC_A2", "GRAPHITE"],
            "phase_count": 2,
            "mass_balance": True,
            "elements_present": True,
        },
    },

    # ---- ORTA (6) -- karbur olusuyor, motor kademe atlayabiliyor ---------

    {
        "id": "B4_steel1_M23C6",
        "zorluk": "orta",
        "olcum": "Krom karburu olusuyor. Karbonun neredeyse tamami karbure "
                 "girdigi icin karbur miktari 0.01/0.2069 ~ 0.048 civari "
                 "olmali -- stokiyometriden onceden hesaplanabilir bir sayi.",
        "soru": "steel1.TDB'de Fe=0.79 Cr=0.20 C=0.01 icin 1100 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "phases": ["BCC_A2", "M23C6"],
            "stoichiometry": {"M23C6": 6 / 29},
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B5_steel1_M7C3_seyreltik_V",
        "zorluk": "orta",
        "olcum": "A6'nin cok fazli esdegeri: ayni seyreltik V (0.001), ama "
                 "karbon artirilarak sistem iki fazli hale getirildi. Artik "
                 "V'nin fazlar arasindaki paylasimi gercek bir olcum -- tek "
                 "fazli surumde bu imkansizdi.",
        "soru": "steel1.TDB'de Fe=0.919 C=0.04 Cr=0.04 V=0.001 icin "
                "1100 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.919, "C": 0.04,
                                     "CR": 0.04, "V": 0.001},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "phases": ["FCC_A1", "M7C3"],
            "stoichiometry": {"M7C3": 3 / 10},
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B6_steel1_bes_element_uc_faz",
        "zorluk": "orta",
        "olcum": "Bes element, uc faz, iki seyreltik element (V ve Mo) "
                 "paylasiliyor. Bes bagimsiz kutle dengesi ayni anda "
                 "kapanmali. Bu vaka uc asamali yinelemeli olcumun de "
                 "konusuydu (bkz. RAPOR.md, Bolum 3).",
        "soru": "steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 "
                "icin 1100 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.879, "C": 0.04, "CR": 0.06,
                                     "MO": 0.02, "V": 0.001},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "phases": ["BCC_A2", "M23C6", "FCC_A1"],
            "stoichiometry": {"M23C6": 6 / 29},
            "backend_used": "native_oc",
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B7_steel1_dusuk_sicaklik",
        "zorluk": "orta",
        "olcum": "B6 ile ayni bilesim, 200 K asagida. Dusuk sicaklikta karbur "
                 "miktari artmali. Ayni bilesimin iki sicakligi, motorun "
                 "sicaklik bagimliligini tutarli isledigini gosteriyor.",
        "soru": "steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 "
                "icin 900 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.879, "C": 0.04, "CR": 0.06,
                                     "MO": 0.02, "V": 0.001},
            "composition_basis": "mole_fraction",
            "temperature_K": 900,
        },
        "expected": {
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B8_saf2507_dubleks",
        "zorluk": "orta",
        "olcum": "Karbonsuz bir paslanmaz celik veritabani (Cr, Fe, Mn, Mo, "
                 "N, Ni). Cift fazli paslanmaz celikler ferrit + ostenit "
                 "dengesindedir. Karburlerin hic olmadigi bir cok fazli "
                 "sistem -- B grubunun geri kalanindan farkli bir kimya.",
        "soru": "saf2507.TDB'de Fe=0.62 Cr=0.25 Ni=0.07 Mo=0.04 Mn=0.01 "
                "N=0.01 icin 1200 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "saf2507.TDB",
            "elements_composition": {"FE": 0.62, "CR": 0.25, "NI": 0.07,
                                     "MO": 0.04, "MN": 0.01, "N": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
        },
        "expected": {
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B9_iron4cd_FeNiC",
        "zorluk": "orta",
        "olcum": "En buyuk veritabani (13 element, 124 faz). Nikel iceren tek "
                 "celik dosyasi; karbon eklenerek cok fazli hale getirildi. "
                 "124 faz arasindan dogru olanlari secmesi gerekiyor.",
        "soru": "iron4cd.TDB'de Fe=0.85 Ni=0.10 C=0.05 icin 1100 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "iron4cd.TDB",
            "elements_composition": {"FE": 0.85, "NI": 0.10, "C": 0.05},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "mass_balance": True,
            "elements_present": True,
        },
    },

    # ---- ZOR (3) -- alti element, coklu karbur, bilesim kumeleri ---------

    {
        "id": "B10_steel7_alti_element",
        "zorluk": "zor",
        "olcum": "Alti element, dort faz, iki farkli karbur (M23C6 ve M6C) "
                 "artikMC tipi bir dorduncu faz. Uc bagimsiz stokiyometri ve "
                 "alti kutle dengesi ayni anda tutmali. Bu vaka zaman asimi "
                 "duzeltmesinin de dogrulamasiydi.",
        "soru": "steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 "
                "Fe=0.837 icin 1173 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel7.TDB",
            "elements_composition": {"C": 0.04, "CR": 0.06, "MO": 0.05,
                                     "SI": 0.003, "V": 0.01, "FE": 0.837},
            "composition_basis": "mole_fraction",
            "temperature_K": 1173,
        },
        "expected": {
            "stoichiometry": {"M23C6": 6 / 29, "M6C": 1 / 7},
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B11_steel7_dusuk_sicaklik",
        "zorluk": "zor",
        "olcum": "B10 ile ayni alti elementli bilesim, 1000 K'de. Faz kumesi "
                 "degismesi bekleniyor; hangi karburlerin cikacagi onceden "
                 "bilinmiyor, olcut kutle korunumu ve element varligi.",
        "soru": "steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 "
                "Fe=0.837 icin 1000 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel7.TDB",
            "elements_composition": {"C": 0.04, "CR": 0.06, "MO": 0.05,
                                     "SI": 0.003, "V": 0.01, "FE": 0.837},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "B12_iron4cd_yedi_element",
        "zorluk": "zor",
        "olcum": "ARTIK COZULUYOR. Bu vaka bir motor siniri olarak "
                 "yazilmisti: yedi element birden, OCASI 4204 ile "
                 "yakinsamiyor, native motor da cozemiyor. Sinir bizdeydi. "
                 "Uyari veren bir TDB'de motor RETURN bekliyor ve makronun "
                 "kosul satiri o istemi cevaplamis oluyordu; iron4cd tam "
                 "oyle bir veritabani. Duzeltildikten sonra native kademe "
                 "cozuyor: FCC_A1 + M23C6, kesirler 1'e topluyor, Katman A "
                 "ve karsilik denetimi geciyor -- %16 Cr, %8 Ni, %0.1 C "
                 "icin ders kitabi sonucu. Olculen sey artik dogru sayi.",
        "soru": "iron4cd.TDB'de Fe=0.70 Cr=0.16 Ni=0.08 Mo=0.02 Mn=0.02 "
                "Si=0.01 C=0.01 icin 1100 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "iron4cd.TDB",
            "elements_composition": {"FE": 0.70, "CR": 0.16, "NI": 0.08,
                                     "MO": 0.02, "MN": 0.02, "SI": 0.01,
                                     "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {
            "phases": ["FCC_A1", "M23C6_D84"],
            "elements_present": True,
            "mass_balance": True,
        },
    },
]
C_FAZ_GECISI = [
    # Sicaklik taramasi: erime, kati-kati donusum, otektik. Diyagram yolunu
    # (native STEP -> gap-fill -> gnuplot) ve nokta kapsamini sinar.
    # Olcut, taranan noktalarin cozulup cozulmedigi ve beklenen fazlarin
    # tarama boyunca gorunup gorunmedigi.

    {
        "id": "C1_agcu_otektik",
        "zorluk": "kolay",
        "olcum": "Ag-Cu otektigi ~1056 K'de. Tarama kati bolgeden sivi "
                 "bolgeye gecmeli; her iki uc da ayni veri setinde gorunmeli.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 800-1400 K faz diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 800, "temperature_max_K": 1400,
            "n_points": 20,
        },
        "expected": {"phases": ["LIQUID"], "max_failed_fraction": 0.10},
    },
    {
        "id": "C2_alni_erime",
        "zorluk": "kolay",
        "olcum": "NiAl genis bir araligta tek fazli, sonra ~1920 K'de eriyor. "
                 "Tarama boyunca hem kati hem sivi faz gorunmeli.",
        "soru": "alni-4slx.TDB'de Al=0.5 Ni=0.5 icin 500-2000 K faz "
                "diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.5, "NI": 0.5},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 500, "temperature_max_K": 2000,
            "n_points": 20,
        },
        "expected": {"phases": ["LIQUID"], "max_failed_fraction": 0.10},
    },
    {
        "id": "C3_steel1_genis_tarama",
        "zorluk": "orta",
        "olcum": "300-2000 K: ferrit+grafit, ostenit, delta-ferrit+sivi ve "
                 "tam sivi -- dort ayri rejim tek taramada. Bu sunucunun "
                 "en genis sicaklik araligi.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 300-2000 K faz "
                "diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 300, "temperature_max_K": 2000,
            "n_points": 25,
        },
        "expected": {"max_failed_fraction": 0.20},
    },
    {
        "id": "C4_steel1_karbur_cozunmesi",
        "zorluk": "orta",
        "olcum": "Bes elementli celik, 900-1400 K. Sicaklik arttikca karbur "
                 "cozunup matrise girmeli. B6/B7 ile ayni bilesim -- iki tek "
                 "nokta ile bir tarama ayni sistemi farkli aciardan "
                 "gosteriyor.\n\n"
                 "1200 K olcutu sonradan eklendi ve sebebi kayda deger: bu "
                 "vaka, diyagramin doksan derecelik bir bolumu YANLIS FAZI "
                 "gosterirken geciyordu. STEP, 900 K'de kararli olan ferrit "
                 "cizgisini surekliligle 1243 K'ye tasiyordu; oysa ~1130 "
                 "K'den sonra ostenit kararli. Vaka geciyordu cunku tek "
                 "olcutu 'kac nokta cozuldu' idi ve 45 noktanin hepsi "
                 "hesaplanabilmisti. Kapsama, dogruluk demek degil.",
        "soru": "steel1.TDB'de Fe=0.879 C=0.04 Cr=0.06 Mo=0.02 V=0.001 icin "
                "900-1400 K faz diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.879, "C": 0.04, "CR": 0.06,
                                     "MO": 0.02, "V": 0.001},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 900, "temperature_max_K": 1400,
            "n_points": 20,
        },
        "expected": {
            "max_failed_fraction": 0.20,
            # Bagimsiz tek nokta hesaplariyla dogrulandi: 900 K'de ferrit,
            # 1200 K'de ostenit. Ikisi de global minimizasyon yapan yoldan,
            # yani surekliligi olcen STEP'ten bagimsiz.
            "phases_present_at": {900: ["BCC_A2"], 1200: ["FCC_A1"]},
            "phases_absent_at": {1200: ["BCC_A2"]},
        },
    },
    {
        "id": "C5_agcu_otektik_bilesim",
        "zorluk": "orta",
        "olcum": "Tam otektik bilesimde (%72 Ag) tarama. Otektikte kati->sivi "
                 "gecisi tek sicaklikta olur; dar bir aralikta olup bitmeli.",
        "soru": "agcu.TDB'de Ag=0.72 Cu=0.28 icin 900-1200 K faz "
                "diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.72, "CU": 0.28},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 900, "temperature_max_K": 1200,
            "n_points": 20,
        },
        "expected": {"phases": ["LIQUID"], "max_failed_fraction": 0.10},
    },
    {
        "id": "C6_alfe_tarama",
        "zorluk": "orta",
        "olcum": "Dort alt orgulu BCC modeli kullanan bir veritabaninda "
                 "tarama. A4 ile ayni bilesim, tek nokta yerine aralik.",
        "soru": "AlFe-4SLBF.TDB'de Al=0.2 Fe=0.8 icin 800-1800 K faz "
                "diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "AlFe-4SLBF.TDB",
            "elements_composition": {"AL": 0.2, "FE": 0.8},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 800, "temperature_max_K": 1800,
            "n_points": 20,
        },
        "expected": {"max_failed_fraction": 0.25},
    },
    {
        "id": "C7_alni_yakinsama_zorlugu",
        "zorluk": "zor",
        "olcum": "BILINEN ZOR NOKTA. Bu bilesim ve aralik, Python dongusu "
                 "yoluna dustugunde noktalarin ~%23'u yakinsamiyor. Olculen "
                 "sey, sistemin eksigi GIZLEMEDEN raporlamasi: her dusen "
                 "nokta kendi hatasini tasimali ve Katman A orani bildirmeli.",
        "soru": "alni-4slx.TDB'de Al=0.75 Ni=0.25 icin 800-1700 K faz "
                "diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.75, "NI": 0.25},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 800, "temperature_max_K": 1700,
            "n_points": 20,
        },
        "expected": {"max_failed_fraction": 0.40},
    },
    {
        "id": "C8_steel7_tarama",
        "zorluk": "zor",
        "olcum": "Alti elementli celik uzerinde tarama. Her nokta ayri bir "
                 "cok fazli hesap; en pahali vaka. B10/B11'in tarama hali.",
        "soru": "steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 "
                "Fe=0.837 icin 900-1400 K faz diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "steel7.TDB",
            "elements_composition": {"C": 0.04, "CR": 0.06, "MO": 0.05,
                                     "SI": 0.003, "V": 0.01, "FE": 0.837},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 900, "temperature_max_K": 1400,
            "n_points": 15,
        },
        "expected": {"max_failed_fraction": 0.30},
    },
]
D_BILESIM_KUMESI = [
    # Ayni faz adinin birden cok kez, farkli bilesimlerle cikmasi. Ag-Cu'da
    # karismazlik boslugu iki FCC katisi uretir (FCC_A1, FCC_A1_AUTO#2);
    # celiklerde ayni ad hem ostenit hem MC karburu olabilir.
    #
    # Bu sinif, bu projede iki gercek hatanin cikti yer: LIQUID/LIQUID#1 ad
    # tutarsizligi ve kutle kesri / mol miktari karisikligi (uc fazin toplami
    # 1.26 cikmisti). Toplamin 1 olmasi bu grupta ozellikle anlamli.

    {
        "id": "D1_agcu_karismazlik",
        "zorluk": "kolay",
        "olcum": "Otektik altinda iki FCC katisi bir arada: biri gumusce, "
                 "digeri bakirca zengin. Ayni faz adi, iki bilesim kumesi.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 900 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_K": 900,
        },
        "expected": {
            "phase_count": 2,
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "D2_agcu_gumus_zengin",
        "zorluk": "orta",
        "olcum": "Boslugu gumus tarafindan gecmek. Faz miktarlari kolun "
                 "kaldirac kuralina uymali: gumusce zengin taraf agir basmali.",
        "soru": "agcu.TDB'de Ag=0.9 Cu=0.1 icin 900 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.9, "CU": 0.1},
            "composition_basis": "mole_fraction",
            "temperature_K": 900,
        },
        "expected": {"mass_balance": True, "elements_present": True},
    },
    {
        "id": "D3_agcu_bakir_zengin",
        "zorluk": "orta",
        "olcum": "Ayni boslugun oteki ucu. D2 ile birlikte, iki bilesim "
                 "kumesinin bilesime gore yer degistirdigini gosteriyor.",
        "soru": "agcu.TDB'de Ag=0.2 Cu=0.8 icin 900 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.2, "CU": 0.8},
            "composition_basis": "mole_fraction",
            "temperature_K": 900,
        },
        "expected": {"mass_balance": True, "elements_present": True},
    },
    {
        "id": "D4_agcu_dusuk_sicaklik",
        "zorluk": "orta",
        "olcum": "Sicaklik dustukce bosluk genisler, iki katinin bilesimleri "
                 "birbirinden uzaklasir. Ayni bilesim, D1'den 200 K asagida.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 700 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_K": 700,
        },
        "expected": {
            "phase_count": 2,
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "D5_steel7_iki_fcc_kumesi",
        "zorluk": "zor",
        "olcum": "AYNI SONUCTA IKI FCC KUMESI: biri demirce zengin matris "
                 "(FCC_A1_AUTO#2, Fe 0.92), digeri vanadyum karburu "
                 "(FCC_A1, C 0.46 / V 0.36). Ikisi de ayni kristal yapiyi "
                 "tasir ve yalnizca bilesim ayirt eder. Faz adinin kimlik "
                 "olmadigini gosteren en net vaka. "
                 "Varsayilan kume '#1' eki olmadan yazilir; ikinci kume "
                 "'#2' ekini KORUR, cunku o gercekten ayri bir kumedir. "
                 "Vaka eskiden FCC_A1#1 bekliyordu -- o, hangi kademenin "
                 "cevapladigina gore degisen bir yazimdi.",
        "soru": "steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 "
                "Fe=0.837 icin 1173 K'de hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel7.TDB",
            "elements_composition": {"C": 0.04, "CR": 0.06, "MO": 0.05,
                                     "SI": 0.003, "V": 0.01, "FE": 0.837},
            "composition_basis": "mole_fraction",
            "temperature_K": 1173,
        },
        "expected": {
            "phases": ["FCC_A1_AUTO#2", "FCC_A1"],
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "D6_agcu_otektik_noktasinda",
        "zorluk": "zor",
        "olcum": "Tam otektik sicakliginda (1056 K): kati ve sivi bir arada, "
                 "gecis araligi bir kac Kelvin. Sayisal olarak en hassas "
                 "nokta; kucuk bir sapma tamamen farkli bir faz kumesi verir.",
        "soru": "agcu.TDB'de Ag=0.6 Cu=0.4 icin 1056 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "composition_basis": "mole_fraction",
            "temperature_K": 1056,
        },
        "expected": {"mass_balance": True, "elements_present": True},
    },
]
E_YARI_KARARLI = [
    # Kararli bir fazi kapatip ne oldugana bakmak. CALPHAD'in kendine has bir
    # yetenegi: gercekte olusan degil, olusmasi engellenirse ne olurdu
    # sorusunun cevabi. Celiklerde grafit yerine sementit olusmasi tam bu
    # yolla modellenir.
    #
    # Olcut kesin: kapatilan faz sonucta OLMAMALI. Motor askiya almayi
    # sessizce yutarsa kararli dengeyi dondurur -- sorulan soru bu degildir.

    {
        "id": "E1_steel1_grafit_kapali",
        "zorluk": "kolay",
        "olcum": "Grafit kapatilinca karbon metalik fazlarda cozunmek zorunda "
                 "kalir; sistem ferrit+grafitten ferrit+ostenite gecer. "
                 "Kapatilan faz sonucta gorunmemeli.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K'de GRAPHITE fazini "
                "kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "suspended_phases": ["GRAPHITE"],
        },
        "expected": {
            "phases_absent": ["GRAPHITE"],
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "E2_steel1_grafit_kapali_enerji",
        "zorluk": "orta",
        "olcum": "TERMODINAMIK BIR ESITSIZLIK. Kararli bir fazi askiya almak "
                 "Gibbs enerjisini ancak YUKSELTEBILIR, asla dusuremez -- "
                 "cunku serbest secenekler kumesi daralir. Acikken -41981.6, "
                 "kapaliyken bundan daha az negatif olmali. Referans "
                 "gerektirmeyen, dogrudan fizikten gelen bir olcut.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 icin 1000 K'de GRAPHITE fazini "
                "kapatarak hesapla ve enerjiyi acik haliyle karsilastir",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "suspended_phases": ["GRAPHITE"],
        },
        "expected": {
            "phases_absent": ["GRAPHITE"],
            "gibbs_energy_J": {"value": -41966.0, "tolerance": 50.0},
            "mass_balance": True,
        },
    },
    {
        "id": "E3_steel1_karbur_kapali",
        "zorluk": "orta",
        "olcum": "Bu sefer kapatilan sey grafit degil bir karbur. B4 ile ayni "
                 "bilesim: acikken M23C6 olusuyordu, kapaliyken krom ve karbon "
                 "baska bir yere gitmek zorunda.",
        "soru": "steel1.TDB'de Fe=0.79 Cr=0.20 C=0.01 icin 1100 K'de M23C6 "
                "fazini kapatarak hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
            "suspended_phases": ["M23C6"],
        },
        "expected": {
            "phases_absent": ["M23C6"],
            "mass_balance": True,
            "elements_present": True,
        },
    },
    {
        "id": "E4_steel7_iki_faz_kapali",
        "zorluk": "zor",
        "olcum": "Alti elementli sistemde AYNI ANDA IKI karbur kapatiliyor. "
                 "B10'da dort faz cikiyordu; ikisi engellenince kalan "
                 "elementlerin baska bir denge bulmasi gerekiyor.\n\n"
                 "SONUC: hesaplanamiyor, ve bu bir MIMARI SINIRI ortaya "
                 "cikardi. Faz kapatma yalnizca OCASI'de destekleniyor; "
                 "native motor kademesi suspended_phases verilen istekler "
                 "icin hic devreye girmiyor. Yani yari kararli hesaplarda "
                 "kademeli motorun guvenlik agi YOK -- OCASI yakinsamazsa "
                 "baska deneyecek bir sey kalmiyor. B12'de iki kademe de "
                 "denenmisti; burada tek kademe var.",
        "soru": "steel7.TDB'de C=0.04 Cr=0.06 Mo=0.05 Si=0.003 V=0.01 "
                "Fe=0.837 icin 1173 K'de M23C6 ve M6C fazlarini kapatarak "
                "hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel7.TDB",
            "elements_composition": {"C": 0.04, "CR": 0.06, "MO": 0.05,
                                     "SI": 0.003, "V": 0.01, "FE": 0.837},
            "composition_basis": "mole_fraction",
            "temperature_K": 1173,
            "suspended_phases": ["M23C6", "M6C"],
        },
        "expected": {
            "known_defect": "yari kararli hesapta kademeli motorun yedegi "
                            "yok: suspended_phases yalnizca OCASI'de "
                            "destekleniyor, o yakinsamazsa alternatif kalmiyor",
        },
    },
]
F_KARSILASTIRMA = [
    # compare_alloys iki bilesimi ayni sicaklikta hesaplayip bir de ozet
    # donduruyor. Ozet BAGIMSIZ bir kaynak degil: iki sonuctan turetilmis
    # olmali. Puanlayici bunu ayrica denetliyor -- ozetteki enerji farki, iki
    # sonucun farkina esit degilse ozet uydurulmus demektir.

    {
        "id": "F1_steel1_karbon_farki",
        "zorluk": "kolay",
        "olcum": "Ayni celigin iki karbon seviyesi. Ikisinde de ayni fazlar "
                 "cikmali; degisen sey grafit miktari olmali, ferritin IC "
                 "bilesimi degil -- ferrit karbonu zaten doymus durumda.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 ile Fe=0.95 C=0.05 "
                "bilesimlerini 1000 K'de karsilastir",
        "tool": "compare_alloys",
        "arguments": {
            "database": "steel1.TDB",
            "composition_a": {"FE": 0.99, "C": 0.01},
            "composition_b": {"FE": 0.95, "C": 0.05},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
            "label_a": "Fe-0.01C", "label_b": "Fe-0.05C",
        },
        "expected": {
            "phases_in_both": ["BCC_A2", "GRAPHITE"],
            "gibbs_difference_sign": "+",
        },
    },
    {
        "id": "F2_agcu_bilesim_farki",
        "zorluk": "kolay",
        "olcum": "Karismazlik boslugunun iki yakasi ayni sicaklikta. Fazlar "
                 "ayni, miktarlar farkli olmali.",
        "soru": "agcu.TDB'de Ag=0.8 Cu=0.2 ile Ag=0.3 Cu=0.7 bilesimlerini "
                "900 K'de karsilastir",
        "tool": "compare_alloys",
        "arguments": {
            "database": "agcu.TDB",
            "composition_a": {"AG": 0.8, "CU": 0.2},
            "composition_b": {"AG": 0.3, "CU": 0.7},
            "composition_basis": "mole_fraction",
            "temperature_K": 900,
            "label_a": "Ag-zengin", "label_b": "Cu-zengin",
        },
        "expected": {},
    },
    {
        "id": "F3_steel1_krom_farki",
        "zorluk": "orta",
        "olcum": "Krom eklemenin faz kumesini degistirmesi: kromsuz tarafta "
                 "grafit, kromlu tarafta karbur beklenir. Yani iki alasimin "
                 "'yalniz bende olan fazlar' listeleri bos olmamali.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 ile Fe=0.79 Cr=0.20 C=0.01 "
                "bilesimlerini 1100 K'de karsilastir",
        "tool": "compare_alloys",
        "arguments": {
            "database": "steel1.TDB",
            "composition_a": {"FE": 0.99, "C": 0.01},
            "composition_b": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
            "label_a": "kromsuz", "label_b": "20Cr",
        },
        "expected": {},
    },
    {
        "id": "F4_steel1_iki_motor_kademesi",
        "zorluk": "zor",
        "olcum": "Iki taraf farkli motor kademelerine dusuyor: biri OCASI ile "
                 "cozuluyor, otekinde OCASI yakinsamayip native devraliyor. "
                 "Karsilastirma ozetinin, farkli motorlardan gelen iki sonucu "
                 "tutarli bicimde birlestirebilmesi gerekiyor.",
        "soru": "steel1.TDB'de Fe=0.99 C=0.01 bilesimini 1000 K ile ayni "
                "bilesimin 1200 K halini karsilastir",
        "tool": "compare_alloys",
        "arguments": {
            "database": "steel1.TDB",
            "composition_a": {"FE": 0.99, "C": 0.01},
            "composition_b": {"FE": 0.98, "C": 0.02},
            "composition_basis": "mole_fraction",
            "temperature_K": 1200,
            "label_a": "C-0.01", "label_b": "C-0.02",
        },
        "expected": {},
    },
]
G_CELIK_DISI = [
    # Bu sunucudan hic gecmemis sistem siniflari: oksitler, tuzlar, gaz fazi.
    # Bilincli bir risk. Celik ve ikili metal sistemleri disinda hicbir sey
    # denenmedi; ayristiricinin, faz adlandirmasinin ve kademeli motorun
    # oralarda nasil davrandigi bilinmiyor.
    #
    # Bu vakalarin bir kismi kalabilir. Bu bir basarisizlik degil BULGU olur:
    # "sistem su sinif veritabanlarinda calismiyor" da raporlanabilir bir
    # sonuctur, ve kapsamin nerede bittigini bilmek onu bilmemekten iyidir.

    {
        "id": "G1_mgnacl_tuz",
        "zorluk": "kolay",
        "olcum": "TUZ SISTEMI -- hic denenmedi. Metalik olmayan, iyonik bir "
                 "sistem; faz adlari da farkli (SALT, NACL, MGCL2).\n\n"
                 "Vakayi yazarken iki sey ogrenildi:\n\n"
                 "1. Ilk yazilista bilesim yuk dengesiz secilmisti (Na + 2Mg "
                 "= 0.65 ama Cl = 0.5). Iyonik sistemde katyon ve anyon "
                 "yukleri esitlenmek zorunda. Vaka yazarinin hatasiydi.\n\n"
                 "2. Yuk dengesi duzeltilince de yakinsamadi. Daraltarak "
                 "sinir bulundu: SAF NaCl calisiyor, ama bilesimde MAGNEZYUM "
                 "olan hicbir nokta cozulmuyor (saf MgCl2 dahil, %5 Mg "
                 "katkisi dahil, 1300 K'de bile). Yani sinir sicaklikta ya da "
                 "yuk dengesinde degil, Mg iceren fazlarin kendisinde.\n\n"
                 "Ayrica dikkat: saf NaCl sonucu ayni fazin IKI OZDES bilesim "
                 "kumesini donduruyor (NACL#1 ve NACL_AUTO#2, her biri 0.5). "
                 "Kutle korunumu kapaniyor ama gosterim dejenere -- tek bir "
                 "faz ikiye bolunmus gorunuyor.",
        "soru": "MgNaCl.TDB'de Na=0.5 Cl=0.5 icin 1100 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "MgNaCl.TDB",
            "elements_composition": {"NA": 0.5, "CL": 0.5},
            "composition_basis": "mole_fraction",
            "temperature_K": 1100,
        },
        "expected": {"mass_balance": True, "elements_present": True},
    },
    {
        "id": "G2_ou_oksit",
        "zorluk": "kolay",
        "olcum": "OKSIT SISTEMI -- hic denenmedi. UO2 stokiyometrisine yakin "
                 "bir bilesim (U 1 : O 2). Bu veritabaninda cok sayida "
                 "stokiyometrik bilesik ve bir IONIC_LIQUID fazi var.",
        "soru": "OU.TDB'de U=0.333 O=0.667 icin 1000 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "OU.TDB",
            "elements_composition": {"U": 0.333, "O": 0.667},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {"mass_balance": True, "elements_present": True},
    },
    {
        "id": "G3_cho_gaz",
        "zorluk": "orta",
        "olcum": "GAZ FAZI -- hic denenmedi, ve BIR KUSUR BULDU.\n\n"
                 "Motor hesabi yapiyor (GAS = 1.0, G = -136100 J) ama "
                 "ayristirici gaz fazinin bilesimini yanlis okuyor: element "
                 "kesirleri yerine MOLEKUL TURLERINI dolduruyor --\n"
                 "  H2 0.4339, C1O1 0.3223, C1O2 0.1211, H2O1 0.1138, "
                 "C1H4 0.0088 ...\n"
                 "ve baslik metninden bir kalinti yakaliyor: 'ARE': 73.0.\n\n"
                 "Element kutle dengesi bu yuzden asla kapanamaz (C icin "
                 "2.5e-30 dondu, 0.2 beklenirken). Kati ve sivi fazlarda "
                 "bilesenler zaten element oldugu icin kusur bugune kadar "
                 "gorunmemisti; gaz fazinda bilesenler molekul.\n\n"
                 "Vaka bilerek acik birakildi: bu bir gerileme degil, "
                 "belgelenmis bir sinir. Duzeltilirse bayrak kalkar ve vaka "
                 "normal olcutlerine doner.",
        "soru": "CHO-gas.TDB'de C=0.2 H=0.5 O=0.3 icin 1000 K'de denge "
                "hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "CHO-gas.TDB",
            "elements_composition": {"C": 0.2, "H": 0.5, "O": 0.3},
            "composition_basis": "mole_fraction",
            "temperature_K": 1000,
        },
        "expected": {
            "known_defect": "gaz fazi bilesimi element yerine molekul turu "
                            "olarak ayristiriliyor; kutle dengesi kapanamaz",
        },
    },
    {
        "id": "G4_bef_intermetalik",
        "zorluk": "orta",
        "olcum": "Sert intermetalik sistem (Mo-Ni-Re): SIGMA, CHI, "
                 "MONI_DELTA gibi fazlar. Celiklerde de gorulen ama burada "
                 "baskin olan faz aileleri. Bu veritabani da hic denenmedi.",
        "soru": "BEF.TDB'de Mo=0.3 Ni=0.5 Re=0.2 icin 1400 K'de denge hesapla",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "BEF.TDB",
            "elements_composition": {"MO": 0.3, "NI": 0.5, "RE": 0.2},
            "composition_basis": "mole_fraction",
            "temperature_K": 1400,
        },
        "expected": {"mass_balance": True, "elements_present": True},
    },
    {
        "id": "G5_ou_tarama",
        "zorluk": "zor",
        "olcum": "Oksit sisteminde sicaklik taramasi: hic denenmemis bir "
                 "veritabani sinifi ile hic denenmemis bir kombinasyon. Hem "
                 "diyagram yolu hem oksit ayristirmasi ayni anda sinaniyor.",
        "soru": "OU.TDB'de U=0.333 O=0.667 icin 1000-2500 K faz diyagrami ciz",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "OU.TDB",
            "elements_composition": {"U": 0.333, "O": 0.667},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 1000, "temperature_max_K": 2500,
            "n_points": 15,
        },
        "expected": {"max_failed_fraction": 0.40},
    },
]

H_BILESIM_EKSENI = [
    # Izotermal kesit: sicaklik sabit, bir elementin orani taraniyor.
    # C grubundan farki, sorunun kendisi: "bu alasim isinirken ne oluyor"
    # degil, "bu sicaklikta bu elementten daha fazla eklersem ne cikiyor".
    #
    # Olcut faz listesi DEGIL, faz SIRASI. Bir taramada "M7C3 de var M23C6
    # de var" demek hicbir sey soylemiyor; bilgi hangisinin once ciktiginda.
    # Sira, sistemin kendi ciktisindan degil kimyadan geliyor: M7C3'un
    # karbonu 3/10 = 0.30, M23C6'nin 6/29 = 0.207. Karbon arttikca daha
    # karbon-zengini karbur kararli hale gelir, tersi degil.

    {
        "id": "H1_krom_taramasi_1100K",
        "zorluk": "orta",
        "olcum": "Krom artarken uc sey birden olmali: karbur M7C3'ten "
                 "M23C6'ya donmeli, matris ostenitten ferrite gecmeli, ve "
                 "eksenin sonu gercekten hesaplanmali. Son nokta ayrica "
                 "STEP'in surekliligini sinar -- STEP orada yari kararli "
                 "FCC+M7C3 veriyordu, kararli cevap BCC+M23C6.",
        "soru": "steel1.TDB'de 1100 K'de Fe-%20Cr-%1C alasiminda kromu "
                "%1'den %30'a cikarirsam hangi fazlar cikar",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "CR", "axis_min": 0.01, "axis_max": 0.30,
            "temperature_K": 1100, "n_points": 12,
        },
        "expected": {
            "phases": ["FCC_A1", "M7C3", "M23C6", "BCC_A2"],
            "phase_order": [("M7C3", "M23C6"), ("FCC_A1", "BCC_A2")],
            "phases_at_start": ["FCC_A1"],
            "phases_at_end": ["BCC_A2", "M23C6"],
            "max_failed_fraction": 0.10,
        },
    },
    # 2026-08-24: bu vaka bir kez "BCC_A2 hicbir noktada yok" diye kaldi,
    # o kosum 62 saniye surmustu (normalde saniyeler). Ucu bagimsiz olmak
    # uzere dort kosumda daha tekrarlamadi; ilk nokta her seferinde
    # BCC_A2 0.7611 + FCC_A1 0.2389 geldi. Aciklanamadi, o yuzden
    # yazildi -- tekrarlarsa aranacak yer STEP'in eksen basindaki noktayi
    # uretip uretmedigi.
    {
        "id": "H2_karbon_taramasi",
        "zorluk": "orta",
        "olcum": "Ayni sistemde bu sefer karbon taraniyor. Dusuk karbonda "
                 "ferrit+ostenit birlikte; karbon arttikca ostenit "
                 "kararlanip karbur buyuyor ve M23C6'dan M7C3'e -- yani "
                 "H1'in TERSI sirada -- gecmeli. Iki vaka birlikte, sıranın "
                 "ezberlenmis bir cevap olmadigini gosteriyor.",
        "soru": "steel1.TDB'de 1100 K'de Fe-%10Cr alasiminda karbonu "
                "%0.1'den %5'e cikarirsam ne olur",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.89, "CR": 0.10, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "C", "axis_min": 0.001, "axis_max": 0.05,
            "temperature_K": 1100, "n_points": 12,
        },
        "expected": {
            "phases": ["BCC_A2", "FCC_A1", "M23C6", "M7C3"],
            "phase_order": [("M23C6", "M7C3")],
            "phases_at_start": ["BCC_A2", "FCC_A1"],
            "phases_at_end": ["FCC_A1", "M7C3"],
            "max_failed_fraction": 0.10,
        },
    },
    {
        "id": "H3_krom_taramasi_1400K",
        "zorluk": "orta",
        "olcum": "H1 ile ayni tarama, 300 K daha sicak. Ostenit cok daha "
                 "gec birakiyor (1100 K'de ~%11'de, 1400 K'de ~%14'te) ve "
                 "arada genis bir iki-fazli bolge var. Ayni sorunun "
                 "sicakliga duyarli oldugunu sinar -- tek bir taramaya "
                 "bakip 'krom ferrit yapar' demek yeterli degil.",
        "soru": "steel1.TDB'de 1400 K'de Fe-%20Cr-%1C alasiminda kromu "
                "%1'den %30'a cikarirsam hangi fazlar cikar",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.79, "CR": 0.20, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "CR", "axis_min": 0.01, "axis_max": 0.30,
            "temperature_K": 1400, "n_points": 12,
        },
        "expected": {
            "phases": ["FCC_A1", "BCC_A2", "M23C6"],
            "phase_order": [("FCC_A1", "BCC_A2")],
            "phases_at_start": ["FCC_A1"],
            "phases_at_end": ["BCC_A2", "M23C6"],
            "max_failed_fraction": 0.10,
        },
    },
    {
        "id": "H4_molibden_taramasi",
        "zorluk": "zor",
        "olcum": "Tek taramada dort ayri rejim: M7C3, M23C6, M6C ve Laves "
                 "fazi. Molibden kendi karburunu (M6C) yapar ve yeterince "
                 "artinca Fe2Mo Laves fazi cikar. Dort elementli sistem, "
                 "uc farkli karbur -- bu sunucunun en kalabalik kesiti.",
        "soru": "steel1.TDB'de 1100 K'de Fe-%10Cr-%3C alasimina molibden "
                "eklersem, %15'e kadar, hangi fazlar cikar",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.85, "CR": 0.10, "MO": 0.02,
                                     "C": 0.03},
            "composition_basis": "mole_fraction",
            "axis_element": "MO", "axis_min": 0.0, "axis_max": 0.15,
            "temperature_K": 1100, "n_points": 12,
        },
        "expected": {
            "phases": ["M7C3", "M23C6", "M6C", "LAVES_PHASE", "BCC_A2"],
            "phase_order": [("M23C6", "M6C"), ("M6C", "LAVES_PHASE")],
            "phases_at_start": ["FCC_A1", "M7C3"],
            "phases_at_end": ["BCC_A2", "M6C", "LAVES_PHASE"],
            "max_failed_fraction": 0.10,
        },
    },
]

I_KATILASMA = [
    # Scheil-Gulliver: denge degil YOL. Sivi homojen sayilir, her sicaklik
    # adiminda olusan kati sistemden cikarilir, kalan sivinin bilesimi buna
    # gore guncellenir. Gercek dokumdeki segregasyon budur.
    #
    # Olcut faz listesi degil, ZENGINLESME. Son sivinin bilesimi nominal
    # degerin uzerine cikmali -- Scheil'in var olma sebebi bu. Ve tamamen
    # hesap makinesiyle kontrol edilebilir.
    #
    # Iki vakada BEKLENEN completed=False. Motor bu sistemlerde katilasmayi
    # sonuna kadar goturemiyor; gecme olcutu bunu duzeltmek degil, DOGRU
    # SOYLEMEK. Yarim kalmis bir egriyi tam gibi sunmak, bu projenin
    # yakaladigi hatalarin aynisi olurdu.

    {
        "id": "I1_cost507R_katilasma",
        "zorluk": "orta",
        "olcum": "Al-Mg-Si-Zn dokum alasimi. Katilasma sonuna kadar gidiyor "
                 "ve son sivi %73 cinko -- nominal %2'den otuz kat fazla. "
                 "Dagitimin kendi ornek makrosu da 'son sivi %70 Zn' diyor, "
                 "yani bu sayi motorun kendi belgesiyle bagimsiz olarak "
                 "dogrulanabiliyor.",
        "soru": "cost507R.TDB'de Al-%2Mg-%3Si-%2Zn alasimini 1000 K'den "
                "sogutursam katilasma sirasinda segregasyon nasil olur",
        "tool": "calculate_scheil_solidification",
        "arguments": {
            "database": "cost507R.TDB",
            "elements_composition": {"AL": 0.93, "MG": 0.02, "SI": 0.03,
                                     "ZN": 0.02},
            "composition_basis": "mole_fraction",
            "seed_temperature_K": 1000,
            "temperature_min_K": 600,
        },
        "expected": {
            "completed": True,
            "max_final_liquid_fraction": 0.02,
            "solid_phases": ["FCC_A1", "MG2SI"],
            "segregation": {"ZN": 0.5},
        },
    },
    {
        "id": "I2_steel1_katilasma_eksik",
        "zorluk": "zor",
        "olcum": "Fe-%1C. Karbon son siviya suruluyor (%1 -> %17) ama "
                 "katilasma sonuna kadar gitmiyor: cozucu, sivi asirilastikca "
                 "yakinsamayi birakiyor. Bu vakanin gecme olcutu hesabin "
                 "tamamlanmasi DEGIL, tamamlanmadigini soylemesi.",
        "soru": "steel1.TDB'de Fe-%1C celigini 1900 K'den sogutursam "
                "katilasma sirasinda karbon nasil dagilir",
        "tool": "calculate_scheil_solidification",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "seed_temperature_K": 1900,
            "temperature_min_K": 1000,
        },
        "expected": {
            "completed": False,
            "solid_phases": ["BCC_A2"],
            "segregation": {"C": 0.05},
        },
    },
    {
        "id": "I3_agcu_otektige_yakin",
        "zorluk": "zor",
        "olcum": "Ag-%20Cu, otektik bilesime yakin. Sivi dogrudan degismez "
                 "noktaya iniyor -- Scheil icin en zor durum, ve motor "
                 "%13 sivi kalmisken duruyor. Bakir 0.20'den 0.82'ye "
                 "zenginlesiyor. I1 ile birlikte: ayni arac hem tamamlanan "
                 "hem yarim kalan durumu dogru raporlamali.",
        "soru": "agcu.TDB'de Ag-%20Cu lehimini 1300 K'den sogutursam "
                "katilasma nasil ilerler",
        "tool": "calculate_scheil_solidification",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.8, "CU": 0.2},
            "composition_basis": "mole_fraction",
            "seed_temperature_K": 1300,
            "temperature_min_K": 800,
        },
        "expected": {
            "completed": False,
            "solid_phases": ["FCC_A1"],
            "segregation": {"CU": 0.6},
        },
    },
]

J_FAZ_DIYAGRAMI = [
    # Iki eksenli gercek faz diyagrami. Digerleri bir ekseni sabitler; bu
    # hicbirini sabitlemez, fazlarin bulustugu SINIRLARI izler.
    #
    # Olcut degismez sicakliklar. Bunlar diyagramin en belirgin ozellikleri
    # ve -- onemlisi -- bu projede BAGIMSIZ olarak olculduler. Fe-C
    # otektoidi, tek nokta denge hesaplarini ikiye bolerek 1010-1012 K
    # arasinda bulunmustu (1010 K'de ferrit+grafit, 1012 K'de ostenit).
    # MAP 1011.173 diyor. Iki yontem, ayni sayi.

    {
        "id": "J1_agcu_faz_diyagrami",
        "zorluk": "orta",
        "olcum": "Ag-Cu, klasik otektik diyagram. Tek bir degismez tepkime "
                 "olmali ~1056 K'de. Bagimsiz kontrol: tek nokta "
                 "hesaplarinda 1055 K'de sistem tamamen kati, 1060 K'de "
                 "%99 sivi -- otektik ikisinin arasinda. Ayrica karismazlik "
                 "boslugunun iki yarisi (FCC_A1 ve FCC_A1_AUTO#2) ayri "
                 "gorunmeli.\n\n"
                 "Tohum sicakligi ozellikle veriliyor ve olcumun bir "
                 "parcasi: MAP tohumdan disari dogru izler. 1000 K iki "
                 "kati fazin bolgesinde, oradan baslayinca karismazlik "
                 "boslugu da bulunuyor. Varsayilan orta nokta (1150 K) tek "
                 "fazli sivida kaliyor ve diyagram daha az sinir iceriyor "
                 "-- ayni sistem, ayni arac, farkli baslangic, farkli "
                 "kapsam. Kaydediliyor cunku kullanicinin bilmesi gereken "
                 "bir davranis.",
        "soru": "agcu.TDB icin Ag-Cu faz diyagramini ciz",
        "tool": "calculate_phase_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.8, "CU": 0.2},
            "composition_basis": "mole_fraction",
            "axis_element": "CU", "axis_min": 0, "axis_max": 1,
            "temperature_min_K": 800, "temperature_max_K": 1500,
            "seed_temperature_K": 1000,
        },
        "expected": {
            "phases": ["LIQUID", "FCC_A1", "FCC_A1_AUTO#2"],
            "invariant_temperatures_K": [1056.1],
            "invariant_tolerance_K": 2.0,
            "min_boundaries": 4,
        },
    },
    {
        "id": "J2_steel1_fe_c_diyagrami",
        "zorluk": "zor",
        "olcum": "Fe-C, kararli (grafit) sistem. UC degismez tepkime birden: "
                 "peritektik ~1768 K, otektik ~1427 K, otektoid ~1011 K. "
                 "Ucu de ders kitabi degeri, ve otektoid bu projede ayri "
                 "bir yontemle dogrulanmis durumda. Bir diyagramin ucunu "
                 "birden dogru bulmasi, tek bir sayiyi tutturmasindan cok "
                 "daha zor.",
        "soru": "steel1.TDB icin Fe-C faz diyagramini %0-25 karbon, "
                "500-2000 K araliginda ciz",
        "tool": "calculate_phase_diagram",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.98, "C": 0.02},
            "composition_basis": "mole_fraction",
            "axis_element": "C", "axis_min": 0, "axis_max": 0.25,
            "temperature_min_K": 500, "temperature_max_K": 2000,
        },
        "expected": {
            "phases": ["LIQUID", "BCC_A2", "FCC_A1", "GRAPHITE"],
            "invariant_temperatures_K": [1011.2, 1426.6, 1767.8],
            "invariant_tolerance_K": 2.0,
            "min_boundaries": 8,
        },
    },
    {
        "id": "J3_alni_diyagram_izlenemiyor",
        "zorluk": "zor",
        "olcum": "MAP bu motorun en kirilgan hesabi ve kendisi bunu her "
                 "kosumdan once yaziyor. Al-Ni'de, tek denge olarak temiz "
                 "cozulen bir tohumdan hicbir sinir izleyemiyor. Dogru "
                 "davranis basarmak degil, basaramadigini SOYLEMEK -- ve "
                 "yerine ne yapilabilecegini onermek, cunku MAP'in yedek "
                 "kademesi yok: bu motorda sinir izleyen baska bir sey "
                 "bulunmuyor.",
        "soru": "alni-4slx.TDB icin Al-Ni faz diyagramini ciz",
        "tool": "calculate_phase_diagram",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.5, "NI": 0.5},
            "composition_basis": "mole_fraction",
            "axis_element": "NI", "axis_min": 0, "axis_max": 1,
            "temperature_min_K": 600, "temperature_max_K": 2200,
        },
        "expected": {
            "rejected": True,
            "stage": "EXECUTION",
            "reason_contains": ["could not be traced", "isothermal section"],
        },
    },
]

DOGRU_HESAP = (A_TEK_FAZ + B_COK_FAZ + C_FAZ_GECISI + D_BILESIM_KUMESI
               + E_YARI_KARARLI + F_KARSILASTIRMA + G_CELIK_DISI
               + H_BILESIM_EKSENI + I_KATILASMA + J_FAZ_DIYAGRAMI)
# --- S · Ozetin kendisi ---------------------------------------------
#
# Buraya kadarki her vaka SAYININ dogru olup olmadigini soruyor. Bu grup
# ayri bir sey soruyor: sayi dogru geldiginde cagiran taraf ondan dogru
# CEVABI cikarabiliyor mu.
#
# Olculdu: cikarabilmiyor. 215 satirlik bir taramada 24 K genisligindeki
# delta-ferrit alani "yok" diye bildirildi; 19 satirlik bir kesitte
# x=0.19'daki baskinlik esigi x=0.26 diye bildirildi. Iki durumda da veri
# yukun icindeydi ve iki durumda da satirlar arasindan cikarilmasi
# gerekiyordu. Tek satirdan okunan hicbir deger yanlis cikmadi.
#
# Bu yuzden cikarim artik sunucuda, deterministik olarak yapiliyor
# (scan_summary.py) ve sonuca "scan_summary" olarak ekleniyor. Buradaki
# vakalar o alanin DOGRU cevabi verdigini sabitliyor -- ayrica her tarama
# vakasinda ozetin ham veriyle tutarliligi otomatik olarak sinaniyor
# (run.py, _ozet_tutarli).

DOGRU_RAPOR = [
    {
        "id": "S1_ozet_baskinlik_esigi",
        "zorluk": "orta",
        "olcum": "Ferrit hangi krom oraninda baskin hale geliyor. Ham "
                 "noktalarda cevap 12. satirda duruyor (BCC 0.524, FCC "
                 "0.476, x=0.1906) ve 19 satiri karsilastirmayi "
                 "gerektiriyor. Elle olculdugunde x=0.26 diye bildirilmisti "
                 "-- yedi puan sapma, ve esigin yanlis tarafina. Ozet bunu "
                 "artik hesaplayip veriyor; vaka verdigi degeri sabitliyor.",
        "soru": "steel1.TDB'de 1400 K'de Fe-%1C bazli alasimda krom "
                "artarken ferrit ne zaman baskin hale geliyor",
        "tool": "calculate_isothermal_section",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.89, "CR": 0.10, "C": 0.01},
            "composition_basis": "mole_fraction",
            "axis_element": "CR", "axis_min": 0.01, "axis_max": 0.30,
            "temperature_K": 1400, "n_points": 20,
        },
        "expected": {
            "phases": ["FCC_A1", "BCC_A2", "M23C6"],
            "summary_dominant_from": {"BCC_A2": 0.1906},
            # Bir eksen adimi 0.0156; tolerans onun biraz ustunde, cunku
            # esigin kendisi iki ornekleme noktasinin ARASINDA -- daha dar
            # bir tolerans olcum hassasiyetinin otesini iddia ederdi.
            "summary_dominant_tolerance": 0.02,
            "max_failed_fraction": 0.10,
        },
    },
    {
        "id": "S2_ozet_erime_araligi",
        "zorluk": "zor",
        "olcum": "Fe-%1C isitilirken erimenin nerede baslayip nerede "
                 "bittigi. Arada delta-ferrit + sivi alani var (~1767-1791 "
                 "K, BCC %71'e cikiyor) ama ornekleme araligi 17.3 K "
                 "oldugu icin tek satira dusuyor. Elle olculdugunde o tek "
                 "satir gozden kacti ve delta-ferrit 'bu veritabaninda "
                 "gorunmuyor' diye bildirildi. Ozet onu hem phases_seen'de "
                 "hem under_sampled'da isaretliyor: var, ama cozunurlugu "
                 "yetersiz -- inkar edilemez ve genisligi de iddia "
                 "edilemez.",
        "soru": "steel1.TDB'de Fe-%1C celigi 300 K'den 2000 K'ye "
                "isitilirken fazlar nasil degisir",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "composition_basis": "mole_fraction",
            "temperature_min_K": 300, "temperature_max_K": 2000,
            "n_points": 100,
        },
        "expected": {
            "phases": ["BCC_A2", "FCC_A1", "GRAPHITE", "LIQUID"],
            "phase_order": [("GRAPHITE", "FCC_A1"), ("FCC_A1", "LIQUID")],
            # Sistemin tamamen sivi oldugu yer. 1.15'te bu sayi "solidus"
            # diye etiketlenmisti; erimenin BITTIGI yer, basladigi yer
            # degil. Tolerans bir ornekleme adimindan (17.3 K) genis.
            "summary_dominant_from": {"LIQUID": 1792.0},
            "summary_dominant_tolerance": 25.0,
            "max_failed_fraction": 0.10,
        },
    },
]

CASES = DOGRU_HESAP + DOGRU_RED + DOGRU_RAPOR
