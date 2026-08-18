# russian-trusted-ca

CLI tool to install and remove the Russian Ministry of Digital Development's
root certificates (Russian Trusted Root CA / Sub CA) from the Linux system
trust store.

Useful for accessing Russian government and banking sites (e.g.
`online.sberbank.ru`, `gosuslugi.ru`) that use certificates issued by a
national CA not trusted by most Linux distributions by default.

> **Important:** installing a root CA affects the security of the whole system.
> If you only need access to specific sites, consider the
> [safer alternatives](#safer-alternatives-to-system-wide-installation) first.

## Features

- automatic download of certificates from the official Gosuslugi CDN;
- verification of downloaded files by subject and SHA-256 fingerprint via
  `openssl`;
- distribution support:
  - Arch Linux (`ca-certificates` / `update-ca-trust`);
  - Debian/Ubuntu (`ca-certificates` / `update-ca-certificates`);
  - Fedora and compatible systems (`update-ca-trust`).
- TLS handshake check against the system trust store or a scoped CA bundle;
- scoped installation into Firefox / Chromium NSS profiles without touching the
  OS trust store;
- audit and list commands to inspect installed certificates.

## Requirements

- Linux;
- Python 3.9 or newer;
- `curl`;
- `openssl`;
- `sudo` for writing to system certificate directories;
- `certutil` (from `nss-tools`) for NSS profile installation.

## Installation

```bash
git clone https://github.com/vitkuz573/russian-trusted-ca.git
cd russian-trusted-ca
pip install -e .
```

## Usage

### Install system-wide

```bash
russian-trusted-ca install
```

Force reinstall:

```bash
russian-trusted-ca install --force
```

Create a backup of existing anchors before installing:

```bash
russian-trusted-ca install --backup
```

### Uninstall system-wide

```bash
russian-trusted-ca uninstall
```

### Status

```bash
russian-trusted-ca status
```

### Audit installed certificates

```bash
russian-trusted-ca audit
```

Reinstall if fingerprints do not match:

```bash
russian-trusted-ca audit --fix
```

### List installed system CAs

```bash
russian-trusted-ca list
russian-trusted-ca list --filter "Russian Trusted"
```

### Check TLS connection to a host

Using the system trust store:

```bash
russian-trusted-ca check online.sberbank.ru
```

Using a scoped CA bundle:

```bash
russian-trusted-ca check online.sberbank.ru --bundle ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem
```

### Build a scoped CA bundle

```bash
russian-trusted-ca bundle
```

Default output:
`~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem`

Custom path:

```bash
russian-trusted-ca bundle -o ./russian-trusted-ca-bundle.pem
```

Print the default path:

```bash
russian-trusted-ca bundle --print-path
```

Use the bundle with `curl`:

```bash
curl --cacert ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem \
     https://online.sberbank.ru/
```

### Install into a browser profile only (NSS)

This limits trust to a single browser profile without changing the system store.

```bash
russian-trusted-ca nss-install
```

Use a specific profile:

```bash
russian-trusted-ca nss-install --profile ~/.pki/nssdb
```

Remove from profiles:

```bash
russian-trusted-ca nss-uninstall
```

## Example

Before installation:

```bash
$ russian-trusted-ca check online.sberbank.ru
FAILED - SSL error: CERTIFICATE_VERIFY_FAILED
```

After installation:

```bash
$ russian-trusted-ca check online.sberbank.ru
OK - TLS TLSv1.2 with Sberbank of Russia (*.online.sberbank.ru)
```

## Certificate authenticity verification

Certificates are downloaded from the official Gosuslugi CDN
(`gu-st.ru/content/lending/`) and verified locally via `openssl`:

- the subject must match `Russian Trusted Root CA` / `Russian Trusted Sub CA`;
- the SHA-256 fingerprint must match the hard-coded known value.

This protects against file substitution during download even when the TLS
connection to the CDN cannot be validated by the OS.

## Risks

Installing a root certificate is a privileged operation that affects the
security of the whole system.

After installing Russian Trusted Root CA into the system store:

- the issuing CA can issue trusted certificates for **any** domain;
- MITM attacks against HTTPS connections are possible within this chain of trust;
- many international services and browsers do not trust this CA by default;
- you can remove the certificates at any time with
  `russian-trusted-ca uninstall`.

Only install if you understand the consequences and trust the Russian Ministry
of Digital Development as a certificate authority.

## Safer alternatives to system-wide installation

If your goal is to access specific sites without global CA trust, use one of
these scoped options.

### 1. Scoped CA bundle

```bash
russian-trusted-ca bundle
curl --cacert ~/.local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem \
     https://online.sberbank.ru/
```

Trust applies only to the explicit call; the system store is not modified.

### 2. Scoped SSL context in Python

```python
import ssl
import urllib.request
from pathlib import Path

bundle = Path.home() / ".local/share/russian-trusted-ca/russian-trusted-ca-bundle.pem"
ctx = ssl.create_default_context(cafile=str(bundle))

req = urllib.request.Request("https://online.sberbank.ru/")
with urllib.request.urlopen(req, context=ctx) as resp:
    print(resp.status)
```

### 3. Browser profile import

Import the certificates only into a specific browser profile instead of the OS
store:

- **Chromium / Google Chrome**:
  `Settings → Privacy and security → Security → Manage certificates →
  Authorities → Import`.
- **Firefox**:
  `Settings → Privacy & Security → Certificates → View Certificates →
  Authorities → Import`.

When importing, choose "Trust this CA to identify websites" only if you trust
the source.

### 4. Separate browser profile

Create a dedicated Chrome/Firefox profile for Russian government services and
import the CA there. Other profiles and applications remain unaffected.

### 5. Container / virtual machine

Run the browser or script inside Docker or a VM, install the CA inside the
isolated environment, and leave the host untouched. This protects the main
system even if the CA is compromised.

### 6. NSS profile installation

Use `russian-trusted-ca nss-install` to add the CA only to browser NSS
databases. This is a middle ground between a per-request bundle and a full
system install.

### When to use this tool system-wide

System-wide installation is justified when:

- many applications and system services need access at once;
- you accept the risks and trust the CA operator;
- isolation or per-request bundles are not practical.

## Development

```bash
pip install -e ".[dev]"
make lint
make test
```

## Author

Vitaly Kuzyaev <vitkuz573@gmail.com>

## License

MIT
