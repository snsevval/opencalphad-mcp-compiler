"""Is the configured Layer B reviewer usable?

Reachability is not the question -- semantic_check already reports that as
`available`. The question is whether the reviewer, once reached, produces a
readable verdict AND the right one. A model that approves everything is as
useless as one that cannot be reached, and only a case it should reject
tells the two apart.

So: the same real result twice, once untouched and once with its phase
fractions broken past any tolerance. Pass means BASARILI on the first and
BASARISIZ on the second.

    python3 probe_reviewer.py                  # the configured chain
    python3 probe_reviewer.py <model-id> ...   # specific candidates
"""
import copy
import sys
import time

import semantic_check

REQUEST = {
    "database": "steel1.TDB",
    "elements_composition": {"FE": 0.99, "C": 0.01},
    "temperature_K": 1000,
    "pressure_Pa": 100000.0,
}

GOOD = {
    "gibbs_energy_J": -41981.57771667154,
    "chemical_potentials_J_per_mol": {"FE": -42277.77, "C": -12658.35},
    "phase_molar_amounts": {"BCC_A2": 0.9907152789, "GRAPHITE": 0.0092847211},
    "phase_element_composition": {
        "BCC_A2": {"FE": 0.999278017694, "C": 0.000721982306},
        "GRAPHITE": {"C": 1.0, "FE": 0.0},
    },
    "backend_used": "ocasi",
}


def broken():
    """The same result with a defect no valid calculation can produce:
    fractions summing to 1.45, and carbon leaving the graphite. Layer A
    would catch the sum on its own -- the point here is whether the
    reviewer, asked for a physical judgement, notices too."""
    bad = copy.deepcopy(GOOD)
    bad["phase_molar_amounts"] = {"BCC_A2": 0.99, "GRAPHITE": 0.46}
    bad["phase_element_composition"]["GRAPHITE"] = {"C": 0.42, "FE": 0.58}
    return bad


def ask(model, result, label):
    print(f"  {label:<10}", end="", flush=True)
    started = time.time()
    # review() picks from the module-level chain; narrow it to the one
    # candidate so a fallback cannot answer in its place.
    saved, semantic_check.MODELS = semantic_check.MODELS, [model]
    try:
        review = semantic_check.review(REQUEST, result, timeout_s=90,
                                       retries=(0,))
    finally:
        semantic_check.MODELS = saved
    took = time.time() - started
    if not review.get("available"):
        print(f"ULASILAMADI  ({took:.0f}s)  {review.get('reason','')[:70]}")
        return None
    verdict = review.get("passed")
    shown = {True: "BASARILI", False: "BASARISIZ", None: "OKUNAMADI"}[verdict]
    print(f"{shown:<12} ({took:.0f}s)")
    if verdict is None:
        print(f"             {review.get('reason','')[:150]}")
    return verdict


def main(models):
    print(f"vaka: steel1 Fe-C 1000K, G={GOOD['gibbs_energy_J']:.3f}\n")
    usable = []
    for model in models:
        print(model)
        ok = ask(model, GOOD, "dogru:")
        bad = ask(model, broken(), "bozuk:")
        if ok is True and bad is False:
            print("  -> KULLANILABILIR\n")
            usable.append(model)
        elif ok is True and bad is True:
            print("  -> her seye evet diyor, hakem degil\n")
        else:
            print("  -> kullanilamaz\n")
    print("kullanilabilir:", usable or "(yok)")
    return 0 if usable else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:] or semantic_check.MODELS))
