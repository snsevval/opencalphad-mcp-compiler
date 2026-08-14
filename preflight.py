"""PREFLIGHT: validate a calculation request before OCASI/native ever
starts (see the plan file, Faz 10).

Deliberately separate from oc_service.calculate_equilibrium's own
internal checks (e.g. "at least 2 nonzero elements") -- this module is
the explicit, named PREFLIGHT_VALIDATION stage of the request state
machine, meant to be called by the verification loop (and usable by
server.py too) as its own step with its own reported outcome, rather than
folded silently into the calculation call.

Every check here is something that can be answered WITHOUT touching
OCASI or the native binaries -- reading the TDB's own element list and
doing arithmetic on the request's numbers. Catching a bad request here is
strictly cheaper and safer than letting OCASI/native discover it (recall:
loading a TDB's declared elements without constraining all of them was
exactly the root cause behind the steel1/steel7 segfaults earlier this
project -- PREFLIGHT's element check exists specifically to catch the
class of mistake that caused that).
"""
import os

import oc_service


class PreflightError(Exception):
    """Raised (or returned as a problem list, see check_*) when a request
    fails validation before any engine is touched."""


def _resolve_db_path(database):
    return database if os.path.isabs(database) else os.path.join(oc_service.DEFAULT_DB_DIR, database)


def _check_common(database, elements_composition, pressure_Pa, suspended_phases=None):
    """Checks shared by both calculate_equilibrium and
    calculate_property_diagram requests. Returns a list of problem
    strings (empty means this part is valid)."""
    problems = []

    db_path = _resolve_db_path(database)
    if not os.path.isfile(db_path):
        problems.append(f"Database not found: {db_path}")
        return problems  # nothing else is checkable without the file

    try:
        info = oc_service.inspect_database(database)
    except Exception as exc:
        problems.append(f"Could not read database: {exc}")
        return problems

    db_elements = set(info["elements"])
    requested = {el.upper() for el in elements_composition}
    missing = requested - db_elements
    if missing:
        problems.append(
            f"Element(s) {sorted(missing)} not declared in {info['name']} "
            f"(database has: {sorted(db_elements)})"
        )

    if len(requested) < 2:
        problems.append(
            "At least two elements with a nonzero amount are required "
            "(a pure single-element composition is a known unstable "
            "condition state for this engine)."
        )

    # Suspending a phase the database never declares is a silent no-op in
    # the engine: the calculation runs and returns the STABLE equilibrium,
    # which is a different question than the metastable one the caller
    # asked for. Observed live on agcu.TDB (no GRAPHITE anywhere in it) --
    # the request was swallowed, and the client model then reported that
    # graphite had been "suppressed". Rejecting instead, and naming the
    # phases that do exist, mirrors the element check above: the message
    # is what lets the caller repair the request.
    if suspended_phases:
        db_phases = {p.upper() for p in info.get("phases", [])}
        unknown = set()
        for name in suspended_phases:
            # "FCC_A1#2" -> "FCC_A1": composition sets are a runtime
            # concept; a TDB declares only the base phase name.
            base = str(name).split("#")[0].strip().upper()
            if base and base not in db_phases:
                unknown.add(str(name))
        if unknown:
            problems.append(
                f"Phase(s) {sorted(unknown)} not declared in {info['name']} "
                f"(database has: {sorted(db_phases)})"
            )

    for el, amount in elements_composition.items():
        if amount < 0:
            problems.append(f"Composition amount for '{el}' is negative ({amount}).")

    total = sum(elements_composition.values())
    if total <= 0:
        problems.append("Composition amounts sum to zero or less.")
    elif not (0.5 <= total <= 2.0):
        # Not a hard failure -- amounts get normalized internally either
        # way -- but a total this far from a "reasonable" scale (~1 mole,
        # or clearly-intended percentages/fractions) is worth surfacing
        # rather than silently normalizing without comment.
        problems.append(
            f"Note: composition amounts sum to {total:.4g}, which is far "
            "from a typical ~1.0 scale -- values will still be normalized, "
            "but double-check this is the intended composition."
        )

    if pressure_Pa <= 0:
        problems.append(f"Pressure must be positive, got {pressure_Pa}.")

    return problems


def check_equilibrium_request(
    database, elements_composition, temperature_K, pressure_Pa=1e5, suspended_phases=None
):
    """PREFLIGHT for calculate_equilibrium. Returns a list of problem
    strings; empty list means the request is valid."""
    problems = _check_common(
        database, elements_composition, pressure_Pa, suspended_phases
    )
    if temperature_K <= 0:
        problems.append(f"Temperature must be positive (Kelvin), got {temperature_K}.")
    return problems


def check_property_diagram_request(
    database, elements_composition, temperature_min_K, temperature_max_K,
    pressure_Pa=1e5, suspended_phases=None,
):
    """PREFLIGHT for calculate_property_diagram. Returns a list of
    problem strings; empty list means the request is valid."""
    problems = _check_common(
        database, elements_composition, pressure_Pa, suspended_phases
    )
    if temperature_min_K <= 0:
        problems.append(f"temperature_min_K must be positive, got {temperature_min_K}.")
    if temperature_max_K <= 0:
        problems.append(f"temperature_max_K must be positive, got {temperature_max_K}.")
    if temperature_min_K >= temperature_max_K:
        problems.append(
            f"temperature_min_K ({temperature_min_K}) must be less than "
            f"temperature_max_K ({temperature_max_K})."
        )
    return problems
