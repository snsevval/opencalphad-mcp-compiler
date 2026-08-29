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

ALL_OPERATIONS = set(INPUT["accept"]["operations"])


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
    total = sum((request.get("composition") or {}).values())
    if total <= 0:
        return []          # already reported by sum_positive; not twice
    if rule["low"] <= total <= rule["high"]:
        return []
    return [rule["message"].format(total=format(total, ".4g"))]


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
    kurallar = INPUT["reject"] + INPUT["route"]

    # Common rules first, then the operation's own -- and a missing or
    # unreadable database stops only the COMMON ones.
    #
    # That scope matters and was got wrong first time round: the original
    # returns early from its shared helper, but the per-operation checks
    # that follow the helper still run. A request naming a database that
    # does not exist AND a negative temperature reports both. Fuzzing
    # caught it; the hand-written cases never combined the two.
    ortak = [r for r in kurallar if r["applies"] == "*"]
    kendine_ozel = [r for r in kurallar
                    if r["applies"] != "*" and _applies(r, operation)]

    for rule in ortak:
        predicate = PREDICATES.get(rule["check"])
        if predicate is None:
            continue
        found = predicate(rule, request, ctx)
        problems.extend(found)
        if found and rule["id"] in ("database-exists", "database-readable"):
            break

    for rule in kendine_ozel:
        predicate = PREDICATES.get(rule["check"])
        if predicate is None:
            continue
        problems.extend(predicate(rule, request, ctx))

    return problems


def route_for(operation, problems):
    """Alternatives for a rejection that is answerable elsewhere.

    Only for the "wrong tool" class. An impossible request gets nothing:
    inventing a route would push the caller toward a calculation nobody
    asked for, which is the failure the stop rule exists to prevent.
    """
    blob = " ".join(problems)
    notes = []
    for rule in INPUT["route"]:
        if not _applies(rule, operation):
            continue
        marker = rule["message"].split("{")[0].strip()[:40]
        if marker and marker in blob and rule.get("route_note"):
            notes.append(rule["route_note"].strip())
    return notes

def stop_rule_block(indent="    "):
    """The stop rule as one block, ready to drop into a tool docstring.

    Assembled from settings/output.toml. It used to be six paragraphs
    typed out by hand in six docstrings, which is how a correction to it
    turned into six separate edits.
    """
    rule = OUTPUT["stop_rule"]
    lines = ["PREFLIGHT REJECTION — STOP RULE",
             "If the result has stage=\"PREFLIGHT\", the request was refused",
             "before any calculation ran. Two cases, and they call for",
             "opposite actions:",
             ""]
    for baslik, anahtar in (
        ("(a) The rejection carries an \"alternative\" field.", "on_route_present"),
        ("(b) No \"alternative\" field.", "on_no_route"),
        ("(c) stage=\"PRECONDITION\" is different again.", "on_precondition"),
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
    for entry in OUTPUT.get("note", []):
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
    d = OUTPUT["derive"]
    return {
        "presence_tolerance": d["presence_tolerance"],
        "dominance_threshold": d["dominance_threshold"],
        "enabled": list(d["enabled"]),
    }


def precondition(check_id, **fields):
    """The message for a precondition that costs a calculation to test."""
    for entry in INPUT.get("precondition", []):
        if entry.get("id") == check_id:
            return entry["message"].strip().format(**fields)
    return None


def coverage(points, axis_key, requested_n, span_low, span_high):
    """How much of the requested scan actually came back.

    Every other check asks whether the numbers that arrived are sound.
    None of them asks how many never did -- and one point is a perfectly
    well-formed result. Measured: a twenty-position request returned a
    single position, passed every layer, and carried no warning at all.

    Returns None when there is nothing to compare against.
    """
    if not points or requested_n in (None, 0) or span_low is None or span_high is None:
        return None
    solved = [p for p in points if "error" not in p and p.get(axis_key) is not None]
    if not solved:
        return None
    span = abs(span_high - span_low)
    if span <= 0:
        return None
    lo = min(p[axis_key] for p in solved)
    hi = max(p[axis_key] for p in solved)
    covered = abs(hi - lo) / span
    return {
        "requested_positions": requested_n,
        "solved_positions": len(solved),
        "requested_range": [span_low, span_high],
        "covered_range": [lo, hi],
        "covered_fraction": round(min(covered, 1.0), 4),
    }


def coverage_note(cov, minimum_fraction=0.9):
    """The warning text when a scan came back short, or None when it did
    not. `planned` in the settings suppresses it, as for any note."""
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
