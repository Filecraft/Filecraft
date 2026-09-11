#!/usr/bin/env python3
"""Framework-only APK: JDK 17 + SDK platform 36 (r2), build-tools 36.0.0. No Gradle."""
import argparse
import hashlib
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / "build"
JAVA = Path(os.environ.get("JAVA_HOME", ROOT / ".toolchain/jdk-17.0.15+6/Contents/Home"))
SDK = Path(os.environ.get("ANDROID_SDK_ROOT", os.environ.get("ANDROID_HOME", ROOT / ".toolchain/sdk")))
TOOLS = SDK / "build-tools/36.0.0"
ANDROID = SDK / "platforms/android-36/android.jar"
EXT = ".exe" if os.name == "nt" else ""

def run(*args):
    subprocess.run([str(x) for x in args], check=True, cwd=ROOT)

def java(tool):
    path = JAVA / "bin" / (tool + EXT)
    if not path.is_file():
        sys.exit("JDK 17 required: set JAVA_HOME; see android/README.md")
    return path

def core():
    classes = BUILD / "core"
    classes.mkdir(parents=True, exist_ok=True)
    run(java("javac"), "--release", "8", "-d", classes,
        ROOT / "src/com/prepare/app/Geometry.java", ROOT / "src/com/prepare/app/Policy.java",
        ROOT / "src/com/prepare/app/Copy.java", ROOT / "tests/CoreTests.java")
    run(java("java"), "-cp", classes, "com.prepare.app.CoreTests")

def normalize(source, destination, extra):
    with zipfile.ZipFile(source) as src:
        entries = {n: src.read(n) for n in src.namelist() if not n.endswith("/")}
    entries.update(extra)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for name, content in sorted(entries.items()):
            info = zipfile.ZipInfo(name, (2024, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED if name == "resources.arsc" else zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            out.writestr(info, content)

def verify_resources(apk, required=True):
    with zipfile.ZipFile(apk) as archive:
        names = archive.namelist()
        if "resources.arsc" not in names:
            if required:
                raise AssertionError("resources.arsc missing")
            return
        if names.count("resources.arsc") != 1:
            raise AssertionError("duplicate resources.arsc")
        info = archive.getinfo("resources.arsc")
        if info.compress_type != zipfile.ZIP_STORED:
            raise AssertionError("resources.arsc must be ZIP_STORED")
        with open(apk, "rb") as stream:
            stream.seek(info.header_offset)
            header = stream.read(30)
        if header[:4] != b"PK\x03\x04":
            raise AssertionError("invalid ZIP local header")
        method = struct.unpack_from("<H", header, 8)[0]
        name_len, extra_len = struct.unpack_from("<HH", header, 26)
        offset = info.header_offset + 30 + name_len + extra_len
        if method != zipfile.ZIP_STORED or offset % 4:
            raise AssertionError("resources.arsc must be stored and 4-byte aligned in local header")


def apk(test=False):
    if not ANDROID.is_file() or not (TOOLS / ("aapt2" + EXT)).is_file():
        sys.exit("SDK platform 36 and build-tools 36.0.0 required; see android/README.md")
    name = "prepare-tests" if test else "prepare"
    work = BUILD / name
    if work.exists(): shutil.rmtree(work)
    (work / "classes").mkdir(parents=True)
    (work / "dex").mkdir()
    manifest = ROOT / ("tests/AndroidManifest.xml" if test else "AndroidManifest.xml")
    link = [TOOLS / ("aapt2" + EXT), "link", "-o", work / "resources.apk", "-I", ANDROID, "--manifest", manifest]
    if not test:
        run(TOOLS / ("aapt2" + EXT), "compile", "--dir", ROOT / "res", "-o", work / "compiled.zip")
        link += [work / "compiled.zip"]
    run(*link)
    sources = [ROOT / "tests/EngineTests.java"] if test else sorted((ROOT / "src").rglob("*.java"))
    classpath = str(ANDROID) + (os.pathsep + str(BUILD / "prepare/classes") if test else "")
    run(java("javac"), "-source", "8", "-target", "8", "-Xlint:-options", "-encoding", "UTF-8", "-g:none",
        "-classpath", classpath, "-d", work / "classes", *sources)
    run(java("java"), "-cp", TOOLS / "lib/d8.jar", "com.android.tools.r8.D8", "--release", "--min-api", "28",
        "--lib", ANDROID, "--output", work / "dex", *sorted((work / "classes").rglob("*.class")))
    extra = {p.name: p.read_bytes() for p in sorted((work / "dex").glob("*.dex"))}
    if not test:
        for name in ["LICENSE", "NOTICE"]:
            extra["assets/" + name] = (ROOT.parent / name).read_bytes()
        extra["assets/PRIVACY.md"] = (ROOT / "store/PRIVACY.md").read_bytes()
    raw = work / "unaligned.apk"
    normalize(work / "resources.apk", raw, extra)
    target = BUILD / ("prepare-tests-unsigned.apk" if test else "prepare-unsigned.apk")
    run(TOOLS / ("zipalign" + EXT), "-f", "4", raw, target)
    run(TOOLS / ("zipalign" + EXT), "-c", "4", target)
    # Inspect the actual aligned artifact, not just the normalizer's intention.
    verify_resources(target, required=not test)
    print(f"PASS {target.name}: resources.arsc stored and 4-byte aligned (if present)")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    target.with_suffix(".apk.sha256").write_text(digest + "  " + target.name + "\n")
    if not test and target.stat().st_size >= 1000000: sys.exit("APK exceeds 1 MB hard budget")
    print(f"UNSIGNED {target}: {target.stat().st_size} bytes; SHA256 {digest}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--core", action="store_true", help="only JVM core tests; no Android SDK needed")
    args = parser.parse_args()
    core()
    if not args.core:
        run(sys.executable, "-m", "unittest", "discover", "-s", ROOT / "tests", "-p", "test_release_gates.py", "-v")
        apk()
        apk(test=True)
