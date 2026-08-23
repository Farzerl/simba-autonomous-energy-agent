# ADTC model directory

Run `bash download_model.sh` from the repository root. It downloads the official
`Qwen3-1.7B-Q8_0.gguf` file here. GGUF weights are intentionally not committed to
Git. The script pins the public revision and verifies SHA-256.

This model is the Gate 1 model-profile lane. The existing Chronos-2 files elsewhere
in SIMBA-EMS remain numerical forecasting models and are not the submitted chat
GGUF.

The deterministic SIMBA demo works without this file. The GGUF is used by the
separate model-profile path and by the optional localhost-only llama-server provider.
