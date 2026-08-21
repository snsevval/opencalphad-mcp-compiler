"""Native OpenCalphad STEP + gnuplot backend for calculate_property_diagram.

Design principle (Faz 10): the CALCULATION loop and the ARTIFACT
(CSV/chart) loop are separate, and must stay separate. If a result's
numbers are correct but its chart looks wrong (wrong axis range, a
mislabeled/duplicated phase series, missing gridlines), the fix belongs
entirely in render_gnuplot_png/open_interactive_window -- never re-run
build_combined_series or the underlying engines over it. The y-range fix
and the "..">-truncated-name canonicalization in this file are both
examples of artifact-only fixes that touched no calculation code. Re-
running OCASI/native because a plot looked ugly would waste real
engine time solving a problem that was never in the numbers.

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
# Now sharing native_fallback.OC_BINARY (prefers the bundled 6.058 Windows
# binary when present): its STEP line-tracer is far more capable than our
# own 6.120 build's -- it finds the true invariant node and adaptively
# refines right up to a phase-count-changing transition (confirmed: 155
# equilibria vs our 6.120's 8, for agcu.TDB 800-1400K -- see the plan file,
# Faz 7 addendum), which is exactly the sharp transition shape STEP-based
# GUI charts show and our gap-fill (evenly spaced, discrete points) could
# never reproduce on its own. Its "list/excel_csv_file" export prints the
# table to the screen instead of writing the named file; run_native_step's
# _extract_screen_csv_block recovers it from stdout instead.
OC_BINARY = native_fallback.OC_BINARY

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
                         temperature_max_K, n_points, pressure_Pa, csv_basename,
                         axis_element=None, axis_min=None, axis_max=None):
    """Build the native STEP .ocm macro.

    Scans temperature by default. Pass axis_element to scan that element's
    mole fraction instead, between axis_min and axis_max, holding
    temperature fixed at temperature_min_K -- an isothermal section, which
    is the question "what forms as I add more of this?" rather than "what
    happens to this alloy as it heats".


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
    # When an element is being scanned it cannot also be the dependent one:
    # the dependent element is the one with no condition of its own, and
    # the axis IS a condition. So it is chosen among the rest.
    candidates = {el: v for el, v in fractions.items()
                  if el.upper() != (axis_element or "").upper()}
    dependent_el = max(candidates, key=candidates.get)
    independents = [el for el in elements_composition if el != dependent_el]

    elements_line = " ".join(elements_composition.keys())
    # The scanned element gets no fixed condition either -- "set axis"
    # supplies its value at every point. Writing both would over-constrain
    # the system, which the engine reports as a nonzero degrees of freedom
    # or simply refuses.
    x_condition_lines = "\n".join(
        f"set condition x({el.lower()})={fractions[el]:.10g}"
        for el in independents
        if el.upper() != (axis_element or "").upper()
    )
    db_stem = os.path.splitext(os.path.basename(db_path))[0]
    # Seed at the low end of the range rather than the midpoint: a STEP
    # "startpoint" search can fail (error 4204, "Failed finding startpoints
    # for step/map") at a seed that a plain single calculate_equilibrium
    # would actually converge at just fine -- the low end tends to be a
    # simpler, more stable phase assemblage and is a safer default seed.
    seed_T = temperature_min_K

    if axis_element:
        axis_name = f"x({axis_element.lower()})"
        axis_lo, axis_hi = axis_min, axis_max
        # The seed has to sit ON the axis, so the scanned element gets its
        # starting value as a condition here and the axis takes over from
        # there. Same reasoning as the temperature seed above: start at the
        # low end, where the phase assemblage tends to be simplest.
        seed_line = f"set condition {axis_name}={axis_lo:.10g}\n"
        csv_x_column = f"X({axis_element.upper()})"
    else:
        axis_name = "T"
        axis_lo, axis_hi = temperature_min_K, temperature_max_K
        seed_line = ""
        csv_x_column = "T"

    macro = (
        # "set echo"/"set log" (from the GUI-captured macro this is
        # otherwise based on) are intentionally omitted: we never read the
        # resulting .LOG file, and "set log" hangs specifically when the
        # engine binary runs against a UNC working directory (confirmed
        # with the Windows 6.058 binary invoked from WSL over
        # \\wsl.localhost\...) trying to create the log file there.
        f"read tdb {db_stem}.TDB\n"
        f"{elements_line}\n"
        "\n"
        "\n"
        f"set condition T = {seed_T:.10g}\n"
        f"set condition P = {pressure_Pa:.10g}\n"
        "set condition n = 1.0\n"
        f"{x_condition_lines}\n"
        f"{seed_line}"
        "\n"
        "calculate equilibrium\n"
        "\n"
        "list result 4\n"
        "\n"
        "\n"
        f"set axis 1 {axis_name} {axis_lo:.10g} {axis_hi:.10g} {n_points}\n"
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
        f"{csv_x_column}\n"
        "BPW(*)\n"
        f"{csv_basename}\n"
        "\n"
        "exit Y\n"
    )
    return macro


def run_native_step(db_path, elements_composition, temperature_min_K,
                     temperature_max_K, n_points, pressure_Pa, timeout=60,
                     axis_element=None, axis_min=None, axis_max=None):
    """Run the STEP macro in an isolated scratch directory and return the
    raw CSV text (or raise NativeStepError if no CSV was produced).

    axis_element switches the scan from temperature to that element's mole
    fraction, holding temperature at temperature_min_K."""
    if not os.path.isfile(OC_BINARY):
        raise NativeStepError(f"Native OC binary not found: {OC_BINARY}")
    if not os.path.isfile(db_path):
        raise NativeStepError(f"Database not found: {db_path}")

    csv_basename = "step_data"
    # The Windows binary's file-writing commands (here: the CSV export)
    # hang when the working directory is a WSL UNC path
    # (\\wsl.localhost\...) -- confirmed with "set log" and reproduced for
    # the CSV write too. Give it a real Windows-drive scratch directory
    # instead; the Linux ELF binary works fine with a normal /tmp dir.
    scratch_parent = "/mnt/c/Windows/Temp" if OC_BINARY.lower().endswith(".exe") else None
    with tempfile.TemporaryDirectory(prefix="oc_step_", dir=scratch_parent) as scratch:
        db_stem = os.path.splitext(os.path.basename(db_path))[0]
        scratch_db = os.path.join(scratch, f"{db_stem}.TDB")
        with open(db_path, "rb") as src, open(scratch_db, "wb") as dst:
            dst.write(src.read())

        macro_text = generate_step_macro(
            db_path, elements_composition, temperature_min_K,
            temperature_max_K, n_points, pressure_Pa, csv_basename,
            axis_element=axis_element, axis_min=axis_min, axis_max=axis_max,
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
        if os.path.isfile(csv_path):
            with open(csv_path, errors="ignore") as f:
                return f.read()

        # The 6.058 binary's "excel_csv_file" list variant does not write
        # the named file at all -- it always answers "Output on screen"
        # regardless of the filename macro line, and prints the same
        # comma-separated table directly to stdout instead (confirmed by
        # direct inspection; this also means it captures the true STEP
        # line-tracer's output, including the fine adaptive stepping right
        # at a phase-count-changing invariant node, which our own Linux
        # 6.120 build's STEP algorithm doesn't reach in the first place).
        # Recover the table from stdout instead of requiring a file.
        with open(stdout_path, errors="ignore") as f:
            stdout_text = f.read()
        # Same column name the macro asked the engine to write, so the
        # on-screen fallback looks for the header it will actually see.
        csv_x_column = f"X({axis_element.upper()})" if axis_element else "T"
        screen_csv = _extract_screen_csv_block(stdout_text, csv_x_column)
        if screen_csv is not None:
            return screen_csv

        tail = stdout_text[-2000:]
        raise NativeStepError(
            "Native STEP did not produce a CSV output file or a "
            "recognizable on-screen CSV block "
            f"(macro likely failed before reaching the list step). "
            f"stdout tail: {tail}"
        )


def _extract_screen_csv_block(stdout_text, x_column="T"):
    """Pull the excel_csv_file table back out of raw stdout when it was
    printed to the screen instead of written to a file (see
    run_native_step). Returns the CSV text (header + data lines) or None
    if no such block is found.

    Tolerant of stray non-data lines in the middle of the block (engine
    log/warning lines occasionally interleave with the table when stdout
    and stderr share a buffer) -- only lines matching the expected
    "<float>,..." shape are kept; anything else between the header and the
    next non-CSV section is silently dropped rather than treated as fatal.
    """
    lines = stdout_text.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(f'"{x_column}",') and "BPW(" in stripped:
            header_idx = i
            break
    if header_idx is None:
        return None

    data_row_re = re.compile(rf"^\s*{_FLOAT}\s*,")
    kept = [lines[header_idx]]
    for line in lines[header_idx + 1:]:
        if data_row_re.match(line):
            kept.append(line.strip())
        elif line.strip() == "" or line.strip().startswith(("Note:", "STOP")):
            continue  # blank lines / interleaved warnings: skip, keep scanning
        else:
            break  # reached the next command's own output -- table is done
    if len(kept) <= 1:
        return None
    return "\n".join(kept) + "\n"


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


def _strip_default_composition_set(name):
    """Drop a trailing "#1" composition-set suffix.

    In OpenCalphad "#1" is a phase's FIRST (default) composition set, and
    the engine prints it inconsistently depending on which output path it
    came through: STEP's CSV writes plain "LIQUID" while the single-point
    equilibrium listing writes "LIQUID#1" for the very same phase. Left
    alone, a combined series ends up with both spellings as two separate
    chart series covering different temperature ranges -- which is exactly
    what the independent Layer B reviewer flagged on agcu.TDB.

    Only "#1" is stripped. "#2" and higher denote genuinely additional
    composition sets (e.g. FCC_A1_AUTO#2, the Cu-rich half of the Ag-Cu
    miscibility gap) and must stay distinct -- merging those would fuse
    two physically different phases into one line.
    """
    return name[:-2] if name.endswith("#1") else name


def _canonicalize_phase_name(name, known_full_names):
    """Bring a phase name to the one spelling used across both data
    sources: de-truncate STEP's fixed-width column headers, and drop the
    default "#1" composition-set suffix.

    De-truncation: OC's own STEP CSV writer shortens long phase-tuple
    names to fit its column width, e.g. "FCC_A1_AUTO#2" becomes
    "FCC_A..TO#2". That happens inside the engine, not in our code, so it
    can only be reversed heuristically -- by matching the prefix/suffix
    around ".." against the full, untruncated names native_fallback
    prints. If no unambiguous match exists the truncated name is kept as
    is (worst case: that phase plots as its own series, which is safe,
    just less tidy).
    """
    if ".." in name:
        prefix, _, suffix = name.partition("..")
        candidates = [
            full for full in known_full_names
            if ".." not in full and full.startswith(prefix) and full.endswith(suffix)
        ]
        if len(candidates) == 1:
            return _strip_default_composition_set(candidates[0])
    return _strip_default_composition_set(name)


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


def _fractions_agree(a, b, tol=1e-4):
    """Do two readings of the same axis position describe the same
    equilibrium? Both sides must already be canonicalized -- otherwise
    "LIQUID" and "LIQUID#1" would read as a disagreement.

    Phases below tol are ignored on both sides: a phase reported at 1e-7 by
    one engine and simply absent from the other is the same physical answer,
    and treating that as a conflict would fire on every point where a phase
    is just appearing.
    """
    def significant(fractions):
        return {name: value for name, value in fractions.items() if value > tol}

    left, right = significant(a), significant(b)
    if set(left) != set(right):
        return False
    return all(abs(left[name] - right[name]) <= tol for name in left)


def composition_at(elements_composition, axis_element, x):
    """The composition to hand a single-point call at axis position x.

    The scanned element takes the axis value; the others keep their
    original proportions; the largest of the others absorbs the remainder,
    which is the same element the macro leaves dependent. Without this the
    gap-fill would compute a different alloy than STEP did at the same x.
    """
    total = sum(elements_composition.values())
    fractions = {el: amt / total for el, amt in elements_composition.items()}
    others = {el: v for el, v in fractions.items()
              if el.upper() != axis_element.upper()}
    if not others:
        raise NativeStepError(
            f"Cannot scan {axis_element}: it is the only element."
        )
    dependent = max(others, key=others.get)
    out = {el: v for el, v in others.items() if el != dependent}
    scanned = next(el for el in fractions if el.upper() == axis_element.upper())
    out[scanned] = x
    remainder = 1.0 - sum(out.values())
    if remainder <= 0.0:
        raise NativeStepError(
            f"Composition axis reached {x:g} for {axis_element}, which "
            f"leaves nothing for {dependent}."
        )
    out[dependent] = remainder
    return out


def build_combined_series(db_path, elements_composition, temperature_min_K,
                           temperature_max_K, n_points, pressure_Pa,
                           step_timeout=60, fallback_timeout=15,
                           axis_element=None, axis_min=None, axis_max=None):
    """Run native STEP, detect gaps where its line terminated early, and
    fill those gaps with native_fallback.run_and_parse single-point calls,
    on a single consistent basis (phase mass fraction).

    STEP's own points are authoritative wherever they exist, with one
    measured exception: the two endpoints are read a second time from the
    single-point engine, which re-minimises globally, and a disagreement
    there is resolved against STEP (see the endpoint block below for the
    case that prompted it). Everywhere else fallback only fills positions
    STEP's line dropped, never overriding one STEP already covered.
    Fallback's raw
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
        n_points, pressure_Pa, timeout=step_timeout,
        axis_element=axis_element, axis_min=axis_min, axis_max=axis_max,
    )
    raw_points = parse_step_csv(csv_text)
    step_points = _dedupe_sorted(raw_points)

    # Everything below works on "axis position", which is temperature on
    # the default axis and a mole fraction on a composition axis. Only two
    # things differ between them: the range being covered, and what a
    # single-point call at a given position needs as arguments.
    if axis_element:
        span_lo, span_hi = axis_min, axis_max

        def single_point_args(position):
            return (composition_at(elements_composition, axis_element, position),
                    temperature_min_K)
    else:
        span_lo, span_hi = temperature_min_K, temperature_max_K

        def single_point_args(position):
            return elements_composition, position

    nominal_spacing = (span_hi - span_lo) / max(n_points - 1, 1)
    gap_threshold = nominal_spacing * 3

    gaps = []
    if step_points[0][0] > span_lo + gap_threshold:
        gaps.append((span_lo, step_points[0][0]))
    for (T1, _), (T2, _) in zip(step_points, step_points[1:]):
        if T2 - T1 > gap_threshold:
            gaps.append((T1, T2))
    if step_points[-1][0] < span_hi - gap_threshold:
        gaps.append((step_points[-1][0], span_hi))

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
                point_composition, point_temperature = single_point_args(T)
                result = native_fallback.run_and_parse(
                    db_path, point_composition, point_temperature, pressure_Pa,
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

    # STEP follows a line; it does not re-minimise globally at each step.
    # Where that line stops being the global minimum, STEP keeps following
    # it and reports a metastable equilibrium with nothing to say anything
    # is wrong. Measured on steel1 Fe-Cr-C at 1100 K, scanning x(Cr) from
    # 0.01 to 0.30: STEP's ordinary steps matched fresh single-point
    # equilibria to five decimals, but the point it carries to the axis
    # limit when terminating a line reported FCC_A1+M7C3 where the stable
    # answer is BCC_A2+M23C6.
    #
    # An endpoint is where a continuation has travelled furthest from the
    # solution it started at, and there are only two of them -- cheap to
    # read a second time from the engine that does re-minimise globally.
    # Disagreements are resolved in favour of the global minimisation.
    endpoint_readings = {}
    for position in {step_points[0][0], step_points[-1][0]}:
        try:
            point_composition, point_temperature = single_point_args(position)
            result = native_fallback.run_and_parse(
                db_path, point_composition, point_temperature, pressure_Pa,
                timeout=fallback_timeout
            )
            fresh = _phase_mass_fractions_from_moles(
                result["phase_molar_amounts"], result["phase_element_composition"]
            )
        except Exception:
            continue  # no second reading available; STEP's own point stands
        if fresh:
            endpoint_readings[position] = fresh

    # Built from the RAW fallback names, before canonicalization: these are
    # the full, untruncated spellings that STEP's truncated headers get
    # matched back against.
    known_full_names = set()
    for _, fractions in fallback_points:
        known_full_names.update(fractions.keys())
    for fractions in endpoint_readings.values():
        known_full_names.update(fractions.keys())

    def _canonicalize(fractions):
        return {
            _canonicalize_phase_name(name, known_full_names): value
            for name, value in fractions.items()
        }

    endpoint_replacements = {}
    for position, fresh in endpoint_readings.items():
        step_fractions = next(f for T, f in step_points if T == position)
        if not _fractions_agree(_canonicalize(step_fractions), _canonicalize(fresh)):
            endpoint_replacements[position] = fresh

    # Both sources go through the same canonicalization -- the fallback
    # side needs it too, since it's the one that spells the default
    # composition set as "LIQUID#1" where STEP writes plain "LIQUID".
    combined = []
    for T, fractions in step_points:
        if T in endpoint_replacements:
            combined.append((T, _canonicalize(endpoint_replacements[T]),
                             "native_fallback (endpoint recheck)"))
        else:
            combined.append((T, _canonicalize(fractions), "step"))

    gap_filled_temperatures = []
    for T, fractions in fallback_points:
        combined.append((T, _canonicalize(fractions), "native_fallback"))
        gap_filled_temperatures.append(T)

    combined.sort(key=lambda p: p[0])
    _validate_combined_points(combined)
    return combined, gap_filled_temperatures


def render_gnuplot_png(combined_points, title, output_png_path, timeout=20,
                       x_label="Temperature (K)"):
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
            # noenhanced: phase names contain underscores (FCC_A1_AUTO#2) and
            # gnuplot's enhanced text would render them as subscripts.
            f'set terminal pngcairo size 1400,850 font "Arial,14" noenhanced',
            f'set output "{output_png_path}"',
            f'set xlabel "{x_label}"',
            'set ylabel "Phase fraction"',
            'set datafile separator ","',
            'set key outside right',
            'set grid',
            'set yrange [0:1]',
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


def open_interactive_window(combined_points, title, x_label="Temperature (K)"):
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
            'set terminal qt size 1100,750 font "Arial,12" noenhanced',
            f'set title "{title}"',
            f'set xlabel "{x_label}"',
            'set ylabel "Phase fraction"',
            'set datafile separator ","',
            'set key outside right',
            'set grid',
            'set yrange [0:1]',
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
