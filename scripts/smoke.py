#!/usr/bin/env python3
"""Check the installed package without sign-in, devices or runtime effects."""
import json
from pathlib import Path
import platform
import subprocess
import time


def check_hardware(hardware):
    if not isinstance(hardware, list) or not 1 <= len(hardware) <= 64:
        raise ValueError("Installed CLI returned an invalid offline hardware list")
    paths, identities = set(), set()
    for profile in hardware:
        if not isinstance(profile, dict) or any(not isinstance(profile.get(key), str) or not profile[key] for key in ("board", "medium", "compatibility", "boot")) or not isinstance(profile.get("qualified"), bool):
            raise ValueError("Installed CLI returned an invalid offline hardware profile")
        path, identity = (profile["board"], profile["medium"]), profile["compatibility"]
        if path in paths or identity in identities:
            raise ValueError("Installed CLI returned duplicate offline hardware identities")
        paths.add(path)
        identities.add(identity)
    return len(hardware)


def check_notarization(binary, *, run=subprocess.run, now=time.monotonic, pause=time.sleep, budget=300, interval=15):
    deadline = now() + budget
    attempt = 0
    while True:
        remaining = deadline - now()
        if remaining <= 0:
            raise RuntimeError("Apple notarization ticket could not be verified within the retry deadline")
        attempt += 1
        try:
            result = run(["codesign", "--verify", "--strict", "--verbose=4", "-R=notarized", "--check-notarization", str(binary)], capture_output=True, text=True, timeout=min(30, remaining))
            if result.returncode == 0:
                return
        except subprocess.TimeoutExpired:
            pass
        remaining = deadline - now()
        if remaining > 0:
            print(f"Waiting for Apple's notarization ticket (attempt {attempt})", flush=True)
            pause(min(interval, remaining))


def main():
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
        check_notarization(binary)
    actual = subprocess.check_output([str(binary), "version"], text=True).strip()
    expected = f"iotk {manifest['version']} ({manifest['revision']})"
    if actual != expected:
        raise ValueError("Installed executable identity differs from the published build")
    hardware = json.loads(subprocess.check_output([str(binary), "hardware"], text=True))
    count = check_hardware(hardware)
    if not list((binary.resolve().parent / "licenses").glob("*-LICENSE.txt")):
        raise ValueError("Installed package lost upstream third-party notices")
    print(f"Native Homebrew package verified: {actual}; {count} hardware profiles and license notices")


if __name__ == "__main__":
    main()
