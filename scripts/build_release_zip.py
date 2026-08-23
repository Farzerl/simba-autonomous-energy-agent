from __future__ import annotations

import argparse
import hashlib
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRECTORIES = {
    ".git",
    ".idea",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    ".vscode",
    "__pycache__",
    "logs",
    "private_data",
    "raw_data",
    "runtime",
    "venv",
}
EXCLUDED_SUFFIXES = {
    ".bin",
    ".ckpt",
    ".gguf",
    ".joblib",
    ".key",
    ".log",
    ".pem",
    ".pkl",
    ".pt",
    ".pth",
    ".pyc",
    ".rar",
    ".safetensors",
    ".zip",
}
EXCLUDED_NAMES = {
    ".coverage",
    ".env",
    "audit.json",
    "submission.json",
    "verdict.json",
}


def include(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    if any(part in EXCLUDED_DIRECTORIES for part in relative.parts):
        return False
    if path.name in EXCLUDED_NAMES or path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    if path.name.endswith(".gguf.partial") or path.name.startswith("_patch_"):
        return False
    return path.is_file()


def release_files() -> list[Path]:
    return sorted(
        (path for path in ROOT.rglob("*") if include(path) and path.name != "MANIFEST.sha256"),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def refresh_manifest(files: list[Path]) -> Path:
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(ROOT).as_posix()}")
    manifest = ROOT / "MANIFEST.sha256"
    manifest.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return manifest


def write_zip(output: Path, folder_name: str) -> None:
    files = release_files()
    manifest = refresh_manifest(files)
    files.append(manifest)
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing archive: {output}")

    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo.from_file(path, arcname=f"{folder_name}/{relative}")
            mode = 0o100755 if path.suffix.lower() == ".sh" else 0o100644
            info.external_attr = mode << 16
            info.create_system = 3
            with path.open("rb") as source, archive.open(info, "w") as target:
                while block := source.read(1024 * 1024):
                    target.write(block)

    print(f"Release ZIP: {output}")
    print(f"Files: {len(files)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a clean Ubuntu/GitHub SIMBA release ZIP.")
    parser.add_argument("output", type=Path)
    parser.add_argument("--folder-name", default="SIMBA_EMS_ADTC_Gate1_Ubuntu_GitHub")
    args = parser.parse_args()
    write_zip(args.output.resolve(), args.folder_name)


if __name__ == "__main__":
    main()
