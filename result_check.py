"""VERIFY A (deterministic): universal structural checks on a calculation
result, shared by the live MCP server and the verification loop.

Lives at the project root rather than inside verification/ on purpose:
server.py runs these on every real request, and verification/validator.py
layers its test-only reference-value comparisons on top of the same
functions. Production code must not depend on the test harness, so the
shared part lives here and the harness imports it, not the other way
round.

"Structural" means: checks that hold for ANY thermodynamically sensible
result regardless of database, composition or temperature -- phase
fractions summing to one, values staying inside [0, 1], no NaN, no error
field. Anything that needs a known reference number for a specific case
belongs in verification/, not here.
"""

SUM_TOLERANCE = 1e-3


def check_phase_fraction_sums(result):
    """Wherever phase_molar_amounts appears -- a single-point result, or
    per-point inside a property diagram -- the fractions should sum to ~1
    and each stay within [0, 1]. Returns a list of problem descriptions
    (empty means everything checked out).

    Points that already carry their own "error" are skipped rather than
    reported twice: a temperature the engine couldn't solve is already
    surfaced as that point's error, and re-flagging its (absent) fractions
    would just be noise.
    """
    problems = []

    def _check_one(amounts, where):
        if not amounts:
            return
        total = sum(amounts.values())
        if abs(total - 1.0) > SUM_TOLERANCE:
            problems.append(f"{where}: phase fractions sum to {total:.6f}, not 1.0")
        for name, value in amounts.items():
            if value != value:  # NaN
                problems.append(f"{where}: phase '{name}' is NaN")
            elif not (-1e-9 <= value <= 1.0 + 1e-9):
                problems.append(f"{where}: phase '{name}'={value} outside [0,1]")

    if "phase_molar_amounts" in result:
        _check_one(result["phase_molar_amounts"], "result")
    for point in result.get("points", []):
        if "error" in point:
            continue
        _check_one(point.get("phase_molar_amounts"), f"point T={point.get('temperature_K')}")
    return problems


def check_point_coverage(result, max_failed_fraction=0.10):
    """For property diagrams: how many sampled temperatures actually
    solved. Returns a list of problem descriptions.

    A property diagram where a handful of points failed is still useful
    and is reported as such (each failed point keeps its own error), but
    once a large share of the sweep is missing the chart stops being a
    trustworthy picture of the system -- that's a result worth flagging
    rather than presenting as if it were complete. The 10% default was
    chosen so that the known-good runs in this project (which fill every
    or nearly every point) pass, while a sweep like alni-4slx Al-Ni --
    where roughly a quarter of the temperatures fail to converge -- is
    caught. Before this check existed only the model-based Layer B
    noticed that case.
    """
    points = result.get("points")
    if not points:
        return []
    failed = [p for p in points if "error" in p]
    if not failed:
        return []
    fraction = len(failed) / len(points)
    if fraction > max_failed_fraction:
        temps = [p.get("temperature_K") for p in failed]
        shown = ", ".join(f"{t:g}" for t in temps[:8] if t is not None)
        more = "" if len(temps) <= 8 else f" (+{len(temps) - 8} more)"
        return [
            f"{len(failed)} of {len(points)} temperature points failed to "
            f"converge ({fraction:.0%}): {shown}{more}"
        ]
    return []


def verify_result(result):
    """Run every structural check. Returns (passed, problems)."""
    if not isinstance(result, dict):
        return False, [f"Result is not a dict (got {type(result).__name__})."]
    if "error" in result:
        return False, [f"Result carries an error: {result['error']}"]

    problems = check_phase_fraction_sums(result)
    problems += check_point_coverage(result)
    return (not problems), problems
