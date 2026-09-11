"""Deterministic, dependency-free source packaging; Python 3.9+ build tool."""
from pathlib import Path
import hashlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def build(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    output = destination / "document-engine-source.zip"
    source = ROOT / "engine"
    files = [ROOT / "LICENSE"] + [p for p in source.rglob("*") if p.is_file() and not p.is_symlink() and not any(part in {"dist", "__pycache__", ".DS_Store"} for part in p.relative_to(source).parts)]
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(files):
            info = zipfile.ZipInfo(file.relative_to(ROOT).as_posix(), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, file.read_bytes())
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(output.suffix + ".sha256").write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    return output

if __name__ == "__main__":
    print(build(ROOT / "engine" / "dist"))
