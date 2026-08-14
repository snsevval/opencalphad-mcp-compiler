"""Ag-Cu STEP + gap-fill kosusunu yeniden calistirip iki cikti kaydeder:

  agcu_combined.csv   makale sekli icin uzun-format veri (T, phase, fraction, source)
  agcu_gnuplot.png    sistemin kendi urettigi gnuplot grafigi

Cikti Windows masaustune yazilir; boylece kullanici dogrudan kullanabilir.
"""
import csv
import os
import sys

sys.path.insert(0, "/root/projects/oc-mcp")

import native_step

DB = "/mnt/c/Users/sevval/Documents/OpenCalphad/OC6/macros/agcu.TDB"
COMP = {"AG": 0.6, "CU": 0.4}
T_MIN, T_MAX, N_POINTS = 800.0, 1400.0, 15
PRESSURE = 100000.0

OUT_DIR = "/mnt/c/Users/sevval/Desktop"
CSV_PATH = os.path.join(OUT_DIR, "agcu_combined.csv")
PNG_PATH = os.path.join(OUT_DIR, "agcu_gnuplot.png")


def main():
    if not os.path.isfile(DB):
        print(f"HATA: veritabani yok: {DB}")
        return 1

    print(f"Kosuluyor: agcu, Ag 0.6 / Cu 0.4, {T_MIN:.0f}-{T_MAX:.0f} K ...",
          flush=True)
    combined, gap_filled = native_step.build_combined_series(
        DB, COMP, T_MIN, T_MAX, N_POINTS, PRESSURE)

    gap_set = {round(float(t), 4) for t in gap_filled}
    print(f"  toplam nokta : {len(combined)}", flush=True)
    print(f"  gap-fill     : {len(gap_set)}", flush=True)

    # Uzun format: her (sicaklik, faz) ikilisi bir satir. Sekil kodunun
    # pivotlamasi bu bicimden yapiliyor.
    rows = 0
    phases = set()
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["T", "phase", "fraction", "source"])
        for temperature, fractions, source in combined:
            src = source
            if src not in ("step", "gapfill"):
                # build_combined_series bazi surumlerde farkli etiket koyuyor;
                # gap_filled listesi kesin kaynak.
                src = "gapfill" if round(float(temperature), 4) in gap_set else "step"
            for name, value in sorted(fractions.items()):
                phases.add(name)
                w.writerow([f"{float(temperature):.4f}", name,
                            f"{float(value):.9f}", src])
                rows += 1

    print(f"\nCSV yazildi : {CSV_PATH}  ({rows} satir)", flush=True)
    print(f"  fazlar    : {sorted(phases)}", flush=True)

    try:
        native_step.render_gnuplot_png(
            combined, "Ag-Cu  (Ag 0.6 / Cu 0.4)", PNG_PATH)
        boyut = os.path.getsize(PNG_PATH) // 1024
        print(f"PNG yazildi : {PNG_PATH}  ({boyut} KB)", flush=True)
    except Exception as exc:
        print(f"PNG uretilemedi: {type(exc).__name__}: {exc}", flush=True)

    # Makaledeki dogrulanmis degerlerle hizli tutarlilik kontrolu.
    print("\n--- referans kontrolu (Tablo 7) ---", flush=True)
    beklenen = {850: 0.734371, 900: 0.739091, 950: 0.744818,
                1000: 0.751819, 1050: 0.760506}
    for temperature, fractions, _ in combined:
        t_yuvarlak = int(round(float(temperature)))
        if t_yuvarlak in beklenen and abs(float(temperature) - t_yuvarlak) < 0.6:
            for name, value in fractions.items():
                if name.startswith("FCC_A1#1") or name == "FCC_A1":
                    fark = abs(value - beklenen[t_yuvarlak])
                    print(f"  {t_yuvarlak} K  hesap={value:.6f}  "
                          f"makale={beklenen[t_yuvarlak]:.6f}  fark={fark:.2e}",
                          flush=True)
                    break
    return 0


if __name__ == "__main__":
    sys.exit(main())
