# Homebrew tap instructions

- Keep this repository public and limited to packaging, public release metadata
  and update tooling. Do not copy private IoTKit source or credentials here.
- Generate `Casks/iotk.rb` and `release.json` with `scripts/update.py`; use
  immutable Cloudflare download URLs and verify upstream publication bytes.
- Preserve third-party notices. Do not assign an open-source license to the
  upstream CLI; its licensing is independent of this tap.
- macOS packages must retain hardened-runtime Developer ID signatures for team
  `X7RWL5MAV2`, identifier `io.iotkit.iotk`, secure timestamps and accepted Apple
  notarization. Preserve Homebrew quarantine and verify Gatekeeper before running.
- Development package versions must order upgrades by upstream build run number.
  Never replace immutable build identities or silently downgrade packages.
- Run updater tests and a real native `brew install` plus `scripts/smoke.py` before publishing
  a changed package. Distinguish native tests from cross-architecture verification.
- Use Conventional Commits on one linear `main` chain. Do not push without user
  authorization; the committed update workflow is authorized to publish its
  verified package updates with its repository-scoped token.
- At the end of a turn, propose useful instruction corrections or additions.
