"""DEBUGGER: give a verification failure a type, and say what -- if
anything -- can be done about it automatically.

Until now a failed check produced a sentence. A sentence is fine for a
human reading one result, but it forces every downstream consumer (the
client model, the verification loop, anything built on this API) to
re-derive the failure's nature from prose. This module turns the sentence
into a category plus an explicit recovery strategy, so the decision is
made once, here, by code that can see all the failure classes at once.

The strategies are deliberately narrow, and the reason matters: most
failure classes have NO honest automatic recovery.

  - A convergence failure has already been through the whole engine
    cascade by the time verification runs. Retrying runs the same
    deterministic calculation again and gets the same answer.
  - A malformed result (fractions that don't sum to one, NaN) is a defect
    in the normalization layer, not a transient. Retrying hides it.
  - Insufficient coverage could be "fixed" by narrowing the range or
    dropping points -- but that answers a different question than the one
    asked, which is exactly the failure mode this project refuses
    elsewhere (see server.py's PREFLIGHT stop rule).

What genuinely can be retried is the REVIEW, not the calculation: an
unreadable verdict or an unreachable reviewer says nothing about the
chemistry and everything about which model happened to answer. So the
only automatic strategy here re-runs Layer B against the next model in
the chain, leaving the numbers untouched.
"""

# Kategori -> (otomatik strateji, kullaniciya oneri)
# strateji None ise otomatik yapilabilecek bir sey yok demektir.
PREFLIGHT = "preflight_rejected"
CONVERGENCE = "convergence"
COVERAGE = "coverage"
MALFORMED = "malformed_result"
ENGINE = "engine_error"
SEMANTIC = "semantic_objection"
REVIEWER_UNREADABLE = "reviewer_unreadable"
REVIEWER_UNREACHABLE = "reviewer_unreachable"
UNKNOWN = "unknown"

STRATEGY_RETRY_REVIEWER = "retry_reviewer_with_next_model"

_TABLE = {
    PREFLIGHT: (
        None,
        "İstek motora hiç gönderilmedi. Hata mesajındaki geçerli "
        "element/faz listesine göre isteği düzeltin.",
    ),
    CONVERGENCE: (
        None,
        "Motor bu koşulda yakınsayamadı ve tüm kademeler denendi. "
        "Farklı bir sıcaklık veya bileşim gerekebilir.",
    ),
    COVERAGE: (
        None,
        "Taramanın bir kısmı yakınsamadı. Hesaplanan noktalar geçerlidir; "
        "eksik bölge için daha dar bir aralık deneyebilirsiniz.",
    ),
    MALFORMED: (
        None,
        "Sonuç yapısal olarak tutarsız. Bu bir hesap zorluğu değil, "
        "birleştirme/normalizasyon katmanında incelenmesi gereken bir durum.",
    ),
    ENGINE: (
        None,
        "Motor hesabı tamamlayamadı. Hata metni sonuçta korunmuştur.",
    ),
    SEMANTIC: (
        None,
        "Bağımsız değerlendirici sonucu fiziksel olarak makul bulmadı. "
        "Gerekçe sonuçta yer alıyor; insan incelemesi önerilir.",
    ),
    REVIEWER_UNREADABLE: (
        STRATEGY_RETRY_REVIEWER,
        "Değerlendiricinin cevabından net bir karar çıkmadı; "
        "zincirdeki sonraki modele soruldu.",
    ),
    REVIEWER_UNREACHABLE: (
        STRATEGY_RETRY_REVIEWER,
        "Değerlendiriciye ulaşılamadı; zincirdeki sonraki modele soruldu. "
        "Bu, hesabın hatalı olduğu anlamına GELMEZ.",
    ),
    UNKNOWN: (
        None,
        "Başarısızlık sınıflandırılamadı; ham gerekçe sonuçta yer alıyor.",
    ),
}

_COVERAGE_MARK = "failed to converge"
_MALFORMED_MARKS = ("sum to", "is NaN", "outside [0,1]")
_CONVERGENCE_MARKS = ("did not converge", "error code 4204", "error code 4187")


def classify(result):
    """Return a typed failure record, or None when nothing failed.

    Reads only what the result already carries -- no re-running, no
    guessing. Order matters: the most specific signal wins, so a
    reviewer problem is never reported as a generic engine error.
    """
    if not isinstance(result, dict):
        return None

    if result.get("stage") == "PREFLIGHT":
        return _record(PREFLIGHT, result.get("problems") or [result.get("error", "")])

    ver = result.get("verification") or {}
    layer_b = ver.get("layer_b") or {}

    # Layer B durumlari once: bunlar hesap hakkinda degil, denetim
    # hakkindadir ve tek otomatik olarak duzeltilebilir siniftir.
    if layer_b:
        if layer_b.get("available") is False:
            return _record(REVIEWER_UNREACHABLE, [layer_b.get("reason", "")])
        if layer_b.get("available") and layer_b.get("passed") is None:
            return _record(REVIEWER_UNREADABLE, [layer_b.get("reason", "")])

    if ver.get("passed") is True:
        return None

    problems = ver.get("problems") or []
    blob = " ".join(str(p) for p in problems)

    if layer_b.get("passed") is False:
        return _record(SEMANTIC, problems)
    if _COVERAGE_MARK in blob:
        return _record(COVERAGE, problems)
    if any(m in blob for m in _MALFORMED_MARKS):
        return _record(MALFORMED, problems)
    if any(m in blob for m in _CONVERGENCE_MARKS) or result.get("error"):
        return _record(CONVERGENCE if any(m in blob for m in _CONVERGENCE_MARKS)
                       else ENGINE, problems or [result.get("error", "")])
    if problems:
        return _record(UNKNOWN, problems)
    return None


def _record(category, problems):
    strategy, advice = _TABLE[category]
    return {
        "category": category,
        "retryable": strategy is not None,
        "strategy": strategy,
        "user_action": advice,
        "problems": [str(p)[:400] for p in problems if p],
    }
