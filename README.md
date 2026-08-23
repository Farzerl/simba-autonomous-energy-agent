# SIMBA Autonomous Energy Operations Agent

SIMBA is an offline, approval-gated energy operations agent for African
campuses, hospitals, farms and small enterprises. An operator sets a demand
limit; SIMBA observes the facility network, forecasts a possible peak, ranks
safe non-critical interventions, asks for approval, applies approved actions to
a software plant, verifies the response and replans when conditions change.

The public prototype never switches real electrical equipment.

## What it does

`OBSERVE → FORECAST → PLAN → SAFETY CHECK → APPROVAL → EMULATE → VERIFY → REPLAN`

The included resilience demonstration deliberately creates one of two
complications:

- a selected device becomes unavailable; or
- an approved action produces less reduction than expected.

SIMBA blocks or detects the problem, excludes the failed resource, creates a
new safety-cleared plan, inherits approval only when the new actions remain
inside the approved limits, and verifies the final campus demand.

The default public scenario starts at 1,280.81 kVA with a 1,203.961 kVA limit.
Both resilience paths finish below the limit, record zero critical-load
actions, and keep live electrical control disabled.

## Offline African-language interface

The complete agent workflow, controls, safety boundary and mission outcome can
be viewed in:

- English (`en`)
- ChiShona (`sn`)
- isiNdebele (`nd`)
- Kiswahili (`sw`)
- isiZulu (`zu`)

Translations are bundled locally in `dashboard/static/i18n.js`. Selecting a
language makes no network request and does not use the LLM. This deterministic
localisation keeps safety wording stable on constrained, intermittently
connected sites.

## Run on Ubuntu 22.04

Target profile: x86-64, four CPU cores, 8 GB RAM, integrated graphics and no
cloud dependency during operation.

```bash
chmod +x setup_ubuntu.sh run_simba_demo.sh download_model.sh
./setup_ubuntu.sh
./run_simba_demo.sh
```

The launcher opens `http://127.0.0.1:8000/?tab=agent`. Choose a resilience test
and press **Run resilient demo**.

Terminal-only verification:

```bash
.venv/bin/python scripts/smoke_test_agent.py
.venv/bin/python scripts/benchmark_agent.py --runs 10
```

## Run on Windows for development

For a one-click local run, use `INSTALL_SIMBA_AGENT.bat` once, then double-click
`RUN_SIMBA_AGENT.bat`.

```powershell
py -3 -m venv .venv
.venv\Scripts\python -m pip install -r requirements-ubuntu-agent.txt
.venv\Scripts\python scripts\run_demo.py
```

## Safety and autonomy boundary

The local language model is not authoritative for electrical arithmetic,
tariffs, critical-load classification, device readiness, action capacity,
approval limits, stale-command checks or impact verification. Deterministic
engineering services own those decisions.

The optional model may only:

- select one plan identifier from an already safety-cleared set; and
- produce a short explanation.

Invalid model output, an unavailable local model server or an out-of-set plan
falls back to the highest-ranked deterministic plan. The public server always
constructs `ControlGateway(mode="simulation", allow_live=False)` and overrides
environment settings that might otherwise request live control.

## ADTC 2026 model package

The application demonstration and the ADTC model profile are separate paths.
The official pipeline downloads the GGUF declared in `metadata.json` and runs
it through llama.cpp. The selected model is the official Qwen3-1.7B Q8_0 GGUF;
the pinned 1.83 GB file measured about 1.84 GB process RSS in development. This
repository follows the official package structure:

```text
metadata.json
download_model.sh
REPORT.md
model/                 # GGUF is downloaded here and excluded from Git
```

Download and verify the pinned public model:

```bash
bash download_model.sh
python scripts/adtc_preflight.py --require-model --allow-placeholders
```

Run the current official profiler on a representative Ubuntu laptop:

```bash
python3.11 -m pip install "git+https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler.git"
adtc-profiler run --submission . --mode participant --output submission.json
```

Use `--skip-accuracy` only for iteration. The final `submission.json` should
come from a complete participant run. Do not invent throughput, memory,
temperature or accuracy values.

## Development checks

```bash
python scripts/adtc_preflight.py --allow-placeholders
pytest -q
python scripts/smoke_test_agent.py
python scripts/benchmark_agent.py --runs 10
```

Before publishing, run the strict repository preflight:

```bash
python scripts/adtc_preflight.py
python scripts/adtc_preflight.py --require-model
```

## Repository map

- `src/agent/` — mission state machine, plans, providers, safety and tools
- `src/control/` — software-only control gateway and emulator service
- `src/tariff/` — deterministic ZETDC time-of-use logic
- `dashboard/` — offline operator interface and language packs
- `config/` — mission limits, response priors and compact-context settings
- `data/simulation/` — public synthetic 22-facility scenario
- `tests/` — API, approval, fail-closed, resilience and localisation tests
- `evidence/` — reproducible application benchmark output
- `submission/` — Devpost draft, video script and remaining owner inputs

## Honest prototype boundary

The clean repository contains a deterministic public fixture with generic
facility names and Chronos-2 routing metadata. It excludes private facility
data, large forecasting weights, runtime logs, virtual environments and GGUF
weights. The original SIMBA workstation retains the trained forecasting stack;
this public package proves the autonomous control loop reproducibly without
publishing private operational material.

## License

Application code is released under Apache-2.0. Third-party models and tools keep
their own licences; see `NOTICE.md`.
