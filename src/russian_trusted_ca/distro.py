"""Linux distribution detection for CA trust layouts."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from russian_trusted_ca.exceptions import DistroDetectionError


@dataclass(frozen=True)
class DistroInfo:
    """Description of a Linux distribution CA trust layout."""

    name: str
    anchors_dir: Path
    update_cmd: list[str]
    cert_ext: str


class CertPaths:
    """Resolved paths for installed certificate files."""

    def __init__(self, distro: DistroInfo) -> None:
        self.root_cert = distro.anchors_dir / f"{self._root_name}{distro.cert_ext}"
        self.sub_cert = distro.anchors_dir / f"{self._sub_name}{distro.cert_ext}"

    _root_name = "russian-trusted-root-ca"
    _sub_name = "russian-trusted-sub-ca"

    def is_installed(self) -> bool:
        """Return True when both certificate files are present."""
        return self.root_cert.exists() and self.sub_cert.exists()


def detect_distro() -> DistroInfo:
    """Detect the CA trust layout of the current Linux distribution.

    Returns:
        DistroInfo with anchors directory and update command.

    Raises:
        DistroDetectionError: if the distribution layout is not recognised.
    """
    # Arch Linux / Fedora-like with update-ca-trust
    if Path("/etc/ca-certificates/trust-source/anchors").is_dir():
        update_cmd = ["update-ca-trust"]
        if shutil.which("update-ca-trust") is None:  # pragma: no cover
            update_cmd = ["/usr/bin/update-ca-trust"]
        return DistroInfo(
            name="ca-trust (Arch/Fedora)",
            anchors_dir=Path("/etc/ca-certificates/trust-source/anchors"),
            update_cmd=update_cmd,
            cert_ext=".crt",
        )

    # Debian/Ubuntu with update-ca-certificates
    if Path("/usr/local/share/ca-certificates").is_dir():  # pragma: no cover
        return DistroInfo(
            name="ca-certificates (Debian/Ubuntu)",
            anchors_dir=Path("/usr/local/share/ca-certificates"),
            update_cmd=["update-ca-certificates"],
            cert_ext=".crt",
        )

    raise DistroDetectionError(
        "Unsupported Linux distribution; cannot find CA anchors directory",
    )  # pragma: no cover
