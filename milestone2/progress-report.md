# Progress Report
## CSCI 4531/6531 — Milestone 2

**Team:** Keith Zhang (Architect), Zihan Yang (Engineer), Waylon Tan (Auditor)  
**Application:** #4 Encrypted Messenger  
**Date:** October 30, 2026  

---

## Build Status

### What Is Working

| Feature / Flow | Status | How to Verify |
|---|---|---|
| User registration | Complete | Start the infrastructure with `python setup_infra.py`, run `python application.py`, and create an account from the desktop registration screen. |
| Login and email 2FA flow | Complete | Run the infrastructure, sign in with a demo account such as `alice`, and submit the emailed verification code. SMTP configuration is required. |
| Relay and client-node forwarding | Complete | Run `python setup_infra.py`; observe the printed server and router addresses. |
| Contact discovery and session initiation | Complete | After login, refresh the contacts list and select a contact. The server records the relationship and the client initiates it before sending the first message. |
| Message delivery through the relay | Complete | Log in two clients, select an available contact, and send a message. The recipient client displays the forwarded message, but the session management is not fully implemented. |
| Logout and presence updates | Complete | Log in, log out, and observe the client return to the login screen and other clients refresh presence. |

### What Is Incomplete

| Feature | Status | Blocker / Reason |
|---|---|---|
| End-to-end message confidentiality | Partial | The planned client-side encryption and key exchange are not fully implemented. |
| Authorization and session binding | Partial | Request handlers trust caller-supplied usernames and do not consistently require an authenticated session or an authorized contact relationship. |
| Input validation and hardened transport | Not Started | Payload type/size validation, meaningful HTTP error statuses, TLS, persistence, and production key storage remain to be implemented. |

### Architecture as Built

The working build is a Python desktop application connected to a centrailized server. 
A `Client` sends serialized `Payload` objects through a `Router` as a relay point
to `FullServer`; the server handles account, login/2FA, contact, session, logout,
and message requests, then forwards messages through a router to the recipient
client. The Tkinter application polls its client node for received messages.

---

## Unexpected Changes and Deviations

No major deviations from Milestone 1 proposal.

---

## Demo Video

Detailed in separate document (demo.pdf)

---

## AI Usage Summary

Detailed in separate document (ai-usage.pdf)

---

## Known Concerns

Detailed in separate document (audit-plan.pdf)