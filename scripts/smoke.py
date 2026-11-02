#!/usr/bin/env python3
"""Check the installed package without sign-in, devices or runtime effects."""
import json
from pathlib import Path
import platform
import subprocess

root = Path(__file__).resolve().parent.parent
manifest = json.loads((root / "release.json").read_text())["manifest"]
prefix = subprocess.check_output(["brew", "--prefix"], text=True).strip()
binary = Path(prefix) / "bin/iotk"
if platform.system() == "Darwin":
    subprocess.run(["codesign", "--verify", "--strict", "--verbose=2", str(binary)], check=True)
    signature = subprocess.run(["codesign", "--display", "--verbose=4", str(binary)], capture_output=True, text=True, check=True)
    details = signature.stdout + signature.stderr
    for expected in ("TeamIdentifier=X7RWL5MAV2\n", "Identifier=io.iotkit.iotk\n", "Authority=Developer ID Application:", "(runtime)", "Timestamp="):
        if expected not in details:
            raise ValueError("Installed macOS CLI does not have the qualified Developer ID signature")
    subprocess.run(["codesign", "--verify", "--strict", "--verbose=4", "-R=notarized", "--check-notarization", str(binary)], check=True)
actual = subprocess.check_output([str(binary), "version"], text=True).strip()
expected = f"iotk {manifest['version']} ({manifest['revision']})"
if actual != expected:
    raise ValueError("Installed executable identity differs from the published build")
hardware = json.loads(subprocess.check_output([str(binary), "hardware"], text=True))
if not isinstance(hardware, list) or len(hardware) != 6:
    raise ValueError("Installed CLI cannot read its six offline hardware profiles")
if not list((binary.resolve().parent / "licenses").glob("*-LICENSE.txt")):
    raise ValueError("Installed package lost upstream third-party notices")
print(f"Native Homebrew package verified: {actual}; six hardware profiles and license notices")
