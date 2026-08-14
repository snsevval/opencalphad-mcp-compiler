"""Ablation isci surecinin duzeltilmis halini tek vakada dogrular."""
import json
import sys

sys.path.insert(0, "/root/projects/oc-mcp")
import ablation_run as ar  # noqa: E402

case3 = next(c for c in ar.CASES if c["no"] == 3)
case11 = next(c for c in ar.CASES if c["no"] == 11)

for mod, case in (("bare", case3), ("cascade", case3), ("cascade", case11)):
    r = ar.calistir(mod, case, timeout_s=180)
    print(f"--- {mod} / vaka {case['no']}")
    print("   ", json.dumps(
        {k: v for k, v in r.items()
         if k in ("outcome", "backend_used", "gibbs_energy_J", "n_points",
                  "n_failed_points", "error", "runtime_s", "stderr_tail",
                  "returncode")},
        ensure_ascii=False))
