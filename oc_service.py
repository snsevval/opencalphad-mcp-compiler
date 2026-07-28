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

    return {
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
