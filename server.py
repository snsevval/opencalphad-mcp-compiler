"""MCP server exposing OpenCalphad (via OCASI/pyOC) as tools for an AI assistant.

See the plan at
C:\\Users\\sevval\\.claude\\plans\\imd-benim-amac-m-opencalpha-buzzing-pancake.md
for the wider architecture.

Every equilibrium calculation runs in its own subprocess (see
run_equilibrium.py) because the underlying Fortran engine can segfault on
non-converging inputs; that must not be allowed to take the whole MCP
server down. calculate_property_diagram and compare_alloys are built on top
of that same single-point primitive, so a bad point among many still fails
in isolation instead of aborting the whole call.

Request pipeline (see the plan file, Faz 10): every calculation tool runs
PREFLIGHT before touching an engine and VERIFY A on whatever comes back.
PREFLIGHT rejects impossible requests (element not in the database, bad
composition, inverted temperature range) for free, instead of letting
OCASI discover them the expensive way -- that class of mistake is exactly
what caused this project's earlier segfaults. VERIFY A then runs the same
deterministic structural checks (result_check.py) that the verification
loop uses, so a result reaching the user has been checked by the same
rules the test harness applies -- and says so, via the "verification"
field it attaches.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
from typing import Optional

from mcp.server.fastmcp import FastMCP, Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import oc_service  # noqa: E402
import native_step  # noqa: E402
import preflight  # noqa: E402
import result_check  # noqa: E402
import semantic_check  # noqa: E402
import failure_classify  # noqa: E402

mcp = FastMCP("opencalphad")

# Layer B costs a round trip to an external model (~12s measured), so it
# is opt-out rather than mandatory -- set OC_SEMANTIC_CHECK=0 to skip it
# when latency matters more than the second opinion.
SEMANTIC_CHECK_ENABLED = os.environ.get("OC_SEMANTIC_CHECK", "1") != "0"
# DEBUGGER: classify a verification failure and, where a retry is honest,
# close the loop. Off switch kept because it is the only stage that can
# issue a second outbound call after the result already exists.
DEBUGGER_ENABLED = os.environ.get("OC_DEBUGGER", "1") != "0"

# How long one equilibrium subprocess may run before it is killed. It was
# 60s -- the same figure the MCP client used for its own per-request
# timeout, so a slow calculation lost twice over. steel7's six-element
# system at 1173 K sat right on that line: the client gave up at exactly
# 60s, and the model, seeing a timeout rather than a result, simply
# reissued the identical call. Raised here and to 300s in the client, so
# the two limits are no longer racing. A ceiling, not a target -- a
# calculation that needs minutes is saying something about the system, and
# the timeout message still says which combination did it.
CALC_TIMEOUT_S = int(os.environ.get("OC_CALC_TIMEOUT_S", "300"))


def _element_distribution(result: dict, elements_composition: dict) -> Optional[dict]:
    """How much of each requested element ended up in which phase.

    Arithmetic on the engine's own output -- phase amount times the
    element's fraction inside that phase -- and no new claim about the
    chemistry. It is here because leaving the multiplication to the reader
    was measured to go wrong: asked the same question twice, the client
    model reported once that molybdenum had collected in the carbide (it
    had: 65%) and once that it had collected in a phase holding 2% of it.
    A phase can hold a high CONCENTRATION of an element while holding
    almost none of its total AMOUNT, because the phase itself is tiny --
    here a phase making up 0.17% of the system carried a third of the
    vanadium by concentration and half of it by amount.

    Phases come sorted by amount, so "where is most of it" is read off the
    first entry rather than derived.

    `total` against `requested` is also the check Layer A never had: an
    element whose total comes back at zero never entered the calculation,
    whatever the composition tables look like. The native fallback is
    known to drop elements it cannot write into its macro, and nothing
    downstream would otherwise notice.
    """
    amounts = result.get("phase_molar_amounts") or {}
    per_phase = result.get("phase_element_composition") or {}
    if not amounts or not per_phase:
        return None

    # The engine normalizes the composition, so compare like with like.
    scale = sum(elements_composition.values())
    if scale <= 0:
        return None

    distribution = {}
    for element, requested in elements_composition.items():
        symbol = element.upper()
        shares = {}
        for phase, phase_amount in amounts.items():
            fraction = (per_phase.get(phase) or {}).get(symbol)
            if fraction:
                shares[phase] = phase_amount * fraction
        # Six significant figures, not six decimals: a trace element's
        # share runs to 1e-6 and fixed rounding would erase it. Float
        # noise like 0.7898059025999999 otherwise travels into the answer
        # and implies precision the engine never claimed.
        distribution[symbol] = {
            "by_phase": {
                phase: float(f"{value:.6g}")
                for phase, value in sorted(shares.items(), key=lambda kv: -kv[1])
            },
            "total": float(f"{sum(shares.values()):.6g}"),
            "requested": float(f"{requested / scale:.6g}"),
        }
    return distribution


def _preflight_failure(problems: list) -> dict:
    """Shape a PREFLIGHT rejection the same way every tool reports it, so
    a client can tell "this request was never run" apart from "it ran and
    failed" by the stage field alone."""
    return {
        "error": "Request rejected before calculation: " + "; ".join(problems),
        "stage": "PREFLIGHT",
        "problems": problems,
    }


def _attach_verification(result: dict, request_args: Optional[dict] = None) -> dict:
    """Run VERIFY A (and VERIFY B when enabled) and record the outcome.

    Deliberately non-destructive: a result that fails a check is still
    returned with its numbers intact, flagged rather than replaced. The
    caller asked for a calculation and the engine produced one; hiding it
    would remove the very evidence needed to judge what went wrong.

    Layer B runs only if Layer A passed -- there is no point paying for an
    outside opinion on a result already known to be malformed -- and its
    outcome is recorded separately from Layer A's. Crucially, a Layer B
    that could not be reached (the free tier returns 529 unpredictably) is
    reported as unavailable, never as disapproval: NVIDIA's capacity must
    not turn into a false alarm about the user's chemistry.
    """
    passed, problems = result_check.verify_result(result)
    verification = {
        "stage": "VERIFY_A",
        "passed": passed,
        "problems": problems,
    }

    if passed and SEMANTIC_CHECK_ENABLED and request_args is not None:
        review = semantic_check.review(request_args, result)
        verification["layer_b"] = review
        _apply_review(verification, review, problems)

    result["verification"] = verification

    # ---- DEBUGGER + RE-VERIFY -------------------------------------
    # Everything above is a pipeline: it reports what happened and stops.
    # This closes it into a loop for the one failure class where a retry
    # is honest. failure_classify says which class we are in and whether
    # anything can be done; only a review that produced no usable verdict
    # gets retried, and only against a DIFFERENT reviewer. The numbers are
    # never recomputed -- the calculation is deterministic, so re-running
    # it would return the same result and the same verdict.
    if DEBUGGER_ENABLED and request_args is not None:
        failure = failure_classify.classify(result)
        if failure is not None:
            result["failure"] = failure
            if failure.get("strategy") == failure_classify.STRATEGY_RETRY_REVIEWER:
                _retry_review(result, verification, request_args, problems)

    return result


def _apply_review(verification: dict, review: dict, problems: list) -> None:
    """Fold a Layer B outcome into the verification record. A reviewer that
    objected fails the result; a reviewer that could not be reached, or
    whose verdict could not be read, leaves Layer A's decision standing --
    an absent opinion is not a negative one."""
    if review.get("available") and review.get("passed") is False:
        verification["passed"] = False
        verification["stage"] = "VERIFY_A+B"
        verification["problems"] = problems + [
            "Bağımsız model denetimi sonucu makul bulmadı: "
            + review.get("reason", "")[:500]
        ]
    elif review.get("available"):
        verification["stage"] = "VERIFY_A+B"


def _retry_review(result: dict, verification: dict, request_args: dict,
                  problems: list) -> None:
    """Ask the rest of the reviewer chain, skipping whoever already failed
    to produce a usable verdict. Records the attempt either way, so a
    result never silently gains (or loses) an independent review."""
    first = verification.get("layer_b") or {}
    tried = [m for m in [first.get("model_used")] if m]
    retry = semantic_check.review(request_args, result, skip_models=tried)

    attempt = {
        "stage": "DEBUGGER",
        "category": result["failure"]["category"],
        "skipped_models": tried,
        "layer_b_retry": retry,
    }
    if retry.get("available") and retry.get("passed") is not None:
        verification["layer_b"] = retry
        _apply_review(verification, retry, problems)
        attempt["outcome"] = "resolved"
        # The retry answered, so the original failure no longer stands.
        result.pop("failure", None)
        residual = failure_classify.classify(result)
        if residual is not None:
            result["failure"] = residual
    else:
        attempt["outcome"] = "unresolved"
    verification["debugger"] = attempt


def _calc_one(
    database: str,
    elements_composition: dict,
    temperature_K: float,
    pressure_Pa: float = 1e5,
    suspended_phases: Optional[list] = None,
) -> dict:
    """Run one single-point equilibrium in an isolated subprocess."""
    payload = {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_K": temperature_K,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": suspended_phases,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "result.json")
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(HERE, "run_equilibrium.py"), out_path],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=os.environ,
                timeout=CALC_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return {
                "error": (
                    f"Equilibrium calculation timed out after {CALC_TIMEOUT_S} "
                    "seconds and was "
                    "killed. This database/composition/temperature combination "
                    "likely does not converge."
                )
            }
        if os.path.exists(out_path):
            with open(out_path) as f:
                return json.load(f)
        return {
            "error": (
                f"Equilibrium calculation crashed (exit code {proc.returncode}). "
                "This usually means the calculation did not converge for this "
                "database/composition/temperature combination."
            ),
            "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
        }


@mcp.tool()
def list_databases(directory: Optional[str] = None) -> list[dict]:
    """List available thermodynamic (.TDB) databases with their elements.

    Args:
        directory: optional folder to scan; defaults to the standard
            OpenCalphad macros/databases folder.
    """
    return oc_service.list_databases(directory or oc_service.DEFAULT_DB_DIR)


@mcp.tool()
def inspect_database(database: str, directory: Optional[str] = None) -> dict:
    """Get the elements and phase names declared inside one .TDB database.

    Use this before calculate_equilibrium/suspend a phase, to see valid
    element symbols and exact phase names (e.g. to know it's "GRAPHITE" and
    not "GRAPHITE_A9") for that specific database.

    Args:
        database: database filename (e.g. "steel7.TDB") or full path.
        directory: optional folder to resolve a bare filename against;
            defaults to the standard OpenCalphad macros/databases folder.
    """
    return oc_service.inspect_database(database, directory or oc_service.DEFAULT_DB_DIR)


@mcp.tool()
def calculate_equilibrium(
    database: str,
    elements_composition: dict[str, float],
    temperature_K: float,
    pressure_Pa: float = 1e5,
    suspended_phases: Optional[list[str]] = None,
) -> dict:
    """Calculate a single-point thermodynamic equilibrium with OpenCalphad.

    PREFLIGHT REJECTION — STOP RULE
    If the result has stage="PREFLIGHT", the request was refused before any
    calculation ran. When that happens:
      1. Do NOT call this or any other calculation tool again in this turn.
      2. Quote the rejection reason to the user, including any list of valid
         elements or phases it names.
      3. Ask which corrected request they want. Naming options is fine;
         running one is not.
    The user asked a specific question. Computing a different one — even a
    near-identical one, even while announcing the change — hands them a
    result they did not ask for.

    Args:
        database: database filename (e.g. "steel7.TDB") or full path.
        elements_composition: element symbol -> molar amount, e.g.
            {"FE": 0.95, "C": 0.05}. Does not need to be pre-normalized.
            Must include at least two elements with a nonzero amount — a
            pure single-element composition (e.g. only {"FE": 1.0}) is
            rejected, since it puts this engine's condition system into an
            unstable state. For a near-pure system, add a second element
            with a small nonzero amount (e.g. {"FE": 0.999, "C": 0.001}).
        temperature_K: temperature in Kelvin.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).
        suspended_phases: phase names to exclude from the calculation
            (e.g. ["GRAPHITE"]) — this is how you turn a phase "off".
            Must be phases the database actually declares; use
            inspect_database to see them. A name the database does not
            declare is rejected rather than silently ignored.

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran on it before handing it back -- phase fractions
    summing to one, values in range, no NaN, and for a sweep, how many
    points actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    problems = preflight.check_equilibrium_request(
        database, elements_composition, temperature_K, pressure_Pa, suspended_phases
    )
    if problems:
        return _preflight_failure(problems)

    result = _calc_one(
        database, elements_composition, temperature_K, pressure_Pa, suspended_phases
    )
    distribution = _element_distribution(result, elements_composition)
    if distribution is not None:
        result["element_distribution"] = distribution
    return _attach_verification(result, {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_K": temperature_K,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": suspended_phases,
    })


@mcp.tool()
def compare_alloys(
    database: str,
    composition_a: dict[str, float],
    composition_b: dict[str, float],
    temperature_K: float,
    pressure_Pa: float = 1e5,
    suspended_phases: Optional[list[str]] = None,
    label_a: str = "A",
    label_b: str = "B",
) -> dict:
    """Calculate equilibrium for two compositions at the same T/P and compare them.

    PREFLIGHT REJECTION — STOP RULE
    If the result has stage="PREFLIGHT", the request was refused before any
    calculation ran. Do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason to the user (including any list of
    valid elements or phases it names) and ask which corrected request they
    want. Naming options is fine; running one is not.

    Useful for questions like "suspend graphite and compare to the normal
    result" (call this twice with suspended_phases set only for B), or
    "how does adding more Cr change the stable phases".

    Args:
        database: database filename or full path, shared by both calculations.
        composition_a: element -> molar amount for the first alloy.
        composition_b: element -> molar amount for the second alloy.
        temperature_K: temperature in Kelvin, shared by both calculations.
        pressure_Pa: pressure in Pascal, shared by both calculations.
        suspended_phases: phase names to exclude, shared by both calculations.
            Must be phases the database actually declares.
        label_a: short label for composition_a in the result (e.g. "with C").
        label_b: short label for composition_b in the result (e.g. "no C").

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran on it before handing it back -- phase fractions
    summing to one, values in range, no NaN, and for a sweep, how many
    points actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    problems = (
        preflight.check_equilibrium_request(
            database, composition_a, temperature_K, pressure_Pa, suspended_phases
        )
        + preflight.check_equilibrium_request(
            database, composition_b, temperature_K, pressure_Pa, suspended_phases
        )
    )
    if problems:
        return _preflight_failure(problems)

    # Both sides get the same verification treatment. That means two Layer B
    # round trips when it's enabled, which roughly doubles this tool's
    # latency -- accepted rather than special-cased, since a comparison
    # whose two halves were checked differently would be worth less than
    # the seconds saved. OC_SEMANTIC_CHECK=0 turns it off when that matters.
    def _args_for(composition):
        return {
            "database": database,
            "elements_composition": composition,
            "temperature_K": temperature_K,
            "pressure_Pa": pressure_Pa,
            "suspended_phases": suspended_phases,
        }

    result_a = _attach_verification(
        _calc_one(database, composition_a, temperature_K, pressure_Pa, suspended_phases),
        _args_for(composition_a),
    )
    result_b = _attach_verification(
        _calc_one(database, composition_b, temperature_K, pressure_Pa, suspended_phases),
        _args_for(composition_b),
    )

    if "error" in result_a or "error" in result_b:
        comparison = {
            "note": (
                "Comparison skipped because at least one side failed to "
                f"converge — see the '{label_a}'/'{label_b}' error field above."
            )
        }
    else:
        phases_a = set(result_a["phase_molar_amounts"])
        phases_b = set(result_b["phase_molar_amounts"])
        comparison = {
            "gibbs_energy_difference_J": result_b["gibbs_energy_J"] - result_a["gibbs_energy_J"],
            "phases_only_in_" + label_a: sorted(phases_a - phases_b),
            "phases_only_in_" + label_b: sorted(phases_b - phases_a),
            "phases_in_both": sorted(phases_a & phases_b),
        }

    return {
        label_a: result_a,
        label_b: result_b,
        "comparison": comparison,
    }


@mcp.tool()
def calculate_property_diagram(
    database: str,
    elements_composition: dict[str, float],
    temperature_min_K: float,
    temperature_max_K: float,
    n_points: int = 15,
    pressure_Pa: float = 1e5,
    suspended_phases: Optional[list[str]] = None,
):
    """Sweep temperature and calculate a phase diagram over that range.

    PREFLIGHT REJECTION — STOP RULE
    If the result has stage="PREFLIGHT", the request was refused before any
    calculation ran. Do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason to the user (including any list of
    valid elements or phases it names) and ask which corrected request they
    want. Naming options is fine; running one is not.

    Primary method: runs OpenCalphad's own native STEP algorithm (the same
    continuation-based calculation its GUI uses), rendered with real
    gnuplot. STEP's internal solver can fail to converge at some
    temperatures (a known engine limitation, unrelated to this specific
    composition/database); any such gaps are transparently filled in with
    independent single-point native equilibrium calls so the chart has no
    holes -- each returned point says whether it came from "step" or
    "native_fallback". If the native STEP/gnuplot path fails entirely (or
    suspended_phases is given, which it doesn't support yet), this falls
    back to the original method: repeating calculate_equilibrium across the
    range and plotting with matplotlib (phase molar amount on top, Gibbs
    energy on the bottom -- the Gibbs panel keeps the chart informative
    even when the system stays single-phase the whole way through).
    Either way, the returned chart is the complete, intended visualization
    for this data — present it as-is rather than building a separate plot
    yourself.

    Args:
        database: database filename or full path.
        elements_composition: element -> molar amount (same rules as
            calculate_equilibrium — at least two nonzero elements).
        temperature_min_K: lower end of the temperature sweep, in Kelvin.
        temperature_max_K: upper end of the temperature sweep, in Kelvin.
        n_points: how many temperature points to sample (default 15). Keep
            this modest (<=30) — each point may require its own calculation.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).
        suspended_phases: phase names to exclude from the calculation.
            Must be phases the database actually declares. Only supported
            by the matplotlib fallback (native STEP path is skipped
            entirely when this is given).

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran on it before handing it back -- phase fractions
    summing to one, values in range, no NaN, and for a sweep, how many
    points actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    if n_points < 2:
        n_points = 2

    problems = preflight.check_property_diagram_request(
        database, elements_composition, temperature_min_K, temperature_max_K,
        pressure_Pa, suspended_phases,
    )
    if problems:
        return _preflight_failure(problems)

    _diagram_args = {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_min_K": temperature_min_K,
        "temperature_max_K": temperature_max_K,
        "n_points": n_points,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": suspended_phases,
    }

    if not suspended_phases:
        try:
            db_path = (
                database if os.path.isabs(database)
                else os.path.join(oc_service.DEFAULT_DB_DIR, database)
            )
            combined, gap_filled_temperatures = native_step.build_combined_series(
                db_path, elements_composition, temperature_min_K,
                temperature_max_K, n_points, pressure_Pa,
            )
            chart_title = f"{os.path.basename(database)} property diagram"
            with tempfile.TemporaryDirectory() as tmpdir:
                png_path = os.path.join(tmpdir, "diagram.png")
                chart_bytes = native_step.render_gnuplot_png(
                    combined, chart_title, png_path,
                )
            points = [
                {
                    "temperature_K": T,
                    "phase_molar_amounts": fractions,
                    "source": source,
                }
                for T, fractions, source in combined
            ]
            window_opened = native_step.open_interactive_window(combined, chart_title)
            data = {
                "database": os.path.basename(database),
                "composition": elements_composition,
                "pressure_Pa": pressure_Pa,
                "suspended_phases": [],
                "points": points,
                "backend_used": "native_oc_step_gnuplot",
                "interactive_window_opened": window_opened,
                "native_step_points": len(combined) - len(gap_filled_temperatures),
                "gap_filled_points": len(gap_filled_temperatures),
                "note": (
                    "Phase values from OpenCalphad's native STEP are mass "
                    "fractions; temperatures where STEP's own solver could "
                    "not converge were filled in with independent "
                    "single-point native equilibrium calls instead (molar "
                    "amounts) so the chart has no gaps -- both are scaled "
                    "0-1 and shown together as an approximation, see each "
                    "point's 'source' field."
                ),
                "chart_error": None,
            }
            return [
                _attach_verification(data, _diagram_args),
                Image(data=chart_bytes, format="png"),
            ]
        except Exception as exc:
            native_backend_error = str(exc)
    else:
        native_backend_error = (
            "native STEP backend does not support suspended_phases yet; "
            "used the matplotlib fallback instead."
        )

    step = (temperature_max_K - temperature_min_K) / (n_points - 1)
    temperatures = [temperature_min_K + i * step for i in range(n_points)]

    points = []
    phase_series: dict[str, list] = {}
    for T in temperatures:
        result = _calc_one(database, elements_composition, T, pressure_Pa, suspended_phases)
        if "error" in result or not result.get("phase_molar_amounts"):
            points.append({
                "temperature_K": T,
                "error": result.get("error") or (
                    "Calculation returned no stable phases (likely an "
                    "unreliable/degenerate solve at this point)."
                ),
            })
            continue
        amounts = result["phase_molar_amounts"]
        points.append({
            "temperature_K": T,
            "gibbs_energy_J": result["gibbs_energy_J"],
            "phase_molar_amounts": amounts,
        })
        for phase in amounts:
            phase_series.setdefault(phase, [None] * n_points)

    for i, point in enumerate(points):
        amounts = point.get("phase_molar_amounts", {})
        for phase, series in phase_series.items():
            series[i] = amounts.get(phase, 0.0) if "error" not in point else None

    gibbs_series = [
        p["gibbs_energy_J"] if "error" not in p else None for p in points
    ]

    chart_bytes = None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Two panels always: phase molar amount (top) and Gibbs energy
        # (bottom). A single-phase sweep makes the top panel a flat line,
        # but the bottom panel (which always varies with T) keeps the chart
        # informative on its own, without needing a second, separate plot.
        fig, (ax_phase, ax_gibbs) = plt.subplots(
            2, 1, figsize=(7, 7), sharex=True, height_ratios=[1.2, 1]
        )
        for phase, series in phase_series.items():
            ax_phase.plot(temperatures, series, marker="o", label=phase)
        ax_phase.set_ylabel("Phase molar amount")
        ax_phase.set_title(f"{os.path.basename(database)} property diagram")
        ax_phase.legend(fontsize="small")
        ax_phase.grid(True, alpha=0.3)

        ax_gibbs.plot(temperatures, gibbs_series, marker="o", color="tab:red")
        ax_gibbs.set_xlabel("Temperature (K)")
        ax_gibbs.set_ylabel("Gibbs energy (J/mol)")
        ax_gibbs.grid(True, alpha=0.3)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        plt.close(fig)
        chart_bytes = buf.getvalue()
    except Exception as exc:  # chart is a bonus, never fail the whole call over it
        chart_error = str(exc)
    else:
        chart_error = None

    data = {
        "database": os.path.basename(database),
        "composition": elements_composition,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": list(suspended_phases) if suspended_phases else [],
        "points": points,
        "backend_used": "python_loop_matplotlib",
        "native_backend_error": native_backend_error,
        "chart_error": chart_error,
    }
    _attach_verification(data, _diagram_args)
    if chart_bytes:
        return [data, Image(data=chart_bytes, format="png")]
    return data


if __name__ == "__main__":
    mcp.run(transport="stdio")
