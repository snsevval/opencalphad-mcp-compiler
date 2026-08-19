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

  1 DOGRU_HESAP  (45)  dogru sayiyi uretiyor mu?      motor + Katman A
  2 DOGRU_RED    (25)  yapmamasi gerekeni reddediyor  PREFLIGHT
                       mu?
  3 DOGRU_RAPOR  (30)  gercekte ne oldugunu soyluyor  Katman A/B + anlati
                       mu?

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
            "temperature_K": 1000,
        },
        "expected": {
            "rejected": True,
            "stage": "PREFLIGHT",
            "reason_contains": ["sum to"],
        },
    },
]


# Kategori 1 (DOGRU_HESAP, 45) ve 3 (DOGRU_RAPOR, 30) sirada.
DOGRU_HESAP = []
DOGRU_RAPOR = []

CASES = DOGRU_HESAP + DOGRU_RED + DOGRU_RAPOR
