"""Ablation kosucusu: 18 hesaplama vakasi x 5 yapilandirma.

Her (mod, vaka) ikilisi AYRI bir surecte calisir. Gerekce: PREFLIGHT kapali
yapilandirmada motor segmentasyon hatasi verebiliyor; bu yakalanabilir bir
istisna degil, surecin oldurulmesi. Cikis kodu negatifse (sinyal) ya da
11 ise cokme olarak kaydedilir.

Kullanim:
    ablation_run.py                 # yapilandirma 1-4 (API cagrisi YOK)
    ablation_run.py full            # yalnizca 5. yapilandirma (API gerekir)
    ablation_run.py all             # hepsi
"""
import json
import os
import subprocess
import sys
import time

HERE = "/root/projects/oc-mcp"
WORKER = os.path.join(HERE, "ablation_worker.py")
PY = "/root/projects/ocvenv/bin/python"
OUT_JSON = os.path.join(HERE, "ablation_results.json")

# Gecersiz olmasi BEKLENEN istekler (PREFLIGHT yakalamali).
GECERSIZ = {6, 7, 8, 9, 10, 17}

CASES = [
    {"no": 3, "ad": "steel1 Fe-C 1000K", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.99, "C": 0.01},
                   "temperature_K": 1000}},
    {"no": 4, "ad": "steel1 Fe-C 1200K (OCASI yakinsamiyor)", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.99, "C": 0.01},
                   "temperature_K": 1200}},
    {"no": 5, "ad": "AlFe-4SLBF 1000K", "tool": "calculate_equilibrium",
     "arguments": {"database": "AlFe-4SLBF.TDB",
                   "elements_composition": {"AL": 0.2, "FE": 0.8},
                   "temperature_K": 1000}},
    {"no": 6, "ad": "GECERSIZ: olmayan element (NI)", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.9, "NI": 0.1},
                   "temperature_K": 1000}},
    {"no": 7, "ad": "GECERSIZ: tek element (Fe=1.0)", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 1.0},
                   "temperature_K": 1000}},
    {"no": 8, "ad": "GECERSIZ: ters sicaklik araligi", "tool": "calculate_property_diagram",
     "arguments": {"database": "agcu.TDB",
                   "elements_composition": {"AG": 0.6, "CU": 0.4},
                   "temperature_min_K": 1500, "temperature_max_K": 800}},
    {"no": 9, "ad": "GECERSIZ: negatif sicaklik", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.99, "C": 0.01},
                   "temperature_K": -500}},
    {"no": 10, "ad": "GECERSIZ: olmayan dosya", "tool": "calculate_equilibrium",
     "arguments": {"database": "olmayan_bir_dosya.TDB",
                   "elements_composition": {"FE": 0.9, "C": 0.1},
                   "temperature_K": 1000}},
    {"no": 11, "ad": "agcu property diagram 800-1400K", "tool": "calculate_property_diagram",
     "arguments": {"database": "agcu.TDB",
                   "elements_composition": {"AG": 0.6, "CU": 0.4},
                   "temperature_min_K": 800, "temperature_max_K": 1400}},
    {"no": 12, "ad": "steel1 property diagram 300-2000K", "tool": "calculate_property_diagram",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.99, "C": 0.01},
                   "temperature_min_K": 300, "temperature_max_K": 2000}},
    {"no": 13, "ad": "alni-4slx 800-1700K (yakinsama zorlugu)", "tool": "calculate_property_diagram",
     "arguments": {"database": "alni-4slx.TDB",
                   "elements_composition": {"AL": 0.75, "NI": 0.25},
                   "temperature_min_K": 800, "temperature_max_K": 1700}},
    {"no": 14, "ad": "steel7 6 element 1173K", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel7.TDB",
                   "elements_composition": {"C": 0.04, "CR": 0.06, "MO": 0.05,
                                            "SI": 0.003, "V": 0.01, "FE": 0.837},
                   "temperature_K": 1173}},
    {"no": 15, "ad": "compare_alloys Fe-C", "tool": "compare_alloys",
     "arguments": {"database": "steel1.TDB",
                   "composition_a": {"FE": 0.99, "C": 0.01},
                   "composition_b": {"FE": 0.95, "C": 0.05},
                   "temperature_K": 1000}},
    {"no": 16, "ad": "steel1 GRAPHITE askiya alinmis", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.99, "C": 0.01},
                   "temperature_K": 1000, "suspended_phases": ["GRAPHITE"]}},
    {"no": 17, "ad": "GECERSIZ: agcu'da olmayan faz (GRAPHITE)", "tool": "calculate_equilibrium",
     "arguments": {"database": "agcu.TDB",
                   "elements_composition": {"AG": 0.6, "CU": 0.4},
                   "temperature_K": 1000, "suspended_phases": ["GRAPHITE"]}},
    {"no": 18, "ad": "steel1 seyreltik (C=0.001)", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.999, "C": 0.001},
                   "temperature_K": 1000}},
    {"no": 19, "ad": "saf2507 super duplex 1200K", "tool": "calculate_equilibrium",
     "arguments": {"database": "saf2507.TDB",
                   "elements_composition": {"CR": 0.25, "FE": 0.627, "MN": 0.01,
                                            "MO": 0.04, "N": 0.003, "NI": 0.07},
                   "temperature_K": 1200}},
    {"no": 20, "ad": "steel1 1200K (seffaflik vakasi)", "tool": "calculate_equilibrium",
     "arguments": {"database": "steel1.TDB",
                   "elements_composition": {"FE": 0.99, "C": 0.01},
                   "temperature_K": 1200}},
]

ENV = dict(os.environ)
ENV["OC_BUILD_DIR"] = "/root/projects/opencalphad"
ENV["LD_LIBRARY_PATH"] = "/root/projects/opencalphad/.libs"
ENV["LD_PRELOAD"] = ("/root/projects/opencalphad/.libs/libOC.so.0:"
                     "/root/projects/opencalphad/.libs/libOPENCALPHAD.so.0")

# Katman B'nin NVIDIA anahtarina ihtiyaci var. run_server.sh bunu .env'den
# yukluyor; bu kosucu sunucu uzerinden gitmedigi icin ayni isi burada yapmak
# gerekiyor, yoksa "full" yapilandirmasi anahtar yok diye sessizce
# available=false doner ve olcum yapilandirma farkini degil eksik ortami
# olcer.
_ENV_FILE = os.path.join(HERE, ".env")
if os.path.isfile(_ENV_FILE):
    with open(_ENV_FILE) as _fh:
        for _line in _fh:
            _line = _line.strip()
            if not _line or _line.startswith("#") or "=" not in _line:
                continue
            _k, _v = _line.split("=", 1)
            ENV.setdefault(_k.strip(), _v.strip().strip('"').strip("'"))


def calistir(mod, case, timeout_s=300):
    t0 = time.time()
    try:
        p = subprocess.run(
            [PY, WORKER, mod, json.dumps(case, ensure_ascii=False)],
            capture_output=True, text=True, timeout=timeout_s, env=ENV, cwd=HERE,
        )
    except subprocess.TimeoutExpired:
        return {"mod": mod, "no": case["no"], "outcome": "timeout",
                "engine_touched": True, "runtime_s": timeout_s}

    rc = p.returncode
    if rc != 0:
        # Negatif kod = sinyal (SIGSEGV = -11). Bazi kabuklarda 139.
        crash = rc < 0 or rc in (11, 139, 134)
        return {"mod": mod, "no": case["no"],
                "outcome": "crash" if crash else "nonzero_exit",
                "engine_touched": True, "returncode": rc,
                "stderr_tail": (p.stderr or "")[-200:].replace("\n", " "),
                "runtime_s": round(time.time() - t0, 3)}

    for line in reversed((p.stdout or "").strip().splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {"mod": mod, "no": case["no"], "outcome": "no_output",
            "engine_touched": True, "runtime_s": round(time.time() - t0, 3)}


def main():
    arg = sys.argv[1] if len(sys.argv) > 1 else "local"
    if arg == "full":
        modlar = ["full"]
    elif arg == "all":
        modlar = ["bare", "preflight", "cascade", "layera", "full"]
    else:
        modlar = ["bare", "preflight", "cascade", "layera"]

    # Onceki sonuclari koru (full ayri kosulabilsin diye)
    tum = []
    if os.path.isfile(OUT_JSON):
        try:
            with open(OUT_JSON) as fh:
                tum = [r for r in json.load(fh) if r.get("mod") not in modlar]
        except Exception:
            tum = []

    for mod in modlar:
        print("=" * 78, flush=True)
        print(f"YAPILANDIRMA: {mod}", flush=True)
        print("=" * 78, flush=True)
        for case in CASES:
            r = calistir(mod, case)
            tum.append(r)
            oc = r.get("outcome", "?")
            extra = ""
            if oc == "computed":
                if r.get("gibbs_energy_J") is not None:
                    extra = f"  G={r['gibbs_energy_J']}"
                if r.get("n_points") is not None:
                    extra = f"  {r['n_points']} nokta ({r.get('n_failed_points',0)} basarisiz)"
                if r.get("layer_a_passed") is not None:
                    extra += f"  A={'gecti' if r['layer_a_passed'] else 'KALDI'}"
                if r.get("layer_b_passed") is not None:
                    extra += f"  B={r['layer_b_passed']}"
            elif oc == "crash":
                extra = f"  rc={r.get('returncode')}"
            elif oc == "engine_error":
                extra = f"  {str(r.get('error'))[:70]}"
            print(f"  [{case['no']:>2}] {case['ad'][:44]:<44} {oc:<19}"
                  f"{r.get('runtime_s','?'):>8}s{extra}", flush=True)
            with open(OUT_JSON, "w") as fh:
                json.dump(tum, fh, indent=2, ensure_ascii=False, default=str)
        print(flush=True)

    print(f"Kaydedildi: {OUT_JSON}  ({len(tum)} kayit)", flush=True)


if __name__ == "__main__":
    main()
