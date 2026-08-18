"""Certificate download utilities."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from russian_trusted_ca.exceptions import DownloadError


def download(url: str, dest: Path) -> None:
    """Download a file using curl.

    The official distribution host is signed by the Russian Trusted CA, so a
    system without the CA already trusted will reject the TLS handshake.  We
    therefore use ``--insecure`` for the download itself, then validate the file
    contents via openssl afterwards.

    Args:
        url: URL to download.
        dest: local path to save the file to.

    Raises:
        DownloadError: if curl is missing or the download fails.
    """
    if shutil.which("curl") is None:
        raise DownloadError("curl is required but not found in PATH")

    try:
        subprocess.run(
            ["curl", "-fsSL", "--insecure", "-o", str(dest), url],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise DownloadError(
            f"Failed to download {url}: {exc.stderr.decode(errors='replace')}",
        ) from exc
