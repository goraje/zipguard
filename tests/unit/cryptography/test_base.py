from __future__ import annotations

import pytest

from ziplet.cryptography.base import BaseZipDecrypter, BaseZipEncryptor


class TestBaseZipDecrypter:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseZipDecrypter()  # type: ignore[abstract]

    def test_subclass_missing_decrypt_cannot_instantiate(self) -> None:
        class Incomplete(BaseZipDecrypter):
            pass

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate(self) -> None:
        class Concrete(BaseZipDecrypter):
            def decrypt(self, data: bytes) -> bytes:
                return data

        obj = Concrete()
        assert obj.decrypt(b"hello") == b"hello"

    def test_decrypt_passthrough(self) -> None:
        class Concrete(BaseZipDecrypter):
            def decrypt(self, data: bytes) -> bytes:
                return data

        assert Concrete().decrypt(b"\x00\x01\x02") == b"\x00\x01\x02"


class TestBaseZipEncryptor:
    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            BaseZipEncryptor()  # type: ignore[abstract]

    def test_subclass_missing_encrypt_cannot_instantiate(self) -> None:
        class Incomplete(BaseZipEncryptor):
            def update_zipinfo(self, zipinfo: object) -> None:
                pass

            def encryption_header(self) -> bytes:
                return b""

            def flush(self) -> bytes:
                return b""

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_missing_update_zipinfo_cannot_instantiate(self) -> None:
        class Incomplete(BaseZipEncryptor):
            def encrypt(self, data: bytes) -> bytes:
                return data

            def encryption_header(self) -> bytes:
                return b""

            def flush(self) -> bytes:
                return b""

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_missing_flush_cannot_instantiate(self) -> None:
        class Incomplete(BaseZipEncryptor):
            def update_zipinfo(self, zipinfo: object) -> None:
                pass

            def encrypt(self, data: bytes) -> bytes:
                return data

            def encryption_header(self) -> bytes:
                return b""

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_concrete_subclass_can_instantiate(self) -> None:
        class Concrete(BaseZipEncryptor):
            def update_zipinfo(self, zipinfo: object) -> None:
                pass

            def encrypt(self, data: bytes) -> bytes:
                return data

            def encryption_header(self) -> bytes:
                return b"\x00"

            def flush(self) -> bytes:
                return b""

        obj = Concrete()
        assert obj.encrypt(b"data") == b"data"
        assert obj.encryption_header() == b"\x00"
        assert obj.flush() == b""
