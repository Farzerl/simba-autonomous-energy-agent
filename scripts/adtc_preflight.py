from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ALLOWED_DOMAINS = {
    "math_scientific_reasoning",
    "healthcare_medical",
    "agriculture",
    "creative_writing",
    "coding_assistants",
    "corporate_enterprise",
    "autonomous_ai_agents",
}
ALLOWED_PACKAGING = {"docker_image", "docker_build_from_repo", "binary_bundle"}
PLACEHOLDER_PATTERN = re.compile(r"REPLACE_WITH|your-team-id|your-name|your-email|your-github", re.I)
WEIGHT_SUFFIXES = {".gguf", ".safetensors", ".bin", ".pt", ".pth", ".ckpt"}
FORBIDDEN_TOP_LEVEL = {
    ".venv",
    "venv",
    "runtime",
    "logs",
    "patch_backups",
    "training_data",
    "workstation_bin",
}
REQUIRED_FILES = {
    ".gitignore",
    "LICENSE",
    "metadata.json",
    "download_model.sh",
    "REPORT.md",
    "README.md",
}


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    message: str


def _walk_files(root: Path) -> Iterable[Path]:
    for directory, names, filenames in os.walk(root):
        names[:] = [name for name in names if name not in {".git", "__pycache__"}]
        base = Path(directory)
        for filename in filenames:
            yield base / filename


def inspect(root: Path, allow_placeholders: bool, require_model: bool, development_tree: bool = False) -> list[Finding]:
    findings: list[Finding] = []

    def add(level: str, code: str, message: str) -> None:
        findings.append(Finding(level, code, message))

    for relative in sorted(REQUIRED_FILES):
        if not (root / relative).is_file():
            add("FAIL", "missing_required_file", f"Missing required file: {relative}")

    metadata_path = root / "metadata.json"
    metadata: dict[str, object] = {}
    if metadata_path.is_file():
        try:
            value = json.loads(metadata_path.read_text(encoding="utf-8"))
            if not isinstance(value, dict):
                raise ValueError("root value must be an object")
            metadata = value
        except Exception as exc:
            add("FAIL", "metadata_invalid_json", f"metadata.json is invalid: {exc}")

    if metadata:
        serialized = json.dumps(metadata, sort_keys=True)
        if PLACEHOLDER_PATTERN.search(serialized):
            level = "WARN" if allow_placeholders else "FAIL"
            add(level, "identity_placeholders", "Team ID and submitter identity must be filled from Devpost before submission.")

        if metadata.get("domain") not in ALLOWED_DOMAINS:
            add("FAIL", "domain_invalid", "metadata.domain is not an official ADTC domain value.")
        if metadata.get("domain") != "autonomous_ai_agents":
            add("FAIL", "domain_mismatch", "SIMBA must use the autonomous_ai_agents domain.")
        languages = metadata.get("language_scope")
        if not isinstance(languages, list) or not languages or not all(isinstance(item, str) and item.strip() for item in languages):
            add("FAIL", "language_scope_invalid", "language_scope must contain at least one language code.")
        if metadata.get("budget_laptop_claim") is not True:
            add("FAIL", "budget_claim_invalid", "budget_laptop_claim must be true for the standard 8 GB profile.")

        submitter = metadata.get("submitter")
        if not isinstance(submitter, dict):
            add("FAIL", "submitter_invalid", "submitter must be an object.")
        else:
            for key in ("name", "email", "github_handle"):
                if not str(submitter.get(key, "")).strip():
                    add("FAIL", "submitter_field_missing", f"submitter.{key} is required.")

        pairing = metadata.get("cross_disciplinary_pairing")
        if not isinstance(pairing, dict) or pairing.get("load_bearing") is not True:
            add("FAIL", "pairing_invalid", "The cross-disciplinary pairing must be present and load-bearing.")

        prompts = metadata.get("test_prompts")
        if not isinstance(prompts, list) or len(prompts) != 2:
            add("FAIL", "prompt_count", "metadata.json must contain exactly two test prompts.")
        else:
            identifiers = set()
            for index, prompt in enumerate(prompts, start=1):
                if not isinstance(prompt, dict):
                    add("FAIL", "prompt_invalid", f"Test prompt {index} must be an object.")
                    continue
                identifier = str(prompt.get("prompt_id", "")).strip()
                text = str(prompt.get("prompt", "")).strip()
                if not identifier or not text:
                    add("FAIL", "prompt_empty", f"Test prompt {index} requires prompt_id and prompt.")
                if identifier in identifiers:
                    add("FAIL", "prompt_duplicate_id", f"Duplicate prompt_id: {identifier}")
                identifiers.add(identifier)

        model = metadata.get("model")
        if not isinstance(model, dict):
            add("FAIL", "model_invalid", "metadata.model must be an object.")
        else:
            if model.get("runtime") != "llama.cpp":
                add("FAIL", "runtime_invalid", "The official Gate 1 runtime accepts llama.cpp only.")
            if not str(model.get("quantization", "")).upper().startswith("GGUF "):
                add("FAIL", "quantization_invalid", "model.quantization must name a GGUF quantization.")
            if model.get("packaging") not in ALLOWED_PACKAGING:
                add("FAIL", "packaging_invalid", "model.packaging is not an accepted template value.")

        runtime = metadata.get("_runtime")
        model_path_text = str(runtime.get("model_path", "")) if isinstance(runtime, dict) else ""
        model_path = Path(model_path_text)
        if (
            not model_path_text
            or model_path.is_absolute()
            or ".." in model_path.parts
            or model_path.suffix.lower() != ".gguf"
            or not model_path_text.replace("\\", "/").startswith("model/")
        ):
            add("FAIL", "model_path_invalid", "_runtime.model_path must be a safe relative model/*.gguf path.")
        else:
            target = root / model_path
            if require_model and not target.is_file():
                add("FAIL", "model_missing", f"Downloaded GGUF not found at {model_path_text}.")
            if target.is_file():
                try:
                    with target.open("rb") as handle:
                        header = handle.read(4)
                    if header != b"GGUF" or target.stat().st_size < 100_000_000:
                        add("FAIL", "model_invalid", "Downloaded model failed the GGUF header/size check.")
                except OSError as exc:
                    add("FAIL", "model_unreadable", f"Could not inspect downloaded model: {exc}")

            script = root / "download_model.sh"
            if script.is_file():
                script_text = script.read_text(encoding="utf-8")
                if model_path.name not in script_text:
                    add("FAIL", "download_path_mismatch", "download_model.sh does not name the metadata model path.")
                if not re.search(r"https://", script_text):
                    add("FAIL", "download_url_missing", "download_model.sh must use a public HTTPS URL.")

    if not development_tree:
        for name in sorted(FORBIDDEN_TOP_LEVEL):
            if (root / name).exists():
                add("FAIL", "release_hygiene", f"Clean public package must not contain top-level {name}/.")

    for path in _walk_files(root):
        relative = path.relative_to(root)
        if development_tree and relative.parts and relative.parts[0] in FORBIDDEN_TOP_LEVEL:
            continue
        if path.suffix.lower() in WEIGHT_SUFFIXES:
            if development_tree:
                continue
            if path.suffix.lower() == ".gguf" and relative.parts and relative.parts[0] == "model" and require_model:
                continue
            add("FAIL", "weight_committed", f"Model weight must not be in the public package: {relative.as_posix()}")
        if path.name in {".env", "id_rsa", "id_ed25519"} or path.suffix.lower() in {".pem", ".key", ".pfx"}:
            add("FAIL", "secret_file", f"Potential secret/private key file found: {relative.as_posix()}")
        if path.suffix.lower() == ".sh" and b"\r\n" in path.read_bytes():
            add("FAIL", "shell_line_endings", f"Shell script must use LF line endings: {relative.as_posix()}")

    ignore_path = root / ".gitignore"
    if ignore_path.is_file():
        ignore = ignore_path.read_text(encoding="utf-8")
        for required in ("*.gguf", "*.safetensors", ".venv/", "submission.json", "audit.json"):
            if required not in ignore:
                add("FAIL", "gitignore_gap", f".gitignore should include {required}")

    license_path = root / "LICENSE"
    if license_path.is_file():
        license_text = license_path.read_text(encoding="utf-8", errors="replace")
        if "Apache License" not in license_text and "MIT License" not in license_text and "GNU GENERAL PUBLIC LICENSE" not in license_text:
            add("FAIL", "license_not_open_source", "LICENSE is not recognisable as an OSI-style open-source licence.")

    if os.name != "nt":
        for relative in ("download_model.sh", "run_simba_demo.sh", "setup_ubuntu.sh"):
            path = root / relative
            if path.is_file() and not path.stat().st_mode & stat.S_IXUSR:
                add("FAIL", "script_not_executable", f"Shell script is not executable: {relative}")

    if not any(item.level == "FAIL" for item in findings):
        add("PASS", "repository_contract", "ADTC repository contract checks passed.")
    return findings


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate the SIMBA ADTC submission package before publishing.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--allow-placeholders", action="store_true", help="Warn instead of fail for identity placeholders during local staging.")
    parser.add_argument("--require-model", action="store_true", help="Also require and validate the downloaded GGUF.")
    parser.add_argument("--development-tree", action="store_true", help="Allow local runtime, environments and forecasting weights; never use for the public staging folder.")
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    root = args.root.resolve()
    findings = inspect(root, args.allow_placeholders, args.require_model, args.development_tree)
    if args.as_json:
        print(json.dumps({"root": str(root), "findings": [item.__dict__ for item in findings]}, indent=2))
    else:
        print(f"ADTC preflight: {root}")
        for item in findings:
            print(f"[{item.level}] {item.code}: {item.message}")
    raise SystemExit(1 if any(item.level == "FAIL" for item in findings) else 0)


if __name__ == "__main__":
    main()
