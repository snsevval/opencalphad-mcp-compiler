"""Runs a single calculate_equilibrium call in its own process.

The underlying Fortran engine can segfault on pathological/non-converging
inputs (observed during testing), which a Python try/except cannot catch.
Isolating each calculation in a subprocess means a crash only fails that one
tool call instead of taking down the whole MCP server.

Reads a single JSON object from stdin with keys: database,
elements_composition, temperature_K, pressure_Pa (optional),
suspended_phases (optional). Writes the JSON result to the output file
given as argv[1] on success. The underlying Fortran engine prints its own
diagnostics straight to stdout, so the result is written to a dedicated
file instead of stdout to avoid interleaving with that output.
On failure, writes a JSON {"error": "..."} to the output file and exits
with code 1.
"""
import json
import sys

import oc_service


def main():
    out_path = sys.argv[1]
    args = json.load(sys.stdin)
    try:
        result = oc_service.calculate_equilibrium(
            database=args["database"],
            elements_composition=args["elements_composition"],
            temperature_K=args["temperature_K"],
            pressure_Pa=args.get("pressure_Pa", 1e5),
            suspended_phases=args.get("suspended_phases"),
        )
    except oc_service.EquilibriumError as exc:
        with open(out_path, "w") as f:
            json.dump({"error": str(exc)}, f)
        sys.exit(1)
    with open(out_path, "w") as f:
        json.dump(result, f)


if __name__ == "__main__":
    main()
