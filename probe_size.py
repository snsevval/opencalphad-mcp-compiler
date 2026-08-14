"""Hipotez testi: 'Worker local total request limit reached (32/32)' hatasi
istek SAYISINDAN mi yoksa istek BOYUTUNDAN mi kaynaklaniyor?

Kucuk yoklamalar hep geciyor, kullanicinin oturumu hep takiliyor. Aradaki
tek belirgin fark baglam buyuklugu. Bu betik ayni modele giderek buyuyen
istemler gonderip kirilma noktasini ariyor.

Ayrica arka arkaya hizli cagri yaparak sayi hipotezini de sinar.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request

ENV_PATH = "/root/projects/oc-mcp/.env"
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL = "nvidia/nemotron-3-ultra-550b-a55b"


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


def call(key, prompt, max_tokens=1, timeout_s=120):
    payload = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": 0.0,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{BASE_URL}/chat/completions", data=payload,
        headers={"Authorization": f"Bearer {key}",
                 "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            resp.read()
        return "OK", round(time.time() - t0, 2), ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", "replace")[:300].replace("\n", " ")
        except Exception:
            body = ""
        return f"HTTP {exc.code}", round(time.time() - t0, 2), body
    except Exception as exc:
        return type(exc).__name__, round(time.time() - t0, 2), str(exc)[:200]


def main():
    key = load_key()
    if not key:
        print("HATA: NVIDIA_API_KEY yok")
        return 1

    print("=" * 96)
    print("TEST 1 — ISTEK BOYUTU")
    print("  Ayni modele giderek buyuyen istem. Kirilma noktasi var mi?")
    print("=" * 96)
    # ~4 karakter = 1 token kabaca
    boyutlar = [10, 1_000, 5_000, 20_000, 60_000, 150_000, 400_000, 800_000]
    dolgu = "Bu bir termodinamik hesap sonucudur. Faz oranlari ve Gibbs enerjisi. "
    for n in boyutlar:
        prompt = (dolgu * (n // len(dolgu) + 1))[:n]
        tok = n // 4
        durum, sure, detay = call(key, prompt)
        print(f"  {n:>8} karakter (~{tok:>7} token) | {durum:<12} | {sure:>6.2f}s | {detay[:90]}",
              flush=True)
        if durum != "OK":
            print(f"  --> KIRILMA NOKTASI: ~{n} karakter", flush=True)
            break

    print()
    print("=" * 96)
    print("TEST 2 — ISTEK SAYISI")
    print("  Kucuk istekler, hizli arka arkaya. Sayaç dolan bir sey var mi?")
    print("=" * 96)
    hata = 0
    for i in range(1, 41):
        durum, sure, detay = call(key, "hi")
        if durum != "OK":
            hata += 1
            print(f"  {i:>3}. istek | {durum} | {detay[:100]}", flush=True)
            if hata >= 3:
                print("  --> ard arda hata, duruluyor", flush=True)
                break
        elif i % 10 == 0:
            print(f"  {i:>3}. istek | OK ({sure:.2f}s)", flush=True)
    if hata == 0:
        print("  40 istegin 40'i gecti — sayi tabanli bir sinir GORULMEDI", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
