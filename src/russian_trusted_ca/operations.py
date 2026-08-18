"""High-level install/uninstall/status operations."""

from __future__ import annotations

import socket
import ssl
import subprocess
import tempfile
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


def install_certificates(distro: DistroInfo, *, force: bool = False) -> None:
    """Download and install Russian Trusted CA certificates.

    Args:
        distro: detected distribution layout.
        force: reinstall even if already present.
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
    print(f"Root CA:             {paths.root_cert}  "
          f"{'present' if paths.root_cert.exists() else 'missing'}")
    print(f"Sub CA:              {paths.sub_cert}   "
          f"{'present' if paths.sub_cert.exists() else 'missing'}")
    return 0 if paths.is_installed() else 1


def check_connection(host: str, port: int = 443) -> int:
    """Verify TLS handshake with the default system trust store.

    Args:
        host: hostname to connect to.
        port: TCP port.

    Returns:
        0 on success, 1 on failure.
    """
    print(f"Checking TLS connection to {host}:{port} ...")
    context = ssl.create_default_context()
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=host) as tls_sock:
                cert = tls_sock.getpeercert()
                print(f"OK - TLS {tls_sock.version()} with {cert.get('subject')}")
                return 0
    except ssl.SSLError as exc:
        print(f"FAILED - SSL error: {exc.reason}")
        return 1
    except OSError as exc:
        print(f"FAILED - connection error: {exc}")
        return 1
