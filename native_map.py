"""Two-axis phase diagrams via OpenCalphad's native MAP.

The iconic CALPHAD deliverable, and the last of the engine's calculation
types this server did not reach. A property diagram fixes the composition
and sweeps temperature; an isothermal section fixes temperature and sweeps
composition. MAP does neither: it traces the PHASE BOUNDARIES themselves
across both axes at once, which is the picture a metallurgist means by
"the phase diagram".

The difference from STEP is in the shape of the answer, and it is why this
module shares no parsing with native_step. STEP walks one axis and every
point has the same columns, so its output is a table. MAP follows
boundaries -- curves along which two phases coexist -- and those curves
start, end, meet at invariant points, and involve different phases from
one another. Its output is a set of lines, not a table, and the phases
present change between them.

DATA COMES OUT THROUGH plot, NOT list. STEP results export with
"list / excel_csv_file"; asking the same of MAP results gets a refusal in
the engine's own words -- "You must give a STEP command before list
excell_csv". The route that does work is the plot command, which writes a
gnuplot script with the data embedded in a heredoc, and that embedded
block is what parse_map_plt reads. The script's own rendering is left
unused: it targets an interactive wxt window and ends in "pause mouse",
which would hang. The numbers are taken and the chart is drawn here.

WHAT THE EMBEDDED BLOCK LOOKS LIKE (steel1 Fe-C):

    KEYS:  T X(LIQUID,C) X(BCC-A2,C) X(FCC-A1,C) X(GRAPHITE,C)
     # First line: BCC_A2 FCC_A1
       1    1.052714E+03 NaN     6.452456E-04    2.000000E-02 NaN
      ...
    # shift of line   1
      19    1.011173E+03    0.000000E+00    1.000000E+00 ...
    ...
    # end of line  11

Column one is a running index, column two is temperature, and the rest are
one composition per phase named in KEYS, NaN where that phase is not part
of this boundary. The "shift of line" comments separate one boundary from
the next; only the first is named, so which phases a boundary involves is
recovered from which columns carry numbers.

INVARIANTS FALL OUT OF THAT STRUCTURE. A boundary whose points all sit at
one temperature is an invariant reaction -- eutectic, eutectoid,
peritectic -- and its span across the composition axis is the reaction's
extent. In the steel1 diagram, line 2 is three points all at 1011.173 K,
which is the Fe-C eutectoid this project measured independently at
1010-1012 K by bisecting single equilibria. Detecting them costs one
comparison and turns an anonymous curve into the feature a reader is
looking for, so parse_map_plt marks them.

MAP IS FRAGILE AND SAYS SO. The engine prints "The map command is
fragile, please send problematic diagrams to the [author]" before every
run. Measured here: agcu Ag-Cu produced 118 equilibria and steel1 Fe-C
330, while alni-4slx Al-Ni produced no result at all from a seed that
calculates cleanly as a single equilibrium. A failure is therefore
reported as a failure -- there is no second tier to fall back to, because
no other part of this engine traces boundaries.
"""
import math
import os
import re
import shutil
import subprocess
import tempfile
import time

import native_fallback

OC_BINARY = native_fallback.OC_BINARY
OC_BUILD_DIR = native_fallback.OC_BUILD_DIR

# A boundary counts as invariant when its temperatures agree to this much.
# Generous on purpose: the engine prints an invariant's points at one
# computed temperature, so the spread is float noise, not physics.
def _invariant_tolerance_K():
    """From settings/execution.toml [tolerances]. MAP reports one invariant
    reaction as several points with rounding between them; this is how
    close they must be to count as one temperature."""
    try:
        import settings_engine
        return settings_engine.execution_number(
            "tolerances", "map_invariant_K", 1e-3)
    except Exception:                                    # noqa: BLE001
        return 1e-3

def _policy_number(bolum, anahtar, default):
    """One number from settings/execution.toml, read once at import.

    Timeouts and tolerances are policy: raising a timeout changes whether a
    slow calculation comes back or is abandoned. The literal stays as the
    fallback because a missing settings file must not leave a subprocess
    waiting forever.
    """
    try:
        import settings_engine
        return settings_engine.execution_number(bolum, anahtar, default)
    except Exception:                                    # noqa: BLE001
        return default


MAP_TIMEOUT_S = _policy_number("timeouts", "map_s", 240)
CHART_TIMEOUT_S = _policy_number("timeouts", "chart_render_s", 30)
REAP_TIMEOUT_S = _policy_number("timeouts", "process_reap_s", 5)


_KEYS = re.compile(r"^KEYS:\s*(.*)$")
_LINE_BREAK = re.compile(r"^#\s*(?:shift|end) of line\s+\d+")
_FIRST_LINE = re.compile(r"^\s*#\s*First line:\s*(.*)$")
# "X(FCC-A1#1,CU)" -> phase FCC-A1#1. The engine spells composition-set
# names with hyphens here and underscores everywhere else, so the name is
# put back into the spelling the rest of this server uses.
_KEY_PHASE = re.compile(r"^X\((.+),([^,)]+)\)$", re.IGNORECASE)


class NativeMapError(Exception):
    """Raised when MAP could not be run or produced no diagram."""


def _canonical_phase(name):
    """Spell a phase the way the rest of this server does.

    Two differences to undo. MAP writes FCC-A1-AUTO#2 where every other
    output says FCC_A1_AUTO#2. And whether a phase carries its "#1"
    suffix depends on the seed: mapping agcu from a liquid seed reports
    LIQUID and FCC_A1, from a two-solid seed LIQUID#1 and FCC_A1#1 -- the
    same phases either way. "#1" is a phase's default composition set and
    is dropped, exactly as native_step drops it; "#2" and higher are
    genuinely separate composition sets (FCC_A1_AUTO#2 is the Cu-rich half
    of the Ag-Cu miscibility gap) and are kept.
    """
    name = name.replace("-", "_")
    return name[:-2] if name.endswith("#1") else name


def generate_map_macro(db_path, elements_composition, axis_element,
                       axis_min, axis_max, axis_step,
                       temperature_min_K, temperature_max_K,
                       temperature_step_K, seed_temperature_K, pressure_Pa,
                       basename="ocmap"):
    """Build the MAP macro, following examples/macros/map1.OCM.

    Both axes are given on one line each, and their third value is a STEP,
    not a point count -- the same reading that an earlier attempt at Scheil
    got wrong, with the same consequence if repeated: an axis advanced in
    huge jumps walks straight through the features being looked for.

    The seed equilibrium matters more here than anywhere else. MAP starts
    from it and traces outward, so it has to be a point the engine can
    solve; the caller's composition supplies it.
    """
    total = sum(elements_composition.values())
    if total <= 0:
        raise NativeMapError("Composition amounts must sum to something positive.")
    fractions = {el.upper(): amount / total
                 for el, amount in elements_composition.items()}
    symbol = axis_element.upper()
    if symbol not in fractions:
        raise NativeMapError(
            f"axis_element {axis_element} is not in the composition."
        )
    if len(fractions) < 2:
        raise NativeMapError("A phase diagram needs at least two elements.")

    # The scanned element is an axis, so it cannot also be the dependent
    # one, and it gets no fixed condition of its own beyond the seed.
    others = {el: v for el, v in fractions.items() if el != symbol}
    dependent = max(others, key=others.get)
    conditions = " ".join(
        f"x({el.lower()})={fractions[el]:.10g}"
        for el in fractions if el != dependent
    )

    stem = os.path.splitext(os.path.basename(db_path))[0]
    return (
        "new Y\n"
        f"r t ./{stem}\n"
        # Four, not one. A database that warns while loading makes the
        # engine stop and wait for RETURN, and the next macro line answers
        # that prompt instead of being read as a command -- so `set c`
        # never arrives and the calculation runs with no conditions at
        # all, returning G=0 and NaN. From outside that looks like an
        # alloy the solver could not handle. Measured on iron4cd, where it
        # cost a whole question and was written up as an engine limit.
        # Spare blank lines at a command prompt are harmless.
        f"{' '.join(fractions)}\n"
        "\n"
        "\n"
        "\n"
        "\n"
        f"set cond t={seed_temperature_K:.10g} p={pressure_Pa:.10g} n=1 "
        f"{conditions}\n"
        "\n"
        "c e\n"
        "\n"
        f"set ax 1 x({symbol.lower()}) {axis_min:.10g} {axis_max:.10g} "
        f"{axis_step:.10g}\n"
        f"set ax 2 t {temperature_min_K:.10g} {temperature_max_K:.10g} "
        f"{temperature_step_K:.10g}\n"
        "\n"
        "map\n"
        "\n"
        # plot is used only to make the engine write its data out; the
        # script it produces renders to an interactive window and ends in
        # "pause mouse", so it is read, not run.
        "plot\n"
        f"x(*,{symbol.lower()})\n"
        "T\n"
        f"title {basename}\n"
        f"output ./{basename}\n"
        "render\n"
        "\n"
        "\n"
    )


def run_native_map(db_path, elements_composition, axis_element,
                   axis_min, axis_max, axis_step,
                   temperature_min_K, temperature_max_K, temperature_step_K,
                   seed_temperature_K, pressure_Pa,
                   timeout=MAP_TIMEOUT_S, max_bytes=4_000_000):
    """Run MAP and return the text of the gnuplot script it wrote.

    Raises NativeMapError if no script appeared, which is what a failed
    map looks like from outside: the engine reports its own trouble on
    screen and simply produces nothing.
    """
    if not os.path.isfile(OC_BINARY):
        raise NativeMapError(f"Native OC binary not found: {OC_BINARY}")

    basename = "ocmap"
    macro = generate_map_macro(
        db_path, elements_composition, axis_element, axis_min, axis_max,
        axis_step, temperature_min_K, temperature_max_K, temperature_step_K,
        seed_temperature_K, pressure_Pa, basename=basename,
    )

    workdir = tempfile.mkdtemp(prefix="oc_map_")
    try:
        shutil.copy(db_path, workdir)
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = os.path.join(OC_BUILD_DIR, ".libs")
        proc = subprocess.Popen(
            [OC_BINARY],
            cwd=workdir,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
        )
        try:
            try:
                proc.stdin.write(macro)
                proc.stdin.close()
            except (BrokenPipeError, OSError):
                pass
            chunks = []
            total = 0
            start = time.monotonic()
            while total < max_bytes and (time.monotonic() - start) < timeout:
                chunk = proc.stdout.read(8192)
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
        finally:
            proc.kill()
            try:
                proc.wait(timeout=REAP_TIMEOUT_S)
            except subprocess.TimeoutExpired:
                pass

        screen = "".join(chunks)
        plt_path = os.path.join(workdir, basename + ".plt")
        if not os.path.isfile(plt_path):
            equilibria = re.search(
                r"Finished step/map with\s+(\d+)\s+equilibria", screen)
            detail = (f" The engine reported {equilibria.group(1)} equilibria "
                      "but wrote no diagram." if equilibria else
                      " The engine traced no boundaries from this starting point.")
            raise NativeMapError(
                "MAP produced no phase diagram." + detail
            )
        with open(plt_path, errors="replace") as f:
            return f.read()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def parse_map_plt(plt_text):
    """Read the data embedded in the engine's gnuplot script.

    Returns a dict holding the boundaries. Each boundary is one traced
    curve: the phases that coexist along it, its points, and whether it is
    an invariant reaction (every point at one temperature).
    """
    lines = plt_text.splitlines()

    keys = None
    start = None
    for index, line in enumerate(lines):
        found = _KEYS.match(line.strip())
        if found:
            keys = found.group(1).split()
            start = index + 1
            break
    if not keys or len(keys) < 2:
        raise NativeMapError("The diagram carries no KEYS header to read.")

    # keys[0] is the temperature column; the rest name one phase each.
    phase_names = []
    axis_element = None
    for key in keys[1:]:
        found = _KEY_PHASE.match(key)
        if found:
            phase_names.append(_canonical_phase(found.group(1)))
            axis_element = found.group(2).upper()
        else:
            phase_names.append(_canonical_phase(key))

    boundaries = []
    current = []
    current_phases = None

    def _close():
        if not current:
            return
        temperatures = [p["temperature_K"] for p in current]
        invariant = ((max(temperatures) - min(temperatures))
                     <= _invariant_tolerance_K())
        # Which phases this boundary is actually about. "Appears at least
        # once" is too generous: at the point where a boundary meets an
        # invariant the engine prints 0.0 for the absent phases instead of
        # NaN, so a two-phase boundary ending on a eutectic would list
        # every phase in the system on the strength of its last row.
        # Requiring a majority keeps the boundary's own phases and drops
        # the ones that appear only where it terminates -- and leaves
        # invariants listing all their participants, which is correct.
        present = []
        for name in phase_names:
            seen = sum(1 for p in current if name in p["compositions"])
            if seen * 2 > len(current):
                present.append(name)
        boundary = {
            "phases": current_phases or present,
            "invariant": invariant,
            "points": list(current),
        }
        if invariant:
            boundary["temperature_K"] = temperatures[0]
        boundaries.append(boundary)

    for line in lines[start:]:
        stripped = line.strip()
        if stripped == "EOD":
            break
        named = _FIRST_LINE.match(line)
        if named:
            current_phases = [_canonical_phase(n) for n in named.group(1).split()]
            continue
        if _LINE_BREAK.match(stripped):
            _close()
            current = []
            current_phases = None
            continue
        if not stripped or stripped.startswith("#"):
            continue

        tokens = stripped.split()
        if len(tokens) < 2:
            continue
        try:
            temperature = float(tokens[1])
        except ValueError:
            continue
        compositions = {}
        for name, token in zip(phase_names, tokens[2:]):
            try:
                value = float(token)
            except ValueError:
                continue  # "NaN": this phase is not on this boundary
            if math.isnan(value):
                continue
            compositions[name] = value
        if compositions:
            current.append({
                "temperature_K": temperature,
                "compositions": compositions,
            })
    _close()

    if not boundaries:
        raise NativeMapError("The diagram contains no boundary lines.")

    invariants = [b for b in boundaries if b["invariant"]]
    return {
        "axis_element": axis_element,
        "phases": phase_names,
        "boundaries": boundaries,
        "invariant_temperatures_K": sorted(
            {round(b["temperature_K"], 3) for b in invariants}
        ),
        "point_count": sum(len(b["points"]) for b in boundaries),
    }


def render_gnuplot_png(diagram, title, output_png_path,
                       timeout=CHART_TIMEOUT_S,
                       axis_min=None, axis_max=None,
                       temperature_min_K=None, temperature_max_K=None):
    """Draw the phase diagram: composition across, temperature up.

    Built from the parsed boundaries rather than by running the engine's
    own script, which targets an interactive window and ends in "pause
    mouse". Each boundary contributes one curve per phase on it, so a
    two-phase boundary draws both sides -- which is what makes a two-phase
    field readable as a field rather than a line.
    """
    axis = diagram.get("axis_element") or "X"
    series = []
    for index, boundary in enumerate(diagram["boundaries"]):
        for phase in boundary["phases"]:
            points = [
                (p["compositions"][phase], p["temperature_K"])
                for p in boundary["points"] if phase in p["compositions"]
            ]
            if len(points) >= 2:
                series.append((phase, boundary["invariant"], points))
    if not series:
        raise NativeMapError("No boundary had enough points to draw.")

    with tempfile.TemporaryDirectory(prefix="oc_map_plot_") as scratch:
        data_path = os.path.join(scratch, "data.dat")
        with open(data_path, "w") as f:
            for _phase, _invariant, points in series:
                for x, temperature in points:
                    f.write(f"{x:.8g} {temperature:.8g}\n")
                f.write("\n\n")  # blank pair separates gnuplot index blocks

        # A colour per phase, fixed before anything is drawn. Deriving it
        # from the order phases happen to appear in makes the same phase
        # change colour between curves, which is how the first version of
        # this chart drew the liquidus in a colour its own key gave to
        # another phase.
        colour_of = {name: 1 + (i % 8)
                     for i, name in enumerate(diagram["phases"])}

        # One legend entry per phase, not per boundary: a phase appears on
        # several boundaries and repeating its name once per curve would
        # bury the key under duplicates.
        seen = set()
        plot_terms = []
        for index, (phase, invariant, _points) in enumerate(series):
            if phase in seen:
                title_clause = "notitle"
            else:
                seen.add(phase)
                title_clause = f'title "{phase}"'
            width = 3 if invariant else 2
            plot_terms.append(
                f'"{data_path}" index {index} using 1:2 with lines '
                f'lc {colour_of.get(phase, 9)} lw {width} {title_clause}'
            )

        script = [
            'set terminal pngcairo size 1400,900 font "Arial,14" noenhanced',
            f'set output "{output_png_path}"',
            f'set title "{title}"',
            f'set xlabel "x({axis})"',
            'set ylabel "Temperature (K)"',
            'set key outside right',
            'set grid',
        ]
        # Clip to what was asked for. Without this a pure phase drags the
        # axis to the far edge on the strength of its own composition --
        # graphite sits at x(C)=1, so a request for 0 to 0.25 came back
        # drawn across the full range with every feature squeezed into the
        # left tenth of it.
        if axis_min is not None and axis_max is not None:
            script.append(f"set xrange [{axis_min:.10g}:{axis_max:.10g}]")
        if temperature_min_K is not None and temperature_max_K is not None:
            script.append(
                f"set yrange [{temperature_min_K:.10g}:{temperature_max_K:.10g}]"
            )
        script.append("plot " + ", ".join(plot_terms))
        script_path = os.path.join(scratch, "diagram.plt")
        with open(script_path, "w") as f:
            f.write("\n".join(script) + "\n")

        proc = subprocess.run(
            ["gnuplot", script_path],
            cwd=scratch, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        if proc.returncode != 0 or not os.path.isfile(output_png_path):
            raise NativeMapError(f"gnuplot failed: {proc.stderr[-1000:]}")
        with open(output_png_path, "rb") as f:
            return f.read()
