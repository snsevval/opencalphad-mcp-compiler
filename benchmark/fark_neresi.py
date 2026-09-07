# -*- coding: utf-8 -*-
"""Iki kayit arasindaki fark TAM OLARAK hangi alanlarda?

"55 vaka farkli" yeterli degil. Beklenen degisiklik yuke tek bir alan
eklemekti; farkin baska bir yere de dokunmadigini gostermek gerekiyor,
yoksa beklenen degisiklik beklenmeyen birini gizler.

Yol: iki yuku ic ice gezip farkli olan her YOLU topla. Sonra yollarin
kumesine bak -- hepsi ayni tek alansa degisiklik kapsanmis demektir.
"""
import collections
import io
import json
import sys

DEGISKEN = {"timings_ms", "stage_ms", "elapsed_ms", "chart_path",
            "interactive_window_opened"}


def sil(d):
    if isinstance(d, dict):
        return {k: sil(v) for k, v in d.items() if k not in DEGISKEN}
    if isinstance(d, list):
        return [sil(x) for x in d]
    return d


def oku(yol):
    kayit = {}
    for satir in io.open(yol, encoding="utf-8"):
        satir = satir.strip()
        if not satir:
            continue
        d = json.loads(satir)
        anahtar = (d.get("tool"),
                   json.dumps(d.get("arguments"), sort_keys=True, default=str))
        kayit[anahtar] = sil(d.get("result"))
    return kayit


def yollar(a, b, kok=""):
    """Iki yapinin farkli oldugu yollari dondurur."""
    if type(a) is not type(b):
        return [kok + " <tur>"]
    if isinstance(a, dict):
        cikan = []
        for k in set(a) | set(b):
            yeni = "%s.%s" % (kok, k)
            if k not in a:
                cikan.append(yeni + " <sonradan eklendi>")
            elif k not in b:
                cikan.append(yeni + " <kaldirildi>")
            else:
                cikan += yollar(a[k], b[k], yeni)
        return cikan
    if isinstance(a, list):
        if len(a) != len(b):
            return [kok + " <uzunluk %d->%d>" % (len(a), len(b))]
        cikan = []
        for i, (x, y) in enumerate(zip(a, b)):
            cikan += yollar(x, y, "%s[%d]" % (kok, i))
        return cikan
    return [] if a == b else [kok]


once, sonra = oku(sys.argv[1]), oku(sys.argv[2])
ortak = set(once) & set(sonra)
sayac = collections.Counter()
ornek = {}
farkli = 0
for k in ortak:
    f = yollar(once[k], sonra[k])
    if not f:
        continue
    farkli += 1
    for y in f:
        sayac[y] += 1
        ornek.setdefault(y, k)

print("ortak %d vaka, %d tanesi farkli" % (len(ortak), farkli))
print()
print("%-6s  %s" % ("kac", "yol"))
print("-" * 70)
for yol, n in sayac.most_common(40):
    print("%-6d  %s" % (n, yol))
if len(sayac) > 40:
    print("... %d yol daha" % (len(sayac) - 40))

# Beklenen tek degisiklik: verification.checked eklenmesi
beklenen = {y for y in sayac if y.endswith(".checked <sonradan eklendi>")}
digerleri = set(sayac) - beklenen
print()
if digerleri:
    print("BEKLENMEYEN %d yol:" % len(digerleri))
    for y in sorted(digerleri)[:20]:
        print("   %-58s ornek: %s" % (y, ornek[y][0]))
else:
    print("Butun farklar tek bir alandan: verification.checked eklendi.")
