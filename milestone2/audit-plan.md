# Audit Plan
## CSCI 4531/6531 — Milestone 2

**Team:** Keith Zhang (Architect), Zihan Yang (Engineer), Waylon Tan (Auditor)  
**Application:** #4 Encrypted Messenger  
**Date:** October 30, 2026  


## Attack Surface Map

### Trust Boundaries

| Boundary | What crosses it | Risk |
|---|---|---|
| Client → Router | User submitted JSON payloads | Sensitive data exposure, malformed input |
| Router → Server | Registration, login, and message requests | Unauthorized access, credential exposure |
| Server → Router | Forwarded messages and routing information | Sensitive data exposure, message misdelivery |
| Router → Recipient Client | Forwarded messages and sender information | Sender impersonation, message tampering |

### Security-Sensitive Operations

| Operation | Property | Location in code |
|---|---|---|
| User registration and password storage | Accounts | `full_server.py:_register()` |
| Password verification on login | Authentication | `full_server.py:_login()` |
| 2FA verification | Authentication | `full_server.py:_verify_2fa()` |
| Session initiation | Session Management | `full_server.py:_initiate_session()` |
| Message forwarding | Message Security | `full_server.py:_send_message()` |

---

## Threat Scenarios

Test harness: a Python script using `requests` that POSTs hand-built `Payload` JSON directly to the server's `/payload` endpoint and to a client's `/receive` endpoint, bypassing the desktop UI. Two registered test accounts (`alice`, `bob`) and one unregistered attacker identity (`mallory`) are used throughout.

| # | Property | Attack Scenario | How We Will Test It | Expected secure result |
|---|---|---|---|---|
| 1 | Accounts | Brute-force / credential stuffing on `login` | Script 1,000 rapid `login` requests for `alice` with wrong passwords, then one with the correct password; observe throttling, lockout, or delay | Rate limiting or lockout activates; correct password is also refused during lockout |
| 2 | Accounts | Duplicate or malformed registration (existing username, case variants such as `Alice`, whitespace, empty or oversized username, weak password) | Send `register` for existing and edge-case usernames/passwords; check whether the existing account is overwritten | Existing account unchanged; invalid input rejected with an error `status_code` |
| 3 | Password storage | Plaintext or weakly hashed passwords at rest | Register a user, then inspect the server's storage (in-memory structures, any files or database) for the password string; check whether the hash is salted and slow (bcrypt/argon2/scrypt) | No plaintext; salted, slow hash |
| 4 | Authentication (2FA) | Brute-force or bypass of the verification code | Script all 1,000,000 6-digit-style guesses (or a capped sample) against `2fa`; also send `initiate_session` and `message` after `login` without ever sending `2fa` | Code attempts limited; codes expire; session features refused until 2FA succeeds |
| 5 | Authentication (2FA) | Reuse or leak of the 2FA code | Reuse a valid code a second time; search server stdout and logs for the code value | Code is single-use, short-lived, and never logged |
| 6 | Session management | Message sent with no session or no login (known concern 1) | As `mallory` (never logged in), send a `message` payload with `username: alice` and `target: bob` | Rejected with an error; nothing delivered to `bob` |
| 7 | Session management | Impersonation via the `username` field | Log in as `alice`, then send `message` with `username: bob` (and `initiate_session` / `fetch_contacts` likewise); the claimed username should not be trusted | Identity is bound to the authenticated session, not the request field; mismatch rejected |
| 8 | Session management | Session fixation, expiry, and logout | Reuse an old session after the intended expiry, after re-login, and after the user's router/client address changes; send `message` without `initiate_session` to a contact | Stale or never-initiated sessions are rejected |
| 9 | Authorization | Messaging a target the sender has no session with, or fetching another user's contacts | As `alice`, `message` a `target` she has not initiated a session with; as `mallory`, call `fetch_contacts` for `alice` | Delivery and contact data refused unless authorized |
| 10 | Message confidentiality | Plaintext messages readable by a passive on-path observer | Capture the raw HTTP body at a router (or its logs) while `alice` messages `bob`; grep for the message text | Only ciphertext visible (expected to FAIL today: encryption not implemented; record as a finding) |
| 11 | Message integrity and authenticity | Tampering or forging a message in transit, or forging the `sender` shown to the recipient | POST a hand-built payload straight to `bob`'s `/receive` with `sender: alice`; modify a captured payload's `message` and replay it onward | Recipient verifies the signature and rejects unsigned or altered messages (expected to FAIL today) |
| 12 | Replay protection | Replaying a captured valid payload | Capture a legitimate `message` or `login` payload and re-send it N times, including after delay | Duplicates detected via nonce/timestamp; replays rejected (expected to FAIL today) |
| 13 | Message delivery | Interception and dropping (allowed by the threat model) | Drop a forwarded payload at the router and observe client behavior | Sender is not told "delivered" falsely; no crash or silent loss (acknowledgement or error surfaced) |
| 14 | Input validation | Malformed or hostile JSON | Send to `/payload`: invalid JSON, missing `data`/`route`, `data` that is not a JSON string, unknown or missing `type`, duplicate keys, wrong types (int/list/null in `username`), 10 MB+ bodies, deeply nested JSON, unicode and control characters, wrong `Content-Length`; send to other paths (not `/payload`) | Server returns an error and keeps running; no stack trace to the caller; size limits enforced |
| 15 | Injection / output handling | Hostile strings that reach the client UI or storage (e.g. format strings, very long messages, path or SQL-like characters in `username`) | Register and message with such values; check the receiving desktop client display and the persistent store | Treated purely as data; no crash, truncation bug, or query manipulation |
| 16 | Key protection (known concern 2) | Private key exposure at rest or in memory | Search the project directory and client storage for key files; check file permissions and whether keys are stored unencrypted; check whether a second local user or the "local operator" can read them | Private keys encrypted at rest or access-restricted |
| 17 | Logging / data exposure (known concern 3) | Secrets in debug logs | Run a full register, login, 2FA, and message flow; search all stdout, stderr, and log files for passwords, 2FA codes, session tokens, key material, and plaintext messages (routers log payload `data`) | No secrets or plaintext content in any log |
| 18 | Availability | Resource exhaustion by one client | Open many concurrent connections and send slow or oversized requests (the node uses a threaded HTTP server); flood `register` | Rate limits and timeouts apply; legitimate requests still served |
| 19 | Information disclosure | User enumeration and verbose errors | Compare error responses and timing for existing vs non-existing usernames on `login` and `register` | Identical responses and timing; no internal details |

Each scenario will be logged as: ID, steps, observed result, pass/fail, severity, and a proposed fix. Scenarios 10-12 depend on the unimplemented encryption/signing layer, so they will be re-run once it is merged.

---

## AI Red-Team Methodology

### Tool

Both Claude and GPT will be used for testing, and their results will be cross-checked to identify recurring vulnerabilities and model-specific findings.

### Prompting strategy

The strategy is run in three passes:

1. **Design-context review.** Provide the AI with a short summary of the architecture, threat model, trusted fields, current implementation limits, and existing threat scenarios. Ask it to identify likely concerns and map them to the scenarios already listed. This keeps the design review focused without requiring a separate list of attacks for every property.
2. **White-box code review.** Give the AI access to the repository and identify the implementation files and functions that control each scenario. Ask it to inspect the code for concrete vulnerabilities, explain the attack path, and identify the expected secure behavior. The AI may create or modify audit scripts and test fixtures directly, but production-code changes require separate authorization.
3. **Exploit validation.** For each credible finding, ask the AI to write or modify a minimal proof-of-concept script and run it against the local setup. If the finding involves visual behavior or a frontend interaction, ask a human tester to execute and assess it. Record the observed response and evidence, then classify the result as confirmed, not reproducible, or theoretical. Ask the AI to check whether multiple weaknesses combine, such as a missing session check with username spoofing and unsigned messages.

We will use the same threat-model preamble in every prompt so the AI does not waste findings on out-of-scope items (such as tampering with `route`).

### Triage and prioritization

AI output is treated as a list of hypotheses, not findings. Each suggestion goes through:

1. **Scope filter.** Discard anything that's out of the threat scope, for example attacks that rely on modifying `route` or router addresses (since it's assumed to be fully secure due to the fact that it's simulating the real network relay).
2. **Deduplicate and map.** Merge duplicates and map each item to a property and to a row in the Threat Scenarios table (adding new rows for anything novel).
3. **Verify.** Reproduce each finding with a script or human test, as appropriate, against the running app. Classify the result as *confirmed*, *not reproducible* (likely a hallucination or already mitigated), or *theoretical* (plausible but untested). Only confirmed items are reported as vulnerabilities.
4. **Score.** Rank confirmed findings by Impact x Exploitability (High/Medium/Low each), plus whether it requires authentication and whether it breaks a core property (account takeover, impersonation, and message disclosure rank highest).
5. **Prioritize fixes.** Group fixes into three priorities: (1) access control, including authentication, session checks, authorization, and identity binding; (2) confidentiality and integrity, including secret and key protection, encryption, signing, and replay protection; and (3) resilience, including input validation and availability.

---

## Known Concerns

1. **Insufficient input and protocol validation.** The server accepts attacker-controlled payload fields without consistent type, size, duplicate-field, or structural validation. Malformed requests can produce errors or unhandled exceptions, and the network layer does not consistently return meaningful error statuses.

2. **Deferred key-protection requirement.** Private-key management is not fully implemented in the current build. When key support is fixed, private keys should be able to be protected against unauthorized local access.
