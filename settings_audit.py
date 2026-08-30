"""Are the settings and the code still saying the same thing?

Runs in both directions, which is the point. Every check written while
moving the rules asked one question -- are the settings correct? -- and
none asked the other one: is there anything left in the code that should
not be there. Dead rules do not change behaviour, so the differential
tests passed, correctly, three times over a body of nine rules that
nobody was calling and anybody could have edited to no effect.

Three failures of this shape in one day, all silent, all found by someone
asking rather than by anything running:

  - a wiring tracker that missed one call form and reported three live
    sections as unread
  - a patch that truncated a module above three helpers and removed them,
    while the schema test kept passing
  - the original rule bodies left standing above the wrappers that
    replaced them

None of these breaks anything. That is exactly what makes them expensive:
the code runs, the tests pass, and something has quietly stopped being
connected.

Exit code 1 if anything is off, so it can go in a run.
"""

import ast
import io
import os
import re
import sys
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, "settings")

# Sections that are documentation for a reader rather than values the code
# consumes. Listed by name so that a section going quiet by accident is not
# mistaken for one that was always meant to be quiet.
BEKLENEN_SESSIZ = {
    "reviewer_note",     # which model to reach for by hand, and why
    "conversion",        # conditions under which output may touch a number
    "honesty",           # invariants the code obeys; not switches
    "floor",             # what may never be turned off
    "report",            # units and inclusion flags, not yet implemented
    "policy",            # enforced by is_engine_failure, not read by key
    "signals",           # names for what the exception types already say
    "binary",            # engine preference, still a constant
}


def _kaynak():
    metinler = {}
    for kok, _, dosyalar in os.walk(HERE):
        # benchmark/ ve verification/ kendi "problems" listelerini kurar --
        # onlar olcut, kural degil.
        if any(p in kok for p in ("/logs", "/.git", "__pycache__",
                                  "/settings", "/benchmark", "/verification")):
            continue
        for d in dosyalar:
            if d.endswith(".py") and d != os.path.basename(__file__):
                yol = os.path.join(kok, d)
                metinler[yol] = io.open(yol, encoding="utf-8",
                                        errors="ignore").read()
    return metinler


def _okunuyor(anahtar, hepsi):
    a = re.escape(anahtar)
    kalip = (r'\["%s"\]' % a) + "|" + (r'get\("%s"' % a) + "|" \
        + (r'execution_setting\(\s*"%s"' % a) + "|" + (r'\.%s\b' % a)
    return bool(re.search(kalip, hepsi))


def yon_bir(hepsi):
    """Dosyadaki her bolumun kodda bir okuyucusu var mi?"""
    sorunlar = []
    for ad in ("input", "execution", "output"):
        d = tomllib.load(open(os.path.join(SETTINGS, ad + ".toml"), "rb"))
        for bolum in d:
            if bolum == "schema_version" or bolum in BEKLENEN_SESSIZ:
                continue
            if not _okunuyor(bolum, hepsi):
                sorunlar.append(
                    "%s.toml [%s] dosyada var, kodda okuyan yok" % (ad, bolum))
    return sorunlar


def yon_iki(metinler):
    """Kodda, ayar dosyalarina tasinmis olmasi gereken kural kalmis mi?

    Aranan sey bir desen degil, bir ISARET: hata mesaji ureten bir kural
    govdesi. Tasinmis bir kuralin kopyasi geride kalirsa burada gorunur.
    """
    sorunlar = []
    for yol, metin in metinler.items():
        ad = os.path.basename(yol)
        if ad in ("settings_engine.py", "result_check.py"):
            continue          # yuklemler burada yasar, mesajlar dosyadan gelir
        try:
            agac = ast.parse(metin)
        except SyntaxError:
            continue
        for node in ast.walk(agac):
            if (isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "append"
                    and isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "problems"):
                sorunlar.append(
                    "%s:%d kural govdesi kodda kalmis (problems.append)"
                    % (ad, node.lineno))
    return sorunlar


def yon_uc(metinler):
    """Yurutucunun disari actigi her sey gercekten cagriliyor mu?

    add_block.py'nin uc yardimciyi silmesi bu sekilde gorulurdu: fonksiyon
    kaybolur, cagiran kalir. Tersi de gecerli -- cagiran kaybolur, fonksiyon
    kalir, ve kimse fark etmez.
    """
    yol = os.path.join(HERE, "settings_engine.py")
    if not os.path.isfile(yol):
        return ["settings_engine.py yok"]
    agac = ast.parse(io.open(yol, encoding="utf-8").read())
    acilan = [n.name for n in agac.body
              if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    # Ic kullanim da sayilir: run_cascade'in tiers_for'u cagirmasi o
    # fonksiyonun bagli oldugunu gosterir. Aranan sey HIC cagrilmayan,
    # yani bir yamanin geride biraktigi fonksiyon.
    hepsi = "\n".join(metinler.values())
    kendi = io.open(yol, encoding="utf-8").read()
    sonuc = []
    for ad in acilan:
        disaridan = ("settings_engine.%s" % ad) in hepsi
        icerden = len(re.findall(r"\b%s\s*\(" % re.escape(ad), kendi)) > 1
        if not disaridan and not icerden:
            sonuc.append("settings_engine.%s() hicbir yerden cagrilmiyor" % ad)
    return sonuc


def main():
    metinler = _kaynak()
    hepsi = "\n".join(metinler.values())
    sorunlar = yon_bir(hepsi) + yon_iki(metinler) + yon_uc(metinler)
    if sorunlar:
        print("AYAR DENETIMI: %d sorun" % len(sorunlar))
        for s in sorunlar:
            print("   ", s)
        return 1
    print("AYAR DENETIMI: temiz -- dosya ile kod ayni seyi soyluyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
