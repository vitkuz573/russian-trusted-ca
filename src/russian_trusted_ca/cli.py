"""Command-line interface for the Russian Trusted CA installer."""

from __future__ import annotations

import argparse
import platform
import sys
from pathlib import Path

from russian_trusted_ca.distro import detect_distro
from russian_trusted_ca.exceptions import PlatformError, RussianTrustedCAError
from russian_trusted_ca.nss import install_to_nss, remove_from_nss
from russian_trusted_ca.operations import (
    audit_certificates,
    build_bundle,
    check_connection,
    install_certificates,
    list_system_cas,
    print_status,
    uninstall_certificates,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Install or remove Russian Trusted Root CA certificates",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    install_parser = sub.add_parser(
        "install",
        help="download and install certificates",
    )
    install_parser.add_argument(
        "--force",
        action="store_true",
        help="reinstall even if already present",
    )
    install_parser.add_argument(
        "--backup",
        action="store_true",
        help="create a backup of system CA store before installing",
    )

    sub.add_parser("uninstall", help="remove certificates from system trust store")
    sub.add_parser("status", help="show installation status")

    audit_parser = sub.add_parser(
        "audit",
        help="verify installed certificates match known fingerprints",
    )
    audit_parser.add_argument(
        "--fix",
        action="store_true",
        help="re-download and reinstall certificates if they do not match",
    )

    list_parser = sub.add_parser(
        "list",
        help="list installed system CA certificates",
    )
    list_parser.add_argument(
        "--filter",
        default="Russian Trusted",
        help="substring to filter certificate subjects (default: Russian Trusted)",
    )

    check_parser = sub.add_parser("check", help="check TLS handshake to a host")
    check_parser.add_argument("host", help="hostname to connect to")
    check_parser.add_argument("--port", type=int, default=443, help="TCP port")
    check_parser.add_argument(
        "--bundle",
        type=Path,
        help="use a scoped CA bundle instead of the system trust store",
    )

    bundle_parser = sub.add_parser(
        "bundle",
        help="download certificates and build a scoped CA bundle",
    )
    bundle_parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=(
            Path.home()
            / ".local"
            / "share"
            / "russian-trusted-ca"
            / "russian-trusted-ca-bundle.pem"
        ),
        help="path to write the bundle",
    )
    bundle_parser.add_argument(
        "--print-path",
        action="store_true",
        help="print the default bundle path and exit",
    )
    bundle_parser.add_argument(
        "--install-nss",
        action="store_true",
        help="import the bundle into found NSS browser profiles",
    )
    bundle_parser.add_argument(
        "--nss-profile",
        type=Path,
        help="specific NSS profile directory (default: auto-detect)",
    )

    nss_parser = sub.add_parser(
        "nss-install",
        help="install certificates into a browser NSS profile",
    )
    nss_parser.add_argument(
        "--profile",
        type=Path,
        help="NSS profile directory (default: auto-detect)",
    )
    nss_parser.add_argument(
        "--bundle",
        type=Path,
        help="path to PEM bundle (default: build a fresh one)",
    )

    nss_uninstall_parser = sub.add_parser(
        "nss-uninstall",
        help="remove certificates from a browser NSS profile",
    )
    nss_uninstall_parser.add_argument(
        "--profile",
        type=Path,
        help="NSS profile directory (default: auto-detect)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point for the CLI.

    Args:
        argv: command-line arguments.

    Returns:
        process exit code.
    """
    parser = _build_parser()
    args = parser.parse_args(argv)

    if platform.system() != "Linux":
        raise PlatformError(f"Unsupported platform: {platform.system()}")

    distro = detect_distro()

    command = args.command
    if command == "install":
        install_certificates(distro, force=args.force, backup=args.backup)
    elif command == "uninstall":
        uninstall_certificates(distro)
    elif command == "status":
        return print_status(distro)
    elif command == "audit":
        return audit_certificates(distro, fix=args.fix)
    elif command == "list":
        return list_system_cas(distro, filter_text=args.filter)
    elif command == "check":
        return check_connection(args.host, args.port, bundle=args.bundle)
    elif command == "bundle":
        if args.print_path:
            print(args.output)
            return 0
        build_bundle(args.output)
        if args.install_nss:
            install_to_nss(args.output, profile_dir=args.nss_profile)
        return 0
    elif command == "nss-install":
        default_bundle = (
            Path.home()
            / ".local"
            / "share"
            / "russian-trusted-ca"
            / "russian-trusted-ca-bundle.pem"
        )
        bundle = args.bundle or default_bundle
        if bundle == default_bundle and not default_bundle.exists():
            build_bundle(default_bundle)
        install_to_nss(bundle, profile_dir=args.profile)
        return 0
    elif command == "nss-uninstall":
        remove_from_nss(profile_dir=args.profile)
        return 0

    return 0


def entrypoint() -> None:  # pragma: no cover
    """Console script entry point that handles exceptions."""
    try:
        sys.exit(main())
    except RussianTrustedCAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
