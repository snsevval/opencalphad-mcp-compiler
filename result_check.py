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


# ── CORRESPONDENCE ───────────────────────────────────────────────────
# A different question from the structural checks above, and kept apart
# for that reason. Those ask "is this a well-formed thermodynamic
# result?"; these ask "is it a result for the question that was asked?"
#
# Nothing in this server asked the second question until now. A
# calculation could return phase fractions summing perfectly to one,
# every value in range, no NaN -- and describe a different system than
# the caller requested. That has happened: with PREFLIGHT disabled, a
# request for Fe-0.1Ni came back as pure iron, structurally flawless,
# because the native macro silently dropped the element it could not
# write. PREFLIGHT now catches that particular case upstream, but only
# that one: it can tell an element is not in the database, not that an
# element which IS in the database failed to reach the calculation.
#
# Availability differs by engine tier and is reported rather than
# papered over. Two of these checks read the native engine's own printed
# account of the conditions it used; OCASI is called through function
# arguments and produces no such account, so there is nothing to read
# back. That asymmetry is proportionate rather than a gap -- the failure
# those two checks guard against (a macro line swallowed by an
# interactive prompt, which has happened repeatedly in this project)
# cannot occur on a path that has no text to parse.

MASS_BALANCE_TOLERANCE = 2e-4


def check_requested_elements(result, request_args):
    """Every requested element must appear somewhere in the result.

    An element absent from every phase composition was not part of the
    calculation, whatever the numbers look like.
    """
    requested = {e.upper() for e in (request_args.get("elements_composition") or {})}
    if not requested:
        return []
    per_phase = result.get("phase_element_composition") or {}
    if not per_phase:
        return []
    seen = set()
    for composition in per_phase.values():
        seen |= {e.upper() for e in composition}
    problems = []
    missing = sorted(requested - seen)
    if missing:
        problems.append(
            f"Requested element(s) {missing} appear in no phase composition -- "
            "they were not part of the calculation."
        )

    # The other direction, which the first version of this check left out.
    # A result holding an element nobody asked for is describing a
    # different system. Observed: steel1 at 1e9 Pa returned FE4N as the
    # only phase -- an iron nitride, in a database whose elements are
    # C, CR, FE, MO, SI, V. There is no nitrogen to make it from. The
    # numbers were well-formed and every other check passed.
    unexpected = sorted(seen - requested)
    if unexpected:
        # Capped because one failure mode makes this list very long and
        # says the same thing every time: a gas phase reports molecular
        # species rather than elements, so CHO-gas comes back holding H2,
        # C1O1, C1O2 and thirty more. The count is the signal there, not
        # the enumeration.
        shown = unexpected[:8]
        more = "" if len(unexpected) <= 8 else f" (+{len(unexpected) - 8} more)"
        problems.append(
            f"Result contains {len(unexpected)} constituent(s) that were "
            f"not requested: {shown}{more} -- the calculation was not run "
            "on the system asked for."
        )
    return problems


def check_mass_balance(result, request_args):
    """Each element's amount, summed over the phases, must match the request.

    Stronger than presence: an element can appear and still be there in the
    wrong quantity. Phase amount times the element's fraction within that
    phase, summed, is the total the engine actually placed -- and it has to
    equal what was asked for, once the request is normalised the way the
    engine normalises it.
    """
    composition = request_args.get("elements_composition") or {}
    amounts = result.get("phase_molar_amounts") or {}
    per_phase = result.get("phase_element_composition") or {}
    if not composition or not amounts or not per_phase:
        return []
    scale = sum(composition.values())
    if scale <= 0:
        return []

    problems = []
    for element, requested in composition.items():
        symbol = element.upper()
        placed = sum(
            amount * (per_phase.get(phase) or {}).get(symbol, 0.0)
            for phase, amount in amounts.items()
        )
        wanted = requested / scale
        if abs(placed - wanted) > MASS_BALANCE_TOLERANCE:
            problems.append(
                f"Mass balance for {symbol}: phases hold {placed:.6g}, "
                f"request was {wanted:.6g}."
            )
    return problems


def check_suspended_phases_absent(result, request_args):
    """A phase the request suspended must not be in the result.

    The engine can swallow a suspension request and return the stable
    equilibrium instead -- a different question than the metastable one
    that was asked. Observed on agcu.TDB, which declares no GRAPHITE: the
    request was ignored and the client model then reported that graphite
    had been suppressed.
    """
    suspended = request_args.get("suspended_phases") or []
    if not suspended:
        return []
    amounts = result.get("phase_molar_amounts") or {}
    present = [name for name in suspended if name in amounts]
    if present:
        return [
            f"Phase(s) {sorted(present)} were requested suspended but appear "
            "in the result -- the suspension did not take effect."
        ]
    return []


def check_reported_conditions(result, request_args):
    """Compare the engine's own account of its conditions with the request.

    Native prints what it understood before it prints the answer:

        Conditions ...: 1:T=1200, 2:P=100000, 3:N=1, 4:X(C)=.01
        Degrees of freedom are   0

    The form differs from the request on purpose. The macro sends a total
    of one mole plus a mole fraction for each element except the largest,
    which is left dependent -- so a two-element system shows four
    conditions, and an n-element system shows n+2.

    What this catches is not an engine fault but a macro fault: a
    condition line swallowed by one of the engine's own interactive
    prompts. That has happened repeatedly here -- element selection
    needing a blank line, "list,,,," eating the line after it. A swallowed
    composition line does not stop the calculation. The engine solves an
    under-constrained system, prints a well-formed result, and only these
    two lines say so.

    Returns (problems, available). available=False means the tier gave no
    account to read, which is not the same as agreement.
    """
    reported = result.get("reported_conditions")
    if not reported:
        return [], False

    composition = request_args.get("elements_composition") or {}
    problems = []

    for key, requested in (("T", request_args.get("temperature_K")),
                           ("P", request_args.get("pressure_Pa"))):
        if requested is None or key not in reported:
            continue
        if abs(reported[key] - float(requested)) > 1e-6 * max(1.0, abs(float(requested))):
            problems.append(
                f"Engine used {key}={reported[key]:g}, request was {requested:g}."
            )

    if composition:
        scale = sum(composition.values())
        dependent = max(composition, key=composition.get)
        expected = {
            f"X({el.upper()})": amount / scale
            for el, amount in composition.items() if el != dependent
        }
        for name, fraction in expected.items():
            if name not in reported:
                problems.append(
                    f"Engine reported no condition for {name} -- the "
                    "composition line did not reach it."
                )
            elif abs(reported[name] - fraction) > 1e-6:
                problems.append(
                    f"Engine used {name}={reported[name]:g}, "
                    f"request was {fraction:g}."
                )
        expected_count = len(expected) + 3  # T, P, N, and one X per independent
        if len(reported) != expected_count:
            problems.append(
                f"Engine reported {len(reported)} conditions, "
                f"{expected_count} were sent."
            )

    return problems, True


def check_degrees_of_freedom(result):
    """Zero degrees of freedom means the question was fully determined.

    Anything else means the conditions did not pin the system down and the
    engine chose among a family of solutions. This project spent weeks on
    a segfault whose root cause was exactly that -- a database's six
    elements loaded while only two were constrained -- and the engine
    printed this number every single time.

    Returns (problems, available).
    """
    dof = result.get("degrees_of_freedom")
    if dof is None:
        return [], False
    if dof != 0:
        return [
            f"Degrees of freedom are {dof}, not 0 -- the conditions do not "
            "fully determine the system and the engine chose among several "
            "possible solutions."
        ], True
    return [], True


def verify_correspondence(result, request_args):
    """Does this result answer the request? Returns a report dict.

    Separate from verify_result's return shape on purpose: a check that
    could not be run and a check that passed must not look alike, so the
    report names both what was checked and what was unavailable.
    """
    if not isinstance(result, dict) or "error" in result:
        return None
    if not isinstance(request_args, dict):
        return None

    problems = []
    checked = []
    unavailable = []

    for name, found in (
        ("elements", check_requested_elements(result, request_args)),
        ("mass_balance", check_mass_balance(result, request_args)),
        ("suspended_phases", check_suspended_phases_absent(result, request_args)),
    ):
        checked.append(name)
        problems += found

    for name, (found, available) in (
        ("conditions", check_reported_conditions(result, request_args)),
        ("degrees_of_freedom", check_degrees_of_freedom(result)),
    ):
        if available:
            checked.append(name)
            problems += found
        else:
            unavailable.append(name)

    report = {"passed": not problems, "problems": problems, "checked": checked}
    if unavailable:
        report["unavailable"] = unavailable
        report["unavailable_reason"] = (
            "this engine tier is called through function arguments and "
            "prints no account of the conditions it used"
        )
    return report
