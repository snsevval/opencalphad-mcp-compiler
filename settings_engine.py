"""Reads settings/*.toml and applies them. The rules live there; the
machinery to apply them lives here.

Why this exists
---------------
The rules this server runs by were written in four different languages:
preflight checks as Python conditionals, fallback decisions as nested
try/except across five files, output notes as embedded strings, and one
stop rule hand-copied into six docstrings. Answering "what does this
system check, and why?" meant reading four files. Correcting the stop rule
meant editing six copies by hand.

They are now three TOML files. This module is what makes them load-bearing
rather than documentation: a rule that is written down but not applied is
worse than no rule at all, because it reads as a guarantee.

What is here and what is not
----------------------------
`check` names a predicate, and the predicates are below. Adding a rule of
a kind already listed in the settings is a change to the TOML alone.
Adding a kind that has never existed needs one small function here as
well -- that is the honest limit of "rules only through the file", and it
is roughly a fifth of the rules we have added so far.

Message text is reproduced exactly, down to the format specifiers. That is
not fussiness: the benchmark compares rejection reasons as substrings, and
more to the point, a caller reads these. Moving a rule must not reword it.
Rewording is a decision to take on purpose, and separately.
"""

import os
import tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS_DIR = os.path.join(HERE, "settings")


def _load(name):
    with open(os.path.join(SETTINGS_DIR, name + ".toml"), "rb") as handle:
        return tomllib.load(handle)


INPUT = _load("input")
EXECUTION = _load("execution")
OUTPUT = _load("output")

ALL_OPERATIONS = set(INPUT["accept"]["operations"])   # compile rebinds this below


def _applies(rule, operation):
    scope = rule["applies"]
    if scope == "*":
        return True
    return operation in (scope if isinstance(scope, list) else [scope])


def _fields(rule):
    """A rule names one field, several, or none."""
    if "fields" in rule:
        return list(rule["fields"])
    if "field" in rule:
        return [rule["field"]]
    return []


# ---------------------------------------------------------------------
# Predicates.
#
# Each takes the rule, the request, and a context holding whatever cost
# something to compute (the database's declared elements and phases), and
# returns a list of problem strings -- empty when the rule is satisfied.
#
# They return strings rather than booleans because the message is part of
# the rule: several of these say what the database DOES contain, and that
# is what lets a caller repair the request instead of guessing.
# ---------------------------------------------------------------------

def _file_exists(rule, request, ctx):
    if ctx.get("db_path") and os.path.isfile(ctx["db_path"]):
        return []
    return [rule["message"].format(path=ctx.get("db_path"))]


def _database_parses(rule, request, ctx):
    if ctx.get("db_error") is None:
        return []
    return [rule["message"].format(error=ctx["db_error"])]


def _subset_of_database_elements(rule, request, ctx):
    requested = {el.upper() for el in request.get("composition") or {}}
    missing = requested - ctx["db_elements"]
    if not missing:
        return []
    return [rule["message"].format(missing=sorted(missing),
                                   database=ctx["db_name"],
                                   available=sorted(ctx["db_elements"]))]


def _basis_declared(rule, request, ctx):
    """The caller has named the basis their numbers are in.

    Required, not defaulted. A default turns silence into a declaration,
    and silence is exactly what produced a four-fold error in nitrogen --
    see the rule's `because` in input.toml.
    """
    if not request.get("composition"):
        return []          # another rule owns an empty composition
    izinli = INPUT["accept"]["composition"].get("basis", {}).get(
        "values", ["mole_fraction"])
    beyan = request.get("composition_basis")
    if beyan in izinli:
        return []
    if beyan:
        return ["composition_basis %r is not one of: %s"
                % (beyan, ", ".join(izinli))]
    return [rule["message"].strip()]


def _min_nonzero_count(rule, request, ctx):
    composition = request.get("composition") or {}
    if len({el.upper() for el in composition}) >= rule["minimum"]:
        return []
    return [rule["message"]]


def _subset_of_database_phases(rule, request, ctx):
    named = request.get("phase_status") or []
    if not named:
        return []
    unknown = set()
    for name in named:
        # "FCC_A1#2" -> "FCC_A1": composition sets are a runtime concept,
        # a TDB declares only the base phase name.
        base = name.split("#")[0].strip().upper()
        if base and base not in ctx["db_phases"]:
            unknown.add(name.upper())
    if not unknown:
        return []
    return [rule["message"].format(unknown=sorted(unknown),
                                   database=ctx["db_name"],
                                   available=sorted(ctx["db_phases"]))]


def _all_non_negative(rule, request, ctx):
    problems = []
    for element, amount in (request.get("composition") or {}).items():
        if amount < 0:
            problems.append(rule["message"].format(element=element, value=amount))
    return problems


def _sum_positive(rule, request, ctx):
    total = sum((request.get("composition") or {}).values())
    return [] if total > 0 else [rule["message"]]


def _sum_within(rule, request, ctx):
    """Is the composition on a plausible scale for the basis it declares?

    A weight_percent composition summing to 100 is correct; the same total
    in mole fractions is off by two orders of magnitude. One range for both
    refused a perfectly good weight-percent request.
    """
    total = sum((request.get("composition") or {}).values())
    if total <= 0:
        return []          # already reported by sum_positive; not twice

    baz = (request.get("composition_basis")
           or INPUT["accept"]["composition"].get("basis", {})
           .get("default", "mole_fraction"))
    aralik = (rule.get("scale_by_basis") or {}).get(baz)
    if not aralik:
        aralik = {"low": rule.get("low", 0.5), "high": rule.get("high", 2.0)}
    if aralik["low"] <= total <= aralik["high"]:
        return []
    return [rule["message"].format(total=format(total, ".4g"),
                                   expected=100 if aralik["high"] > 10 else 1,
                                   basis=baz)]


def _positive(rule, request, ctx):
    problems = []
    for field in _fields(rule):
        value = request.get(field)
        if value is None:
            continue
        if value <= 0:
            problems.append(rule["message"].format(field=field, value=value))
    return problems


def _range_ordered(rule, request, ctx):
    low_name, high_name = rule["low"], rule["high"]
    low, high = request.get(low_name), request.get(high_name)
    if low is None or high is None or low < high:
        return []
    return [rule["message"].format(low=low, high=high,
                                   low_name=low_name, high_name=high_name)]


def _axis_element_present(rule, request, ctx):
    axis = (request.get("axis_element") or "").upper()
    symbols = {el.upper() for el in request.get("composition") or {}}
    if axis in symbols:
        return []
    return [rule["message"].format(axis=request.get("axis_element"),
                                   symbols=sorted(symbols))]


def _fraction_within(rule, request, ctx):
    low, high, closed = rule["low"], rule["high"], rule["closed"]
    problems = []
    for field in _fields(rule):
        value = request.get(field)
        if value is None:
            continue
        ok = (low <= value <= high) if closed else (low <= value < high)
        if not ok:
            problems.append(rule["message"].format(field=field, value=value))
    return problems


def _min_element_count(rule, request, ctx):
    """Only when the scanned element IS in the composition.

    Mirrors an `elif` in the original: if the axis element is absent, that
    is the problem worth reporting, and counting the elements of an alloy
    the axis does not belong to says nothing useful. Found by fuzzing --
    the hand-written cases all had the axis element present.
    """
    composition = request.get("composition") or {}
    symbols = {el.upper() for el in composition}
    if (request.get("axis_element") or "").upper() not in symbols:
        return []
    if len(symbols) >= rule["minimum"]:
        return []
    return [rule["message"].format(axis=request.get("axis_element"))]


def _dependent_element_has_room(rule, request, ctx):
    """What is left for the dependent element at the far end of the scan.

    The macro holds the other elements fixed and lets one absorb the
    balance. If the axis reaches far enough, that one is driven negative.
    """
    composition = request.get("composition") or {}
    axis = (request.get("axis_element") or "").upper()
    axis_max = request.get("axis_max")
    total = sum(composition.values())
    # `total > 0`, not `total`: a negative sum is degenerate and the
    # original skips this check there rather than reporting against it.
    # (sum_positive has already rejected it.) Fuzz found the difference.
    if total <= 0 or axis_max is None or axis not in {e.upper() for e in composition}:
        return []
    others = sum(amount / total for el, amount in composition.items()
                 if el.upper() != axis)
    held = others - max(
        (amount / total for el, amount in composition.items()
         if el.upper() != axis),
        default=0.0,
    )
    if axis_max + held < 1.0:
        return []
    return [rule["message"].format(axis_max=axis_max, held=format(held, ".4g"))]


def _value_within_range(rule, request, ctx):
    value = request.get(rule["value"])
    low, high = request.get(rule["low"]), request.get(rule["high"])
    if value is None or low is None or high is None:
        return []
    if low <= value <= high:
        return []
    return [rule["message"].format(value=value, low=low, high=high)]


PREDICATES = {
    "file_exists": _file_exists,
    "database_parses": _database_parses,
    "subset_of_database_elements": _subset_of_database_elements,
    "basis_declared": _basis_declared,
    "min_nonzero_count": _min_nonzero_count,
    "subset_of_database_phases": _subset_of_database_phases,
    "all_non_negative": _all_non_negative,
    "sum_positive": _sum_positive,
    "sum_within": _sum_within,
    "positive": _positive,
    "range_ordered": _range_ordered,
    "axis_element_present": _axis_element_present,
    "fraction_within": _fraction_within,
    "min_element_count": _min_element_count,
    "dependent_element_has_room": _dependent_element_has_room,
    "value_within_range": _value_within_range,
    # single_phase_liquid_at_seed is a PRECONDITION: it costs a
    # calculation, so it is applied by the tool that can pay for one.
}


def _context(database):
    """Whatever the rules need that costs something to look up. Computed
    once per request rather than once per rule."""
    import oc_service          # imported here: cheap for callers that
                               # only want to read the settings
    ctx = {"db_path": None, "db_error": None, "db_name": database,
           "db_elements": set(), "db_phases": set()}
    if not database:
        ctx["db_error"] = "no database given"
        return ctx
    ctx["db_path"] = (database if os.path.isabs(database)
                      else os.path.join(oc_service.DEFAULT_DB_DIR, database))
    if not os.path.isfile(ctx["db_path"]):
        return ctx
    try:
        info = oc_service.inspect_database(database)
    except Exception as exc:                    # noqa: BLE001
        ctx["db_error"] = str(exc)
        return ctx
    ctx["db_name"] = info["name"]
    ctx["db_elements"] = set(info["elements"])
    ctx["db_phases"] = {p.upper() for p in info.get("phases", [])}
    return ctx


# ═════════════════════════════════════════════════════════════════════
# COMPILE
#
# The settings used to be read rule by rule, on every request. That is a
# rule engine, and it fails quietly: PREDICATES.get(rule["check"]) returns
# None for a name that does not exist, the loop moves on, and the rule is
# gone. Measured -- "min_nonzero_count" mistyped as "min_nonzero_kount"
# took a request from one complaint to none, with no error at load and no
# sign anywhere that a rule had stopped running. It is the same failure
# preflight.py had when nine rules sat in it that nobody called.
#
# So the files are resolved once, here, and the runtime reads only what
# comes out. Every name is bound to the thing it names while there is
# still someone to tell.
#
# The severity split is by consequence, not by tidiness:
#
#   STOPS     getting this wrong makes a rule silently not run
#   WARNS     getting this wrong leaves something declared and unused
#
# A server that will not start is a bad morning. A server that starts with
# a rule missing is a wrong answer nobody questions.
# ═════════════════════════════════════════════════════════════════════


class SettingsError(Exception):
    """A settings file names something the code cannot honour."""


# Keys that document rather than configure. Present everywhere, consumed
# by nothing, and not a sign of anything missing.
_DOCUMENTATION_KEYS = ("because", "status", "status_because", "id",
                       "applies", "message", "route_to", "route_note",
                       "match", "check")


class InputPolicy:
    """input.toml, resolved: which rules run for which operation, each one
    already bound to the predicate that carries it out."""

    def __init__(self, operations, defaults, composition,
                 common, per_operation, routes, preconditions, stop_rule):
        self.operations = operations          # set of names
        self.defaults = defaults              # {pressure_Pa: ...}
        self.composition = composition        # basis + normalise_to_one
        self.common = common                  # [(rule, predicate)]
        self.per_operation = per_operation    # {op: [(rule, predicate)]}
        self.routes = routes                  # {op: [(marker, note)]}
        self.preconditions = preconditions    # [rule]
        self.stop_rule = stop_rule            # what a rejection permits


class ExecutionPlan:
    """execution.toml, resolved: the tier order for each operation and the
    constants the run needs, looked up once instead of per request."""

    def __init__(self, cascades, endpoint_recheck, gap_detection,
                 reviewers, reviewer_budget, binary_order,
                 weak_independence, signals, scheil, engine_failures,
                 timeouts, tolerances, retry_http,
                 validator_reviewers, vision_reviewers):
        self.cascades = cascades              # {op: (tiers, entry)}
        self.endpoint_recheck = endpoint_recheck
        self.gap_detection = gap_detection
        self.reviewers = reviewers            # [ {model, independence} ]
        self.reviewer_budget = reviewer_budget
        self.binary_order = binary_order      # [(name, path)]
        self.weak_independence = weak_independence   # set of model names
        self.signals = signals                # set of signal names
        self.scheil = scheil                  # step ladder + completion
        self.engine_failures = engine_failures  # names that may advance a tier
        self.timeouts = timeouts              # how long each tier gets
        self.tolerances = tolerances          # when two numbers are one
        self.retry_http = retry_http          # provider replies worth retrying
        self.validator_reviewers = validator_reviewers  # the runner's chain
        self.vision_reviewers = vision_reviewers        # Layer C, reads charts


class OutputPlan:
    """output.toml, resolved: the wording and the derivations, keyed the
    way the runtime asks for them."""

    def __init__(self, derive, notes, conversion, floor, verify, honesty,
                 verification=None):
        self.derive = derive
        self.notes = notes                    # {id: text}
        self.verify = verify                  # [rule] -- Layer A, as declared
        self.verification = verification      # the same, bound to predicates
        self.honesty = honesty                # {id: rule} -- our own output
        self.conversion = conversion          # {name: block}
        self.floor = floor


class VerificationPlan:
    """Layer A's checks, resolved to their predicates once, at compile time.

    The declaration lives in output.toml and the arithmetic lives in
    result_check; this is the join between them, and it used to be made on
    every result -- a lazy import, a list comprehension and a dict lookup
    per rule, per calculation. It was never unsafe, because compile_settings
    refuses to start on a name that does not resolve. It was the rule-engine
    shape: the runtime holding names and looking them up as it went. The
    input rules have arrived pre-bound since the compiler went in, and these
    had not caught up.

    Keyed by stage because the two stages ask different questions and are
    reported differently -- `result` asks whether this is a well-formed
    thermodynamic answer, `correspondence` whether it answers the request
    that was made.
    """

    def __init__(self, asamalar):
        self._asamalar = asamalar             # {stage: [(rule, predicate)]}

    def for_stage(self, stage):
        """The checks declared for one stage, already bound. Order kept:
        output.toml lists them in the order they should run and a reader
        of the file should be reading the running order."""
        return self._asamalar.get(stage, ())

    def stages(self):
        return sorted(self._asamalar)

    def __len__(self):
        return sum(len(v) for v in self._asamalar.values())


class CompiledPolicy:
    """Everything the runtime is allowed to read. Built once, at import."""

    def __init__(self, input_policy, execution_plan, output_plan, warnings):
        self.input = input_policy
        self.execution = execution_plan
        self.output = output_plan
        self.warnings = warnings

    def report(self):
        """The warnings as text, for settings_audit and for startup."""
        if not self.warnings:
            return "DERLEME: temiz -- her ad bagli, okunmayan anahtar yok"
        satirlar = ["DERLEME: %d uyari" % len(self.warnings)]
        satirlar += ["   " + u for u in self.warnings]
        return "\n".join(satirlar)


def _consume_unread(block, consumed, path, warnings):
    """Warn about keys the compiler did not claim.

    Only for sections that carry no `status`: a section that says why it is
    unread has already answered this question. Everything else in a wired
    section should have a reader, and until now nothing checked -- which is
    how accept.defaults sat in the file with nine hardcoded copies of its
    value in the code.
    """
    for key, value in block.items():
        if key in _DOCUMENTATION_KEYS:
            continue
        p = "%s.%s" % (path, key)
        if p in consumed:
            continue
        if isinstance(value, dict):
            if "status" in value:
                continue
            _consume_unread(value, consumed, p, warnings)
        else:
            warnings.append("%s dosyada var, derleyici okumuyor" % p)


def compile_settings(giris=None, yurutme=None, cikti=None):
    """Resolve the three settings files into the policy the runtime reads.

    Raises SettingsError for anything that would make a rule quietly not
    run. Collects the rest as warnings, so a declared-but-unread key is
    visible without refusing to start.
    """
    giris = giris if giris is not None else INPUT
    yurutme = yurutme if yurutme is not None else EXECUTION
    cikti = cikti if cikti is not None else OUTPUT

    hatalar, uyarilar, consumed = [], [], set()

    # ---- input ------------------------------------------------------
    operations = set(giris["accept"]["operations"])
    consumed.add("input.accept.operations")

    defaults = dict(giris["accept"].get("defaults", {}))
    defaults.pop("because", None)
    for k in defaults:
        consumed.add("input.accept.defaults.%s" % k)

    composition = dict(giris["accept"].get("composition", {}))
    consumed.add("input.accept.composition.normalise_to_one")
    consumed.add("input.accept.composition.basis")

    common, per_operation, routes = [], {op: [] for op in operations}, \
        {op: [] for op in operations}

    for rule in giris["reject"] + giris["route"]:
        kimlik = rule.get("id", "<isimsiz>")
        kapsam = rule.get("applies", "*")
        # `applies` is "*", one operation name, or a list of them --
        # whichever _applies() already accepts.
        adlar = [] if kapsam == "*" else (
            kapsam if isinstance(kapsam, list) else [kapsam])
        bilinmeyen = [a for a in adlar if a not in operations]
        if bilinmeyen:
            hatalar.append("kural %r: applies=%r diye bir islem yok"
                           % (kimlik, bilinmeyen))
            continue

        ad = rule.get("check")
        if ad is not None:
            predicate = PREDICATES.get(ad)
            if predicate is None:
                hatalar.append(
                    "kural %r: check=%r diye bir yuklem yok -- kural "
                    "sessizce kosmayacakti" % (kimlik, ad))
                continue
            if kapsam == "*":
                common.append((rule, predicate))
            else:
                for op in operations:
                    if _applies(rule, op):
                        per_operation[op].append((rule, predicate))
            if not rule.get("message"):
                hatalar.append("kural %r: message yok, sikayet uretemez"
                               % kimlik)

        # A route may carry its own check, or be a pure router keyed by
        # `match` to text another rule produces.
        if rule.get("route_note"):
            isaret = rule.get("match") or \
                rule.get("message", "").split("{")[0].strip()[:40]
            if not isaret:
                hatalar.append(
                    "kural %r: route_note var ama eslesecek isaret yok -- "
                    "mesaj placeholder ile basliyor, `match` gerekli"
                    % kimlik)
                continue
            for op in operations:
                if _applies(rule, op):
                    routes[op].append((isaret, rule["route_note"].strip()))

    # A precondition's `check` does NOT name a predicate here: it costs a
    # calculation, so the tool that can pay for one performs it and calls
    # precondition() for the wording. What this side needs is an id to look
    # up by and a message to format -- those are what is checked.
    preconditions = list(giris.get("precondition", []))
    for rule in preconditions:
        if not rule.get("id"):
            hatalar.append("precondition: id yok, aranamaz")
        elif not rule.get("message"):
            hatalar.append("precondition %r: message yok, soyleyecegi sey yok"
                           % rule["id"])

    _consume_unread(giris["accept"], consumed, "input.accept", uyarilar)

    # ---- execution --------------------------------------------------
    signal_blok = yurutme.get("signals", {})
    signals = set(k for k in signal_blok
                  if k not in _DOCUMENTATION_KEYS
                  and k != "engine_failures")
    motor_hatalari = tuple(signal_blok.get("engine_failures", []))
    if not motor_hatalari:
        hatalar.append(
            "signals.engine_failures bos -- her motor arizasi kendi "
            "kademesinde kalirdi, hicbir yedek devreye giremezdi")

    cascades = {}
    for entry in yurutme.get("cascade", []):
        op = entry.get("operation")
        if op not in operations:
            hatalar.append("cascade: %r diye bir islem yok" % op)
            continue
        tiers = list(entry.get("tiers", []))
        if not tiers:
            hatalar.append("cascade %r: hic kademe yok" % op)
            continue
        for tier in tiers:
            if not tier.get("handler"):
                hatalar.append("cascade %r: handler adi olmayan kademe" % op)
            for sinyal in tier.get("on", []):
                if sinyal not in signals:
                    hatalar.append(
                        "cascade %r, kademe %r: on=%r diye bir sinyal yok "
                        "-- bu kademeye asla girilemezdi"
                        % (op, tier.get("handler"), sinyal))
        cascades[op] = (tiers, entry)

    hakemler = list(yurutme.get("reviewer", []))
    # The chain says which of ITS entries are weak; [independence] also
    # covers models selectable by hand that never appear in the chain.
    zayif = {r["model"] for r in hakemler
             if r.get("independence") == "weak" and r.get("model")}
    zayif |= set(yurutme.get("independence", {}).get("weak_models", []))

    ikili = yurutme.get("binary", {})
    yollar = ikili.get("paths", {})
    binary_order = [(ad, yollar[ad]) for ad in ikili.get("order", [])
                    if ad in yollar]
    for ad in ikili.get("order", []):
        if ad not in yollar:
            uyarilar.append("binary.order %r icin paths girdisi yok" % ad)

    execution_plan = ExecutionPlan(
        cascades=cascades,
        endpoint_recheck=dict(yurutme.get("endpoint_recheck", {})),
        gap_detection=dict(yurutme.get("gap_detection", {})),
        reviewers=hakemler,
        reviewer_budget=dict(yurutme.get("reviewer_budget", {})),
        binary_order=binary_order,
        weak_independence=zayif,
        signals=signals,
        scheil=dict(yurutme.get("scheil", {})),
        engine_failures=motor_hatalari,
        timeouts={k: v for k, v in yurutme.get("timeouts", {}).items()
                  if k != "because"},
        tolerances={k: v for k, v in yurutme.get("tolerances", {}).items()
                    if k != "because"},
        retry_http=set(yurutme.get("reviewer_retry", {}).get(
            "transient_http", [])),
        validator_reviewers=list(yurutme.get("validator_reviewer", [])),
        vision_reviewers=list(yurutme.get("vision_reviewer", [])),
    )

    # ---- output -----------------------------------------------------
    notlar = {}
    for n in cikti.get("note", []):
        kimlik = n.get("id")
        if not kimlik:
            hatalar.append("output.note: id'siz not")
            continue
        if not n.get("text") and not n.get("note"):
            uyarilar.append("not %r: metni bos" % kimlik)
        notlar[kimlik] = n

    # Layer A's checks. The predicates live in result_check, which imports
    # nothing, so reaching into it here is safe and the resolution happens
    # while there is still someone to tell about a name that does not
    # exist. A check declared and unresolvable would otherwise be a check
    # that silently never runs -- the failure this compiler was built for.
    dogrulamalar = list(cikti.get("verify", []))
    kayit = {}
    if dogrulamalar:
        try:
            import result_check
            kayit = result_check.VERIFY_PREDICATES
        except Exception as exc:                         # noqa: BLE001
            hatalar.append("verify: result_check okunamadi (%s)" % exc)
        for rule in dogrulamalar:
            kimlik = rule.get("id", "<isimsiz>")
            if not rule.get("check"):
                hatalar.append("verify %r: check adi yok" % kimlik)
            elif kayit and rule["check"] not in kayit:
                hatalar.append(
                    "verify %r: check=%r diye bir kontrol yok -- kural "
                    "sessizce kosmayacakti" % (kimlik, rule["check"]))
            if rule.get("stage") not in ("result", "correspondence"):
                hatalar.append("verify %r: stage=%r gecersiz"
                               % (kimlik, rule.get("stage")))

    # The binding itself. Rules that failed a check above are skipped here
    # and the error already recorded, so this never binds half a name --
    # and `hatalar` stops the import before anything reads the plan anyway.
    asamalar = {}
    for rule in dogrulamalar:
        yuklem = kayit.get(rule.get("check"))
        if yuklem is None or rule.get("stage") not in (
                "result", "correspondence"):
            continue
        asamalar.setdefault(rule["stage"], []).append((rule, yuklem))
    dogrulama_plani = VerificationPlan(asamalar)

    # [honesty] declares invariants about OUR behaviour, each naming a
    # predicate in result_check. Resolved here for the same reason the
    # verify checks are: an invariant nothing can run is a promise, and a
    # promise silently unkept is worse than one never made.
    durustluk = {k: v for k, v in cikti.get("honesty", {}).items()
                 if isinstance(v, dict) and v.get("check")}
    if durustluk:
        try:
            import result_check
            kayit_inv = result_check.OUTPUT_INVARIANTS
        except Exception as exc:                         # noqa: BLE001
            hatalar.append("honesty: result_check okunamadi (%s)" % exc)
            kayit_inv = {}
        for kimlik, kural in durustluk.items():
            if kayit_inv and kural["check"] not in kayit_inv:
                hatalar.append(
                    "honesty %r: check=%r diye bir degismez yok -- beyan "
                    "edilip hic kontrol edilmeyecekti" % (kimlik, kural["check"]))

    output_plan = OutputPlan(
        derive=dict(cikti.get("derive", {})),
        notes=notlar,
        conversion={k: v for k, v in cikti.get("conversion", {}).items()
                    if isinstance(v, dict)},
        floor=dict(cikti.get("floor", {})),
        verify=dogrulamalar,
        honesty=durustluk,
        verification=dogrulama_plani,
    )

    if hatalar:
        raise SettingsError(
            "ayar dosyalari acilamadi -- %d hata:\n   %s"
            % (len(hatalar), "\n   ".join(hatalar)))

    return CompiledPolicy(
        InputPolicy(operations, defaults, composition, common,
                    per_operation, routes, preconditions,
                    dict(giris.get("stop_rule", {}))),
        execution_plan, output_plan, uyarilar)


POLICY = compile_settings()
ALL_OPERATIONS = POLICY.input.operations
if POLICY.warnings:
    import sys as _sys
    print(POLICY.report(), file=_sys.stderr)


def check(operation, **request):
    """Apply the input rules for one operation.

    Returns a list of problem strings; empty means the request is valid.
    Same shape, and the same strings, as the hand-written checks it
    replaces -- the settings were verified against those message by
    message before this module was written.

    Stops early on a missing or unreadable database, as the original did:
    nothing else is checkable without the file.
    """
    if operation not in ALL_OPERATIONS:
        raise ValueError("unknown operation: %r" % operation)

    ctx = _context(request.get("database"))
    problems = []

    # Rules arrive already split and already bound to their predicates.
    # Nothing is looked up by name here any more: a name that resolved to
    # nothing would have stopped the import.
    #
    # Common rules first, then the operation's own -- and a missing or
    # unreadable database stops only the COMMON ones.
    #
    # That scope matters and was got wrong first time round: the original
    # returns early from its shared helper, but the per-operation checks
    # that follow the helper still run. A request naming a database that
    # does not exist AND a negative temperature reports both. Fuzzing
    # caught it; the hand-written cases never combined the two.
    for rule, predicate in POLICY.input.common:
        found = predicate(rule, request, ctx)
        problems.extend(found)
        if found and rule["id"] in ("database-exists", "database-readable"):
            break

    for rule, predicate in POLICY.input.per_operation.get(operation, []):
        problems.extend(predicate(rule, request, ctx))

    return problems


def route_for(operation, problems):
    """Alternatives for a rejection that is answerable elsewhere.

    Only for the "wrong tool" class. An impossible request gets nothing:
    inventing a route would push the caller toward a calculation nobody
    asked for, which is the failure the stop rule exists to prevent.

    The marker each route matches on is resolved at compile time, from
    `match` where a rule gives one and from the message otherwise. A route
    whose message opens with a placeholder yields an empty marker and could
    never fire -- that now stops the import instead of going unnoticed.
    """
    blob = " ".join(problems)
    notes = []
    for isaret, note in POLICY.input.routes.get(operation, []):
        if isaret in blob and note not in notes:
            notes.append(note)
    return notes

def stop_rule_block(indent="    "):
    """The stop rule as one block, ready to drop into a tool docstring.

    Assembled from settings/output.toml. It used to be six paragraphs
    typed out by hand in six docstrings, which is how a correction to it
    turned into six separate edits.
    """
    rule = POLICY.input.stop_rule
    lines = ["PREFLIGHT REJECTION — STOP RULE",
             "If the result has stage=\"PREFLIGHT\", the request was refused",
             "before any calculation ran. Two cases, and they call for",
             "opposite actions:",
             ""]
    for baslik, anahtar in (
        ("(a) The rejection carries an \"alternative\" field.", "on_route_present"),
        ("(b) No \"alternative\" field.", "on_no_route"),
        ("(c) stage=\"PRECONDITION\" is different again.", "on_precondition"),
        ("COMPOSITION BASIS is required on every request.",
         "on_composition_basis"),
    ):
        lines.append(baslik)
        lines.extend("    " + satir for satir in rule[anahtar].strip().split("\n"))
        lines.append("")
    return ("\n" + indent).join(lines).rstrip()


# ---------------------------------------------------------------------
# Output side.
#
# The rules above decide what runs. These decide what comes back and how
# it is worded -- which matters more than it sounds: a sentence that can
# be read two ways becomes a wrong finding, and one of these was read
# the wrong way in a live session.
# ---------------------------------------------------------------------

def note(note_id, **fields):
    """The text for one output note, filled in.

    Returns None when the note is not declared or is still `planned`, so
    a caller can leave the field out rather than emit an empty string.
    """
    for entry in POLICY.output.notes.values():
        if entry.get("id") != note_id:
            continue
        if entry.get("status") == "planned":
            return None
        try:
            return entry["text"].strip().format(**fields)
        except KeyError:
            # A template asking for a field the caller did not supply is a
            # settings bug, not a calculation failure. Hand back the
            # unfilled text rather than raising into someone's chemistry.
            return entry["text"].strip()
    return None


def derive_settings():
    """Tolerances the scan summary derives with."""
    d = POLICY.output.derive
    return {
        "presence_tolerance": d["presence_tolerance"],
        "dominance_threshold": d["dominance_threshold"],
        "enabled": list(d["enabled"]),
    }


def binary_order():
    """Which native engine build to try, in order, from execution.toml.

    Returns (name, path) pairs. The path may contain $OC_BUILD_DIR, which
    the caller expands -- where a build lives is environment, while which
    build is preferred is a measured decision and belongs in the file.
    """
    return list(POLICY.execution.binary_order)


def execution_number(bolum, anahtar, default):
    """One number from execution.toml, with the code's own value as the
    fallback. Timeouts and tolerances are policy -- raising a timeout
    changes whether a slow calculation returns or is abandoned -- but a
    missing settings file should not leave a subprocess waiting forever.
    """
    try:
        return getattr(POLICY.execution, bolum).get(anahtar, default)
    except Exception:                                    # noqa: BLE001
        return default


def conversion_setting(name):
    """What output.toml permits for one kind of basis conversion."""
    blok = POLICY.output.conversion.get(name)
    return dict(blok) if isinstance(blok, dict) else None


def axis_weight_percent(composition, axis_element, x):
    """The scanned element's weight per cent at axis position x.

    An axis position is a mole fraction of the scanned element in the
    overall composition, and the payload used to carry it as a bare number
    called `x`. Measured on 1.29: the caller converted 25 of them by hand
    and every figure came out low, because nickel is heavier than the alloy
    around it and the conversion has to move the other way.

    composition_at() is the same reconstruction the gap-fill uses, so the
    alloy converted here is the alloy the engine computed. Returns None
    rather than a guess whenever any part of that is unavailable -- an
    absent second basis is a gap, a wrong one is a wrong answer.
    """
    kural = conversion_setting("axis_position")
    if not kural or not kural.get("allowed"):
        return None
    try:
        import native_step
        kutle = native_step.ATOMIC_MASS
        tam = native_step.composition_at(composition, axis_element, x)
    except Exception:                                    # noqa: BLE001
        return None
    if any(el.upper() not in kutle for el in tam):
        return None
    agirlik = {el: v * kutle[el.upper()] for el, v in tam.items()}
    toplam = sum(agirlik.values())
    hedef = next((el for el in tam if el.upper() == axis_element.upper()), None)
    if toplam <= 0 or hedef is None:
        return None
    return round(100.0 * agirlik[hedef] / toplam, 4)


def precondition(check_id, **fields):
    """The message for a precondition that costs a calculation to test."""
    for entry in POLICY.input.preconditions:
        if entry.get("id") == check_id:
            return entry["message"].strip().format(**fields)
    return None


def coverage_note(cov, minimum_fraction=0.9):
    """The reader-facing sentence for a scan that came back short.

    The measurement itself lives in result_check.measure_requested_positions
    -- it is a check, and checks belong in that layer. What stays here is
    the wording, which comes from output.toml like every other note.
    """
    if not cov:
        return None
    if cov["covered_fraction"] >= minimum_fraction:
        return None
    return note(
        "scan-coverage-incomplete",
        solved=cov["solved_positions"],
        requested=cov["requested_positions"],
        covered_range="%.4g to %.4g" % tuple(cov["covered_range"]),
    )


def execution_setting(*path, default=None):
    """One value out of settings/execution.toml, by path.

    Falls back rather than raising: a settings file that cannot be read
    must not stop a calculation, and every default here is the number the
    file states anyway. The point of moving them was to make them
    readable in one place, not to add a way for the server to fail.
    """
    node = EXECUTION
    for key in path:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


def is_engine_failure(exc):
    """Does this exception name a signal the cascade is allowed to act on?

    settings/execution.toml declares `unnamed_failure = "surface"`: a
    failure matching no named signal does NOT advance a tier. Which names
    count is [signals].engine_failures in the same file.

    The isinstance block below stays in code on purpose. Those classes have
    SUBCLASSES, and catching a subclass is something a list of names cannot
    do -- our own bugs have to surface rather than fall through to a slower
    path that returns something plausible.

    The reason is measured in kind rather than in one incident: today a
    bare `except Exception` catches an engine fault and a typo in our own
    code alike, and the second one degrades quietly into the slower path
    and comes back looking like a success. A programming error should be
    loud. An engine limit is what the second tier exists for.
    """
    if isinstance(exc, (NameError, TypeError, AttributeError, KeyError,
                        IndexError, ImportError, SyntaxError,
                        ZeroDivisionError, UnboundLocalError)):
        return False
    return (type(exc).__name__ in POLICY.execution.engine_failures
            or isinstance(exc, OSError))


class CascadeExhausted(Exception):
    """Every tier for this operation was tried and none produced a result."""


def tiers_for(operation):
    """The tier list for one operation, in file order."""
    tiers, entry = POLICY.execution.cascades.get(operation, ([], {}))
    return list(tiers), entry


def run_cascade(operation, handlers, request=None):
    """Walk the tiers for `operation` in the order settings/execution.toml
    gives them, and return the first result.

    `handlers` maps a tier's `handler` name to a callable of no arguments.
    Each one keeps its own post-processing -- which fields it stamps on the
    result is its business, not this function's.

    Three rules, all read from the file rather than written here:

      order         the sequence of tiers
      on            which signals from the previous tier let us enter this
                    one; a failure naming no listed signal is re-raised,
                    because falling back on an unrecognised error is how a
                    bug in our own code turns into a slower answer that
                    looks like a success
      cannot_serve  a request field this tier is unable to honour at all.
                    Not a signal: a signal says why the last tier stopped,
                    this says what the next one cannot do.

    Reordering, adding or removing a tier is a change to the settings file.
    What a tier DOES stays in code, because that part is work rather than
    rule.
    """
    tiers, entry = tiers_for(operation)
    if not tiers:
        raise CascadeExhausted("no tiers declared for %r" % operation)

    request = request or {}
    ilk_hata = None
    denenen = []

    for index, tier in enumerate(tiers):
        ad = tier.get("handler")
        if ad not in handlers:
            continue

        if index > 0:
            # Entering this tier at all: is the previous failure one it
            # lists, and can it serve this request?
            izinli = tier.get("on") or []
            if ilk_hata is not None and not _signal_listed(ilk_hata, izinli):
                raise ilk_hata
            engel = [alan for alan in (tier.get("cannot_serve") or [])
                     if request.get(alan)]
            if engel:
                raise ilk_hata if ilk_hata else CascadeExhausted(
                    "%s cannot serve a request with %s" % (ad, engel))

        try:
            return handlers[ad]()
        except Exception as exc:                          # noqa: BLE001
            if not is_engine_failure(exc):
                raise
            denenen.append("%s: %s" % (ad, exc))
            if ilk_hata is None:
                ilk_hata = exc

    if entry.get("exhausted") == "fail_with_route" and entry.get("route_to"):
        raise CascadeExhausted("%s -> try %s instead"
                               % ("; ".join(denenen), entry["route_to"]))
    raise CascadeExhausted("; ".join(denenen) or "no handler ran")


def _signal_listed(exc, signal_names):
    """Does this failure match one of the signals a tier accepts?

    The signals are declared in the file and the mapping to exception
    types is here, because a type is a code fact. Today the engine layer
    does not distinguish "did not converge" from "crashed" -- both arrive
    as one error type -- so any engine failure matches any engine signal.
    Written this way rather than pretending to a precision we do not have.
    """
    if not signal_names:
        return True
    return is_engine_failure(exc)

def resolve_composition(composition, basis=None):
    """Turn a declared composition into the canonical mole fractions the
    engine is conditioned on.

    This is the INPUT side of the basis question, and until now it did not
    exist. input.toml declared the setting -- three values, a default, and
    a paragraph saying "declared, the conversion becomes ours and stops
    being arithmetic the caller has to get right" -- but the only code that
    read it ran AFTER the engine, on the result. So a caller who said
    weight_percent had their numbers conditioned as mole fractions anyway.

    That is not a rounding difference. W(C)=0.01 in iron is x(C)=0.045:
    hypereutectoid, austenite plus carbide. X(C)=0.01 is 0.217 wt%:
    hypoeutectoid, and a little ferrite at 1100 K. Two alloys, one payload,
    no way to tell which was computed.

    Returns (canonical, report). `canonical` is what the engine gets;
    `report` records what arrived, in which basis, and what it became --
    None when nothing needed doing, so a mole-fraction request looks
    exactly as it always did.
    """
    ayarlar = POLICY.input.composition.get("basis", {})
    izinli = ayarlar.get("values", ["mole_fraction"])
    basis = basis or ayarlar.get("default", "mole_fraction")
    if basis not in izinli:
        raise ValueError(
            "unknown composition basis %r; settings allow %s"
            % (basis, ", ".join(izinli)))

    if not composition:
        return composition, None

    toplam = sum(composition.values())
    if toplam <= 0:
        return composition, None          # a rejection rule owns this case

    normalise = POLICY.input.composition.get("normalise_to_one", True)
    olcekli = bool(normalise) and abs(toplam - 1.0) > 1e-9

    if basis == "mole_fraction":
        kanonik = ({el: v / toplam for el, v in composition.items()}
                   if olcekli else dict(composition))
        if not olcekli:
            return composition, None
        return kanonik, {"declared_basis": basis,
                         "declared": dict(composition),
                         "canonical_mole_fraction": _round6(kanonik),
                         "converted": False,
                         "rescaled": True,
                         "declared_sum": round(toplam, 6)}

    # ---- mass basis: convert before the engine sees it ---------------
    try:
        import native_step
        kutle = native_step.ATOMIC_MASS
    except Exception:                                    # noqa: BLE001
        raise ValueError("cannot convert %s: atomic masses unavailable"
                         % basis)
    eksik = [el for el in composition if el.upper() not in kutle]
    if eksik:
        # Better to refuse than to convert with a guessed mass -- a wrong
        # conversion is a different alloy, silently.
        raise ValueError(
            "cannot convert %s to mole fractions: no atomic mass for %s"
            % (basis, ", ".join(sorted(eksik))))

    mol = {el: (v / toplam) / kutle[el.upper()]
           for el, v in composition.items()}
    mol_toplam = sum(mol.values())
    kanonik = {el: v / mol_toplam for el, v in mol.items()}
    return kanonik, {"declared_basis": basis,
                     "declared": dict(composition),
                     "canonical_mole_fraction": _round6(kanonik),
                     "converted": True,
                     "rescaled": olcekli,
                     "declared_sum": round(toplam, 6)}


def _round6(d):
    return {el: round(v, 6) for el, v in d.items()}


def composition_report(composition, basis=None):
    """State the composition in both bases, and say which one arrived.

    Steel is quoted by weight by convention and this engine conditions on
    mole fractions, and until now the payload said neither. Measured three
    times: a caller sent 0.05 for "1% C", sent 0.003 for "3% C", and the
    independent reviewer read x(C)=0.01 as one weight per cent and
    objected to a result that was correct. The reviewer's objection was
    right about the alloy it had in mind -- 1 wt% is x(C)=0.045, which is
    hypereutectoid -- and that alloy was not the one being computed.

    Nobody involved was being careless. The number had no unit attached.
    """
    ayarlar = POLICY.input.composition.get("basis", {})
    basis = basis or ayarlar.get("default", "mole_fraction")
    if not composition:
        return None
    try:
        import native_step
        kutle = native_step.ATOMIC_MASS
    except Exception:                                    # noqa: BLE001
        return {"basis": basis}

    bilinmeyen = [el for el in composition if el.upper() not in kutle]
    if bilinmeyen:
        # Better to say nothing than to convert with a guessed mass.
        return {"basis": basis, "unconvertible": sorted(bilinmeyen)}

    toplam = sum(composition.values())
    if toplam <= 0:
        return {"basis": basis}
    mol = {el: v / toplam for el, v in composition.items()}
    agirlik = {el: mol[el] * kutle[el.upper()] for el in mol}
    ag_toplam = sum(agirlik.values())
    return {
        "basis": basis,
        "mole_fraction": {el: round(v, 6) for el, v in mol.items()},
        "weight_percent": {el: round(100.0 * v / ag_toplam, 4)
                           for el, v in agirlik.items()},
    }
