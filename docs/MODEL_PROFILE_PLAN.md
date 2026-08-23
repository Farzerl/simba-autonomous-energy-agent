# GGUF selection and profile plan

## Decision rule

Keep deterministic engineering outside the model. Select the smallest model that
follows both submitted prompts reliably and produces valid concise output. Compare:

1. task completion and constraint adherence;
2. generation tokens/second on four CPU threads;
3. peak resident memory;
4. time to first token;
5. thermal behavior on the target Ubuntu laptop.

## Completed development baseline

Qwen2.5-1.5B-Instruct Q4_K_M was tested with official llama.cpp on an older
Intel i5-6300U using four threads. `llama-bench` measured approximately 27.71
prompt tokens/second, 8.17 generation tokens/second and 1.48 GB peak RSS. These
are local development observations, not the platform participant profile.

The first plan-selection response selected the more disruptive, lower-confidence
option and added a Markdown fence. The application safely rejects invalid plan IDs,
extracts JSON defensively and falls back to deterministic ranking.

## Selected model

Qwen3-1.7B Q8_0 correctly selected the higher-confidence, lower-disruption plan on
the same task. It measured 19.59 prompt tokens/second, 4.77 generation tokens/second
and 1,841.70 MB peak RSS in development. Its raw generation rate is lower, but the
observed quality improvement is preferred because quality has the largest Gate 1
weight. The exact official GGUF is pinned in `download_model.sh`.

## Required final run

On Ubuntu 22.04, after identity fields are filled:

```bash
bash download_model.sh
python3 scripts/adtc_preflight.py --require-model
adtc-profiler run --submission . --mode participant --output submission.json
```

Do not edit profiler output. Copy its actual RSS, throughput, latency and thermal
values to `REPORT.md` and the platform form. If the model, quantization, prompt or
llama.cpp build changes, rerun the complete profile.
