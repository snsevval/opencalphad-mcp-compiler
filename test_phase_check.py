"""Faz adi PREFLIGHT kontrolunun testi (gercek MCP protokolu uzerinden).

Uc durum:
  1. Olmayan faz  -> REDDEDILMELI, gercek faz listesi mesajda olmali
  2. Var olan faz -> GECMELI, hesap normal calismali
  3. #2 ekli faz  -> GECMELI (bilesim kumesi eki temizlenmeli)

Ayrica regresyon: faz verilmeyen normal bir istek etkilenmemeli.
"""
import json
import sys
import time

sys.path.insert(0, "/root/projects/oc-mcp")
from verification import executor

CASES = [
    {
        "ad": "1. Olmayan faz (agcu'da GRAPHITE yok)",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "temperature_K": 1000,
            "suspended_phases": ["GRAPHITE"],
        },
        "bekle_red": True,
    },
    {
        "ad": "2. Var olan faz (steel1'de GRAPHITE var)",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "temperature_K": 1000,
            "suspended_phases": ["GRAPHITE"],
        },
        "bekle_red": False,
    },
    {
        "ad": "3. Bilesim kumesi ekli (#1 temizlenmeli)",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "temperature_K": 1000,
            "suspended_phases": ["FCC_A1#1"],
        },
        "bekle_red": False,
    },
    {
        "ad": "4. REGRESYON: faz verilmeden normal hesap",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "temperature_K": 1000,
        },
        "bekle_red": False,
    },
]


def main():
    ok = 0
    for case in CASES:
        print("=" * 72, flush=True)
        print(case["ad"], flush=True)
        print("  girdi: " + json.dumps(case["arguments"], ensure_ascii=False), flush=True)
        t0 = time.time()
        try:
            r = executor.execute(case, timeout_s=120)
            hata = None
        except Exception as exc:
            r, hata = None, f"{type(exc).__name__}: {exc}"
        sure = time.time() - t0

        if hata:
            print(f"  ISTISNA: {hata}", flush=True)
            print("  DURUM: HATA", flush=True)
            continue

        stage = r.get("stage")
        reddedildi = (stage == "PREFLIGHT")
        print(f"  sure : {sure:.2f}s", flush=True)
        print(f"  stage: {stage}", flush=True)
        if reddedildi:
            print(f"  error: {r.get('error')}", flush=True)
        else:
            print(f"  backend: {r.get('backend_used')}", flush=True)
            print(f"  G      : {r.get('gibbs_energy_J')}", flush=True)
            print(f"  fazlar : {list((r.get('phase_molar_amounts') or {}).keys())}", flush=True)

        gecti = (reddedildi == case["bekle_red"])
        print(f"  DURUM: {'GECTI' if gecti else 'BASARISIZ'}", flush=True)
        ok += 1 if gecti else 0
        print(flush=True)

    print("=" * 72, flush=True)
    print(f"SONUC: {ok}/{len(CASES)}", flush=True)
    return 0 if ok == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
