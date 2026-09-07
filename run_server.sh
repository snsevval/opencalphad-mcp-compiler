#!/bin/bash
# Wrapper that sets the linker environment the OpenCalphad OCASI (pyOC) build
# needs at process start, then execs the MCP server.
# LD_PRELOAD must be set before the process starts (Python's os.environ is
# too late for it), so this has to live outside server.py.
#
# Every path below used to be written out in full, pointing into one
# developer's home directory. On any other machine this script started,
# failed to preload, and the server answered every request with an import
# error -- so the paths are now derived from where this file actually is,
# with environment variables kept as the override for installs that put
# things elsewhere.
set -u

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The engine build. OC_BUILD_DIR wins; otherwise look beside the checkout,
# which is where a clone-and-build lands it, then one level up.
if [ -z "${OC_BUILD_DIR:-}" ]; then
    for aday in "$HERE/../opencalphad" "$HERE/opencalphad" "$HOME/opencalphad"; do
        if [ -d "$aday/.libs" ]; then
            OC_BUILD_DIR="$(cd "$aday" && pwd)"
            break
        fi
    done
fi
OC_BUILD_DIR="${OC_BUILD_DIR:-$HERE/../opencalphad}"
export OC_BUILD_DIR

if [ ! -d "$OC_BUILD_DIR/.libs" ]; then
    # Said once, plainly, before anything else fails in a less obvious way.
    echo "oc-mcp: OpenCalphad build not found at $OC_BUILD_DIR" >&2
    echo "        Set OC_BUILD_DIR to the directory containing .libs/" >&2
fi

export LD_LIBRARY_PATH="$OC_BUILD_DIR/.libs${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
export LD_PRELOAD="$OC_BUILD_DIR/.libs/libOC.so.0:$OC_BUILD_DIR/.libs/libOPENCALPHAD.so.0"

# VERIFY B needs NVIDIA_API_KEY. MCP clients (OpenClaw and others)
# launch this script with a bare environment, so the key has to be read
# here rather than inherited from a shell. Missing .env is not fatal --
# semantic_check reports the review as unavailable and the calculation
# still returns normally.
if [ -f "$HERE/.env" ]; then
    set -a
    . "$HERE/.env"
    set +a
fi

# The interpreter. A virtualenv beside or inside the checkout is used when
# present; otherwise whatever python3 is on PATH, which is what a plain
# "pip install -r requirements.txt" leaves behind.
PY=""
for aday in "$HERE/.venv/bin/python" "$HERE/venv/bin/python" \
            "$HERE/../ocvenv/bin/python" "$HOME/ocvenv/bin/python"; do
    if [ -x "$aday" ]; then
        PY="$aday"
        break
    fi
done
PY="${OC_PYTHON:-${PY:-$(command -v python3)}}"

if [ -z "$PY" ]; then
    echo "oc-mcp: no python3 found. Set OC_PYTHON to your interpreter." >&2
    exit 1
fi

exec "$PY" "$HERE/server.py" "$@"
