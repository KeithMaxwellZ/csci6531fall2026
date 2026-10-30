# How to Run

Place `info.json` in the same folder as the executables and add the SMTP credentials used to send verification codes:

```json
{
  "gm": "your-sender@example.com",
  "pw": "your-smtp-password-or-app-password"
}
```

Any compatible SMTP provider can be used. For Google, use an app password rather than your regular account password.

## Start the System

1. Run `EncryptedMessenger.exe`.
2. The executable starts the server and three relay nodes.
3. It also starts two built-in client windows. These clients can be closed without stopping the server or relays.
4. Log in or register from a client window.

## Start Additional Clients

Optionally run `Application.exe` to start additional client windows. Multiple clients can use the same relay, but a one-to-one client-to-relay assignment is preferred.

Keep `info.json`, `EncryptedMessenger.exe`, and `Application.exe` in the same directory.