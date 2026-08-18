"""Command-line interface for the Russian Trusted CA installer."""

from __future__ import annotations

import argparse
import platform
import sys

from russian_trusted_ca.distro import detect_distro
from russian_trusted_ca.exceptions import PlatformError, RussianTrustedCAError
from russian_trusted_ca.operations import (
    check_connection,
    install_certificates,
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

    sub.add_parser("uninstall", help="remove certificates from system trust store")
    sub.add_parser("status", help="show installation status")

    check_parser = sub.add_parser("check", help="check TLS handshake to a host")
    check_parser.add_argument("host", help="hostname to connect to")
    check_parser.add_argument("--port", type=int, default=443, help="TCP port")

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

    if args.command == "install":
        install_certificates(distro, force=args.force)
    elif args.command == "uninstall":
        uninstall_certificates(distro)
    elif args.command == "status":
        return print_status(distro)
    elif args.command == "check":
        return check_connection(args.host, args.port)

    return 0


def entrypoint() -> None:
    """Console script entry point that handles exceptions."""
    try:
        sys.exit(main())
    except RussianTrustedCAError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
