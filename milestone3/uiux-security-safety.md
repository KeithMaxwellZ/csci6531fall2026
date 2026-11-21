# Safety-Focused UI/UX Features

The Encrypted Messenger interface communicates security-sensitive outcomes with clear, user-readable feedback while avoiding unnecessary disclosure of account or system details.

- After three failed password attempts, the login UI shows a lockout warning and reports a 30-second timeout before another attempt can be made.
- Successful account registration produces an explicit success confirmation.
- A failed message send produces a warning. The message is removed from the optimistic transcript instead of being displayed as successfully sent.
- Login, 2FA, missing-field, authentication, and malformed-request failures use generic pop-up messages. These messages provide useful feedback without exposing personal information or internal server details.
- Invalid login credentials are consistently reported as “Invalid username or password.” This prevents an attacker from learning whether a guessed username exists.
- Authentication and protected operations require server-side session tokens. The interface provides feedback and workflow controls, but it does not act as the security boundary.
