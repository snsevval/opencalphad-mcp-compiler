"""NVIDIA kapasite yoklamasi.

Amac: OpenClaw'in verdigi "ResourceExhausted: Worker local total request
limit reached (33/32)" hatasinin kaynagini belirlemek.

  - NVIDIA API'si nemotron-3-ultra'ya SU AN yanit veriyorsa
    -> sinir NVIDIA'da DEGIL, OpenClaw istemcisinde.
  - NVIDIA da reddediyorsa
    -> sinir gercekten servis tarafinda.

Kullanim:
    python3 probe_capacity.py            # tek seferlik anlik tesbit
    python3 probe_capacity.py <saniye>   # surekli yoklama, N saniyede bir
"""
import datetime
import json
import os
import sys
import time
import urllib.error
import urllib.request

ENV_PATH = "/root/projects/oc-mcp/.env"
BASE_URL = "https://integrate.api.nvidia.com/v1"
LOG_PATH = "/root/projects/oc-mcp/capacity_probe.log"

# OpenClaw'in surdugu model + Katman B'nin kullandigi iki model.
MODELS = [
    "nvidia/nemotron-3-ultra-550b-a55b",
    "nvidia/nemotron-3-super-120b-a12b",
    "deepseek-ai/deepseek-v4-flash",
]


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


def probe(model, key, timeout_s=30):
    """Mumkun olan en kucuk istek: tek token. Kapasiteyi kendimiz
    tuketmemek icin kasitli olarak minimal tutuldu."""
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 1,
        "temperature": 0.0,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions",
        data=payload,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            resp.read()
        return "OK", round(time.time() - t0, 2), ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")[:200].replace("\n", " ")
        except Exception:
            body = ""
        return f"HTTP {exc.code}", round(time.time() - t0, 2), body
    except Exception as exc:
        return type(exc).__name__, round(time.time() - t0, 2), str(exc)[:200]


def bir_tur(key, log_fh=None):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    satirlar = []
    for model in MODELS:
        durum, sure, detay = probe(model, key)
        kisa = model.split("/")[-1]
        satir = f"{ts} | {kisa:<32} | {durum:<12} | {sure:>6.2f}s | {detay}"
        print(satir, flush=True)
        satirlar.append((model, durum, sure, detay))
        if log_fh:
            log_fh.write(satir + "\n")
            log_fh.flush()
    return ts, satirlar


def main():
    key = load_key()
    if not key:
        print("HATA: NVIDIA_API_KEY bulunamadi.", flush=True)
        return 1

    araliksn = int(sys.argv[1]) if len(sys.argv) > 1 else 0

    if araliksn == 0:
        print("=" * 100, flush=True)
        print("ANLIK TESBIT", flush=True)
        print("=" * 100, flush=True)
        _, satirlar = bir_tur(key)
        print("=" * 100, flush=True)
        ultra = [s for s in satirlar if "ultra" in s[0]][0]
        print(flush=True)
        if ultra[1] == "OK":
            print("YORUM: nemotron-3-ultra NVIDIA API'sinde SU AN CALISIYOR.", flush=True)
            print("       Yani 'Worker local total request limit (33/32)' hatasi", flush=True)
            print("       NVIDIA'dan DEGIL, OpenClaw istemcisinden geliyor.", flush=True)
            print("       Beklemek yerine OpenClaw'i yeniden baslatmak gerekir.", flush=True)
        else:
            print(f"YORUM: nemotron-3-ultra NVIDIA API'sinde de reddediyor ({ultra[1]}).", flush=True)
            print("       Sinir gercekten servis tarafinda.", flush=True)
        return 0

    print(f"SUREKLI YOKLAMA -- her {araliksn} saniyede bir. Ctrl+C ile durdur.", flush=True)
    print(f"Kayit: {LOG_PATH}", flush=True)
    print("=" * 100, flush=True)
    with open(LOG_PATH, "a") as log_fh:
        log_fh.write(f"\n=== yoklama basladi {datetime.datetime.now()} aralik={araliksn}s ===\n")
        try:
            while True:
                bir_tur(key, log_fh)
                print("-" * 100, flush=True)
                time.sleep(araliksn)
        except KeyboardInterrupt:
            print("\nDurduruldu.", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
