import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch

from cryptography.exceptions import InvalidTag

from crypto_utils import (
    decrypt_message,
    derive_message_key,
    encrypt_message,
    generate_exchange_key_pair,
    generate_signing_key_pair,
    hash_password,
    make_session_tag,
    sign_message,
    verify_password,
    verify_session_tag,
    verify_signature,
)
from full_server import FullServer


class CryptoProtocolTests(unittest.TestCase):
    def test_password_record_is_not_plaintext(self):
        record = hash_password("correct horse battery staple")
        self.assertNotIn("correct horse battery staple", record)
        self.assertTrue(verify_password("correct horse battery staple", record))
        self.assertFalse(verify_password("wrong password", record))

    def test_authenticated_message_encryption_round_trip(self):
        sender_private, sender_public = generate_exchange_key_pair()
        receiver_private, receiver_public = generate_exchange_key_pair()
        sender_key = derive_message_key(sender_private, receiver_public)
        receiver_key = derive_message_key(receiver_private, sender_public)
        nonce, ciphertext = encrypt_message(b"secret", sender_key, b"counter:1")

        self.assertEqual(
            decrypt_message(ciphertext, nonce, receiver_key, b"counter:1"), b"secret"
        )
        with self.assertRaises(InvalidTag):
            decrypt_message(ciphertext, nonce, receiver_key, b"counter:2")

    def test_signature_binds_message_counter(self):
        private_key, public_key = generate_signing_key_pair()
        signature = sign_message(private_key, b"ciphertext", 7)

        self.assertTrue(verify_signature(public_key, b"ciphertext", 7, signature))
        self.assertFalse(verify_signature(public_key, b"ciphertext", 8, signature))
        self.assertFalse(verify_signature(public_key, b"changed", 7, signature))

    def test_session_tag_rejects_changed_uuid(self):
        tag = make_session_tag("session-token", "user-uuid")
        self.assertTrue(verify_session_tag("session-token", "user-uuid", tag))
        self.assertFalse(verify_session_tag("session-token", "other-uuid", tag))


class ServerPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "server.sqlite3"
        self.server = FullServer(database_path=self.database_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registered_user_and_audit_log_persist(self):
        response = self.server._register(
            {"username": "carol", "password": "password", "email": "carol@example.com"}
        )
        self.assertEqual(json.loads(response.data)["status_code"], 200)

        reloaded = FullServer(database_path=self.database_path)
        self.assertIn("carol", reloaded.users)
        self.assertTrue(reloaded.users["carol"]["password"].startswith("pbkdf2_sha256$"))

        with closing(sqlite3.connect(self.database_path)) as connection:
            logs = connection.execute(
                "SELECT event, success FROM audit_logs WHERE username = ?",
                ("carol",),
            ).fetchall()
        self.assertIn(("register", 1), logs)

    @patch("full_server.smtplib.SMTP")
    def test_login_otp_and_token_flow(self, smtp_class):
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp_class.return_value = smtp

        login = json.loads(self.server._login({"username": "alice", "password": "alice"}).data)
        self.assertEqual(login["status_code"], 200)
        self.assertEqual(smtp.send_message.call_args.args[0]["To"], "keithzhang021@gmail.com")

        session = self.server.sessions["alice"]
        rejected = json.loads(
            self.server._verify_2fa({"username": "alice", "code": "000000"}).data
        )
        self.assertEqual(rejected["status_code"], 401)

        verified = json.loads(
            self.server._verify_2fa(
                {"username": "alice", "code": session["two_factor_code"]}
            ).data
        )
        self.assertEqual(verified["status_code"], 200)
        self.assertTrue(verified["session_token"])
        self.assertTrue(verified["reauth_token"])


if __name__ == "__main__":
    unittest.main()
