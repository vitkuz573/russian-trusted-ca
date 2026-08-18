"""Certificate verification utilities."""

from __future__ import annotations

import subprocess
from pathlib import Path

from russian_trusted_ca.exceptions import VerificationError


def _run_openssl(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["openssl", "x509", *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )


def _normalise_fingerprint(fp: str) -> str:
    return fp.replace(":", "").replace(" ", "").upper()


def verify_certificate(
    path: Path,
    expected_cn: str,
    expected_fingerprint: str,
) -> None:
    """Verify that a PEM file has the expected subject and SHA-256 fingerprint.

    Args:
        path: path to the certificate file.
        expected_cn: expected common name substring in the subject.
        expected_fingerprint: expected SHA-256 fingerprint (colon-separated).

    Raises:
        VerificationError: if validation fails.
    """
    subject_result = _run_openssl(["-in", str(path), "-noout", "-subject"])
    if subject_result.returncode != 0:
        raise VerificationError(
            f"Downloaded file is not a valid PEM certificate: {path}",
        )
    if expected_cn not in subject_result.stdout:
        raise VerificationError(
            f"Unexpected certificate subject: {subject_result.stdout.strip()!r}",
        )

    fp_result = _run_openssl(
        ["-in", str(path), "-noout", "-fingerprint", "-sha256"],
    )
    if fp_result.returncode != 0:
        raise VerificationError(f"Cannot compute fingerprint for {path}")

    actual = fp_result.stdout.strip().split("=", 1)[-1]
    if _normalise_fingerprint(actual) != _normalise_fingerprint(expected_fingerprint):
        raise VerificationError(
            f"Fingerprint mismatch for {path}: "
            f"expected {expected_fingerprint}, got {actual}",
        )
