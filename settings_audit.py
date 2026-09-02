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

# A section may declare `status`, and that is what says whether the code
# is expected to read it:
#
#   yok         wired, and read
#   "code"      never moving -- documentation here, the decision is code
#   "todo"      could move, has not
#   "planned"   not a move at all; something has to be written first
#
# Read from the files rather than kept as a list here. The list this
# replaces had to be edited by hand every time a section changed state,
# which is the same failure this whole module exists to catch: two places
# saying what should be said once.
TASINMAYACAK = {"code", "todo", "planned"}


def _durum(bolum_degeri):
    if isinstance(bolum_degeri, dict):
        return bolum_degeri.get("status")
    if isinstance(bolum_degeri, list) and bolum_degeri:
        ilk = bolum_degeri[0]
        if isinstance(ilk, dict):
            return ilk.get("status")
    return None


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
            if bolum == "schema_version":
                continue
            durum = _durum(d[bolum])
            if durum in TASINMAYACAK:
                continue          # neden okunmadigini kendisi soyluyor
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



def _cagri(modul, fonksiyon):
    """Bir fonksiyonun donusunu olcen deneme."""
    def olc():
        return getattr(__import__(modul), fonksiyon)()
    return olc


def _katman_a_esigi():
    """Yirmi noktanin biri hatali: %5. Esik 0.10'ken sessiz, 0.0'ken sikayet.

    Bu deneme oteki ikisinden farkli bir sey soruyor. Onlar bir okuyucunun
    dosyayi okuyup okumadigini soruyor; bu, Katman A'nin BUTUN zincirinin
    dosyadan geldigini: beyan output.toml'da, derleyici onu yuklemine
    bagliyor, ve yuklem kuralin esigini gercekten kullaniyor. Elde tutulan
    bir kontrol listesi ya da koda gomulmus bir esik buradan gecemez.
    """
    import result_check
    yuk = {"points": [{"temperature_K": 900.0 + i} for i in range(20)]}
    yuk["points"][0]["error"] = "olcum icin"
    _, bulunan = result_check.verify_result(yuk)
    return bool(bulunan)


DENEMELER = [
    ("semantic_check._max_tokens", "execution.toml",
     "max_tokens = 4000", "max_tokens = 1234",
     _cagri("semantic_check", "_max_tokens"), 1234, ("semantic_check",)),

    ("semantic_check._transient_http", "execution.toml",
     "transient_http = [429, 500, 502, 503, 504, 529]",
     "transient_http = [418]",
     _cagri("semantic_check", "_transient_http"), {418}, ("semantic_check",)),

    ("Katman A esigi", "output.toml",
     "max_failed_fraction = 0.10", "max_failed_fraction = 0.0",
     _katman_a_esigi, True, ("result_check",)),
]


def yon_dort():
    """Ayari okudugunu SANAN ama sessizce yedege dusen okuyucu var mi?

    Bir okuyucu genellikle soyle yazilir:

        try:
            import settings_engine
            return settings_engine.POLICY...
        except Exception:
            return default

    Import basarisiz olursa -- ornegin modul seviyesinde yoksa -- fonksiyon
    yedege duser ve HIC ses cikarmaz. Bugun iki tane vardi. Biri dogru
    GORUNUYORDU, cunku yedegi dosyadaki degerin aynisiydi: ayari hic
    okumadan dogru cevap veriyordu, ki bu en zor fark edilen tur.

    Iddiayi test etmenin tek yolu dosyayi degistirip cevabin degisip
    degismedigine bakmak. Degismiyorsa okumuyordur.
    """
    sorunlar = []
    dokunulan = {}

    def tazele(moduller):
        """Ayar okuyan her seyi unut, sonra yeniden yukle."""
        for m in tuple(moduller) + ("settings_engine",):
            sys.modules.pop(m, None)

    def olc(deneme):
        etiket, dosya, eski, yeni, cagir, beklenen, moduller = deneme
        yol = os.path.join(SETTINGS, dosya)
        if yol not in dokunulan:
            dokunulan[yol] = io.open(yol, encoding="utf-8").read()
        asil = dokunulan[yol]
        if eski not in asil:
            return ["%s: %r dosyada yok -- deneme kosulamadi" % (etiket, eski)]

        # ONCE: dosya el degmemis halde. Bu olculmezse hep ayni cevabi
        # donduren bir fonksiyon denemeden gecer.
        tazele(moduller)
        try:
            once = cagir()
        except Exception as exc:                         # noqa: BLE001
            return ["%s cagrilamadi (degistirmeden once): %s" % (etiket, exc)]

        io.open(yol, "w", encoding="utf-8").write(asil.replace(eski, yeni))
        tazele(moduller)
        try:
            sonra = cagir()
        except Exception as exc:                         # noqa: BLE001
            return ["%s cagrilamadi: %s" % (etiket, exc)]

        if once == sonra:
            return ["%s ayari OKUMUYOR: %s degistirildi, cevap %r olarak "
                    "AYNI kaldi -- sessizce yedege dusuyor"
                    % (etiket, dosya, once)]
        if sonra != beklenen:
            return ["%s dosyayi takip ediyor ama beklenmeyen deger: %r "
                    "beklenirken %r" % (etiket, beklenen, sonra)]
        return []

    try:
        for deneme in DENEMELER:
            sorunlar += olc(deneme)
    finally:
        for yol, asil in dokunulan.items():
            io.open(yol, "w", encoding="utf-8").write(asil)
        tazele(("semantic_check", "result_check"))
    return sorunlar

def main():
    metinler = _kaynak()
    hepsi = "\n".join(metinler.values())
    sorunlar = (yon_bir(hepsi) + yon_iki(metinler)
                + yon_uc(metinler) + yon_dort())
    if sorunlar:
        print("AYAR DENETIMI: %d sorun" % len(sorunlar))
        for s in sorunlar:
            print("   ", s)
        return 1
    print("AYAR DENETIMI: temiz -- dosya ile kod ayni seyi soyluyor")
    return 0


if __name__ == "__main__":
    sys.exit(main())
