"""Kiyaslama kosucusu: vakalari GERCEK MCP protokolu uzerinden calistirir.

Ic fonksiyonlari cagirmak yerine stdio uzerinden run_server.sh'i konusturur
-- yani test edilen sey kullanicinin gordugu yol olur, ic fonksiyonlarin
"calisiyor gorunmesi" degil. verification/executor.py ile ayni gerekce.

    python3 benchmark/run.py                # butun vakalar
    python3 benchmark/run.py DOGRU_RED      # tek kategori
    python3 benchmark/run.py red_bef_demir  # tek vaka

Cikis kodu: kalan vaka varsa 1, hepsi gectiyse 0.
"""
import asyncio
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, HERE)

from mcp import ClientSession, StdioServerParameters  # noqa: E402
from mcp.client.stdio import stdio_client  # noqa: E402

import cases as case_registry  # noqa: E402

RUN_SERVER_SH = os.path.join(ROOT, "run_server.sh")


def _first_text(result):
    for block in result.content:
        if block.type == "text":
            return block.text
    return ""


def judge(case, payload):
    """Vakayi degerlendirir. (gecti, aciklama) dondurur."""
    expected = case["expected"]

    if expected.get("rejected"):
        # Bir hesap sonucu donduyse vaka kalmistir: reddedilmesi gereken
        # istek calistirilmis demektir.
        if "gibbs_energy_J" in payload or "points" in payload:
            return False, "reddedilmedi -- hesap sonucu dondu"

        blob = json.dumps(payload, ensure_ascii=False)
        stage = payload.get("stage")

        want_stage = expected.get("stage", "PREFLIGHT")
        if want_stage is None:
            # Reddedilmeli ama PREFLIGHT'ta DEGIL -- asamanin kendisi olcum.
            if stage == "PREFLIGHT":
                return False, "PREFLIGHT'ta reddedildi, oysa gecmesi bekleniyordu"
        elif stage != want_stage:
            return False, f"stage={stage!r}, beklenen {want_stage!r}"

        missing = [s for s in expected.get("reason_contains", []) if s not in blob]
        if missing:
            return False, f"redde su metin(ler) gecmiyor: {missing}"
        return True, f"reddedildi ({stage})"

    return True, "(deger karsilastirmasi henuz yazilmadi)"


async def run_all(selected):
    params = StdioServerParameters(command=RUN_SERVER_SH, args=[])
    devnull = open(os.devnull, "w")
    results = []
    async with stdio_client(params, errlog=devnull) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=120)
            for case in selected:
                started = time.time()
                try:
                    raw = await asyncio.wait_for(
                        session.call_tool(case["tool"],
                                          arguments=case["arguments"]),
                        timeout=180,
                    )
                    payload = json.loads(_first_text(raw))
                except Exception as exc:
                    payload = {"error": f"{type(exc).__name__}: {exc}"}
                passed, note = judge(case, payload)
                results.append({
                    "id": case["id"],
                    "zorluk": case["zorluk"],
                    "passed": passed,
                    "note": note,
                    "seconds": round(time.time() - started, 2),
                })
    return results


def main(argv):
    wanted = argv[1] if len(argv) > 1 else None
    if wanted in (None, "hepsi"):
        selected = case_registry.CASES
    elif hasattr(case_registry, wanted):
        selected = getattr(case_registry, wanted)
    else:
        selected = [c for c in case_registry.CASES if c["id"] == wanted]
    if not selected:
        print(f"vaka bulunamadi: {wanted}")
        return 2

    results = asyncio.run(run_all(selected))

    width = max(len(r["id"]) for r in results)
    for r in results:
        mark = "GECTI" if r["passed"] else "KALDI"
        print(f"  {mark:5}  {r['id']:<{width}}  {r['zorluk']:<5} "
              f"{r['seconds']:>6.2f}s  {r['note']}")

    kaldi = [r for r in results if not r["passed"]]
    print()
    print(f"{len(results) - len(kaldi)}/{len(results)} gecti")
    for zorluk in ("kolay", "orta", "zor"):
        grup = [r for r in results if r["zorluk"] == zorluk]
        if grup:
            ok = sum(1 for r in grup if r["passed"])
            print(f"  {zorluk:<6} {ok}/{len(grup)}")
    return 1 if kaldi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
