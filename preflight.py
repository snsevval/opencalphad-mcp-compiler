"""PREFLIGHT entry points. THE RULES ARE NOT HERE.

They are in settings/input.toml, and settings_engine applies them. This
file holds five function names and their signatures, because server.py,
the ablation worker and the verification loop call them that way -- and
nothing else. Every function below forwards.

Said in capitals at the top because until a moment ago it was not true of
the whole file: the original rule bodies were still sitting above these
wrappers, dead, called by nobody, nine rules that could be edited to no
effect whatsoever. Something that looks like a rule and is not one is
worse than no rule at all, and a reader has no way to tell by looking.

What PREFLIGHT means has not changed: everything decided before OCASI or
a native binary is touched, using the TDB's own element list and
arithmetic on the request. It is a named stage with its own reported
outcome rather than a check folded silently into a calculation. Catching
a bad request here is cheaper and safer than letting the engine discover
it -- the element check exists because loading a TDB's declared elements
without constraining all of them was the root cause behind the
steel1/steel7 segfaults early in this project.
"""
import os

import oc_service

# One atmosphere, from settings/input.toml [accept.defaults].
# It was declared there and hardcoded here at the same time; the
# file is the one that says why.
import settings_engine as _se
_DEFAULT_PRESSURE = _se.POLICY.input.defaults.get("pressure_Pa", 1e5)


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
    database, elements_composition, temperature_K, pressure_Pa=_DEFAULT_PRESSURE,
    suspended_phases=None,
    composition_basis=None,
):
    """PREFLIGHT for calculate_equilibrium. Returns a list of problem
    strings; empty list means the request is valid."""
    return _delegate("equilibrium", database, elements_composition,
                     composition_basis=composition_basis,
                     temperature_K=temperature_K, pressure_Pa=pressure_Pa,
                     suspended_phases=suspended_phases)


def check_property_diagram_request(
    database, elements_composition, temperature_min_K, temperature_max_K,
    pressure_Pa=_DEFAULT_PRESSURE, suspended_phases=None,
    composition_basis=None,
):
    """PREFLIGHT for calculate_property_diagram."""
    return _delegate("property_diagram", database, elements_composition,
                     composition_basis=composition_basis,
                     temperature_min_K=temperature_min_K,
                     temperature_max_K=temperature_max_K,
                     pressure_Pa=pressure_Pa,
                     suspended_phases=suspended_phases)


def check_isothermal_section_request(
    database, elements_composition, axis_element, axis_min, axis_max,
    temperature_K, pressure_Pa=_DEFAULT_PRESSURE, suspended_phases=None,
    composition_basis=None,
):
    """PREFLIGHT for calculate_isothermal_section."""
    return _delegate("isothermal_section", database, elements_composition,
                     composition_basis=composition_basis,
                     axis_element=axis_element, axis_min=axis_min,
                     axis_max=axis_max, temperature_K=temperature_K,
                     pressure_Pa=pressure_Pa,
                     suspended_phases=suspended_phases)


def check_scheil_request(
    database, elements_composition, seed_temperature_K, temperature_min_K,
    pressure_Pa=_DEFAULT_PRESSURE,
    composition_basis=None,
):
    """PREFLIGHT for calculate_scheil_solidification.

    Scheil's other precondition -- that the seed temperature is in the
    single-phase liquid -- is not here: it is a question about the alloy,
    not about the request, and settling it means computing an
    equilibrium. The tool checks it separately, before paying for a
    simulation that would otherwise fail obscurely.
    """
    return _delegate("scheil", database, elements_composition,
                     composition_basis=composition_basis,
                     seed_temperature_K=seed_temperature_K,
                     temperature_min_K=temperature_min_K,
                     pressure_Pa=pressure_Pa)


def check_phase_diagram_request(
    database, elements_composition, axis_element, axis_min, axis_max,
    temperature_min_K, temperature_max_K, seed_temperature_K,
    pressure_Pa=_DEFAULT_PRESSURE,
    composition_basis=None,
):
    """PREFLIGHT for calculate_phase_diagram.

    Two axes, so both get the checks a single axis gets, plus one that
    only makes sense here: the seed has to sit inside the box being
    mapped. MAP starts from that equilibrium and traces outward, so a
    seed outside the range is not a diagram of what was asked for.
    """
    return _delegate("phase_diagram", database, elements_composition,
                     composition_basis=composition_basis,
                     axis_element=axis_element, axis_min=axis_min,
                     axis_max=axis_max,
                     temperature_min_K=temperature_min_K,
                     temperature_max_K=temperature_max_K,
                     seed_temperature_K=seed_temperature_K,
                     pressure_Pa=pressure_Pa)


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
