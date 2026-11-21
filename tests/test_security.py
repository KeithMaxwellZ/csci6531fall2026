import base64
import json
import sqlite3
import tempfile
import time
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import MagicMock, patch

from nacl.exceptions import CryptoError

from application import MessengerApp
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
    generate_rsa_identity_key_pair,
    rsa_sign,
    rsa_verify,
    verify_signature,
)
from full_server import FullServer
from payload import Payload


class CryptoProtocolTests(unittest.TestCase):
    def test_password_record_is_not_plaintext(self):
        record = hash_password("correct horse battery staple")
        self.assertNotIn("correct horse battery staple", record)
        self.assertTrue(verify_password("correct horse battery staple", record))
        self.assertFalse(verify_password("wrong password", record))

    def test_ciphertext_tampering_and_wrong_key_are_rejected(self):
        sender_private, sender_public = generate_exchange_key_pair()
        receiver_private, receiver_public = generate_exchange_key_pair()
        outsider_private, outsider_public = generate_exchange_key_pair()
        sender_key = derive_message_key(sender_private, receiver_public)
        receiver_key = derive_message_key(receiver_private, sender_public)
        outsider_key = derive_message_key(outsider_private, outsider_public)

        nonce, ciphertext = encrypt_message(b"private text", sender_key, b"sender=alice,target=bob,counter=1")
        tampered = bytes([ciphertext[0] ^ 1]) + ciphertext[1:] if ciphertext else ciphertext

        self.assertEqual(
            decrypt_message(ciphertext, nonce, receiver_key, b"sender=alice,target=bob,counter=1"),
            b"private text",
        )
        with self.assertRaises(CryptoError):
            decrypt_message(tampered, nonce, receiver_key, b"sender=alice,target=bob,counter=1")
        with self.assertRaises(CryptoError):
            decrypt_message(ciphertext, nonce, outsider_key, b"sender=alice,target=bob,counter=1")

    def test_authenticated_message_encryption_round_trip(self):
        sender_private, sender_public = generate_exchange_key_pair()
        receiver_private, receiver_public = generate_exchange_key_pair()
        sender_key = derive_message_key(sender_private, receiver_public)
        receiver_key = derive_message_key(receiver_private, sender_public)
        nonce, ciphertext = encrypt_message(b"secret", sender_key, b"counter:1")

        self.assertEqual(
            decrypt_message(ciphertext, nonce, receiver_key, b"counter:1"), b"secret"
        )
        with self.assertRaises(CryptoError):
            decrypt_message(ciphertext, nonce, receiver_key, b"counter:2")

    def test_chat_session_context_separates_message_keys(self):
        sender_private, sender_public = generate_exchange_key_pair()
        receiver_private, receiver_public = generate_exchange_key_pair()
        sender_first_key = derive_message_key(
            sender_private, receiver_public, b"messenger:first-session"
        )
        receiver_first_key = derive_message_key(
            receiver_private, sender_public, b"messenger:first-session"
        )
        sender_second_key = derive_message_key(
            sender_private, receiver_public, b"messenger:second-session"
        )

        self.assertEqual(sender_first_key, receiver_first_key)
        self.assertNotEqual(sender_first_key, sender_second_key)

    def test_refreshing_contact_keys_preserves_session_key(self):
        app = MessengerApp.__new__(MessengerApp)
        app.username = "alice"
        app.session_token = "test-token"
        app.exchange_private_key, _ = generate_exchange_key_pair()
        _, bob_exchange_public_key = generate_exchange_key_pair()
        _, bob_identity_public_key = generate_rsa_identity_key_pair()
        app.contact_exchange_keys = {}
        app.contact_identity_keys = {}
        app.contact_key_fingerprints = {}

        sender_private, sender_public = generate_exchange_key_pair()
        receiver_private, receiver_public = generate_exchange_key_pair()
        session_key = derive_message_key(
            sender_private,
            receiver_public,
            context=b"messenger:shared-session",
        )
        app.message_keys = {"bob": session_key}
        app.client = MagicMock()
        app.client._forward.return_value = Payload(json.dumps({
            "status_code": 200,
            "exchange_public_key": base64.b64encode(bob_exchange_public_key).decode("ascii"),
            "identity_public_key": base64.b64encode(bob_identity_public_key).decode("ascii"),
        }), "")

        self.assertTrue(app._fetch_contact_keys("bob"))
        self.assertIs(app.message_keys["bob"], session_key)

    def test_rsa_identity_signature_round_trip(self):
        private_key, public_key = generate_rsa_identity_key_pair()
        message = b"verified identity fingerprint"
        signature = rsa_sign(private_key, message)

        self.assertTrue(rsa_verify(public_key, message, signature))
        self.assertFalse(rsa_verify(public_key, b"changed message", signature))

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
        self.alice_token = "alice-token"
        self.server.sessions["alice"] = {
            "authenticated": True,
            "session_token": self.alice_token,
            "session_expires_at": time.time() + 60,
        }

    def request(self, request, username="alice", token="__default__", server=None):
        server = server or self.server
        request = dict(request)
        request.setdefault("username", username)
        if token == "__default__":
            request.setdefault("session_token", self.alice_token)
        elif token is not None:
            request["session_token"] = token
        response = server.on_receive(Payload(json.dumps(request), ""))
        return json.loads(response.data)

    def establish_contact(self):
        response = self.request({"type": "initiate_session", "contact": "bob"})
        self.assertEqual(response["status_code"], 200)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_registered_user_and_audit_log_persist(self):
        response = self.server._register(
            {"username": "carol", "password": "password", "email": "carol@example.com"}
        )
        self.assertEqual(json.loads(response.data)["status_code"], 200)

        reloaded = FullServer(database_path=self.database_path)
        self.assertIn("carol", reloaded.users)
        self.assertTrue(reloaded.users["carol"]["password"].startswith("$argon2"))

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

        login = self.request({"type": "login", "password": "alice"}, token=None)
        self.assertEqual(login["status_code"], 200)
        self.assertEqual(smtp.send_message.call_args.args[0]["To"], "alice@example.com")

        session = self.server.sessions["alice"]
        rejected = self.request({"type": "2fa", "code": "000000"}, token=None)
        self.assertEqual(rejected["status_code"], 401)

        verified = self.request({"type": "2fa", "code": session["two_factor_code"]}, token=None)
        self.assertEqual(verified["status_code"], 200)
        self.assertTrue(verified["session_token"])
        self.assertTrue(verified["reauth_token"])
        authenticated = self.request(
            {"type": "fetch_contacts"}, token=verified["session_token"]
        )
        self.assertEqual(authenticated["status_code"], 200)
        logged_out = self.request(
            {"type": "logout"}, token=verified["session_token"]
        )
        self.assertEqual(logged_out["status_code"], 200)

    def test_login_syncs_mutual_contact_directory(self):
        with patch("full_server.smtplib.SMTP"):
            login = self.request({"type": "login", "password": "alice"}, token=None)
        self.assertEqual(login["status_code"], 200)

        code = self.server.sessions["alice"]["two_factor_code"]
        verified = self.request({"type": "2fa", "code": code}, token=None)
        self.assertEqual(verified["status_code"], 200)

        contacts = self.request(
            {"type": "fetch_contacts"},
            token=verified["session_token"],
        )
        self.assertEqual(contacts["contacts"], ["bob"])

    def test_duplicate_registration_and_wrong_password(self):
        duplicate = json.loads(self.server._register(
            {"username": "alice", "password": "other", "email": "other@example.com"}
        ).data)
        self.assertEqual(duplicate["status_code"], 409)

        wrong_password = json.loads(self.server._login(
            {"username": "alice", "password": "wrong"}
        ).data)
        self.assertEqual(wrong_password["status_code"], 401)

        unknown_user = json.loads(self.server._login(
            {"username": "nobody", "password": "password"}
        ).data)
        self.assertEqual(unknown_user["status_code"], 401)

    def test_malformed_and_unknown_requests(self):
        malformed = json.loads(self.server.on_receive(Payload("not-json", "")).data)
        self.assertEqual(malformed["status_code"], 400)

        unknown = json.loads(self.server.on_receive(Payload(
            json.dumps({"type": "does_not_exist"}), ""
        )).data)
        self.assertEqual(unknown["status_code"], 400)

        missing = json.loads(self.server.on_receive(Payload(
            json.dumps({"type": "register"}), ""
        )).data)
        self.assertEqual(missing["status_code"], 400)

    def test_two_factor_attempt_limit_and_expiry(self):
        with patch("full_server.smtplib.SMTP"):
            login = self.request({"type": "login", "password": "alice"}, token=None)
        self.assertEqual(login["status_code"], 200)

        for _ in range(5):
            rejected = self.request({"type": "2fa", "code": "000000"}, token=None)
        self.assertEqual(rejected["status_code"], 401)

        self.server.sessions["alice"] = {
            "authenticated": False,
            "two_factor_code": "123456",
            "two_factor_expires_at": time.time() - 1,
            "two_factor_attempts": 0,
        }
        expired = self.request({"type": "2fa", "code": "123456"}, token=None)
        self.assertEqual(expired["status_code"], 401)
        self.assertIn("expired", expired["message"])

    def test_passwords_use_distinct_salts_and_persist_after_reload(self):
        first = self.server._register(
            {"username": "dana", "password": "same-password", "email": "d1@example.com"}
        )
        second = self.server._register(
            {"username": "erin", "password": "same-password", "email": "e1@example.com"}
        )
        self.assertEqual(json.loads(first.data)["status_code"], 200)
        self.assertEqual(json.loads(second.data)["status_code"], 200)

        reloaded = FullServer(database_path=self.database_path)
        dana_hash = reloaded.users["dana"]["password"]
        erin_hash = reloaded.users["erin"]["password"]
        self.assertNotEqual(dana_hash, erin_hash)
        self.assertTrue(verify_password("same-password", dana_hash))
        self.assertTrue(verify_password("same-password", erin_hash))

        with closing(sqlite3.connect(self.database_path)) as connection:
            rows = connection.execute(
                "SELECT password FROM users WHERE username IN ('dana', 'erin')"
            ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row[0].startswith("$argon2") for row in rows))

    def test_contacts_and_audit_events_survive_user_reload(self):
        register = self.request({
            "type": "register",
            "username": "carol",
            "password": "password",
            "email": "carol@example.com",
        }, token=None)
        self.assertEqual(register["status_code"], 200)

        self.server.sessions["carol"] = {
            "authenticated": True,
            "session_token": "carol-token",
            "session_expires_at": time.time() + 60,
        }
        initiated = self.request(
            {"type": "initiate_session", "contact": "bob"},
            username="carol",
            token="carol-token",
        )
        self.assertEqual(initiated["status_code"], 200)

        reloaded = FullServer(database_path=self.database_path)
        self.assertIn("carol", reloaded.users)
        self.assertIn("bob", reloaded.users)
        reloaded.sessions["carol"] = {
            "authenticated": True,
            "session_token": "carol-token",
            "session_expires_at": time.time() + 60,
        }
        contacts = self.request(
            {"type": "fetch_contacts"},
            username="carol",
            token="carol-token",
            server=reloaded,
        )
        self.assertEqual(contacts["contacts"], ["bob"])

        with closing(sqlite3.connect(self.database_path)) as connection:
            register_events = connection.execute(
                "SELECT event, success FROM audit_logs WHERE username = 'carol'"
            ).fetchall()
        self.assertIn(("register", 1), register_events)

    def test_public_keys_persist_across_server_restart_and_key_change_is_visible(self):
        self.establish_contact()
        _exchange_private, exchange_public = generate_exchange_key_pair()
        _identity_private, identity_public = generate_rsa_identity_key_pair()
        exchange_text = base64.b64encode(exchange_public).decode("ascii")
        identity_text = base64.b64encode(identity_public).decode("ascii")

        published = self.request({
            "type": "publish_keys",
            "exchange_public_key": exchange_text,
            "identity_public_key": identity_text,
        })
        self.assertEqual(published["status_code"], 200)

        reloaded = FullServer(database_path=self.database_path)
        reloaded.sessions["alice"] = {
            "authenticated": True,
            "session_token": "alice-token",
            "session_expires_at": time.time() + 60,
        }
        reloaded.sessions["bob"] = {
            "authenticated": True,
            "session_token": "bob-token",
            "session_expires_at": time.time() + 60,
        }
        fetched = self.request({
            "type": "fetch_keys",
            "contact": "alice",
        }, username="bob", token="bob-token", server=reloaded)
        self.assertEqual(fetched["exchange_public_key"], exchange_text)
        self.assertEqual(fetched["identity_public_key"], identity_text)

        _new_exchange_private, new_exchange_public = generate_exchange_key_pair()
        _new_identity_private, new_identity_public = generate_rsa_identity_key_pair()
        new_exchange_text = base64.b64encode(new_exchange_public).decode("ascii")
        new_identity_text = base64.b64encode(new_identity_public).decode("ascii")
        changed = self.request({
            "type": "publish_keys",
            "exchange_public_key": new_exchange_text,
            "identity_public_key": new_identity_text,
        }, server=reloaded)
        self.assertEqual(changed["status_code"], 200)
        changed = self.request({
            "type": "fetch_keys",
            "contact": "alice",
        }, username="bob", token="bob-token", server=reloaded)
        self.assertNotEqual(changed["exchange_public_key"], exchange_text)
        self.assertNotEqual(changed["identity_public_key"], identity_text)

    def test_public_keys_publish_and_fetch(self):
        self.establish_contact()
        _exchange_private, exchange_public = generate_exchange_key_pair()
        _identity_private, identity_public = generate_rsa_identity_key_pair()
        exchange_text = base64.b64encode(exchange_public).decode("ascii")
        identity_text = base64.b64encode(identity_public).decode("ascii")

        published = self.request({
            "type": "publish_keys",
            "exchange_public_key": exchange_text,
            "identity_public_key": identity_text,
        })
        self.assertEqual(published["status_code"], 200)

        self.server.sessions["bob"] = {
            "authenticated": True,
            "session_token": "bob-token",
            "session_expires_at": time.time() + 60,
        }
        fetched = self.request({
            "type": "fetch_keys",
            "contact": "alice",
        }, username="bob", token="bob-token")
        self.assertEqual(fetched["status_code"], 200)
        self.assertEqual(fetched["exchange_public_key"], exchange_text)
        self.assertEqual(fetched["identity_public_key"], identity_text)

    def test_client_rejects_changed_contact_key_after_pinning(self):
        app = MessengerApp.__new__(MessengerApp)
        app.username = "bob"
        app.session_token = "bob-token"
        app.client = MagicMock()
        app.client.router_addr = "http://router"
        app.exchange_private_key, _ = generate_exchange_key_pair()
        app.contact_key_fingerprints = {}
        app.contact_exchange_keys = {}
        app.contact_identity_keys = {}
        app.message_keys = {}
        app._create_payload = lambda request: Payload(json.dumps(request), "server")

        _peer_private, peer_exchange_public = generate_exchange_key_pair()
        _identity_private, identity_public = generate_rsa_identity_key_pair()
        first_response = Payload(json.dumps({
            "status_code": 200,
            "exchange_public_key": base64.b64encode(peer_exchange_public).decode("ascii"),
            "identity_public_key": base64.b64encode(identity_public).decode("ascii"),
        }), "")
        _new_peer_private, new_exchange_public = generate_exchange_key_pair()
        _new_identity_private, new_identity_public = generate_rsa_identity_key_pair()
        changed_response = Payload(json.dumps({
            "status_code": 200,
            "exchange_public_key": base64.b64encode(new_exchange_public).decode("ascii"),
            "identity_public_key": base64.b64encode(new_identity_public).decode("ascii"),
        }), "")
        app.client._forward.side_effect = [first_response, changed_response]

        self.assertTrue(app._fetch_contact_keys("alice"))
        self.assertFalse(app._fetch_contact_keys("alice"))

    def test_authenticated_request_operations_are_scoped(self):
        unauthenticated_session = self.request(
            {"type": "initiate_session", "contact": "alice"}, token="wrong-token"
        )
        self.assertEqual(unauthenticated_session["status_code"], 401)

        self.establish_contact()
        fetch = self.request({"type": "fetch_contacts"})
        self.assertIn("bob", fetch["contacts"])

    def test_authenticated_requests_require_matching_live_token(self):
        missing = self.request({"type": "fetch_contacts"}, token=None)
        self.assertEqual(missing["status_code"], 401)

        malformed = self.request({"type": "fetch_contacts"}, token=123)
        self.assertEqual(malformed["status_code"], 401)

        wrong_user = self.request(
            {"type": "fetch_contacts"}, username="bob", token=self.alice_token
        )
        self.assertEqual(wrong_user["status_code"], 401)

        valid = self.request({"type": "fetch_contacts"})
        self.assertEqual(valid["status_code"], 200)

        logged_out = self.request({"type": "logout"})
        self.assertEqual(logged_out["status_code"], 200)
        revoked = self.request({"type": "fetch_contacts"})
        self.assertEqual(revoked["status_code"], 401)

        self.server.sessions["alice"] = {
            "authenticated": True,
            "session_token": self.alice_token,
            "session_expires_at": time.time() - 1,
        }
        expired = self.request({"type": "fetch_contacts"})
        self.assertEqual(expired["status_code"], 401)

    def test_received_session_updates_key_and_repeated_session_is_reused(self):
        app = MessengerApp.__new__(MessengerApp)
        app.username = "bob"
        app.session_token = "bob-token"
        app.client = MagicMock()
        app.exchange_private_key, bob_exchange_public = generate_exchange_key_pair()
        peer_exchange_private, peer_exchange_public = generate_exchange_key_pair()
        peer_identity_private, peer_identity_public = generate_rsa_identity_key_pair()
        app.contact_exchange_keys = {"alice": peer_exchange_public}
        app.contact_identity_keys = {"alice": peer_identity_public}
        app.contact_key_fingerprints = {}
        app.message_keys = {}
        app.chat_sessions = {}
        app.chat_session_history = {}
        app.incoming_counters = {}
        app.outgoing_counters = {}
        app.session_contacts = set()
        app._fetch_contact_keys = lambda contact: True
        app._create_payload = lambda request: Payload(json.dumps(request), "server")

        session_id = "round-one-session"
        app.contact_exchange_keys["alice"] = peer_exchange_public
        key = derive_message_key(peer_exchange_private, bob_exchange_public, context=f"messenger:{session_id}".encode("utf-8"))

        nonce, ciphertext = encrypt_message(b"round one", key, json.dumps({
            "sender": "alice",
            "target": "bob",
            "session_id": session_id,
            "counter": 1,
        }, sort_keys=True).encode("utf-8"))
        envelope = {
            "nonce": base64.b64encode(nonce).decode("ascii"),
            "ciphertext": base64.b64encode(ciphertext).decode("ascii"),
            "counter": 1,
            "session_id": session_id,
            "signature": base64.b64encode(rsa_sign(peer_identity_private, json.dumps({
                "sender": "alice", "target": "bob", "session_id": session_id, "counter": 1,
            }, sort_keys=True).encode("utf-8") + nonce + ciphertext)).decode("ascii"),
        }
        payload = Payload(json.dumps({"sender": "alice", "message": json.dumps(envelope)}), "")

        self.assertEqual(app._on_receive_message(payload), ("alice", "round one"))
        self.assertEqual(app.chat_sessions["alice"], session_id)
        self.assertTrue(app._do_initiate_session("alice"))
        self.assertEqual(app.chat_sessions["alice"], session_id)
        app.client._forward.assert_not_called()

    def test_message_requires_an_established_contact(self):
        response = self.request({
            "type": "message",
            "target": "bob",
            "message": "not authorized yet",
        })
        self.assertEqual(response["status_code"], 403)

    @patch("full_server.smtplib.SMTP")
    def test_login_is_rate_limited_server_side(self, smtp_class):
        for _ in range(3):
            response = self.request({"type": "login", "password": "wrong"}, token=None)
            self.assertEqual(response["status_code"], 401)
        locked = self.request({"type": "login", "password": "alice"}, token=None)
        self.assertEqual(locked["status_code"], 429)

        self.server.login_failures["alice"]["locked_until"] = time.monotonic() - 1
        smtp = MagicMock()
        smtp.__enter__.return_value = smtp
        smtp_class.return_value = smtp
        after_expiry = self.request({"type": "login", "password": "alice"}, token=None)
        self.assertEqual(after_expiry["status_code"], 200)
        self.assertNotIn("alice", self.server.login_failures)

    @patch("router.logger")
    def test_router_debug_logging_does_not_include_payload_body(self, logger):
        from router import BaseRouter

        BaseRouter("http://server").inspect_payload(Payload('password="secret"', "route"))
        logged_text = " ".join(str(call) for call in logger.debug.call_args_list)
        self.assertNotIn("secret", logged_text)

    def test_contacts_persist_across_server_restart(self):
        self.establish_contact()
        reloaded = FullServer(database_path=self.database_path)
        reloaded.sessions["alice"] = {
            "authenticated": True,
            "session_token": "alice-token",
            "session_expires_at": time.time() + 60,
        }
        contacts = self.request({"type": "fetch_contacts"}, server=reloaded)
        self.assertEqual(contacts["contacts"], ["bob"])


if __name__ == "__main__":
    unittest.main()
