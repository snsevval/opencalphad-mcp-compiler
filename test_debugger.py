"""DEBUGGER testi: siniflandirma + dongu kapanmasi.

Sinifllandirma birimi gercek gozlenmis basarisizlik sekilleriyle sinaniyor
(hepsi bu projede canli olarak goruldu). Dongu kapanmasi ise gercek MCP
protokolu uzerinden.
"""
import json
import sys

sys.path.insert(0, "/root/projects/oc-mcp")
import failure_classify as fc  # noqa: E402

VAKALAR = [
    ("PREFLIGHT reddi",
     {"stage": "PREFLIGHT", "error": "Request rejected...",
      "problems": ["Element(s) ['NI'] not declared in steel1.TDB"]},
     fc.PREFLIGHT, False),

    ("Kapsama yetersiz (alni-4slx, gercek vaka)",
     {"verification": {"stage": "VERIFY_A", "passed": False,
                       "problems": ["3 of 15 temperature points failed to converge (20%)"]}},
     fc.COVERAGE, False),

    ("Bozuk sonuc: faz toplami 1 degil",
     {"verification": {"stage": "VERIFY_A", "passed": False,
                       "problems": ["phase fractions sum to 1.26, not 1.0"]}},
     fc.MALFORMED, False),

    ("Bozuk sonuc: NaN",
     {"verification": {"stage": "VERIFY_A", "passed": False,
                       "problems": ["phase 'LIQUID' is NaN"]}},
     fc.MALFORMED, False),

    ("Yakinsama hatasi",
     {"verification": {"stage": "VERIFY_A", "passed": False,
                       "problems": ["Result carries an error: Equilibrium did not converge (error code 4204)"]}},
     fc.CONVERGENCE, False),

    ("Katman B itirazi",
     {"verification": {"stage": "VERIFY_A+B", "passed": False,
                       "problems": ["Bağımsız model denetimi sonucu makul bulmadı: ..."],
                       "layer_b": {"available": True, "passed": False,
                                   "model_used": "deepseek-ai/deepseek-v4-flash"}}},
     fc.SEMANTIC, False),

    ("Degerlendirici karari okunamadi (gercek vaka)",
     {"verification": {"stage": "VERIFY_A+B", "passed": True, "problems": [],
                       "layer_b": {"available": True, "passed": None,
                                   "model_used": "nvidia/nemotron-3-super-120b-a12b",
                                   "reason": "Model cevabından net bir SONUC okunamadı"}}},
     fc.REVIEWER_UNREADABLE, True),

    ("Degerlendiriciye ulasilamadi",
     {"verification": {"stage": "VERIFY_A", "passed": True, "problems": [],
                       "layer_b": {"available": False,
                                   "reason": "model erişilemedi: HTTP 529"}}},
     fc.REVIEWER_UNREACHABLE, True),

    ("Basarili sonuc -> siniflandirma YOK",
     {"verification": {"stage": "VERIFY_A+B", "passed": True, "problems": [],
                       "layer_b": {"available": True, "passed": True,
                                   "model_used": "deepseek-ai/deepseek-v4-flash"}}},
     None, None),
]

print("=" * 78)
print("1. SINIFLANDIRMA")
print("=" * 78)
ok = 0
for ad, sonuc, beklenen_kat, beklenen_retry in VAKALAR:
    f = fc.classify(sonuc)
    kat = f["category"] if f else None
    retry = f["retryable"] if f else None
    gecti = (kat == beklenen_kat) and (retry == beklenen_retry)
    ok += 1 if gecti else 0
    print(f"[{'GECTI' if gecti else 'BASARISIZ'}] {ad}")
    print(f"          kategori={kat}  retryable={retry}"
          f"  (beklenen: {beklenen_kat} / {beklenen_retry})")
    if f and f.get("strategy"):
        print(f"          strateji={f['strategy']}")
print(f"\nSINIFLANDIRMA: {ok}/{len(VAKALAR)}")

# ---- 2. Dongu kapanmasi: gercek MCP protokolu ----------------------
print()
print("=" * 78)
print("2. DONGU KAPANMASI (gercek MCP protokolu)")
print("=" * 78)
from verification import executor  # noqa: E402

case = {
    "tool": "calculate_equilibrium",
    "arguments": {"database": "steel1.TDB",
                  "elements_composition": {"FE": 0.99, "C": 0.01},
                  "temperature_K": 1200},
}
r = executor.execute(case, timeout_s=180)
ver = r.get("verification", {})
print(f"  backend_used : {r.get('backend_used')}")
print(f"  stage        : {ver.get('stage')}")
print(f"  passed       : {ver.get('passed')}")
lb = ver.get("layer_b") or {}
print(f"  Katman B     : available={lb.get('available')} passed={lb.get('passed')}"
      f" model={lb.get('model_used')}")
print(f"  failure alani: {json.dumps(r.get('failure'), ensure_ascii=False)}")
print(f"  debugger     : {json.dumps(ver.get('debugger'), ensure_ascii=False)[:300]}")

saglikli = (ver.get("passed") is True) and (r.get("failure") is None)
print(f"\n  DURUM: {'GECTI — saglikli sonucta debugger devreye girmedi' if saglikli else 'INCELE'}")

sys.exit(0 if ok == len(VAKALAR) and saglikli else 1)
