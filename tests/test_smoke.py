import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location("smoke", Path(__file__).resolve().parents[1] / "scripts/smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


class HardwareTests(unittest.TestCase):
    def profiles(self, count):
        return [dict(board=f"board-{i}", medium="sd", compatibility=f"fixture-{i}", boot="fixture boot", qualified=False) for i in range(count)]

    def test_profile_count_can_grow_without_replacing_the_upstream_matrix(self):
        for count in (6, 8, 9, 64):
            with self.subTest(count=count):
                self.assertEqual(smoke.check_hardware(self.profiles(count)), count)

    def test_empty_unbounded_or_malformed_metadata_is_rejected(self):
        for hardware in (None, {}, [], self.profiles(65), [None], [{}], [dict(self.profiles(1)[0], qualified="false")]):
            with self.subTest(hardware=hardware):
                with self.assertRaises(ValueError):
                    smoke.check_hardware(hardware)

    def test_duplicate_paths_or_compatibility_identities_are_rejected(self):
        first, second = self.profiles(2)
        for profile in (dict(second, board=first["board"]), dict(second, compatibility=first["compatibility"])):
            with self.subTest(profile=profile):
                with self.assertRaisesRegex(ValueError, "duplicate"):
                    smoke.check_hardware([first, profile])


class TicketTests(unittest.TestCase):
    def test_ticket_propagation_retries_the_full_requirement_before_acceptance(self):
        elapsed, sleeps, calls = [0], [], []
        def run(args, **options):
            self.assertIn("-R=notarized", args)
            self.assertIn("--check-notarization", args)
            self.assertLessEqual(options["timeout"], 30)
            calls.append(args)
            return SimpleNamespace(returncode=0 if len(calls) == 3 else 3)
        def pause(seconds):
            sleeps.append(seconds); elapsed[0] += seconds
        smoke.check_notarization("/verified/iotk", run=run, now=lambda:elapsed[0], pause=pause)
        self.assertEqual(len(calls), 3)
        self.assertEqual(sleeps, [15, 15])

    def test_unverified_ticket_is_fatal_at_the_bounded_deadline(self):
        elapsed, calls = [0], []
        def run(args, **options):
            calls.append(args)
            return SimpleNamespace(returncode=3)
        def pause(seconds): elapsed[0] += seconds
        with self.assertRaisesRegex(RuntimeError, "retry deadline"):
            smoke.check_notarization("/verified/iotk", run=run, now=lambda:elapsed[0], pause=pause, budget=30, interval=10)
        self.assertEqual(elapsed[0], 30)
        self.assertEqual(len(calls), 3)

    def test_network_timeout_cannot_exceed_the_total_verification_budget(self):
        elapsed = [0]
        def run(args, **options):
            self.assertEqual(options["timeout"], 20)
            elapsed[0] += options["timeout"]
            raise subprocess.TimeoutExpired(args, options["timeout"])
        with self.assertRaisesRegex(RuntimeError, "retry deadline"):
            smoke.check_notarization("/verified/iotk", run=run, now=lambda:elapsed[0], pause=lambda _:self.fail("Budget exhausted"), budget=20)


if __name__ == "__main__":
    unittest.main()
