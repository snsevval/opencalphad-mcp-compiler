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

    return judge_result(case, payload)


# Cogu vakanin gecme olcutu bir referans degere DAYANMAZ. Kutle korunumu ve
# karbur stokiyometrisi sonucun kendi icinden ya da formulden cikar, motorun
# ciktisindan degil -- yani sistemin kendi sayisini kendine referans yapma
# tuzagina dusmeden dogrulama yapilabiliyor. Referans deger yalnizca elde
# gercekten dogrulanmis bir sayi varsa yaziliyor.
MASS_BALANCE_TOL = 2e-4       # element basina, mol
SUM_TOL = 1e-3                # faz miktarlari toplami
STOICH_TOL = 1e-3             # karbur karbon orani


def _mass_balance(payload, request_composition):
    """Her element icin (faz miktari x fazdaki derisim) toplami, istenen
    miktara esit mi. Sunucunun element_distribution alani bu carpimi zaten
    yapiyor; yoksa buradan hesaplanir, ki alanin kendisi de sinanmis olur."""
    problems = []
    scale = sum(request_composition.values())
    amounts = payload.get("phase_molar_amounts") or {}
    per_phase = payload.get("phase_element_composition") or {}
    for element, requested in request_composition.items():
        symbol = element.upper()
        total = sum(
            amount * (per_phase.get(phase) or {}).get(symbol, 0.0)
            for phase, amount in amounts.items()
        )
        want = requested / scale
        if abs(total - want) > MASS_BALANCE_TOL:
            problems.append(f"{symbol}: {total:.6g} != {want:.6g}")
    return problems


def judge_result(case, payload):
    """Hesap vakalari icin. Olcutlerin hepsi hesap makinesiyle kontrol
    edilebilir; hicbiri uzmanlik gerektirmiyor."""
    expected = case["expected"]
    checks = []

    # Belgelenmis acik kusur. Vaka KALIYOR ama bunun bir gerileme degil,
    # bilinen ve kaydedilmis bir sinir oldugu ayrilabilsin diye ayri
    # isaretleniyor. Kusur duzeltilirse bu bayrak kaldirilir ve vaka normal
    # olcutlerine doner -- yani bayragin kendisi bir yapilacak isin kaydidir.
    if expected.get("known_defect"):
        return None, expected["known_defect"]

    # Bazi vakalarda dogru davranis HESAPLAYAMAMAKTIR. Motorun her bilesimi
    # cozebilmesi gerekmiyor; gerekli olan, cozemedigini SOYLEMESI -- cokmek
    # ya da uydurma bir sayi dondurmek yerine. Bu projenin gecmisinde ayni
    # durum segfault uretiyordu, o yuzden temiz hata kendi basina bir olcut.
    if expected.get("engine_limit"):
        if "error" not in payload:
            return False, "hata beklenirken sonuc dondu -- motor sinirini asmis?"
        if payload.get("gibbs_energy_J") is not None:
            return False, "hem hata hem sayi dondu"
        blob = str(payload["error"])
        tiers = [t for t in ("OCASI", "native") if t in blob]
        if len(tiers) < 2:
            return False, f"her iki kademe denenmemis gorunuyor: {blob[:100]}"
        return True, "iki kademe de denendi, temiz hata dondu"

    if "error" in payload:
        return False, f"hata dondu: {str(payload['error'])[:120]}"

    # --- karsilastirma vakalari ---------------------------------------
    # compare_alloys iki tam sonucu ve bir karsilastirma ozeti donduruyor.
    # Her iki tarafi da tek nokta vakasi gibi denetliyoruz, sonra ozetin
    # onlarla tutarli oldugunu kontrol ediyoruz -- ozet bagimsiz bir kaynak
    # degil, ayni sayilardan turetilmis olmali.
    if "comparison" in payload:
        summary = payload["comparison"]
        etiketler = [k for k in payload if k != "comparison"
                     and isinstance(payload[k], dict)
                     and "phase_molar_amounts" in payload[k]]
        if len(etiketler) != 2:
            return False, f"iki alasim beklenirken {len(etiketler)} bulundu"
        notlar = []
        for etiket in etiketler:
            yan = payload[etiket]
            toplam = sum((yan.get("phase_molar_amounts") or {}).values())
            if abs(toplam - 1.0) > SUM_TOL:
                return False, f"{etiket}: faz toplami {toplam:.6f}"
            notlar.append(f"{etiket} toplam {toplam:.4f}")
        fark = summary.get("gibbs_energy_difference_J")
        if fark is None:
            return False, "karsilastirmada gibbs_energy_difference_J yok"
        beklenen = (payload[etiketler[1]]["gibbs_energy_J"]
                    - payload[etiketler[0]]["gibbs_energy_J"])
        if abs(fark - beklenen) > 1.0:
            return False, (f"ozet fark {fark:.1f}, iki sonucun farki "
                           f"{beklenen:.1f} -- ozet turetilmemis")
        notlar.append(f"dG={fark:,.1f} J tutarli")
        for name in expected.get("phases_in_both", []):
            if name not in (summary.get("phases_in_both") or []):
                return False, f"'{name}' iki alasimda da beklenirken yok"
        if expected.get("phases_in_both"):
            notlar.append("ortak fazlar dogru")
        if expected.get("gibbs_difference_sign"):
            isaret = "+" if fark > 0 else "-"
            if isaret != expected["gibbs_difference_sign"]:
                return False, f"dG isareti {isaret}, beklenen {expected['gibbs_difference_sign']}"
            notlar.append(f"dG isareti {isaret}")
        return True, " | ".join(notlar)

    amounts = payload.get("phase_molar_amounts") or {}
    points = payload.get("points")

    # --- diyagram vakalari -------------------------------------------
    if points is not None:
        solved = [p for p in points if "error" not in p]
        if not solved:
            return False, "hicbir nokta cozulemedi"
        checks.append(f"{len(solved)}/{len(points)} nokta")
        want_max_failed = expected.get("max_failed_fraction")
        if want_max_failed is not None:
            failed = (len(points) - len(solved)) / len(points)
            if failed > want_max_failed:
                return False, f"cozulemeyen nokta orani {failed:.0%} > {want_max_failed:.0%}"
        for name in expected.get("phases", []):
            seen = any(name in (p.get("phase_molar_amounts") or {}) for p in solved)
            if not seen:
                return False, f"'{name}' fazi hicbir noktada yok"
        if expected.get("phases"):
            checks.append("beklenen fazlar var")

    # --- tek nokta vakalari ------------------------------------------
    else:
        if not amounts:
            return False, "faz miktari donmedi"

        total = sum(amounts.values())
        if abs(total - 1.0) > SUM_TOL:
            return False, f"faz miktarlari {total:.6f}, 1.0 degil"
        checks.append(f"toplam {total:.4f}")

        missing = [n for n in expected.get("phases", []) if n not in amounts]
        if missing:
            return False, f"beklenen faz(lar) yok: {missing} (gelen: {sorted(amounts)})"
        if expected.get("phases"):
            checks.append(f"{len(expected['phases'])} faz dogru")

        # Faz kapatma vakalarinda kapatilan fazin ORTADA OLMAMASI olcut.
        # Motor askiya almayi sessizce yutarsa sonuc kararli dengedir --
        # sorulan yari kararli soru degil.
        beklenmeyen = [n for n in expected.get("phases_absent", []) if n in amounts]
        if beklenmeyen:
            return False, f"kapatilmasi gereken faz sonucta var: {beklenmeyen}"
        if expected.get("phases_absent"):
            checks.append(f"{len(expected['phases_absent'])} faz kapali")

        if expected.get("phase_count") is not None:
            if len(amounts) != expected["phase_count"]:
                return False, (f"{len(amounts)} faz dondu, beklenen "
                               f"{expected['phase_count']}: {sorted(amounts)}")

        if expected.get("mass_balance"):
            problems = _mass_balance(payload, case["arguments"]["elements_composition"])
            if problems:
                return False, "kutle dengesi kapanmiyor -> " + "; ".join(problems)
            checks.append("kutle dengesi")

        if expected.get("elements_present"):
            per_phase = payload.get("phase_element_composition") or {}
            seen = set()
            for composition in per_phase.values():
                seen |= {e.upper() for e in composition}
            wanted = {e.upper() for e in case["arguments"]["elements_composition"]}
            absent = wanted - seen
            if absent:
                return False, f"istenen element(ler) hicbir fazda yok: {sorted(absent)}"
            checks.append("elementler yerinde")

        for phase, carbon in (expected.get("stoichiometry") or {}).items():
            actual = ((payload.get("phase_element_composition") or {})
                      .get(phase, {}).get("C"))
            if actual is None:
                return False, f"'{phase}' fazinda C bulunamadi"
            if abs(actual - carbon) > STOICH_TOL:
                return False, (f"{phase} stokiyometrisi: C={actual:.6g}, "
                               f"beklenen {carbon:.6g}")
            checks.append(f"{phase} stokiyometrisi")

        reference = expected.get("gibbs_energy_J")
        if reference is not None:
            actual = payload.get("gibbs_energy_J")
            if actual is None:
                return False, "gibbs_energy_J yok"
            if abs(actual - reference["value"]) > reference["tolerance"]:
                return False, (f"G={actual:.3f}, referans {reference['value']} "
                               f"+/- {reference['tolerance']}")
            checks.append(f"G={actual:.1f}")

    want_backend = expected.get("backend_used")
    if want_backend and payload.get("backend_used") != want_backend:
        return False, (f"backend={payload.get('backend_used')!r}, "
                       f"beklenen {want_backend!r}")
    if payload.get("backend_used"):
        checks.append(payload["backend_used"])

    return True, " | ".join(checks)


async def run_all(selected, semantic_check=True):
    # TAM SISTEM varsayilan. Katman B cagri basina ~35 saniye ekliyor ve bir
    # kiyaslama kosumunu yarim saate cikariyor -- ama olculmek istenen sey
    # sistemin kendisi, hizlandirilmis bir kesiti degil. --hizli bayragi
    # gelistirme sirasinda vaka yazarken kullanilir, raporlanan kosumda degil.
    #
    # Saglayici cokerse kiyaslama yine de gecerli kalir: gecme olcutleri
    # Katman B'nin KARARINA dayanmiyor, cunku ulasilamayan bir hakem
    # kimyaya dair hicbir sey soylemez. Kosum bunu ayrica kaydeder.
    env = dict(os.environ)
    env["OC_SEMANTIC_CHECK"] = "1" if semantic_check else "0"
    params = StdioServerParameters(command=RUN_SERVER_SH, args=[], env=env)
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
                # Katman B'nin bu vakada ne dedigi ayrica kaydediliyor.
                # Gecme olcutu DEGIL -- ulasilamayan bir hakem kimyaya dair
                # hicbir sey soylemez -- ama tam sistem kosuldugunda hakemin
                # kac vakada gorus bildirebildigi olcumun parcasi.
                review = ((payload.get("verification") or {}).get("layer_b")
                          if isinstance(payload, dict) else None) or {}
                results.append({
                    "id": case["id"],
                    "zorluk": case["zorluk"],
                    "passed": passed,
                    "note": note,
                    "seconds": round(time.time() - started, 2),
                    "layer_b": (
                        None if not review else
                        "ulasilamadi" if not review.get("available") else
                        {True: "BASARILI", False: "BASARISIZ",
                         None: "okunamadi"}[review.get("passed")]
                    ),
                })
    return results


def main(argv):
    # Bayraklar secici degil: "run.py --hizli" butun vakalari kosmali.
    secim = [a for a in argv[1:] if not a.startswith("--")]
    wanted = secim[0] if secim else None
    if wanted in (None, "hepsi"):
        selected = case_registry.CASES
    elif hasattr(case_registry, wanted):
        selected = getattr(case_registry, wanted)
    else:
        selected = [c for c in case_registry.CASES if c["id"] == wanted]
    if not selected:
        print(f"vaka bulunamadi: {wanted}")
        return 2

    results = asyncio.run(run_all(selected, semantic_check="--hizli" not in argv))

    width = max(len(r["id"]) for r in results)
    for r in results:
        mark = {True: "GECTI", False: "KALDI", None: "BULGU"}[r["passed"]]
        hakem = f"  [B:{r['layer_b']}]" if r.get("layer_b") else ""
        print(f"  {mark:5}  {r['id']:<{width}}  {r['zorluk']:<5} "
              f"{r['seconds']:>6.2f}s  {r['note']}{hakem}")

    kaldi = [r for r in results if r["passed"] is False]
    bulgu = [r for r in results if r["passed"] is None]
    olculen = [r for r in results if r["passed"] is not None]
    print()
    print(f"{len(olculen) - len(kaldi)}/{len(olculen)} gecti"
          + (f"   ({len(bulgu)} belgelenmis kusur ayri tutuldu)" if bulgu else ""))
    for zorluk in ("kolay", "orta", "zor"):
        grup = [r for r in olculen if r["zorluk"] == zorluk]
        if grup:
            ok = sum(1 for r in grup if r["passed"])
            print(f"  {zorluk:<6} {ok}/{len(grup)}")

    hakemli = [r for r in results if r.get("layer_b")]
    if hakemli:
        dagitim = {}
        for r in hakemli:
            dagitim[r["layer_b"]] = dagitim.get(r["layer_b"], 0) + 1
        print()
        print("Katman B: " + " · ".join(f"{k} {v}" for k, v in
                                        sorted(dagitim.items())))
    return 1 if kaldi else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
