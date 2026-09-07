# -*- coding: utf-8 -*-
"""Yirmi referansi olculen degerlerle karsilastirir, iki sutunlu.

Okuma ARALIK dondurur, tek sayi degil. Sebep: sonlu adimli bir tarama
gecisin yerini ancak iki ornekleme noktasi arasinda bilir. Gozlenen ilk
tam-sivi noktasi araligin UST ucudur; onu tek sayi gibi sunmak butun
sapmalari sistematik olarak yukari kaydirir ve olcumun tasimadigi bir
kesinlik iddia eder.
"""
import json
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, os.path.join(ROOT, "benchmark"))
import referans as R                                      # noqa: E402

YUK = json.load(open(os.path.join(ROOT, "referans_olcum20.json")))


def sivi_dususu(y):
    """Isitirken sivi orani azaliyor mu? Fizik hayir diyor."""
    pts = [p for p in (y.get("points") or [])
           if isinstance(p, dict) and p.get("phase_molar_amounts")
           and p.get("temperature_K") is not None]
    if len(pts) < 2:
        return []

    def sv(p):
        return sum(v for k, v in p["phase_molar_amounts"].items()
                   if str(k).upper().startswith("LIQUID") and v is not None)
    s = sorted(pts, key=lambda p: p["temperature_K"])
    return [(a["temperature_K"], sv(a), a.get("source"),
             b["temperature_K"], sv(b), b.get("source"))
            for a, b in zip(s, s[1:]) if sv(a) - sv(b) > 1e-3]


def oku(ref, y):
    tur = ref["oku"][0]
    ozet = y.get("scan_summary") or {}

    if tur in ("ilk_sivi", "tam_sivi"):
        erime = ozet.get("melting")
        if not erime:
            return None, "taramada sivi gorulmedi"
        alan = "first_liquid" if tur == "ilk_sivi" else "fully_liquid"
        bilgi = erime.get(alan)
        if not bilgi:
            return None, "%s yok" % alan
        a = bilgi.get("boundary_between")
        return (tuple(a) if a else bilgi["observed_at"]), None

    if tur in ("baskin_gecis", "ilk_kati_gecis"):
        _, nereden, nereye = ref["oku"]
        bolgeler = ozet.get("dominant_phase_regions") or []
        for a, b in zip(bolgeler, bolgeler[1:]):
            if a.get("phase") == nereden and b.get("phase") == nereye:
                return (a["to"], b["from"]), None
        gorulen = [b.get("phase") for b in bolgeler]
        return None, "%s -> %s yok (baskin sira: %s)" % (nereden, nereye,
                                                         gorulen)
    return None, "bilinmeyen okuma turu"


def kars(hedef, olculen, tol):
    if olculen is None:
        return "-", None
    if isinstance(olculen, tuple):
        alt, ust = olculen
        if alt <= hedef <= ust:
            return "ICINDE", 0.0
        sapma = (alt - hedef) if hedef < alt else (ust - hedef)
        return ("TAMAM" if abs(sapma) <= tol else "SAPMA"), sapma
    sapma = olculen - hedef
    return ("TAMAM" if abs(sapma) <= tol else "SAPMA"), sapma


def bicim(v):
    if v is None:
        return "-"
    if isinstance(v, tuple):
        return "%.2f..%.2f" % v
    return "%.2f" % v


tutarsiz = {a: sivi_dususu(y) for a, y in YUK.items()}
tutarsiz = {a: d for a, d in tutarsiz.items() if d}

print("%-22s %-26s %9s %-17s %8s %-8s | %9s %8s %s"
      % ("id", "nokta", "DOSYA", "bizim", "sapma", "durum",
         "ITS-90", "sapma", "durum"))
print("-" * 132)

sayim = {}
for ref in R.REFERANSLAR:
    y = YUK.get(ref["kosum"]) or {}
    if "error" in y:
        print("%-22s %-26s  HATA %s" % (ref["id"], ref["nokta"][:26],
                                        str(y["error"])[:50]))
        sayim["HATA"] = sayim.get("HATA", 0) + 1
        continue
    deger, notu = oku(ref, y)
    d1, s1 = kars(ref["referans_K"], deger, ref["tolerans_K"])
    if ref["kosum"] in tutarsiz:
        d1, s1 = "SUPHELI", None

    ikinci = ""
    if "ikinci_referans_K" in ref:
        d2, s2 = kars(ref["ikinci_referans_K"], deger, ref["tolerans_K"])
        ikinci = "| %9.3f %8s %-8s" % (
            ref["ikinci_referans_K"],
            ("%+.3f" % s2) if s2 is not None else "-", d2)
    else:
        ikinci = "|      --          (ITS-90 kapsami disi)"

    print("%-22s %-26s %9.2f %-17s %8s %-8s %s"
          % (ref["id"], ref["nokta"][:26], ref["referans_K"], bicim(deger),
             ("%+.3f" % s1) if s1 is not None else "-", d1, ikinci))
    if notu:
        print("%-22s    ! %s" % ("", notu))
    sayim[d1] = sayim.get(d1, 0) + 1

print("-" * 132)
print("DOSYA sutunu:  " + "   ".join("%s %d" % kv
                                     for kv in sorted(sayim.items())))
if tutarsiz:
    print("\nFIZIKSEL TUTARSIZLIK:")
    for ad, d in tutarsiz.items():
        for t1, s1, k1, t2, s2, k2 in d:
            print("  %-18s %9.3f sivi=%.4f [%s] -> %9.3f sivi=%.4f [%s]"
                  % (ad, t1, s1, k1, t2, s2, k2))
