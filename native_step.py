"""Native OpenCalphad STEP + gnuplot backend for calculate_property_diagram.

Runs OpenCalphad's own continuation-based STEP algorithm (via the native
./OC command-line binary) instead of recomputing every temperature from
scratch in Python -- this is what OpenCalphad's own CAE GUI does, and its
generated macro (captured in tests/fixtures/step_diagram/, produced by
OpenCalphad CAE 0.1.0) is the template generate_step_macro follows.

Known, confirmed limitation (see the plan file, Faz 6): STEP's own internal
line-tracer can terminate a temperature line early when the local
equilibrium solver hits its 500-iteration cap (error 4204) -- this happens
right next to phase-transition points and at some plain single-phase
temperatures too. Retrying with a different grid-minimizer mode (the same
fix already added to liboctq.F90 as tqce_native_retry) does NOT fix this
class of non-convergence (confirmed at steel1 Fe-C 1200K in Faz 4 -- both
modes failed). So instead of chasing a Fortran-level fix with unproven
payoff, any temperature STEP's line drops is filled in with a direct,
already-proven-reliable single-point native_fallback.run_and_parse call
(cold start, which empirically succeeds at points STEP's warm-started
continuation cannot reach, e.g. 1200K).

Note on units (RESOLVED 2026-07-27, see the plan file Faz 6 addendum):
STEP's own CSV reports BPW(<phase>) = mass fraction of each phase.
native_fallback.run_and_parse's phase_molar_amounts are moles of phase
(formula units), NOT mass fraction -- for simple single-sublattice phases
these numbers happen to look similar, but for phases with different
formula-unit sizes (e.g. Ag-Cu's FCC_A1#1/FCC_A1_AUTO#2 miscibility-gap
composition sets) they diverge by up to ~10 percentage points, which
showed up as a real, confirmed sawtooth artifact in the combined chart --
NOT a warm-start-vs-cold-start solver disagreement (a regression check at
five exact matching temperatures showed mass-fraction agreement to within
0.00003, ruling that hypothesis out). build_combined_series therefore
converts every gap-filled point to mass fraction (via phase_element_composition
and standard atomic weights, see _phase_mass_fractions_from_moles) before
merging with STEP's own BPW values, so the whole combined series is on one
consistent basis.
"""
import os
import re
import subprocess
import tempfile
import time

import native_fallback

OC_BUILD_DIR = os.environ.get("OC_BUILD_DIR", "/root/projects/opencalphad")
OC_BINARY = os.path.join(OC_BUILD_DIR, "OC")

_FLOAT = r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?"

# Standard atomic weights (g/mol), IUPAC conventional values, keyed by the
# element symbols as OpenCalphad/TDB files spell them (upper case). Covers
# the elements likely to appear in OC's bundled example databases; add more
# as needed if a new database uses an element not listed here.
ATOMIC_MASS = {
    "H": 1.008, "HE": 4.0026, "LI": 6.94, "BE": 9.0122, "B": 10.81, "C": 12.011,
    "N": 14.007, "O": 15.999, "F": 18.998, "NE": 20.180, "NA": 22.990, "MG": 24.305,
    "AL": 26.982, "SI": 28.085, "P": 30.974, "S": 32.06, "CL": 35.45, "AR": 39.948,
    "K": 39.098, "CA": 40.078, "SC": 44.956, "TI": 47.867, "V": 50.942, "CR": 51.996,
    "MN": 54.938, "FE": 55.845, "CO": 58.933, "NI": 58.693, "CU": 63.546, "ZN": 65.38,
    "GA": 69.723, "GE": 72.630, "AS": 74.922, "SE": 78.971, "BR": 79.904, "KR": 83.798,
    "RB": 85.468, "SR": 87.62, "Y": 88.906, "ZR": 91.224, "NB": 92.906, "MO": 95.95,
    "TC": 98.0, "RU": 101.07, "RH": 102.91, "PD": 106.42, "AG": 107.868, "CD": 112.41,
    "IN": 114.82, "SN": 118.71, "SB": 121.76, "TE": 127.60, "I": 126.90, "XE": 131.29,
    "CS": 132.91, "BA": 137.33, "HF": 178.49, "TA": 180.95, "W": 183.84, "RE": 186.21,
    "OS": 190.23, "IR": 192.22, "PT": 195.08, "AU": 196.97, "HG": 200.59, "TL": 204.38,
    "PB": 207.2, "BI": 208.98,
}


class NativeStepError(Exception):
    """Raised when the native STEP macro itself fails to run or produce a CSV."""


def generate_step_macro(db_path, elements_composition, temperature_min_K,
                         temperature_max_K, n_points, pressure_Pa, csv_basename):
    """Build the native STEP .ocm macro.

    Matches the exact working syntax captured from OpenCalphad CAE's own
    "Generate Macro File" (tests/fixtures/step_diagram/
    steel1_FeC_300_2000_step100.ocm): separate "set condition ..." lines
    (not the "set c ..." shorthand), TWO blank lines after the element
    list, and the specific blank-line counts around "step"/"normal" that
    answer OC's own default-accept prompts. The plot/render section is
    deliberately omitted -- we build our own gnuplot script from the
    (gap-filled) data instead of using OC's own wxt-terminal render, which
    would otherwise try to open an interactive window.
    """
    total = sum(elements_composition.values())
    fractions = {el: amt / total for el, amt in elements_composition.items()}
    dependent_el = max(fractions, key=fractions.get)
    independents = [el for el in elements_composition if el != dependent_el]

    elements_line = " ".join(elements_composition.keys())
    x_condition_lines = "\n".join(
        f"set condition x({el.lower()})={fractions[el]:.10g}" for el in independents
    )
    db_stem = os.path.splitext(os.path.basename(db_path))[0]
    # Seed at the low end of the range rather than the midpoint: a STEP
    # "startpoint" search can fail (error 4204, "Failed finding startpoints
    # for step/map") at a seed that a plain single calculate_equilibrium
    # would actually converge at just fine -- the low end tends to be a
    # simpler, more stable phase assemblage and is a safer default seed.
    seed_T = temperature_min_K

    macro = (
        "set echo\n"
        "Y\n"
        "set log\n"
        "run\n"
        "\n"
        f"read tdb {db_stem}.TDB\n"
        f"{elements_line}\n"
        "\n"
        "\n"
        f"set condition T = {seed_T:.10g}\n"
        f"set condition P = {pressure_Pa:.10g}\n"
        "set condition n = 1.0\n"
        f"{x_condition_lines}\n"
        "\n"
        "calculate equilibrium\n"
        "\n"
        "list result 4\n"
        "\n"
        "\n"
        f"set axis 1 T {temperature_min_K:.10g} {temperature_max_K:.10g} {n_points}\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "step\n"
        "normal\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "\n"
        "list\n"
        "excel_csv_file\n"
        "T\n"
        "BPW(*)\n"
        f"{csv_basename}\n"
        "\n"
        "exit Y\n"
    )
    return macro


def run_native_step(db_path, elements_composition, temperature_min_K,
                     temperature_max_K, n_points, pressure_Pa, timeout=60):
    """Run the STEP macro in an isolated scratch directory and return the
    raw CSV text (or raise NativeStepError if no CSV was produced)."""
    if not os.path.isfile(OC_BINARY):
        raise NativeStepError(f"Native OC binary not found: {OC_BINARY}")
    if not os.path.isfile(db_path):
        raise NativeStepError(f"Database not found: {db_path}")

    csv_basename = "step_data"
    with tempfile.TemporaryDirectory(prefix="oc_step_") as scratch:
        db_stem = os.path.splitext(os.path.basename(db_path))[0]
        scratch_db = os.path.join(scratch, f"{db_stem}.TDB")
        with open(db_path, "rb") as src, open(scratch_db, "wb") as dst:
            dst.write(src.read())

        macro_text = generate_step_macro(
            db_path, elements_composition, temperature_min_K,
            temperature_max_K, n_points, pressure_Pa, csv_basename
        )
        macro_path = os.path.join(scratch, "step.ocm")
        with open(macro_path, "w") as f:
            f.write(macro_text)

        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.path.join(OC_BUILD_DIR, ".libs")

        stdout_path = os.path.join(scratch, "stdout.txt")
        stderr_path = os.path.join(scratch, "stderr.txt")
        with open(macro_path) as stdin_f, \
             open(stdout_path, "w") as stdout_f, \
             open(stderr_path, "w") as stderr_f:
            try:
                subprocess.run(
                    [OC_BINARY],
                    cwd=scratch,
                    stdin=stdin_f,
                    stdout=stdout_f,
                    stderr=stderr_f,
                    env=env,
                    timeout=timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                pass

        csv_path = os.path.join(scratch, f"{csv_basename}.csv")
        if not os.path.isfile(csv_path):
            with open(stdout_path, errors="ignore") as f:
                tail = f.read()[-2000:]
            raise NativeStepError(
                "Native STEP did not produce a CSV output file "
                f"(macro likely failed before reaching the list step). "
                f"stdout tail: {tail}"
            )
        with open(csv_path, errors="ignore") as f:
            return f.read()


def parse_step_csv(csv_text):
    """Parse OC's own excel_csv_file output into (points, phase_names).

    points: list of (temperature_K, {phase_name: fraction}) tuples, in the
    file's own (not necessarily sorted) order -- STEP walks outward from
    the seed temperature in both directions, so the file typically goes
    up first, then restarts at the seed and walks down.
    """
    lines = [line for line in csv_text.splitlines() if line.strip()]
    if not lines:
        raise NativeStepError("Native STEP CSV output was empty.")

    header = [h.strip().strip('"') for h in lines[0].split(",")]
    phase_names = []
    for h in header[1:]:
        m = re.match(r"BPW\((.+)\)", h)
        phase_names.append(m.group(1) if m else h)

    points = []
    for line in lines[1:]:
        cells = [c.strip() for c in line.split(",")]
        if len(cells) < 2:
            continue
        try:
            T = float(cells[0])
        except ValueError:
            continue
        fractions = {}
        for name, cell in zip(phase_names, cells[1:]):
            if cell == "":
                continue
            try:
                fractions[name] = float(cell)
            except ValueError:
                continue
        points.append((T, fractions))

    if not points:
        raise NativeStepError("Native STEP CSV had a header but no data rows.")
    return points


def _dedupe_sorted(points, tol=1e-6):
    """Sort by T and merge points whose T is within tol of each other
    (STEP restarts from the seed point for the second direction, so the
    seed appears twice)."""
    ordered = sorted(points, key=lambda p: p[0])
    merged = []
    for T, fractions in ordered:
        if merged and abs(merged[-1][0] - T) <= tol:
            continue
        merged.append((T, fractions))
    return merged


def _phase_mass_fractions_from_moles(phase_molar_amounts, phase_element_composition):
    """Convert native_fallback's phase molar amounts to mass fractions.

    mass_i = moles_i * (sum of constituent mole-fraction * atomic weight),
    then normalized by the total mass across all phases -- this is exactly
    what native's own "Mass" column would report (verified: matches STEP's
    BPW to within 0.00003 at five cross-checked temperatures for agcu.TDB,
    see the plan file Faz 6 addendum), computed here from moles + internal
    composition since our build's default equilibrium listing prints
    Moles/mole-fraction, not Mass/mass-fraction.
    """
    masses = {}
    for name, n_moles in phase_molar_amounts.items():
        comp = phase_element_composition.get(name, {})
        avg_atomic_mass = sum(
            frac * ATOMIC_MASS.get(el.upper(), 0.0) for el, frac in comp.items()
        )
        masses[name] = n_moles * avg_atomic_mass
    total_mass = sum(masses.values())
    if total_mass <= 0:
        return {}
    return {name: m / total_mass for name, m in masses.items()}


def _canonicalize_phase_name(name, known_full_names):
    """De-truncate a STEP CSV column header like "FCC_A..TO#2" back to its
    full phase-tuple name (e.g. "FCC_A1_AUTO#2") by matching the prefix/
    suffix around ".." against phase names already seen from native_fallback
    (which prints full, untruncated names). OC's own STEP CSV writer
    truncates long phase-tuple names to fit a fixed column width; this does
    NOT happen in our code and is not something we control -- we can only
    reverse it heuristically. If no unambiguous match is found, the name is
    returned unchanged (worst case: that phase shows as a separate series
    on the chart instead of being merged, which is safe, just less tidy).
    """
    if ".." not in name:
        return name
    prefix, _, suffix = name.partition("..")
    candidates = [
        full for full in known_full_names
        if ".." not in full and full.startswith(prefix) and full.endswith(suffix)
    ]
    if len(candidates) == 1:
        return candidates[0]
    return name


def _validate_combined_points(combined, sum_tol=1e-5):
    """Verify every point's phase fractions sum to 1 +/- sum_tol and stay
    within [0, 1] before any CSV/chart is produced from them. Raises
    NativeStepError (loudly, rather than silently plotting bad data) if a
    point is out of tolerance."""
    for T, fractions, source in combined:
        total = sum(fractions.values())
        if not (1.0 - sum_tol <= total <= 1.0 + sum_tol):
            raise NativeStepError(
                f"Phase fractions at T={T} ({source}) sum to {total:.6f}, "
                f"expected 1.0 +/- {sum_tol}: {fractions}"
            )
        for name, v in fractions.items():
            if not (-1e-9 <= v <= 1.0 + 1e-9):
                raise NativeStepError(
                    f"Phase fraction {name}={v} at T={T} ({source}) is "
                    "outside the valid [0, 1] range."
                )


def build_combined_series(db_path, elements_composition, temperature_min_K,
                           temperature_max_K, n_points, pressure_Pa,
                           step_timeout=60, fallback_timeout=15):
    """Run native STEP, detect gaps where its line terminated early, and
    fill those gaps with native_fallback.run_and_parse single-point calls,
    on a single consistent basis (phase mass fraction).

    STEP's own points are authoritative wherever they exist -- fallback is
    only ever used to fill temperatures STEP's line dropped, never to
    override a temperature STEP already covered. Fallback's raw
    phase_molar_amounts (moles of phase, not mass fraction) are converted
    via _phase_mass_fractions_from_moles before merging, and STEP's own
    truncated phase-tuple names (e.g. "FCC_A..TO#2") are de-truncated
    against the full names seen from fallback via _canonicalize_phase_name,
    so "the same phase" always ends up under one key across both sources.

    Returns (combined_points, gap_filled_temperatures) where combined_points
    is a T-sorted list of (temperature_K, {phase_name: mass_fraction}, source)
    tuples, source being "step" or "native_fallback". Raises NativeStepError
    (via _validate_combined_points) if any point's fractions don't sum to
    1 +/- 1e-5 or fall outside [0, 1] -- this is checked before any CSV or
    chart is produced from the data.
    """
    csv_text = run_native_step(
        db_path, elements_composition, temperature_min_K, temperature_max_K,
        n_points, pressure_Pa, timeout=step_timeout
    )
    raw_points = parse_step_csv(csv_text)
    step_points = _dedupe_sorted(raw_points)

    nominal_spacing = (temperature_max_K - temperature_min_K) / max(n_points - 1, 1)
    gap_threshold = nominal_spacing * 3

    gaps = []
    if step_points[0][0] > temperature_min_K + gap_threshold:
        gaps.append((temperature_min_K, step_points[0][0]))
    for (T1, _), (T2, _) in zip(step_points, step_points[1:]):
        if T2 - T1 > gap_threshold:
            gaps.append((T1, T2))
    if step_points[-1][0] < temperature_max_K - gap_threshold:
        gaps.append((step_points[-1][0], temperature_max_K))

    # Fill gaps first (mass fraction, from moles + composition) so we have
    # a pool of full, untruncated phase names to de-truncate STEP's own
    # column headers against.
    fallback_points = []
    step_temperatures = {T for T, _ in step_points}
    for lo, hi in gaps:
        n_fill = max(int(round((hi - lo) / nominal_spacing)) - 1, 1)
        for i in range(1, n_fill + 1):
            T = lo + (hi - lo) * i / (n_fill + 1)
            if any(abs(T - existing) < 1e-6 for existing in step_temperatures):
                continue  # STEP already has this exact temperature -- keep STEP's
            try:
                result = native_fallback.run_and_parse(
                    db_path, elements_composition, T, pressure_Pa,
                    timeout=fallback_timeout
                )
            except Exception:
                continue  # leave this point as a genuine gap rather than fail the whole chart
            mass_fractions = _phase_mass_fractions_from_moles(
                result["phase_molar_amounts"], result["phase_element_composition"]
            )
            if not mass_fractions:
                continue
            fallback_points.append((T, mass_fractions))

    known_full_names = set()
    for _, fractions in fallback_points:
        known_full_names.update(fractions.keys())

    combined = []
    for T, fractions in step_points:
        canon_fractions = {
            _canonicalize_phase_name(name, known_full_names): value
            for name, value in fractions.items()
        }
        combined.append((T, canon_fractions, "step"))

    gap_filled_temperatures = []
    for T, fractions in fallback_points:
        combined.append((T, fractions, "native_fallback"))
        gap_filled_temperatures.append(T)

    combined.sort(key=lambda p: p[0])
    _validate_combined_points(combined)
    return combined, gap_filled_temperatures


def render_gnuplot_png(combined_points, title, output_png_path, timeout=20):
    """Build a pngcairo gnuplot script from combined_points and render it.

    Raises on any failure (gnuplot missing, script error, timeout) so the
    caller can fall back to matplotlib -- this function never tries to be
    the only way to get a chart.
    """
    phase_names = []
    for _, fractions, _ in combined_points:
        for name in fractions:
            if name not in phase_names:
                phase_names.append(name)
    if not phase_names:
        raise NativeStepError("No phase data to plot.")

    with tempfile.TemporaryDirectory(prefix="oc_gnuplot_") as scratch:
        data_path = os.path.join(scratch, "data.csv")
        with open(data_path, "w") as f:
            f.write("T," + ",".join(phase_names) + "\n")
            for T, fractions, _source in combined_points:
                row = [f"{T:.6g}"] + [
                    f"{fractions[name]:.6g}" if name in fractions else ""
                    for name in phase_names
                ]
                f.write(",".join(row) + "\n")

        script_lines = [
            f'set terminal pngcairo size 1400,850 font "Arial,14"',
            f'set output "{output_png_path}"',
            f'set title "{title}"',
            'set xlabel "Temperature (K)"',
            'set ylabel "Phase fraction"',
            'set datafile separator ","',
            'set key outside right',
            'set grid',
        ]
        plot_terms = [
            f'"{data_path}" using 1:{i + 2} with linespoints title "{name}"'
            for i, name in enumerate(phase_names)
        ]
        script_lines.append("plot " + ", ".join(plot_terms))
        script_path = os.path.join(scratch, "chart.plt")
        with open(script_path, "w") as f:
            f.write("\n".join(script_lines) + "\n")

        proc = subprocess.run(
            ["gnuplot", script_path],
            cwd=scratch,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        if proc.returncode != 0 or not os.path.isfile(output_png_path):
            raise NativeStepError(f"gnuplot failed: {proc.stderr[-1000:]}")
        with open(output_png_path, "rb") as f:
            return f.read()


def open_interactive_window(combined_points, title):
    """Fire-and-forget: opens a real, persistent gnuplot window (qt
    terminal) via WSLg, showing the same chart as render_gnuplot_png.

    This is for terminal-only MCP clients (e.g. OpenClaw) that can't
    render the returned PNG inline -- the window pops up directly on the
    Windows desktop (confirmed working via WSLg) as a bonus alongside the
    PNG, not a replacement for it. Returns immediately without waiting for
    the user to close the window; never raises (best-effort only, a failed
    window must not break the main tool call).
    """
    try:
        phase_names = []
        for _, fractions, _ in combined_points:
            for name in fractions:
                if name not in phase_names:
                    phase_names.append(name)
        if not phase_names:
            return False

        workdir = tempfile.mkdtemp(prefix="oc_gnuplot_window_")
        data_path = os.path.join(workdir, "data.csv")
        with open(data_path, "w") as f:
            f.write("T," + ",".join(phase_names) + "\n")
            for T, fractions, _source in combined_points:
                row = [f"{T:.6g}"] + [
                    f"{fractions[name]:.6g}" if name in fractions else ""
                    for name in phase_names
                ]
                f.write(",".join(row) + "\n")

        script_lines = [
            'set terminal qt size 1100,750 font "Arial,12"',
            f'set title "{title}"',
            'set xlabel "Temperature (K)"',
            'set ylabel "Phase fraction"',
            'set datafile separator ","',
            'set key outside right',
            'set grid',
        ]
        plot_terms = [
            f'"{data_path}" using 1:{i + 2} with linespoints title "{name}"'
            for i, name in enumerate(phase_names)
        ]
        script_lines.append("plot " + ", ".join(plot_terms))
        script_path = os.path.join(workdir, "chart.plt")
        with open(script_path, "w") as f:
            f.write("\n".join(script_lines) + "\n")

        subprocess.Popen(
            ["gnuplot", "-persist", script_path],
            cwd=workdir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        return False
