# Encrypted Messenger

**CSCI 4531/6531 — Course Project**
**Application:** A local desktop messenger with client-side message protection

## What This Application Does

Encrypted Messenger is a Python desktop application for private one-to-one
messaging over a small local relay network. Users register an account, sign in
with a password and an email verification code, choose a contact, and exchange
messages through the Tkinter chat interface. A central server manages accounts,
contacts, public keys, sessions, delivery, and audit events; routers forward
payloads without needing the message plaintext.

The project is intended for a local or academic deployment. Its primary security
goal is to protect message confidentiality, integrity, authenticity, and replay
freshness even though the relay and server handle the encrypted message envelope.
It also protects account credentials and server operations with password hashing,
two-factor authentication, session validation, authorization, and rate limiting.

## Security Properties Implemented

| Property | Implementation | Key files |
|---|---|---|
| Password protection | Salted Argon2id password records through `argon2-cffi`; legacy PBKDF2 records can be upgraded during login | `crypto_utils.py:hash_password`, `crypto_utils.py:verify_password`, `full_server.py` |
| Authentication | Password verification followed by a six-digit email 2FA code; codes expire after five minutes and allow five attempts | `full_server.py:_login`, `full_server.py:_send_2fa_code`, `full_server.py:_verify_2fa` |
| Login abuse resistance | Three failed password attempts trigger a 30-second server lockout; 2FA attempts are capped | `full_server.py`, `application.py` |
| Session security | Random session tokens, constant-time comparison, 24-hour expiry, and logout revocation | `crypto_utils.py:generate_session_token`, `full_server.py:_authenticate`, `full_server.py:_logout` |
| Authorization | Protected operations require an authenticated session, and messaging requires an established contact relationship | `full_server.py:on_receive`, `full_server.py:_send_message` |
| Message confidentiality and tamper detection | X25519 plus HKDF derives a session key; XChaCha20-Poly1305 encrypts and authenticates each message with fresh nonces and associated data | `crypto_utils.py:derive_message_key`, `crypto_utils.py:encrypt_message`, `crypto_utils.py:decrypt_message`, `application.py` |
| Message authenticity | The sender signs the message envelope with an RSA identity key; the recipient verifies it before decryption | `crypto_utils.py:rsa_sign`, `crypto_utils.py:rsa_verify`, `application.py:_do_send_message`, `application.py:_on_receive_message` |
| Replay resistance and key continuity | Signed counters and session identifiers reject stale messages; contact key fingerprints detect unexpected key changes | `application.py:_do_send_message`, `application.py:_on_receive_message`, `application.py:_fetch_contact_keys` |
| Persistence and auditability | SQLite stores users, contacts, public keys, and authentication/audit events | `full_server.py:_initialize_database`, `full_server.py:_log_event` |

## Quick Start

See the project [SETUP.md](../../../SETUP.md) for the setup guide. The application requires Windows,
Python 3, and the dependencies listed in `requirements.txt`.

Create a root-level `info.json` containing a Gmail address and an app password so
the server can send 2FA codes. Keep this file private and never commit it:

```json
{
	"gm": "your-address@gmail.com",
	"pw": "your-google-app-password"
}
```

From the project root, install dependencies and start the local server, routers,
and two client windows:

```powershell
python -m pip install -r requirements.txt
python setup_infra.py
```

The setup script prints the server and router addresses. Register accounts from
the client UI before signing in. Press `Ctrl+C` in PowerShell to stop the local
infrastructure and client processes.

## Project Structure

```
application.py      # Tkinter desktop client and chat workflow
client.py           # Client-side HTTP forwarding
crypto_utils.py     # Password hashing and cryptographic primitives
full_server.py      # Account, session, 2FA, authorization, and delivery logic
router.py           # Relay/router implementation
server.py           # Base HTTP node/server behavior
payload.py          # JSON payload serialization
setup_infra.py      # Starts the server, routers, and client processes
db_init.sql         # SQLite schema initialization
tests/              # Security and protocol tests
```

## Security Architecture Notes

The client creates the message protection material and encrypts and signs a
message before forwarding it. X25519 and HKDF derive a contact/session-specific
key, while XChaCha20-Poly1305 authenticates the ciphertext and associated data.
The server and routers forward the envelope and do not intentionally store the
message plaintext. The recipient checks the sender signature, session identifier,
counter, and contact key fingerprint before accepting and decrypting a message.

The server remains the security boundary for accounts and protected operations.
`FullServer._authenticate` validates session ownership, expiry, and revocation;
`FullServer.on_receive` applies authentication requirements before dispatching
protected request types; and the message handler checks contact authorization.
SQLite persistence keeps account, contact, public-key, and audit data across
server restarts.

This is a local academic prototype. Network transport currently uses HTTP rather
than TLS, so credentials, session tokens, 2FA traffic, and routing metadata are
not protected from a network observer. The client also keeps private keys in
memory and does not provide production key backup, rotation, or recovery.
