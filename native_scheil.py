"""Scheil-Gulliver solidification via OpenCalphad's native STEP SCHEIL.

A different question from anything else this server answers. Every other
tool computes equilibrium: given conditions, what is stable. Scheil
computes a PATH -- liquid is assumed homogeneous, the solid formed at each
temperature step is removed from the system, and the remaining liquid's
composition is updated accordingly. That is the non-equilibrium
solidification a real casting undergoes, and the segregation it predicts
(the last liquid can be wildly enriched) is what heat treatments exist to
undo.

Two consequences follow from "path", and both shape this module.

GAP-FILL DOES NOT TRANSFER. native_step fills a temperature STEP's line
never reached by computing that temperature independently, because an
equilibrium at 1050 K does not depend on how the system got there. A
Scheil state does: the liquid composition at 1050 K is the result of every
gram of solid removed above it. There is no independent calculation that
produces "the Scheil state at 1050 K", so a simulation that stops early
stops early. This module reports where it stopped instead of filling in.

THE TEMPERATURE STEP IS NOT A DISPLAY SETTING. It is the increment the
simulation actually advances by, so it changes the answer. Measured over
five systems and five step sizes (25 runs):

    system                1 K    2 K    5 K   10 K   20 K
    steel1 Fe-1C         5.63   2.88   1.08      -      -
    steel1 Fe-5Cr-1C    32.57  32.42   0.37  29.72  29.04
    agcu Ag-80          20.83  12.70  28.87  15.09  32.06
    agcu Ag-90           9.91   4.29   3.08   7.14   7.97
    cost507R Al-Mg-Si-Zn 0.43   0.34   0.30  27.15  27.14
    (per cent liquid still unsolidified when the run stopped; lower is
     better, "-" means the run produced no points at all)

Two things in that table decide the design. 10 K and 20 K are reliably
bad -- they are excluded rather than offered. And within 1-5 K the outcome
is ERRATIC, not smoothly optimal: Fe-5Cr-1C stalls at 32% for both 1 K and
2 K, finishes at 0.37% at 5 K, and stalls again at 10 K. Neighbouring step
sizes give unrelated results, and nothing observable predicts which will
work. That is why run_with_step_ladder tries several and keeps the best
rather than picking one: when the outcome cannot be predicted but CAN be
measured, trying and comparing is the only honest move. The comparison
needs no judgement -- less liquid left is strictly better.

Runs end at the same convergence limit the rest of this project has met
throughout -- "Error storing equilibria 4204 / Too many iterations" -- as
the last liquid grows extreme and the solver can no longer follow it. The
final per cent is therefore reported next to every result, because the last
few per cent is exactly where the terminal eutectic forms and where a
segregation study was looking.

THE ITERATION LIMIT IS SETTABLE, AND DELIBERATELY LEFT ALONE. Runs end at
"Error storing equilibria 4204 / Too many iterations". That limit is not a
hard-coded constant: ocparam.F90 defines default_maxiter = 500, each
equilibrium record carries its own ceq%maxiter, and the engine exposes a
user command for it -- "set numeric_options", whose first prompt is "Max
number of iterations". No rebuild needed. Raising it to 5000 was measured:

    steel1 Fe-1C    103 points, 2.88% left  ->  191 points, 1.23% left
    agcu Ag-80      114 points, 12.7% left  ->  268 points, axis exhausted
    (50000 changed nothing further; 5000 is past the binding constraint)

The default is kept anyway, because the second row is worse than it looks.
Following agcu's liquid composition across those extra points:

    99.96% liquid at 1134 K, x(Cu) 0.200
    11.94% liquid at  870 K, x(Cu) 0.859
    10.28% liquid at  600 K, x(Cu) 0.982

The fraction plateaus near 10% while the composition runs toward pure
copper. The Ag-Cu eutectic is at 1052 K and x(Cu) 0.4; by 870 K this path
is long past it and still following the Ag-rich liquidus into its
metastable extension -- only FCC_A1 ever forms, the Cu-rich solid never
appears. Molten metal at 600 K is not a result.

So the higher limit trades an obvious failure for a deceptive one. At 500
the run stops with an error and nobody is misled; at 5000 it produces 268
points and a smooth curve that reads as a finished solidification. An
obvious gap is safer than a plausible fabrication, which is the same
principle the "completed" field exists to serve.

Raising it becomes the right move only alongside a check that finds where
the path leaves reality -- each point carries a liquid composition and a
temperature, so asking whether that composition is actually liquid at that
temperature is one ordinary equilibrium, and a binary search over the tail
would locate the departure in a handful of calls. That check is the
prerequisite, not an accompaniment. Until it exists the limit stays at its
default, and the parameter is not offered to callers either: a knob whose
main effect is better-looking wrong answers should not be within reach.

Macro form follows the distribution's own examples/macros/step-scheil.OCM:
the "set c" shorthand on one line, the axis given as separate lines
ending with the STEP (not a point count), "step scheil" as a single
command, and two confirmations. Getting the axis wrong -- passing a point
count where a step belongs -- is what made an earlier attempt at this
conclude, incorrectly, that ternary systems could not be simulated at all.
"""
import os
import re
import shutil
import subprocess
import tempfile
import time

import native_fallback

OC_BINARY = native_fallback.OC_BINARY
OC_BUILD_DIR = native_fallback.OC_BUILD_DIR

# The step ladder and the completion threshold are in
# settings/execution.toml under [scheil], with the measurements that chose
# them. Read through functions rather than bound at import: this module is
# imported by settings_engine's own dependency chain, and a module-level
# read would run before the policy exists.


def _scheil_setting(key, default):
    try:
        import settings_engine
        deger = settings_engine.POLICY.execution.scheil.get(key)
        return default if deger is None else deger
    except Exception:                                    # noqa: BLE001
        return default


def step_ladder():
    """Temperature steps to try, best first."""
    return tuple(float(x) for x in _scheil_setting("step_ladder_K",
                                                   (5.0, 2.0, 1.0)))


def complete_below_per_cent():
    """Below this the melt counts as spent."""
    return float(_scheil_setting("complete_below_per_cent", 1.0))

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


SCHEIL_TIMEOUT_S = _policy_number("timeouts", "scheil_s", 180)
REAP_TIMEOUT_S = _policy_number("timeouts", "process_reap_s", 5)


_LIQUID_LINE = re.compile(r"^\s*Liquid:\s+([\d.]+)%\s+([\d.]+):\s*(.*)$")
_NODE_LINE = re.compile(r"Creating a node at\s+([\d.]+)\s+where\s+(\S+)\s+appears")
_STORE_ERROR = re.compile(r"Error storing equilibria\s+(\d+)")
_LINE_ERROR = re.compile(r"Terminating line with\s+\d+\s+equilibria.*due to error\s+(\d+)")


class ScheilError(Exception):
    """Raised when the simulation could not be run at all."""


def generate_scheil_macro(db_path, elements_composition, seed_temperature_K,
                          temperature_min_K, temperature_step_K, pressure_Pa):
    """Build the STEP SCHEIL macro, and say which columns its output will carry.

    Returns (macro_text, independent_elements). The second value is not
    decoration: the simulation prints the remaining liquid's composition as
    bare numbers with no headers, one per element that got an x(...)
    condition, in the order those conditions were written. Without that
    order the numbers cannot be attached to elements.
    """
    total = sum(elements_composition.values())
    if total <= 0:
        raise ScheilError("Composition amounts must sum to something positive.")
    fractions = {el.upper(): amount / total
                 for el, amount in elements_composition.items()}
    if len(fractions) < 2:
        raise ScheilError("Scheil needs at least two elements.")

    # The largest element is left dependent, exactly as elsewhere in this
    # project -- it carries the remainder and gets no condition of its own.
    dependent = max(fractions, key=fractions.get)
    independents = [el for el in fractions if el != dependent]

    condition = " ".join(
        f"x({el.lower()})={fractions[el]:.10g}" for el in independents
    )
    stem = os.path.splitext(os.path.basename(db_path))[0]
    elements_line = " ".join(fractions)

    macro = (
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
        f"{elements_line}\n"
        "\n"
        "\n"
        "\n"
        "\n"
        f"set c t={seed_temperature_K:.10g} p={pressure_Pa:.10g} n=1 {condition}\n"
        "\n"
        "c e\n"
        "\n"
        "set ax 1 t\n"
        f"{temperature_min_K:.10g}\n"
        f"{seed_temperature_K:.10g}\n"
        f"{temperature_step_K:.10g}\n"
        "\n"
        # One command, then the engine's own two confirmations. It states
        # its preconditions (composition set, an equilibrium in the liquid,
        # a T axis) and defaults to NO, so an unanswered prompt silently
        # abandons the simulation rather than failing.
        "step scheil\n"
        "Y\n"
        "y\n"
        "\n"
    )
    return macro, independents


def run_native_scheil(db_path, elements_composition, seed_temperature_K,
                      temperature_min_K, temperature_step_K, pressure_Pa,
                      timeout=SCHEIL_TIMEOUT_S, max_bytes=4_000_000):
    """Run one simulation and return (raw_text, independent_elements).

    Bounded in both time and bytes and then killed, for the reason
    native_fallback documents: the engine loops on its own prompt once a
    macro ends, so the run is never waited on -- it is read until the
    result is in hand and stopped.
    """
    if not os.path.isfile(OC_BINARY):
        raise ScheilError(f"Native OC binary not found: {OC_BINARY}")

    macro, independents = generate_scheil_macro(
        db_path, elements_composition, seed_temperature_K,
        temperature_min_K, temperature_step_K, pressure_Pa,
    )

    workdir = tempfile.mkdtemp(prefix="oc_scheil_")
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
        return "".join(chunks), independents
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def parse_scheil_output(raw_text, independent_elements):
    """Turn one simulation's screen output into a solidification path.

    The progress lines look like

        Liquid:  96.43% 1180.61:    0.1020

    and for a multicomponent alloy carry one composition value per
    independent element, unheaded, in condition order.

    Returns a dict. "completed" answers the only question that decides
    whether the curve can be read as a whole story: did the melt actually
    run out, or did the simulation stop with liquid still in it.
    """
    points = []
    for line in raw_text.splitlines():
        found = _LIQUID_LINE.match(line)
        if not found:
            continue
        per_cent = float(found.group(1))
        temperature = float(found.group(2))
        values = []
        for token in found.group(3).split():
            try:
                values.append(float(token))
            except ValueError:
                break
        composition = {
            element: value
            for element, value in zip(independent_elements, values)
        }
        points.append({
            "temperature_K": temperature,
            "liquid_fraction": per_cent / 100.0,
            "liquid_composition": composition,
        })

    # The first node is where the first solid appears -- the liquidus for
    # this alloy, and a number the caller would otherwise have to guess.
    liquidus_K = None
    solid_phases = []
    for found in _NODE_LINE.finditer(raw_text):
        if liquidus_K is None:
            liquidus_K = float(found.group(1))
        name = found.group(2)
        if name not in solid_phases:
            solid_phases.append(name)

    completed = "liquid fraction less than 1%" in raw_text
    final = points[-1] if points else None
    if final is not None and final["liquid_fraction"] * 100 < complete_below_per_cent():
        completed = True

    reason = None
    if not completed:
        store = _STORE_ERROR.search(raw_text)
        node = _LINE_ERROR.search(raw_text)
        if store and store.group(1) == "4204":
            reason = ("the equilibrium solver stopped converging as the "
                      "remaining liquid became extreme (engine error 4204, "
                      "too many iterations)")
        elif node:
            reason = (f"the simulation could not resolve a phase change "
                      f"along the path (engine error {node.group(1)})")
        elif not points:
            reason = ("the simulation produced no points -- the seed "
                      "equilibrium may not be in the single-phase liquid")
        else:
            reason = "the simulation stopped before the melt was spent"

    return {
        "points": points,
        "liquidus_K": liquidus_K,
        "solid_phases": solid_phases,
        "completed": completed,
        "final_liquid_fraction": final["liquid_fraction"] if final else None,
        "final_temperature_K": final["temperature_K"] if final else None,
        "termination_reason": reason,
    }


def run_with_step_ladder(db_path, elements_composition, seed_temperature_K,
                         temperature_min_K, pressure_Pa,
                         temperature_step_K=None, timeout=SCHEIL_TIMEOUT_S):
    """Run the simulation, trying several temperature steps, and keep the best.

    "Best" needs no judgement: the run that leaves the least liquid
    unsolidified got furthest along the same path. See the module docstring
    for why one fixed step will not do -- neighbouring step sizes give
    unrelated results and nothing observable says in advance which will
    work.

    Pass temperature_step_K to run exactly one step and skip the ladder,
    for a caller who already knows what their system wants.

    Returns the winning parse, with the ladder recorded in it: the step it
    used, and what every step tried achieved. That record is the evidence
    for the number returned, and it is cheap to carry.
    """
    ladder = ((float(temperature_step_K),) if temperature_step_K
              else step_ladder())

    attempts = []
    best = None
    for step in ladder:
        try:
            raw, independents = run_native_scheil(
                db_path, elements_composition, seed_temperature_K,
                temperature_min_K, step, pressure_Pa, timeout=timeout,
            )
            result = parse_scheil_output(raw, independents)
        except ScheilError:
            raise
        except Exception as exc:
            attempts.append({"temperature_step_K": step, "error": str(exc)})
            continue

        remaining = result["final_liquid_fraction"]
        attempts.append({
            "temperature_step_K": step,
            "points": len(result["points"]),
            "final_liquid_fraction": remaining,
            "completed": result["completed"],
        })

        if result["points"] and (
            best is None
            or best["final_liquid_fraction"] is None
            or (remaining is not None and remaining < best["final_liquid_fraction"])
        ):
            best = result
            best["temperature_step_K"] = step

        if result["completed"]:
            break  # the melt is spent; a finer step has nothing left to find

    if best is None:
        raise ScheilError(
            "The Scheil simulation produced no solidification path at any "
            f"temperature step tried ({', '.join(f'{s:g} K' for s in ladder)}). "
            "The seed temperature may not be in the single-phase liquid region."
        )
    best["steps_tried"] = attempts
    return best
