"""Ablation isci sureci: TEK bir vakayi TEK bir yapilandirmada calistirir.

Ayri surecte calismak zorunlu: yapilandirma 1'de (PREFLIGHT kapali) motor
segmentasyon hatasi verebiliyor. Bu bir Python istisnasi degil, surecin
isletim sistemi tarafindan sonlandirilmasi -- yakalanamaz. Kosucu bu
sureci baslatip cikis koduna bakarak cokmeyi tespit eder.

Kullanim:  ablation_worker.py <mod> <vaka-json>
Ciktisi :  tek satir JSON (stdout'un son satiri)

Modlar (birikimli):
  bare      : PREFLIGHT yok, yedek motor yok, dogrulama yok -> sadece OCASI
  preflight : + PREFLIGHT
  cascade   : + kademeli motor (yedek native, STEP)
  layera    : + Katman A (deterministik yapisal denetim)
  full      : + Katman B (bagimsiz model denetimi)
"""
import json
import os
import sys
import time

sys.path.insert(0, "/root/projects/oc-mcp")

MOD_SIRASI = ["bare", "preflight", "cascade", "layera", "full"]


def acik_mi(mod, katman):
    """Birikimli modlar: 'cascade' modu preflight'i de icerir."""
    return MOD_SIRASI.index(katman) <= MOD_SIRASI.index(mod)


def main():
    mod = sys.argv[1]
    case = json.loads(sys.argv[2])
    tool = case["tool"]
    args = case["arguments"]

    out = {"mod": mod, "no": case["no"], "tool": tool}
    t0 = time.time()

    # --- PREFLIGHT ---------------------------------------------------
    if acik_mi(mod, "preflight"):
        import preflight
        if tool == "calculate_property_diagram":
            problems = preflight.check_property_diagram_request(
                args["database"], args["elements_composition"],
                args["temperature_min_K"], args["temperature_max_K"],
                args.get("pressure_Pa", 1e5), args.get("suspended_phases"),
            )
        elif tool == "compare_alloys":
            problems = (
                preflight.check_equilibrium_request(
                    args["database"], args["composition_a"], args["temperature_K"],
                    args.get("pressure_Pa", 1e5), args.get("suspended_phases"))
                + preflight.check_equilibrium_request(
                    args["database"], args["composition_b"], args["temperature_K"],
                    args.get("pressure_Pa", 1e5), args.get("suspended_phases"))
            )
        else:
            problems = preflight.check_equilibrium_request(
                args["database"], args["elements_composition"], args["temperature_K"],
                args.get("pressure_Pa", 1e5), args.get("suspended_phases"),
            )
        # Sadece gercek retleri say; "Note:" ile baslayanlar uyaridir.
        hard = [p for p in problems if not p.startswith("Note:")]
        if hard:
            out.update({
                "outcome": "preflight_rejected",
                "engine_touched": False,
                "problems": hard,
                "runtime_s": round(time.time() - t0, 3),
            })
            print(json.dumps(out, ensure_ascii=False))
            return

    # --- YURUTME -----------------------------------------------------
    import oc_service
    result = None
    err = None

    # oc_service.calculate_equilibrium bu iki normalizasyonu kendi yapar;
    # _calculate_equilibrium_ocasi ve native_step ise COZULMUS mutlak yol ve
    # BUYUK HARFLI bilesim bekler. Ciplak yollari cagirirken ayni hazirligi
    # elle yapmak zorundayiz, yoksa olcum yapilandirma farkini degil bizim
    # cagri hatamizi olcer.
    def _db_path(name):
        return name if os.path.isabs(name) else os.path.join(
            oc_service.DEFAULT_DB_DIR, name)

    def _upper(comp):
        return {el.upper(): amt for el, amt in comp.items()}

    dbp = _db_path(args["database"])
    if not os.path.isfile(dbp):
        out.update({"outcome": "engine_error", "engine_touched": True,
                    "error": f"Database not found: {dbp}",
                    "runtime_s": round(time.time() - t0, 3)})
        print(json.dumps(out, ensure_ascii=False))
        return

    try:
        kademeli = acik_mi(mod, "cascade")

        def hesapla(comp, T):
            """Tek nokta. Kademeli acikken tam yol, kapaliyken ciplak OCASI."""
            if kademeli:
                return oc_service.calculate_equilibrium(
                    args["database"], comp, T, args.get("pressure_Pa", 1e5),
                    args.get("suspended_phases"))
            return oc_service._calculate_equilibrium_ocasi(
                dbp, _upper(comp), T, args.get("pressure_Pa", 1e5),
                args.get("suspended_phases"))

        if tool == "calculate_property_diagram":
            tmin = args["temperature_min_K"]
            tmax = args["temperature_max_K"]
            n = args.get("n_points", 15)
            if kademeli:
                import native_step
                try:
                    # (combined, gap_filled_temperatures) demeti doner;
                    # combined ise (T, kesirler, kaynak) uclulerinden olusur.
                    # server.py ile ayni sekle cevir, yoksa Katman A yanlis
                    # sey denetler.
                    combined, _gap_T = native_step.build_combined_series(
                        dbp, _upper(args["elements_composition"]), tmin, tmax,
                        n, args.get("pressure_Pa", 1e5),
                    )
                    result = {
                        "points": [
                            {"temperature_K": T, "phase_molar_amounts": fr,
                             "source": src}
                            for T, fr, src in combined
                        ],
                        "backend_used": "native_oc_step_gnuplot",
                    }
                except Exception as step_exc:
                    # 4. KADEME (son care): native STEP yolu tamamen
                    # basarisiz oldugunda server.py nokta nokta taramaya
                    # duser. Bu kademe olmadan alni-4slx gibi STEP'in
                    # tikandigi veritabanlari cevapsiz kalir -- olcum
                    # sistemin kademe sayisini eksik yansitir.
                    step = (tmax - tmin) / (n - 1)
                    pts = []
                    for i in range(n):
                        T = tmin + i * step
                        try:
                            r = hesapla(args["elements_composition"], T)
                            pts.append({"temperature_K": T,
                                        "phase_molar_amounts":
                                            r.get("phase_molar_amounts", {})})
                        except Exception as exc:
                            pts.append({"temperature_K": T,
                                        "error": str(exc)[:120]})
                    result = {
                        "points": pts,
                        "backend_used": "python_loop_matplotlib",
                        "native_step_error": str(step_exc)[:200],
                    }
            else:
                # Kademeli kapali: her noktayi ciplak OCASI ile hesapla.
                step = (tmax - tmin) / (n - 1)
                pts = []
                for i in range(n):
                    T = tmin + i * step
                    try:
                        r = hesapla(args["elements_composition"], T)
                        pts.append({"temperature_K": T,
                                    "phase_molar_amounts": r.get("phase_molar_amounts", {})})
                    except Exception as exc:
                        pts.append({"temperature_K": T, "error": str(exc)[:120]})
                result = {"points": pts, "backend_used": "ocasi_loop"}

        elif tool == "compare_alloys":
            a = hesapla(args["composition_a"], args["temperature_K"])
            b = hesapla(args["composition_b"], args["temperature_K"])
            result = {"a": a, "b": b,
                      "backend_used": a.get("backend_used", "ocasi")}

        else:
            result = hesapla(args["elements_composition"], args["temperature_K"])
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"[:300]

    out["engine_touched"] = True
    out["runtime_s"] = round(time.time() - t0, 3)

    if err is not None:
        out.update({"outcome": "engine_error", "error": err})
        print(json.dumps(out, ensure_ascii=False, default=str))
        return

    out["backend_used"] = result.get("backend_used")

    # --- KATMAN A ----------------------------------------------------
    if acik_mi(mod, "layera"):
        import result_check
        # compare_alloys iki sonuc dondurur; ikisini de denetle.
        if tool == "compare_alloys":
            pa, prob_a = result_check.verify_result(result["a"])
            pb, prob_b = result_check.verify_result(result["b"])
            passed_a, problems_a = pa, prob_a + prob_b
            out["layer_a_passed"] = bool(pa and pb)
            out["layer_a_problems"] = problems_a
        else:
            passed, problems = result_check.verify_result(result)
            out["layer_a_passed"] = bool(passed)
            out["layer_a_problems"] = problems
    else:
        out["layer_a_passed"] = None

    # --- KATMAN B ----------------------------------------------------
    if acik_mi(mod, "full"):
        import semantic_check
        rev = semantic_check.review(args, result, timeout_s=60, retries=(0, 4))
        out["layer_b_available"] = rev.get("available")
        out["layer_b_passed"] = rev.get("passed")
        out["layer_b_model"] = rev.get("model_used")
    else:
        out["layer_b_available"] = None
        out["layer_b_passed"] = None

    out["outcome"] = "computed"
    # Sonucun ozeti (tam sonuc cok buyuk olabilir)
    if tool == "calculate_property_diagram":
        pts = result.get("points", [])
        out["n_points"] = len(pts)
        out["n_failed_points"] = sum(1 for p in pts if "error" in p)
    elif tool == "compare_alloys":
        out["gibbs_energy_J"] = result["a"].get("gibbs_energy_J")
        out["gibbs_energy_J_b"] = result["b"].get("gibbs_energy_J")
    else:
        out["gibbs_energy_J"] = result.get("gibbs_energy_J")
        out["phases"] = list((result.get("phase_molar_amounts") or {}).keys())

    print(json.dumps(out, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
