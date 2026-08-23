# Africa Deep Tech Challenge 2026 — verified Gate 1 requirements

Checked against the official challenge page, official repository template,
official profiler repository and Devpost rules on 22 August 2026.

## Runtime envelope

- Ubuntu 22.04, x86-64 Intel i5-class CPU, four CPU cores and 8 GB DDR4.
- Integrated graphics only; no discrete GPU.
- `llama.cpp` runtime and GGUF weights.
- Inference must be 100% offline after the public model download.
- The model process has a 7 GB memory ceiling; OOM or crash is disqualifying.

## Repository contract

- Public open-source GitHub repository using the official template layout.
- `metadata.json`, `download_model.sh`, `REPORT.md`, `model/` and `.gitignore`.
- Exactly two entrant prompts in metadata. The template says two additional hidden
  prompts; the challenge FAQ currently says three. Build for either hidden count.
- Public, credential-free, idempotent model download to the exact metadata path.
- GGUF weights are downloaded but not committed.

## Gate 1 artifacts

- Public repository and technical report.
- Model/profile evidence and screenshots or short clips.
- Demo video no longer than two minutes.
- GitHub, video and requested performance/efficiency details in Devpost.

## Scoring currently published

- 50% accuracy/quality.
- 30% generation throughput.
- 20% memory efficiency.
- 10-point thermal penalty above 85 °C or on throttling.
- The challenge page lists a 15% meaningful African-language multiplier and a
  10% budget-profile bonus. Devpost rules instead describe an African Use Case
  bonus of up to 10 points. Treat these as a live documentation discrepancy and
  make only evidence-backed claims.
- Profiler reference throughput: 15 generation tokens/second; memory budget: 7 GB.

## Deadline discrepancy

The main challenge page says 25 August 2026. The Devpost countdown/banner displays
24 August 2026 at 11:45 PM PDT. Use the earlier timestamp as the operational
deadline and confirm the live countdown immediately before submission.

## Eligibility declarations

Owner confirmation is required for team size (one to three), African residency,
age of majority, venture/team age under 12 months as of 16 June 2026, early-stage
status, originality, funding/grants no more than USD 25,000, and the other current
Devpost rules.

## Sources

- https://africadeeptech.org/challenge-2026/
- https://github.com/Africa-Deep-Tech-Foundation/adtc-2026-submission-template
- https://github.com/Africa-Deep-Tech-Foundation/adtc-profiler
- https://adtc-2026.devpost.com/rules
- https://adtc-2026.devpost.com/
