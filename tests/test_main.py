"""Tests for the package __main__ module."""

from __future__ import annotations

from russian_trusted_ca import __main__


def test_main_module_runs_entrypoint(mocker) -> None:
    """Running the module should invoke entrypoint."""
    entrypoint = mocker.patch("russian_trusted_ca.__main__.entrypoint")
    __main__.__dict__["__name__"] = "__main__"
    __main__.entrypoint = entrypoint
    exec("if __name__ == '__main__': entrypoint()", __main__.__dict__)  # noqa: S102
    entrypoint.assert_called_once()
