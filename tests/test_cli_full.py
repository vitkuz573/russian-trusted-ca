"""Full CLI command coverage tests."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from russian_trusted_ca.cli import main

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


def _distro_mock(mocker: MockerFixture, tmp_path: Path):
    return mocker.Mock(
        name="test",
        anchors_dir=tmp_path / "anchors",
        update_cmd=["update-certs"],
        cert_ext=".crt",
    )


def test_cli_install(mocker: MockerFixture, tmp_path: Path) -> None:
    install = mocker.patch("russian_trusted_ca.cli.install_certificates")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["install"]) == 0
    install.assert_called_once()


def test_cli_install_force_and_backup(mocker: MockerFixture, tmp_path: Path) -> None:
    install = mocker.patch("russian_trusted_ca.cli.install_certificates")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["install", "--force", "--backup"]) == 0
    install.assert_called_once()
    _, kwargs = install.call_args
    assert kwargs["force"] is True
    assert kwargs["backup"] is True


def test_cli_uninstall(mocker: MockerFixture, tmp_path: Path) -> None:
    uninstall = mocker.patch("russian_trusted_ca.cli.uninstall_certificates")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["uninstall"]) == 0
    uninstall.assert_called_once()


def test_cli_status(mocker: MockerFixture, tmp_path: Path) -> None:
    status = mocker.patch("russian_trusted_ca.cli.print_status", return_value=0)
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["status"]) == 0
    status.assert_called_once()


def test_cli_audit(mocker: MockerFixture, tmp_path: Path) -> None:
    audit = mocker.patch("russian_trusted_ca.cli.audit_certificates", return_value=0)
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["audit", "--fix"]) == 0
    audit.assert_called_once()
    _, kwargs = audit.call_args
    assert kwargs["fix"] is True


def test_cli_list(mocker: MockerFixture, tmp_path: Path) -> None:
    list_cas = mocker.patch("russian_trusted_ca.cli.list_system_cas", return_value=0)
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["list", "--filter", "Test"]) == 0
    list_cas.assert_called_once()
    _, kwargs = list_cas.call_args
    assert kwargs["filter_text"] == "Test"


def test_cli_check(mocker: MockerFixture, tmp_path: Path) -> None:
    check = mocker.patch("russian_trusted_ca.cli.check_connection", return_value=0)
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["check", "online.sberbank.ru", "--port", "443"]) == 0
    check.assert_called_once()


def test_cli_bundle_print_path(mocker: MockerFixture, tmp_path: Path, capsys) -> None:
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["bundle", "--print-path"]) == 0
    captured = capsys.readouterr()
    assert "russian-trusted-ca-bundle.pem" in captured.out


def test_cli_bundle_install_nss(mocker: MockerFixture, tmp_path: Path) -> None:
    build = mocker.patch("russian_trusted_ca.cli.build_bundle")
    install_nss = mocker.patch("russian_trusted_ca.cli.install_to_nss")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["bundle", "--install-nss", "--nss-profile", str(tmp_path)]) == 0
    build.assert_called_once()
    install_nss.assert_called_once()


def test_cli_nss_install_with_bundle(mocker: MockerFixture, tmp_path: Path) -> None:
    install_nss = mocker.patch("russian_trusted_ca.cli.install_to_nss")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    bundle = tmp_path / "bundle.pem"
    bundle.write_text("test")
    assert (
        main(
            [
                "nss-install",
                "--bundle",
                str(bundle),
                "--profile",
                str(tmp_path),
            ]
        )
        == 0
    )
    install_nss.assert_called_once()


def test_cli_nss_install_builds_default_bundle(
    mocker: MockerFixture,
    tmp_path: Path,
) -> None:
    build = mocker.patch("russian_trusted_ca.cli.build_bundle")
    install_nss = mocker.patch("russian_trusted_ca.cli.install_to_nss")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["nss-install"]) == 0
    build.assert_called_once()
    install_nss.assert_called_once()


def test_cli_nss_uninstall(mocker: MockerFixture, tmp_path: Path) -> None:
    remove_nss = mocker.patch("russian_trusted_ca.cli.remove_from_nss")
    mocker.patch("russian_trusted_ca.cli.platform.system", return_value="Linux")
    mocker.patch(
        "russian_trusted_ca.distro.detect_distro",
        return_value=_distro_mock(mocker, tmp_path),
    )
    assert main(["nss-uninstall", "--profile", str(tmp_path)]) == 0
    remove_nss.assert_called_once()
