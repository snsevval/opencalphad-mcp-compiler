"""MCP server exposing OpenCalphad (via OCASI/pyOC) as tools for an AI assistant.

See the plan at
the project plan
for the wider architecture.

Every equilibrium calculation runs in its own subprocess (see
run_equilibrium.py) because the underlying Fortran engine can segfault on
non-converging inputs; that must not be allowed to take the whole MCP
server down. calculate_property_diagram and compare_alloys are built on top
of that same single-point primitive, so a bad point among many still fails
in isolation instead of aborting the whole call.

Request pipeline (see the plan file, Faz 10): every calculation tool runs
PREFLIGHT before touching an engine and VERIFY A on whatever comes back.
PREFLIGHT rejects impossible requests (element not in the database, bad
composition, inverted temperature range) for free, instead of letting
OCASI discover them the expensive way -- that class of mistake is exactly
what caused this project's earlier segfaults. VERIFY A then runs the same
deterministic structural checks (result_check.py) that the verification
loop uses, so a result reaching the user has been checked by the same
rules the test harness applies -- and says so, via the "verification"
field it attaches.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
from typing import Optional

from mcp.server.fastmcp import FastMCP, Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import oc_service  # noqa: E402
import native_step  # noqa: E402
import native_scheil  # noqa: E402
import native_map  # noqa: E402
import preflight  # noqa: E402
import result_check  # noqa: E402
import scan_summary  # noqa: E402
import settings_engine  # noqa: E402

# One atmosphere, from settings/input.toml [accept.defaults].
# It was declared there and hardcoded here at the same time; the
# file is the one that says why.
_DEFAULT_PRESSURE = settings_engine.POLICY.input.defaults.get(
    "pressure_Pa", 1e5)
import call_log  # noqa: E402
import semantic_check  # noqa: E402
import failure_classify  # noqa: E402

mcp = FastMCP("opencalphad")

# Layer B costs a round trip to an external model (~12s measured), so it
# is opt-out rather than mandatory -- set OC_SEMANTIC_CHECK=0 to skip it
# when latency matters more than the second opinion.
SEMANTIC_CHECK_ENABLED = os.environ.get("OC_SEMANTIC_CHECK", "1") != "0"
# DEBUGGER: classify a verification failure and, where a retry is honest,
# close the loop. Off switch kept because it is the only stage that can
# issue a second outbound call after the result already exists.
DEBUGGER_ENABLED = os.environ.get("OC_DEBUGGER", "1") != "0"

# How long one equilibrium subprocess may run before it is killed. It was
# 60s -- the same figure the MCP client used for its own per-request
# timeout, so a slow calculation lost twice over. steel7's six-element
# system at 1173 K sat right on that line: the client gave up at exactly
# 60s, and the model, seeing a timeout rather than a result, simply
# reissued the identical call. Raised here and to 300s in the client, so
# the two limits are no longer racing. A ceiling, not a target -- a
# calculation that needs minutes is saying something about the system, and
# the timeout message still says which combination did it.
CALC_TIMEOUT_S = int(os.environ.get("OC_CALC_TIMEOUT_S", "300"))


def _element_distribution(result: dict, elements_composition: dict) -> Optional[dict]:
    """How much of each requested element ended up in which phase.

    Arithmetic on the engine's own output -- phase amount times the
    element's fraction inside that phase -- and no new claim about the
    chemistry. It is here because leaving the multiplication to the reader
    was measured to go wrong: asked the same question twice, the client
    model reported once that molybdenum had collected in the carbide (it
    had: 65%) and once that it had collected in a phase holding 2% of it.
    A phase can hold a high CONCENTRATION of an element while holding
    almost none of its total AMOUNT, because the phase itself is tiny --
    here a phase making up 0.17% of the system carried a third of the
    vanadium by concentration and half of it by amount.

    Phases come sorted by amount, so "where is most of it" is read off the
    first entry rather than derived.

    `total` against `requested` is also the check Layer A never had: an
    element whose total comes back at zero never entered the calculation,
    whatever the composition tables look like. The native fallback is
    known to drop elements it cannot write into its macro, and nothing
    downstream would otherwise notice.
    """
    amounts = result.get("phase_molar_amounts") or {}
    per_phase = result.get("phase_element_composition") or {}
    if not amounts or not per_phase:
        return None

    # The engine normalizes the composition, so compare like with like.
    scale = sum(elements_composition.values())
    if scale <= 0:
        return None

    distribution = {}
    for element, requested in elements_composition.items():
        symbol = element.upper()
        shares = {}
        for phase, phase_amount in amounts.items():
            fraction = (per_phase.get(phase) or {}).get(symbol)
            if fraction:
                shares[phase] = phase_amount * fraction
        # Six significant figures, not six decimals: a trace element's
        # share runs to 1e-6 and fixed rounding would erase it. Float
        # noise like 0.7898059025999999 otherwise travels into the answer
        # and implies precision the engine never claimed.
        distribution[symbol] = {
            "by_phase": {
                phase: float(f"{value:.6g}")
                for phase, value in sorted(shares.items(), key=lambda kv: -kv[1])
            },
            "total": float(f"{sum(shares.values()):.6g}"),
            "requested": float(f"{requested / scale:.6g}"),
        }
    return distribution


def _phase_notes(result: dict, elements_composition: dict) -> Optional[dict]:
    """Flag a phase whose contents contradict what its name suggests.

    A phase name in a TDB denotes crystal structure, not composition, so
    chemically unrelated things share one. FCC_A1 is austenite -- an
    iron solution -- and it is also the MC carbides (VC, TiC, NbC), which
    are FCC by structure and contain almost no iron. steel7 at 1173 K
    returns both at once, as FCC_A1_AUTO#2 (Fe 0.92) and FCC_A1#1
    (C 0.46, V 0.36). Only the composition tells them apart.

    Measured over five fresh sessions on one steel1 composition, the
    client model called an FCC_A1 holding Fe 0.0014 "austenite" in three
    of them -- once going on to conclude that vanadium "forms no carbide"
    when 56% of it sat in the very carbide it had just misnamed. It was
    not short of data: one of those runs printed a distribution table
    showing iron in that phase at 2.49e-06, in its own output, two
    sections above the misnaming. So more numbers do not fix this; the
    contradiction has to be said.

    The note says only what is arithmetically true and leaves the naming
    alone -- calling it a carbide would be a claim OpenCalphad never made.
    The trigger carries no chemistry either: a phase is flagged when its
    dominant element is not the alloy's dominant element, which holds for
    any database, and stays silent on the ordinary phases where the name
    and the contents agree.

    Stating the fact was measured first, over five fresh sessions: the
    note was reproduced in all five, and the phase was still called
    austenite in three -- the same rate as before it existed. Information
    was never what was missing. What did change is that the false
    conclusion drawn from the label ("vanadium forms no carbide") never
    recurred, because the contradicting number now stands beside it.

    So the note now asks for a justification rather than stating a fact,
    and deliberately does not forbid a name. Forbidding one would have to
    name the words to forbid -- austenite, ferrite -- which is steel
    vocabulary hardcoded into a server that also serves Ag-Cu and
    Mg-Na-Cl, and the next database would bring its own wrong names. It
    would also silence the two runs in five where the model read the same
    phase correctly as a vanadium carbide, which is the reading worth
    having. A request for justification leaves those intact while giving
    a model that wants to write "austenite" something it has to reconcile
    with Fe = 0.0014.
    """
    per_phase = result.get("phase_element_composition") or {}
    if not per_phase or not elements_composition:
        return None

    alloy_major = max(elements_composition, key=elements_composition.get).upper()

    notes = {}
    for phase, composition in per_phase.items():
        if not composition:
            continue
        # A phase holding one element cannot be misread -- its composition
        # is its identity. GRAPHITE is carbon wherever it appears, and
        # flagging it would be noise on every Fe-C result. The ambiguity
        # only arises in solution phases, where one name spans many
        # compositions.
        if sum(1 for value in composition.values() if value > 0.01) < 2:
            continue
        phase_major = max(composition, key=composition.get)
        if phase_major.upper() == alloy_major:
            continue
        notes[phase] = settings_engine.note(
            "phase-name-is-structure-not-composition",
            phase_major=phase_major,
            phase_major_fraction=format(composition[phase_major], ".4g"),
            alloy_major=alloy_major,
        )
    return notes or None


def _preflight_failure(problems: list) -> dict:
    """Shape a PREFLIGHT rejection the same way every tool reports it, so
    a client can tell "this request was never run" apart from "it ran and
    failed" by the stage field alone."""
    rejection = {
        "error": "Request rejected before calculation: " + "; ".join(problems),
        "stage": "PREFLIGHT",
        "problems": problems,
    }
    # A refusal that names no way forward leaves the caller two bad
    # options: hand back nothing, or work around the rule. Measured (1.26):
    # it chose the second. Where the request is answerable by a DIFFERENT
    # tool, say so -- routing the same question is not the same thing as
    # substituting another one, and the stop rule should not have to cover
    # both with one instruction.
    alternative = preflight.suggest(problems)
    if alternative:
        rejection["alternative"] = alternative
    return rejection


def _attach_coverage(result: dict, axis_key: str, requested_n,
                     span_low, span_high) -> dict:
    """Say how much of the requested scan came back.

    The other checks ask whether the numbers are sound. This one asks how
    many are missing -- a question none of them was posing, and the reason
    a one-point answer to a twenty-point request came back marked as
    verified.
    """
    cov = result_check.measure_requested_positions(
        result.get("points"), axis_key, requested_n, span_low, span_high)
    if not cov:
        return result
    result["coverage"] = cov
    warning = settings_engine.coverage_note(cov)
    if warning:
        result["coverage_warning"] = warning
    return result


def _attach_mixed_basis_note(result: dict) -> dict:
    """Say so when a series holds points from more than one engine.

    STEP reports phase mass fractions; positions its line never reached are
    filled by single-point equilibrium calls converted to the same basis.
    The two once disagreed by 26 per cent, which is why each point carries
    a `source` -- but a caller reading the series as one curve has no
    reason to look at the field unless told.
    """
    if not isinstance(result, dict):
        return result
    if result.get("native_step_points") and result.get("gap_filled_points"):
        metin = settings_engine.note("mixed-basis-in-combined-scan")
        if metin:
            result.setdefault("notes", []).append(metin)
    return result


def _attach_scan_summary(result: dict, axis_key: str,
                         to_weight_percent=None) -> dict:
    """Hand over the across-row answers, not only the rows.

    A scan returns every number a caller needs, but the questions asked of
    it -- where a phase first appears, where one becomes dominant, where
    melting starts and finishes -- live between rows rather than in any
    one of them. Measured behaviour is that those derivations go wrong
    while single-row reads stay exact, so the derivation is done here,
    once, deterministically, and shipped alongside the points.

    Costs no engine call: it is a pure function of the points already in
    hand. Omitted entirely when there is too little to summarize, so an
    empty shell never reads as "nothing happens here".
    """
    summary = scan_summary.summarize(result.get("points"), axis_key,
                                     to_weight_percent=to_weight_percent)
    if summary:
        result["scan_summary"] = summary
    return result


def _attach_axis_basis(result: dict) -> dict:
    """Put a unit on every axis position, and the second basis beside it.

    A composition axis arrives as a bare number called `x`. Measured on
    1.29: the caller built a weight-per-cent column for 25 of them and
    every entry was low, because the scanned element is heavier than the
    alloy around it. The base composition report does not help here -- in
    it, the scanned element is still zero.
    """
    composition = result.get("composition")
    axis_element = result.get("axis_element")
    if not composition or not axis_element:
        return result
    for nokta in result.get("points") or []:
        if "x" not in nokta:
            continue
        agirlik = settings_engine.axis_weight_percent(
            composition, axis_element, nokta["x"])
        if agirlik is not None:
            nokta["x_weight_percent"] = agirlik
    return result


class _Sure:
    """Time one stage and record it on the result.

    The run has been called slow for weeks without anyone knowing which
    part of it was. Total wall time cannot tell an engine that got slower
    from a reviewer that started timing out, and those need opposite
    fixes.

    Milliseconds, integers: this is for reading a pattern across ninety
    cases, not for benchmarking a function.
    """

    def __init__(self, result, ad):
        self.result = result
        self.ad = ad
        self.t0 = None

    def __enter__(self):
        self.t0 = time.time()
        return self

    def __exit__(self, *_):
        if isinstance(self.result, dict):
            kayit = self.result.setdefault("timings_ms", {})
            kayit[self.ad] = kayit.get(self.ad, 0) + int(
                (time.time() - self.t0) * 1000)
        return False


def _sure_ekle(result, ad, baslangic):
    """Same, for a stage whose result did not exist when it started."""
    if isinstance(result, dict):
        kayit = result.setdefault("timings_ms", {})
        kayit[ad] = kayit.get(ad, 0) + int((time.time() - baslangic) * 1000)
    return result


def _canonical_phases(result):
    """One spelling of every phase name on the way out.

    Applied at the boundary rather than in each tier, because the tiers are
    exactly where it went wrong: STEP writes LIQUID, the single-point path
    writes LIQUID#1 for the same phase, MAP writes FCC-A1-AUTO#2 with
    hyphens. Which tier answered is provenance -- it belongs in `source`,
    not in the phase name.

    Measured: 3,400 logged results carry a "#1" name, and a benchmark case
    failed when a scan fell to the slower tier and returned FCC_A1#1 where
    FCC_A1 was expected.

    "#2" and higher survive. They are genuinely separate composition sets
    -- FCC_A1_AUTO#2 is the copper-rich half of the Ag-Cu miscibility gap
    -- and merging them would fuse two different phases into one line.
    """
    if not isinstance(result, dict):
        return result
    canon = native_step.canonical_phase_name

    def _rekey(d):
        if not isinstance(d, dict):
            return d
        yeni = {}
        for ad, deger in d.items():
            k = canon(ad)
            # Two spellings of one phase must not become two entries; if
            # both arrive, the later one is the same number.
            yeni[k] = deger
        return yeni

    for alan in ("phase_molar_amounts", "phase_element_composition",
                 "driving_forces_RT", "phase_status"):
        if alan in result:
            result[alan] = _rekey(result[alan])
    for nokta in result.get("points") or []:
        if isinstance(nokta, dict) and "phase_molar_amounts" in nokta:
            nokta["phase_molar_amounts"] = _rekey(nokta["phase_molar_amounts"])
    return result


def _attach_basis(result, basis, source=None):
    """State what the numbers in this result are a fraction OF.

    The field carrying them is called phase_molar_amounts everywhere, and
    on a scan that name is not what the values mean: STEP reports BPW(),
    which is phase MASS fraction, and gap-filled points are converted to
    match before merging. A single-point equilibrium really does return
    molar amounts. Same field name, two different quantities, and until now
    nothing said which one was in hand.

    Measured: the two once disagreed by 26 per cent and the difference was
    read as a physical effect until it was traced.

    Renaming the field would break every caller. Stating the basis costs
    nothing and answers the question the name raises.
    """
    if not isinstance(result, dict):
        return result
    result["basis"] = basis
    if source is not None and "source" not in result:
        result["source"] = source
    for nokta in result.get("points") or []:
        if isinstance(nokta, dict):
            nokta.setdefault("basis", basis)
    return result


def _attach_verification(result: dict, request_args: Optional[dict] = None,
                         declared_basis: Optional[dict] = None) -> dict:
    """Run VERIFY A (and VERIFY B when enabled) and record the outcome.

    Deliberately non-destructive: a result that fails a check is still
    returned with its numbers intact, flagged rather than replaced. The
    caller asked for a calculation and the engine produced one; hiding it
    would remove the very evidence needed to judge what went wrong.

    Layer B runs only if Layer A passed -- there is no point paying for an
    outside opinion on a result already known to be malformed -- and its
    outcome is recorded separately from Layer A's. Crucially, a Layer B
    that could not be reached (the free tier returns 529 unpredictably) is
    reported as unavailable, never as disapproval: NVIDIA's capacity must
    not turn into a false alarm about the user's chemistry.
    """
    # What the caller declared, and what it became before the engine saw
    # it. Only present when something was actually converted or rescaled.
    _attach_declared_basis(result, declared_basis)

    # Say which basis the composition arrived in, and give both.
    # Steel is quoted by weight by convention and this engine conditions on
    # mole fractions; the payload used to say neither, and three separate
    # readers each assumed a different one.
    if isinstance(result, dict) and result.get('composition'):
        rapor = settings_engine.composition_report(result['composition'])
        if rapor:
            result['composition_basis'] = rapor

    _t = time.time()
    passed, problems = result_check.verify_result(result)
    verification = {
        "stage": "VERIFY_A",
        "passed": passed,
        "problems": problems,
    }

    # Does the result answer the request? A separate question from whether
    # it is well-formed, so it is reported separately rather than folded
    # into the same pass/fail -- the two demand different responses. A
    # malformed result means something in this pipeline is broken; a result
    # that is fine but answers a different question means the request did
    # not survive the trip.
    if request_args is not None:
        correspondence = result_check.verify_correspondence(result, request_args)
        _sure_ekle(result, "verify_a", _t)
        if correspondence is not None:
            verification["correspondence"] = correspondence
            if not correspondence["passed"]:
                passed = False
                verification["passed"] = False
                problems = problems + correspondence["problems"]
                verification["problems"] = problems

    # Defined even when the review does not run: the DEBUGGER block
    # below has its own condition and would otherwise reference a name
    # that only exists on one path.
    stage_deadline = None
    if passed and SEMANTIC_CHECK_ENABLED and request_args is not None:
        # One deadline for the whole stage, shared with the DEBUGGER's
        # retry below. Read from settings/execution.toml so the number
        # sits next to the measurement that produced it.
        stage_deadline = time.time() + settings_engine.POLICY.execution            .reviewer_budget["stage_deadline_s"]
        _tb = time.time()
        review = semantic_check.review(request_args, result,
                                       deadline=stage_deadline)
        _sure_ekle(result, "verify_b", _tb)
        verification["layer_b"] = review
        _apply_review(verification, review, problems)

    result["verification"] = verification

    # ---- DEBUGGER + RE-VERIFY -------------------------------------
    # Everything above is a pipeline: it reports what happened and stops.
    # This closes it into a loop for the one failure class where a retry
    # is honest. failure_classify says which class we are in and whether
    # anything can be done; only a review that produced no usable verdict
    # gets retried, and only against a DIFFERENT reviewer. The numbers are
    # never recomputed -- the calculation is deterministic, so re-running
    # it would return the same result and the same verdict.
    if DEBUGGER_ENABLED and request_args is not None:
        failure = failure_classify.classify(result)
        if failure is not None:
            result["failure"] = failure
            if failure.get("strategy") == failure_classify.STRATEGY_RETRY_REVIEWER:
                _retry_review(result, verification, request_args,
                              problems, deadline=stage_deadline)

    # Our own output invariants, from output.toml [honesty]. Run last,
    # against the finished payload, because they ask whether the thing
    # about to be handed over matches what the file says we do -- and the
    # DEBUGGER above can still change it.
    #
    # Recorded apart from the chemistry. A violation here is a bug in this
    # server, not a problem with the caller's alloy, and putting our fault
    # in a field that reads as a comment on their metallurgy would be the
    # same confusion Layer B was demoted for.
    _ti = time.time()
    saglam, ihlaller = result_check.check_output_invariants(result)
    _sure_ekle(result, "invariants", _ti)
    verification["output_invariants"] = {
        "passed": saglam,
        "checked": len(settings_engine.POLICY.output.honesty),
    }
    if ihlaller:
        verification["output_invariants"]["violations"] = ihlaller

    return result


def _apply_review(verification: dict, review: dict, problems: list) -> None:
    """Fold a Layer B outcome into the verification record. The review is
    recorded and framed; it never decides. An objection is written down as
    advisory_only and Layer A's verdict stands, because a wrong objection
    presented as a verdict once cost a caller eight correct numbers. A
    reviewer that could not be reached, or whose verdict could not be read,
    leaves the record untouched -- an absent opinion is not a negative one.
    The invariant is checked: result_check.inv_review_does_not_decide."""
    if review.get("available") and review.get("passed") is False:
        # Recorded, framed, and not acted on. The review reports; it does
        # not decide. See output.toml, honesty.review_is_advisory_not_a_verdict:
        # a wrong objection presented as a verdict cost a caller eight
        # correct numbers and produced a claim that the real phase diagram
        # forbade what the engine had computed.
        verification["stage"] = "VERIFY_A+B"
        verification["independent_review"] = {
            "objected": True,
            "advisory_only": True,
            "framing": settings_engine.note(
                "independent-review-objected",
                reason=review.get("reason", "")[:500],
            ),
        }
    elif review.get("available"):
        verification["stage"] = "VERIFY_A+B"
        verification["independent_review"] = {
            "objected": False,
            "advisory_only": True,
        }


def _retry_review(result: dict, verification: dict, request_args: dict,
                  problems: list, deadline=None) -> None:
    """Ask the rest of the reviewer chain, skipping whoever already failed
    to produce a usable verdict. Records the attempt either way, so a
    result never silently gains (or loses) an independent review."""
    first = verification.get("layer_b") or {}
    tried = [m for m in [first.get("model_used")] if m]
    # Shares the stage deadline rather than getting a fresh one: two
    # ninety-second budgets in sequence is a three-minute stage, which is
    # the thing being bounded.
    retry = semantic_check.review(request_args, result, skip_models=tried,
                                  deadline=deadline)

    attempt = {
        "stage": "DEBUGGER",
        "category": result["failure"]["category"],
        "skipped_models": tried,
        "layer_b_retry": retry,
    }
    if retry.get("available") and retry.get("passed") is not None:
        verification["layer_b"] = retry
        _apply_review(verification, retry, problems)
        attempt["outcome"] = "resolved"
        # The retry answered, so the original failure no longer stands.
        result.pop("failure", None)
        residual = failure_classify.classify(result)
        if residual is not None:
            result["failure"] = residual
    else:
        attempt["outcome"] = "unresolved"
    verification["debugger"] = attempt


def _calc_one(
    database: str,
    elements_composition: dict,
    temperature_K: float,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    suspended_phases: Optional[list] = None,
    dormant_phases: Optional[list] = None,
    fixed_phases: Optional[dict] = None,
) -> dict:
    """Run one single-point equilibrium in an isolated subprocess."""
    _t_engine = time.time()
    payload = {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_K": temperature_K,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": suspended_phases,
        "dormant_phases": dormant_phases,
        "fixed_phases": fixed_phases,
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "result.json")
        try:
            proc = subprocess.run(
                [sys.executable, os.path.join(HERE, "run_equilibrium.py"), out_path],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                env=os.environ,
                timeout=CALC_TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            return {
                "error": (
                    f"Equilibrium calculation timed out after {CALC_TIMEOUT_S} "
                    "seconds and was "
                    "killed. This database/composition/temperature combination "
                    "likely does not converge."
                )
            }
        if os.path.exists(out_path):
            with open(out_path) as f:
                sonuc = json.load(f)
            return _sure_ekle(sonuc, "engine", _t_engine)
        return {
            "error": (
                f"Equilibrium calculation crashed (exit code {proc.returncode}). "
                "This usually means the calculation did not converge for this "
                "database/composition/temperature combination."
            ),
            "stderr_tail": proc.stderr[-2000:] if proc.stderr else "",
        }


def _with_stop_rule(function):
    """Fill {STOP_RULE} in a tool's docstring from settings/output.toml.

    Applied BELOW @mcp.tool() so it runs first and the framework reads the
    finished text. The docstring is what the calling model actually sees,
    which is why this rule was copied into six of them by hand -- and why
    correcting it once meant editing all six. It has one home now.
    """
    text = settings_engine.stop_rule_block()
    if function.__doc__:
        function.__doc__ = function.__doc__.replace("{STOP_RULE}", text)
    return function




@mcp.tool()
@call_log.logged
def list_databases(directory: Optional[str] = None) -> list[dict]:
    """List available thermodynamic (.TDB) databases with their elements.

    Args:
        directory: optional folder to scan; defaults to the standard
            OpenCalphad macros/databases folder.
    """
    return oc_service.list_databases(directory or oc_service.DEFAULT_DB_DIR)


@mcp.tool()
@call_log.logged
def inspect_database(database: str, directory: Optional[str] = None) -> dict:
    """Get the elements and phase names declared inside one .TDB database.

    Use this before calculate_equilibrium/suspend a phase, to see valid
    element symbols and exact phase names (e.g. to know it's "GRAPHITE" and
    not "GRAPHITE_A9") for that specific database.

    Args:
        database: database filename (e.g. "steel7.TDB") or full path.
        directory: optional folder to resolve a bare filename against;
            defaults to the standard OpenCalphad macros/databases folder.
    """
    return oc_service.inspect_database(database, directory or oc_service.DEFAULT_DB_DIR)


def _canonical_composition(composition, basis, label=""):
    """Resolve a declared composition to the mole fractions the engine takes.

    The INPUT side of the basis question. W(C)=0.01 and X(C)=0.01 are
    different alloys -- 0.045 against 0.010 in mole fraction -- and until
    this existed both were conditioned identically, because the basis
    setting was read only after the engine had already run.

    Returns (canonical, report, rejection). The rejection is a ready
    payload: an unconvertible request is refused before any calculation,
    the way every other impossible request is, rather than converted with a
    guessed mass.
    """
    try:
        kanonik, rapor = settings_engine.resolve_composition(
            composition, basis)
    except ValueError as exc:
        mesaj = ("%s: %s" % (label, exc)) if label else str(exc)
        return None, None, _preflight_failure([mesaj])
    return kanonik, rapor, None


def _attach_declared_basis(result, rapor):
    """Record what arrived and what it became, and say so if it changed.

    Only when something was actually done -- a mole-fraction request that
    already summed to one carries nothing new, and an unchanged payload is
    the point.
    """
    if not isinstance(result, dict) or not rapor:
        return result
    result["composition_declared"] = rapor
    if rapor.get("rescaled"):
        metin = settings_engine.note("composition-was-rescaled",
                                     total=rapor.get("declared_sum"))
        if metin:
            result.setdefault("notes", []).append(metin)
    return result


@mcp.tool()
@_with_stop_rule
@call_log.logged
def calculate_equilibrium(
    database: str,
    elements_composition: dict[str, float],
    temperature_K: float,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    suspended_phases: Optional[list[str]] = None,
    dormant_phases: Optional[list[str]] = None,
    fixed_phases: Optional[dict[str, float]] = None,
    composition_basis: Optional[str] = None,
) -> dict:
    """Calculate a single-point thermodynamic equilibrium with OpenCalphad.

    {STOP_RULE}

    If the rejection carries an "alternative" field, the question IS
    answerable — just not by this tool. Call the tool it names, with the
    same question. That is routing, not substitution, and the numbered rule
    below does not apply to it.

    Otherwise:
      1. Do NOT call this or any other calculation tool again in this turn.
      2. Quote the rejection reason to the user, including any list of valid
         elements or phases it names.
      3. Ask which corrected request they want. Naming options is fine;
         running one is not.
    The user asked a specific question. Computing a different one — even a
    near-identical one, even while announcing the change — hands them a
    result they did not ask for.

    Args:
        database: database filename (e.g. "steel7.TDB") or full path.
        elements_composition: element symbol -> molar amount, e.g.
            {"FE": 0.95, "C": 0.05}. Does not need to be pre-normalized.
            Must include at least two elements with a nonzero amount — a
            pure single-element composition (e.g. only {"FE": 1.0}) is
            rejected, since it puts this engine's condition system into an
            unstable state. For a near-pure system, add a second element
            with a small nonzero amount (e.g. {"FE": 0.999, "C": 0.001}).
        temperature_K: temperature in Kelvin.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).
        suspended_phases: phase names to exclude from the calculation
            (e.g. ["GRAPHITE"]) — this is how you turn a phase "off".
            Must be phases the database actually declares; use
            inspect_database to see them. A name the database does not
            declare is rejected rather than silently ignored.
        dormant_phases: phase names to hold out of the equilibrium while
            still asking what they would do. Use this to answer "would this
            phase form?" — a dormant phase comes back with a driving force
            in driving_force_RT: positive means it wants to form and is
            only being held out, negative means it could not form here.
            Suspending removes a phase and says nothing about it; this
            removes it and reports.
        fixed_phases: phase name -> amount, to hold a phase at a set amount
            instead of letting the calculation decide it.

    DRIVING FORCES
    Every result carries driving_force_RT: for each phase the database
    declares, how far it is from being stable, in units of RT. Zero means
    stable. Negative means it cannot form under these conditions -- the
    more negative, the further away. Positive means it wants to form and
    something is holding it out. This answers "which phases are close to
    appearing?" without having to guess and re-run.

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran on it before handing it back -- phase fractions
    summing to one, values in range, no NaN, and for a sweep, how many
    points actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    # Every phase name the request mentions goes through the same check,
    # whatever status it asks for. A dormant or fixed name the database
    # does not declare is exactly as wrong as a suspended one, and the
    # rejection is what lets the caller repair it.
    named_phases = list(suspended_phases or []) + list(dormant_phases or []) \
        + list(fixed_phases or {})
    problems = preflight.check_equilibrium_request(
        database, elements_composition, temperature_K, pressure_Pa,
        named_phases or None,
        composition_basis=composition_basis,
    )
    if problems:
        return _preflight_failure(problems)

    # Basis resolution runs AFTER the request has been judged, not before.
    # Normalising first would hand every rule an already-tidied composition
    # -- composition-scale-plausible exists to catch {FE: 99, C: 1} as a
    # possible mistake, and it cannot do that once the numbers have been
    # divided by their sum.
    elements_composition, _basis_report, _red = _canonical_composition(
        elements_composition, composition_basis)
    if _red is not None:
        return _red

    result = _calc_one(
        database, elements_composition, temperature_K, pressure_Pa,
        suspended_phases, dormant_phases, fixed_phases,
    )
    distribution = _element_distribution(result, elements_composition)
    if distribution is not None:
        result["element_distribution"] = distribution
    notes = _phase_notes(result, elements_composition)
    if notes:
        result["phase_notes"] = notes
    # A single-point equilibrium returns molar amounts of each phase, and
    # the engine that produced it is its provenance.
    _canonical_phases(result)
    _attach_basis(result, "phase_molar_amount",
                  source=result.get("backend_used"))
    return _attach_verification(result, {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_K": temperature_K,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": suspended_phases,
        "dormant_phases": dormant_phases,
        "fixed_phases": fixed_phases,
    }, declared_basis=_basis_report)


def _same_elements(composition_a: dict, composition_b: dict) -> bool:
    """Do both sides contain the same elements in nonzero amount?

    This decides whether the Gibbs energies are comparable at all. An
    element present on one side only shifts that side's energy by its own
    reference contribution, which has nothing to do with stability.
    """
    def present(composition):
        return {el.upper() for el, amount in composition.items() if amount}
    return present(composition_a) == present(composition_b)


@mcp.tool()
@_with_stop_rule
@call_log.logged
def compare_alloys(
    database: str,
    composition_a: dict[str, float],
    composition_b: dict[str, float],
    temperature_K: float,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    suspended_phases: Optional[list[str]] = None,
    label_a: str = "A",
    label_b: str = "B",
    composition_basis: Optional[str] = None,
) -> dict:
    """Calculate equilibrium for two compositions at the same T/P and compare them.

    {STOP_RULE}

    If the rejection carries an "alternative" field, the question IS
    answerable — just not by this tool. Call the tool it names, with the
    same question. That is routing, not substitution, and the rule below
    does not apply to it.

    Otherwise: do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason to the user (including any list of
    valid elements or phases it names) and ask which corrected request they
    want. Naming options is fine; running one is not.

    Useful for questions like "suspend graphite and compare to the normal
    result" (call this twice with suspended_phases set only for B), or
    "how does adding more Cr change the stable phases".

    WHAT THE GIBBS ENERGY DIFFERENCE MEANS — READ BEFORE USING IT
    "Lower Gibbs energy is more stable" holds between states of ONE
    composition: which phases a given alloy adopts. It does not hold
    between different compositions. Each Gibbs energy is measured against
    its own elements' reference states, so replacing some Fe with Mo moves
    the number by that swap's reference contribution and says nothing
    about how favourable either alloy is. Two alloys of different
    composition are each at equilibrium; neither is "more stable" than the
    other, and the result carries a note saying so.

    When the elements differ, answer "which is better" with what does
    transfer: which phases each forms and in what amount, how close other
    phases are to appearing (each result's driving_force_RT), or over what
    temperature range each stays single-phase — a property diagram per
    side answers that last one.

    Args:
        database: database filename or full path, shared by both calculations.
        composition_a: element -> molar amount for the first alloy.
        composition_b: element -> molar amount for the second alloy.
        temperature_K: temperature in Kelvin, shared by both calculations.
        pressure_Pa: pressure in Pascal, shared by both calculations.
        suspended_phases: phase names to exclude, shared by both calculations.
            Must be phases the database actually declares.
        label_a: short label for composition_a in the result (e.g. "with C").
        label_b: short label for composition_b in the result (e.g. "no C").

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran on it before handing it back -- phase fractions
    summing to one, values in range, no NaN, and for a sweep, how many
    points actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    # Both sides are read in the same declared basis: comparing an alloy
    # given by weight against one given by mole would compare two things
    # nobody asked about together.
    problems = (
        preflight.check_equilibrium_request(
            database, composition_a, temperature_K, pressure_Pa, suspended_phases,
            composition_basis=composition_basis,
        )
        + preflight.check_equilibrium_request(
            database, composition_b, temperature_K, pressure_Pa, suspended_phases,
            composition_basis=composition_basis,
        )
    )
    if problems:
        return _preflight_failure(problems)

    # After the rejection rules, not before -- see calculate_equilibrium.
    composition_a, _basis_a, _red = _canonical_composition(
        composition_a, composition_basis, label_a)
    if _red is not None:
        return _red
    composition_b, _basis_b, _red = _canonical_composition(
        composition_b, composition_basis, label_b)
    if _red is not None:
        return _red

    # Both sides get the same verification treatment. That means two Layer B
    # round trips when it's enabled, which roughly doubles this tool's
    # latency -- accepted rather than special-cased, since a comparison
    # whose two halves were checked differently would be worth less than
    # the seconds saved. OC_SEMANTIC_CHECK=0 turns it off when that matters.
    def _args_for(composition):
        return {
            "database": database,
            "elements_composition": composition,
            "temperature_K": temperature_K,
            "pressure_Pa": pressure_Pa,
            "suspended_phases": suspended_phases,
        }

    result_a = _attach_verification(
        _calc_one(database, composition_a, temperature_K, pressure_Pa, suspended_phases),
        _args_for(composition_a), declared_basis=_basis_a,
    )
    result_b = _attach_verification(
        _calc_one(database, composition_b, temperature_K, pressure_Pa, suspended_phases),
        _args_for(composition_b), declared_basis=_basis_b,
    )

    if "error" in result_a or "error" in result_b:
        comparison = {
            "note": (
                "Comparison skipped because at least one side failed to "
                f"converge — see the '{label_a}'/'{label_b}' error field above."
            )
        }
    else:
        # Canonicalize before comparing, or the same phase counts as two
        # different ones. Measured on Fe-20Cr against Fe-20Cr-2Mo at
        # 1273 K: both are single-phase ferrite, and the summary said
        # phases_only_in_A ["BCC_A2"], phases_only_in_B ["BCC_A2#1"],
        # phases_in_both [] -- reporting that two alloys share no phase at
        # all when their phase content is identical. "#1" is a phase's
        # default composition set and the engine prints it inconsistently
        # depending on the path a result came through; native_step and
        # native_map already strip it, and this comparison was the one
        # place still working on the raw spelling.
        canon = native_step._strip_default_composition_set
        phases_a = {canon(name) for name in result_a["phase_molar_amounts"]}
        phases_b = {canon(name) for name in result_b["phase_molar_amounts"]}
        comparison = {
            "gibbs_energy_difference_J": result_b["gibbs_energy_J"] - result_a["gibbs_energy_J"],
            "phases_only_in_" + label_a: sorted(phases_a - phases_b),
            "phases_only_in_" + label_b: sorted(phases_b - phases_a),
            "phases_in_both": sorted(phases_a & phases_b),
        }
        # Say what the difference means, because the field name alone says
        # something false. "Lower Gibbs energy" is how stability is decided
        # BETWEEN STATES OF ONE SYSTEM -- which phases a given composition
        # adopts. Between two different compositions there is no such
        # comparison: each G is the energy of a different system relative
        # to its own elements' reference states, so swapping 2% Fe for 2%
        # Mo moves G by the reference contribution of that swap and says
        # nothing about how favourable either alloy is.
        #
        # Measured: asked which of Fe-20Cr and Fe-20Cr-2Mo is more stable
        # at 1273 K, the client model read this field correctly (-569 J)
        # and concluded the molybdenum alloy was more stable. Both are
        # single-phase ferrite; neither is more stable than the other. It
        # took the framing the field name offered, and there was none
        # anywhere else to take.
        kimlik = ("gibbs-difference-is-a-ranking"
                  if _same_elements(composition_a, composition_b)
                  else "gibbs-difference-is-not-a-ranking")
        comparison["gibbs_energy_difference_note"] = settings_engine.note(kimlik)

    return {
        label_a: result_a,
        label_b: result_b,
        "comparison": comparison,
    }


@mcp.tool()
@_with_stop_rule
@call_log.logged
def calculate_property_diagram(
    database: str,
    elements_composition: dict[str, float],
    temperature_min_K: float,
    temperature_max_K: float,
    n_points: int = 15,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    suspended_phases: Optional[list[str]] = None,
    composition_basis: Optional[str] = None,
):
    """Sweep temperature and calculate a phase diagram over that range.

    {STOP_RULE}

    If the rejection carries an "alternative" field, the question IS
    answerable — just not by this tool. Call the tool it names, with the
    same question. That is routing, not substitution, and the rule below
    does not apply to it.

    Otherwise: do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason to the user (including any list of
    valid elements or phases it names) and ask which corrected request they
    want. Naming options is fine; running one is not.

    Primary method: runs OpenCalphad's own native STEP algorithm (the same
    continuation-based calculation its GUI uses), rendered with real
    gnuplot. STEP's internal solver can fail to converge at some
    temperatures (a known engine limitation, unrelated to this specific
    composition/database); any such gaps are transparently filled in with
    independent single-point native equilibrium calls so the chart has no
    holes -- each returned point says whether it came from "step" or
    "native_fallback". If the native STEP/gnuplot path fails entirely (or
    suspended_phases is given, which it doesn't support yet), this falls
    back to the original method: repeating calculate_equilibrium across the
    range and plotting with matplotlib (phase molar amount on top, Gibbs
    energy on the bottom -- the Gibbs panel keeps the chart informative
    even when the system stays single-phase the whole way through).
    Either way, the returned chart is the complete, intended visualization
    for this data — present it as-is rather than building a separate plot
    yourself.

    Args:
        database: database filename or full path.
        elements_composition: element -> molar amount (same rules as
            calculate_equilibrium — at least two nonzero elements).
        temperature_min_K: lower end of the temperature sweep, in Kelvin.
        temperature_max_K: upper end of the temperature sweep, in Kelvin.
        n_points: how many temperature points to sample (default 15). Keep
            this modest (<=30) — each point may require its own calculation.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).
        suspended_phases: phase names to exclude from the calculation.
            Must be phases the database actually declares. Only supported
            by the matplotlib fallback (native STEP path is skipped
            entirely when this is given).

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran on it before handing it back -- phase fractions
    summing to one, values in range, no NaN, and for a sweep, how many
    points actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    if n_points < 2:
        n_points = 2

    problems = preflight.check_property_diagram_request(
        database, elements_composition, temperature_min_K, temperature_max_K,
        pressure_Pa, suspended_phases,
        composition_basis=composition_basis,
    )
    if problems:
        return _preflight_failure(problems)

    # After the rejection rules, not before.
    elements_composition, _basis_report, _red = _canonical_composition(
        elements_composition, composition_basis)
    if _red is not None:
        return _red

    _diagram_args = {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_min_K": temperature_min_K,
        "temperature_max_K": temperature_max_K,
        "n_points": n_points,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": suspended_phases,
    }

    if not suspended_phases:
        try:
            db_path = (
                database if os.path.isabs(database)
                else os.path.join(oc_service.DEFAULT_DB_DIR, database)
            )
            combined, gap_filled_temperatures = native_step.build_combined_series(
                db_path, elements_composition, temperature_min_K,
                temperature_max_K, n_points, pressure_Pa,
            )
            chart_title = f"{os.path.basename(database)} property diagram"
            with tempfile.TemporaryDirectory() as tmpdir:
                png_path = os.path.join(tmpdir, "diagram.png")
                chart_bytes = native_step.render_gnuplot_png(
                    combined, chart_title, png_path,
                )
            points = [
                {
                    "temperature_K": T,
                    "phase_molar_amounts": fractions,
                    "source": source,
                }
                for T, fractions, source in combined
            ]
            window_opened = native_step.open_interactive_window(combined, chart_title)
            data = {
                "database": os.path.basename(database),
                "composition": elements_composition,
                "pressure_Pa": pressure_Pa,
                "suspended_phases": [],
                "points": points,
                "backend_used": "native_oc_step_gnuplot",
                "interactive_window_opened": window_opened,
                "native_step_points": len(combined) - len(gap_filled_temperatures),
                "gap_filled_points": len(gap_filled_temperatures),
                "note": (
                    "Phase values from OpenCalphad's native STEP are mass "
                    "fractions; temperatures where STEP's own solver could "
                    "not converge were filled in with independent "
                    "single-point native equilibrium calls instead (molar "
                    "amounts) so the chart has no gaps -- both are scaled "
                    "0-1 and shown together as an approximation, see each "
                    "point's 'source' field."
                ),
                "chart_error": None,
            }
            _canonical_phases(data)
            _attach_basis(data, "phase_mass_fraction")
            _attach_mixed_basis_note(data)
            _attach_scan_summary(data, "temperature_K")
            _attach_coverage(data, "temperature_K", n_points,
                             temperature_min_K, temperature_max_K)
            return [
                _attach_verification(data, _diagram_args,
                                     declared_basis=_basis_report),
                Image(data=chart_bytes, format="png"),
            ]
        except Exception as exc:
            # settings/execution.toml, policy.unnamed_failure = "surface":
            # only an engine failure moves us to the next tier. Ours is
            # re-raised, because a fallback that absorbs a typo returns a
            # slower answer and no sign that anything went wrong.
            if not settings_engine.is_engine_failure(exc):
                raise
            native_backend_error = str(exc)
    else:
        native_backend_error = (
            "native STEP backend does not support suspended_phases yet; "
            "used the matplotlib fallback instead."
        )

    step = (temperature_max_K - temperature_min_K) / (n_points - 1)
    temperatures = [temperature_min_K + i * step for i in range(n_points)]

    points = []
    phase_series: dict[str, list] = {}
    for T in temperatures:
        result = _calc_one(database, elements_composition, T, pressure_Pa, suspended_phases)
        if "error" in result or not result.get("phase_molar_amounts"):
            points.append({
                "temperature_K": T,
                "source": "python_loop",
                "error": result.get("error") or (
                    "Calculation returned no stable phases (likely an "
                    "unreliable/degenerate solve at this point)."
                ),
            })
            continue
        amounts = result["phase_molar_amounts"]
        points.append({
            "temperature_K": T,
            "gibbs_energy_J": result["gibbs_energy_J"],
            "phase_molar_amounts": amounts,
            # Every point names what produced it. The other two tiers did
            # this already; this one was missed, and the floor invariant is
            # what surfaced it.
            "source": "python_loop",
        })
        for phase in amounts:
            phase_series.setdefault(phase, [None] * n_points)

    for i, point in enumerate(points):
        amounts = point.get("phase_molar_amounts", {})
        for phase, series in phase_series.items():
            series[i] = amounts.get(phase, 0.0) if "error" not in point else None

    gibbs_series = [
        p["gibbs_energy_J"] if "error" not in p else None for p in points
    ]

    chart_bytes = None
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        # Two panels always: phase molar amount (top) and Gibbs energy
        # (bottom). A single-phase sweep makes the top panel a flat line,
        # but the bottom panel (which always varies with T) keeps the chart
        # informative on its own, without needing a second, separate plot.
        fig, (ax_phase, ax_gibbs) = plt.subplots(
            2, 1, figsize=(7, 7), sharex=True, height_ratios=[1.2, 1]
        )
        for phase, series in phase_series.items():
            ax_phase.plot(temperatures, series, marker="o", label=phase)
        ax_phase.set_ylabel("Phase molar amount")
        ax_phase.set_title(f"{os.path.basename(database)} property diagram")
        ax_phase.legend(fontsize="small")
        ax_phase.grid(True, alpha=0.3)

        ax_gibbs.plot(temperatures, gibbs_series, marker="o", color="tab:red")
        ax_gibbs.set_xlabel("Temperature (K)")
        ax_gibbs.set_ylabel("Gibbs energy (J/mol)")
        ax_gibbs.grid(True, alpha=0.3)

        fig.tight_layout()
        buf = io.BytesIO()
        fig.savefig(buf, format="png", dpi=110, bbox_inches="tight")
        plt.close(fig)
        chart_bytes = buf.getvalue()
    except Exception as exc:  # chart is a bonus, never fail the whole call over it
        chart_error = str(exc)
    else:
        chart_error = None

    data = {
        "database": os.path.basename(database),
        "composition": elements_composition,
        "pressure_Pa": pressure_Pa,
        "suspended_phases": list(suspended_phases) if suspended_phases else [],
        "points": points,
        "backend_used": "python_loop_matplotlib",
        "native_backend_error": native_backend_error,
        "chart_error": chart_error,
    }
    # This tier calls the single-point path once per temperature, so its
    # numbers are MOLAR amounts -- not the mass fractions the STEP series
    # carries. Same tool, same field name, different quantity depending on
    # which tier answered, which is the whole reason the basis is stated.
    _canonical_phases(data)
    _attach_basis(data, "phase_molar_amount")
    _attach_mixed_basis_note(data)
    _attach_scan_summary(data, "temperature_K")
    _attach_coverage(data, "temperature_K", n_points,
                     temperature_min_K, temperature_max_K)
    _attach_verification(data, _diagram_args,
                         declared_basis=_basis_report)
    if chart_bytes:
        return [data, Image(data=chart_bytes, format="png")]
    return data


@mcp.tool()
@_with_stop_rule
@call_log.logged
def calculate_isothermal_section(
    database: str,
    elements_composition: dict[str, float],
    axis_element: str,
    axis_min: float,
    axis_max: float,
    temperature_K: float,
    n_points: int = 15,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    composition_basis: Optional[str] = None,
):
    """Hold temperature fixed and scan one element's content instead.

    The companion to calculate_property_diagram, which asks "what happens
    to this alloy as it heats". This asks the other standard question:
    "at this temperature, what forms as I add more of this element" --
    an isothermal section. Use it for questions phrased as adding,
    increasing, or varying an element rather than heating or cooling.

    {STOP_RULE}

    If the rejection carries an "alternative" field, the question IS
    answerable — just not by this tool. Call the tool it names, with the
    same question. That is routing, not substitution, and the rule below
    does not apply to it.

    Otherwise: do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason to the user (including any list of
    valid elements it names) and ask which corrected request they want.
    Naming options is fine; running one is not.

    Method: OpenCalphad's own native STEP algorithm, with the scanned
    element's mole fraction as the axis. STEP follows a line by
    continuation rather than re-minimising at every position, so where its
    line terminates the missing positions are filled with independent
    single-point equilibrium calls, and its two endpoints are read a
    second time from that same single-point engine -- a continuation can
    stay on a phase set that has stopped being the stable one, and the
    endpoint is where it has drifted furthest. Each returned point says
    which engine produced it via its "source" field. If the native STEP
    path fails entirely, the whole axis is scanned single-point instead.
    The returned chart is the complete, intended visualization for this
    data — present it as-is rather than building a separate plot yourself.

    Args:
        database: database filename or full path.
        elements_composition: element -> molar amount, giving the alloy the
            scan starts from. Needs at least three elements: the scanned
            one, plus one to stay fixed and one to take up the remainder.
            The scanned element's own value here is replaced by the axis.
        axis_element: which element's mole fraction to scan.
        axis_min: mole fraction at the start of the scan.
        axis_max: mole fraction at the end of the scan.
        temperature_K: the fixed temperature, in Kelvin.
        n_points: how many positions to sample (default 15). Keep this
            modest (<=30) — each position may require its own calculation.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).

    VERIFICATION
    Every result carries a "verification" field recording the
    deterministic checks this server ran on it before handing it back --
    phase fractions summing to one, values in range, no NaN, and how many
    positions actually converged. Report its outcome next to the numbers.
    Someone reading a calculation has no other way to know whether it was
    checked, and a result that was checked and one that was not must not
    look alike to them. If "passed" is false, say what "problems" lists
    rather than presenting the numbers as if nothing had been found.
    """
    if n_points < 2:
        n_points = 2

    problems = preflight.check_isothermal_section_request(
        database, elements_composition, axis_element, axis_min, axis_max,
        temperature_K, pressure_Pa,
        composition_basis=composition_basis,
    )
    if problems:
        return _preflight_failure(problems)

    # After the rejection rules, not before.
    elements_composition, _basis_report, _red = _canonical_composition(
        elements_composition, composition_basis)
    if _red is not None:
        return _red

    _section_args = {
        "database": database,
        "elements_composition": elements_composition,
        "axis_element": axis_element,
        "axis_min": axis_min,
        "axis_max": axis_max,
        "temperature_K": temperature_K,
        "n_points": n_points,
        "pressure_Pa": pressure_Pa,
    }
    db_path = (
        database if os.path.isabs(database)
        else os.path.join(oc_service.DEFAULT_DB_DIR, database)
    )
    symbol = axis_element.upper()
    chart_title = (
        f"{os.path.basename(database)} isothermal section at {temperature_K:g} K"
    )
    x_label = f"x({symbol})"

    def _shape(combined, source_counts, backend, extra):
        points = [
            {
                "x": x,
                "axis_element": symbol,
                "temperature_K": temperature_K,
                "phase_molar_amounts": fractions,
                "source": source,
            }
            for x, fractions, source in combined
        ]
        data = {
            "database": os.path.basename(database),
            "composition": elements_composition,
            "axis_element": symbol,
            "axis_min": axis_min,
            "axis_max": axis_max,
            "temperature_K": temperature_K,
            "pressure_Pa": pressure_Pa,
            "points": points,
            "backend_used": backend,
        }
        data.update(source_counts)
        data.update(extra)
        _attach_axis_basis(data)
        _canonical_phases(data)
        _attach_basis(data, "phase_mass_fraction")
        _attach_mixed_basis_note(data)
        _attach_scan_summary(data, "x", to_weight_percent=lambda v:
                             settings_engine.axis_weight_percent(
                                 elements_composition, symbol, v))
        return _attach_coverage(data, "x", n_points, axis_min, axis_max)

    try:
        combined, gap_filled = native_step.build_combined_series(
            db_path, elements_composition, temperature_K, temperature_K,
            n_points, pressure_Pa,
            axis_element=symbol, axis_min=axis_min, axis_max=axis_max,
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = os.path.join(tmpdir, "section.png")
            chart_bytes = native_step.render_gnuplot_png(
                combined, chart_title, png_path, x_label=x_label,
            )
        window_opened = native_step.open_interactive_window(
            combined, chart_title, x_label=x_label
        )
        data = _shape(
            combined,
            {
                "native_step_points": len(combined) - len(gap_filled),
                "gap_filled_points": len(gap_filled),
            },
            "native_oc_step_gnuplot",
            {
                "interactive_window_opened": window_opened,
                "note": (
                    "Values from native STEP are phase mass fractions; "
                    "positions its line did not reach, and its two "
                    "endpoints where a second reading disagreed, come from "
                    "single-point equilibrium calls converted to the same "
                    "basis. See each point's 'source' field."
                ),
                "chart_error": None,
            },
        )
        return [
            _attach_verification(data, _section_args,
                                 declared_basis=_basis_report),
            Image(data=chart_bytes, format="png"),
        ]
    except Exception as exc:
        if not settings_engine.is_engine_failure(exc):
            raise
        native_backend_error = str(exc)

    # Native STEP could not run at all. The axis is still perfectly
    # scannable one position at a time -- that is what fills its gaps in
    # the normal path anyway -- so the fallback is the same calculation
    # without the continuation, not a different or lesser answer.
    combined = []
    failures = []
    for i in range(n_points):
        x = axis_min + (axis_max - axis_min) * i / (n_points - 1)
        try:
            point_composition = native_step.composition_at(
                elements_composition, symbol, x
            )
        except Exception as exc:
            failures.append({"x": x, "error": str(exc)})
            continue
        result = _calc_one(
            database, point_composition, temperature_K, pressure_Pa, None
        )
        if "error" in result or not result.get("phase_molar_amounts"):
            failures.append({
                "x": x,
                "error": result.get("error") or (
                    "Calculation returned no stable phases at this position."
                ),
            })
            continue
        # Same spelling as the native path uses. build_combined_series
        # strips the default "#1" composition set from every name it
        # returns; this path did not, so the two ways of answering one
        # question named the same phase differently -- BCC_A2 from STEP,
        # BCC_A2#1 from here. A caller comparing the two, or a test
        # naming a phase, sees a difference that is not in the chemistry.
        mass_fractions = native_step._phase_mass_fractions_from_moles(
            result["phase_molar_amounts"], result["phase_element_composition"]
        )
        combined.append((
            x,
            {native_step._strip_default_composition_set(name): value
             for name, value in mass_fractions.items()},
            "native_fallback",
        ))

    if not combined:
        return {
            "error": (
                "The composition axis could not be scanned: native STEP "
                f"failed ({native_backend_error}) and every single-point "
                "position failed as well."
            ),
            "stage": "EXECUTION",
            "failed_positions": failures,
        }

    chart_bytes = None
    chart_error = None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = os.path.join(tmpdir, "section.png")
            chart_bytes = native_step.render_gnuplot_png(
                combined, chart_title, png_path, x_label=x_label,
            )
    except Exception as exc:  # a chart is a bonus, never fail the call over it
        chart_error = str(exc)

    data = _shape(
        combined,
        {"native_step_points": 0, "gap_filled_points": len(combined)},
        "single_point_scan",
        {
            "native_backend_error": native_backend_error,
            "failed_positions": failures,
            "chart_error": chart_error,
        },
    )
    _attach_verification(data, _section_args,
                         declared_basis=_basis_report)
    if chart_bytes:
        return [data, Image(data=chart_bytes, format="png")]
    return data


@mcp.tool()
@_with_stop_rule
@call_log.logged
def calculate_scheil_solidification(
    database: str,
    elements_composition: dict[str, float],
    seed_temperature_K: float,
    temperature_min_K: Optional[float] = None,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    temperature_step_K: Optional[float] = None,
    composition_basis: Optional[str] = None,
):
    """Simulate non-equilibrium solidification (Scheil-Gulliver).

    A different question from every other tool here. The others compute
    equilibrium: given conditions, what is stable. This computes a PATH.
    The liquid is taken as homogeneous, the solid formed at each
    temperature step is removed from the system, and the remaining liquid's
    composition is updated accordingly -- which is what a real casting
    does, because diffusion in the solid is too slow to keep up with
    freezing. Use it for questions about casting, solidification,
    segregation, or why the last part of a melt to freeze differs from the
    first.

    {STOP_RULE}

    If the rejection carries an "alternative" field, the question IS
    answerable — just not by this tool. Call the tool it names, with the
    same question. That is routing, not substitution, and the rule below
    does not apply to it.

    Otherwise: do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason to the user and ask which
    corrected request they want.

    A stage="PRECONDITION" result is different and DOES invite a retry: it
    means the seed temperature is not in the single-phase liquid, and it
    names what was stable there instead. Solidification has to start from a
    melt. Suggest a higher seed temperature and ask before re-running.

    Args:
        database: database filename or full path.
        elements_composition: element -> molar amount. At least two.
        seed_temperature_K: where the simulation starts, in Kelvin. Must be
            hot enough that the alloy is entirely liquid.
        temperature_min_K: how far down to cool (default: 800 K below the
            seed). Solidification usually ends well above this.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).
        temperature_step_K: the cooling increment. Leave unset to let the
            server try several and keep whichever got furthest -- this is
            not a display setting, it changes how far the simulation gets,
            and no observable property predicts which value will work.

    READING THE RESULT
    "completed" is the field that decides how the curve may be described.
    True means the melt was spent and the path is the whole story. False
    means the simulation stopped with liquid still unsolidified, and
    "final_liquid_fraction" says how much: report that figure rather than
    presenting a partial curve as a finished solidification. The last few
    per cent is where the terminal eutectic forms, so a run that stopped at
    12% left out the part a segregation question was usually asking about.

    "liquid_composition" at each point is the segregation: watch an element
    climb from its nominal value toward the last liquid. That enrichment is
    the result, not a side effect.

    VERIFICATION
    Every result carries a "verification" field recording the deterministic
    checks this server ran. Report its outcome next to the numbers.
    """
    if temperature_min_K is None:
        temperature_min_K = max(seed_temperature_K - 800.0, 1.0)

    problems = preflight.check_scheil_request(
        database, elements_composition, seed_temperature_K,
        temperature_min_K, pressure_Pa,
        composition_basis=composition_basis,
    )
    if problems:
        return _preflight_failure(problems)

    # After the rejection rules, not before.
    elements_composition, _basis_report, _red = _canonical_composition(
        elements_composition, composition_basis)
    if _red is not None:
        return _red

    db_path = (
        database if os.path.isabs(database)
        else os.path.join(oc_service.DEFAULT_DB_DIR, database)
    )

    # Scheil's own precondition, checked by computing it rather than by
    # hoping. The engine states it plainly ("you must have calculated an
    # equilibrium in the liquid") and then, given a seed that is already
    # part solid, fails somewhere deep in its line tracer with an error
    # code that says nothing about the real problem. One equilibrium is far
    # cheaper than one simulation, and it can name what was stable instead.
    seed = _calc_one(database, elements_composition, seed_temperature_K,
                     pressure_Pa, None)
    if "error" not in seed:
        amounts = seed.get("phase_molar_amounts") or {}
        solid = [name for name, amount in amounts.items()
                 if amount > 1e-6 and not name.upper().startswith("LIQUID")]
        if solid:
            return {
                "error": settings_engine.precondition(
                    "scheil-seed-is-liquid",
                    seed=format(seed_temperature_K, "g"),
                    phases=sorted(solid),
                ),
                "stage": "PRECONDITION",
                "phases_at_seed": {k: float(f"{v:.6g}") for k, v in amounts.items()},
                "seed_temperature_K": seed_temperature_K,
            }

    _scheil_args = {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_K": seed_temperature_K,
        "pressure_Pa": pressure_Pa,
    }

    try:
        result = native_scheil.run_with_step_ladder(
            db_path, elements_composition, seed_temperature_K,
            temperature_min_K, pressure_Pa,
            temperature_step_K=temperature_step_K,
            timeout=CALC_TIMEOUT_S,
        )
    except Exception as exc:
        return {
            "error": f"The Scheil simulation could not be run: {exc}",
            "stage": "EXECUTION",
        }

    points = [
        {
            "temperature_K": p["temperature_K"],
            "liquid_fraction": float(f"{p['liquid_fraction']:.6g}"),
            "liquid_composition": {
                el: float(f"{v:.6g}") for el, v in p["liquid_composition"].items()
            },
        }
        for p in result["points"]
    ]

    data = {
        "database": os.path.basename(database),
        "composition": elements_composition,
        "pressure_Pa": pressure_Pa,
        "seed_temperature_K": seed_temperature_K,
        "liquidus_K": result["liquidus_K"],
        "solid_phases_formed": result["solid_phases"],
        "points": points,
        "completed": result["completed"],
        "final_liquid_fraction": result["final_liquid_fraction"],
        "final_temperature_K": result["final_temperature_K"],
        "termination_reason": result["termination_reason"],
        "temperature_step_K": result["temperature_step_K"],
        "steps_tried": result["steps_tried"],
        "backend_used": "native_oc_scheil",
        "note": (
            "Scheil is a path, not an equilibrium: each point depends on "
            "all the solid removed above it. A temperature the simulation "
            "did not reach cannot be filled in by computing it separately, "
            "which is why an incomplete run is reported as incomplete "
            "rather than completed by other means."
        ),
    }
    return _attach_verification(data, _scheil_args,
                                declared_basis=_basis_report)


@mcp.tool()
@_with_stop_rule
@call_log.logged
def calculate_phase_diagram(
    database: str,
    elements_composition: dict[str, float],
    axis_element: str,
    axis_min: float,
    axis_max: float,
    temperature_min_K: float,
    temperature_max_K: float,
    seed_temperature_K: Optional[float] = None,
    axis_step: Optional[float] = None,
    temperature_step_K: Optional[float] = None,
    pressure_Pa: float = _DEFAULT_PRESSURE,
    composition_basis: Optional[str] = None,
):
    """Trace the phase boundaries themselves across composition and temperature.

    The phase diagram, in the sense a metallurgist means it. The other
    tools each fix one axis: calculate_property_diagram fixes composition
    and sweeps temperature, calculate_isothermal_section fixes temperature
    and sweeps composition. This one fixes neither -- it follows the
    boundaries where phases meet, across both at once. Use it when someone
    asks for "the phase diagram" of a system rather than the behaviour of
    one alloy.

    {STOP_RULE}

    If the rejection carries an "alternative" field, the question IS
    answerable — just not by this tool. Call the tool it names, with the
    same question. That is routing, not substitution, and the rule below
    does not apply to it.

    Otherwise: do NOT call this or any other calculation tool again in
    this turn. Quote the rejection reason and ask which corrected request
    the user wants.

    Args:
        database: database filename or full path.
        elements_composition: element -> molar amount. This is the seed the
            diagram is traced outward from, not a restriction on it.
        axis_element: which element's mole fraction forms the horizontal axis.
        axis_min, axis_max: the composition range to map.
        temperature_min_K, temperature_max_K: the temperature range to map.
        seed_temperature_K: where tracing starts (default: mid-range). Must
            lie inside the temperature range.
        axis_step, temperature_step_K: how finely each axis is walked.
            These are steps, not point counts; leave unset for sensible
            defaults.
        pressure_Pa: pressure in Pascal (default 1e5, i.e. 1 bar).

    READING THE RESULT
    "boundaries" is a list of traced curves, each naming the phases that
    coexist along it. A boundary marked "invariant" is a reaction happening
    at one fixed temperature -- eutectic, eutectoid, peritectic -- and
    "invariant_temperatures_K" collects them, which is usually the first
    thing a reader wants from a diagram.

    MAP is the engine's most fragile calculation and says so itself before
    every run. If it produces nothing, that is reported as a failure rather
    than approximated: no other part of this engine traces boundaries, so
    there is nothing to fall back to. A property diagram at a fixed
    composition, or an isothermal section at a fixed temperature, is the
    nearest thing that will work.
    """
    if seed_temperature_K is None:
        seed_temperature_K = (temperature_min_K + temperature_max_K) / 2.0

    problems = preflight.check_phase_diagram_request(
        database, elements_composition, axis_element, axis_min, axis_max,
        temperature_min_K, temperature_max_K, seed_temperature_K, pressure_Pa,
        composition_basis=composition_basis,
    )
    if problems:
        return _preflight_failure(problems)

    # After the rejection rules, not before.
    elements_composition, _basis_report, _red = _canonical_composition(
        elements_composition, composition_basis)
    if _red is not None:
        return _red

    # Steps, not point counts. 40 across and 70 up match the distribution's
    # own map1.OCM, which is the only calibration available for what this
    # engine finds comfortable.
    if axis_step is None:
        axis_step = (axis_max - axis_min) / 40.0
    if temperature_step_K is None:
        temperature_step_K = (temperature_max_K - temperature_min_K) / 70.0

    db_path = (
        database if os.path.isabs(database)
        else os.path.join(oc_service.DEFAULT_DB_DIR, database)
    )
    symbol = axis_element.upper()
    title = f"{os.path.basename(database)} phase diagram"

    try:
        plt_text = native_map.run_native_map(
            db_path, elements_composition, symbol, axis_min, axis_max,
            axis_step, temperature_min_K, temperature_max_K,
            temperature_step_K, seed_temperature_K, pressure_Pa,
            timeout=CALC_TIMEOUT_S,
        )
        diagram = native_map.parse_map_plt(plt_text)
    except Exception as exc:
        return {
            "error": (
                f"The phase diagram could not be traced: {exc} MAP is the "
                "most fragile calculation this engine offers and has no "
                "fallback here. A property diagram at one composition, or "
                "an isothermal section at one temperature, covers the same "
                "system a slice at a time."
            ),
            "stage": "EXECUTION",
            "seed_temperature_K": seed_temperature_K,
        }

    chart_bytes = None
    chart_error = None
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = os.path.join(tmpdir, "diagram.png")
            chart_bytes = native_map.render_gnuplot_png(
                diagram, title, png_path,
                axis_min=axis_min, axis_max=axis_max,
                temperature_min_K=temperature_min_K,
                temperature_max_K=temperature_max_K,
            )
    except Exception as exc:  # a chart is a bonus, never fail the call over it
        chart_error = str(exc)

    boundaries = [
        {
            "phases": b["phases"],
            "invariant": b["invariant"],
            **({"temperature_K": b["temperature_K"]} if b["invariant"] else {}),
            "point_count": len(b["points"]),
            "points": [
                {
                    "temperature_K": float(f"{p['temperature_K']:.6g}"),
                    "compositions": {
                        phase: float(f"{value:.6g}")
                        for phase, value in p["compositions"].items()
                    },
                }
                for p in b["points"]
            ],
        }
        for b in diagram["boundaries"]
    ]

    data = {
        "database": os.path.basename(database),
        "axis_element": diagram["axis_element"] or symbol,
        "axis_min": axis_min,
        "axis_max": axis_max,
        "temperature_min_K": temperature_min_K,
        "temperature_max_K": temperature_max_K,
        "pressure_Pa": pressure_Pa,
        "seed_temperature_K": seed_temperature_K,
        "phases": diagram["phases"],
        "invariant_temperatures_K": diagram["invariant_temperatures_K"],
        "boundaries": boundaries,
        "point_count": diagram["point_count"],
        "backend_used": "native_oc_map",
        "chart_error": chart_error,
        "note": (
            "Each boundary is a curve along which the named phases coexist. "
            "An invariant boundary is a reaction at one fixed temperature. "
            "The chart is the complete intended visualization for this "
            "data -- present it as-is rather than building a separate plot."
        ),
    }
    _attach_verification(data, {
        "database": database,
        "elements_composition": elements_composition,
        "temperature_K": seed_temperature_K,
        "pressure_Pa": pressure_Pa,
    }, declared_basis=_basis_report)
    if chart_bytes:
        return [data, Image(data=chart_bytes, format="png")]
    return data


if __name__ == "__main__":
    mcp.run(transport="stdio")
