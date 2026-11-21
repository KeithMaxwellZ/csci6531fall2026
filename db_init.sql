-- Initialize the Encrypted Messenger SQLite database.
-- Run against a new or existing database; CREATE TABLE IF NOT EXISTS leaves existing tables intact.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT NOT NULL,
    email TEXT NOT NULL,
    is_admin INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL,
    exchange_public_key TEXT NOT NULL DEFAULT '',
    identity_public_key TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL NOT NULL,
    username TEXT,
    event TEXT NOT NULL,
    success INTEGER NOT NULL,
    details TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contacts (
    username TEXT NOT NULL,
    contact TEXT NOT NULL,
    created_at REAL NOT NULL,
    PRIMARY KEY (username, contact)
);
