"""Scoped installation into NSS certificate databases.

NSS databases are used by Firefox, Chromium, Thunderbird and some other
applications.  Installing a certificate into a profile-specific NSS database
limits trust to that profile instead of the whole OS.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from russian_trusted_ca.exceptions import RussianTrustedCAError


def _run_certutil(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _find_certutil() -> str:
    certutil = shutil.which("certutil")
    if certutil is None:
        raise RussianTrustedCAError(
            "certutil not found; install nss-tools to manage NSS databases",
        )
    return certutil


def nss_profile_dirs() -> list[Path]:
    """Return common NSS database directories on Linux.

    Returns:
        List of paths that may contain cert9.db/cert8.db.
    """
    home = Path.home()
    candidates: list[Path] = []

    # Chromium / Google Chrome family
    for browser in (".pki", ".config/chromium", ".config/google-chrome",
                    ".config/chrome", ".config/vivaldi", ".config/opera"):
        base = home / browser
        if not base.exists():
            continue
        if browser == ".pki":
            candidates.append(base / "nssdb")
        else:
            candidates.extend(
                d for d in base.iterdir()
                if d.is_dir() and (d / "cert9.db").exists()
            )

    # Firefox
    firefox_dir = home / ".mozilla" / "firefox"
    if firefox_dir.exists():
        candidates.extend(
            d for d in firefox_dir.iterdir()
            if d.is_dir() and (d / "cert9.db").exists()
        )

    return sorted({str(p): p for p in candidates if p.exists()}.values())


def install_to_nss(
    cert_path: Path,
    *,
    profile_dir: Path | None = None,
    nickname: str = "Russian Trusted Root CA",
    trust: str = "C,,",
) -> None:
    """Install a certificate into an NSS database.

    Args:
        cert_path: path to PEM certificate.
        profile_dir: NSS database directory. If None, install into all found
            Chromium/Firefox profile databases.
        nickname: certificate nickname in the database.
        trust: trust attributes string (default: ``C,,`` = trusted CA for SSL).

    Raises:
        RussianTrustedCAError: if certutil is missing or operation fails.
    """
    certutil = _find_certutil()

    if profile_dir is not None:
        dirs = [profile_dir]
    else:
        dirs = nss_profile_dirs()
        if not dirs:
            raise RussianTrustedCAError(
                "No NSS databases found. "
                "Open Chromium/Firefox once or specify --nss-profile explicitly.",
            )

    for db_dir in dirs:
        db_dir.mkdir(parents=True, exist_ok=True)
        _run_certutil([
            certutil,
            "-A",
            "-d", f"sql:{db_dir}",
            "-n", nickname,
            "-t", trust,
            "-i", str(cert_path),
        ])
        print(f"Installed {nickname} into {db_dir}")


def remove_from_nss(
    *,
    profile_dir: Path | None = None,
    nickname: str = "Russian Trusted Root CA",
) -> None:
    """Remove a certificate from an NSS database.

    Args:
        profile_dir: NSS database directory. If None, remove from all found
            Chromium/Firefox profile databases.
        nickname: certificate nickname in the database.
    """
    certutil = _find_certutil()

    dirs = [profile_dir] if profile_dir is not None else nss_profile_dirs()

    for db_dir in dirs:
        try:
            _run_certutil([
                certutil,
                "-D",
                "-d", f"sql:{db_dir}",
                "-n", nickname,
            ])
            print(f"Removed {nickname} from {db_dir}")
        except subprocess.CalledProcessError as exc:
            msg = exc.stdout.strip()
            if "SEC_ERROR_BAD_DATABASE" in msg or "not found" in msg.lower():
                print(f"Not found in {db_dir}: {nickname}")
            else:
                raise
