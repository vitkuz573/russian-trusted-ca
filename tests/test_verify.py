"""Tests for certificate verification."""

import subprocess
from pathlib import Path

import pytest

from russian_trusted_ca.exceptions import VerificationError
from russian_trusted_ca.verify import verify_certificate


@pytest.fixture()
def valid_self_signed(tmp_path: Path) -> Path:
    cert = tmp_path / "cert.pem"
    subprocess.run(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-keyout",
            str(tmp_path / "key.pem"),
            "-out",
            str(cert),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=Russian Trusted Root CA",
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return cert


def test_verify_certificate_valid_subject(valid_self_signed: Path):
    fingerprint = _fingerprint(valid_self_signed)
    verify_certificate(valid_self_signed, "Russian Trusted Root CA", fingerprint)


def test_verify_certificate_bad_subject(valid_self_signed: Path):
    fingerprint = _fingerprint(valid_self_signed)
    with pytest.raises(VerificationError):
        verify_certificate(valid_self_signed, "Wrong CA", fingerprint)


def test_verify_certificate_bad_fingerprint(valid_self_signed: Path):
    with pytest.raises(VerificationError):
        verify_certificate(valid_self_signed, "Russian Trusted Root CA", "00:" * 32)


def _fingerprint(path: Path) -> str:
    import subprocess

    result = subprocess.run(
        ["openssl", "x509", "-in", str(path), "-noout", "-fingerprint", "-sha256"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip().split("=", 1)[-1]
