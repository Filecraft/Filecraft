#!/usr/bin/env python3
"""Sign separate test copies with an ephemeral TEST ONLY key; run instrumentation."""
import os
from pathlib import Path
import subprocess
import sys
import build

B = build.BUILD
SDK = build.SDK
key = B / "TEST-ONLY.keystore"

def run(*args, capture=False):
    return subprocess.run([str(x) for x in args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None, stderr=subprocess.STDOUT if capture else None)

try:
    # Never use this identity for production. Never alter the unsigned release artifact.
    if key.exists(): key.unlink()
    run(build.java("keytool"), "-genkeypair", "-keystore", key, "-storepass", "android", "-keypass", "android",
        "-alias", "prepare-test-only", "-dname", "CN=Prepare disposable TEST ONLY", "-keyalg", "RSA",
        "-keysize", "2048", "-validity", "2", "-noprompt")
    for stem in ("prepare", "prepare-tests"):
        run(build.java("java"), "-jar", build.TOOLS / "lib/apksigner.jar", "sign", "--ks", key,
            "--ks-pass", "pass:android", "--key-pass", "pass:android", "--out", B / (stem + "-TEST-ONLY.apk"),
            B / (stem + "-unsigned.apk"))
    adb = SDK / ("platform-tools/adb.exe" if os.name == "nt" else "platform-tools/adb")
    # Uninstall first: a newly generated test identity cannot update a prior test install.
    for package in ("com.prepare.app.tests", "com.prepare.app"):
        subprocess.run([str(adb), "uninstall", package], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for stem in ("prepare", "prepare-tests"):
        run(adb, "install", "-r", "-t", B / (stem + "-TEST-ONLY.apk"))
    output = run(adb, "shell", "am", "instrument", "-w", "com.prepare.app.tests/com.prepare.app.EngineTests", capture=True).stdout
    print(output)
    (B / "instrumentation.txt").write_text(output)
    if "OK (" not in output or "INSTRUMENTATION_CODE: -1" not in output or "FAIL" in output:
        sys.exit("Instrumentation failed (adb exit status alone is not sufficient)")
finally:
    if key.exists(): key.unlink()
