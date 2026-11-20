# Security Audit Instructions
## Encrypted Messenger

This document lets someone unfamiliar with the project reproduce the security audit
independently. Follow SETUP.md first to set up the application environment.

---

## Prerequisites

* Python and required dependencies installed according to SETUP.md
* Access to the application source code
* Python unittest module
* Terminal or command-line environment
* Test accounts available: 
  - alice (admin role) 
  - bob (regular user role)
* GUI application launched using setup_infra.py when required.

---

## Audit Scenario 1 — Unauthorized Message Sending

**Security property tested:** Authentication / Authorization 
**Expected result:** The server rejects unauthenticated message requests with status code 401

### Steps

1. Open a terminal in the project root directory and run the following command:
```bash
python -m unittest tests.test_security_audit.SecurityAuditTests.test_unauthorized_message -v
```

2. Observe the output of test_unauthorized_message.

### Expected Output (defended)

```
Actual Result: {'status_code': 401, 'message': 'Authentication required'}
ok
```

### Actual Result (from our audit)

```
test_unauthorized_message (tests.test_security_audit.SecurityAuditTests.test_unauthorized_message) ... Actual Result: {'status_code': 401, 'message': 'Authentication required'}
ok

----------------------------------------------------------------------
Ran 1 test in 0.074s

OK
```

### Response

No mitigation required
- The server correctly rejected the unauthenticated message request.
  No vulnerability was identified in the tested server handler path

---

## Audit Scenario 2 — Session Impersonation

**Security property tested:** Authentication / Authorization 
**Expected result:** The server rejects a request using Alice's session token while claiming to be Bob, returning status code 401

### Steps

1. Open a terminal in the project root directory and run the following command:

```bash
python -m unittest tests.test_security_audit.SecurityAuditTests.test_session_impersonation -v
```

2. The test creates a temporary database and simulates an authenticated session for Alice

3. The test attempts to send a message using Bob's username and Alice's session token

4. Observe the server response.

### Expected Output (defended)

```
Actual Result: {'status_code': 401, 'message': 'Authentication required'}
ok
```

### Actual Result

```
test_session_impersonation (tests.test_security_audit.SecurityAuditTests.test_session_impersonation) ... Actual Result: {'status_code': 401, 'message': 'Authentication required'}
ok

----------------------------------------------------------------------
Ran 1 test in 0.070s

OK
```

### Response
No mitigation required
- The server rejected the request containing Alice's session token and Bob's username.
No vulnerability was identified in the tested request path.

---

## Audit Scenario 3 — Brute-Force Login

**Security property tested:** Authentication / Rate Limiting
**Expected result:** After three failed login attempts, 
the server temporarily blocks additional login attempts and returns status code 429

### Steps

1. Open a terminal in the project root directory and run the following command:
```bash
python -m unittest tests.test_security_audit.SecurityAuditTests.test_brute_force_login -v
```

2. The test creates a temporary database and submits four consecutive login requests using the username alice and an incorrect password.

3. Observe the server response codes.

### Expected Output (defended)

```
Attempt 1: 401 - Invalid credentials
Attempt 2: 401 - Invalid credentials
Attempt 3: 401 - Invalid credentials
Attempt 4: 429 - Too many login attempts
ok
```

### Actual Result

```
test_brute_force_login (tests.test_security_audit.SecurityAuditTests.test_brute_force_login) ... Attempt 1: 401 - Invalid credentials
Attempt 2: 401 - Invalid credentials
Attempt 3: 401 - Invalid credentials
Attempt 4: 429 - Too many login attempts
ok

----------------------------------------------------------------------
Ran 1 test in 0.183s

OK
```

### Response

No mitigation required
- The server correctly activated rate limiting after three failed login attempts. 
The fourth attempt returned status code 429, preventing further password guessing during the temporary lockout period. No vulnerability was identified in this test.

---

## Audit Scenario 4 — Message Tampering

**Security property tested:** Integrity / Authenticated Encryption
**Expected result:** The application's encryption functions detect modifications to ciphertext and reject the tampered message.

### Steps

1. Open a terminal in the project root directory and run the following command:
```bash
python -m unittest tests.test_security_audit.SecurityAuditTests.test_message_tampering -v
```

2. The test generates a random encryption key and encrypts a sample message using XChaCha20-Poly1305

3. The original ciphertext is decrypted to verify normal operation

4. The test modifies one bit of the encrypted message and attempts to decrypt the modified ciphertext

5. Observe whether the modified ciphertext is rejected.

### Expected Output (defended)

```
Original message decrypted successfully.
Tampered ciphertext rejected.
ok
```

### Actual Result

```
test_message_tampering (tests.test_security_audit.SecurityAuditTests.test_message_tampering) ... Original message decrypted successfully.
Tampered ciphertext rejected.
ok

----------------------------------------------------------------------
Ran 1 test in 0.344s

OK
```

### Response

No mitigation required
- The XChaCha20-Poly1305 authenticated decryption function correctly rejected the modified ciphertext. No vulnerability was identified in the tested cryptographic operation.

---

## Audit Scenario 5 - Logout Session Replay

**Security property tested:** Authentication / Session Management
**Expected result:** The server invalidates the session token after logout and rejects subsequent requests using the old token with status code 401.

### Steps

1. Open a terminal in the project root directory and run the following command:
```bash
python -m unittest tests.test_security_audit.SecurityAuditTests.test_logout_session_replay -v
```

2. The test creates a temporary database and logs in as Alice using valid credentials. SMTP email delivery is mocked to avoid requiring external email configuration.

3. The test completes 2FA using the demo verification code 666 and obtains a server-generated session token

4. The test logs out using the valid session token

5. The test attempts to send a message using the same token after logout

6. Observe whether the server rejects the replayed token.

### Expected Output (defended)

```
Login successful.
2FA verification successful.
Logout status: 200
Replay status: 401
Replay response: Authentication required
ok
```

### Actual Result

```
test_logout_session_replay (tests.test_security_audit.SecurityAuditTests.test_logout_session_replay) ... Login successful.
2FA verification successful.
Logout status: 200
Replay status: 401
Replay response: Authentication required
ok

----------------------------------------------------------------------
Ran 1 test in 0.101s

OK
```

### Response

No mitigation required
- The server successfully invalidated the session token after logout and rejected the replay attempt. No vulnerability was identified in the tested session management functionality.

---

## AI Red-Team Findings

### AI Tool Used

ChatGPT

### Prompt Used

```
Review the latest source code of our Encrypted Messenger project and identify potential security vulnerabilities. Help me design at least five security attack scenarios using Python unittest, focusing on authentication, authorization, encryption, message integrity, and rate limiting.
```

### Findings Summary

| # | Finding | Property | Tested | Result | Status |
|---|---|---|---|---|---|
| 1 | Unauthorized Message Sending | Authentication | Yes | Defended | No fix required |
| 2 | Session Impersonation | Authorization | Yes | Defended | No fix required |
| 3 | Brute-Force Login | Rate Limiting | Yes | Defended | No fix required |
| 4 | Message Tampering | Integrity | Yes | Defended | No fix required |
| 5 | Logout Session Replay | Session Management | Yes | Defended | No fix required |

---

## Known Residual Risks

| Risk | Severity | Justification for Accepting |
|---|---|---|
| Hardcoded 2FA Demo Bypass | High | The code 666 is retained for local demonstration. It should be disabled before production deployment |
| Missing TLS 1.3 | Medium | The application is currently used for local demonstration and testing. TLS should be implemented before deployment over untrusted networks. |
