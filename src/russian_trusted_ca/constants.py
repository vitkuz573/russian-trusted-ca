"""Constants for Russian Trusted CA certificates."""

from __future__ import annotations

# Official Russian Trusted CA certificate distribution (Gosuslugi CDN).
# These hosts are signed by the Russian Trusted CA itself, so a system without
# the CA already trusted will reject the TLS handshake.  The downloaded files
# are validated via openssl afterwards.
ROOT_CA_URL = "https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt"
SUB_CA_URL = "https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt"

# Known SHA-256 fingerprints of the official certificates.
ROOT_CA_FINGERPRINT = (
    "D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:"
    "35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31"
)
SUB_CA_FINGERPRINT = (
    "BB:BD:E2:10:3E:79:0B:99:9E:C6:2B:D0:3C:F6:25:A5:"
    "A2:E7:C3:16:E1:0A:FE:6A:49:0E:ED:EA:D8:B3:FD:9B"
)

ROOT_CA_SUBJECT = "Russian Trusted Root CA"
SUB_CA_SUBJECT = "Russian Trusted Sub CA"

CERT_BASENAME_ROOT = "russian-trusted-root-ca"
CERT_BASENAME_SUB = "russian-trusted-sub-ca"
