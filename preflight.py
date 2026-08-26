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


def check_phase_diagram_request(
    database, elements_composition, axis_element, axis_min, axis_max,
    temperature_min_K, temperature_max_K, seed_temperature_K,
    pressure_Pa=1e5,
):
    """PREFLIGHT for calculate_phase_diagram. Returns a list of problem
    strings; empty list means the request is valid.

    Two axes, so both get the checks a single axis gets, plus one that
    only makes sense here: the seed has to sit inside the box being
    mapped. MAP starts from that equilibrium and traces outward, so a seed
    outside the range is not a diagram of what was asked for.
    """
    problems = _check_common(database, elements_composition, pressure_Pa, None)

    symbols = {el.upper() for el in elements_composition}
    if axis_element.upper() not in symbols:
        problems.append(
            f"axis_element '{axis_element}' is not in the composition "
            f"({sorted(symbols)})."
        )

    for name, value in (("axis_min", axis_min), ("axis_max", axis_max)):
        if not (0.0 <= value <= 1.0):
            problems.append(
                f"{name} must be a mole fraction in [0, 1], got {value}."
            )
    if axis_min >= axis_max:
        problems.append(
            f"axis_min ({axis_min}) must be less than axis_max ({axis_max})."
        )

    for name, value in (("temperature_min_K", temperature_min_K),
                        ("temperature_max_K", temperature_max_K),
                        ("seed_temperature_K", seed_temperature_K)):
        if value <= 0:
            problems.append(f"{name} must be positive (Kelvin), got {value}.")
    if temperature_min_K >= temperature_max_K:
        problems.append(
            f"temperature_min_K ({temperature_min_K}) must be less than "
            f"temperature_max_K ({temperature_max_K})."
        )
    if not (temperature_min_K <= seed_temperature_K <= temperature_max_K):
        problems.append(
            f"seed_temperature_K ({seed_temperature_K}) is outside the "
            f"temperature range being mapped ({temperature_min_K} to "
            f"{temperature_max_K}). The diagram is traced outward from the "
            "seed, so it has to start inside."
        )
    return problems


def check_scheil_request(
    database, elements_composition, seed_temperature_K, temperature_min_K,
    pressure_Pa=1e5,
):
    """PREFLIGHT for calculate_scheil_solidification. Returns a list of
    problem strings; empty list means the request is valid.

    Only the checks that need no engine. Scheil's other precondition --
    that the seed temperature is in the single-phase liquid -- cannot be
    settled here: it is a question about the alloy, not about the request,
    and answering it means computing an equilibrium. The tool checks it
    separately, before paying for a simulation that would otherwise fail
    obscurely.
    """
    problems = _check_common(database, elements_composition, pressure_Pa, None)

    if seed_temperature_K <= 0:
        problems.append(
            f"seed_temperature_K must be positive (Kelvin), got {seed_temperature_K}."
        )
    if temperature_min_K <= 0:
        problems.append(
            f"temperature_min_K must be positive, got {temperature_min_K}."
        )
    if temperature_min_K >= seed_temperature_K:
        problems.append(
            f"temperature_min_K ({temperature_min_K}) must be below "
            f"seed_temperature_K ({seed_temperature_K}) -- solidification "
            "is simulated by cooling from the seed."
        )
    return problems


def check_isothermal_section_request(
    database, elements_composition, axis_element, axis_min, axis_max,
    temperature_K, pressure_Pa=1e5, suspended_phases=None,
):
    """PREFLIGHT for calculate_isothermal_section. Returns a list of
    problem strings; empty list means the request is valid.

    The axis checks are the ones the engine would otherwise discover the
    expensive way. Scanning an element that is not in the composition
    would silently scan nothing; scanning the only other element leaves no
    dependent element for the macro to balance against; and an axis
    reaching far enough would drive the dependent element negative, which
    the engine reports as an unsolvable condition rather than a bad
    request.
    """
    problems = _check_common(
        database, elements_composition, pressure_Pa, suspended_phases
    )
    if temperature_K <= 0:
        problems.append(f"Temperature must be positive (Kelvin), got {temperature_K}.")

    symbols = {el.upper() for el in elements_composition}
    if axis_element.upper() not in symbols:
        problems.append(
            f"axis_element '{axis_element}' is not in the composition "
            f"({sorted(symbols)}). The scanned element must be one of the "
            "elements the alloy is made of."
        )
    elif len(symbols) < 3:
        problems.append(
            f"Scanning {axis_element} in a two-element system leaves only "
            "one other element, which the macro needs as the dependent "
            "one. A composition scan needs at least three elements."
        )

    for name, value in (("axis_min", axis_min), ("axis_max", axis_max)):
        if not (0.0 <= value < 1.0):
            problems.append(
                f"{name} must be a mole fraction in [0, 1), got {value}."
            )
    if axis_min >= axis_max:
        problems.append(
            f"axis_min ({axis_min}) must be less than axis_max ({axis_max})."
        )

    # What is left for the dependent element at the far end of the scan.
    total = sum(elements_composition.values())
    if total > 0 and axis_element.upper() in symbols:
        others = sum(
            amount / total for el, amount in elements_composition.items()
            if el.upper() not in (axis_element.upper(),)
        )
        held = others - max(
            (amount / total for el, amount in elements_composition.items()
             if el.upper() != axis_element.upper()),
            default=0.0,
        )
        if axis_max + held >= 1.0:
            problems.append(
                f"axis_max ({axis_max}) leaves nothing for the dependent "
                f"element: the other fixed elements already take "
                f"{held:.4g} of the total."
            )
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
    """Reddedilen istegin bilinen bir alternatifi varsa onu dondur.

    Sadece "bu arac yapamaz, baskasi yapar" sinifi icin doner. Imkansiz
    istekler (olmayan element, ters aralik, negatif sicaklik) icin bos
    doner -- orada yonlendirilecek bir yer yok ve uydurmasi zararli olur:
    cagiran tarafi, kullanicinin sormadigi bir hesaba iter.
    """
    bulunan = []
    for problem in problems or []:
        for kalip, oneri in _ALTERNATIFLER:
            if kalip in problem and oneri not in bulunan:
                bulunan.append(oneri)
    return bulunan
