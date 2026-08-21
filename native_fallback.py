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


def generate_macro(db_path, elements_composition, temperature_K, pressure_Pa,
                   suspended_phases=None, dormant_phases=None,
                   fixed_phases=None):
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

    # Phase status, if any, must be set before the calculation. The prompt
    # sequence was read out of the engine's own source rather than guessed
    # (src/userif/pmon6.F90): a name, a blank line to end the name list,
    # then one of S(uspend) D(ormant) E(ntered) F(ixed). Fixed also asks an
    # amount, which is why it carries one.
    status_block = ""
    for status_letter, names in (("S", suspended_phases), ("D", dormant_phases)):
        for name in names or ():
            status_block += f"set status phase\n{name}\n\n{status_letter}\n"
    for name, amount in (fixed_phases or {}).items():
        status_block += f"set status phase\n{name}\n\nF\n{amount:.10g}\n"

    macro = (
        "new Y\n"
        f"r t ./{db_stem}\n"
        f"{elements_line}\n"
        "\n"
        f"{status_block}"
        f"set c t={temperature_K:.10g} p={pressure_Pa:.10g} n=1 {x_conditions}\n"
        "c e\n"
        "list,,,,\n"
        # Every phase in the database, ranked by how close it is to being
        # stable, with its driving force -- and the dormant ones listed
        # separately. "list,,,," above shows only what is stable, so the
        # question "would this phase form?" had no answer at all until now.
        # The command path is LIST -> SHORT -> P, found in pmon6.F90 where
        # it calls list_sorted_phases: "phases sorted: stable / unstable in
        # driving force order / dormant the same".
        "list\n"
        "short\n"
        "P\n"
    )
    return macro


def run_native_equilibrium(
    db_path,
    elements_composition,
    temperature_K,
    pressure_Pa,
    timeout=12,
    max_bytes=500_000,
    suspended_phases=None,
    dormant_phases=None,
    fixed_phases=None,
):
    """Run native ./OC with a bounded-time, bounded-size read and return raw text.

    Never raises on the process itself hanging/looping -- it is always
    killed once either limit is hit, and whatever was captured (which
    includes the equilibrium result if the calculation converged at all)
    is returned for parsing.
    """
    if not os.path.isfile(OC_BINARY):
        raise NativeEquilibriumError(f"Native OC binary not found: {OC_BINARY}")

    macro_text = generate_macro(
        db_path, elements_composition, temperature_K, pressure_Pa,
        suspended_phases=suspended_phases, dormant_phases=dormant_phases,
        fixed_phases=fixed_phases,
    )
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

    # The "Some global data" block carries more than the Gibbs energy, and
    # until now everything but G/N and RT was read straight past:
    #
    #   T= 1200.00 K, P= 1.0000E+05 Pa, V= 7.2784E-06 m3
    #   N= 1.0000E+00 moles, B= 5.5409E+01 g, RT= 9.9774E+03 J/mol
    #   G= -5.65638E+04 J, G/N=-5.6564E+04 J/mol, H= 3.5345E+04 J, S= 7.659E+01 J/K
    #
    # H and S are totals over N moles, as G (not G/N) is. Reading them costs
    # nothing and buys a check this server never had: G = H - T*S must hold.
    # On the captured fixture it does, to 0.8 J in 56,564 -- which is the
    # rounding in a four-significant-figure entropy, not an error. A result
    # that fails it is malformed in a way no phase-fraction sum would reveal.
    def _global(pattern):
        found = re.search(pattern, raw_text)
        return float(found.group(1)) if found else None

    # The engine's own account of what it was asked. It prints this before
    # it prints the answer:
    #
    #   Conditions ...: 1:T=1200, 2:P=100000, 3:N=1, 4:X(C)=.01
    #   Degrees of freedom are   0
    #
    # Until now only the presence of the second line was used, as a
    # sentinel for "a calculation finished". The numbers themselves were
    # read straight past -- including the degrees of freedom, which is the
    # engine saying whether the conditions pinned the system down at all.
    # A macro line swallowed by one of the engine's interactive prompts
    # (which has happened here more than once) does not stop the
    # calculation: the engine solves what is left, prints a well-formed
    # result, and says so only in these two lines.
    reported_conditions = {}
    conditions_match = re.search(r"Conditions\s*\.*\s*:\s*\n([^\n]*)", raw_text)
    if conditions_match:
        # "1:T=1200, 2:P=100000, 3:N=1, 4:X(C)=.01" -- the index is the
        # engine's own numbering and carries no meaning for us; the name may
        # be bare (T) or carry a component (X(C)); the value may be written
        # without a leading zero (.01).
        condition_re = re.compile(
            r"\d+\s*:\s*([A-Za-z]+(?:\([^)]*\))?)\s*=\s*(-?\.?\d[\d.]*(?:[eE][-+]?\d+)?)"
        )
        for name, value in condition_re.findall(conditions_match.group(1)):
            reported_conditions[name.upper()] = float(value)

    dof_match = re.search(r"Degrees of freedom are\s+(-?\d+)", raw_text)
    degrees_of_freedom = int(dof_match.group(1)) if dof_match else None

    volume_m3 = _global(rf"\bV=\s*({_FLOAT})\s*m3")
    moles_total = _global(rf"\bN=\s*({_FLOAT})\s*moles")
    mass_g = _global(rf"\bB=\s*({_FLOAT})\s*g\b")
    enthalpy_J = _global(rf"\bH=\s*({_FLOAT})\s*J\b")
    entropy_J_per_K = _global(rf"\bS=\s*({_FLOAT})\s*J/K")

    chemical_potentials = {}
    # Activity is the fifth column of the component table and was already
    # being matched by the regex below -- captured, then dropped. It is the
    # quantity a metallurgist reaches for when asking whether a species will
    # react, and it was one group index away the whole time.
    activities = {}
    component_mole_fractions = {}
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
            component_mole_fractions[name] = float(m.group(3))
            activities[name] = float(m.group(5))

    phase_molar_amounts = {}
    phase_element_composition = {}
    # Per-phase columns that were matched and discarded. Status says whether
    # a phase is ENTERED, DORMANT, FIXED or SUSPENDED -- without it a caller
    # cannot tell a phase that is genuinely stable from one the request
    # merely held in place. dGm/RT is the driving force: zero for a stable
    # phase by definition, and the only way to answer "would this phase form
    # if it could?" for one that is not.
    phase_status = {}
    phase_volume_m3 = {}
    phase_formula_units = {}
    phase_driving_force_RT = {}
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
                phase_status[name] = m.group(2)
                phase_volume_m3[name] = float(m.group(4))
                phase_formula_units[name] = float(m.group(5))
                phase_driving_force_RT[name] = float(m.group(7))
                phase_element_composition[name] = {}
                current_phase = name
                _consume_constituents(m.group(8), phase_element_composition[name])
            elif current_phase is not None:
                _consume_constituents(line, phase_element_composition[current_phase])

    if not phase_molar_amounts:
        raise NativeEquilibriumError("Native OC output had no parseable stable phases.")

    # The sorted listing that "list short P" appends: every phase in the
    # database, ranked by how close it is to being stable, with its driving
    # force. Until this was added the question "would this phase form?" had
    # no answer -- the equilibrium listing shows only what IS stable, so a
    # phase that missed by a hair and one that could never form looked
    # identical, which is to say invisible.
    #
    #   List of stable and entered phases
    #     No tup Name              Mol.comp. Comp/FU   dGm/RT
    #      2   2 BCC_A2#1          9.68E-01     1.00  0.00E+00
    #      5   5 CHI_A12           0.00E+00    58.00 -1.82E-03
    #     20  20 SIGMA             0.00E+00    30.00 -2.46E-03
    #   List of dormant phases
    #     16  16 M23C6             0.00E+00    29.00  2.24E-03
    #
    # Sign convention, from the engine's own warning text ("unstable phase
    # with positive driving force"): zero for a stable phase, negative for
    # one that cannot form under these conditions, positive for one that
    # wants to and is only being held out -- which is what a dormant phase
    # is for.
    driving_forces = {}
    dormant_listed = []
    ranked_re = re.compile(
        rf"^\s*\d+\s+\d+\s+(\S+)\s+({_FLOAT})\s+({_FLOAT})\s+({_FLOAT})\s*$"
    )
    in_dormant = False
    for line in raw_text.splitlines():
        # Only a new section heading changes which list we are in. The
        # column header that follows it ("No tup Name ... dGm/RT") is
        # shared by both sections and must not reset the flag -- it did in
        # the first version, which is why the dormant list came back empty
        # while the driving forces themselves parsed fine.
        if "List of" in line:
            in_dormant = "dormant" in line.lower()
            continue
        if "No tup Name" in line:
            continue
        found = ranked_re.match(line)
        if found:
            driving_forces[found.group(1)] = float(found.group(4))
            if in_dormant:
                dormant_listed.append(found.group(1))

    # Existing keys keep their names and meanings -- everything downstream
    # (result_check, the benchmark, the client models) reads them, and a
    # rename would be a silent breakage of exactly the kind this project
    # spends its effort catching. The new fields are additions only, and any
    # that the output did not carry stay absent rather than becoming zero:
    # a missing measurement and a measurement of zero must not look alike.
    result = {
        "gibbs_energy_J": gibbs_energy_J,
        "chemical_potentials_J_per_mol": chemical_potentials,
        "phase_molar_amounts": phase_molar_amounts,
        "phase_element_composition": phase_element_composition,
    }
    for key, value in (
        ("reported_conditions", reported_conditions or None),
        ("degrees_of_freedom", degrees_of_freedom),
        ("driving_force_RT", driving_forces or None),
        ("dormant_phases_listed", dormant_listed or None),
        ("enthalpy_J", enthalpy_J),
        ("entropy_J_per_K", entropy_J_per_K),
        # Native prints entropy directly, so G = H - T*S is an independent
        # check here. The OCASI path has no entropy symbol and rearranges it
        # from G and H, where the same check would be circular -- hence the
        # marker, so a caller can tell which it is holding.
        ("entropy_source", "measured" if entropy_J_per_K is not None else None),
        ("volume_m3", volume_m3),
        ("moles_total", moles_total),
        ("mass_g", mass_g),
        ("RT_J_per_mol", RT),
        ("activities", activities or None),
        ("component_mole_fractions", component_mole_fractions or None),
        ("phase_status", phase_status or None),
        ("phase_volume_m3", phase_volume_m3 or None),
        ("phase_formula_units", phase_formula_units or None),
        ("phase_driving_force_RT", phase_driving_force_RT or None),
    ):
        if value is not None:
            result[key] = value
    return result


def run_and_parse(db_path, elements_composition, temperature_K, pressure_Pa,
                  timeout=12, suspended_phases=None, dormant_phases=None,
                  fixed_phases=None):
    raw_text = run_native_equilibrium(
        db_path, elements_composition, temperature_K, pressure_Pa,
        timeout=timeout, suspended_phases=suspended_phases,
        dormant_phases=dormant_phases, fixed_phases=fixed_phases,
    )
    return parse_native_output(raw_text)
