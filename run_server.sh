#!/bin/bash
# Wrapper that sets the linker environment the OpenCalphad OCASI (pyOC) build
# needs at process start, then execs the MCP server.
# LD_PRELOAD must be set before the process starts (Python's os.environ is
# too late for it), so this has to live outside server.py.
export OC_BUILD_DIR=/root/projects/opencalphad
export LD_LIBRARY_PATH="$OC_BUILD_DIR/.libs"
export LD_PRELOAD="$OC_BUILD_DIR/.libs/libOC.so.0:$OC_BUILD_DIR/.libs/libOPENCALPHAD.so.0"
exec /root/projects/ocvenv/bin/python /root/projects/oc-mcp/server.py "$@"
