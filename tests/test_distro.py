"""Tests for distribution detection."""

from pathlib import Path

import pytest

from russian_trusted_ca.distro import CertPaths, DistroInfo, detect_distro
from russian_trusted_ca.exceptions import DistroDetectionError


def test_cert_paths(mocker):
    distro = DistroInfo(
        name="test",
        anchors_dir=Path("/etc/certs"),
        update_cmd=["update-certs"],
        cert_ext=".crt",
    )
    paths = CertPaths(distro)
    assert paths.root_cert == Path("/etc/certs/russian-trusted-root-ca.crt")
    assert paths.sub_cert == Path("/etc/certs/russian-trusted-sub-ca.crt")


def test_detect_distro_arch(mocker):
    mocker.patch("pathlib.Path.is_dir", side_effect=[True, False])
    mocker.patch("shutil.which", return_value="/usr/bin/update-ca-trust")
    info = detect_distro()
    assert info.name == "ca-trust (Arch/Fedora)"


def test_detect_distro_debian(mocker):
    mocker.patch("pathlib.Path.is_dir", side_effect=[False, True])
    info = detect_distro()
    assert info.name == "ca-certificates (Debian/Ubuntu)"


def test_detect_distro_unsupported(mocker):
    mocker.patch("pathlib.Path.is_dir", return_value=False)
    with pytest.raises(DistroDetectionError):
        detect_distro()
