"""Docstring degisikliginin uc araca da temiz uygulandigini dogrular."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server  # noqa: E402

ESKI_IZLER = ("Suggesting a corrected request", "report the rejection")
ARACLAR = ("calculate_equilibrium", "compare_alloys", "calculate_property_diagram")

ok = True
for ad in ARACLAR:
    d = getattr(server, ad).__doc__ or ""
    yeni = "PREFLIGHT REJECTION" in d
    eski = any(iz in d for iz in ESKI_IZLER)
    print(f"=== {ad}")
    print(f"    STOP RULE eklendi : {yeni}")
    print(f"    eski metin kaldi  : {eski}")
    ok = ok and yeni and not eski

print()
print("SONUC:", "TAMAM" if ok else "EKSIK")
sys.exit(0 if ok else 1)
