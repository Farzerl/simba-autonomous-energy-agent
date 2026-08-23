# SIMBA Autonomous Agent — build status

**Updated:** 22 August 2026  
**Application status:** functional and tested on the Windows development machine  
**Publication status:** code-complete; owner identity, final Ubuntu profiler output and video URL remain

## Working now

- Persistent missions, explicit states and sequenced audit events.
- Campus/facility trigger observation and deterministic candidate generation.
- Response estimates from public emulator/history priors and multi-objective plan ranking.
- Energy Safety Firewall that excludes critical, unavailable, stale or out-of-limit actions.
- Approval, modify, reject and approve-with-limits decisions.
- Software-in-the-loop execution with live electrical control hard-disabled.
- Two reproducible resilience paths: unavailable device and underperforming action.
- Verification, dynamic replanning and fail-closed behavior when limits are too tight.
- Offline interface languages: English, ChiShona, isiNdebele, Kiswahili and isiZulu.
- Windows launcher, Ubuntu setup/launcher, headless smoke test and Ubuntu 22.04 CI.
- Template-compatible metadata, exactly two prompts and an idempotent GGUF download.

## Verified behavior

Ten baseline public-fixture missions all reached the target and replanned once. The
representative unavailable-device mission starts at 1,280.810 kVA against a
1,203.961 kVA limit, realises an 84.181 kVA reduction and verifies 1,196.629 kVA
(7.332 kVA headroom). It records zero critical-load actions and keeps live control
disabled. A fresh final benchmark is written to
`evidence/public_synthetic_agent_benchmark.json` before packaging.

The final ten-run app benchmark passed 10/10 missions with 928.602 ms mean,
949.456 ms median and a 34.043 MB process RSS sample. This is
application telemetry, not the separate llama.cpp model-profile result.

## Honest critique

The deterministic agent loop is the strongest part: it is reproducible, bounded,
auditable and does not depend on a model to perform electrical arithmetic. The main
competitive risk is small-model instruction following. The initial Qwen2.5 1.5B
test chose a more disruptive plan despite a safer option and wrapped JSON in a code
fence. Prompt constraints, server-side JSON validation and deterministic fallback
prevent that output from becoming an unsafe action. Qwen3-1.7B Q8_0 was selected
after it chose the correct plan; it traded generation speed for better instruction
following while remaining at about 1.84 GB peak RSS in development testing.

## Remaining owner actions

1. Fill the fields listed in `submission/OWNER_INPUTS.md`.
2. Confirm every team member and venture satisfies the eligibility declarations.
3. Run the official participant profiler on Ubuntu and paste its unedited output
   into the documented placeholders.
4. Record the two-minute demo and add its public URL.
5. Publish the clean repository and submit before the earlier displayed deadline.

No final official accuracy, performance, memory, thermal or language multiplier is
claimed until those platform-controlled checks are complete.
