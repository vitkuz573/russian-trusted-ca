"""High-level install/uninstall/status operations."""

from __future__ import annotations

import shutil
import socket
import ssl
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from russian_trusted_ca.constants import (
    ROOT_CA_FINGERPRINT,
    ROOT_CA_SUBJECT,
    ROOT_CA_URL,
    SUB_CA_FINGERPRINT,
    SUB_CA_SUBJECT,
    SUB_CA_URL,
)
from russian_trusted_ca.distro import CertPaths, DistroInfo
from russian_trusted_ca.download import download
from russian_trusted_ca.verify import verify_certificate


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _fingerprint(path: Path) -> str:
    """Return SHA-256 fingerprint of a PEM certificate."""
    result = _run(
        ["openssl", "x509", "-in", str(path), "-noout", "-fingerprint", "-sha256"],
    )
    return result.stdout.strip().split("=", 1)[-1]


def _backup_dir() -> Path:
    return Path.home() / ".local" / "share" / "russian-trusted-ca" / "backups"


def install_certificates(
    distro: DistroInfo,
    *,
    force: bool = False,
    backup: bool = False,
) -> None:
    """Download and install Russian Trusted CA certificates.

    Args:
        distro: detected distribution layout.
        force: reinstall even if already present.
        backup: save a timestamped copy of anchors before changing them.
    """
    paths = CertPaths(distro)
    if paths.is_installed() and not force:
        print("Russian Trusted CA certificates are already installed.")
        print(f"  {paths.root_cert}")
        print(f"  {paths.sub_cert}")
        return

    if not distro.anchors_dir.exists():
        raise FileNotFoundError(
            f"Anchors directory does not exist: {distro.anchors_dir}",
        )

    if backup:
        backup_path = _backup_dir() / datetime.now(timezone.utc).strftime(
            "%Y%m%d%H%M%S",
        )
        backup_path.mkdir(parents=True, exist_ok=True)
        for cert in (paths.root_cert, paths.sub_cert):
            if cert.exists():
                shutil.copy2(cert, backup_path / cert.name)
                print(f"Backed up {cert} -> {backup_path / cert.name}")

    with tempfile.TemporaryDirectory(prefix="russian_trusted_ca_") as tmp:
        tmp_root = Path(tmp) / "root-ca.pem"
        tmp_sub = Path(tmp) / "sub-ca.pem"

        print(f"Downloading root CA from {ROOT_CA_URL} ...")
        download(ROOT_CA_URL, tmp_root)
        print(f"Downloading sub CA from {SUB_CA_URL} ...")
        download(SUB_CA_URL, tmp_sub)

        print("Verifying downloaded certificates ...")
        verify_certificate(tmp_root, ROOT_CA_SUBJECT, ROOT_CA_FINGERPRINT)
        verify_certificate(tmp_sub, SUB_CA_SUBJECT, SUB_CA_FINGERPRINT)

        print(f"Installing certificates to {distro.anchors_dir} ...")
        _run(["sudo", "cp", str(tmp_root), str(paths.root_cert)])
        _run(["sudo", "cp", str(tmp_sub), str(paths.sub_cert)])

    print(f"Updating system CA trust ({' '.join(distro.update_cmd)}) ...")
    _run(["sudo", *distro.update_cmd])

    print("Russian Trusted CA certificates installed successfully.")


def uninstall_certificates(distro: DistroInfo) -> None:
    """Remove Russian Trusted CA certificates from the system trust store.

    Args:
        distro: detected distribution layout.
    """
    paths = CertPaths(distro)
    removed = False
    for cert in (paths.root_cert, paths.sub_cert):
        if cert.exists():
            print(f"Removing {cert} ...")
            _run(["sudo", "rm", "-f", str(cert)])
            removed = True
        else:
            print(f"Not found: {cert}")

    if removed:
        print(f"Updating system CA trust ({' '.join(distro.update_cmd)}) ...")
        _run(["sudo", *distro.update_cmd])
        print("Russian Trusted CA certificates removed successfully.")
    else:
        print("Nothing to remove.")


def print_status(distro: DistroInfo) -> int:
    """Print installation status and return exit code.

    Args:
        distro: detected distribution layout.

    Returns:
        0 if both certificates are installed, 1 otherwise.
    """
    paths = CertPaths(distro)
    print(f"Distribution layout: {distro.name}")
    print(f"Anchors directory:   {distro.anchors_dir}")
    print(
        f"Root CA:             {paths.root_cert}  "
        f"{'present' if paths.root_cert.exists() else 'missing'}"
    )
    print(
        f"Sub CA:              {paths.sub_cert}   "
        f"{'present' if paths.sub_cert.exists() else 'missing'}"
    )
    return 0 if paths.is_installed() else 1


def audit_certificates(distro: DistroInfo, *, fix: bool = False) -> int:
    """Verify installed certificates match the expected fingerprints.

    Args:
        distro: detected distribution layout.
        fix: re-download and reinstall certificates if fingerprints mismatch.

    Returns:
        0 if certificates are valid or successfully fixed, 1 otherwise.
    """
    paths = CertPaths(distro)
    expected = {
        paths.root_cert: (ROOT_CA_FINGERPRINT, ROOT_CA_SUBJECT),
        paths.sub_cert: (SUB_CA_FINGERPRINT, SUB_CA_SUBJECT),
    }
    ok = True

    for cert, (expected_fp, expected_subj) in expected.items():
        if not cert.exists():
            print(f"MISSING: {cert}")
            ok = False
            continue

        try:
            verify_certificate(cert, expected_subj, expected_fp)
            print(f"OK:      {cert}")
        except Exception as exc:  # noqa: BLE001
            print(f"BAD:     {cert} - {exc}")
            ok = False

    if not ok and fix:
        print("Attempting to fix installed certificates ...")
        install_certificates(distro, force=True)
        return audit_certificates(distro, fix=False)

    if ok:
        print("Audit passed.")
    else:
        print("Audit failed. Run with --fix to reinstall.")

    return 0 if ok else 1


def list_system_cas(distro: DistroInfo, filter_text: str = "") -> int:
    """List installed system CA certificates.

    Args:
        distro: detected distribution layout.
        filter_text: optional substring to filter subjects.

    Returns:
        0 always.
    """
    bundle = distro.anchors_dir
    if not bundle.exists():
        print(f"Anchors directory not found: {bundle}")
        return 0

    for cert_file in sorted(bundle.glob(f"*{distro.cert_ext}")):
        try:
            subject = _run(
                ["openssl", "x509", "-in", str(cert_file), "-noout", "-subject"],
            ).stdout.strip()
            if not filter_text or filter_text in subject:
                print(f"{cert_file.name}: {subject}")
        except subprocess.CalledProcessError:
            continue

    return 0


def check_connection(
    host: str,
    port: int = 443,
    *,
    bundle: Path | None = None,
) -> int:
    """Verify TLS handshake.

    Args:
        host: hostname to connect to.
        port: TCP port.
        bundle: optional scoped CA bundle to use instead of the system store.

    Returns:
        0 on success, 1 on failure.
    """
    print(f"Checking TLS connection to {host}:{port} ...")
    if bundle is not None:
        print(f"Using CA bundle: {bundle}")
        context = ssl.create_default_context(cafile=str(bundle))
    else:
        context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert()
                subject = cert.get("subject") if cert else None
                print(f"OK - TLS {tls_sock.version()} with {subject}")
                return 0
    except ssl.SSLError as exc:
        print(f"FAILED - SSL error: {exc.reason}")
        return 1
    except OSError as exc:
        print(f"FAILED - connection error: {exc}")
        return 1


def build_bundle(output: Path) -> None:
    """Download, verify, and bundle certificates without touching the system store.

    The resulting PEM bundle can be used with ``curl --cacert``,
    ``ssl.create_default_context(cafile=...)`` or imported into a single browser
    profile. It is not installed into the OS-wide trust store.

    Args:
        output: destination path for the PEM bundle.
    """
    output.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="russian_trusted_ca_bundle_") as tmp:
        tmp_root = Path(tmp) / "root-ca.pem"
        tmp_sub = Path(tmp) / "sub-ca.pem"

        print(f"Downloading root CA from {ROOT_CA_URL} ...")
        download(ROOT_CA_URL, tmp_root)
        print(f"Downloading sub CA from {SUB_CA_URL} ...")
        download(SUB_CA_URL, tmp_sub)

        print("Verifying downloaded certificates ...")
        verify_certificate(tmp_root, ROOT_CA_SUBJECT, ROOT_CA_FINGERPRINT)
        verify_certificate(tmp_sub, SUB_CA_SUBJECT, SUB_CA_FINGERPRINT)

        print(f"Writing bundle to {output} ...")
        output.write_text(tmp_root.read_text() + "\n" + tmp_sub.read_text())

    print("Bundle created successfully.")
    print(f"  {output}")
    print("Use it with: curl --cacert <bundle> https://online.sberbank.ru/")
    print("Or import it into a single browser profile.")
