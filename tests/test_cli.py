"""Tests for the CLI entry point."""

from pathlib import Path

import pytest

from russian_trusted_ca.cli import main
from russian_trusted_ca.exceptions import PlatformError


def test_cli_status_missing(mocker, tmp_path: Path):
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=mocker.Mock(
            name="test",
            anchors_dir=tmp_path,
            update_cmd=["update-certs"],
            cert_ext=".crt",
        ),
    )
    assert main(["status"]) == 1


def test_cli_unsupported_platform(mocker):
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Windows")
    with pytest.raises(PlatformError):
        main(["status"])
