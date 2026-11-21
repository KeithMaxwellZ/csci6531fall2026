# Encrypted Messenger

A local encrypted messaging application written in Python.

## Requirements

- Windows
- Python 3 available as `python` in PowerShell

## Configure Email Verification

Create `info.json` in the project root:

```json
{
  "gm": "your-address@gmail.com",
  "pw": "your-google-app-password"
}
```

Use a Gmail app password, not your normal Google password. Enable 2-Step Verification in Google, open the app-password settings, and generate a password for this application.

Keep `info.json` private because it contains credentials.

## Install and Run

Open PowerShell in the project folder:

```powershell
python -m pip install -r requirements.txt
python setup_infra.py
```

The setup script starts the server, routers, and two client windows. Use `Ctrl+C` to stop it.

Before logging in, register actual users in the messenger application. The existing demo credentials are for demo use only.

## Run a Client Manually

```powershell
python application.py --client
```

## Database

`db_init.sql` creates the SQLite tables `users`, `audit_logs`, and `contacts` for `server.sqlite3`. The server may add demo users `alice` and `bob` when the users table is empty.
