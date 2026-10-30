# AI Usage Report
## CSCI 4531/6531 — Milestone 2

**Team:** Keith Zhang (Architect), Zihan Yang (Engineer), Waylon Tan (Auditor)  
**Application:** #4 Encrypted Messenger  
**Date:** October 30, 2026  

---

## Summary

### Tools Used

| Tool | Primary Use |
|---|---|
| Claude sonnet 5.5 | Architecture discussions, explaining library choices |
| GPT-5.6 Luna | Implementation of functions |


### What AI Got Right

- Generation of most UI/UX elements and functions
- Generations of placeholders for service functions
- Documentation and verifications of human codes

### Where AI Required Correction

- Implemented bugged animations of transitions, to make it easy we decided to just get rid of animations
- Introduced a duplicate logout button, it could pass compliation but it's a obvious visual bug.
- Implemented client-side lockout, which we identified as bypassable without server-side rate limiting. (It's a known issue and we are working on the fix)

### Security-Critical Sections Handled Without AI

- Manually reviewed the 2FA flow, logout broadcasts, password hashing and salting.
- Implementation of the whole server-relay-client infrasture.

---

## Interaction Transcripts

---

### Transcript 1 — UI implementation

**Tool:** Claude

**Prompt:**
```
Base on the design doc here, implement a user interface. Also, it launches a client node on startup. For exact sending and resolving functions, you can put some placeholders to make some dummy reactions, I'll do them by myself
```

**AI Response (excerpt):**
```
Implemented the UI in application.py.

It now includes:

Tkinter login/account creation screen
Chat interface with Bob and Carol contacts
Placeholder message sending and receiving
Administrator dashboard with service and account status
Automatic BaseClient node startup on application launch
Clean client shutdown when the window closes
Run it with:

python application.py

Validation passed: syntax compilation and client node start/stop smoke test.
```

**Your annotation:**
I checked its output and it's mostly aligned with my expectation. Just fixed some minor alignment or width/height issues.

---

### Transcript 2 — Function completeness tracking

**Tool:** Claude

**Prompt:**
```
Base on this design plan and the code I provided here, does these cover all planned functionalities?
(Markdown and python scripts are attached)
```

**AI Response (excerpt):**
```
The application has these functions:

Present and connected

Login screen: show_login
Chat screen: show_chat
Contact selection: select_contact
Message display: _render_messages
Message composition: send_message
Client startup/reconnection: _connect_and_show
Application shutdown: close
Basic payload creation/decoding

Present but not connected

_do_fetch_contacts exists, but contacts remain hardcoded in _build_contacts.
_on_receive_message exists, but no callback, polling loop, or UI update calls it.
_do_initiate_session exists, but no UI action invokes it.
BaseClient.on_receive stores incoming payloads, but the application never reads those payloads into the conversation view.
```

**Your annotation:**
This wasn't for implementing stuffs but was helping me tracking my progress and verifying if I have everything I need.

---


