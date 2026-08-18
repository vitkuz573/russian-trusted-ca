"""Tests for the scoped bundle command."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from russian_trusted_ca.cli import main
from russian_trusted_ca.operations import build_bundle

if TYPE_CHECKING:
    from pytest import MonkeyPatch

EXPECTED_CERT_COUNT = 2


@pytest.fixture
def fake_certs(tmp_path: Path) -> tuple[Path, Path]:
    """Return a pair of valid self-signed certs that look like the official ones."""
    root = tmp_path / "root-ca.pem"
    sub = tmp_path / "sub-ca.pem"
    root_key = tmp_path / "root-key.pem"
    sub_key = tmp_path / "sub-key.pem"

    _run_openssl([
        "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(root_key), "-out", str(root),
        "-days", "1", "-nodes",
        "-subj", "/CN=Russian Trusted Root CA",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    ])

    _run_openssl([
        "req", "-x509", "-newkey", "rsa:2048",
        "-keyout", str(sub_key), "-out", str(sub),
        "-days", "1", "-nodes",
        "-subj", "/CN=Russian Trusted Sub CA",
        "-addext", "basicConstraints=critical,CA:TRUE",
        "-addext", "keyUsage=critical,keyCertSign,cRLSign",
    ])

    return root, sub


def _fake_download_factory(root: Path, sub: Path):
    """Return a download function that copies the fixture certs."""
    def fake_download(url: str, dest: Path) -> None:
        if "root" in url:
            dest.write_bytes(root.read_bytes())
        else:
            dest.write_bytes(sub.read_bytes())

    return fake_download


def test_build_bundle_creates_file(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    fake_certs: tuple[Path, Path],
) -> None:
    """build_bundle should write a PEM bundle containing both certificates."""
    root, sub = fake_certs

    monkeypatch.setattr(
        "russian_trusted_ca.operations.download",
        _fake_download_factory(root, sub),
    )
    monkeypatch.setattr(
        "russian_trusted_ca.operations.verify_certificate",
        lambda _path, _cn, _fp: None,
    )

    output = tmp_path / "bundle.pem"
    build_bundle(output)

    assert output.exists()
    text = output.read_text()
    assert "BEGIN CERTIFICATE" in text
    assert text.count("BEGIN CERTIFICATE") == EXPECTED_CERT_COUNT


def test_cli_bundle(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    fake_certs: tuple[Path, Path],
) -> None:
    """The bundle CLI subcommand should produce the bundle file."""
    root, sub = fake_certs
    output = tmp_path / "cli-bundle.pem"

    monkeypatch.setattr(
        "russian_trusted_ca.operations.download",
        _fake_download_factory(root, sub),
    )
    monkeypatch.setattr(
        "russian_trusted_ca.operations.verify_certificate",
        lambda _path, _cn, _fp: None,
    )
    monkeypatch.setattr("russian_trusted_ca.cli.platform.system", lambda: "Linux")
    monkeypatch.setattr(
        "russian_trusted_ca.distro.detect_distro",
        lambda: type("Distro", (), {
            "name": "test",
            "anchors_dir": tmp_path,
            "update_cmd": ["update-certs"],
            "cert_ext": ".crt",
        })(),
    )

    assert main(["bundle", "-o", str(output)]) == 0
    assert output.exists()
    assert output.read_text().count("BEGIN CERTIFICATE") == EXPECTED_CERT_COUNT


def _run_openssl(args: list[str]) -> None:
    subprocess.run(
        ["openssl", *args],
        check=True,
        capture_output=True,
    )
