"""Tests for certificate download utilities."""

from pathlib import Path

import pytest

from russian_trusted_ca.download import download
from russian_trusted_ca.exceptions import DownloadError


def test_download_missing_curl(mocker, tmp_path: Path):
    mocker.patch("shutil.which", return_value=None)
    with pytest.raises(DownloadError):
        download("https://example.com/cert.pem", tmp_path / "cert.pem")


def test_download_failed(mocker, tmp_path: Path):
    mocker.patch("shutil.which", return_value="/usr/bin/curl")
    mocker.patch(
        "subprocess.run",
        side_effect=Exception("network error"),
    )
    with pytest.raises(DownloadError):
        download("https://example.com/cert.pem", tmp_path / "cert.pem")
