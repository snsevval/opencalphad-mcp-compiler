#!/usr/bin/env python3
"""RECEIVED -> PREFLIGHT_VALIDATION -> EXECUTING -> VERIFYING ->
(PASSED | FIX -> RE-VERIFYING) -> COMPLETED orchestrator
(see the plan file, Faz 9 + Faz 10).

Standalone script: `python3 verification/run_loop.py`. No agent CLI /
Nemotron session required to run it -- it drives the real MCP server
(run_server.sh) exactly the way an AI client would, and (for cases
without a precise numeric reference) asks an independent model to judge
physical plausibility.

PLAN: walks verification/cases.py's fixed list in order (v1 -- a
model-suggested planner that targets under-tested or previously-failed
combinations is a deliberately deferred v2, see the plan file).

PREFLIGHT_VALIDATION (Faz 10): every case is checked by preflight.py
BEFORE OCASI/native is ever touched -- element existence, composition
range, temperature ordering, pressure sign. A case that fails here is
FAILED_SAFE immediately; EXECUTE is never attempted and FIX never
retries a request that was invalid to begin with (retrying garbage
doesn't make it valid).

FIX: intentionally narrow. This project's own fallback layers (OCASI ->
native single-point -> native STEP -> gap-fill -> matplotlib) already do
the real recovery work inside a single EXECUTE call (this was a
deliberate, discussed decision -- see the plan file's Faz 10 "Tartışmalı
karar": an external suggestion to drop the native fallback and treat
OCASI's own failure as final was rejected, because it would re-report
"unsolvable" on cases -- e.g. steel1 Fe-C at 1200K -- that this project
spent real effort solving and cross-checked against the GUI's own
output). FIX here only retries EXECUTE once for cases where the call
itself failed or VERIFY rejected the result, on the chance it was
transient. It never edits code or auto-patches a genuine logic bug --
those get written to the report for a human to look at, consistent with
how every fix this session was made (diagnose, then ask before changing
code).
"""
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))


def _load_dotenv(path):
    """Minimal .env loader (no extra dependency): sets os.environ from
    KEY=VALUE lines, without overwriting anything already set in the real
    environment. The .env file itself is git-ignored -- see .gitignore --
    so a secret placed there never gets committed/pushed."""
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            if key and key not in os.environ:
                os.environ[key] = value.strip()


_load_dotenv(os.path.join(HERE, "..", ".env"))

from cases import CASES  # noqa: E402
import executor  # noqa: E402
import validator  # noqa: E402
import preflight  # noqa: E402


def run_preflight(case):
    """PREFLIGHT_VALIDATION stage. Returns a list of problem strings
    (empty means the request is valid)."""
    args = case["arguments"]
    if case["tool"] == "calculate_equilibrium":
        return preflight.check_equilibrium_request(
            args["database"], args["elements_composition"],
            args["temperature_K"], args.get("pressure_Pa", 1e5),
        )
    if case["tool"] == "calculate_property_diagram":
        return preflight.check_property_diagram_request(
            args["database"], args["elements_composition"],
            args["temperature_min_K"], args["temperature_max_K"],
            args.get("pressure_Pa", 1e5),
        )
    return [f"Unknown tool '{case['tool']}', PREFLIGHT has no checks for it."]


def run_one_case(case):
    """PREFLIGHT_VALIDATION -> EXECUTING -> VERIFYING -> (FIX ->
    RE-VERIFYING if needed). Returns a result dict for the report."""
    record = {"id": case["id"], "tool": case["tool"], "stages": [], "attempts": []}

    problems = run_preflight(case)
    if problems:
        record["stages"].append("PREFLIGHT_VALIDATION: FAILED_SAFE")
        record["preflight_problems"] = problems
        record["final_status"] = "BASARISIZ"
        return record
    record["stages"].append("PREFLIGHT_VALIDATION: ok")

    def attempt(label):
        entry = {"label": label}
        try:
            result = executor.execute(case)
        except executor.ExecutionError as exc:
            entry["execute_error"] = str(exc)
            entry["verify"] = None
            record["attempts"].append(entry)
            return None, False
        entry["raw_result_summary"] = {
            k: result.get(k) for k in ("backend_used", "gibbs_energy_J", "error")
            if k in result
        }
        v = validator.verify(case, result)
        entry["verify"] = {"passed": v.passed, "layer": v.layer, "reason": v.reason}
        record["attempts"].append(entry)
        return result, v.passed

    record["stages"].append("EXECUTING")
    result, passed = attempt("initial")
    record["stages"].append("VERIFYING: " + ("passed" if passed else "failed"))

    if not passed:
        print(f"  [{case['id']}] VERIFYING failed -> FIX (single retry)...")
        record["stages"].append("FIX: retrying")
        result, passed = attempt("fix_retry")
        record["stages"].append("RE-VERIFYING: " + ("passed" if passed else "failed"))

    record["final_status"] = "BASARILI" if passed else "BASARISIZ"
    return record


def main():
    print(f"RECEIVED {len(CASES)} case(s) -> PREFLIGHT -> EXECUTE -> VERIFY -> [FIX -> RE-VERIFY]\n")
    if not validator.NVIDIA_API_KEY:
        print(
            "Note: NVIDIA_API_KEY not set -- Layer B (independent model review) "
            "will be skipped for structural-only cases; only Layer A (code-based) "
            "checks will run for those.\n"
        )

    report = {"started_at": time.strftime("%Y-%m-%dT%H:%M:%S"), "cases": []}
    pass_count = 0

    for case in CASES:
        print(f"[{case['id']}] ...")
        record = run_one_case(case)
        report["cases"].append(record)
        status = record["final_status"]
        for stage in record["stages"]:
            print(f"  {stage}")
        print(f"  -> COMPLETED: {status}\n")
        if status == "BASARILI":
            pass_count += 1

    report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    report["summary"] = {
        "total": len(CASES),
        "passed": pass_count,
        "failed": len(CASES) - pass_count,
    }

    results_dir = os.path.join(HERE, "results")
    os.makedirs(results_dir, exist_ok=True)
    out_path = os.path.join(results_dir, time.strftime("%Y%m%d_%H%M%S") + ".json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"SONUC: {pass_count}/{len(CASES)} basarili. Rapor: {out_path}")
    return 0 if pass_count == len(CASES) else 1


if __name__ == "__main__":
    sys.exit(main())
