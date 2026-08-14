"""Katman C yeniden tasarimi: resim, cizildigi veriyle uyusuyor mu?

Uc test:
  1  DOGRU grafik              -> gecmeli
  2  y ekseni otomatik olcekli -> kalmali
  3  bir seri hic cizilmemis   -> kalmali

Bozuk grafikler uydurulmuyor, gercek kusur siniflari yeniden uretiliyor.

Test 2 icin veri secimi onemli: tam Ag-Cu araliginda LIQUID zaten 0'dan
1'e ciktigi icin gnuplot'un otomatik olcegi de [0,1] verir ve ortada
yakalanacak bir fark kalmaz. Kusurun asil ciktigi durum, hicbir fazin
0'a inmedigi bir veri parcasidir -- otektik altindaki iki FCC fazi
(~0.73 ve ~0.27) tam olarak boyle bir parca.
"""
import base64
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, "/root/projects/oc-mcp")
sys.path.insert(0, "/root/projects/oc-mcp/verification")

import native_step
import validator

DB = "/mnt/c/Users/sevval/Documents/OpenCalphad/OC6/macros/agcu.TDB"
COMP = {"AG": 0.6, "CU": 0.4}
T_MIN, T_MAX, N_POINTS, PRESSURE = 800.0, 1400.0, 15, 100000.0


def render_raw(combined, output_png, fixed_yrange=True, drop_series=None):
    """Grafigi elle ciz; kusur siniflarini tek tek uretebilmek icin.

    fixed_yrange=False  -> `set yrange [0:1]` yazilmaz, otomatik olcek
    drop_series="AD"    -> o seri veriye ragmen hic cizilmez
    """
    phase_names = []
    for _, fractions, _ in combined:
        for name in fractions:
            if name not in phase_names:
                phase_names.append(name)
    drawn = [n for n in phase_names if n != drop_series]

    with tempfile.TemporaryDirectory() as tmpdir:
        data_path = os.path.join(tmpdir, "d.csv")
        with open(data_path, "w") as fh:
            fh.write("T," + ",".join(phase_names) + "\n")
            for temperature, fractions, _ in combined:
                row = [f"{temperature:.4f}"]
                row += [f"{fractions.get(n, float('nan')):.9f}" for n in phase_names]
                fh.write(",".join(row) + "\n")

        plot_terms = [
            f'"{data_path}" using 1:{phase_names.index(n) + 2} '
            f'with linespoints title "{n}"'
            for n in drawn
        ]
        lines = [
            'set terminal pngcairo size 1400,850 font "Arial,14" noenhanced',
            f'set output "{output_png}"',
            'set title "Ag-Cu  (Ag 0.6 / Cu 0.4)"',
            'set xlabel "Temperature (K)"',
            'set ylabel "Phase fraction"',
            'set datafile separator ","',
            'set key outside right',
            'set grid',
        ]
        if fixed_yrange:
            lines.append('set yrange [0:1]')
        lines.append("plot " + ", \\\n     ".join(plot_terms))
        script = "\n".join(lines)
        script_path = os.path.join(tmpdir, "p.plt")
        with open(script_path, "w") as fh:
            fh.write(script + "\n")
        subprocess.run(["gnuplot", script_path], check=True, timeout=30)


def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")


def rapor(baslik, sonuc, beklenen_gecti):
    print(f"\n{'=' * 78}\n{baslik}\n{'=' * 78}")
    if sonuc is None:
        print("  ATLANDI (grafik veya veri yok)")
        return False
    print(f"  karar   : {'GECTI' if sonuc.passed else 'KALDI'}")
    print(f"  gerekce : {sonuc.reason}")
    okuma = (sonuc.details or {}).get("reading")
    if okuma:
        print("  modelin okudugu:")
        for k, v in okuma.items():
            print(f"      {k:8s} = {v}")
    dogru = sonuc.passed == beklenen_gecti
    print(f"  BEKLENEN: {'GECTI' if beklenen_gecti else 'KALDI'}   "
          f"-> {'DOGRU' if dogru else 'YANLIS'}")
    return dogru


def main():
    if not validator.NVIDIA_API_KEY:
        print("HATA: NVIDIA_API_KEY yok")
        return 1

    print("Hesap calisiyor: agcu, Ag 0.6 / Cu 0.4, 800-1400 K ...", flush=True)
    combined, _ = native_step.build_combined_series(
        DB, COMP, T_MIN, T_MAX, N_POINTS, PRESSURE)

    points = [
        {"temperature_K": T, "phase_molar_amounts": fr, "source": src}
        for T, fr, src in combined
    ]
    print(f"  {len(points)} nokta, fazlar: "
          f"{sorted(validator.chart_ground_truth({'points': points})['legend'])}",
          flush=True)

    # Otektik altindaki parca: yalnizca iki FCC fazi, hicbiri 0'a inmiyor.
    # Otomatik olcek burada [0,1]'den belirgin sekilde sapar.
    alt = [
        (T, {k: v for k, v in fr.items() if k.startswith("FCC")}, src)
        for T, fr, src in combined if T < 1050.0
    ]
    alt = [(T, fr, src) for T, fr, src in alt if fr]
    alt_vals = [v for _, fr, _ in alt for v in fr.values()]
    print(f"  alt parca: {len(alt)} nokta, deger araligi "
          f"{min(alt_vals):.3f} - {max(alt_vals):.3f}", flush=True)
    alt_points = [
        {"temperature_K": T, "phase_molar_amounts": fr, "source": src}
        for T, fr, src in alt
    ]

    tmp = tempfile.mkdtemp()
    p_dogru = os.path.join(tmp, "1_dogru.png")
    p_yekseni = os.path.join(tmp, "2_yekseni.png")
    p_eksik = os.path.join(tmp, "3_eksik_seri.png")

    native_step.render_gnuplot_png(combined, "Ag-Cu  (Ag 0.6 / Cu 0.4)", p_dogru)
    render_raw(alt, p_yekseni, fixed_yrange=False)
    render_raw(combined, p_eksik, drop_series="LIQUID")
    print("  uc grafik uretildi\n", flush=True)

    basari = 0

    sonuc = validator.verify_layer_c(
        {}, {"points": points, "_chart_png_base64": b64(p_dogru)})
    basari += rapor("TEST 1 -- DOGRU GRAFIK", sonuc, True)

    sonuc = validator.verify_layer_c(
        {}, {"points": alt_points, "_chart_png_base64": b64(p_yekseni)})
    basari += rapor("TEST 2 -- Y EKSENI OTOMATIK OLCEKLI "
                    "(veri 0'a inmiyor, kod [0,1] bekliyor)", sonuc, False)

    sonuc = validator.verify_layer_c(
        {}, {"points": points, "_chart_png_base64": b64(p_eksik)})
    basari += rapor("TEST 3 -- LIQUID SERISI HIC CIZILMEMIS "
                    "(veride var, resimde yok)", sonuc, False)

    # Erisilemezlik bir itiraz degildir. Model bulunamadiginda dogru bir
    # grafik "kusurlu" diye isaretlenmemeli; katman yalnizca "bakamadim"
    # demeli ve karara katilmamali.
    vaka = {"tool": "calculate_property_diagram", "arguments": {},
            "expected": {}}
    sonuc_verisi = {"points": points, "_chart_png_base64": b64(p_dogru)}

    gercek_modeller = validator.VISION_MODELS
    gercek_bayrak = validator.VISION_CHECK_ENABLED

    # Referans: Katman C hic calismadan verilen karar.
    validator.VISION_CHECK_ENABLED = False
    try:
        katmansiz = validator.verify(vaka, sonuc_verisi)
    finally:
        validator.VISION_CHECK_ENABLED = gercek_bayrak

    # Ayni istek, Katman C acik ama modele ulasilamiyor.
    validator.VISION_MODELS = ["yok/boyle-bir-model-yok"]
    try:
        sonuc = validator.verify_layer_c({}, sonuc_verisi)
        erisilemez = validator.verify(vaka, sonuc_verisi)
    finally:
        validator.VISION_MODELS = gercek_modeller

    print(f"\n{'=' * 78}\nTEST 4 -- MODEL ERISILEMEZ\n{'=' * 78}")
    print(f"  available            : {sonuc.available}   (False olmali)")
    print(f"  gerekce              : {sonuc.reason[:80]}")
    print(f"  Katman C kapaliyken  : passed={katmansiz.passed} layer={katmansiz.layer}")
    print(f"  model erisilemezken  : passed={erisilemez.passed} layer={erisilemez.layer}")
    dogru4 = (
        sonuc.available is False
        and erisilemez.passed == katmansiz.passed
        and "C" not in erisilemez.layer
    )
    print(f"  karar degismedi mi   : {erisilemez.passed == katmansiz.passed}")
    print(f"  -> {'DOGRU' if dogru4 else 'YANLIS'}")
    basari += dogru4

    print(f"\n{'=' * 78}\nSONUC: {basari}/4\n{'=' * 78}")
    print(f"grafikler: {tmp}")
    return 0 if basari == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
