"""DEBUGGER'in dongu kapatma yolunu izole test eder.

Gercek API cagrisi yapmaz: semantic_check.review yerine, ilk cagrida
okunamayan karar donduren, ikinci cagrida (skip_models ile) kullanilabilir
karar donduren bir sahte kullanilir. Test edilen sey ag degil, server.py'nin
karar mantigi.
"""
import sys

sys.path.insert(0, "/root/projects/oc-mcp")
import server  # noqa: E402
import semantic_check  # noqa: E402

SAGLIKLI = {
    "gibbs_energy_J": -56564.0,
    "phase_molar_amounts": {"FCC_A1": 1.0},
    "backend_used": "native_oc",
}
ISTEK = {"database": "steel1.TDB",
         "elements_composition": {"FE": 0.99, "C": 0.01},
         "temperature_K": 1200}

gercek_review = semantic_check.review
cagrilar = []


def sahte_okunamaz_sonra_okunur(request_args, result, **kw):
    """1. cagri: okunamayan karar. 2. cagri (skip_models dolu): gecerli karar."""
    skip = kw.get("skip_models") or ()
    cagrilar.append(list(skip))
    if not skip:
        return {"available": True, "passed": None,
                "model_used": "nvidia/nemotron-3-super-120b-a12b",
                "reason": "Model cevabından net bir SONUC okunamadı: ..."}
    return {"available": True, "passed": True,
            "model_used": "deepseek-ai/deepseek-v4-flash",
            "reason": "Gerekçe: ...\nSONUC: BASARILI"}


def sahte_hep_okunamaz(request_args, result, **kw):
    cagrilar.append(list(kw.get("skip_models") or ()))
    return {"available": True, "passed": None,
            "model_used": "nvidia/nemotron-3-super-120b-a12b",
            "reason": "okunamadı"}


def kos(sahte, baslik):
    global cagrilar
    cagrilar = []
    semantic_check.review = sahte
    try:
        r = server._attach_verification(dict(SAGLIKLI), dict(ISTEK))
    finally:
        semantic_check.review = gercek_review
    ver = r.get("verification", {})
    dbg = ver.get("debugger") or {}
    print(f"--- {baslik}")
    print(f"    Katman B cagri sayisi : {len(cagrilar)}   skip_models: {cagrilar}")
    print(f"    debugger.category     : {dbg.get('category')}")
    print(f"    debugger.outcome      : {dbg.get('outcome')}")
    print(f"    nihai layer_b model   : {(ver.get('layer_b') or {}).get('model_used')}")
    print(f"    nihai layer_b passed  : {(ver.get('layer_b') or {}).get('passed')}")
    print(f"    failure alani         : {(r.get('failure') or {}).get('category')}")
    return r, ver, dbg


ok = 0

r, ver, dbg = kos(sahte_okunamaz_sonra_okunur, "A · ilk model okunamaz, ikincisi cevap veriyor")
kosullar = [
    (len(cagrilar) == 2, "iki kez soruldu"),
    (cagrilar[1] == ["nvidia/nemotron-3-super-120b-a12b"], "ilk model atlandi"),
    (dbg.get("outcome") == "resolved", "outcome=resolved"),
    ((ver.get("layer_b") or {}).get("model_used") == "deepseek-ai/deepseek-v4-flash",
     "nihai karar ikinci modelden"),
    (r.get("failure") is None, "failure alani temizlendi"),
]
for k, ad in kosullar:
    print(f"      [{'OK ' if k else 'HATA'}] {ad}")
    ok += 1 if k else 0
print()

r, ver, dbg = kos(sahte_hep_okunamaz, "B · her iki model de okunamaz karar veriyor")
kosullar2 = [
    (len(cagrilar) == 2, "iki kez soruldu, sonra durdu"),
    (dbg.get("outcome") == "unresolved", "outcome=unresolved"),
    (r.get("failure", {}).get("category") == "reviewer_unreadable",
     "failure alani korundu"),
    (ver.get("passed") is True, "Katman A karari gecerli kaldi — hesap hatali sayilmadi"),
]
for k, ad in kosullar2:
    print(f"      [{'OK ' if k else 'HATA'}] {ad}")
    ok += 1 if k else 0

toplam = len(kosullar) + len(kosullar2)
print()
print(f"SONUC: {ok}/{toplam}")
sys.exit(0 if ok == toplam else 1)
