"""Allow running the package with ``python -m russian_trusted_ca``."""

from russian_trusted_ca.cli import entrypoint

if __name__ == "__main__":  # pragma: no cover
    entrypoint()
