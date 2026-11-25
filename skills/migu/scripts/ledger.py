#!/usr/bin/env python3
"""SQLite production ledger: budget reservation, duplicate-submit protection, idempotency.

Never stores secrets, cookies, or login state. Never submits paid generation.
Unknown remote acceptance is recorded as submission_unknown and must not be retried
with a new submit until the prior attempt is confirmed failed or recovered.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ACTIVE_RESERVE = ('reserved', 'submitted', 'submission_unknown')


class LedgerError(ValueError):
    pass


class InsufficientBudget(LedgerError):
    pass


class DuplicateSubmission(LedgerError):
    pass


class UnknownAcceptance(LedgerError):
    """A prior submit may already have been accepted; do not submit again."""


def _now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _finite(value):
    try:
        return value == value and abs(value) != float('inf')
    except TypeError:
        return False


def request_hash(payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()


def open_ledger(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=5000')
    conn.executescript(
        "CREATE TABLE IF NOT EXISTS budget ("
        " account_id TEXT PRIMARY KEY,"
        " currency TEXT NOT NULL DEFAULT 'credits',"
        " authorized REAL NOT NULL,"
        " reserved REAL NOT NULL DEFAULT 0,"
        " spent REAL NOT NULL DEFAULT 0,"
        " updated_at TEXT NOT NULL);"
        "CREATE TABLE IF NOT EXISTS submissions ("
        " idempotency_key TEXT PRIMARY KEY,"
        " account_id TEXT NOT NULL,"
        " channel_id TEXT NOT NULL,"
        " request_hash TEXT NOT NULL,"
        " kind TEXT NOT NULL,"
        " requested_duration REAL,"
        " reserved_amount REAL NOT NULL,"
        " actual_amount REAL,"
        " status TEXT NOT NULL,"
        " provider_task_id TEXT,"
        " created_at TEXT NOT NULL,"
        " updated_at TEXT NOT NULL);"
    )
    conn.commit()
    return conn


def set_budget(conn, account_id, authorized, currency='credits'):
    if not account_id or not isinstance(account_id, str):
        raise LedgerError('account_id is required')
    if authorized < 0 or not _finite(authorized):
        raise LedgerError('authorized budget must be a finite non-negative number')
    now = _now()
    row = conn.execute('SELECT reserved, spent FROM budget WHERE account_id=?', (account_id,)).fetchone()
    if row is None:
        conn.execute(
            'INSERT INTO budget(account_id, currency, authorized, reserved, spent, updated_at) VALUES (?,?,?,0,0,?)',
            (account_id, currency, float(authorized), now),
        )
    else:
        if row['reserved'] + row['spent'] > authorized + 1e-9:
            raise LedgerError('authorized budget is below already reserved and spent amounts')
        conn.execute(
            'UPDATE budget SET currency=?, authorized=?, updated_at=? WHERE account_id=?',
            (currency, float(authorized), now, account_id),
        )
    conn.commit()
    return budget_state(conn, account_id)


def budget_state(conn, account_id):
    row = conn.execute('SELECT * FROM budget WHERE account_id=?', (account_id,)).fetchone()
    if row is None:
        raise LedgerError('unknown budget account: ' + account_id)
    data = dict(row)
    data['available'] = data['authorized'] - data['reserved'] - data['spent']
    return data


def get_submission(conn, idempotency_key):
    row = conn.execute('SELECT * FROM submissions WHERE idempotency_key=?', (idempotency_key,)).fetchone()
    return dict(row) if row else None


def _existing_decision(existing, request_hash):
    """Reuse or reject an existing row for the same idempotency key."""
    if existing['request_hash'] != request_hash:
        raise DuplicateSubmission('idempotency key reused with a different request')
    if existing['status'] == 'submission_unknown':
        raise UnknownAcceptance('prior submit is submission_unknown; recover before a new submit')
    if existing['status'] in ('reserved', 'submitted', 'succeeded'):
        return existing
    raise DuplicateSubmission(
        'key already closed as %s; use a new idempotency key to retry' % existing['status']
    )


def _begin_immediate(conn):
    if conn.in_transaction:
        conn.commit()
    conn.execute('BEGIN IMMEDIATE')


def reserve(conn, *, idempotency_key, account_id, channel_id, request_hash, kind, amount,
            requested_duration=None):
    if not idempotency_key or not isinstance(idempotency_key, str):
        raise LedgerError('idempotency_key is required')
    if not channel_id or kind not in ('image', 'video'):
        raise LedgerError('channel_id and kind (image|video) are required')
    if amount < 0 or not _finite(amount):
        raise LedgerError('reserve amount must be a finite non-negative number')
    if requested_duration is not None and (requested_duration < 0 or not _finite(requested_duration)):
        raise LedgerError('requested_duration must be a finite non-negative number')

    def decide_existing(existing):
        return _existing_decision(existing, request_hash)

    _begin_immediate(conn)
    try:
        existing = get_submission(conn, idempotency_key)
        if existing:
            row = decide_existing(existing)
            conn.commit()
            return row

        state = budget_state(conn, account_id)
        if amount > state['available'] + 1e-9:
            raise InsufficientBudget(
                'insufficient budget: need %.4f, available %.4f' % (amount, state['available'])
            )
        now = _now()
        conn.execute(
            'INSERT INTO submissions('
            'idempotency_key, account_id, channel_id, request_hash, kind, requested_duration,'
            'reserved_amount, actual_amount, status, provider_task_id, created_at, updated_at)'
            ' VALUES (?,?,?,?,?,?,?,?,?,?,?,?)',
            (idempotency_key, account_id, channel_id, request_hash, kind,
             requested_duration, float(amount), None, 'reserved', None, now, now),
        )
        conn.execute(
            'UPDATE budget SET reserved=reserved+?, updated_at=? WHERE account_id=?',
            (float(amount), now, account_id),
        )
        conn.commit()
        return get_submission(conn, idempotency_key)
    except sqlite3.IntegrityError:
        conn.rollback()
        existing = get_submission(conn, idempotency_key)
        if existing is None:
            raise DuplicateSubmission('idempotency key collided; existing row could not be recovered')
        return decide_existing(existing)
    except Exception:
        conn.rollback()
        raise


def mark_submitted(conn, idempotency_key, provider_task_id=None):
    row = _require(conn, idempotency_key)
    if row['status'] == 'submission_unknown':
        raise UnknownAcceptance('recover the unknown submission before marking submitted again')
    if row['status'] not in ('reserved', 'submitted'):
        raise LedgerError('cannot mark submitted from status ' + row['status'])
    _update(conn, idempotency_key, status='submitted',
            provider_task_id=provider_task_id or row['provider_task_id'])
    return get_submission(conn, idempotency_key)


def mark_unknown(conn, idempotency_key):
    """Record that it is unknown whether the provider accepted the request."""
    row = _require(conn, idempotency_key)
    if row['status'] in ('succeeded', 'failed', 'released'):
        raise LedgerError('cannot mark a closed submission as unknown')
    _update(conn, idempotency_key, status='submission_unknown')
    return get_submission(conn, idempotency_key)


def confirm_success(conn, idempotency_key, actual_amount=None, provider_task_id=None):
    row = _require(conn, idempotency_key)
    if row['status'] == 'succeeded':
        return row
    if row['status'] not in ('reserved', 'submitted', 'submission_unknown'):
        raise LedgerError('cannot confirm success from status ' + row['status'])
    charged = row['reserved_amount'] if actual_amount is None else float(actual_amount)
    if charged < 0 or not _finite(charged):
        raise LedgerError('actual_amount must be a finite non-negative number')
    state = budget_state(conn, row['account_id'])
    # Releasing this reservation returns reserved_amount to the pool; spent then rises by charged.
    # available would go negative if charged exceeds reserved_amount plus current available.
    room = row['reserved_amount'] + state['available']
    if charged > room + 1e-9:
        raise InsufficientBudget(
            'actual amount %.4f exceeds authorized budget (room %.4f); increase authorized budget before confirming'
            % (charged, room)
        )
    now = _now()
    conn.execute(
        'UPDATE submissions SET status=?, actual_amount=?, provider_task_id=?, updated_at=? WHERE idempotency_key=?',
        ('succeeded', charged, provider_task_id or row['provider_task_id'], now, idempotency_key),
    )
    conn.execute(
        'UPDATE budget SET reserved=reserved-?, spent=spent+?, updated_at=? WHERE account_id=?',
        (row['reserved_amount'], charged, now, row['account_id']),
    )
    conn.commit()
    return get_submission(conn, idempotency_key)


def confirm_failure(conn, idempotency_key, provider_task_id=None):
    row = _require(conn, idempotency_key)
    if row['status'] == 'failed':
        return row
    if row['status'] not in ('reserved', 'submitted', 'submission_unknown'):
        raise LedgerError('cannot confirm failure from status ' + row['status'])
    now = _now()
    conn.execute(
        'UPDATE submissions SET status=?, provider_task_id=?, updated_at=? WHERE idempotency_key=?',
        ('failed', provider_task_id or row['provider_task_id'], now, idempotency_key),
    )
    if row['status'] in ACTIVE_RESERVE:
        conn.execute(
            'UPDATE budget SET reserved=reserved-?, updated_at=? WHERE account_id=?',
            (row['reserved_amount'], now, row['account_id']),
        )
    conn.commit()
    return get_submission(conn, idempotency_key)


def release(conn, idempotency_key):
    """Drop an unused reservation that was never sent to the provider."""
    row = _require(conn, idempotency_key)
    if row['status'] == 'released':
        return row
    if row['status'] == 'submission_unknown':
        raise UnknownAcceptance(
            'submission_unknown cannot be released; confirm_success or confirm_failure after recovery'
        )
    if row['status'] != 'reserved':
        raise LedgerError('only reserved submissions that were never sent can be released')
    now = _now()
    conn.execute(
        'UPDATE submissions SET status=?, updated_at=? WHERE idempotency_key=?',
        ('released', now, idempotency_key),
    )
    conn.execute(
        'UPDATE budget SET reserved=reserved-?, updated_at=? WHERE account_id=?',
        (row['reserved_amount'], now, row['account_id']),
    )
    conn.commit()
    return get_submission(conn, idempotency_key)


def assert_can_submit(conn, idempotency_key, request_hash):
    """Allow the first provider submit only after a live reservation.

    No row, or a failed/released row, cannot be submitted (reserve first; retry with a new key).
    reserved allows the first submit. submitted, succeeded, and submission_unknown are forbidden.
    """
    existing = get_submission(conn, idempotency_key)
    if existing is None:
        raise LedgerError('no reservation for this key; reserve budget before submitting')
    if existing['request_hash'] != request_hash:
        raise DuplicateSubmission('idempotency key reused with a different request')
    if existing['status'] == 'reserved':
        return existing
    if existing['status'] == 'submission_unknown':
        raise UnknownAcceptance('prior submit is submission_unknown; query the provider instead of resubmitting')
    if existing['status'] in ('submitted', 'succeeded'):
        raise DuplicateSubmission('submission already %s; do not submit again' % existing['status'])
    raise DuplicateSubmission(
        'key already closed as %s; use a new idempotency key, then reserve, before retrying' % existing['status']
    )


def _require(conn, key):
    row = get_submission(conn, key)
    if row is None:
        raise LedgerError('unknown idempotency key')
    return row


def _update(conn, key, **fields):
    fields = {k: v for k, v in fields.items() if v is not None}
    fields['updated_at'] = _now()
    assignments = ', '.join(k + '=?' for k in fields)
    conn.execute(
        'UPDATE submissions SET ' + assignments + ' WHERE idempotency_key=?',
        list(fields.values()) + [key],
    )
    conn.commit()
