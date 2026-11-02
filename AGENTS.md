# Homebrew tap instructions

- Keep this repository public and limited to packaging, public release metadata
  and update tooling. Do not copy private IoTKit source or credentials here.
- Generate `Formula/iotk.rb` and `release.json` with `scripts/update.py`; use
  immutable Cloudflare download URLs and verify upstream publication bytes.
- Preserve third-party notices. Do not assign an open-source license to the
  upstream CLI; its licensing is independent of this tap.
- Development package versions must order upgrades by upstream build run number.
  Never replace immutable build identities or silently downgrade packages.
- Run updater tests and a real native `brew install`/`brew test` before publishing
  a changed formula. Distinguish native tests from cross-architecture verification.
- Use Conventional Commits on one linear `main` chain. Do not push without user
  authorization; the committed update workflow is authorized to publish its
  verified formula updates with its repository-scoped token.
- At the end of a turn, propose useful instruction corrections or additions.
