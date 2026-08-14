"""On dakikalik sinama: Nemotron, OpenAI bicimli arac semasi verildiginde
gercekten tool_call uretiyor mu?

Kendi ReAct surucumuzu yazmanin on kosulu bu. Tutarsa geri kalani mekanik
is; tutmazsa istem/sema bicimini ayarlamak gerekir ve maliyet degisir.

Hicbir seye dokunmaz: sadece API'ye tek bir istek atar, cevabi inceler.
"""
import json
import os
import sys
import urllib.error
import urllib.request

ENV_PATH = "/root/projects/oc-mcp/.env"
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"

# server.py'nin gercekten bildirdigi araclardan biri; sema ayni bicimde.
TOOLS = [{
    "type": "function",
    "function": {
        "name": "inspect_database",
        "description": (
            "Return the elements and phase names declared in a thermodynamic "
            "database file. Use this before composing a calculation request "
            "so the composition only names elements the database actually has."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "database": {
                    "type": "string",
                    "description": "Database file name, e.g. 'steel1.TDB'.",
                },
            },
            "required": ["database"],
        },
    },
}]

SORU = "steel1.TDB veritabaninda hangi elementler var?"


def load_key():
    key = os.environ.get("NVIDIA_API_KEY", "")
    if key:
        return key
    if os.path.isfile(ENV_PATH):
        with open(ENV_PATH) as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("NVIDIA_API_KEY"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def main():
    key = load_key()
    if not key:
        print("HATA: NVIDIA_API_KEY yok")
        return 1

    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": SORU}],
        "tools": TOOLS,
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 400,
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )

    print("=" * 78)
    print("SINAMA — Nemotron arac cagirir mi?")
    print("=" * 78)
    print(f"model : {MODEL}")
    print(f"soru  : {SORU}")
    print(f"arac  : inspect_database(database: string)")
    print()

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")[:400]
        print(f"HTTP {exc.code}\n{body}")
        return 1
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}")
        return 1

    mesaj = (data.get("choices") or [{}])[0].get("message", {}) or {}
    tool_calls = mesaj.get("tool_calls") or []
    icerik = (mesaj.get("content") or "").strip()

    if tool_calls:
        print(">>> ARAC CAGRISI URETTI\n")
        for tc in tool_calls:
            fn = tc.get("function", {}) or {}
            print(f"  id        : {tc.get('id')}")
            print(f"  fonksiyon : {fn.get('name')}")
            print(f"  argumanlar: {fn.get('arguments')}")
            try:
                args = json.loads(fn.get("arguments") or "{}")
                print(f"  ayristi   : {args}")
                dogru_ad = fn.get("name") == "inspect_database"
                dogru_db = "steel1" in str(args.get("database", "")).lower()
                print(f"\n  dogru arac : {dogru_ad}")
                print(f"  dogru db   : {dogru_db}")
                if dogru_ad and dogru_db:
                    print("\n  SONUC: TAM ISABET — surucu yazilabilir")
                    return 0
                print("\n  SONUC: arac cagirdi ama argumanlar beklendigi gibi degil")
                return 0
            except json.JSONDecodeError as exc:
                print(f"  argumanlar JSON degil: {exc}")
                return 1

    print(">>> ARAC CAGIRMADI, duz metin dondu\n")
    print(f"  icerik: {icerik[:600]}")
    print("\n  SONUC: sema/istem bicimi ayarlanmasi gerekiyor")
    return 1


if __name__ == "__main__":
    sys.exit(main())
