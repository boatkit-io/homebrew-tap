import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("update", Path(__file__).resolve().parents[1] / "scripts/update.py")
updater = importlib.util.module_from_spec(spec)
spec.loader.exec_module(updater)


def fixture(number=1):
    artifacts, payloads = [], {}
    for target in sorted(updater.TARGETS):
        name = f"iotk-0.0.0-dev.{'a' * 12}-{target}." + ("zip" if target.startswith("windows-") else "tar.gz")
        payloads[name] = target.encode()
        digest = hashlib.sha256(payloads[name]).hexdigest()
        artifacts.append(dict(target=target, file=name, size=len(payloads[name]), sha256=digest, binarySha256=digest))
    manifest = dict(schemaVersion=1, name="iotk", version="0.0.0-dev." + "a" * 12, revision="a" * 40, clean=True, artifacts=artifacts)
    raw = json.dumps(manifest).encode()
    identity = hashlib.sha256(raw).hexdigest()
    release = dict(id=identity, manifest=manifest, provenance=dict(repository="boatkit-io/iotkit", buildRunNumber=number))
    payloads["manifest.json"] = raw
    prefix = f"/v1/cli-downloads/{identity}/"

    def read(path, limit):
        if path == "/v1/cli-releases":
            return json.dumps(dict(latest=release)).encode()
        assert path.startswith(prefix)
        return payloads[path[len(prefix):]]
    return release, payloads, read


class UpdateTests(unittest.TestCase):
    def test_verified_update_and_unchanged_run_avoid_repeated_downloads(self):
        release, _, read = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(updater.update(root, read))
            package = (root / "Casks/iotk.rb").read_text()
            self.assertIn('version "0.0.0-dev.1"', package)
            self.assertEqual(package.count('      url "https://api.iotkit.io/v1/cli-downloads/'), 4)
            self.assertIn('binary "iotk"', package)
            self.assertNotIn("def install", package)
            self.assertNotIn("windows-", package)
            def unchanged(path, limit):
                self.assertEqual(path, "/v1/cli-releases")
                return read(path, limit)
            self.assertFalse(updater.update(root, unchanged))

    def test_corrupt_payload_or_manifest_never_writes_a_package(self):
        for name in ("manifest.json", "iotk-0.0.0-dev." + "a" * 12 + "-darwin-amd64.tar.gz"):
            _, payloads, read = fixture()
            payloads[name] += b"corrupt"
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                with self.assertRaises((ValueError, json.JSONDecodeError)):
                    updater.update(root, read)
                self.assertFalse((root / "Casks/iotk.rb").exists())

    def test_catalog_cannot_substitute_paths_checksums_or_repository(self):
        release, _, _ = fixture()
        for change in ("path", "checksum", "dirty", "repository", "missing", "version"):
            bad = copy.deepcopy(release)
            if change == "path": bad["manifest"]["artifacts"][0]["file"] = "../private"
            if change == "checksum": bad["manifest"]["artifacts"][0]["sha256"] = "wrong"
            if change == "dirty": bad["manifest"]["clean"] = False
            if change == "repository": bad["provenance"]["repository"] = "someone/else"
            if change == "missing": bad["manifest"]["artifacts"].pop()
            if change == "version": bad["manifest"]["version"] = '#{system("false")}'
            with self.subTest(change=change), self.assertRaises(ValueError):
                updater.validate(bad)

    def test_older_build_or_replaced_identity_cannot_overwrite_current_package(self):
        current, _, read = fixture(3)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            updater.update(root, read)
            before = (root / "Casks/iotk.rb").read_text()
            _, _, older = fixture(2)
            with self.assertRaisesRegex(ValueError, "downgrade"):
                updater.update(root, older)
            bad = copy.deepcopy(current)
            bad["id"] = "b" * 64
            with self.assertRaisesRegex(ValueError, "immutable"):
                updater.update(root, lambda path, limit: json.dumps(dict(latest=bad)).encode())
            self.assertEqual((root / "Casks/iotk.rb").read_text(), before)

    def test_stable_versions_and_unknown_channels(self):
        release, _, _ = fixture(100)
        release["manifest"]["version"] = "v0.1.0"
        self.assertEqual(updater.package_version(release), "0.1.0")
        release["manifest"]["version"] = "unrecognized-channel"
        with self.assertRaisesRegex(ValueError, "version ordering"):
            updater.package_version(release)


if __name__ == "__main__":
    unittest.main()
