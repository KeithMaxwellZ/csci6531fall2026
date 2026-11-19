"""Cryptographic building blocks used by the messenger protocol."""

import base64
import hashlib
import hmac
import secrets
from typing import Optional, Tuple

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa, padding, x25519
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

PASSWORD_ITERATIONS = 600_000
KEY_SIZE = 32
PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str, salt: Optional[bytes] = None) -> str:
    """Return a salted Argon2id password record."""
    if salt is not None:
        return _hash_password_with_legacy_salt(password, salt)
    return PASSWORD_HASHER.hash(password)


def _hash_password_with_legacy_salt(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS
    )
    return "$".join(
        (
            "pbkdf2_sha256",
            str(PASSWORD_ITERATIONS),
            _encode(salt),
            _encode(digest),
        )
    )


def verify_password(password: str, password_record: str) -> bool:
    """Verify Argon2id records and legacy PBKDF2 records."""
    if password_record.startswith("$argon2"):
        try:
            return PASSWORD_HASHER.verify(password_record, password)
        except (VerificationError, InvalidHashError, VerifyMismatchError):
            return False
    try:
        algorithm, iterations, salt_text, digest_text = password_record.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        expected = _decode(digest_text)
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), _decode(salt_text), int(iterations)
        )
    except (InvalidSignature, TypeError, ValueError):
        return False
    return hmac.compare_digest(actual, expected)


def generate_rsa_identity_key_pair() -> Tuple[bytes, bytes]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return private_pem, public_pem


def rsa_sign(private_pem: bytes, message: bytes) -> bytes:
    private_key = serialization.load_pem_private_key(private_pem, password=None)
    return private_key.sign(message, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())


def rsa_verify(public_pem: bytes, message: bytes, signature: bytes) -> bool:
    try:
        public_key = serialization.load_pem_public_key(public_pem)
        public_key.verify(signature, message, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        return True
    except (InvalidSignature, TypeError, ValueError):
        return False


def generate_signing_key_pair() -> Tuple[bytes, bytes]:
    private_key = ed25519.Ed25519PrivateKey.generate()
    return (
        private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ),
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ),
    )


def sign_message(private_key: bytes, message: bytes, counter: int) -> bytes:
    key = ed25519.Ed25519PrivateKey.from_private_bytes(private_key)
    return key.sign(_counter_bytes(counter) + message)


def verify_signature(public_key: bytes, message: bytes, counter: int, signature: bytes) -> bool:
    try:
        key = ed25519.Ed25519PublicKey.from_public_bytes(public_key)
        key.verify(signature, _counter_bytes(counter) + message)
    except (InvalidSignature, TypeError, ValueError):
        return False
    return True


def generate_exchange_key_pair() -> Tuple[bytes, bytes]:
    private_key = x25519.X25519PrivateKey.generate()
    return (
        private_key.private_bytes(
            serialization.Encoding.Raw,
            serialization.PrivateFormat.Raw,
            serialization.NoEncryption(),
        ),
        private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        ),
    )


def derive_message_key(private_key: bytes, peer_public_key: bytes, context: bytes = b"messenger") -> bytes:
    private = x25519.X25519PrivateKey.from_private_bytes(private_key)
    shared_secret = private.exchange(x25519.X25519PublicKey.from_public_bytes(peer_public_key))
    return HKDF(algorithm=hashes.SHA256(), length=KEY_SIZE, salt=None, info=context).derive(shared_secret)


def encrypt_message(plaintext: bytes, key: bytes, associated_data: bytes = b"") -> Tuple[bytes, bytes]:
    from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_encrypt

    nonce = secrets.token_bytes(24)
    ciphertext = crypto_aead_xchacha20poly1305_ietf_encrypt(
        plaintext,
        associated_data,
        nonce,
        key,
    )
    return nonce, ciphertext


def decrypt_message(ciphertext: bytes, nonce: bytes, key: bytes, associated_data: bytes = b"") -> bytes:
    from nacl.bindings import crypto_aead_xchacha20poly1305_ietf_decrypt

    return crypto_aead_xchacha20poly1305_ietf_decrypt(ciphertext, associated_data, nonce, key)


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def make_session_tag(token: str, uuid: str) -> str:
    return hmac.new(token.encode("utf-8"), uuid.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_session_tag(token: str, uuid: str, tag: str) -> bool:
    expected = make_session_tag(token, uuid)
    return hmac.compare_digest(expected, tag)


def _counter_bytes(counter: int) -> bytes:
    if counter < 0:
        raise ValueError("counter must be non-negative")
    return counter.to_bytes(8, "big")


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))
