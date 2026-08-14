"""Fallback to the native OpenCalphad command-line binary (./OC) for cases
where OCASI (pyOC) fails to converge.

Why this exists: OCASI's tqce_native_retry (see oc_service.py) mirrors the
native command monitor's own calceq2(1)->4204->calceq2(0) retry, but some
cold-start single-point calculations (e.g. steel1.TDB Fe-C at 1200K) still
don't converge in OCASI even though the exact same calculation converges
fine through native ./OC (confirmed: G=-56563.8 J/mol, phase FCC_A1). Rather
than chase OCASI's internal state/initialization further, this module runs
the proven-working native binary as an automatic fallback.

Native ./OC has no clean non-interactive "just give me the result and exit"
mode: after a macro finishes, it falls back to reading further commands from
stdin, and since stdin is already closed/exhausted it spins printing its
prompt forever ("*** WARNING: MACRO ENDS WITHOUT SET INTERACTIVE!"). Rather
than fight that (attempts to end cleanly with "set interactive" did not
work reliably), run_native_equilibrium reads output with both a time and a
byte-count cap and always kills the process afterward -- the data we need
is printed within the first couple KB, long before the spin loop matters.
This same read-then-kill pattern is what makes it safe to use here too.

Which binary: our own compiled OpenCalphad 6.120 (dev branch) build has a
confirmed weaker grid-minimizer/STEP solver than the 6.058 stable release
bundled with the separately-installed OpenCalphad CAE GUI (e.g. steel1
Fe-C at 1200K does not converge cold-start in our 6.120 build at all, in
either grid-minimizer mode -- see the plan file, Faz 4/6 -- but converges
in 11 iterations on 6.058, matching the known-correct reference value
G=-56563.789 J/mol exactly). Since WSL2 can invoke a Windows .exe directly
from a Linux path via its process interop, we prefer that 6.058 binary
when it's present on disk, and only fall back to our own Linux build if
it isn't (e.g. on a machine without that separate GUI install).
"""
import os
import re
import subprocess
import time

OC_BUILD_DIR = os.environ.get("OC_BUILD_DIR", "/root/projects/opencalphad")
_LINUX_BINARY = os.path.join(OC_BUILD_DIR, "OC")
_WINDOWS_GUI_BINARY = "/mnt/c/OpenCalphad_CAE_0_1_0/Console/Windows/oc6P.exe"
OC_BINARY = os.environ.get(
    "OC_BINARY",
    _WINDOWS_GUI_BINARY if os.path.isfile(_WINDOWS_GUI_BINARY) else _LINUX_BINARY,
)

_FLOAT = r"[-+]?\d+(?:\.\d+)?(?:[Ee][-+]?\d+)?"


class NativeEquilibriumError(Exception):
    """Raised when the native ./OC fallback also fails to produce a result."""


def generate_macro(db_path, elements_composition, temperature_K, pressure_Pa):
    """Build the native .ocm macro text for a single-point equilibrium.

    Uses the N=1 total moles + independent-element X(...) mole-fraction
    condition style (confirmed working, matches the GUI's own convention),
    not the N(el)=amount style. The element with the largest amount is left
    as the implicit dependent/solvent element (no explicit condition); all
    others get an explicit X(el)=fraction condition.
    """
    total = sum(elements_composition.values())
    fractions = {el: amt / total for el, amt in elements_composition.items()}
    dependent_el = max(fractions, key=fractions.get)
    independents = [el for el in elements_composition if el != dependent_el]

    elements_line = " ".join(elements_composition.keys())
    x_conditions = " ".join(
        f"x({el.lower()})={fractions[el]:.10g}" for el in independents
    )
    db_stem = os.path.splitext(os.path.basename(db_path))[0]

    macro = (
        "new Y\n"
        f"r t ./{db_stem}\n"
        f"{elements_line}\n"
        "\n"
        f"set c t={temperature_K:.10g} p={pressure_Pa:.10g} n=1 {x_conditions}\n"
        "c e\n"
        "list,,,,\n"
    )
    return macro


def run_native_equilibrium(
    db_path,
    elements_composition,
    temperature_K,
    pressure_Pa,
    timeout=12,
    max_bytes=500_000,
):
    """Run native ./OC with a bounded-time, bounded-size read and return raw text.

    Never raises on the process itself hanging/looping -- it is always
    killed once either limit is hit, and whatever was captured (which
    includes the equilibrium result if the calculation converged at all)
    is returned for parsing.
    """
    if not os.path.isfile(OC_BINARY):
        raise NativeEquilibriumError(f"Native OC binary not found: {OC_BINARY}")

    macro_text = generate_macro(db_path, elements_composition, temperature_K, pressure_Pa)
    db_dir = os.path.dirname(db_path) or "."

    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = os.path.join(OC_BUILD_DIR, ".libs")

    proc = subprocess.Popen(
        [OC_BINARY],
        cwd=db_dir,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
    )

    try:
        try:
            proc.stdin.write(macro_text)
            proc.stdin.close()
        except (BrokenPipeError, OSError):
            pass

        chunks = []
        total = 0
        start = time.monotonic()
        while total < max_bytes and (time.monotonic() - start) < timeout:
            chunk = proc.stdout.read(8192)
            if not chunk:
                break  # real EOF: process exited on its own
            chunks.append(chunk)
            total += len(chunk)
    finally:
        proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass

    return "".join(chunks)


def _consume_constituents(text, target):
    tokens = text.split()
    i = 0
    while i + 1 < len(tokens):
        el, frac_str = tokens[i], tokens[i + 1]
        try:
            frac = float(frac_str)
        except ValueError:
            i += 1
            continue
        target[el.upper()] = frac
        i += 2


def parse_native_output(raw_text):
    """Parse native ./OC's default post-'c e' equilibrium listing.

    Deliberately tolerant of scientific notation, variable whitespace, and
    phase-composition lines continuing across multiple lines -- it does not
    depend on fixed column widths, only on the labeled section headers
    native always prints ("Some data for components", "Some data for
    phases", etc).
    """
    if "Equilibrium result" not in raw_text or "Degrees of freedom are" not in raw_text:
        raise NativeEquilibriumError(
            "Native OC produced no recognizable equilibrium result "
            "(did not converge, crashed, or was killed before finishing)."
        )

    rt_match = re.search(rf"RT=\s*({_FLOAT})\s*J/mol", raw_text)
    gn_match = re.search(rf"G/N=\s*({_FLOAT})\s*J/mol", raw_text)
    if not gn_match:
        raise NativeEquilibriumError("Could not parse Gibbs energy from native OC output.")
    gibbs_energy_J = float(gn_match.group(1))
    RT = float(rt_match.group(1)) if rt_match else None

    chemical_potentials = {}
    comp_section = re.search(
        r"Some data for components[^\n]*\n(.*?)(?:\n\s*\n|Some data for phases)",
        raw_text,
        re.DOTALL,
    )
    if comp_section:
        for line in comp_section.group(1).splitlines():
            m = re.match(
                rf"\s*(\S+)\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s+(\S.*)?$",
                line,
            )
            if not m:
                continue
            name = m.group(1).upper()
            if name == "COMPONENT":  # header line
                continue
            chem_pot_over_rt = float(m.group(4))
            chemical_potentials[name] = chem_pot_over_rt * RT if RT is not None else chem_pot_over_rt

    phase_molar_amounts = {}
    phase_element_composition = {}
    phases_section = re.search(
        r"Some data for phases[^\n]*\n[^\n]*\n(.*?)(?:\n-{2,}>|\n---+>|\Z)",
        raw_text,
        re.DOTALL,
    )
    if phases_section:
        current_phase = None
        phase_line_re = re.compile(
            rf"\s*([A-Za-z0-9_#]+)\.*\s+(\S+)\s+({_FLOAT})\s+({_FLOAT})\s+"
            rf"({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s+X:\s*(.*)$"
        )
        for line in phases_section.group(1).splitlines():
            if not line.strip():
                continue
            m = phase_line_re.match(line)
            if m:
                name = m.group(1)
                moles = float(m.group(3))
                phase_molar_amounts[name] = moles
                phase_element_composition[name] = {}
                current_phase = name
                _consume_constituents(m.group(8), phase_element_composition[name])
            elif current_phase is not None:
                _consume_constituents(line, phase_element_composition[current_phase])

    if not phase_molar_amounts:
        raise NativeEquilibriumError("Native OC output had no parseable stable phases.")

    return {
        "gibbs_energy_J": gibbs_energy_J,
        "chemical_potentials_J_per_mol": chemical_potentials,
        "phase_molar_amounts": phase_molar_amounts,
        "phase_element_composition": phase_element_composition,
    }


def run_and_parse(db_path, elements_composition, temperature_K, pressure_Pa, timeout=12):
    raw_text = run_native_equilibrium(
        db_path, elements_composition, temperature_K, pressure_Pa, timeout=timeout
    )
    return parse_native_output(raw_text)
