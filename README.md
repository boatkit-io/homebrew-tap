# IoTKit Homebrew tap

Install the IoTKit CLI on macOS or Linux, with Apple Silicon/ARM64 or Intel/AMD64:

```sh
brew install boatkit-io/tap/iotk
iotk version
iotk login --team YOUR_TEAM
```

Upgrade or remove it through Homebrew:

```sh
brew update
brew upgrade iotk
brew uninstall iotk
```

The tap contains a binary cask, so installing the published executable requires
no compiler toolchain. Executables and third-party notices come
from immutable, public Cloudflare-hosted IoTKit downloads. Downloading requires
no account; management operations require your normal IoTKit sign-in and team
permissions. No Go, Node.js or container engine is required to run the CLI.

Existing manual installations may take precedence over Homebrew in your PATH.
Use `command -v iotk` and `brew list --cask iotk` to check which installation you run.

## Versions and updates

The tap follows the latest fully validated and published CLI build. Until
upstream provides stable CLI versions, Homebrew versions are `0.0.0-dev.N`,
where `N` is the upstream build run number. This orders upgrades reliably;
`iotk version` reports the original upstream version and exact source revision.
`release.json` records the public upstream identity used by the package.

The update workflow checks hourly and can also be started manually from Actions.
It verifies the exact manifest identity and the size and SHA-256 of all four
macOS/Linux archives, installs and tests the native macOS package with its
Developer ID signature and Gatekeeper assessment, then commits the new package.
Apple's standalone-code notarization check retries ticket propagation for up to
five minutes; it still fails closed if the ticket cannot be verified.
Unchanged builds do not re-download the archives. Publication
uses only this tap's repository token; it has no private source or IoTKit/cloud
credentials. Older builds and changed identities for an existing run are rejected.

To update locally:

```sh
python3 -m unittest discover -s tests
python3 scripts/update.py
python3 scripts/smoke.py
```

Windows ZIP downloads are available through IoTKit's public download API; this
Homebrew package covers macOS and Linux. Native Linux execution and every CPU
architecture are separate qualification checks; archive verification alone does
not qualify execution on that platform. macOS packages use BoatKit, LLC.'s
Developer ID Application identity (team `X7RWL5MAV2`) and Apple notarization.
Normal Homebrew quarantine remains enabled; the tap does not bypass Gatekeeper.
