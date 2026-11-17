"""Server-side accounts, managed content, settings history and audit records."""

import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from . import storage


DEFAULT_SETTINGS = {
    "whole_threshold": 0.50,
    "fused_threshold": 0.50,
    "fused_photo_threshold": 0.75,
    "daf_signal_threshold": 0.40,
    "daf_box_threshold": 0.50,
    "whole_weight": 30,
    "fused_weight": 45,
    "daf_weight": 25,
    "retention_days": 0,
}
COOKIE = "truthlens_session"
SESSION_SECONDS = 7 * 86400
PASSWORD_ROUNDS = 600_000


@contextmanager
def connection(*, write=False):
    db = sqlite3.connect(storage.ROOT / "administration.sqlite3", timeout=10)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        with db:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
    finally:
        db.close()


def initialize():
    with connection(write=True) as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL,
                login_key TEXT NOT NULL UNIQUE, password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','admin')),
                active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                digest TEXT PRIMARY KEY, account_id INTEGER NOT NULL REFERENCES accounts(id), expires INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS audit (
                id INTEGER PRIMARY KEY, account_id INTEGER, actor TEXT NOT NULL,
                operation TEXT NOT NULL, target TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                id INTEGER PRIMARY KEY, body TEXT NOT NULL, actor TEXT NOT NULL, created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS catalog (
                kind TEXT NOT NULL, item_id TEXT NOT NULL, body TEXT NOT NULL,
                status TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(kind,item_id)
            );
        """)
        db.execute("INSERT OR IGNORE INTO settings VALUES(1,?,?,?)",
                   (json.dumps(DEFAULT_SETTINGS), "系统", now()))


def now():
    return datetime.now(timezone.utc).isoformat()


def setup_token_path():
    return storage.ROOT / "admin-setup.txt"


def admin_exists(db):
    return bool(db.execute("SELECT 1 FROM accounts WHERE role='admin' AND active=1 LIMIT 1").fetchone())


def ensure_setup_token():
    with connection(write=True) as db:
        if admin_exists(db):
            return
        try:
            fd = os.open(setup_token_path(), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            return
        with os.fdopen(fd, "w", encoding="ascii") as stream:
            stream.write(secrets.token_urlsafe(30) + "\n")


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PASSWORD_ROUNDS)
    return salt + ":" + digest.hex()


def token_digest(token):
    return hashlib.sha256(token.encode()).hexdigest()


def account_view(account):
    return {**{key: account[key] for key in ("id", "username", "role", "created_at")},
            "active": bool(account["active"])}


def add_audit(db, account, operation, target=""):
    db.execute(
        "INSERT INTO audit(account_id,actor,operation,target,created_at) VALUES(?,?,?,?,?)",
        (account["id"] if account else None, account["username"] if account else "系统", operation, target, now()),
    )


def audit(account, operation, target=""):
    with connection(write=True) as db:
        add_audit(db, account, operation, target)


def session_account(token):
    if not token:
        return None
    with connection() as db:
        row = db.execute(
            "SELECT a.* FROM sessions s JOIN accounts a ON s.account_id=a.id "
            "WHERE s.digest=? AND s.expires>? AND a.active=1",
            (token_digest(token), int(time.time())),
        ).fetchone()
    return account_view(row) if row else None


def issue_session(db, account_id, previous_token):
    token = secrets.token_urlsafe(32)
    current = int(time.time())
    db.execute("DELETE FROM sessions WHERE expires<=? OR digest=?", (current, token_digest(previous_token)))
    db.execute("INSERT INTO sessions VALUES(?,?,?)", (token_digest(token), account_id, current + SESSION_SECONDS))
    return token


def settings_row(row):
    return {"version": row["id"], "values": {**DEFAULT_SETTINGS, **json.loads(row["body"])},
            "actor": row["actor"], "created_at": row["created_at"]}


def active_settings():
    if not (storage.ROOT / "administration.sqlite3").exists():
        return {"version": 1, "values": DEFAULT_SETTINGS.copy(), "actor": "系统", "created_at": None}
    with connection() as db:
        return settings_row(db.execute("SELECT * FROM settings ORDER BY id DESC LIMIT 1").fetchone())


def catalog_entries(kind, defaults, *, published_only=False):
    entries = {item["id"]: {**item, "status": "published", "updated_at": None} for item in defaults}
    rows = []
    if (storage.ROOT / "administration.sqlite3").exists():
        with connection() as db:
            rows = db.execute("SELECT * FROM catalog WHERE kind=? ORDER BY updated_at DESC", (kind,)).fetchall()
    entries.update({row["item_id"]: {**json.loads(row["body"]), "id": row["item_id"],
                                    "status": row["status"], "updated_at": row["updated_at"]} for row in rows})
    return [item for item in entries.values() if not published_only or item["status"] == "published"]
