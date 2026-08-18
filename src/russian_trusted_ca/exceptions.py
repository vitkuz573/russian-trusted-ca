"""Custom exceptions for the Russian Trusted CA installer."""


class RussianTrustedCAError(Exception):
    """Base exception for all installer errors."""


class DistroDetectionError(RussianTrustedCAError):
    """Raised when the Linux distribution CA layout cannot be detected."""


class DownloadError(RussianTrustedCAError):
    """Raised when a certificate download fails."""


class VerificationError(RussianTrustedCAError):
    """Raised when a downloaded certificate fails verification."""


class PlatformError(RussianTrustedCAError):
    """Raised when the platform is unsupported."""
