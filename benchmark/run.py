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


def _ozet_tutarli(payload, solved):
    """scan_summary'yi ham noktalardan BAGIMSIZ olarak yeniden turetip
    karsilastirir.

    Ayni fonksiyonu tekrar cagirmak bir sey kanitlamaz -- kendi ciktisiyla
    kendini dogrulamis olur. Burada gecisler ve baskinlik esikleri
    noktalardan bastan hesaplanip ozetin soyledigiyle karsilastiriliyor;
    ozet ile ham veri ayrisirsa cagiran tarafa yanlis cevap gidiyor
    demektir ve bu, hicbir yerde hata vermeden olur.
    """
    TOL = 1e-4
    ozet = payload.get("scan_summary")
    if len(solved) < 2:
        return []
    if not ozet:
        return ["scan_summary alani yok -- tarama sonucu ozetsiz dondu"]

    eksen = ozet.get("axis", "temperature_K")

    def _fazlar(p):
        return tuple(sorted(k for k, v in (p.get("phase_molar_amounts") or {}).items()
                            if v is not None and v > TOL))

    sirali = sorted(solved, key=lambda p: p.get(eksen))
    sorunlar = []

    gorulen = sorted({f for p in sirali for f in _fazlar(p)})
    if gorulen != sorted(ozet.get("phases_seen", [])):
        sorunlar.append(f"phases_seen {ozet.get('phases_seen')} != ham veri {gorulen}")

    beklenen_gecis = sum(1 for a, b in zip(sirali, sirali[1:])
                         if _fazlar(a) != _fazlar(b))
    if beklenen_gecis != len(ozet.get("phase_transitions", [])):
        sorunlar.append(f"{len(ozet.get('phase_transitions', []))} gecis bildirildi, "
                        f"ham veride {beklenen_gecis} var")

    for bolge in ozet.get("dominant_phase_regions", []):
        faz = bolge.get("phase")
        if faz is None:
            continue
        nokta = min(sirali, key=lambda p: abs(p.get(eksen) - bolge["from"]))
        pay = (nokta.get("phase_molar_amounts") or {}).get(faz, 0.0)
        if pay <= 0.5:
            sorunlar.append(f"{faz} bolgesi {bolge['from']:.4g}'de basliyor deniyor "
                            f"ama orada payi {pay:.3f} (<= 0.5)")

    erime = ozet.get("melting")
    if erime:
        nokta = min(sirali, key=lambda p: abs(p.get(eksen) - erime["first_liquid"]["observed_at"]))
        sivi = sum(v for k, v in (nokta.get("phase_molar_amounts") or {}).items()
                   if k.upper().startswith("LIQUID"))
        if sivi <= TOL:
            sorunlar.append("first_liquid isaret edilen noktada sivi yok")

    return sorunlar


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

    # --- faz diyagrami (MAP) vakalari --------------------------------
    # Cikti tablo degil, EGRI KUMESI: her sinir boyunca hangi fazlarin
    # birlikte var oldugu degisir. O yuzden olcutler de farkli.
    #
    # Asil olcut DEGISMEZ SICAKLIKLAR. Bunlar diyagramin en belirgin,
    # en kolay dogrulanabilir ozellikleri -- ve bu projede BAGIMSIZ
    # olarak olculduler: Fe-C otektoidi tek denge hesaplarini ikiye
    # bolerek 1010-1012 K arasinda bulunmustu, MAP 1011.173 diyor.
    # Yani sistemin kendi ciktisini kendine referans yapmiyoruz.
    if payload.get("backend_used") == "native_oc_map":
        sinirlar = payload.get("boundaries") or []
        if not sinirlar:
            return False, "hicbir faz siniri izlenemedi"
        checks.append(f"{len(sinirlar)} sinir, {payload.get('point_count')} nokta")

        for name in expected.get("phases", []):
            if name not in (payload.get("phases") or []):
                return False, (f"'{name}' fazi diyagramda yok "
                               f"(gelen: {payload.get('phases')})")
        if expected.get("phases"):
            checks.append("fazlar dogru")

        bulunan = payload.get("invariant_temperatures_K") or []
        tol = expected.get("invariant_tolerance_K", 2.0)
        for beklenen in expected.get("invariant_temperatures_K", []):
            if not any(abs(b - beklenen) <= tol for b in bulunan):
                return False, (f"{beklenen:g} K civarinda degismez tepkime "
                               f"bulunamadi (bulunanlar: {bulunan})")
            checks.append(f"degismez {beklenen:g} K")

        en_az = expected.get("min_boundaries")
        if en_az is not None and len(sinirlar) < en_az:
            return False, f"{len(sinirlar)} sinir, en az {en_az} bekleniyordu"

        # Her sinir en az iki fazin bulustugu yerdir; tek fazli bir sinir
        # tanim geregi olamaz. Ucretsiz bir yapisal denetim.
        for b in sinirlar:
            if len(b.get("phases") or []) < 2:
                return False, f"tek fazli sinir: {b.get('phases')}"
        checks.append("sinirlar en az iki fazli")
        return True, " | ".join(checks)

    # --- Scheil katilasma vakalari -----------------------------------
    # Denge degil YOL: her nokta kendinden once ayrilan butun katiya
    # bagli. Bu yuzden olcutler de farkli.
    #
    # En onemlisi "completed". Yarim kalmis bir katilasma egrisini tam
    # gibi sunmak, bu projenin yakaladigi hatalarin aynisi olurdu --
    # ustelik eksik kalan son birkac yuzde, segregasyon sorusunun asil
    # sordugu yer. Bazi vakalarda BEKLENEN completed=False'tur: gecme
    # olcutu dogru hesaplamak degil, eksikligi dogru soylemektir.
    if payload.get("backend_used") == "native_oc_scheil":
        if not points:
            return False, "katilasma yolu bos dondu"
        checks.append(f"{len(points)} nokta")

        beklenen_tamam = expected.get("completed")
        if beklenen_tamam is not None and payload.get("completed") != beklenen_tamam:
            return False, (f"completed={payload.get('completed')}, beklenen "
                           f"{beklenen_tamam} (kalan sivi "
                           f"{payload.get('final_liquid_fraction')})")
        if beklenen_tamam is not None:
            checks.append("tamamlanma dogru raporlandi")

        ust = expected.get("max_final_liquid_fraction")
        if ust is not None:
            kalan = payload.get("final_liquid_fraction")
            if kalan is None or kalan > ust:
                return False, f"kalan sivi {kalan}, ust sinir {ust}"
            checks.append(f"kalan sivi {kalan:.4f}")

        for name in expected.get("solid_phases", []):
            if name not in (payload.get("solid_phases_formed") or []):
                return False, (f"'{name}' katilasmada olusmamis "
                               f"(olusanlar: {payload.get('solid_phases_formed')})")
        if expected.get("solid_phases"):
            checks.append("katilar dogru")

        # Segregasyonun kendisi: Scheil'in var olma sebebi. Son sivinin
        # bilesimi nominal degerin uzerine cikmali. Tamamen hesap
        # makinesiyle kontrol edilebilir, termodinamik gerektirmez.
        istek = case["arguments"]["elements_composition"]
        olcek = sum(istek.values())
        for element, en_az in (expected.get("segregation") or {}).items():
            son = (points[-1].get("liquid_composition") or {}).get(element)
            if son is None:
                return False, f"son sivida '{element}' yok"
            nominal = istek.get(element, 0) / olcek
            if son <= nominal:
                return False, (f"{element} zenginlesmemis: son sivi {son:.4g}, "
                               f"nominal {nominal:.4g}")
            if son < en_az:
                return False, f"{element} son sivida {son:.4g}, beklenen >= {en_az}"
            checks.append(f"{element} {nominal:.3g}->{son:.3g}")

        if payload.get("liquidus_K") is None:
            return False, "liquidus bulunamadi"
        checks.append(f"liquidus {payload['liquidus_K']:.1f} K")
        return True, " | ".join(checks)

    # --- diyagram vakalari -------------------------------------------
    if points is not None:
        solved = [p for p in points if "error" not in p]
        if not solved:
            return False, "hicbir nokta cozulemedi"
        checks.append(f"{len(solved)}/{len(points)} nokta")

        # --- ozet alani ham veriyle tutarli mi ----------------------
        # Bu olcut her tarama vakasinda kosuyor, vaka ayrica istemese de:
        # ozet artik cagiran tarafin OKUDUGU sey, dolayisiyla ham veriyle
        # ayrisirsa yanlis cevap uretir ve bunu sessizce yapar.
        ozet_sorunlari = _ozet_tutarli(payload, solved)
        if ozet_sorunlari:
            return False, "ozet ham veriyle tutmuyor: " + "; ".join(ozet_sorunlari)
        if payload.get("scan_summary"):
            checks.append("ozet tutarli")

        # Vakanin kendi bekledigi baskinlik esigi (varsa).
        for faz, beklenen in (expected.get("summary_dominant_from") or {}).items():
            bolgeler = [b for b in payload["scan_summary"]["dominant_phase_regions"]
                        if b.get("phase") == faz]
            if not bolgeler:
                return False, f"ozet '{faz}' icin baskin bolge bildirmiyor"
            bulunan = bolgeler[0]["from"]
            tolerans = expected.get("summary_dominant_tolerance", 0.02)
            if abs(bulunan - beklenen) > tolerans:
                return False, (f"{faz} baskinligi {bulunan:.4g} bildirildi, "
                               f"beklenen {beklenen:.4g}")
            checks.append(f"{faz} baskinlik esigi dogru")
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

        # --- eksen boyunca SIRA -------------------------------------
        # Bir taramada asil bilgi hangi fazlarin gorundugu degil, HANGI
        # SIRAYLA gorundugu. "Krom artarken karbur M7C3'ten M23C6'ya
        # doner" cumlesi ancak bu sekilde sinanir; sadece "ikisi de var"
        # demek sirayi ters cevirmis bir sonucu da gecirirdi.
        def _ilk_gorundugu(name):
            for p in solved:
                if name in (p.get("phase_molar_amounts") or {}):
                    return p.get("x", p.get("temperature_K"))
            return None

        for once, sonra in expected.get("phase_order", []):
            x_once, x_sonra = _ilk_gorundugu(once), _ilk_gorundugu(sonra)
            if x_once is None:
                return False, f"'{once}' fazi hic gorunmedi"
            if x_sonra is None:
                return False, f"'{sonra}' fazi hic gorunmedi"
            if not x_once < x_sonra:
                return False, (f"'{once}' {x_once:.4g}'te, '{sonra}' "
                               f"{x_sonra:.4g}'te -- sira ters")
        if expected.get("phase_order"):
            checks.append("faz sirasi dogru")

        # --- belirli bir konumda hangi fazlar -----------------------
        # "Kac nokta cozuldu" bir diyagramin DOGRU olup olmadigini
        # olcmuyor. Olculdu: steel1 Fe-4C-6Cr-2Mo-0.1V icin STEP, 900 K'de
        # kararli olan ferrit cizgisini surekliligle 1243 K'ye kadar
        # tasiyordu; oysa ~1130 K'den sonra ostenit kararli. Diyagramin
        # doksan derecelik bir bolumu yanlis fazi gosteriyordu ve C4 vakasi
        # geciyordu, cunku 45 noktanin hepsi hesaplanabilmisti.
        #
        # Referans motorun kendi ciktisi degil: her biri BAGIMSIZ bir tek
        # nokta hesabiyla dogrulanmis, ve tek nokta yolu global
        # minimizasyon yaptigi icin sureklilikten farkli bir sey olcuyor.
        def _en_yakin_nokta(hedef):
            return min(solved, key=lambda p: abs(
                (p.get("x", p.get("temperature_K")) or 0) - hedef))

        for hedef, isimler in (expected.get("phases_present_at") or {}).items():
            nokta = _en_yakin_nokta(float(hedef))
            var = nokta.get("phase_molar_amounts") or {}
            eksik = [n for n in isimler if n not in var]
            if eksik:
                return False, (f"{hedef} civarinda beklenen faz(lar) yok: "
                               f"{eksik} (gelen: {sorted(var)})")
            checks.append(f"{hedef}: {'+'.join(isimler)}")

        for hedef, isimler in (expected.get("phases_absent_at") or {}).items():
            nokta = _en_yakin_nokta(float(hedef))
            var = nokta.get("phase_molar_amounts") or {}
            fazla = [n for n in isimler if n in var]
            if fazla:
                return False, (f"{hedef} civarinda olmamasi gereken faz "
                               f"var: {fazla} -- surekliligin yari kararli "
                               "bir dalda kalmis olmasi bu sekilde gorunur")
            checks.append(f"{hedef}: {'/'.join(isimler)} yok")

        # Eksen uclarinda ne olmasi gerektigi. Ucun kendisi hesaplanmadan
        # gecerse bu olcut kalir -- istenen araligin sonu sonucta yoksa
        # soru tam cevaplanmamistir.
        for anahtar, indeks, etiket in (("phases_at_start", 0, "baslangic"),
                                        ("phases_at_end", -1, "bitis")):
            beklenen = expected.get(anahtar)
            if not beklenen:
                continue
            uc = solved[indeks]
            var = uc.get("phase_molar_amounts") or {}
            eksik = [n for n in beklenen if n not in var]
            if eksik:
                return False, (f"{etiket} noktasinda (x={uc.get('x', uc.get('temperature_K')):.4g}) "
                               f"beklenen faz(lar) yok: {eksik} (gelen: {sorted(var)})")
            checks.append(f"{etiket} fazlari dogru")

        # Istenen araligin iki ucu da sonucta olmali. Gap-fill bosluklarin
        # yalnizca ICINE nokta koydugu icin, STEP'in cizgisi eksen sonuna
        # ulasamadiginda istenen uc sessizce dusuyordu -- olculdu: 0.05
        # istenen tarama 0.0455'te bitiyordu.
        for anahtar, alan in (("axis_min", "axis_min"), ("axis_max", "axis_max")):
            sinir = payload.get(alan)
            if sinir is None:
                continue
            aralik = abs((payload.get("axis_max") or 0) - (payload.get("axis_min") or 0))
            if not any(abs(p.get("x", 1e30) - sinir) <= aralik * 1e-3 for p in solved):
                return False, f"istenen eksen sinirinda ({alan}={sinir:g}) nokta yok"
        if payload.get("axis_min") is not None:
            checks.append("eksen uclari kapsandi")

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
    # No one watches a benchmark run, and the interactive gnuplot windows
    # do not close: eighteen of them accumulated over four runs and turned
    # a 1.1 s scan into a 156 s one, timing out three cases whose failure
    # was then blamed on load. A measurement harness must not degrade the
    # thing it measures.
    env["OC_INTERACTIVE_WINDOW"] = "0"
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
                        # 300, not 180. Five runs in a row lost two or
                        # three cases to this, and never the same ones:
                        # every one of them passed on its own, in seconds.
                        # The constant is here to stop a hung run, and 300
                        # still does that. A harness that marks a slow but
                        # correct calculation as broken is reporting on
                        # itself, not on the system.
                        timeout=300,
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
    if not secim or secim == ["hepsi"]:
        selected = case_registry.CASES
    else:
        # Birden fazla ad verilebilir: kategori adi, grup adi ya da vaka
        # id'si karisik olarak. Vaka yazarken tam olarak yeni eklenenleri
        # kosmak icin gerekiyor -- tek tek kosmak her seferinde sunucuyu
        # yeniden ayaga kaldiriyordu.
        selected = []
        bulunmayan = []
        for wanted in secim:
            if hasattr(case_registry, wanted):
                parca = getattr(case_registry, wanted)
            else:
                parca = [c for c in case_registry.CASES if c["id"] == wanted]
            if not parca:
                bulunmayan.append(wanted)
            for case in parca:
                if case not in selected:
                    selected.append(case)
        if bulunmayan:
            print(f"vaka bulunamadi: {', '.join(bulunmayan)}")
            return 2
    if not selected:
        print("secilen vaka yok")
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
