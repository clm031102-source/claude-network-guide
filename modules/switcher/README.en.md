> This directory is an independent source reference for the advanced component. See [NOTICE](../../NOTICE.md) for attribution and the pinned upstream revision. Start with the [main tutorial and local preflight workbench](../../README.md). This repository has not published native installers or a hosted version of the legacy check page. Retained capabilities are not a claim of completed cross-platform validation.

<div align="center">

# ClaudeSwitcher

**A fail-closed local environment manager for multiple Claude accounts**

[中文](README.md) · [Source ZIP](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip) · [Issues](https://github.com/clm031102-source/claude-network-guide/issues)

<img src="assets/icon-2048.png" width="120">

</div>

---

## What it is

ClaudeSwitcher keeps several Claude accounts on one Mac without letting their
local state mix. Each account has its own device fingerprint, sign-in
credentials, and application data; switching swaps those directories atomically
instead of signing out and back in.

Before Claude starts, the app runs a 14-point audit of the machine's network and
regional environment. If a blocking check fails, the app is not launched. A
resident bodyguard stops the protected application when the tunnel drops,
closing the window in which traffic could leave outside the proxy.

## Features

- **14-point preflight audit** — proxy core, TUN interface, exit country, IP stability, time zone, locale, IPv6, DNS leakage, WebRTC candidates, bodyguard status, pinned routing, browser language, ASN type, and Claude reachability.
- **Snapshot switching** — archives and restores whole account directories; APFS copy-on-write cloning avoids duplicating unchanged data.
- **Fail-closed bodyguard** — checks the proxy kernel and virtual interface every ten seconds and terminates protected processes when the tunnel is lost.
- **Drift watchdog** — records a baseline for time zone and proxy settings and rolls back silent changes made by other software.
- **Multiple proxy clients** — detects Clash Verge, Shadowrocket, sing-box, ClashX, and Surge, with an automatic mode; non-Clash clients keep their own configuration.
- **Region adaptation** — captures the exit country, time zone, and locale at install time and re-locks all three after moving to a different node.
- **Pinned routing** — places Claude domains and supporting services above third-party rule sets.
- **WebRTC leak probe** — a standard-library STUN client that compares global and local vantage points to distinguish a proxied path from a direct one.
- **Automatic updates** — a user-level launchd agent checks every 12 hours, verifies artifact hashes, and rolls back if the post-update self-check fails.
- **Diagnostics** — a standalone proxy check reports transport results for the Claude web and API endpoints without reading account data.
- **Native menu bar UI** — a single-file SwiftUI app with no Xcode project and no third-party dependencies.
- **Web check page** — a static browser-side check for exit IP, time zone, language, WebRTC, IPv6, and common fingerprint signals.
- **Windows and Linux ports (beta)** — PowerShell and bash implementations with the same audit and switching model.

## Install

### Current distribution: source only

No native release of this component has been published in this repository. [Download the repository source](https://github.com/clm031102-source/claude-network-guide/archive/refs/heads/main.zip) or clone it below. For the main workflow, use the root project's local preflight workbench. Native update buttons cannot download an unpublished package.

The following are retained build artifact conventions for maintainers; they are not currently available downloads:

| Asset | Use |
|---|---|
| `ClaudeSwitcher-<version>-installer-kit.zip` | Full first-time install. Unzip and double-click `installer/安装.command`; it installs the core script, daemons, and desktop app. |
| `ClaudeSwitcher-<version>-macos-arm64-app-only.dmg` / `.zip` | The macOS app bundle only (no core scripts); for machines where the core is already installed. First-time installs should use the installer kit. |
| `ClaudeSwitcher-<version>-windows.zip` | Windows scripts (beta). See `windows/README.md`. |
| `ClaudeSwitcher-<version>-linux.tar.gz` | Linux scripts (beta). See `linux/README.md`. |

Locally built macOS artifacts use ad-hoc signing and are not notarized; verify their source before opening them. A future native release should include `SHA256SUMS-release.txt` for integrity checks. No native release or release checksum file is currently published here.

Requirements: macOS 13 or later, a proxy client with TUN support, the Claude
desktop app, and Python 3.

### From source

```bash
git clone https://github.com/clm031102-source/claude-network-guide.git
cd claude-network-guide/modules/switcher
# Then double-click installer/安装.command
```

The installer detects the proxy client, proxy group, and regional target, then
builds the desktop app locally. To build and package manually:

```bash
bash scripts/package-macos.sh 1.0.0
```

Artifacts are written to `build/`.

## Usage

1. Open **Claude网络指南账号工具** and wait for the 14 checks.
2. If everything is green, choose an account and launch Claude. If a blocking
   check is red, use the one-click repair action.
3. Sign in once for each additional account; later switches keep sessions
   independent.
4. After changing to a node in another country, run
   `~/.local/bin/claude-switch.sh set-region`.

The full command set, menu bar behavior, and troubleshooting notes are in the
[Chinese README](README.md) and [advanced installation reference](docs/agent-install-reference.md).

## Disclaimer

This project is intended for managing the local environment and sign-in state of
multiple Claude accounts in supported regions, for people who are traveling,
living abroad, or otherwise legitimately located in a supported region. Please
follow Anthropic's Terms of Service. Do not use it for account resale, account
sharing, registering accounts on behalf of others, or circumventing regional
restrictions.

Local environment checks only inspect and configure this machine. They do not
change server-side records and do not guarantee that an account will not be
restricted. The software is provided as-is under the MIT license; you are
responsible for how you use it.

## Links

- [中文说明](README.md)
- [Repository source](https://github.com/clm031102-source/claude-network-guide/tree/main/modules/switcher)
- [Issues](https://github.com/clm031102-source/claude-network-guide/issues)
- [Security policy](SECURITY.md)
- [Advanced installation reference](docs/agent-install-reference.md)
- [Legacy web check source and local preview](docs/WEB-README.md)
- [Windows beta](windows/README.md) · [Linux beta](linux/README.md)

## License

MIT © ClaudeSwitcher Contributors
