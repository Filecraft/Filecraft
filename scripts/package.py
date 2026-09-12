"""Package an already-built release binary; no dependency downloads or credentials."""
from pathlib import Path
import argparse
import hashlib
import os
import plistlib
import shutil
import subprocess
import json
from release_budget import validate_sizes

version = "0.5.0"

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--binary", required=True, type=Path)
args = parser.parse_args()
if not args.binary.is_file():
    parser.error("Build Prepare first; release binary not found")
# Rebuild only our generated bundle; never carry stale resources into a release.
app = root / "build" / "Prepare.app"
if app.is_symlink():
    raise SystemExit("Refusing a symlinked application output")
if app.exists():
    shutil.rmtree(app)
macos = app / "Contents" / "MacOS"
macos.mkdir(parents=True, exist_ok=True)
shutil.copy2(args.binary, macos / "Prepare")
info = {"CFBundleExecutable": "Prepare", "CFBundleIdentifier": "org.prepareapp.prepare",
        "CFBundleName": "Prepare", "CFBundleDisplayName": "Prepare", "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": version, "CFBundleVersion": "5",
        "CFBundleIconFile": "AppIcon",
        "CFBundleDocumentTypes": [{"CFBundleTypeName": "Still images", "CFBundleTypeRole": "Viewer",
                                   "LSHandlerRank": "Alternate",
                                   "LSItemContentTypes": ["public.jpeg", "public.png", "public.heic"]}],
        "LSMinimumSystemVersion": "14.0", "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "Copyright (c) 2026 Prepare contributors"}
(app / "Contents" / "Info.plist").write_bytes(plistlib.dumps(info))
resources = app / "Contents" / "Resources"
resources.mkdir()
for name in ["LICENSE", "NOTICE"]:
    shutil.copy2(root / name, resources / name)
iconset = root / "build" / "Prepare.iconset"
subprocess.run(["swift", str(root / "scripts" / "make-icon.swift"), str(iconset)], check=True)
subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(resources / "AppIcon.icns")], check=True)
identity = os.environ.get("SIGN_IDENTITY", "-")
command = ["codesign", "--force", "--sign", identity]
if identity != "-":
    command += ["--options", "runtime", "--timestamp"]
subprocess.run(command + [str(app)], check=True)
subprocess.run(["codesign", "--verify", "--strict", str(app)], check=True)
architecture = subprocess.check_output(["lipo", "-archs", str(macos / "Prepare")], text=True).strip().replace(" ", "-")
archive = root / "build" / f"Prepare-{version}-{architecture}.zip"
if archive.exists():
    archive.unlink()
subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(archive)], check=True)
sizes = dict(binary=(macos / "Prepare").stat().st_size,
             app=sum(p.stat().st_size for p in app.rglob("*") if p.is_file()),
             archive=archive.stat().st_size)
validate_sizes(**sizes)
(root / "build" / "release-size.json").write_text(json.dumps(dict(version=version, **sizes), indent=2) + "\n")
print(f"PASS: byte budgets {sizes}")
digest = hashlib.sha256(archive.read_bytes()).hexdigest()
archive.with_suffix(".zip.sha256").write_text(f"{digest}  {archive.name}\n")
print(f"App: {app}\nArchive: {archive}\nSHA256: {digest}")
print("LOCAL AD-HOC SIGNATURE; NOT NOTARIZED" if identity == "-" else "Developer ID signed; notarization remains a separate release step")
