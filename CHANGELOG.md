# Changelog

## Unreleased

### Added

- `bundle` command: build a scoped CA bundle without modifying the system trust
  store.
- `bundle --print-path`: print the default bundle path for shell scripts.
- `bundle --install-nss` and `nss-install` / `nss-uninstall` commands: scoped
  installation into Firefox / Chromium NSS profiles using `certutil`.
- `check --bundle`: verify TLS handshake against a scoped CA bundle.
- `audit` command with `--fix` flag: verify installed certificates by
  fingerprint and reinstall if needed.
- `list` command: list installed system CA certificates with optional filter.
- `install --backup`: create a timestamped backup of anchors before installation.
- `README_EN.md` with full English documentation.
- Synchronized Russian `README.md` with full command reference and examples.
- Added project badges and table of contents to README files.
- `SECURITY.md` with certificate analysis, local MITM PoC and risk assessment.

## 1.0.0 — 2026-08-18

- Initial release.
- Install/uninstall Russian Trusted Root CA and Sub CA certificates.
- Automatic download from official Gosuslugi CDN with SHA-256 fingerprint verification.
- Support for Arch Linux/Fedora (`update-ca-trust`) and Debian/Ubuntu (`update-ca-certificates`).
- CLI commands: `install`, `uninstall`, `status`, `check`.
