"""VERIFY step: two independent layers, deliberately not "one model looks
at everything and rubber-stamps it" (see the plan file, Faz 9).

Layer A (deterministic, code, cheap): numeric tolerance checks against a
known reference value where we have one, plus universal structural
sanity checks (no error field, phase fractions sum to ~1, required fields
present) that apply to every case regardless of whether a precise
reference exists.

Layer B (model-based, only when Layer A alone can't judge correctness --
i.e. "structural_only" cases with no precise reference number): an
NVIDIA-hosted model DIFFERENT from whichever model a human/AI client used
to ask for the calculation reviews the raw result for physical
plausibility. This is the actual execution path in this project already
runs through plain Python (executor.py calls the MCP tool directly, no
LLM in the loop at all) -- Layer B's independence is from the CASE
AUTHOR's expectations, not from a co-conspiring executor model.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

import result_check

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
# Deliberately a different model than whatever a human/AI client normally
# drives this MCP server with (that's typically nemotron-3-ultra) -- see
# the plan file, Faz 9: "dümdüz tek model hepsine bakmasın".
# A chain, not a single model: the free tier returns 529 "overloaded"
# unpredictably (three separate loop runs hit it in one session), so if one
# model is busy the next is tried rather than reporting the result as
# unverifiable. Every entry is from a different family than the
# Nemotron that normally drives this MCP server -- see plan file Faz 10:
# the point of Layer B is a genuinely independent second opinion, so
# "same family, different size" would defeat it.
# Order is measured, not assumed. Benchmarked 2026-08-03, 3 calls each
# against a short validation prompt:
#   deepseek-v4-flash   2/3 ok, ~12s      <- only usable independent one
#   step-3.7-flash      2/3 ok but returns content=None (unusable shape)
#   glm-5.2             0/3, all timeouts
#   minimax-m3          0/3, all timeouts
#   mistral-medium-3.5  0/3, all timeouts
#   gemma-4-31b         0/3, all timeouts
#   kimi-k2.6           0/3, all HTTP 404 (not enabled for this account)
# So the free tier currently offers exactly one dependable independent
# reviewer. nemotron-3-super is kept as a last resort because it does
# answer reliably -- but it shares a family with the Nemotron that drives
# this server, so a verdict from it is a WEAKER kind of independence.
# verify_layer_b records which model actually answered, so a report never
# silently passes off the fallback as the independent review.
# OC_VALIDATOR_MODEL (singular) still works and pins the chain to one model.
_DEFAULT_VALIDATOR_MODELS = [
    "deepseek-ai/deepseek-v4-flash",
    "nvidia/nemotron-3-super-120b-a12b",
]

# Layer C reviews the rendered chart, so it needs models that actually
# accept an image. Benchmarked 2026-08-03 against a real agcu.TDB chart,
# asking three checkable questions (y-axis origin, number of series,
# visible discontinuity):
#   nemotron-3-nano-omni  6.9s   all three correct
#   minimax-m3           42.9s   all three correct, also read values off
#                                the curves accurately (~0.73 / ~0.24)
#   inkling              HTTP 404 (not enabled for this account)
#   cosmos3-nano-reasoner HTTP 404 (not enabled for this account)
#   gemma-4-31b          timeout
# Independent model first, same-family fallback second -- same principle
# as Layer B.
_DEFAULT_VISION_MODELS = [
    "minimaxai/minimax-m3",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
]
_pinned_vision = os.environ.get("OC_VISION_MODEL", "")
VISION_MODELS = [_pinned_vision] if _pinned_vision else _DEFAULT_VISION_MODELS

# Layer C asks the model for OBSERVATIONS and lets code decide.
#
# The first version asked for a verdict -- "is this chart defective?" -- and
# got it wrong in both directions (2026-08-03): it passed a chart that drew
# one phase twice, reasoning that "LIQUID" and "LIQUID#1" are different
# names (true as text, but #1 is CALPHAD's default-composition-set suffix),
# and it failed a correct chart because solid phases vanish above ~1060 K,
# which is simply melting. Both observations were accurate; both
# interpretations needed domain rules the model does not hold.
#
# So the question changed. The model now reports only what it sees -- curve
# count, legend entries, axis bounds -- each of which has exactly one right
# answer that chart_ground_truth() already knows, and the comparison is
# made in code. Measured 2026-08-07 on three charts built from real agcu
# data (test_layer_c.py): correct chart passed; a chart with the y-range
# left to autoscale was caught reading 0.2-0.8 against the hard-set 0-1;
# a chart missing the LIQUID series was caught on both curve count and
# legend. 3/3, no false alarms.
#
# On by default since 2026-08-07. The cost is one vision-model call per
# chart; the layer degrades safely without one, since a model that cannot
# be reached or that answers outside the requested format is reported as
# such rather than being counted as agreement. Set
# OC_ENABLE_VISION_CHECK=0 to skip it.
VISION_CHECK_ENABLED = os.environ.get("OC_ENABLE_VISION_CHECK", "1") != "0"

_WEAK_INDEPENDENCE_MODELS = {
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
}
_pinned = os.environ.get("OC_VALIDATOR_MODEL", "")
VALIDATOR_MODELS = [_pinned] if _pinned else _DEFAULT_VALIDATOR_MODELS
VALIDATOR_MODEL = VALIDATOR_MODELS[0]  # kept for reporting/backwards use

class ValidationResult:
    def __init__(self, passed, layer, reason, details=None, available=True):
        self.passed = passed
        self.layer = layer  # "A" or "B" or "A+B"
        self.reason = reason
        self.details = details or {}
        # available=False means the layer could not form an opinion at all --
        # the model was unreachable, or answered outside the requested
        # format. That is a statement about the reviewer, not about the
        # result, so it must never gate: an overloaded API carries no
        # information about whether a phase equilibrium is correct. `passed`
        # is meaningless when this is False.
        self.available = available

    def __repr__(self):
        if not self.available:
            status = "DEGERLENDIRILEMEDI"
        else:
            status = "BASARILI" if self.passed else "BASARISIZ"
        return f"<ValidationResult {status} layer={self.layer}: {self.reason}>"


def verify_layer_a(case, result):
    """Deterministic checks. Always runs first, regardless of whether the
    case has a precise numeric reference."""
    structurally_ok, structural_problems = result_check.verify_result(result)
    if not structurally_ok:
        return ValidationResult(False, "A", "; ".join(structural_problems[:5]))

    if case["tool"] == "calculate_property_diagram":
        points = result.get("points", [])
        if not points:
            return ValidationResult(False, "A", "No points in property diagram result.")
        ok_points = [p for p in points if "error" not in p]
        if not ok_points:
            return ValidationResult(False, "A", "Every point in the property diagram errored.")
        if "backend_used" not in result:
            return ValidationResult(False, "A", "Missing 'backend_used' field.")

    expected = case.get("expected", {})
    if expected.get("structural_only"):
        return ValidationResult(True, "A", "Structural checks passed (no precise reference to compare).")

    # Precise-reference checks (calculate_equilibrium cases).
    if "gibbs_energy_J" in expected:
        ref = expected["gibbs_energy_J"]
        actual = result.get("gibbs_energy_J")
        if actual is None:
            return ValidationResult(False, "A", "Missing 'gibbs_energy_J' in result.")
        if abs(actual - ref["value"]) > ref["tolerance"]:
            return ValidationResult(
                False, "A",
                f"gibbs_energy_J={actual} outside tolerance of reference "
                f"{ref['value']} +/- {ref['tolerance']}",
            )

    if "phase_molar_amounts" in expected:
        actual_phases = result.get("phase_molar_amounts", {})
        for name, ref in expected["phase_molar_amounts"].items():
            actual_v = actual_phases.get(name)
            if actual_v is None:
                return ValidationResult(False, "A", f"Expected phase '{name}' not present in result.")
            if abs(actual_v - ref["value"]) > ref["tolerance"]:
                return ValidationResult(
                    False, "A",
                    f"phase '{name}'={actual_v} outside tolerance of reference "
                    f"{ref['value']} +/- {ref['tolerance']}",
                )

    return ValidationResult(True, "A", "All reference-value checks passed.")


def _post_once(model, prompt, timeout_s, image_b64=None):
    content = prompt if image_b64 is None else [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
    ]
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.0,
        "max_tokens": 500,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{NVIDIA_BASE_URL}/chat/completions",
        data=payload,
        headers={
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        body = json.loads(resp.read().decode("utf-8"))
    return body["choices"][0]["message"]["content"]


# HTTP 529 "Service temporarily overloaded" is the shared-capacity signal
# of the free tier, not a fault of any particular model or of the request
# -- it hit three separate runs of the verification loop in one session,
# on a request that succeeded seconds later unchanged. It says "not now,
# try again", so the correct response is to wait and retry, and only then
# move on to a different model.
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504, 529}


def _call_model_chain(models, prompt, timeout_s=60, image_b64=None):
    """Ask the first model in `models` that answers, riding out transient
    capacity errors.

    Retries each model with growing backoff before moving on. Raises only
    if every model exhausted its retries -- and then reports what each one
    said, so a failure here is diagnosable instead of just "it didn't
    work". Returns (reply_text, model_that_answered).
    """
    if not NVIDIA_API_KEY:
        raise RuntimeError(
            "NVIDIA_API_KEY is not set -- model-based validation cannot run. "
            "Set it in the environment first."
        )

    attempts = []
    for model in models:
        for delay in (0, 4, 10):
            if delay:
                time.sleep(delay)
            try:
                reply = _post_once(model, prompt, timeout_s, image_b64=image_b64)
            except urllib.error.HTTPError as exc:
                attempts.append(f"{model}: HTTP {exc.code}")
                if exc.code not in _TRANSIENT_HTTP_CODES:
                    break  # a real rejection (bad model name, auth) -- next model
                continue
            except Exception as exc:
                attempts.append(f"{model}: {type(exc).__name__}")
                continue
            if not reply:
                # Some models answer with content=None (observed on
                # step-3.7-flash) -- a successful HTTP call carrying no
                # text is no use as a review, so treat it as a failure of
                # that model rather than an empty verdict.
                attempts.append(f"{model}: empty response")
                break
            return reply, model
    raise RuntimeError("all models failed -> " + "; ".join(attempts))


def _call_validator_model(prompt, timeout_s=60):
    return _call_model_chain(VALIDATOR_MODELS, prompt, timeout_s)


_MARKER_RE = re.compile(r"SONUC\s*:\s*(BASARILI|BASARISIZ)", re.IGNORECASE)
_POSITIVE_WORDS = ("başarılı", "basarili", "tutarlı", "makul", "doğru", "pass")
_NEGATIVE_WORDS = ("başarısız", "basarisiz", "tutarsız", "mantıksız", "yanlış", "fail")


def _parse_validator_reply(reply_text):
    """Tolerant parsing: look for the exact 'SONUC: BASARILI/BASARISIZ'
    marker first (what the model is explicitly instructed to produce);
    if that's genuinely missing (models don't always follow format
    instructions -- this is exactly the failure mode that motivated
    designing this as a fallback chain rather than a single strict regex),
    fall back to keyword scanning; if still ambiguous, return None rather
    than guessing -- an inconclusive result must be visible, never
    silently coerced to pass or fail."""
    m = _MARKER_RE.search(reply_text)
    if m:
        return m.group(1).upper() == "BASARILI"
    lower = reply_text.lower()
    has_pos = any(w in lower for w in _POSITIVE_WORDS)
    has_neg = any(w in lower for w in _NEGATIVE_WORDS)
    if has_pos and not has_neg:
        return True
    if has_neg and not has_pos:
        return False
    return None


def verify_layer_b(case, result):
    """Independent model review, for cases where Layer A alone can't
    judge correctness (no precise reference value)."""
    prompt = (
        "Sen bir CALPHAD termodinamik hesap sonucunu denetleyen bağımsız bir "
        "doğrulayıcısın. Aşağıdaki hesap isteğini ve OpenCalphad motorundan "
        "dönen GERÇEK ham sonucu incele. Sonucun fiziksel olarak makul olup "
        "olmadığına karar ver (faz isimleri, sıcaklık aralığı, faz "
        "geçişlerinin genel davranışı ile tutarlı mı; hata/çökme/NaN var mı).\n\n"
        # Without this the reviewer flags ordinary IEEE-754 representation
        # (0.9999999999999999 for 1.0) as a convergence defect -- observed
        # on agcu.TDB, where every such "discrepancy" was ~1e-16, i.e. one
        # unit in the last place. Physical judgement is what's wanted here,
        # not float pedantry.
        "ÖNEMLİ: 0.9999999999999999 gibi değerler kayan nokta (floating "
        "point) gösteriminde tam olarak 1.0 demektir; bu bir yakınsama "
        "hatası DEĞİLDİR ve başarısızlık sebebi sayılmamalıdır. Yalnızca "
        "fiziksel olarak anlamlı sapmaları (yanlış faz, eksik geçiş, "
        "belirgin miktar hatası, hata/NaN) değerlendir.\n\n"
        f"İstek: {json.dumps(case['arguments'], ensure_ascii=False)}\n"
        f"Beklenen bağlam notu: {case.get('expected', {}).get('note', '(yok)')}\n\n"
        # 4000 was too aggressive: a full property_diagram result (100+
        # points) easily runs ~20-25k chars, and truncating mid-list cuts
        # off later temperatures before the model ever sees them --
        # confirmed directly causing a false BASARISIZ verdict on agcu.TDB
        # (truncation landed at T=1050.35K, right before the liquidus
        # transition at ~1056-1061K; the model correctly reported what it
        # was shown as incomplete, because it genuinely was). 40000 covers
        # every case size seen so far with real margin.
        f"Ham sonuç: {json.dumps(result, ensure_ascii=False)[:40000]}\n\n"
        "Cevabının İLK SATIRI tam olarak şu iki değerden biri olmalı, başka "
        "hiçbir şey içermemeli: 'SONUC: BASARILI' veya 'SONUC: BASARISIZ'. "
        "İkinci satırdan itibaren kısa gerekçeni yaz."
    )
    try:
        reply, model_used = _call_validator_model(prompt)
    except Exception as exc:
        return ValidationResult(False, "B", f"Validator model call failed: {exc}")

    details = {"raw_reply": reply, "model_used": model_used}
    # Say so when the verdict came from the same-family fallback rather
    # than a truly independent reviewer -- the whole point of Layer B is
    # independence, so a weaker one must be visible in the report.
    caveat = (
        f" [NOT: bu değerlendirme {model_used} ile yapıldı -- bu model, "
        "sunucuyu süren Nemotron ile aynı aileden, yani bağımsızlığı daha "
        "zayıf.]"
        if model_used in _WEAK_INDEPENDENCE_MODELS else ""
    )

    verdict = _parse_validator_reply(reply)
    if verdict is None:
        return ValidationResult(
            False, "B",
            "Validator model reply had no parseable SONUC marker or clear "
            f"keyword verdict (needs human review). Raw reply: {reply[:500]}"
            + caveat,
            details=details,
        )
    return ValidationResult(verdict, "B", reply.strip() + caveat, details=details)


def _independence_caveat(model_used):
    return (
        f" [NOT: bu değerlendirme {model_used} ile yapıldı -- bu model, "
        "sunucuyu süren Nemotron ile aynı aileden, yani bağımsızlığı daha "
        "zayıf.]"
        if model_used in _WEAK_INDEPENDENCE_MODELS else ""
    )


_CHART_FIELD_RE = re.compile(
    r"^\s*(CURVES|LEGEND|YMIN|YMAX|XMIN|XMAX)\s*[:=]\s*(.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")


def _as_float(text):
    """First number in a free-text answer, or None.

    The model is asked for a bare number but may write "800 K" or "0,2";
    anything with no number at all stays None so the caller can report the
    field unreadable rather than inventing a value.
    """
    match = _NUMBER_RE.search(text or "")
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "."))
    except ValueError:
        return None


def chart_ground_truth(result):
    """What the plotting layer was asked to draw.

    This is the half of the comparison the code already knows for certain:
    the series it handed to gnuplot, the temperature span of the data, and
    the y-range render_gnuplot_png hard-sets. Returns None when the result
    carries no plottable series, so the caller can skip rather than guess.
    """
    points = result.get("points") or []
    names = []
    temperatures = []
    for point in points:
        temperature = point.get("temperature_K")
        if isinstance(temperature, (int, float)):
            temperatures.append(float(temperature))
        for name in (point.get("phase_molar_amounts") or {}):
            if name not in names:
                names.append(name)
    if not names or not temperatures:
        return None
    return {
        "series": len(names),
        "legend": names,
        # render_gnuplot_png emits `set yrange [0:1]` unconditionally, so
        # anything else in the image means gnuplot ignored the setting.
        "y_min": 0.0,
        "y_max": 1.0,
        "x_min": min(temperatures),
        "x_max": max(temperatures),
    }


def _compare_chart_reading(reading, truth):
    """Model's reading of the image against what was plotted.

    Returns (mismatches, unreadable). A field the model did not answer in
    a parseable form goes to `unreadable` -- it is not evidence either way
    and must not be scored as agreement.
    """
    mismatches = []
    unreadable = []

    raw_curves = reading.get("curves")
    curves = _as_float(raw_curves) if raw_curves is not None else None
    if curves is None:
        unreadable.append("curve count")
    elif int(curves) != truth["series"]:
        mismatches.append(
            f"curve count: image shows {int(curves)}, data has {truth['series']}"
        )

    raw_legend = reading.get("legend")
    if not raw_legend:
        unreadable.append("legend entries")
    else:
        seen = sorted(
            part.strip().upper()
            for part in re.split(r"[|;,\n]", raw_legend)
            if part.strip()
        )
        expected = sorted(name.strip().upper() for name in truth["legend"])
        if seen != expected:
            mismatches.append(
                f"legend entries: image shows {seen}, data has {expected}"
            )

    # The y-range is hard-set by render_gnuplot_png, so the image must match
    # it closely; anything else means gnuplot ignored the setting.
    for key, truth_key, label in (
        ("ymin", "y_min", "y-axis lower bound"),
        ("ymax", "y_max", "y-axis upper bound"),
    ):
        value = _as_float(reading.get(key))
        if value is None:
            unreadable.append(label)
        elif abs(value - truth[truth_key]) > 0.05:
            mismatches.append(
                f"{label}: image shows {value:g}, data has {truth[truth_key]:g}"
            )

    # The x-range is autoscaled, and gnuplot rounds its bounds outward to
    # round tick values -- data ending at 1040 legitimately draws an axis to
    # 1050. So the test is containment, not equality: the axis must cover the
    # data (anything narrower cuts points off, which is a real defect) without
    # being absurdly wider than it.
    span = truth["x_max"] - truth["x_min"]
    slack = max(2.0, 0.15 * span)
    x_min = _as_float(reading.get("xmin"))
    if x_min is None:
        unreadable.append("x-axis lower bound")
    elif x_min > truth["x_min"] + 2.0:
        mismatches.append(
            f"x-axis starts at {x_min:g}, after the first data point "
            f"at {truth['x_min']:g} -- points are cut off"
        )
    elif truth["x_min"] - x_min > slack:
        mismatches.append(
            f"x-axis starts at {x_min:g}, far below the data's "
            f"{truth['x_min']:g}"
        )

    x_max = _as_float(reading.get("xmax"))
    if x_max is None:
        unreadable.append("x-axis upper bound")
    elif x_max < truth["x_max"] - 2.0:
        mismatches.append(
            f"x-axis ends at {x_max:g}, before the last data point "
            f"at {truth['x_max']:g} -- points are cut off"
        )
    elif x_max - truth["x_max"] > slack:
        mismatches.append(
            f"x-axis ends at {x_max:g}, far beyond the data's "
            f"{truth['x_max']:g}"
        )

    return mismatches, unreadable


def verify_layer_c(case, result):
    """Does the rendered chart match the data it was drawn from?

    Layers A and B both reason about numbers. The chart is a separate
    artifact produced from those numbers and can disagree with them while
    the numbers stay correct -- gnuplot ignoring the y-range, a series that
    never got drawn, a legend box covering the plot, an empty PNG. No
    numeric layer can see any of that, because the numbers are right.

    The model is therefore asked only for OBSERVATIONS -- how many curves,
    which legend entries, where the axes start and end -- each of which has
    exactly one correct answer that `chart_ground_truth` already holds. The
    comparison, and the verdict, are made by code.

    What this deliberately does NOT ask: whether the plot is "correct".
    That question needs CALPHAD knowledge the model does not have, and it
    is the question an earlier version of this layer got wrong in both
    directions. Defects that live in the DATA rather than the rendering --
    the same phase carried under two spellings, for instance -- belong to
    the merging layer's own validation, not here: the data would be wrong
    on both sides of this comparison and the two would agree.

    Returns None when there is no chart to look at, so the caller can tell
    "nothing to review" apart from "reviewed and rejected".
    """
    image_b64 = result.get("_chart_png_base64")
    if not image_b64:
        return None

    truth = chart_ground_truth(result)
    if truth is None:
        return None

    prompt = (
        "Sana bir çizgi grafiğin görüntüsü veriliyor. Görevin SADECE ne "
        "gördüğünü bildirmek. Değerlendirme yapma, yorum yapma, doğru mu "
        "yanlış mı deme.\n\n"
        "Tam olarak şu altı satırı, bu sırayla, başka hiçbir şey eklemeden "
        "yaz:\n"
        "CURVES: <efsanede kaç ayrı seri var, sadece sayı>\n"
        "LEGEND: <efsanedeki isimler, aynen yazıldığı gibi, aralarına | koy>\n"
        "YMIN: <y ekseninin en alt etiketi, sadece sayı>\n"
        "YMAX: <y ekseninin en üst etiketi, sadece sayı>\n"
        "XMIN: <x ekseninin en sol etiketi, sadece sayı>\n"
        "XMAX: <x ekseninin en sağ etiketi, sadece sayı>\n\n"
        "Bir değeri okuyamıyorsan o satıra sadece BILINMIYOR yaz. Tahmin "
        "etme."
    )

    try:
        reply, model_used = _call_model_chain(
            VISION_MODELS, prompt, timeout_s=90, image_b64=image_b64
        )
    except Exception as exc:
        # Not reachable is not an objection. The chart may be perfect; we
        # simply have no reading of it.
        return ValidationResult(
            True, "C", f"No vision model could be reached ({exc}), so the "
            "chart was not checked.", available=False,
        )

    reading = {
        match.group(1).lower(): match.group(2)
        for match in _CHART_FIELD_RE.finditer(reply)
    }
    for key, value in list(reading.items()):
        if "BILINMIYOR" in value.upper() or "BİLİNMİYOR" in value.upper():
            reading.pop(key)

    details = {
        "raw_reply": reply,
        "model_used": model_used,
        "reading": reading,
        "ground_truth": truth,
    }
    caveat = _independence_caveat(model_used)

    if not reading:
        # Same category as unreachable: the reviewer produced no reading, so
        # there is nothing to compare. Guessing a verdict from prose would
        # invent information that does not exist.
        return ValidationResult(
            True, "C",
            "Vision model returned nothing in the requested format, so the "
            f"chart was not checked. Raw reply: {reply[:500]}" + caveat,
            details=details, available=False,
        )

    mismatches, unreadable = _compare_chart_reading(reading, truth)
    note = f" ({len(unreadable)} field(s) unreadable: {', '.join(unreadable)})" \
        if unreadable else ""

    if mismatches:
        return ValidationResult(
            False, "C",
            "Rendered chart disagrees with the data it was drawn from: "
            + "; ".join(mismatches) + note + caveat,
            details=details,
        )
    return ValidationResult(
        True, "C",
        f"Rendered chart matches the plotted data on "
        f"{6 - len(unreadable)}/6 checked features{note}." + caveat,
        details=details,
    )


def verify(case, result):
    """Full VERIFY step.

    Layer A (deterministic) always runs and can reject on its own. Layer B
    (independent model, numbers) runs only when there is no precise
    reference to compare against -- with a reference, arithmetic already
    settles it and a model opinion adds nothing. Layer C (vision) runs
    whenever a chart was produced, since a chart can be wrong in ways the
    numbers can't show.

    Without NVIDIA_API_KEY both model layers are skipped and Layer A's
    verdict stands alone -- said out loud in the reason, never hidden.
    """
    layer_a = verify_layer_a(case, result)
    if not layer_a.passed:
        return layer_a

    needs_layer_b = bool(case.get("expected", {}).get("structural_only"))
    run_layer_c = VISION_CHECK_ENABLED and bool(result.get("_chart_png_base64"))

    if not needs_layer_b and not run_layer_c:
        return layer_a

    if not NVIDIA_API_KEY:
        return ValidationResult(
            True, "A",
            layer_a.reason + " (Layers B/C skipped: NVIDIA_API_KEY not set.)",
        )

    reasons = [f"Layer A: {layer_a.reason}"]
    passed = True
    details = {}

    if needs_layer_b:
        layer_b = verify_layer_b(case, result)
        reasons.append(f"Layer B: {layer_b.reason}")
        passed = passed and layer_b.passed
        details["layer_b"] = layer_b.details

    layer_c_ran = False
    if run_layer_c:
        layer_c = verify_layer_c(case, result)
        if layer_c is not None:
            reasons.append(f"Layer C: {layer_c.reason}")
            details["layer_c"] = layer_c.details
            # An unavailable reviewer does not gate -- see ValidationResult.
            if layer_c.available:
                passed = passed and layer_c.passed
                layer_c_ran = True

    layers = "A" + ("+B" if needs_layer_b else "") + ("+C" if layer_c_ran else "")
    return ValidationResult(passed, layers, " | ".join(reasons), details=details)
