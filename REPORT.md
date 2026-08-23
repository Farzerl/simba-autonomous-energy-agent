# Technical Report — SIMBA Autonomous Energy Operations Agent

**Team ID:** simba-autonomous-energy-operations-agent  
**Domain:** autonomous_ai_agents  
**Model:** Qwen3-1.7B-Q8_0  
**Owner:** Farai Rashayi  
**Repository:** https://github.com/Farzerl/simba-autonomous-energy-agent  
**Video:** Pending final public demo upload

---

## Problem

African campuses, hospitals, farms and small enterprises face peak-demand costs,
capacity constraints, intermittent connectivity and limited access to cloud AI.
Forecast dashboards identify risk but leave an operator to work out which loads can
move, whether a proposed action is safe, and whether the intervention actually worked.

SIMBA provides an offline, auditable operating loop. Its mission is to keep campus
demand below a configured limit during a target window without touching critical
loads. It observes configured facilities, reuses the existing Chronos-2 demand and
power-quality routes, checks tariffs and anomalies, generates non-critical candidate
actions, ranks plans, requests bounded approval, executes only in the hardware
emulator, verifies the measured response and replans when an action is unavailable or
underperforms. Live electrical control is disabled in this release.

Local operation matters where connectivity is unreliable, facility telemetry is
sensitive and cloud inference cost is difficult to sustain. The operator interface
works offline in English, ChiShona, isiNdebele, Kiswahili and isiZulu.

---

## Design Decisions

- **Base model:** official Qwen3-1.7B. Qwen describes Qwen3 as improving reasoning,
  instruction following, agent/tool use and support for 100+ languages and dialects.
  It is Apache-2.0 and has a creator-published GGUF repository.
- **Quantization:** official Q8_0 GGUF (1.83 GB file). It remains well below the 7 GB
  model-process ceiling while preserving more quality than an aggressive quantization.
  `download_model.sh` pins Qwen revision
  `90862c4b9d2787eaed51d12237eafdfe7c5f6077`, downloads without credentials and
  verifies SHA-256 `061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a`.
- **Alternative considered:** Qwen2.5-1.5B-Instruct Q4_K_M was faster and lighter,
  but repeatedly chose the lower-confidence, more disruptive plan in the submitted
  plan-ranking prompt and wrapped the result in Markdown. Qwen3 selected the correct
  plan and followed the safety ordering. Because quality is the largest score
  component, the measured quality gain was preferred over raw speed.
- **Deterministic-first agent:** the model never performs authoritative kVA, tariff,
  limit, criticality or verification calculations. It may select only among plan IDs
  already cleared by deterministic services. Invalid output is rejected and falls
  back to the top deterministic plan.
- **Compact inference:** structured state contains only the mission goal, risk,
  cleared plan IDs, response estimates, confidence, disruption and constraints.
  The optional persistent localhost llama-server uses non-thinking mode, short output,
  response caching and no network calls.
- **Cross-disciplinary pairing:** energy-systems logic is load-bearing, not a theme.
  Chronos routes, tariff/anomaly services, the Approval Deck, simulator, response
  estimator, Energy Safety Firewall and verifier participate in every mission.

Model source: https://huggingface.co/Qwen/Qwen3-1.7B-GGUF

---

## Constraints

- Target: 8 GB RAM, four CPU cores, integrated graphics and Ubuntu 22.04.
- Pure CPU inference through llama.cpp; no GPU dependency.
- 100% offline inference after the public GGUF download.
- Model-process peak RSS must remain below 7 GB.
- Facility data must remain local and private institutional data is not published.
- Critical loads are excluded before ranking and checked again before execution.
- Operator approval is mandatory, with action-count, reduction, facility, load-group
  and expiry limits.
- All actuation is software-in-the-loop; environment variables cannot enable live
  switching through the public application entry point.
- Forecast model weights were not retrained or modified. The clean public package
  uses a deterministic synthetic fixture when the existing large/private forecasting
  artifacts are absent.

---

## Benchmarks

### Selected GGUF — development machine

Official llama.cpp build b10566 was run CPU-only with four threads on an older
Intel Core i5-6300U Windows development laptop. These observations guide the model
choice; final platform-controlled values must come from the current participant
profiler on Ubuntu.

| Metric | Value |
|---|---|
| Model file | 1.83 GB; Qwen3 1.7B Q8_0 |
| Peak model-process RSS | 1,841.70 MB in short monitored llama-bench run |
| Prompt processing | 19.59 ± 0.16 tokens/s (`pp128`) |
| Generation speed | 4.77 ± 0.01 tokens/s (`tg64`) |
| Time to first token | Not isolated in this development run |
| Thermal throttling | Not measurable with the available Windows sensor interface |
| Plan-quality comparison | Qwen3 selected safe Plan A; Qwen2.5 selected inferior Plan B |

### Deterministic application loop

Ten public-fixture runs alternated unavailable-device and underperforming-action
scenarios. All ten reached the target, replanned once, touched zero critical loads
and kept live control disabled.

| Metric | Value |
|---|---|
| Runs passed | 10/10 |
| Mean / median mission time | 928.602 ms / 949.456 ms |
| Range | 748.001–1,060.899 ms |
| App process RSS sample | 34.043 MB |
| Forecast / limit | 1,280.810 / 1,203.961 kVA |
| Unavailable-device result | 1,196.629 kVA; 7.332 kVA headroom |
| Underperformance result | 1,196.347 kVA; 7.614 kVA headroom |
| Critical-load actions | 0 |
| Live electrical control | Disabled |

Evidence is in `evidence/public_synthetic_agent_benchmark.json`. This app timing is
not a llama.cpp score.

### Final participant profile — owner input

`Official profiler values pending final profiling run. Development measurements below are not a substitute for the official profiler.`

Do not replace the development table with estimates. Keep the generated
`submission.json` unchanged and report only measured values.
