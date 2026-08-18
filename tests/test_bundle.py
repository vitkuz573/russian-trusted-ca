"""Tests for the scoped bundle command."""

from __future__ import annotations

from pathlib import Path

import pytest

from russian_trusted_ca.cli import main
from russian_trusted_ca.operations import build_bundle


@pytest.fixture()
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


def test_build_bundle_creates_file(monkeypatch, tmp_path: Path, fake_certs):
    root, sub = fake_certs

    def fake_download(url: str, dest: Path) -> None:
        if "root" in url:
            dest.write_bytes(root.read_bytes())
        else:
            dest.write_bytes(sub.read_bytes())

    monkeypatch.setattr("russian_trusted_ca.operations.download", fake_download)
    monkeypatch.setattr("russian_trusted_ca.operations.verify_certificate", lambda *args, **kwargs: None)

    output = tmp_path / "bundle.pem"
    build_bundle(output)

    assert output.exists()
    text = output.read_text()
    assert "BEGIN CERTIFICATE" in text
    assert text.count("BEGIN CERTIFICATE") == 2


def test_cli_bundle(monkeypatch, tmp_path: Path, fake_certs):
    root, sub = fake_certs
    output = tmp_path / "cli-bundle.pem"

    def fake_download(url: str, dest: Path) -> None:
        if "root" in url:
            dest.write_bytes(root.read_bytes())
        else:
            dest.write_bytes(sub.read_bytes())

    monkeypatch.setattr("russian_trusted_ca.operations.download", fake_download)
    monkeypatch.setattr("russian_trusted_ca.operations.verify_certificate", lambda *args, **kwargs: None)
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
    assert output.read_text().count("BEGIN CERTIFICATE") == 2


def _run_openssl(args: list[str]) -> None:
    import subprocess
    subprocess.run(
        ["openssl", *args],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
