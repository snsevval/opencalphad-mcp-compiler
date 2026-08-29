"""VERIFY B (semantic): ask an independent model whether a finished
calculation is physically plausible.

Layer A (result_check.py) can prove a result is malformed -- fractions
that don't sum to one, NaN, points that failed to converge. What it
cannot do is notice that a well-formed result describes something that
never happens in nature. That judgement is what this layer buys, and it
has to come from a model that did NOT produce the request: the point is a
second opinion, so the reviewer is chosen from a different model family
than the Nemotron that normally drives this server.

Lives at the project root, not under verification/, because both the live
MCP server and the verification loop use it -- production must not depend
on the test harness (same reasoning as result_check.py).

Reachability is treated as separate from the verdict. The free tier
returns HTTP 529 "overloaded" unpredictably, and a review that could not
be obtained is NOT evidence that a calculation is wrong. review() says so
explicitly via `available`, so a caller can distinguish "the reviewer
looked and objected" from "no reviewer was reachable" -- conflating those
would turn NVIDIA's capacity into false alarms about the user's
chemistry.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"

# Measured 2026-08-03, 3 calls each against a short validation prompt:
#   deepseek-v4-flash   2/3 ok, ~12s   <- only dependable independent one
#   step-3.7-flash      2/3 ok but returns content=None (unusable shape)
#   glm-5.2 / minimax-m3 / mistral-medium-3.5 / gemma-4-31b  0/3, timeouts
#   kimi-k2.6           0/3, HTTP 404 (not enabled for this account)
# nemotron-3-super is last resort: it answers reliably but shares a family
# with the Nemotron driving this server, so its verdict is a WEAKER kind
# of independence -- review() reports which model answered so that is
# never passed off as the independent review.
#
# 2026-08-19: the unversioned alias started returning HTTP 410 Gone; the
# catalogue now lists a dated id instead. A dated id will age too, so the
# failure to plan for is the reviewer disappearing, not this particular
# name -- which is what `available` already handles: the chain went dead
# for two weeks and no calculation was ever reported as wrong for it.
# 2026-08-26: deepseek-v4-flash-0731 katalogda duruyor ama
# /chat/completions'a 404 donuyor -- yani zincir her istekte sessizce
# ikinci siraya, Nemotron ailesine dusuyordu. Olculdu: 46 vakada
# degerlendiren model HER ZAMAN nemotron-super'di, ve DEBUGGER'in
# "baska bir modele sor" adimi da bu yuzden gidecek yer bulamiyordu
# (available=False). Yani "bagimsiz denetim" katmani, aylardir sunucuyu
# suren modelin akrabasina soruyordu.
#
# Bu anahtarda gercekten cevap veren tek YABANCI aile: openai/gpt-oss-120b
# (olculdu; glm5/kimi/qwen/llama-4/mistral-large hepsi 404 ya da 410).
#
# Ama once birinci siraya konuldu ve olculdu -- gercek bir degerlendirme
# istemine cevap suresi kararsiz:
#
#     tek satirlik istem            2.4 s      cevap verdi
#     gercek degerlendirme istemi   3 denemede 240 s'de zaman asimi
#     ayni istem, baska bir turda   ~150 s     cevap verdi (5 vakanin 3'u)
#
# Yani bagimsiz ama guvenilmez ve yavas. Bloklayan yola konursa her hesaba
# once bir bekleme, sonra zaten Nemotron'a dusme ekliyor: hem yavas hem
# yine zayif bagimsiz. Bu yuzden varsayilan hizli ve guvenilir olan;
# gercek bagimsiz denetim isteniyorsa acikca secilir:
#
#     OC_VALIDATOR_MODEL=openai/gpt-oss-120b
#
# Zayif bagimsizlik gizlenmiyor -- independence_note her cevaba iliskiyor,
# ve WEAK_INDEPENDENCE_MODELS bunu makine tarafindan da okunur kiliyor.
_DEFAULT_MODELS = [
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
]

# Gercek bagimsizlik icin kullanilabilecek, olculmus calisan model(ler).
# Zincirde degil, cunku gecikmesi ongorulemiyor; belgede degil, burada,
# cunku bir dahaki sefere aranacak yer burasi.
INDEPENDENT_MODELS = ["openai/gpt-oss-120b"]
_pinned = os.environ.get("OC_VALIDATOR_MODEL", "")
MODELS = [_pinned] if _pinned else _DEFAULT_MODELS

WEAK_INDEPENDENCE_MODELS = {
    "nvidia/nemotron-3-super-120b-a12b",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning",
    "nvidia/nemotron-3.5-lightning-30b-a3b",
}

# 529 is the free tier's shared-capacity signal -- it hit three separate
# loop runs in one session on requests that succeeded seconds later
# unchanged. It means "not now", so wait and retry before moving on.
_TRANSIENT_HTTP_CODES = {429, 500, 502, 503, 504, 529}


def post_once(model, prompt, timeout_s, image_b64=None):
    content = prompt if image_b64 is None else [
        {"type": "text", "text": prompt},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{image_b64}"}},
    ]
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "temperature": 0.0,
        # The prompt asks for reasoning first and the verdict on the last
        # line, so the budget has to cover the reasoning or the verdict is
        # never reached. At 500 a reviewer that opened by converting at%
        # to wt% -- arithmetic that bears on nothing here -- ran out
        # mid-sum and returned no decision at all, which the DEBUGGER then
        # correctly classified as unreadable. The two design choices were
        # fighting each other; this settles it in favour of the one that
        # was there for a measured reason.
        # 2026-08-26, ucuncu tur: 1500 de yetmiyordu. Olculdu -- iki ayri
        # vakada cevap tam ortasinda kesilmisti ("...eutektoid sicakligi
        # 727C (" ve "...0.812754; "), yani muhakeme butceyi yiyip SONUC
        # satirina hic varamamisti. Istenen sey son satirda oldugu icin
        # kesilen tek sey tam da ihtiyac duyulan seydi.
        #
        # Butceyi buyutmek tek basina yetmez: bir dahaki sefere daha uzun
        # dusunen bir model gelir. Asil duzeltme asagida, finish_reason'i
        # okumak -- boylece "karar okunamadi" ile "hakem butceyi bitirdi"
        # ayri iki durum olarak raporlanir.
        "max_tokens": 4000,
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
    choice = body["choices"][0]
    # finish_reason "length" means the reply stopped because the budget
    # ran out, not because the model was done. Returned alongside the text
    # so a truncated review is reported as truncated rather than as a
    # reviewer who had no opinion -- two different problems needing two
    # different responses.
    return choice["message"]["content"], choice.get("finish_reason")


def call_model_chain(models, prompt, timeout_s=60, image_b64=None,
                     retries=(0, 4, 10), deadline=None):
    """Ask the first model that answers. Returns (reply, model_used,
    finish_reason).

    Raises only when every model exhausted its retries, and then names
    what each one did -- a failure here should be diagnosable, not just
    "it didn't work".
    """
    if not NVIDIA_API_KEY:
        raise RuntimeError("NVIDIA_API_KEY is not set.")

    attempts = []
    for model in models:
        for delay in retries:
            # Every attempt had its own timeout and their sum had none.
            # Checked before sleeping and before dialling, so a stage that
            # has run out of time stops rather than starting one more
            # sixty-second wait it cannot afford.
            if deadline is not None and time.time() >= deadline:
                attempts.append("deadline reached")
                raise RuntimeError("review deadline reached -> "
                                   + "; ".join(attempts))
            if delay:
                if deadline is not None and time.time() + delay >= deadline:
                    attempts.append("deadline would pass during backoff")
                    raise RuntimeError("review deadline reached -> "
                                       + "; ".join(attempts))
                time.sleep(delay)
            try:
                budget = timeout_s
                if deadline is not None:
                    budget = max(1, min(timeout_s, int(deadline - time.time())))
                reply, finish_reason = post_once(
                    model, prompt, budget, image_b64=image_b64)
            except urllib.error.HTTPError as exc:
                attempts.append(f"{model}: HTTP {exc.code}")
                if exc.code not in _TRANSIENT_HTTP_CODES:
                    break  # real rejection (bad model, auth) -- try next model
                continue
            except Exception as exc:
                attempts.append(f"{model}: {type(exc).__name__}")
                continue
            if not reply:
                # Observed on step-3.7-flash: HTTP 200 with content=None.
                # A successful call carrying no text is no review at all.
                attempts.append(f"{model}: empty response")
                break
            return reply, model, finish_reason
    raise RuntimeError("all models failed -> " + "; ".join(attempts))


_MARKER_RE = re.compile(r"SONUC\s*:\s*(BASARILI|BASARISIZ)", re.IGNORECASE)
_POSITIVE_WORDS = ("başarılı", "basarili", "tutarlı", "makul", "doğru", "pass")
_NEGATIVE_WORDS = ("başarısız", "basarisiz", "tutarsız", "mantıksız", "yanlış", "fail")


def parse_verdict(reply_text):
    """Read a verdict out of the reply.

    Prefers the exact marker the model was told to emit; falls back to
    keyword scanning when it didn't follow the format (models often
    don't); returns None when genuinely ambiguous rather than guessing --
    an inconclusive review must stay visible, never be quietly rounded to
    pass or fail.

    Takes the LAST marker, not the first. build_prompt asks for the verdict
    after the reasoning, so the final marker is the reviewed one; a marker
    appearing earlier is either a restatement or -- as seen live -- a guess
    the model made before working through the result.
    """
    last = None
    for last in _MARKER_RE.finditer(reply_text):
        pass
    if last is not None:
        verdict = last.group(1).upper() == "BASARILI"
        # Safety net for a marker its own reasoning contradicts. With the
        # verdict asked for last, anything after it is normally empty and
        # this does nothing. It matters when a model emits the marker
        # early anyway and then argues the other way -- the live steel1
        # case. A contradicted verdict is downgraded to "unreadable", never
        # flipped: we do not know which half the reviewer meant, and
        # guessing either way is exactly what this function refuses to do.
        tail = reply_text[last.end():].lower()
        if tail.strip():
            has_pos = any(w in tail for w in _POSITIVE_WORDS)
            has_neg = any(w in tail for w in _NEGATIVE_WORDS)
            if verdict and has_neg and not has_pos:
                return None
            if not verdict and has_pos and not has_neg:
                return None
        return verdict
    lower = reply_text.lower()
    has_pos = any(w in lower for w in _POSITIVE_WORDS)
    has_neg = any(w in lower for w in _NEGATIVE_WORDS)
    if has_pos and not has_neg:
        return True
    if has_neg and not has_pos:
        return False
    return None


def build_prompt(request_args, result, context_note=None):
    return (
        "Sen bir CALPHAD termodinamik hesap sonucunu denetleyen bağımsız bir "
        "doğrulayıcısın. Aşağıdaki hesap isteğini ve OpenCalphad motorundan "
        "dönen GERÇEK ham sonucu incele. Sonucun fiziksel olarak makul olup "
        "olmadığına karar ver (faz isimleri, sıcaklık aralığı, faz "
        "geçişlerinin genel davranışı ile tutarlı mı; hata/çökme/NaN var mı).\n\n"
        # Without this the reviewer flags ordinary IEEE-754 representation
        # (0.9999999999999999 for 1.0) as a convergence defect -- observed
        # on agcu.TDB, where every such "discrepancy" was one unit in the
        # last place. Physical judgement is wanted here, not float pedantry.
        "ÖNEMLİ: 0.9999999999999999 gibi değerler kayan nokta (floating "
        "point) gösteriminde tam olarak 1.0 demektir; bu bir yakınsama "
        "hatası DEĞİLDİR ve başarısızlık sebebi sayılmamalıdır. Yalnızca "
        "fiziksel olarak anlamlı sapmaları (yanlış faz, eksik geçiş, "
        "belirgin miktar hatası, hata/NaN) değerlendir.\n\n"
        # Without this the reviewer reads our own bookkeeping as a failure:
        # observed live on steel1 1200K, where it saw fallback_reason's
        # "did not converge (error code 4204)" -- the record of OCASI
        # giving up before the native engine succeeded -- and declared the
        # (correct) result failed. The fields describe how the answer was
        # reached, not whether it is right.
        "ALAN AÇIKLAMALARI: 'backend_used' hangi motorun kullanıldığını, "
        "'fallback_reason' ise ilk denenen motorun neden bırakılıp yedeğe "
        "geçildiğini anlatır. fallback_reason içinde bir hata metni "
        "bulunması, NİHAİ sonucun hatalı olduğu anlamına GELMEZ -- sonuç o "
        "noktada zaten yedek motorla başarıyla hesaplanmıştır. Gerçek "
        "başarısızlık, sonucun kendisinde 'error' alanı olması ya da "
        "fiziksel olarak tutarsız değerler bulunmasıdır.\n\n"
        f"İstek: {json.dumps(request_args, ensure_ascii=False)}\n"
        f"Beklenen bağlam notu: {context_note or '(yok)'}\n\n"
        # 4000 chars was too tight: a full property_diagram result runs
        # ~20-25k, and truncating mid-list hides later temperatures from
        # the reviewer entirely -- that directly caused a false BASARISIZ
        # on agcu.TDB, where the cut landed just before the liquidus.
        f"Ham sonuç: {json.dumps(result, ensure_ascii=False, default=str)[:40000]}\n\n"
        # Verdict LAST, not first. Asking for the marker up front makes the
        # reviewer commit before it has reasoned, and it does not go back to
        # fix the marker when the reasoning lands elsewhere: observed live on
        # steel1 with GRAPHITE suspended, where deepseek-v4-flash opened with
        # "SONUC: BASARISIZ" and closed with "Sonuç fiziksel olarak tutarlıdır
        # ve başarılı kabul edilmelidir" -- a correct calculation flagged as
        # failed by our own prompt design. Reasoning first, then the marker.
        "Önce kısa gerekçeni yaz: hangi noktalara baktın, ne buldun.\n"
        "Muhakemeni TAMAMLADIKTAN SONRA, cevabının SON SATIRI tam olarak şu "
        "iki değerden biri olmalı ve başka hiçbir şey içermemeli:\n"
        "SONUC: BASARILI\n"
        "SONUC: BASARISIZ\n"
        "Bu satırı gerekçenden önce yazma; vardığın sonucu yansıtsın."
    )


def independence_note(model_used):
    """Text to append when the verdict came from the same-family fallback
    instead of a genuinely independent reviewer. Layer B exists to be
    independent, so a weaker version of it has to be visible."""
    if model_used in WEAK_INDEPENDENCE_MODELS:
        return (
            f" [NOT: bu değerlendirme {model_used} ile yapıldı -- bu model, "
            "sunucuyu süren Nemotron ile aynı aileden, yani bağımsızlığı "
            "daha zayıf.]"
        )
    return ""


def review(request_args, result, context_note=None, timeout_s=60, retries=(0, 4),
           skip_models=(), deadline=None):
    """Ask an independent model to judge a result's physical plausibility.

    Returns a dict. `available` says whether a review was actually
    obtained; only when it is True does `passed` mean anything. Callers on
    the live request path must not treat available=False as a bad result
    -- it means no reviewer answered, which says nothing about the
    chemistry.

    skip_models: models already tried that produced no usable verdict (an
    unreadable answer, or no answer at all). The DEBUGGER stage passes
    these so the rest of the chain gets asked instead. Only the REVIEW is
    repeated -- the calculation is never re-run, because it is
    deterministic and would return the same numbers.
    """
    if not NVIDIA_API_KEY:
        return {
            "available": False,
            "reason": "NVIDIA_API_KEY tanımlı değil, bağımsız model denetimi yapılamadı.",
        }

    models = [m for m in MODELS if m not in set(skip_models)]
    if not models:
        return {
            "available": False,
            "reason": ("Zincirdeki tüm değerlendirici modeller denendi, "
                       "kullanılabilir karar alınamadı: " + ", ".join(skip_models)),
        }

    prompt = build_prompt(request_args, result, context_note)
    try:
        reply, model_used, finish_reason = call_model_chain(
            models, prompt, timeout_s=timeout_s, retries=retries,
            deadline=deadline,
        )
    except Exception as exc:
        return {
            "available": False,
            "reason": f"Bağımsız model denetimi yapılamadı (model erişilemedi): {exc}",
        }

    note = independence_note(model_used)
    verdict = parse_verdict(reply)
    if verdict is None:
        # Half-finished reasoning is not a finding, and handing it to the
        # caller reads as one. What the caller needs is WHY there is no
        # verdict; the text itself only matters for diagnosis, so it is
        # carried separately and labelled, never inlined into "reason".
        if finish_reason == "length":
            why = (f"Bağımsız denetim tamamlanamadı: değerlendirici model "
                   f"({model_used}) yanıt bütçesini muhakemeyle doldurdu ve "
                   f"karar satırına ulaşamadı. Hesap sonucu hakkında bir şey "
                   f"söylemiyor.")
        else:
            why = (f"Bağımsız denetim sonuçsuz: değerlendirici model "
                   f"({model_used}) okunabilir bir SONUC satırı vermedi. "
                   f"Hesap sonucu hakkında bir şey söylemiyor.")
        return {
            "available": True,
            "passed": None,  # reviewed, but the verdict couldn't be read
            "model_used": model_used,
            "finish_reason": finish_reason,
            "reason": why + note,
            "unreadable_reply_excerpt": reply.strip()[-300:],
        }
    return {
        "available": True,
        "passed": verdict,
        "model_used": model_used,
        "finish_reason": finish_reason,
        "reason": reply.strip() + note,
    }
