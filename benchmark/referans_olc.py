# -*- coding: utf-8 -*-
"""Yirmi kosumu gercek MCP yolundan olcer, ham yuku diske yazar."""
import asyncio
import json
import os
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "benchmark"))

from mcp import ClientSession, StdioServerParameters      # noqa: E402
from mcp.client.stdio import stdio_client                 # noqa: E402
import referans as R                                      # noqa: E402

CIKTI = os.path.join(ROOT, "referans_olcum20.json")


def _metin(s):
    for b in s.content:
        if b.type == "text":
            return b.text
    return ""


async def main():
    env = dict(os.environ)
    env["OC_SEMANTIC_CHECK"] = "0"
    env["OC_INTERACTIVE_WINDOW"] = "0"
    params = StdioServerParameters(
        command=os.path.join(ROOT, "run_server.sh"), args=[], env=env)
    devnull = open(os.devnull, "w")
    yukler = {}
    async with stdio_client(params, errlog=devnull) as (read, write):
        async with ClientSession(read, write) as session:
            await asyncio.wait_for(session.initialize(), timeout=120)
            for ad, (arac, args) in R.KOSUMLAR.items():
                t = time.time()
                try:
                    ham = await asyncio.wait_for(
                        session.call_tool(arac, arguments=args), timeout=300)
                    y = json.loads(_metin(ham))
                except Exception as exc:
                    y = {"error": "%s: %s" % (type(exc).__name__, exc)}
                ozet = y.get("scan_summary") or {}
                erime = (ozet.get("melting") or {}).get("fully_liquid") or {}
                print("  %-18s %6.1f s  %-24s %s"
                      % (ad, time.time() - t,
                         y.get("backend_used", "-") if "error" not in y
                         else "HATA",
                         ("HATA: " + str(y["error"])[:70]) if "error" in y
                         else "tam sivi %s  fazlar %s"
                              % (erime.get("observed_at"),
                                 ozet.get("phases_seen"))))
                sys.stdout.flush()
                yukler[ad] = y
    with open(CIKTI, "w") as f:
        json.dump(yukler, f, indent=1)
    print("\n%d kosum -> %s" % (len(yukler), CIKTI))


asyncio.run(main())
