# opencalphad-mcp-server

An MCP (Model Context Protocol) server that connects OpenCalphad, an
open-source CALPHAD thermodynamics calculation engine, to AI assistants
such as Claude and NVIDIA Nemotron. It exposes thermodynamic equilibrium
and property-diagram calculations as tools an AI model can call directly,
with the underlying calculations performed by the real OpenCalphad engine.

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

## Requirements

- A working OpenCalphad build (engine binary and OCASI/pyOC Python
  bindings). See https://github.com/sundmanbo/opencalphad.
- Python 3.11+ with the `mcp` package installed.
- gnuplot (used by `calculate_property_diagram`'s native rendering path).

## Running

Set `OC_BUILD_DIR` to the OpenCalphad build directory, then run
`run_server.sh`, which sets the required `LD_LIBRARY_PATH`/`LD_PRELOAD`
and starts the MCP server over stdio. Point an MCP-compatible client
(Claude Desktop, OpenClaw, etc.) at this script.

## Files

- `server.py`: MCP tool definitions (FastMCP).
- `oc_service.py`: OCASI-based equilibrium calculation, with automatic
  native fallback.
- `native_fallback.py`: single-point equilibrium via the native
  OpenCalphad binary.
- `native_step.py`: temperature-sweep property diagrams via the native
  STEP algorithm, with gap-filling and gnuplot rendering.
- `run_equilibrium.py` / `run_server.sh`: process isolation and server
  startup.
