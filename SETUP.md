# Encrypted Messenger

A local encrypted messaging application written in Python.

## Requirements

- Windows with Python 3 installed
- Python available as `python` in PowerShell

## Configure `info.json`

The server sends sign-in verification codes by email. Create `info.json` in the project root with a Google account's email address and a Google app password created for that account:

```json
{
  "gm": "your-address@gmail.com",
  "pw": "your-google-app-password"
}
```

`gm` must be the Gmail address, and `pw` must be the corresponding Google app password, not the account's normal password. To create an app password, enable 2-Step Verification for the Google account, open Google's app-password settings, and generate a password for this application.

Keep `info.json` private; it contains credentials and should not be committed to source control.

## Initialize the database

The standalone `db_init.sql` file creates the SQLite tables used by the application:

- `users`
- `audit_logs`
- `contacts`

To create a clean `server.sqlite3` database, stop any running server and remove the existing database before initializing it with `db_init.sql`. The SQL file initializes the required tables without creating registered users.

When the Python server starts, it may add its built-in demo users (`alice` and `bob`) if the `users` table is empty.

## Run from source

Open PowerShell in the project folder and install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

Start the local server, routers, and two client windows:

```powershell
python setup_infra.py
```

Before logging in, create actual users through the messenger application's registration screen. Existing credentials in the database is for purely demo usage and cannot be used.

The setup script prints the server and router addresses, then opens two messenger client windows. Use `Ctrl+C` in PowerShell to stop the infrastructure and client processes.

## Run a client manually

To start a client directly from source:

```powershell
python application.py --client
```
