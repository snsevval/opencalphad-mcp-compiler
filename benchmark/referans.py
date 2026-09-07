# -*- coding: utf-8 -*-
"""Referans tablosu: yirmi soru, hepsi birincil kaynaktan.

Kiyaslama dosyasi (cases.py) baska bir sey soruyor. Orada gecme olcutleri
kutle korunumu, stokiyometri, ozet-ham veri tutarliligi -- hepsi sonucun
KENDI ICINDEN dogrulanabilen seyler, ve bu bilincli bir tercih: "sistemin
kendi ciktisini kendine referans yapmak hicbir sey olcmeyen bir test
uretir."

Ama tercih bir bosluk birakiyor. Kutlesi korunan, toplami bir olan, ozeti
tutarli bir sonuc yine de YANLIS SICAKLIKTA olabilir. Olculdu: 88 vakada
"reference", "literature", "melting_K", "transition_K" hic gecmiyor.

Burasi o bosluk.

BIRINCIL KAYNAK NE DEMEK

Sayinin ilk cikti�i belge. Baskasinin aktardigi yer degil. Uc sinif var ve
her satir hangisinden geldigini soyluyor:

  ITS-90        Sicaklik olceginin kendisini tanimlayan resmi metin.
                Indirildi, acildi, tablosu okundu. Bu degerler
                tartisilmaz -- olcegin tanimi.

  dosya-kirilma Motorun okudugu TDB dosyasinin kendi icinden. SGTE
                fonksiyonlari erime noktasinda ikiye bolunur, yani
                dosya erime noktasini kendi yaziyor. Aktarma degil,
                girdinin ta kendisi.

  dosya-beyani  TDB dosyasinin yorum satirlarinda acikca yazilmis deger,
                makale kunyesiyle birlikte. iron4cd.TDB hangi
                degerlendirmeyi uyguladigini ve o degerlendirmeden cikan
                degismez sicakliklari yaziyor.

IKI REFERANS SUTUNU NEDEN GEREKIYOR

Olculdu ve bir satiri bastan yaziyor: agcu.TDB gumus icin 1235.08,
ITS-90 1234.93 diyor. Once "+0.04 sapma" diye kaydedilmisti, sanki bizim
sapmamizmis gibi. Degil -- dosyanin kendi sayisini dogru uretiyoruz,
dosya ITS-90'dan 0.15 K sapiyor.

  dosyanin beyani  ->  BIZI olcer      boru hatti dosyadaki sayiyi uretiyor mu
  ITS-90 / makale  ->  DOSYAYI olcer   dosya gercekle uyusuyor mu

Ikisini tek sutunda toplamak, iki farkli sorunun cevabini birbirine
karistirmak olurdu.

SAF ELEMENT NEDEN SEYRELTIK

Motor tek elementli istegi reddediyor (R3) ve hakli: makro bir bagimli
element istiyor. Bilesim 0.9999/0.0001 -- saf degil ama saf metale
yeterince yakin. Kaymanin kendisi de sonucta gorunur, cunku iki fazli bir
alan acilir ve okuma bir ARALIK olarak doner. Orta noktasini alip tek sayi
gibi sunmak olcumun tasimadigi bir kesinlik iddia etmek olurdu.
"""


def C(derece):
    """Santigrattan Kelvine. ITS-90 degerleri Celsius olarak yazili."""
    return derece + 273.15


# Kaynak kunyeleri tek yerde: ayni kunye alti satirda tekrar ediyor ve
# birinde duzeltilip otekilerde unutulmasi tam olarak bu projenin
# defalarca yakaladigi ariza sinifi.
KAYNAKLAR = {
    "ITS90": (
        "H. Preston-Thomas, 'The International Temperature Scale of 1990 "
        "(ITS-90)', Metrologia, 27, 3-10 (1990). Tablo 1, tanimlayici "
        "sabit noktalar. Belge indirildi ve okundu."),
    "GUSTAFSON85": (
        "P. Gustafson, Scand. J. Metall., 14, 259-67 (1985); sementit "
        "10Hal ile guncellenmis. Degerler iron4cd.TDB'nin Fe-C blogunda "
        "yorum olarak yazili."),
    "SGTE91": (
        "A.T. Dinsdale, 'SGTE Data for Pure Elements', Calphad, 15(4), "
        "317-425 (1991). Deger dogrudan kosulan TDB dosyasinin GHSER "
        "fonksiyonundaki sicaklik kirilmasindan okundu."),
}


REFERANSLAR = [

    # ================================================================
    # A - SAF ELEMENT ERIMESI, CIFT REFERANSLI
    # ================================================================
    # Bu alti satirin ikisi birden var: dosyanin kendi kirilma noktasi ve
    # ITS-90'in tanimlayici degeri. Ikisi ayrildigi anda sapmanin kime ait
    # oldugu da ayrilmis oluyor.
    {
        "id": "al_erime_cost",
        "sistem": "saf Al (cost507R)",
        "nokta": "erime",
        "referans_K": 933.47,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERAL kirilmasi: ... ; 933.60 Y ... ; 2900 N  "
                  "(kati ifadesi 933.47'de kesiliyor)",
        "kaynak": KAYNAKLAR["SGTE91"],
        "ikinci_referans_K": C(660.323),
        "ikinci_sinif": "ITS-90",
        "ikinci_kaynak": KAYNAKLAR["ITS90"] + " Aluminyum donma noktasi "
                                              "660.323 C.",
        "tolerans_K": 2.0,
        "oku": ("tam_sivi",),
        "kosum": "al_cost",
    },
    {
        "id": "cu_erime_cost",
        "sistem": "saf Cu (cost507R)",
        "nokta": "erime",
        "referans_K": 1357.77,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERCU kirilmasi 1357.77",
        "kaynak": KAYNAKLAR["SGTE91"],
        "ikinci_referans_K": 1357.77,
        "ikinci_sinif": "ITS-90",
        "ikinci_kaynak": KAYNAKLAR["ITS90"] + " T90(Cu) = 1357.77 K.",
        "tolerans_K": 2.0,
        "oku": ("tam_sivi",),
        "kosum": "cu_cost",
        "not": "Dosya ile ITS-90 burada AYNI sayiyi veriyor. Ayni elementin "
               "agcu.TDB'deki degeri 1358.02 -- ayni element, iki dosya, "
               "iki sayi. Karsilastirma bunu gorunur kiliyor.",
    },
    {
        "id": "ag_erime_agcu",
        "sistem": "saf Ag (agcu)",
        "nokta": "erime",
        "referans_K": 1235.08,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERAG kirilmasi 1235.08",
        "kaynak": "agcu.TDB dosyasinin kendi GHSERAG fonksiyonu. SGTE-1991 "
                  "degeri degil: bu dosya daha eski bir parametrelemeden "
                  "geliyor (basligi 'From database: SSOL2').",
        "ikinci_referans_K": 1234.93,
        "ikinci_sinif": "ITS-90",
        "ikinci_kaynak": KAYNAKLAR["ITS90"] + " T90(Ag) = 1234.93 K.",
        "tolerans_K": 2.0,
        "oku": ("tam_sivi",),
        "kosum": "ag_agcu",
        "not": "Bu satir tablonun iki sutunlu olmasinin sebebi. Tek sutunla "
               "olculdugunde '+0.04 sapma' diye kaydedilmisti, sanki bizim "
               "sapmamizmis gibi. Dosyanin kendi sayisini dogru "
               "uretiyoruz; dosya ITS-90'dan 0.15 K sapiyor.",
    },
    {
        "id": "cu_erime_agcu",
        "sistem": "saf Cu (agcu)",
        "nokta": "erime",
        "referans_K": 1358.02,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERCU kirilmasi 1358.02 (agcu.TDB icinde)",
        "kaynak": "agcu.TDB dosyasinin kendi GHSERCU fonksiyonu.",
        "ikinci_referans_K": 1357.77,
        "ikinci_sinif": "ITS-90",
        "ikinci_kaynak": KAYNAKLAR["ITS90"] + " T90(Cu) = 1357.77 K.",
        "tolerans_K": 2.0,
        "oku": ("tam_sivi",),
        "kosum": "cu_agcu",
    },
    {
        "id": "zn_erime_cost",
        "sistem": "saf Zn (cost507R)",
        "nokta": "erime",
        "referans_K": 692.68,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERZN kirilmasi 692.68",
        "kaynak": KAYNAKLAR["SGTE91"],
        "ikinci_referans_K": C(419.527),
        "ikinci_sinif": "ITS-90",
        "ikinci_kaynak": KAYNAKLAR["ITS90"] + " Cinko donma noktasi "
                                              "419.527 C.",
        "tolerans_K": 2.0,
        "oku": ("tam_sivi",),
        "kosum": "zn_cost",
    },
    {
        "id": "sn_erime_cost",
        "sistem": "saf Sn (cost507R)",
        "nokta": "erime",
        "referans_K": 505.08,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERSN kirilmasi 505.08",
        "kaynak": KAYNAKLAR["SGTE91"],
        "ikinci_referans_K": C(231.928),
        "ikinci_sinif": "ITS-90",
        "ikinci_kaynak": KAYNAKLAR["ITS90"] + " Kalay donma noktasi "
                                              "231.928 C.",
        "tolerans_K": 2.0,
        "oku": ("tam_sivi",),
        "kosum": "sn_cost",
    },

    # ================================================================
    # B - SAF ELEMENT, ITS-90 KAPSAMI DISI
    # ================================================================
    # ITS-90 yalnizca yedi metali sabit nokta olarak tanimliyor. Bunlar o
    # listede degil, ama dosyanin kendi kirilmasi yine birincil: motorun
    # okudugu sayi bu.
    {
        "id": "fe_erime",
        "sistem": "saf Fe (steel1)",
        "nokta": "erime",
        "referans_K": 1811.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERFE kirilmasi 1811.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 3.0,
        "oku": ("tam_sivi",),
        "kosum": "fe_steel1",
    },
    {
        "id": "ni_erime",
        "sistem": "saf Ni (cost507R)",
        "nokta": "erime",
        "referans_K": 1728.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERNI kirilmasi 1728.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 3.0,
        "oku": ("tam_sivi",),
        "kosum": "ni_cost",
    },
    {
        "id": "si_erime",
        "sistem": "saf Si (cost507R)",
        "nokta": "erime",
        "referans_K": 1687.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERSI kirilmasi 1687.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 3.0,
        "oku": ("tam_sivi",),
        "kosum": "si_cost",
    },
    {
        "id": "mg_erime",
        "sistem": "saf Mg (cost507R)",
        "nokta": "erime",
        "referans_K": 923.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERMG kirilmasi 923.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 3.0,
        "oku": ("tam_sivi",),
        "kosum": "mg_cost",
    },
    {
        "id": "mn_erime",
        "sistem": "saf Mn (cost507R)",
        "nokta": "erime",
        "referans_K": 1519.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERMN kirilmasi 1519.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 3.0,
        "oku": ("tam_sivi",),
        "kosum": "mn_cost",
    },

    # ================================================================
    # C - KATI HAL DONUSUMU
    # ================================================================
    {
        "id": "ti_alfa_beta",
        "sistem": "saf Ti (cost507R)",
        "nokta": "alfa (HCP) -> beta (BCC)",
        "referans_K": 1155.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERTI kirilmalari 900.00 / 1155.00 / 1941.00; "
                  "1155 allotropik donusum, 1941 erime",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 5.0,
        "oku": ("baskin_gecis", "HCP_A3", "BCC_A2"),
        "kosum": "ti_cost",
        "not": "Erimeyen tek satir. Sivi hic olusmuyor, olculen sey iki "
               "kati fazin yer degistirdigi yer -- yani okuma yolu da "
               "digerlerinden farkli ve o yolu da sinamis oluyor.",
    },
    {
        "id": "ti_erime",
        "sistem": "saf Ti (cost507R)",
        "nokta": "erime",
        "referans_K": 1941.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERTI kirilmasi 1941.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 4.0,
        "oku": ("tam_sivi",),
        "kosum": "ti_erime_cost",
    },
    {
        "id": "cr_erime",
        "sistem": "saf Cr (steel1)",
        "nokta": "erime",
        "referans_K": 2180.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERCR kirilmasi 2180.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 4.0,
        "oku": ("tam_sivi",),
        "kosum": "cr_steel1",
    },
    {
        "id": "zr_erime",
        "sistem": "saf Zr (cost507R)",
        "nokta": "erime",
        "referans_K": 2128.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERZR kirilmasi 2128.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 4.0,
        "oku": ("tam_sivi",),
        "kosum": "zr_cost",
    },
    {
        "id": "v_erime",
        "sistem": "saf V (cost507R)",
        "nokta": "erime",
        "referans_K": 2183.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERV kirilmalari 790.00 / 2183.00; 2183 erime",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 4.0,
        "oku": ("tam_sivi",),
        "kosum": "v_cost",
    },
    {
        "id": "mo_erime",
        "sistem": "saf Mo (steel1)",
        "nokta": "erime",
        "referans_K": 2896.00,
        "sinif": "dosya-kirilma",
        "alinti": "GHSERMO kirilmasi 2896.00",
        "kaynak": KAYNAKLAR["SGTE91"],
        "tolerans_K": 5.0,
        "oku": ("tam_sivi",),
        "kosum": "mo_steel1",
        "not": "Tablodaki en yuksek sicaklik. Motorun ust ucta da calistigini "
               "sinar; TEMP-LIM 6000 K, yani sinirin cok altinda.",
    },

    # ================================================================
    # D - Fe-C YARI KARARLI (sementit) SISTEM
    # ================================================================
    # Ders kitabindaki tanidik Fe-Fe3C diyagrami budur ve steel1.TDB'de
    # HESAPLANAMAZ: o dosyada sementit yok, grafit var. iron4cd.TDB'de
    # ikisi de var, ve dosya kendi talimatini yaziyor:
    #
    #   "If you suspend the GRAPHITE to calculate equilibria with CEMENTITE,
    #    you should also suspend DIAMOND. Otherwise DIAMOND may become more
    #    stable than CEMENTITE at low temperature."
    #
    # Yani bu uc satir ayni zamanda faz askiya alma yolunu da siniyor --
    # ve o yolun kademeli motorda yedegi olmadigi kayitli (E4).
    {
        "id": "fec_otektoid_sementit",
        "sistem": "Fe-C yari kararli (sementit)",
        "nokta": "otektoid  gamma -> alfa + sementit",
        "referans_K": 999.68,
        "sinif": "dosya-beyani",
        "alinti": "$ The eutectoid (bcc+fcc+cem) temperature changed from "
                  "999.78 to 999.68 K.",
        "kaynak": KAYNAKLAR["GUSTAFSON85"],
        "tolerans_K": 3.0,
        "oku": ("ilk_kati_gecis", "FCC_A1", "BCC_A2"),
        "kosum": "fec_otektoid_cem",
    },
    {
        "id": "fec_otektik_sementit",
        "sistem": "Fe-C yari kararli (sementit)",
        "nokta": "otektik  L -> gamma + sementit",
        "referans_K": 1421.31,
        "sinif": "dosya-beyani",
        "alinti": "$ The eutectic (fcc+liq+cem) temperature changed from "
                  "1421.51 to 1421.31 K.",
        "kaynak": KAYNAKLAR["GUSTAFSON85"],
        "tolerans_K": 3.0,
        "oku": ("ilk_sivi",),
        "kosum": "fec_otektik_cem",
        "not": "Dosya makaledeki yuvarlamayi da yaziyor: 'a rounding error "
               "in the paper of the temperature of the FCC + LIQ + CEM "
               "equilibrium (1421 K in the paper, 1421.51 K calculated)'. "
               "Karsilastirma dosyanin guncel degerine yapiliyor.",
    },
    {
        "id": "sementit_erime",
        "sistem": "Fe-C yari kararli (sementit)",
        "nokta": "sementit kongruent erimesi",
        "referans_K": 1497.1,
        "sinif": "dosya-beyani",
        "alinti": "$ The congruent melting point of cementite changed from "
                  "1497.8 to 1497.1 K.",
        "kaynak": KAYNAKLAR["GUSTAFSON85"],
        "tolerans_K": 4.0,
        "oku": ("ilk_sivi",),
        "kosum": "sementit_erime",
        "not": "Sementit Fe3C, yani x(C) = 0.25 -- bilesim formulden "
               "geliyor, olcumden degil.",
    },
]


# ====================================================================
# KOSUMLAR: her referansin hangi cagriyla olculdugu
# ====================================================================
#
# Tablodan ayri, cunku bir cagri birden fazla referansi besleyebiliyor ve
# ayni cagriyi iki kez kosmak hem iki kat surer hem iki ayri sonuc
# uretebilirdi -- o zaman iki satirin ayni hesaptan geldigi artik iddia
# edilemezdi.
#
# Sicaklik araliklari referansin +/- 32 K cevresi, 150 nokta: adim ~0.43 K.
# Daha genis bir aralik ayni nokta sayisiyla daha kaba bir okuma verirdi
# ve okunan degerin belirsizligi toleransi asardi. Aralik referansa gore
# secilmis olmasi bir sorun degil: olculen sey degerin NEREDE oldugu degil,
# ORADA olup olmadigi.

def _cevre(merkez, yari=32.0):
    return round(merkez - yari, 2), round(merkez + yari, 2)


def _saf(veritabani, element, ikinci, merkez, yari=32.0, n=150,
         askili=None):
    """Seyreltik ikili: element 0.9999, ikinci 0.0001."""
    alt, ust = _cevre(merkez, yari)
    args = {
        "database": veritabani,
        "elements_composition": {element: 0.9999, ikinci: 0.0001},
        "composition_basis": "mole_fraction",
        "temperature_min_K": alt,
        "temperature_max_K": ust,
        "n_points": n,
    }
    if askili:
        args["suspended_phases"] = askili
    return ("calculate_property_diagram", args)


# Grafit VE elmas birlikte askiya aliniyor. Ikincisi tahmin degil,
# iron4cd.TDB'nin kendi talimati:
#   "If you suspend the GRAPHITE to calculate equilibria with CEMENTITE,
#    you should also suspend DIAMOND. Otherwise DIAMOND may become more
#    stable than CEMENTITE at low temperature."
YARI_KARARLI = ["GRAPHITE_A9", "DIAMOND_A4"]


def _fec(x_karbon, merkez, yari=32.0, n=150):
    alt, ust = _cevre(merkez, yari)
    return ("calculate_property_diagram", {
        "database": "iron4cd.TDB",
        "elements_composition": {"FE": round(1 - x_karbon, 4),
                                 "C": x_karbon},
        "composition_basis": "mole_fraction",
        "suspended_phases": YARI_KARARLI,
        "temperature_min_K": alt,
        "temperature_max_K": ust,
        "n_points": n,
    })


KOSUMLAR = {
    # A - cift referansli saf elementler
    "al_cost":  _saf("cost507R.TDB", "AL", "CU", 933.47),
    "cu_cost":  _saf("cost507R.TDB", "CU", "AL", 1357.77),
    "ag_agcu":  _saf("agcu.TDB",     "AG", "CU", 1235.08),
    "cu_agcu":  _saf("agcu.TDB",     "CU", "AG", 1358.02),
    "zn_cost":  _saf("cost507R.TDB", "ZN", "AL", 692.68),
    "sn_cost":  _saf("cost507R.TDB", "SN", "AL", 505.08),

    # B - ITS-90 kapsami disi
    "fe_steel1": _saf("steel1.TDB",   "FE", "C",  1811.00),
    "ni_cost":   _saf("cost507R.TDB", "NI", "AL", 1728.00),
    "si_cost":   _saf("cost507R.TDB", "SI", "AL", 1687.00),
    "mg_cost":   _saf("cost507R.TDB", "MG", "AL", 923.00),
    "mn_cost":   _saf("cost507R.TDB", "MN", "AL", 1519.00),

    # C - donusum ve yuksek sicaklik
    "ti_cost":       _saf("cost507R.TDB", "TI", "AL", 1155.00),
    "ti_erime_cost": _saf("cost507R.TDB", "TI", "AL", 1941.00),
    "cr_steel1":     _saf("steel1.TDB",   "CR", "FE", 2180.00),
    "zr_cost":       _saf("cost507R.TDB", "ZR", "AL", 2128.00),
    "v_cost":        _saf("cost507R.TDB", "V",  "AL", 2183.00),
    "mo_steel1":     _saf("steel1.TDB",   "MO", "FE", 2896.00),

    # D - Fe-C yari kararli
    # Bilesimler formulden: otektoid 0.76 agirlikca % C, otektik 4.3, ve
    # sementit Fe3C yani tam olarak x(C)=0.25. Ilk ikisi mol kesrine
    # cevrildi (12.011 ve 55.845 ile), ucuncusu zaten mol kesri.
    "fec_otektoid_cem": _fec(0.0344,  999.68),
    "fec_otektik_cem":  _fec(0.1728, 1421.31),
    "sementit_erime":   _fec(0.2500, 1497.10),
}
