"""Abstract base classes for ZIP encryption and decryption.

Provides the interfaces that all encryptor and decrypter implementations
must satisfy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ziplet.zipfile.info import ZipInfo


__all__ = [
    "BaseZipDecrypter",
    "BaseZipEncryptor",
]


class BaseZipDecrypter(ABC):
    """Abstract base class for ZIP entry decrypters.

    Subclasses must implement :meth:`decrypt` to provide the decryption
    logic for a specific algorithm.
    """

    @abstractmethod
    def decrypt(self, data: bytes) -> bytes:
        """Decrypt a chunk of ciphertext.

        Args:
            data (bytes): Ciphertext bytes to decrypt.

        Returns:
            bytes: Decrypted plaintext of the same length as *data*.
        """
        raise NotImplementedError(
            "BaseZipDecrypter implementations must implement `decrypt`."
        )


class BaseZipEncryptor(ABC):
    """Abstract base class for ZIP entry encryptors.

    Subclasses must implement :meth:`update_zipinfo`, :meth:`encrypt`,
    :meth:`encryption_header`, and :meth:`flush` to provide the encryption
    logic for a specific algorithm.
    """

    @abstractmethod
    def update_zipinfo(self, zipinfo: "ZipInfo") -> None:
        """Write algorithm-specific fields into a ZipInfo extra-data structure.

        Args:
            zipinfo (ZipInfo): The entry metadata to update in-place.
        """
        raise NotImplementedError(
            "BaseZipEncryptor implementations must implement `update_zipinfo`."
        )

    @abstractmethod
    def encrypt(self, data: bytes) -> bytes:
        """Encrypt a chunk of plaintext.

        Args:
            data (bytes): Plaintext bytes to encrypt.

        Returns:
            bytes: Ciphertext of the same length as *data*.
        """
        raise NotImplementedError(
            "BaseZipEncryptor implementations must implement `encrypt`."
        )

    @abstractmethod
    def encryption_header(self) -> bytes:
        """Build the encryption header to prepend to the ciphertext.

        Returns:
            bytes: Algorithm-specific header bytes (e.g. salt and password
            verification bytes for AES, or the initialisation value for
            ZipCrypto).
        """
        raise NotImplementedError(
            "BaseZipEncryptor implementations must implement `encryption_header`."
        )

    @abstractmethod
    def flush(self) -> bytes:
        """Finalise encryption and return any trailing authentication bytes.

        Called once after all plaintext has been encrypted. Implementations
        that append an authentication tag (e.g. HMAC) return it here;
        others may return an empty bytes object.

        Returns:
            bytes: Trailing bytes to append after the ciphertext, or
            ``b""`` if none.
        """
        raise NotImplementedError(
            "BaseZipEncryptor implementations must implement `flush`."
        )
