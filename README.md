<!-- # ziplet -->

<p align="center">
	<img src="assets/ziplet-logo.svg" alt="ziplet logo" width="260">
</p>

<p align="center">
	<img src="https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-6ca79e?style=flat-square&logo=python&logoColor=white" alt="Supported Python versions: 3.10, 3.11, 3.12, 3.13, 3.14">
	<img src="https://img.shields.io/badge/license-MIT-6ca79e?style=flat-square" alt="License: MIT">
</p>

`ziplet` is a standalone ZIP library derived from CPython's `zipfile`
module, extended with WinZip AES support adapted from pyzipper.

The project aims to provide a `zipfile`-style API for applications that need
to read and write standard ZIP archives, WinZip AES-encrypted archives and
traditional ZipCrypto archives.

## Why this project exists

`ziplet` started as a split-off from pyzipper for deployments that need to
use the `cryptography` package with a FIPS-configured OpenSSL provider.
Pyzipper uses PyCryptodomeX for its cryptographic primitives, which is outside
the FIPS-validated cryptographic boundary used by those deployments.

This project is not itself FIPS-validated and using `cryptography` does not
make an application FIPS-compliant. A deployment must use a FIPS-validated
cryptographic module and a FIPS-configured Python/OpenSSL environment, and
must follow the applicable operational controls. For a FIPS-constrained
deployment, use WinZip AES only after confirming that the selected provider
permits the algorithms and modes required by the WinZip AES format. Do not use
the legacy ZipCrypto option for FIPS-constrained data; it is a compatibility
feature and is not a FIPS-approved encryption algorithm.

## What it provides?

- a familiar `ZipFile` API.
- read and write support for plain ZIP archives
- write support for WinZip AES and ZipCrypto encryption
- read support that auto-detects AES vs. ZipCrypto for encrypted members
- support for `ZIP_STORED`, `ZIP_DEFLATED`, `ZIP_BZIP2`, `ZIP_LZMA` and
  `ZIP_ZSTANDARD` compression

## Installation

```bash
pip install ziplet
```

## Intended usage

The intended usage is the same as `zipfile`'s: use `ziplet.ZipFile` to create your archive, optionally choose a compression and/or encryption methods and
set a password for encrypted archives if applicable.

### Creating a plain ZIP archive

```python
from ziplet import ZipFile, ZIP_DEFLATED

with ZipFile("example.zip", "w", compression=ZIP_DEFLATED) as zf:
    zf.writestr("hello.txt", "hello world")
```

### Reading a plain ZIP archive

```python
from ziplet import ZipFile

with ZipFile("example.zip", "r") as zf:
    data = zf.read("hello.txt")
```

### Writing an AES-encrypted archive

```python
from ziplet import ZipFile, WZ_AES, ZIP_DEFLATED

password = b"correct horse battery staple"

with ZipFile(
    "secret-aes.zip",
    "w",
    compression=ZIP_DEFLATED,
    encryption=WZ_AES,
) as zf:
    zf.setpassword(password)
    zf.writestr("secret.txt", b"sensitive payload")
```

### Reading an encrypted ZIP archive

```python
from ziplet import ZipFile

password = b"correct horse battery staple"

with ZipFile("secret-aes.zip", "r") as zf:
    zf.setpassword(password)
    data = zf.read("secret.txt")
```

> **NOTE**:
When reading, encryption is normally detected automatically from the archive
metadata, so you typically do not need to specify an encryption mode.

### Customizing AES settings with `ZipFileExtra`

`ZipFileExtra` is the write-time configuration object for AES-specific ZIP
output. It lets you override the WinZip AES version written into the extra
field and choose the AES key size.

```python
from ziplet import ZipFile, ZipFileExtra, WZ_AES, ZIP_DEFLATED

password = b"correct horse battery staple"
extra = ZipFileExtra(force_wz_aes_version=1, wz_aes_nbits=256)

with ZipFile(
    "secret-aes-v1.zip",
    "w",
    compression=ZIP_DEFLATED,
    encryption=WZ_AES,
    extra=extra,
) as zf:
    zf.setpassword(password)
    zf.writestr("secret.txt", b"payload")
```

### Writing AES-encrypted archive with a different key size

```python
from ziplet import ZipFile, ZipFileExtra, WZ_AES

password = b"correct horse battery staple"
extra = ZipFileExtra(wz_aes_nbits=128)

with ZipFile("secret-aes-128.zip", "w", encryption=WZ_AES, extra=extra) as zf:
    zf.setpassword(password)
    zf.writestr("secret.txt", b"payload")
```

### Writing a ZipCrypto-encrypted archive

```python
from ziplet import ZipFile, ZIP_CRYPTO, ZIP_DEFLATED

password = b"correct horse battery staple"

with ZipFile(
    "secret-zipcrypto.zip",
    "w",
    compression=ZIP_DEFLATED,
    encryption=ZIP_CRYPTO,
) as zf:
    zf.setpassword(password)
    zf.writestr("secret.txt", b"legacy compatible payload")
```

### Using in-memory buffers

```python
import io

from ziplet import ZipFile, WZ_AES

password = b"correct horse battery staple"
buffer = io.BytesIO()

with ZipFile(buffer, "w", encryption=WZ_AES) as zf:
    zf.setpassword(password)
    zf.writestr("data.txt", b"payload")

buffer.seek(0)

with ZipFile(buffer, "r") as zf:
    zf.setpassword(password)
    data = zf.read("data.txt")
```

## Public API

The package exports these primary entry points:

- `ZipFile`
- `is_zipfile`
- `ZipFileExtra`
- `WZ_AES`, `WZ_AES_V1`, `WZ_AES_V2`
- `ZIP_CRYPTO`
- `ZIP_STORED`, `ZIP_DEFLATED`, `ZIP_BZIP2`, `ZIP_LZMA`, `ZIP_ZSTANDARD`
- `WzAesExtra`

## Notes

- `ZIP_ZSTANDARD` compression requires a Python runtime that provides zstandard support
- use WinZip AES for modern encrypted ZIP workflows (ZipCrypto is mainly for compatibility with older tools)
- passwords must be byte strings

## Interoperability

The project is intended to interoperate with common ZIP tooling while exposing
an API that feels like the standard library.

- the functional test suite includes 7-Zip interoperability checks in both
	directions: archives written by `ziplet` are validated by 7-Zip, and
	AES- and ZipCrypto-encrypted archives written by 7-Zip are read by
	`ziplet`
- WinZip AES is the primary encrypted format to use for modern workflows
- ZipCrypto is included for compatibility with older ZIP consumers and tools
- plain ZIP archives remain readable through the same `ZipFile` API

This is not a claim of universal compatibility with every ZIP tool and every
feature combination. If interoperability matters for your environment, verify
the exact compression and encryption combinations you plan to ship.

## License

This project is licensed under the MIT License. Additional upstream licensing
and attribution files are included for the CPython- and pyzipper-derived
portions of the codebase:

- `LICENSE`
- `NOTICE`
- `licenses/CPYTHON-3.14.3.txt`
- `licenses/pyzipper-MIT.txt`
