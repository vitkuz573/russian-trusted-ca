"""Tests for NSS profile installation helpers."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from russian_trusted_ca.exceptions import RussianTrustedCAError
from russian_trusted_ca.nss import (
    install_to_nss,
    nss_profile_dirs,
    remove_from_nss,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def test_find_certutil_missing(monkeypatch: MonkeyPatch) -> None:
    """_find_certutil should raise when certutil is not in PATH."""
    monkeypatch.setattr(shutil, "which", lambda _cmd: None)
    with pytest.raises(RussianTrustedCAError):
        install_to_nss(Path("/dev/null"))


def test_nss_profile_dirs_finds_chromium_and_firefox(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
) -> None:
    """nss_profile_dirs should discover Chromium and Firefox NSS databases."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    pki = tmp_path / ".pki" / "nssdb"
    pki.mkdir(parents=True)
    (pki / "cert9.db").write_text("")

    chromium = tmp_path / ".config" / "chromium" / "Default"
    chromium.mkdir(parents=True)
    (chromium / "cert9.db").write_text("")

    firefox = tmp_path / ".mozilla" / "firefox" / "abc123.default"
    firefox.mkdir(parents=True)
    (firefox / "cert9.db").write_text("")

    dirs = nss_profile_dirs()
    assert len(dirs) == 3


def test_nss_profile_dirs_empty(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """nss_profile_dirs should return an empty list when no databases exist."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    assert nss_profile_dirs() == []


def test_install_to_nss_with_profile_dir(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """install_to_nss should import the certificate into the specified profile."""
    cert = tmp_path / "ca.pem"
    cert.write_text("cert")
    profile = tmp_path / "profile"
    profile.mkdir()

    calls = []

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/certutil")
    monkeypatch.setattr(subprocess, "run", fake_run)

    install_to_nss(cert, profile_dir=profile)

    assert len(calls) == 1
    assert calls[0][0] == "/usr/bin/certutil"
    assert "-A" in calls[0]


def test_install_to_nss_auto_detect_no_profiles(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    """install_to_nss should raise when no profiles are found and none specified."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/certutil")
    cert = tmp_path / "ca.pem"
    cert.write_text("cert")
    with pytest.raises(RussianTrustedCAError):
        install_to_nss(cert)


def test_remove_from_nss_success(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """remove_from_nss should delete the certificate from the profile."""
    profile = tmp_path / "profile"
    profile.mkdir()

    calls = []

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/certutil")
    monkeypatch.setattr(subprocess, "run", fake_run)

    remove_from_nss(profile_dir=profile)

    assert len(calls) == 1
    assert calls[0][0] == "/usr/bin/certutil"
    assert "-D" in calls[0]


def test_remove_from_nss_not_found(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys
) -> None:
    """remove_from_nss should handle SEC_ERROR_BAD_DATABASE gracefully."""
    profile = tmp_path / "profile"
    profile.mkdir()

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(
            1,
            cmd,
            output="SEC_ERROR_BAD_DATABASE",
        )

    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/certutil")
    monkeypatch.setattr(subprocess, "run", fake_run)

    remove_from_nss(profile_dir=profile)
    captured = capsys.readouterr()
    assert "Not found" in captured.out


def test_remove_from_nss_other_error(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    """remove_from_nss should re-raise unexpected certutil errors."""
    profile = tmp_path / "profile"
    profile.mkdir()

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd, output="unknown error")

    monkeypatch.setattr(shutil, "which", lambda _cmd: "/usr/bin/certutil")
    monkeypatch.setattr(subprocess, "run", fake_run)

    with pytest.raises(subprocess.CalledProcessError):
        remove_from_nss(profile_dir=profile)
