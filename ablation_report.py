"""Ablation sonuclarindan ozet tablo + results.csv uretir.

Makaledeki her sayi bu betigin ciktisindan gelecek; el ile yazilan rakam
olmayacak.
"""
import csv
import json
import os
from collections import defaultdict

HERE = "/root/projects/oc-mcp"
IN_JSON = os.path.join(HERE, "ablation_results.json")
OUT_CSV = os.path.join(HERE, "results.csv")

MODLAR = ["bare", "preflight", "cascade", "layera", "full"]
MOD_AD = {
    "bare": "Temel (yalniz OCASI)",
    "preflight": "+ PREFLIGHT",
    "cascade": "+ Kademeli motor",
    "layera": "+ Katman A",
    "full": "+ Katman B (tam sistem)",
}
GECERSIZ = {6, 7, 8, 9, 10, 17}

with open(IN_JSON) as fh:
    kayitlar = json.load(fh)

byv = defaultdict(dict)
for r in kayitlar:
    byv[r["mod"]][r["no"]] = r

tum_no = sorted({r["no"] for r in kayitlar})
gecerli = [n for n in tum_no if n not in GECERSIZ]
gecersiz = [n for n in tum_no if n in GECERSIZ]

print("=" * 92)
print("ABLATION OZETI")
print(f"  gecerli vaka: {len(gecerli)}   hatali vaka: {len(gecersiz)}   toplam: {len(tum_no)}")
print("=" * 92)
print(f"{'Yapilandirma':<26}{'Gecerli cozuldu':<18}{'Hatali yakalandi':<20}"
      f"{'Cokme':<8}{'Ort. sure (s)':<14}")
print("-" * 92)

ozet = []
for mod in MODLAR:
    d = byv.get(mod, {})
    if not d:
        continue
    cozuldu = sum(1 for n in gecerli
                  if d.get(n, {}).get("outcome") == "computed")
    yakalandi = sum(1 for n in gecersiz
                    if d.get(n, {}).get("outcome") == "preflight_rejected")
    cokme = sum(1 for n in tum_no
                if d.get(n, {}).get("outcome") in ("crash", "timeout"))
    sureler = [d[n].get("runtime_s", 0) for n in tum_no if n in d]
    ort = sum(sureler) / len(sureler) if sureler else 0
    print(f"{MOD_AD[mod]:<26}{f'{cozuldu}/{len(gecerli)}':<18}"
          f"{f'{yakalandi}/{len(gecersiz)}':<20}{cokme:<8}{ort:<14.2f}")
    ozet.append((mod, cozuldu, yakalandi, cokme, ort))

# Katman B ayrintisi
print()
print("KATMAN B (tam sistem) AYRINTISI")
print("-" * 92)
d = byv.get("full", {})
modeller = defaultdict(int)
kararlar = defaultdict(int)
for n in gecerli:
    r = d.get(n, {})
    if r.get("outcome") != "computed":
        continue
    m = r.get("layer_b_model") or "(yok)"
    modeller[m] += 1
    p = r.get("layer_b_passed")
    kararlar["gecti" if p is True else ("kaldi" if p is False else "okunamadi")] += 1
for m, c in sorted(modeller.items(), key=lambda x: -x[1]):
    print(f"  {m:<44} {c} hesap")
print(f"  kararlar: {dict(kararlar)}")

# Kademe kullanimi
print()
print("MOTOR KADEMESI KULLANIMI (tam sistem)")
print("-" * 92)
kademe = defaultdict(int)
for n in gecerli:
    r = d.get(n, {})
    if r.get("outcome") == "computed":
        kademe[r.get("backend_used") or "(bilinmiyor)"] += 1
for k, c in sorted(kademe.items(), key=lambda x: -x[1]):
    print(f"  {k:<44} {c} hesap")

# ---- results.csv --------------------------------------------------
alanlar = ["case", "gecerli_mi", "yapilandirma", "outcome", "backend_used",
           "gibbs_energy_J", "n_points", "n_failed_points",
           "layer_a_passed", "layer_b_passed", "layer_b_model", "runtime_s"]
with open(OUT_CSV, "w", newline="") as fh:
    w = csv.DictWriter(fh, fieldnames=alanlar)
    w.writeheader()
    for mod in MODLAR:
        for n in tum_no:
            r = byv.get(mod, {}).get(n)
            if not r:
                continue
            w.writerow({
                "case": n,
                "gecerli_mi": "hayir" if n in GECERSIZ else "evet",
                "yapilandirma": mod,
                "outcome": r.get("outcome"),
                "backend_used": r.get("backend_used"),
                "gibbs_energy_J": r.get("gibbs_energy_J"),
                "n_points": r.get("n_points"),
                "n_failed_points": r.get("n_failed_points"),
                "layer_a_passed": r.get("layer_a_passed"),
                "layer_b_passed": r.get("layer_b_passed"),
                "layer_b_model": r.get("layer_b_model"),
                "runtime_s": r.get("runtime_s"),
            })

print()
print(f"results.csv yazildi: {OUT_CSV}  ({len(kayitlar)} satir)")
