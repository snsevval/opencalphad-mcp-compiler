"""Fixed registry of test cases for the Plan -> Execute -> Verify -> Fix ->
Re-verify loop (see the plan file, Faz 9).

Every case here reproduces a scenario this project already worked through
by hand this session (steel1, AlFe-4SLBF, steel7, alni-4slx, agcu) -- this
turns that ad-hoc, one-off manual testing into something repeatable. Where
we established a precise reference value (single-point calculate_equilibrium
cases), "expected" carries it with a tolerance for exact Layer-A (code)
verification. Where the case is a property_diagram (STEP + gap-fill,
inherently a larger dataset with no single reference number), "expected"
is left mostly structural -- Layer A only checks the response is
well-formed, and Layer B (an independent model reviewer) judges whether
the reported phase transitions look physically plausible.

Add new cases here as the project grows; PLAN currently just walks this
list in order (see the plan file's Faz 9: model-suggested planning is a
deliberately deferred v2).
"""

CASES = [
    {
        "id": "steel1_FeC_1000K",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "temperature_K": 1000,
        },
        "expected": {
            "gibbs_energy_J": {"value": -41981.578, "tolerance": 1.0},
            "phase_molar_amounts": {
                "BCC_A2": {"value": 0.9907, "tolerance": 0.01},
                "GRAPHITE": {"value": 0.0093, "tolerance": 0.01},
            },
            "backend_used": "ocasi",
        },
    },
    {
        "id": "steel1_FeC_1200K",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel1.TDB",
            "elements_composition": {"FE": 0.99, "C": 0.01},
            "temperature_K": 1200,
        },
        "expected": {
            "gibbs_energy_J": {"value": -56563.789, "tolerance": 1.0},
            "phase_molar_amounts": {
                "FCC_A1": {"value": 1.0, "tolerance": 0.01},
            },
            # OCASI is known not to converge cold-start at this point (see
            # the plan file, Faz 4/7) -- the native fallback is expected,
            # not a failure. If this ever flips to "ocasi", that's also
            # fine (means OCASI itself improved); the case only fails if
            # neither backend produces the right numbers.
        },
    },
    {
        "id": "alfe4slbf_Al20Fe80_1000K",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "AlFe-4SLBF.TDB",
            "elements_composition": {"AL": 0.2, "FE": 0.8},
            "temperature_K": 1000,
        },
        "expected": {
            "gibbs_energy_J": {"value": -59870.5, "tolerance": 5.0},
        },
    },
    {
        "id": "steel7_6element_1173K",
        "tool": "calculate_equilibrium",
        "arguments": {
            "database": "steel7.TDB",
            "elements_composition": {
                "C": 0.04, "CR": 0.06, "MO": 0.05,
                "SI": 0.003, "V": 0.01, "FE": 0.837,
            },
            "temperature_K": 1173,
        },
        "expected": {
            # No precise pre-established reference for this exact point --
            # structural checks only (converges, phases sum to ~1). Layer B
            # judges plausibility (multi-carbide low-alloy steel at ~900C
            # should show BCC/FCC + carbides, not something wildly off).
        },
    },
    {
        "id": "alni4slx_Al75Ni25_800_1700K",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "alni-4slx.TDB",
            "elements_composition": {"AL": 0.75, "NI": 0.25},
            "temperature_min_K": 800,
            "temperature_max_K": 1700,
            "n_points": 30,
        },
        "expected": {
            "structural_only": True,
            "note": (
                "Al3Ni peritectic ~1112K, liquidus ~1388K (see plan file, "
                "earlier session notes) -- Layer B checks these appear in "
                "the right ballpark, Layer A just checks the response is "
                "well-formed and every point's phase fractions sum to 1."
            ),
        },
    },
    {
        "id": "agcu_Ag60Cu40_800_1400K",
        "tool": "calculate_property_diagram",
        "arguments": {
            "database": "agcu.TDB",
            "elements_composition": {"AG": 0.6, "CU": 0.4},
            "temperature_min_K": 800,
            "temperature_max_K": 1400,
            "n_points": 50,
        },
        "expected": {
            "structural_only": True,
            "note": (
                "FCC miscibility gap 800-~1056K, sharp liquidus ~1056-1061K "
                "(confirmed this session via GUI cross-check, see plan "
                "file Faz 8), then pure LIQUID to 1400K."
            ),
        },
    },
]
