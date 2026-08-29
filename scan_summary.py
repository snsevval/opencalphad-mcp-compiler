"""Derived summary of a scan result: where the phase set changes, which
phase dominates where, and where melting starts and finishes.

Why this exists
---------------
A property diagram or isothermal section comes back as a long list of
sampled points -- 215 rows for a 300-2000 K sweep is normal. Every number
in those rows is correct. But the questions people actually ask ("when
does ferrite become dominant?", "where does it start to melt?", "does
delta-ferrite appear?") are not IN any single row: answering them means
comparing consecutive rows across the whole list.

Measured behaviour: a caller reading these results reports single-row
values accurately and derives across-row values badly. Real cases from
the benchmark record -- a delta-ferrite field 24 K wide reported as
absent, a dominance threshold at x=0.19 reported as x=0.26, a phase
dissolution at 660 K reported as 602 K. In each one the evidence was
present in the payload and the derivation was not performed.

So we perform it here and hand over the answer instead of the raw
material. This module runs no calculation of its own: it is a pure
function of the points already computed, costs no engine call, and adds
well under a kilobyte to a payload that is tens of kilobytes.

What it cannot do
-----------------
It only sees the positions that were sampled. A phase field narrower
than the sampling spacing is invisible here just as it is in the raw
points. That is what the "n_points" count and the "boundary_between"
brackets are for: a region seen at a single position, or a boundary
bracketed by a wide interval, is reported as such rather than as a
precise fact. Under-sampled regions are also collected separately under
"under_sampled" so they cannot be skimmed past.
"""

# A phase below this fraction is treated as absent. STEP and the
# single-point path disagree in the fifth decimal on trace phases, and a
# 1e-6 sliver flickering in and out of the list would otherwise produce a
# transition at every other point.
def _settings():
    """Tolerances come from settings/output.toml, where each sits next to
    the measurement that produced it. Falls back to the values below if
    the settings cannot be read: a missing file must not stop a
    calculation, and these are the numbers the file states anyway."""
    try:
        import settings_engine
        return settings_engine.derive_settings()
    except Exception:                                    # noqa: BLE001
        return {"presence_tolerance": 1e-4, "dominance_threshold": 0.5}


PRESENCE_TOLERANCE = _settings()["presence_tolerance"]

# A phase is "dominant" when it holds more than half of the system. This
# is the threshold the questions themselves use ("when does ferrite
# become dominant") -- not a modelling choice.
DOMINANCE_THRESHOLD = _settings()["dominance_threshold"]


def _present_phases(amounts):
    """The phases actually there, as a sorted tuple. Sorted so that two
    points with the same phases compare equal regardless of dict order."""
    return tuple(sorted(
        name for name, value in (amounts or {}).items()
        if value is not None and value > PRESENCE_TOLERANCE
    ))


def _dominant_phase(amounts):
    """The single phase holding more than half the system, or None when
    no phase does (a genuinely balanced two-phase field)."""
    best_name, best_value = None, 0.0
    for name, value in (amounts or {}).items():
        if value is not None and value > best_value:
            best_name, best_value = name, value
    return best_name if best_value > DOMINANCE_THRESHOLD else None


def _usable(points, axis_key):
    """Points that carry a phase assemblage, sorted along the axis.

    Points the engine could not solve arrive carrying an "error" instead
    of fractions. They are dropped here rather than treated as "no
    phases present", which would invent a transition on either side of
    every failed point.
    """
    rows = []
    for point in points or []:
        if "error" in point:
            continue
        position = point.get(axis_key)
        amounts = point.get("phase_molar_amounts")
        if position is None or not amounts:
            continue
        rows.append((position, amounts))
    rows.sort(key=lambda row: row[0])
    return rows


def _regions(rows):
    """Contiguous runs of the same phase assemblage."""
    regions = []
    for position, amounts in rows:
        phases = _present_phases(amounts)
        if regions and regions[-1]["_phases"] == phases:
            regions[-1]["to"] = position
            regions[-1]["n_points"] += 1
        else:
            regions.append({
                "_phases": phases,
                "phases": list(phases),
                "from": position,
                "to": position,
                "n_points": 1,
            })
    for region in regions:
        del region["_phases"]
    return regions


def _transitions(rows):
    """Every place the phase assemblage changes between two consecutive
    sampled positions.

    The boundary is not AT either position -- it is somewhere between
    them, which is why "boundary_between" carries both and "bracket"
    carries how wide that uncertainty is. A wide bracket is a signal
    that the scan was too coarse there, not a precise result.
    """
    transitions = []
    for (left_pos, left_amounts), (right_pos, right_amounts) in zip(rows, rows[1:]):
        left = _present_phases(left_amounts)
        right = _present_phases(right_amounts)
        if left == right:
            continue
        transitions.append({
            "boundary_between": [left_pos, right_pos],
            # Rounded because it is a derived width, not a computed
            # position: 17.320000000000164 reads as false precision.
            "bracket": round(right_pos - left_pos, 6),
            "from_phases": list(left),
            "to_phases": list(right),
            "appeared": sorted(set(right) - set(left)),
            "disappeared": sorted(set(left) - set(right)),
        })
    return transitions


def _dominant_regions(rows):
    """Contiguous runs over which the same phase holds the majority.

    Stretches where no phase passes half are reported with
    "phase": null rather than dropped, so a caller can see that the
    balanced region exists and where it sits.
    """
    regions = []
    for index, (position, amounts) in enumerate(rows):
        phase = _dominant_phase(amounts)
        if regions and regions[-1]["phase"] == phase:
            regions[-1]["to"] = position
            regions[-1]["n_points"] += 1
        else:
            regions.append({
                "phase": phase,
                "from": position,
                # "from" is the first position where this phase was
                # OBSERVED to hold the majority; the crossover itself is
                # between that position and the one before it. Reporting
                # only "from" invites reading a sampled position as an
                # exact threshold -- the same false precision the
                # transition brackets exist to prevent.
                "from_boundary_between": (
                    [rows[index - 1][0], position] if index else None
                ),
                "to": position,
                "n_points": 1,
            })
    return regions


def _liquid_names(rows):
    """Phase names that are a liquid. Databases spell it LIQUID, LIQUID#1
    or LIQUID_AUTO#2 depending on the output path and on whether a second
    composition set was created."""
    names = set()
    for _, amounts in rows:
        for name in amounts:
            if name.upper().startswith("LIQUID"):
                names.add(name)
    return names


def _melting(rows):
    """Where liquid first appears and where the last solid disappears.

    Reported as observed positions plus the bracket each boundary sits
    in, because these two numbers get mislabelled often: the position
    where melting FINISHES is not the solidus, and a scan whose spacing
    is wider than the two-phase field can only bound them.
    """
    liquids = _liquid_names(rows)
    if not liquids:
        return None

    def liquid_fraction(amounts):
        return sum(value for name, value in amounts.items()
                   if name in liquids and value is not None)

    first_liquid = None
    fully_liquid = None
    for index, (position, amounts) in enumerate(rows):
        share = liquid_fraction(amounts)
        others = _present_phases({k: v for k, v in amounts.items()
                                  if k not in liquids})
        if first_liquid is None and share > PRESENCE_TOLERANCE:
            first_liquid = {
                "observed_at": position,
                "boundary_between": (
                    [rows[index - 1][0], position] if index else None
                ),
            }
        if fully_liquid is None and share > PRESENCE_TOLERANCE and not others:
            fully_liquid = {
                "observed_at": position,
                "boundary_between": (
                    [rows[index - 1][0], position] if index else None
                ),
            }
    if first_liquid is None:
        return None

    melting = {"first_liquid": first_liquid, "fully_liquid": fully_liquid}
    if fully_liquid is not None:
        low = (first_liquid["boundary_between"] or [first_liquid["observed_at"]])[0]
        melting["melting_range_outer"] = [low, fully_liquid["observed_at"]]
    return melting


def summarize(points, axis_key="temperature_K"):
    """Turn a list of scan points into the answers a caller would
    otherwise have to derive by comparing rows.

    `points` is the same list the tool already returns; each entry needs
    `axis_key` and `phase_molar_amounts`. Points carrying an "error" are
    counted and skipped.

    Returns None when there is nothing to summarize (fewer than two
    solved points), so the caller can leave the field out rather than
    attach an empty shell.
    """
    rows = _usable(points, axis_key)
    skipped = len(points or []) - len(rows)
    if len(rows) < 2:
        return None

    regions = _regions(rows)
    transitions = _transitions(rows)
    spacings = sorted(right - left for left, right in
                      zip([r[0] for r in rows], [r[0] for r in rows[1:]]))
    median_spacing = spacings[len(spacings) // 2] if spacings else None

    summary = {
        "axis": axis_key,
        "range": [rows[0][0], rows[-1][0]],
        "points_used": len(rows),
        "points_skipped": skipped,
        "median_spacing": (None if median_spacing is None
                           else round(median_spacing, 6)),
        "phases_seen": sorted({name for _, amounts in rows
                               for name in _present_phases(amounts)}),
        "phase_regions": regions,
        "phase_transitions": transitions,
        "dominant_phase_regions": _dominant_regions(rows),
        "under_sampled": [
            {"phases": region["phases"], "at": region["from"]}
            for region in regions if region["n_points"] == 1
        ],
        "note": (
            "Derived from the points in this same result, not from a "
            "separate calculation. Each boundary lies somewhere INSIDE "
            "its 'boundary_between' pair, not at either end. Anything "
            "listed under 'under_sampled' was seen at one position only, "
            "so its extent is unknown -- report it as present but "
            "poorly resolved rather than describing its width."
        ),
    }

    melting = _melting(rows)
    if melting:
        summary["melting"] = melting
    return summary
