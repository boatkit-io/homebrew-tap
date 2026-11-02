import importlib.util
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest

spec = importlib.util.spec_from_file_location("smoke", Path(__file__).resolve().parents[1] / "scripts/smoke.py")
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)


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
