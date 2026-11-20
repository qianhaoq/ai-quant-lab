"""Local development reservations, not execution reconciliation or investment authority.

Atomic approval consumption and cumulative reservations require one persistent
SQLite file shared by all workers. Changing its path/deleting it resets quotas;
separate ledgers are unsupported. Token reservations are not dollar bill caps.
Order notional excludes fees and external orders, and is not a live fill cap.
"""
import hashlib
import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path

from fastapi import Header, HTTPException

from app.config import get_settings


def principal(authorization: str | None = Header(default=None), x_account_id: str | None = Header(default=None)) -> str:
    settings = get_settings()
    token = authorization.removeprefix('Bearer ') if authorization and authorization.startswith('Bearer ') else ''
    subject = next((subject for key, subject in settings.api_tokens.items() if token and secrets.compare_digest(key.encode(), token.encode())), None)
    if not subject:
        raise HTTPException(401, 'Bearer authentication required')
    # There is exactly one configured broker account; no caller-controlled account routing.
    if subject != settings.broker_owner_subject or (x_account_id and x_account_id != settings.broker_account_id):
        raise HTTPException(403, 'Account not authorized')
    return subject


@contextmanager
def database(settings):
    Path(settings.safety_db_path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(settings.safety_db_path, timeout=10)
    try:
        db.execute('CREATE TABLE IF NOT EXISTS approvals (token TEXT PRIMARY KEY, subject TEXT, payload TEXT, expires REAL)')
        db.execute('CREATE TABLE IF NOT EXISTS usage (scope TEXT PRIMARY KEY, orders INTEGER DEFAULT 0, notional REAL DEFAULT 0, calls INTEGER DEFAULT 0, tokens INTEGER DEFAULT 0)')
        db.execute('CREATE TABLE IF NOT EXISTS leases (id TEXT PRIMARY KEY, expires REAL)')
        db.commit()
        db.execute('BEGIN IMMEDIATE')
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise
    finally:
        db.close()


def fingerprint(intent, settings):
    return json.dumps([intent.model_dump(exclude={'confirmation_phrase', 'approval_token'}), settings.broker_provider, settings.broker_mode, settings.broker_account_id], sort_keys=True)


def issue_approval(intent, settings, subject):
    token = secrets.token_urlsafe(32)
    with database(settings) as db:
        db.execute('DELETE FROM approvals WHERE expires < ?', (time.time(),))
        # Keep only the latest preview for a subject; bounds storage and invalidates stale previews.
        db.execute('DELETE FROM approvals WHERE subject = ?', (subject,))
        db.execute('INSERT INTO approvals VALUES (?, ?, ?, ?)', (hashlib.sha256(token.encode()).hexdigest(), subject, fingerprint(intent, settings), time.time() + 300))
    return token


def reserve_order(intent, settings, subject, notional):
    with database(settings) as db:
        digest = hashlib.sha256((intent.approval_token or '').encode()).hexdigest()
        row = db.execute('SELECT subject, payload, expires FROM approvals WHERE token=?', (digest,)).fetchone()
        if not row or (row[0] != subject or row[1] != fingerprint(intent, settings)) or row[2] < time.time():
            raise HTTPException(400, 'Invalid, expired or replayed approval')
        scope = 'account:' + settings.broker_account_id
        db.execute('INSERT OR IGNORE INTO usage(scope) VALUES (?)', (scope,))
        orders, total = db.execute('SELECT orders, notional FROM usage WHERE scope=?', (scope,)).fetchone()
        if orders >= settings.safety_max_orders or total + notional > settings.safety_max_notional:
            raise HTTPException(429, 'Development cumulative trading safety limit reached')
        db.execute('DELETE FROM approvals WHERE token=?', (digest,))
        db.execute('UPDATE usage SET orders=orders+1, notional=notional+? WHERE scope=?', (notional, scope))
        # Failed/ambiguous broker calls consume reservation too; never automatically retry orders.


def reserve_research(settings):
    lease = secrets.token_hex(16)
    # Conservative input bytes + output cap, reserved even on provider failure. Global across subjects.
    budget = 16000 + settings.safety_model_output_tokens
    with database(settings) as db:
        db.execute('DELETE FROM leases WHERE expires < ?', (time.time(),))
        db.execute("INSERT OR IGNORE INTO usage(scope) VALUES ('model')")
        calls, tokens = db.execute("SELECT calls, tokens FROM usage WHERE scope='model'").fetchone()
        active = db.execute('SELECT count(*) FROM leases').fetchone()[0]
        if calls >= settings.safety_model_calls or tokens + budget > settings.safety_model_total_tokens or active >= settings.safety_model_concurrency:
            raise HTTPException(429, 'Development model call/token/concurrency safety limit reached')
        db.execute("UPDATE usage SET calls=calls+1, tokens=tokens+? WHERE scope='model'", (budget,))
        db.execute('INSERT INTO leases VALUES (?, ?)', (lease, time.time() + 120))
    return lease


def release_research(settings, lease):
    with database(settings) as db:
        db.execute('DELETE FROM leases WHERE id=?', (lease,))
