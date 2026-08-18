# Security Analysis: Russian Trusted Root CA

This document explains what installing the Russian Trusted Root CA means for
system security and how we verified both the official certificates and the
risks they introduce.

## 1. What these certificates are

The Russian Trusted Root CA / Sub CA are national root certificates operated by
the Ministry of Digital Development and Communications of Russia. They are used
by Russian state and banking web sites (e.g. `online.sberbank.ru`,
`gosuslugi.ru`) that no longer receive certificates from the globally trusted
public CAs.

Files fetched by this tool:

| File | Purpose |
|------|---------|
| `russian_trusted_root_ca_pem.crt` | Self-signed root certificate |
| `russian_trusted_sub_ca_pem.crt` | Intermediate CA signed by the root |

## 2. Certificate field analysis

```text
Root CA:
  Subject:   C=RU, O=The Ministry of Digital Development and Communications,
             CN=Russian Trusted Root CA
  Issuer:    same as Subject (self-signed)
  Valid:     2022-03-01 – 2032-02-27
  Key:       RSA 4096, SHA-256
  CA flag:   TRUE, pathlen: 4
  KeyUsage:  Digital Signature, Certificate Sign, CRL Sign

Sub CA:
  Subject:   C=RU, O=The Ministry of Digital Development and Communications,
             CN=Russian Trusted Sub CA
  Issuer:    Russian Trusted Root CA
  Valid:     2022-03-02 – 2027-03-06
  Key:       RSA 4096, SHA-256
  CA flag:   TRUE, pathlen: 0
  KeyUsage:  same signing rights as root
  CDP/AIAs:  rostelecom.ru, company.rt.ru, reestr-pki.ru
```

Observations:

* `CA:TRUE` with `pathlen:4` means the root can issue further intermediate CAs.
* `pathlen:0` on the Sub CA means it can issue end-entity certificates but not
  further subordinate CAs.
* Validity windows are long (root 10 years), which is normal for root CAs.

## 3. What can go wrong: a local proof of concept

When any root CA is added to the system trust store, the OS will trust
**any** TLS certificate issued by that CA for **any** domain. The same risk
applies to the Russian Trusted CA.

We reproduced this locally with our own test CA to avoid touching real
infrastructure.

### 3.1 Create a fake CA and a fake certificate

```bash
# Create a local test root CA
openssl genrsa -out ca.key 2048
openssl req -x509 -new -nodes -key ca.key -sha256 -days 1 -out ca.crt \
  -subj "/C=RU/O=PoC Evil CA/CN=PoC Evil Root CA"

# Create an end-entity certificate for fakebank.local
openssl genrsa -out fakebank.key 2048
openssl req -new -key fakebank.key -out fakebank.csr \
  -subj "/C=RU/O=PoC Evil Bank/CN=fakebank.local"
openssl x509 -req -in fakebank.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out fakebank.crt -days 1 -sha256 \
  -extfile <(printf "subjectAltName=DNS:fakebank.local,DNS:www.fakebank.local\n")
```

### 3.2 Run a fake HTTPS server

```bash
openssl s_server -cert fakebank.crt -key fakebank.key -accept 8443 -www -quiet
```

### 3.3 Trust the fake CA and connect

Before installing the fake CA, `curl` rejects the connection as expected:

```text
curl: (60) SSL certificate problem: self-signed certificate in certificate chain
```

After copying `ca.crt` into the system anchors directory and running
`update-ca-trust`:

```bash
sudo cp ca.crt /etc/ca-certificates/trust-source/anchors/poc-evil-ca.crt
sudo update-ca-trust
curl https://fakebank.local:8443/
```

`curl` now succeeds and reports a valid TLS handshake using the fake
`fakebank.crt`. This demonstrates that adding a root CA to the system store is a
powerful security decision: the CA can sign certificates for any domain.

For the Russian Trusted CA, the exact same mechanism applies. Any entity that
controls the private key of `Russian Trusted Sub CA` can issue a valid-looking
certificate for any site.

## 4. How this tool protects downloads

Because the official CDN is often signed by the Russian Trusted CA itself, the
initial download is performed with `curl --insecure`. The downloaded file is then
verified locally using `openssl`:

1. The certificate subject must match the expected value.
2. The SHA-256 fingerprint must match the known hard-coded value.

This prevents an attacker from replacing the file during the download, even if
the transport TLS cannot be validated by the OS.

### Verified behaviour

We tested the verification function with a forged certificate (the fake CA above
renamed to the official file names). The tool correctly rejected it:

```text
Unexpected certificate subject: 'subject=C=RU, O=PoC Evil CA, CN=PoC Evil Root CA'
```

## 5. Residual risks

Even with correct verification at install time, the following risks remain:

* **Compromise or coercion of the CA operator.** If the private key of the
  Russian Trusted Sub CA is leaked or used maliciously, it can issue valid
  certificates for any domain and intercept HTTPS traffic on systems that trust
  this root.
* **Certificate Transparency is limited.** Russian national CAs are not audited
  by the same set of public Certificate Transparency logs as global CAs, making
  it harder to detect mis-issuance.
* **No technical sandbox.** Once installed, the CA is trusted by every
  application that uses the system CA store: browsers, curl, Python, system
  updaters, etc.
* **Cross-border trust.** Most non-Russian systems and browsers do not trust
  this CA by default. Installing it may create an inconsistent security posture
  across devices.

## 6. Safer alternatives to system-wide installation

If you only need access to a few sites, you do not have to install the CA into
the OS trust store.

### Scoped CA bundle for curl

Create a bundle containing both certificates and pass it only to the requests
that need it:

```bash
cat root.crt sub.crt > russian-trusted-ca-bundle.pem
curl --cacert russian-trusted-ca-bundle.pem https://online.sberbank.ru/
```

### Scoped SSL context in Python

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

### Browser profile import

Import the certificates only into a specific browser profile instead of the
system store. Other applications and browser profiles remain unaffected.

### Container / virtual machine

Run the browser or automation script inside an isolated container or VM, install
the CA there, and leave the host system untouched. This is the safest option
when you need system-wide trust inside a narrow environment.

## 7. Recommendations

* Only install this CA system-wide if you genuinely need access to services that
  use it and you trust the Russian Ministry of Digital Development and
  Communications as a certificate authority.
* Prefer scoped alternatives (per-request bundle, browser profile, container)
  whenever possible.
* Regularly review installed CAs with `russian-trusted-ca status`.
* Remove the CA when it is no longer needed: `russian-trusted-ca uninstall`.

## 8. Reporting issues

If you find a security issue in this tool itself (not in the CA policy), please
open a private issue or email Vitaly Kuzyaev <vitkuz573@gmail.com>.
