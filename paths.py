# -*- coding: utf-8 -*-
"""Nerede ne var: kurulum yollari tek yerden.

Bu dosya bir kusurdan dogdu. Motorun yeri uc ayri modulde ayni satirla
yaziliydi -- oc_service, native_fallback, native_step -- ve ucu de bir
kisinin bilgisayarindaki klasoru gosteriyordu. Veritabanlarinin yeri de
oyleydi. Sonuc, baska bir makinede temiz acilan ve her istege "Database
not found" diyen bir sunucuydu.

Bir sabiti uc yere yazmanin bedeli, bu projede olculmus bir sey: birinde
duzeltilip otekilerde unutulmasi. O yuzden burasi tek tanim, ve
digerleri buradan okuyor.

Bagimlilik yok, bilerek: oc_service pyOC'yi ice aktarmadan ONCE motorun
yerini bilmek zorunda, yani bu modul hicbir seye ihtiyac duymamali.
"""
import glob
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def build_dir():
    """Derlenmis OpenCalphad nerede.

    OC_BUILD_DIR kazanir; run_server.sh onu veriyor ve sunucunun yolu
    oradan geciyor. Geri kalan her sey -- olcum scriptleri, ablation
    kosucusu, tek seferlik sondalar -- varsayilana dusuyordu, ve varsayilan
    tek bir makinede vardi.
    """
    acik = os.environ.get("OC_BUILD_DIR")
    if acik:
        return os.path.expanduser(acik)
    for aday in (os.path.join(HERE, os.pardir, "opencalphad"),
                 os.path.join(HERE, "opencalphad"),
                 os.path.join(os.path.expanduser("~"), "opencalphad")):
        if os.path.isdir(os.path.join(aday, ".libs")):
            return os.path.abspath(aday)
    return os.path.abspath(os.path.join(HERE, os.pardir, "opencalphad"))


def database_candidates():
    """TDB dosyalarinin olabilecegi yerler, denenme sirasiyla.

    Ortam meselesi, kural degil: bir yol makineden makineye degisir ve
    hakkinda aciklanacak bir sey yoktur, o yuzden ayar dosyalarina ait
    degil. Ama SIRA aciklanacak bir sey, ve hicbir yerde yoktu.

    Her giris (etiket, yol). Etiket tasiniyor ki bir basarisizlik neyin
    denendigini soyleyebilsin, yalnizca neyin bulunamadigini degil.
    """
    acik = os.environ.get("OC_DB_DIR")
    if acik:
        # Acikca verilmis, yani kesin kazanir ve bos oldugunda sessizce
        # atlanmaz. Yanlis yeri gosteren bir degisken bildirilmeye deger
        # bir hatadir; tahmine dusmek onu gizler ve cagirana secmedigi bir
        # veritabanindan cevap verir.
        return [("OC_DB_DIR", os.path.expanduser(acik))]

    adaylar = [("repo/databases", os.path.join(HERE, "databases")),
               ("OC_BUILD_DIR/macros", os.path.join(build_dir(), "macros")),
               ("~/OpenCalphad", os.path.join(os.path.expanduser("~"),
                                              "OpenCalphad", "OC6", "macros"))]
    # Windows kurulumunun koydugu yer, bir isim icin degil kim
    # calistiriyorsa onun icin. Tek bir hesap adini yazmak, bu modulun
    # ortadan kaldirmak icin var oldugu hatanin ta kendisi.
    for yol in sorted(glob.glob(
            "/mnt/c/Users/*/Documents/OpenCalphad/OC6/macros")):
        adaylar.append(("WSL/Windows", yol))
    return adaylar


def _has_tdb(yol):
    return bool(glob.glob(os.path.join(yol, "*.TDB"))
                or glob.glob(os.path.join(yol, "*.tdb")))


def resolve_database_dir():
    """(klasor, rapor). Rapor neyin denendigini ve nerede durdugunu soyler.

    Bir aday VAR OLMAKLA kalmayip veritabani ICERMELI. Yoksa rastgele var
    olan bos bir klasor, listenin asagisindaki dolu olani golgeler ve
    basarisizlik yanlis klasor yerine eksik dosya gibi gorunur.
    """
    denenen = []
    for etiket, yol in database_candidates():
        var = os.path.isdir(yol)
        dolu = var and _has_tdb(yol)
        denenen.append({"source": etiket, "path": yol,
                        "exists": var, "has_databases": dolu})
        if dolu or etiket == "OC_DB_DIR":
            return yol, {"chosen": yol if dolu else None,
                         "chosen_source": etiket, "tried": denenen}
    _, ilk = database_candidates()[0]
    return ilk, {"chosen": None, "chosen_source": None, "tried": denenen}


def missing_database_message(rapor):
    """Hicbir veritabani bulunamadiginda yazilacak metin."""
    return ("oc-mcp: no TDB databases found. Looked in:\n"
            + "".join("  %-22s %s%s\n"
                      % (a["source"], a["path"],
                         "" if a["exists"] else "  (no such directory)")
                      for a in rapor["tried"])
            + "  Set OC_DB_DIR to the directory holding your .TDB files, or\n"
              "  put them in %s\n" % os.path.join(HERE, "databases"))
