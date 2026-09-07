# opencalphad-mcp-compiler

An MCP (Model Context Protocol) server that connects OpenCalphad, an
open-source CALPHAD thermodynamics calculation engine, to AI assistants
such as NVIDIA Nemotron. It exposes thermodynamic equilibrium, phase
diagram and solidification calculations as tools a model can call
directly, with every number produced by the real OpenCalphad engine.

The pipeline is compiler-shaped, and the name says so. A question in
natural language becomes a typed request; a static check rejects the
impossible ones before any engine runs; a cascade of backends produces
the numbers; and the result is checked on the way out and summarised
into the answers it implies. Each stage can refuse, and says why.

    question  ->  typed request  ->  PREFLIGHT  ->  engine cascade
                                                         |
                          answer  <-  summary  <-  verification

The reason for the shape is that the engine is not uniformly reliable and
a model reading raw output is not uniformly careful. Both failure modes
are quiet ones: a solver that stops early still returns well-formed
numbers, and a reader that skips a row still writes a confident
paragraph. The stages exist to make each of those loud.

## What it does

- `list_databases` / `inspect_database`: browse available `.TDB`
  thermodynamic databases and their elements/phases.
- `calculate_equilibrium`: single-point equilibrium calculation (Gibbs
  energy, chemical potentials, stable phases and their amounts/
  compositions) for a given composition, temperature, and pressure.
- `compare_alloys`: run two compositions under the same conditions and
  compare the results.
- `calculate_property_diagram`: temperature sweep showing how stable
  phases change with temperature, rendered as a chart.

## Architecture

OpenCalphad exposes two interfaces: OCASI (a compiled Python binding, via
`pyOC`/`rawpyOC`) for fast single-point calculations, and a native
command-line binary for macro-driven calculations including STEP (phase
fraction vs. temperature).

- `calculate_equilibrium` tries OCASI first; if it fails to converge, it
  automatically falls back to running the native binary with an
  equivalent macro (`native_fallback.py`).
- `calculate_property_diagram` tries OpenCalphad's own native STEP
  algorithm first (`native_step.py`), which is faster and matches what
  OpenCalphad's own GUI produces. Where STEP's internal solver cannot
  converge for a given temperature (a known limitation of this engine
  build), the gap is filled in with independent single-point
  calculations, so the resulting chart has no missing data. Both sources
  are converted to a common phase mass-fraction basis before being
  combined. Charts are rendered with gnuplot; an interactive gnuplot
  window can also be opened directly (tested via WSLg on Windows).
- If the native STEP/gnuplot path is unavailable, `calculate_property_diagram`
  falls back to a Python loop over `calculate_equilibrium` with a
  matplotlib chart.
- Every scan result carries a `scan_summary` field alongside its points:
  where the phase assemblage changes, which phase holds the majority over
  which stretch, and where melting starts and finishes. These are the
  questions a scan is usually asked, and none of them is answerable from
  a single row -- so they are derived once, deterministically, from the
  points already computed (`scan_summary.py`, no extra engine calls).
  Boundaries are reported as the pair of sampled positions that straddle
  them rather than as single numbers, and a region seen at one position
  only is listed under `under_sampled`, so the summary states what it
  cannot resolve instead of smoothing over it.

Every request passes a deterministic PREFLIGHT check before the engine is
touched, and every result is checked for structural sanity on the way out;
an optional independent model review runs on top of that. A rejection that
is answerable by a different tool says which one.

## Requirements

- A working OpenCalphad build (engine binary and OCASI/pyOC Python
  bindings). See https://github.com/sundmanbo/opencalphad.
- Python 3.11+ with the `mcp` package installed.
- gnuplot (used by `calculate_property_diagram`'s native rendering path).

## Running

Run `run_server.sh`. It sets the `LD_LIBRARY_PATH`/`LD_PRELOAD` the OCASI
bindings need before the process starts, loads `.env` if present, and
starts the MCP server over stdio. Point an MCP-compatible client
(OpenClaw, or any stdio MCP client) at this script.

Nothing has to be configured for a layout where the OpenCalphad build sits
beside this checkout and the databases are where the installer put them.
Both are searched, in a stated order, and either can be overridden.

### Where the engine is found

1. `OC_BUILD_DIR`, if set
2. `../opencalphad` next to this checkout
3. `./opencalphad` inside it
4. `~/opencalphad`

The first directory containing a `.libs/` is used. If none is found the
script says so on stderr before failing, rather than leaving an import
error to explain it.

### Where the databases are found

TDB files are not shipped with this repository. The directory holding them
is resolved once at startup:

1. `OC_DB_DIR`, if set -- this wins outright, and if it holds no `.TDB`
   files that is reported rather than quietly worked around; answering
   from a directory the caller did not choose would be worse than failing
2. `databases/` inside this checkout
3. `$OC_BUILD_DIR/macros`, where OpenCalphad keeps its example databases
4. `~/OpenCalphad/OC6/macros`
5. `/mnt/c/Users/*/Documents/OpenCalphad/OC6/macros`, where the Windows
   installer puts them, reached through WSL

A candidate has to *contain* a database, not merely exist: an empty
directory that happens to be present would otherwise shadow a full one
further down, and the failure would look like a missing file rather than a
wrong directory. If nothing is found the server still starts and says on
stderr every place it looked, so the fix is `OC_DB_DIR=...` or dropping
the files into `databases/`.

### Environment

| Variable | Meaning |
|---|---|
| `OC_BUILD_DIR` | OpenCalphad build directory (contains `.libs/`) |
| `OC_DB_DIR` | Directory holding the `.TDB` files |
| `OC_PYTHON` | Interpreter to run the server with |
| `OC_SEMANTIC_CHECK` | `0` disables VERIFY B (the outside reviewer) |
| `OC_INTERACTIVE_WINDOW` | `1` opens a gnuplot window per diagram; off by default because these use `gnuplot -persist` and never close on their own |
| `OC_CALL_LOG` | Path for the request/response log |
| `NVIDIA_API_KEY` | VERIFY B credential; read from `.env` if present |

## Files

- `server.py`: MCP tool definitions (FastMCP).
- `oc_service.py`: OCASI-based equilibrium calculation, with automatic
  native fallback.
- `native_fallback.py`: single-point equilibrium via the native
  OpenCalphad binary.
- `native_step.py`: temperature-sweep property diagrams via the native
  STEP algorithm, with gap-filling and gnuplot rendering.
- `native_scheil.py`: Scheil-Gulliver solidification (non-equilibrium
  cooling, solid removed at each step).
- `native_map.py`: two-axis phase diagrams via the native MAP algorithm.
- `scan_summary.py`: phase regions, transitions, dominance and melting
  landmarks derived from a scan's own points.
- `preflight.py`: request validation before any engine call.
- `result_check.py`: structural checks on a returned result.
- `semantic_check.py`: optional independent model review of a result's
  physical plausibility.
- `failure_classify.py`: typed failure classification driving the retry
  stage.
- `call_log.py`: append-only record of each tool call and its payload,
  written for later inspection.
- `run_equilibrium.py` / `run_server.sh`: process isolation and server
  startup.
- `benchmark/`: 88 fixed cases exercised over the real MCP protocol, plus
  the hand-asked question pool and its measurement record.
