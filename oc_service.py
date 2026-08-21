"""Thin service layer over the OCASI pyOC bindings.

Wraps pyOC.opencalphad (the compiled OpenCalphad Application Software
Interface) with plain-Python-in / dict-out functions, so the MCP layer
never has to touch the Fortran-backed API directly.
"""
import glob
import os
import re
import sys

OC_BUILD_DIR = os.environ.get("OC_BUILD_DIR", "/root/projects/opencalphad")
sys.path.insert(0, OC_BUILD_DIR)

import pyOC  # noqa: E402
from pyOC import opencalphad as oc  # noqa: E402
from pyOC import PhaseStatus  # noqa: E402

import native_fallback  # noqa: E402

DEFAULT_DB_DIR = "/mnt/c/Users/sevval/Documents/OpenCalphad/OC6/macros"

_ELEMENT_RE = re.compile(r"^\s*ELEMENT\s+(\S+)", re.IGNORECASE | re.MULTILINE)
_PHASE_RE = re.compile(r"^\s*PHASE\s+(\S+)", re.IGNORECASE | re.MULTILINE)
_NON_ELEMENT_NAMES = {"/-", "VA", "ELECTRON_GAS"}


class EquilibriumError(Exception):
    """Raised when reading a database or calculating an equilibrium fails."""


def inspect_database(database, directory=DEFAULT_DB_DIR):
    """Return the elements and phase names declared in a .TDB file.

    database: filename (resolved against `directory`) or absolute path.
    """
    path = database if os.path.isabs(database) else os.path.join(directory, database)
    if not os.path.isfile(path):
        raise EquilibriumError(f"Database not found: {path}")
    with open(path, "r", errors="ignore") as f:
        text = f.read()
    elements = sorted(
        {
            m.group(1).upper()
            for m in _ELEMENT_RE.finditer(text)
            if m.group(1).upper() not in _NON_ELEMENT_NAMES
        }
    )
    phases = sorted({m.group(1).split(":")[0] for m in _PHASE_RE.finditer(text)})
    return {
        "name": os.path.basename(path),
        "path": path,
        "elements": elements,
        "phases": phases,
    }


def list_databases(directory=DEFAULT_DB_DIR):
    """List .TDB database files in a directory with a quick element preview."""
    paths = sorted(
        set(
            glob.glob(os.path.join(directory, "*.TDB"))
            + glob.glob(os.path.join(directory, "*.tdb"))
        )
    )
    results = []
    for path in paths:
        elements = []
        try:
            with open(path, "r", errors="ignore") as f:
                text = f.read()
            elements = sorted(
                {
                    m.group(1).upper()
                    for m in _ELEMENT_RE.finditer(text)
                    if m.group(1).upper() not in _NON_ELEMENT_NAMES
                }
            )
        except OSError:
            pass
        results.append(
            {
                "name": os.path.basename(path),
                "path": path,
                "size_bytes": os.path.getsize(path),
                "elements": elements,
            }
        )
    return results


def calculate_equilibrium(
    database,
    elements_composition,
    temperature_K,
    pressure_Pa=1e5,
    suspended_phases=None,
    dormant_phases=None,
    fixed_phases=None,
):
    """Calculate a single-point equilibrium.

    Tries OCASI first. If OCASI fails to converge (or returns no stable
    phases), automatically falls back to running the native ./OC binary
    with an equivalent macro -- confirmed to converge on cases (e.g.
    steel1.TDB Fe-C at 1200K) where OCASI's cold-start calculation does
    not, for reasons that are a separate, still-open investigation (see
    the plan file, Faz 5). The result always carries "backend_used"
    ("ocasi" or "native_oc"); a native_oc result also carries
    "fallback_reason" with the OCASI error that triggered the fallback.
    Phase suspension (suspended_phases) is only supported through OCASI --
    if it's given and OCASI fails, the original OCASI error is raised
    rather than silently ignoring the suspension request.

    database: filename (resolved against DEFAULT_DB_DIR) or absolute path.
    elements_composition: dict of element symbol -> molar amount.
    """
    db_path = database if os.path.isabs(database) else os.path.join(DEFAULT_DB_DIR, database)
    if not os.path.isfile(db_path):
        raise EquilibriumError(f"Database not found: {db_path}")

    composition = {el.upper(): amt for el, amt in elements_composition.items()}

    nonzero = [el for el, amt in composition.items() if amt > 0]
    if len(nonzero) < 2:
        raise EquilibriumError(
            "Composition must include at least two elements with a nonzero "
            "amount. A pure single-element composition (e.g. only {'FE': 1.0}) "
            "puts OpenCalphad's condition system into a state ('One component "
            "without condition') that reliably crashes this build's grid "
            "minimizer. Add a second element with a small nonzero amount, or "
            "use a database that only declares that one element."
        )

    # A dormant phase is a question OCASI cannot answer. pyOC reports only
    # phases whose amount is above zero (getPhasesAtEquilibrium filters on
    # exactly that), and a dormant phase has none -- so the very quantity
    # the request is asking for, its driving force, is the one thing that
    # tier drops. The native engine prints it. Routing on capability rather
    # than on convergence is a departure from how the tiers are otherwise
    # chosen, and it is deliberate: sending this request to a tier that
    # structurally cannot answer it would return a result that looks fine
    # and is silent about the thing that was asked.
    if dormant_phases or fixed_phases:
        native_result = native_fallback.run_and_parse(
            db_path, composition, temperature_K, pressure_Pa,
            suspended_phases=suspended_phases, dormant_phases=dormant_phases,
            fixed_phases=fixed_phases,
        )
        native_result.update({
            "database": os.path.basename(db_path),
            "temperature_K": temperature_K,
            "pressure_Pa": pressure_Pa,
            "composition": composition,
            "suspended_phases": list(suspended_phases or []),
            "dormant_phases": list(dormant_phases or []),
            "fixed_phases": dict(fixed_phases or {}),
            "backend_used": "native_oc",
            "backend_reason": (
                "dormant or fixed phase status was requested; OCASI reports "
                "only phases with a nonzero amount and cannot return their "
                "driving force"
            ),
        })
        return native_result

    try:
        result = _calculate_equilibrium_ocasi(
            db_path, composition, temperature_K, pressure_Pa, suspended_phases
        )
        result["backend_used"] = "ocasi"
        return result
    except EquilibriumError as ocasi_error:
        if suspended_phases:
            raise
        try:
            native_result = native_fallback.run_and_parse(
                db_path, composition, temperature_K, pressure_Pa
            )
        except Exception as native_error:
            raise EquilibriumError(
                f"OCASI failed ({ocasi_error}); native OC fallback also "
                f"failed ({native_error})"
            ) from native_error
        native_result.update(
            {
                "database": os.path.basename(db_path),
                "temperature_K": temperature_K,
                "pressure_Pa": pressure_Pa,
                "composition": composition,
                "suspended_phases": [],
                "backend_used": "native_oc",
                "fallback_reason": str(ocasi_error),
            }
        )
        return native_result


def _scalar_or_none(symbol):
    """Read one state variable from OCASI, or None if it is unavailable.

    pyOC's own getScalarResult cannot be used for this. It allocates the
    result buffer with numpy.empty -- uninitialised memory -- passes it to
    the Fortran side, and returns buffer[0] without ever checking the error
    code. When the symbol is not supported the buffer is left untouched and
    whatever happened to be in that memory comes back as a number.

    Measured: asking for G, then H, then S, then V in turn returned the
    correct G, the correct H, and then H's value again for S and for every
    symbol after it -- numpy had handed out the same freed buffer each
    time. Nothing in the return value distinguished a real measurement from
    the previous one echoed back. That is precisely the silent-substitution
    failure the rest of this server is built to prevent, sitting one layer
    below it.

    So: a recognisable sentinel goes in, the error code is cleared before
    and read after, and the value is returned only if the call reported
    success AND actually wrote. A quantity this engine path cannot provide
    comes back as None and is then left out of the result entirely, because
    an absent measurement and a measurement of zero must not look alike.
    """
    import numpy  # local: only this helper needs it
    sentinel = -987654321.0
    buffer = numpy.array([sentinel])
    raw = oc.raw()
    raw.pyseterr(0)
    try:
        raw.pytqgetv(symbol, 0, 0, 1, buffer, oc.eq())
    except Exception:
        return None
    if raw.pygeterr() != 0 or buffer[0] == sentinel:
        raw.pyseterr(0)
        return None
    return float(buffer[0])


def _ocasi_state_variables(temperature_K, gibbs_energy_J):
    """The state variables OCASI can supply, plus entropy derived from them.

    Measured against this build (error code checked per symbol):

        G GM H HM V VM N B T P X(component)   supported
        S SM CP AC(..) DG(..) NP(..)          error 8888 / 4050

    Entropy is missing but not lost: G = H - T*S is an identity, so
    S = (H - G)/T. Checked against the native engine's own printed entropy
    at 1200 K -- (35345 + 56564)/1200 = 76.59, which is exactly what native
    reports -- so this is a rearrangement, not an approximation.

    Activities, driving forces and heat capacity have no route here. The
    native path prints all three, so the two engine tiers do NOT return the
    same fields, and pretending otherwise by filling zeros would be worse
    than the asymmetry. The caller can see which tier ran from
    backend_used, and a field that tier could not measure is simply absent.
    """
    values = {}
    enthalpy_J = _scalar_or_none("H")
    if enthalpy_J is not None:
        values["enthalpy_J"] = enthalpy_J
        if temperature_K:
            values["entropy_J_per_K"] = (enthalpy_J - gibbs_energy_J) / temperature_K
            # Marked, because the difference matters to anyone who later
            # wants to check G = H - T*S. On the native path entropy is
            # measured independently and that identity is a real test. Here
            # it was rearranged FROM G and H, so the same check would be
            # circular and would pass no matter what the engine returned.
            # A vacuous check that looks like a real one is worse than none.
            values["entropy_source"] = "derived_from_G_and_H"
    for key, symbol in (("volume_m3", "V"), ("moles_total", "N"), ("mass_g", "B")):
        value = _scalar_or_none(symbol)
        if value is None:
            continue
        # Volume comes back as exactly zero from databases that carry no
        # volume data at all -- agcu.TDB is one, and its Gibbs energy is
        # identical to the last decimal across four orders of magnitude of
        # pressure for the same reason. Reporting 0.0 would say the system
        # occupies no space. Absent data and a measurement of zero must not
        # look alike, which is the same rule the engine-tier fields follow.
        if key == "volume_m3" and value == 0.0:
            values["volume_note"] = (
                "this database carries no volume data, so volume and any "
                "pressure dependence are unavailable rather than zero"
            )
            continue
        values[key] = value
    return values


def _calculate_equilibrium_ocasi(
    db_path,
    composition,
    temperature_K,
    pressure_Pa,
    suspended_phases,
):
    """Calculate a single-point equilibrium via OCASI. See calculate_equilibrium
    for the public entry point (which adds the native ./OC fallback)."""
    # Only load the elements actually used in this calculation. Reading the
    # full TDB (all declared elements) while only constraining a subset of
    # them leaves the unconstrained elements' degrees of freedom unresolved
    # ("Degrees of freedom not zero" in OC's own diagnostics) -- the root
    # cause of segfaults/heap corruption we saw on multi-element databases
    # like steel1/steel7 (confirmed via gdb + a clean native ./OC comparison
    # run with the same OpenCalphad 6.120 build: restricting to just the
    # used elements converges in ~16-18 iterations with no crash at all).
    selected_elements = tuple(composition.keys())

    oc.setVerbosity(False)
    try:
        oc.readtdb(db_path, elements=selected_elements)
    except Exception as exc:
        raise EquilibriumError(f"Failed to read database {db_path}: {exc}") from exc

    if suspended_phases:
        try:
            oc.setPhasesStatus(tuple(suspended_phases), PhaseStatus.Suspended)
        except Exception as exc:
            raise EquilibriumError(f"Failed to suspend phases {suspended_phases}: {exc}") from exc

    try:
        oc.setPressure(pressure_Pa)
        oc.setTemperature(temperature_K)
        oc.setElementMolarAmounts(composition)
        # No grid-minimizer-off "warmup" pass here: it was found to corrupt
        # the default equilibrium record's state (it warmed up a throwaway
        # COPY of the record, then a second calculateEquilibrium() call on
        # the original, still-cold record crashed) -- a single direct call
        # converges cleanly once the composition is properly constrained
        # (see selected_elements above).
        # Use the native-retry Fortran entry point (tqce_native_retry, added
        # to OCisoCbinding/liboctq.F90) instead of plain calculateEquilibrium.
        # A pure-Python retry with GridMinimizerStatus.Off was tried first,
        # but that routes to calceq3 (a different subroutine) -- it does not
        # reproduce native's actual calceq2(1)->4204->calceq2(0) recovery, so
        # it did not fix the 1200K-class failures. calculateEquilibriumRobust
        # calls a new Fortran subroutine that mirrors that exact recovery.
        oc.calculateEquilibriumRobust()
    except Exception as exc:
        raise EquilibriumError(f"Equilibrium calculation failed: {exc}") from exc

    err = oc.raw().pygeterr()
    if err != 0:
        # Querying phase/state results (getPhasesAtEquilibrium etc.) reads
        # Fortran-side equilibrium-record state that is left inconsistent
        # when calceq2 didn't actually converge -- doing so anyway segfaults
        # instead of erroring cleanly, so bail out here first.
        raise EquilibriumError(
            f"Equilibrium did not converge (error code {err}) even after "
            "the native grid-minimizer retry."
        )
    phases = oc.getPhasesAtEquilibrium()
    amounts = phases.getPhaseMolarAmounts()
    if not amounts:
        raise EquilibriumError(
            "Equilibrium calculation reported success but returned no "
            "stable phases."
        )

    result = {
        "database": os.path.basename(db_path),
        "temperature_K": temperature_K,
        "pressure_Pa": pressure_Pa,
        "composition": composition,
        "suspended_phases": list(suspended_phases) if suspended_phases else [],
        "gibbs_energy_J": oc.getGibbsEnergy(),
        "chemical_potentials_J_per_mol": oc.getChemicalPotentials(),
        "phase_molar_amounts": phases.getPhaseMolarAmounts(),
        "phase_element_composition": phases.getPhaseElementComposition(),
    }
    result.update(_ocasi_state_variables(temperature_K, result["gibbs_energy_J"]))
    return result
