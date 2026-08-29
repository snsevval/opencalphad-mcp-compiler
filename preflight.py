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


def _delegate(operation, database, elements_composition, **extra):
    """Every check now comes from settings/input.toml.

    The rules used to live in this file as Python conditionals. They were
    moved out so that "what does this system check, and why?" has a
    single readable answer, and so that adding a rule of a kind that
    already exists is a change to a settings file rather than to code.

    These five functions stay because their callers do: server.py, the
    ablation worker and the verification loop all call them by name with
    these signatures. What changed is where the answer comes from, not
    what the answer is -- verified across 633 requests, hand-written and
    fuzzed, against the implementation this replaced.
    """
    import settings_engine
    request = dict(extra)
    request["database"] = database
    request["composition"] = elements_composition
    if "suspended_phases" in request:
        request["phase_status"] = request.pop("suspended_phases")
    return settings_engine.check(operation, **request)


def check_equilibrium_request(
    database, elements_composition, temperature_K, pressure_Pa=1e5,
    suspended_phases=None,
):
    """PREFLIGHT for calculate_equilibrium. Returns a list of problem
    strings; empty list means the request is valid."""
    return _delegate("equilibrium", database, elements_composition,
                     temperature_K=temperature_K, pressure_Pa=pressure_Pa,
                     suspended_phases=suspended_phases)


def check_property_diagram_request(
    database, elements_composition, temperature_min_K, temperature_max_K,
    pressure_Pa=1e5, suspended_phases=None,
):
    """PREFLIGHT for calculate_property_diagram."""
    return _delegate("property_diagram", database, elements_composition,
                     temperature_min_K=temperature_min_K,
                     temperature_max_K=temperature_max_K,
                     pressure_Pa=pressure_Pa,
                     suspended_phases=suspended_phases)


def check_isothermal_section_request(
    database, elements_composition, axis_element, axis_min, axis_max,
    temperature_K, pressure_Pa=1e5, suspended_phases=None,
):
    """PREFLIGHT for calculate_isothermal_section."""
    return _delegate("isothermal_section", database, elements_composition,
                     axis_element=axis_element, axis_min=axis_min,
                     axis_max=axis_max, temperature_K=temperature_K,
                     pressure_Pa=pressure_Pa,
                     suspended_phases=suspended_phases)


def check_scheil_request(
    database, elements_composition, seed_temperature_K, temperature_min_K,
    pressure_Pa=1e5,
):
    """PREFLIGHT for calculate_scheil_solidification.

    Scheil's other precondition -- that the seed temperature is in the
    single-phase liquid -- is not here: it is a question about the alloy,
    not about the request, and settling it means computing an
    equilibrium. The tool checks it separately, before paying for a
    simulation that would otherwise fail obscurely.
    """
    return _delegate("scheil", database, elements_composition,
                     seed_temperature_K=seed_temperature_K,
                     temperature_min_K=temperature_min_K,
                     pressure_Pa=pressure_Pa)


def check_phase_diagram_request(
    database, elements_composition, axis_element, axis_min, axis_max,
    temperature_min_K, temperature_max_K, seed_temperature_K,
    pressure_Pa=1e5,
):
    """PREFLIGHT for calculate_phase_diagram.

    Two axes, so both get the checks a single axis gets, plus one that
    only makes sense here: the seed has to sit inside the box being
    mapped. MAP starts from that equilibrium and traces outward, so a
    seed outside the range is not a diagram of what was asked for.
    """
    return _delegate("phase_diagram", database, elements_composition,
                     axis_element=axis_element, axis_min=axis_min,
                     axis_max=axis_max,
                     temperature_min_K=temperature_min_K,
                     temperature_max_K=temperature_max_K,
                     seed_temperature_K=seed_temperature_K,
                     pressure_Pa=pressure_Pa)


# --- Reddin yaninda yol gostermek ------------------------------------
#
# Olculdu (1.26): iki elementli bir sistemde bilesim taramasi istendi ve
# PREFLIGHT uc sikayet birden dondurdu -- "needs at least three elements",
# "axis_max must be a mole fraction in [0,1)", "axis_max leaves nothing for
# the dependent element". Ucu de dogru, ve hicbiri ne yapilmasi
# gerektigini soylemiyor. Cagiran taraf dogru alternatifi kendi buldu ama
# bunu yaparken STOP RULE'u cignemek zorunda kaldi.
#
# Iki durum ayni sey degil:
#
#   istek imkansiz            (olmayan element, ters aralik)  -> dur, sor
#   bu arac yapamaz, baskasi  (ikili sistemde bilesim ekseni)  -> YONLENDIR
#
# Ikincisinde soru degismiyor, sadece dogru kapiya gidiyor. Reddin bunu
# soylemesi gerekiyor; soylemezse ya cagiran taraf kurali cigner ya da
# cevaplanabilir bir soru cevapsiz kalir.
_ALTERNATIFLER = [
    (
        "at least three elements",
        "Bu ikili sistemde bileşim ekseni taranamaz, ama aynı soruya "
        "calculate_phase_diagram cevap verir: iki eksende (bileşim ve "
        "sıcaklık) faz sınırlarını izler, ve istenen sıcaklıktaki kesiti "
        "oradan okunur.",
    ),
    (
        "leaves nothing for the dependent",
        "Eksenin üst ucunu, bağımlı elemente yer kalacak şekilde düşürün "
        "(örneğin 1.0 yerine 0.95); istenen aralığın tamamı gerekiyorsa "
        "calculate_phase_diagram bu kısıta tabi değildir.",
    ),
    (
        "must be a mole fraction in [0, 1)",
        "Eksen ucu mol kesri olmalı. Saf uç (1.0) taranamaz; ona kadar "
        "olan aralık taranabilir, ya da calculate_phase_diagram kullanılır.",
    ),
]


def suggest(problems):
    """Alternatives for a rejection that is answerable elsewhere.

    Now read from settings/input.toml, where each route sits next to the
    rule that produces it. Only the "wrong tool" class gets one: an
    impossible request gets nothing, because inventing a route pushes the
    caller toward a calculation nobody asked for.
    """
    import settings_engine
    notes = []
    for operation in settings_engine.ALL_OPERATIONS:
        for note in settings_engine.route_for(operation, problems or []):
            if note not in notes:
                notes.append(note)
    return notes
