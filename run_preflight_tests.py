"""Soru 6-10: PREFLIGHT senaryolarini gercek MCP protokolu uzerinden calistir.

Bu bes senaryoda dil modeli hic devrede degil -- PREFLIGHT, motor
calismadan once deterministik kod olarak kosuyor. Dolayisiyla NVIDIA
kapasitesinden bagimsiz olarak calistirilabilirler.
"""
import json
import sys
import time

sys.path.insert(0, "/root/projects/oc-mcp")
from verification import executor

CASES = [
    {
        "no": 6,
        "baslik": "Veritabaninda olmayan element (NI)",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.9, "NI": 0.1},
            "temperature_K": 1000,
        },
        "beklenen": "PREFLIGHT reddi: NI steel1.TDB'de tanimli degil",
    },
    {
        "no": 7,
        "baslik": "Tek elementli bilesim",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 1.0},
            "temperature_K": 1000,
        },
        "beklenen": "PREFLIGHT reddi: en az iki element gerekli",
    },
    {
        "no": 8,
        "baslik": "Ters sicaklik araligi (1500 -> 800)",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "temperature_min_K": 1500,
            "temperature_max_K": 800,
        },
        "beklenen": "PREFLIGHT reddi: T_min < T_max olmali",
    },
    {
        "no": 9,
        "baslik": "Negatif sicaklik (-500 K)",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "temperature_K": -500,
        },
        "beklenen": "PREFLIGHT reddi: sicaklik pozitif olmali",
    },
    {
        "no": 10,
        "baslik": "Var olmayan veritabani dosyasi",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "olmayan_bir_dosya.TDB",
            "elements_composition": {"FE": 0.9, "C": 0.1},
            "temperature_K": 1000,
        },
        "beklenen": "PREFLIGHT reddi: database not found",
    },
]


def main():
    sonuclar = []
    for case in CASES:
        print("=" * 72, flush=True)
        print(f"SORU {case['no']} -- {case['baslik']}", flush=True)
        print(f"  arac  : {case['tool']}", flush=True)
        print(f"  girdi : {json.dumps(case['arguments'], ensure_ascii=False)}", flush=True)
        print(f"  beklenen: {case['beklenen']}", flush=True)

        t0 = time.time()
        try:
            result = executor.execute(case, timeout_s=120)
            hata = None
        except Exception as exc:
            result = None
            hata = f"{type(exc).__name__}: {exc}"
        sure = time.time() - t0

        print(f"  SURE  : {sure:.3f} s", flush=True)
        if hata:
            print(f"  ISTISNA: {hata}", flush=True)
            stage = None
            msg = hata
        else:
            stage = result.get("stage")
            msg = result.get("error")
            print(f"  stage : {stage}", flush=True)
            print(f"  error : {msg}", flush=True)
            probs = result.get("problems")
            if probs:
                for p in probs:
                    print(f"     - {p}", flush=True)
            # Motorun hic calismadigini kanitla: bu alanlar OLMAMALI
            for alan in ("backend_used", "gibbs_energy_J", "phase_molar_amounts"):
                if alan in result:
                    print(f"  !! BEKLENMEYEN ALAN: {alan} = {result[alan]!r}", flush=True)

        gecti = (stage == "PREFLIGHT")
        print(f"  DURUM : {'GECTI' if gecti else 'INCELE'}", flush=True)
        sonuclar.append({
            "no": case["no"],
            "baslik": case["baslik"],
            "sure_s": round(sure, 3),
            "stage": stage,
            "error": msg,
            "gecti": gecti,
        })
        print(flush=True)

    print("=" * 72, flush=True)
    print("OZET", flush=True)
    print("=" * 72, flush=True)
    print(f"{'#':<4}{'sure(s)':<10}{'stage':<12}{'durum':<8}baslik", flush=True)
    for s in sonuclar:
        print(f"{s['no']:<4}{s['sure_s']:<10}{str(s['stage']):<12}"
              f"{'GECTI' if s['gecti'] else 'INCELE':<8}{s['baslik']}", flush=True)
    gecen = sum(1 for s in sonuclar if s["gecti"])
    print(f"\nSONUC: {gecen}/{len(sonuclar)} PREFLIGHT'ta yakalandi", flush=True)

    with open("/root/projects/oc-mcp/preflight_test_sonuc.json", "w") as fh:
        json.dump(sonuclar, fh, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
