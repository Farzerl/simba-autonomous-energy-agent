#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODEL_DIR="$HERE/model"
MODEL_FILE="$MODEL_DIR/Qwen3-1.7B-Q8_0.gguf"
PARTIAL_FILE="$MODEL_FILE.partial"
MODEL_URL="https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/resolve/90862c4b9d2787eaed51d12237eafdfe7c5f6077/Qwen3-1.7B-Q8_0.gguf"
EXPECTED_SHA256="061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a"

mkdir -p "$MODEL_DIR"

valid_gguf() {
  [[ -f "$1" ]] || return 1
  [[ $(wc -c < "$1") -gt 100000000 ]] || return 1
  [[ "$(LC_ALL=C head -c 4 "$1")" == "GGUF" ]]
}

valid_sha256() {
  if command -v sha256sum >/dev/null 2>&1; then
    [[ "$(sha256sum "$1" | awk '{print $1}')" == "$EXPECTED_SHA256" ]]
  elif command -v shasum >/dev/null 2>&1; then
    [[ "$(shasum -a 256 "$1" | awk '{print $1}')" == "$EXPECTED_SHA256" ]]
  else
    echo "error: sha256sum or shasum is required to verify the model download" >&2
    return 1
  fi
}

if valid_gguf "$MODEL_FILE" && valid_sha256 "$MODEL_FILE"; then
  echo "model already present and valid at $MODEL_FILE - skipping download"
  exit 0
fi

if [[ -f "$MODEL_FILE" ]]; then
  echo "error: existing model file is not a valid GGUF; remove it and retry" >&2
  exit 1
fi

rm -f "$PARTIAL_FILE"
echo "downloading the official Qwen3 1.7B Q8_0 GGUF (~1.83 GB)..."
if command -v curl >/dev/null 2>&1; then
  curl -L --fail --retry 3 --progress-bar -o "$PARTIAL_FILE" "$MODEL_URL"
elif command -v wget >/dev/null 2>&1; then
  wget --tries=3 --show-progress -O "$PARTIAL_FILE" "$MODEL_URL"
else
  echo "error: neither curl nor wget is installed" >&2
  exit 1
fi

if ! valid_gguf "$PARTIAL_FILE" || ! valid_sha256 "$PARTIAL_FILE"; then
  rm -f "$PARTIAL_FILE"
  echo "error: downloaded file failed the GGUF header/size/SHA-256 check" >&2
  exit 1
fi

mv "$PARTIAL_FILE" "$MODEL_FILE"
echo "done: $MODEL_FILE"
