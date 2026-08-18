"""Full operations module coverage tests."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from russian_trusted_ca.distro import CertPaths, DistroInfo
from russian_trusted_ca.exceptions import VerificationError
from russian_trusted_ca.operations import (
    _backup_dir,
    _fingerprint,
    audit_certificates,
    build_bundle,
    check_connection,
    install_certificates,
    list_system_cas,
    print_status,
    uninstall_certificates,
)

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def _distro(tmp_path: Path) -> DistroInfo:
    anchors = tmp_path / "anchors"
    anchors.mkdir(parents=True, exist_ok=True)
    return DistroInfo(
        name="test",
        anchors_dir=anchors,
        update_cmd=["update-certs"],
        cert_ext=".crt",
    )


def test_backup_dir() -> None:
    """_backup_dir should return a path under ~/.local/share."""
    assert "backups" in str(_backup_dir())


def test_fingerprint_valid(tmp_path: Path) -> None:
    """_fingerprint should return the SHA-256 fingerprint of a certificate."""
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
            "/CN=Test",
        ],
        capture_output=True,
        check=True,
    )
    fp = _fingerprint(cert)
    assert len(fp.replace(":", "")) == 64


def test_install_already_installed(mocker, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    paths.root_cert.write_text("root")
    paths.sub_cert.write_text("sub")
    install_certificates(distro)
    captured = capsys.readouterr()
    assert "already installed" in captured.out


def test_install_anchors_dir_missing(tmp_path: Path) -> None:
    distro = DistroInfo(
        name="test",
        anchors_dir=tmp_path / "missing",
        update_cmd=["update-certs"],
        cert_ext=".crt",
    )
    with pytest.raises(FileNotFoundError):
        install_certificates(distro)


def test_install_full(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    root = tmp_path / "root-ca.pem"
    sub = tmp_path / "sub-ca.pem"
    root.write_text("root")
    sub.write_text("sub")

    calls = []
    real_run = subprocess.run

    def fake_download(url: str, dest: Path) -> None:
        if "root" in url:
            dest.write_bytes(root.read_bytes())
        else:
            dest.write_bytes(sub.read_bytes())
        calls.append(("download", url))

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        calls.append(("run", cmd))
        if cmd[0] == "sudo" and len(cmd) > 1 and cmd[1] in ("cp", "rm"):
            return real_run(cmd[1:], **kwargs)
        if cmd[0] in ("cp", "rm"):
            return real_run(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("russian_trusted_ca.operations.download", fake_download)
    monkeypatch.setattr(
        "russian_trusted_ca.operations.verify_certificate",
        lambda _path, _cn, _fp: None,
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    install_certificates(distro, backup=True)

    assert paths.root_cert.exists()
    captured = capsys.readouterr()
    assert "installed successfully" in captured.out


def test_install_backup_existing(
    monkeypatch: MonkeyPatch,
    tmp_path: Path,
    capsys,
) -> None:
    """Install --backup should copy existing anchors before replacing them."""
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    paths.root_cert.write_text("old-root")
    paths.sub_cert.write_text("old-sub")
    root = tmp_path / "root-ca.pem"
    sub = tmp_path / "sub-ca.pem"
    root.write_text("root")
    sub.write_text("sub")

    real_run = subprocess.run

    def fake_download(url: str, dest: Path) -> None:
        if "root" in url:
            dest.write_bytes(root.read_bytes())
        else:
            dest.write_bytes(sub.read_bytes())

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        if cmd[0] == "sudo" and len(cmd) > 1 and cmd[1] in ("cp", "rm"):
            return real_run(cmd[1:], **kwargs)
        if cmd[0] in ("cp", "rm"):
            return real_run(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("russian_trusted_ca.operations.download", fake_download)
    monkeypatch.setattr(
        "russian_trusted_ca.operations.verify_certificate",
        lambda _path, _cn, _fp: None,
    )
    monkeypatch.setattr(subprocess, "run", fake_run)

    install_certificates(distro, force=True, backup=True)

    captured = capsys.readouterr()
    assert "Backed up" in captured.out


def test_uninstall_removes(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    paths.root_cert.write_text("root")
    paths.sub_cert.write_text("sub")

    calls = []
    real_run = subprocess.run

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        calls.append(("run", cmd))
        if cmd[0] == "sudo" and len(cmd) > 1 and cmd[1] == "rm":
            return real_run(cmd[1:], **kwargs)
        if cmd[0] == "rm":
            return real_run(cmd, **kwargs)
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    uninstall_certificates(distro)
    captured = capsys.readouterr()
    assert "removed successfully" in captured.out
    assert not paths.root_cert.exists()


def test_uninstall_nothing(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    uninstall_certificates(distro)
    captured = capsys.readouterr()
    assert "Nothing to remove" in captured.out


def test_print_status_installed(capsys, tmp_path: Path) -> None:
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    paths.root_cert.write_text("root")
    paths.sub_cert.write_text("sub")
    assert print_status(distro) == 0
    captured = capsys.readouterr()
    assert "present" in captured.out


def test_print_status_missing(capsys, tmp_path: Path) -> None:
    distro = _distro(tmp_path)
    assert print_status(distro) == 1
    captured = capsys.readouterr()
    assert "missing" in captured.out


def test_audit_ok(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    paths.root_cert.write_text("root")
    paths.sub_cert.write_text("sub")
    monkeypatch.setattr(
        "russian_trusted_ca.operations.verify_certificate",
        lambda _path, _cn, _fp: None,
    )
    assert audit_certificates(distro) == 0
    captured = capsys.readouterr()
    assert "Audit passed" in captured.out


def test_audit_missing(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    monkeypatch.setattr(
        "russian_trusted_ca.operations.install_certificates",
        lambda _distro, force: None,
    )
    assert audit_certificates(distro, fix=False) == 1
    captured = capsys.readouterr()
    assert "MISSING" in captured.out


def test_audit_bad_and_fix(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    paths = CertPaths(distro)
    paths.root_cert.write_text("root")
    paths.sub_cert.write_text("sub")

    def fake_verify(path: Path, cn: str, fp: str) -> None:
        raise VerificationError("bad")

    def fake_install(distro_arg: DistroInfo, *, force: bool) -> None:
        monkeypatch.setattr(
            "russian_trusted_ca.operations.verify_certificate",
            lambda _path, _cn, _fp: None,
        )

    monkeypatch.setattr("russian_trusted_ca.operations.verify_certificate", fake_verify)
    monkeypatch.setattr(
        "russian_trusted_ca.operations.install_certificates", fake_install
    )

    assert audit_certificates(distro, fix=True) == 0
    captured = capsys.readouterr()
    assert "Attempting to fix" in captured.out


def test_list_anchors_missing(capsys, tmp_path: Path) -> None:
    distro = DistroInfo(
        name="test",
        anchors_dir=tmp_path / "missing",
        update_cmd=["update-certs"],
        cert_ext=".crt",
    )
    assert list_system_cas(distro) == 0
    captured = capsys.readouterr()
    assert "not found" in captured.out


def test_list_with_filter(monkeypatch: MonkeyPatch, tmp_path: Path, capsys) -> None:
    distro = _distro(tmp_path)
    cert = distro.anchors_dir / "test.crt"
    cert.write_text("pem")

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="subject=CN = Keep", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert list_system_cas(distro, filter_text="Keep") == 0
    captured = capsys.readouterr()
    assert "Keep" in captured.out


def test_list_excluded_by_filter(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys
) -> None:
    distro = _distro(tmp_path)
    cert = distro.anchors_dir / "test.crt"
    cert.write_text("pem")

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        return subprocess.CompletedProcess(
            cmd, returncode=0, stdout="subject=CN = Other", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert list_system_cas(distro, filter_text="Keep") == 0
    captured = capsys.readouterr()
    assert "Other" not in captured.out


def test_list_bad_cert_skipped(
    monkeypatch: MonkeyPatch, tmp_path: Path, capsys
) -> None:
    distro = _distro(tmp_path)
    cert = distro.anchors_dir / "test.crt"
    cert.write_text("pem")

    def fake_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        raise subprocess.CalledProcessError(1, cmd)

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert list_system_cas(distro) == 0
    captured = capsys.readouterr()
    assert captured.out == ""


def test_check_success(monkeypatch: MonkeyPatch) -> None:
    class FakeSock:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def getpeercert(self):
            return {"subject": ((("commonName", "test"),),)}

        def version(self):
            return "TLSv1.3"

    monkeypatch.setattr("socket.create_connection", lambda addr, timeout: FakeSock())
    monkeypatch.setattr(
        "ssl.SSLContext.wrap_socket",
        lambda self, sock, server_hostname: FakeSock(),
    )
    assert check_connection("test") == 0


def test_check_ssl_error(monkeypatch: MonkeyPatch) -> None:
    import ssl as ssl_module

    class ReasonableSSLError(ssl_module.SSLError):
        def __init__(self, reason: str) -> None:
            super().__init__(reason)
            self.reason = reason

    def fake_create_connection(addr, timeout):
        raise ReasonableSSLError("verify failed")

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    assert check_connection("test") == 1


def test_check_os_error(monkeypatch: MonkeyPatch) -> None:
    def fake_create_connection(addr, timeout):
        raise OSError("network down")

    monkeypatch.setattr("socket.create_connection", fake_create_connection)
    assert check_connection("test") == 1


def test_check_with_bundle(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    cert_file = tmp_path / "cert.pem"
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
            str(cert_file),
            "-days",
            "1",
            "-nodes",
            "-subj",
            "/CN=test",
        ],
        capture_output=True,
        check=True,
    )
    bundle = tmp_path / "bundle.pem"
    bundle.write_text(cert_file.read_text())

    class FakeSock:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def getpeercert(self):
            return {"subject": ((("commonName", "test"),),)}

        def version(self):
            return "TLSv1.3"

    monkeypatch.setattr("socket.create_connection", lambda addr, timeout: FakeSock())
    monkeypatch.setattr(
        "ssl.SSLContext.wrap_socket",
        lambda self, sock, server_hostname: FakeSock(),
    )
    assert check_connection("test", bundle=bundle) == 0


def test_build_bundle_real_files(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    root = tmp_path / "root-ca.pem"
    sub = tmp_path / "sub-ca.pem"
    root.write_text("root")
    sub.write_text("sub")

    def fake_download(url: str, dest: Path) -> None:
        if "root" in url:
            dest.write_bytes(root.read_bytes())
        else:
            dest.write_bytes(sub.read_bytes())

    monkeypatch.setattr("russian_trusted_ca.operations.download", fake_download)
    monkeypatch.setattr(
        "russian_trusted_ca.operations.verify_certificate",
        lambda _path, _cn, _fp: None,
    )

    output = tmp_path / "out.pem"
    build_bundle(output)
    assert output.exists()
