"""Append-only record of every tool call and what it returned.

Why this exists
---------------
Repeatedly, judging an answer came down to one question: was the number
the caller reported actually IN the payload we handed it, or did it come
from somewhere else? Three separate cases (1.22, 1.27, 1.28) stalled on
exactly that, and each was settled only by re-running the calculation by
hand afterwards -- which answers "what does the tool return NOW", not
"what did it return THEN". The two differ whenever the engine is
non-deterministic at the margins, which this one is: the same request has
come back through the native STEP path with 215 points and through the
fallback with 100.

One of those hand re-runs (1.27) overturned the verdict: the anomaly the
caller was accused of inventing was in the output all along. That is the
cost of not having this file.

So the payload is written down as it goes out. Nothing else in the server
reads it; it exists to be read by a person afterwards.

Design constraints
------------------
Logging must never change what the caller receives. Every failure here --
unwritable directory, full disk, an object that will not serialize -- is
swallowed, because a calculation that succeeded must not be turned into a
failure by its own bookkeeping.

Written as JSON Lines so a truncated or interleaved write costs one
record rather than the file.
"""

import datetime
import json
import os
import threading

HERE = os.path.dirname(os.path.abspath(__file__))

LOG_PATH = os.environ.get(
    "OC_CALL_LOG", os.path.join(HERE, "logs", "calls.jsonl")
)

# Kept generous on purpose: a property diagram payload is ~40 KB, so this
# is a few hundred runs' worth. The point is a bound, not a small file --
# an investigation two weeks later needs the old records to still be there.
MAX_BYTES = int(os.environ.get("OC_CALL_LOG_MAX_BYTES", str(200 * 1024 * 1024)))

# Enabled by default. A record that has to be switched on before it is
# needed is not there when it is needed -- that is the situation this
# module exists to end.
ENABLED = os.environ.get("OC_CALL_LOG_ENABLED", "1") != "0"

_lock = threading.Lock()


def _rotate_if_needed(path):
    """Keep at most two generations. Old records matter, but not without
    bound; one rollover keeps roughly twice MAX_BYTES on disk."""
    try:
        if os.path.getsize(path) < MAX_BYTES:
            return
    except OSError:
        return
    previous = path + ".1"
    try:
        if os.path.exists(previous):
            os.remove(previous)
        os.replace(path, previous)
    except OSError:
        pass


def _serializable(value):
    """Turn a tool return into something JSON can hold.

    Image parts are recorded by size only. The bytes answer no question a
    person would come here to ask, and inlining them would bury the text
    that does under a megabyte of base64.
    """
    if isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(item)
            else:
                data = getattr(item, "data", None)
                parts.append({
                    "_non_dict_part": type(item).__name__,
                    "_bytes": len(data) if data is not None else None,
                })
        return parts
    return value


def record(tool, arguments, result):
    """Append one call. Returns nothing and raises nothing."""
    if not ENABLED:
        return
    try:
        payload = _serializable(result)
        line = json.dumps(
            {
                "at": datetime.datetime.now(datetime.timezone.utc)
                .isoformat(timespec="seconds"),
                "tool": tool,
                "arguments": arguments,
                "result": payload,
            },
            ensure_ascii=False,
            default=str,   # anything exotic degrades to its repr, never raises
        )
    except Exception:
        return
    try:
        with _lock:
            os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
            _rotate_if_needed(LOG_PATH)
            with open(LOG_PATH, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
    except Exception:
        return


def logged(function):
    """Decorator recording a tool's arguments and its return.

    Applied BELOW @mcp.tool() so the framework still introspects the real
    function: functools.wraps sets __wrapped__, which inspect.signature
    follows, so the generated schema is unchanged. Verified against the
    live tool listing rather than assumed.

    An exception is recorded and re-raised untouched -- the caller's error
    behaviour is not this module's to change.
    """
    import functools

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except Exception as exc:
            record(function.__name__, kwargs or args,
                   {"_raised": f"{type(exc).__name__}: {exc}"})
            raise
        record(function.__name__, kwargs or args, result)
        return result

    return wrapper
