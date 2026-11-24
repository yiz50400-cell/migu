"""Ledger tests use a temporary SQLite file and never submit paid generation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/migu/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


ledger = load('ledger')


class LedgerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.conn = ledger.open_ledger(Path(self.tmp.name) / 'ledger.sqlite')
        self.addCleanup(self.conn.close)
        ledger.set_budget(self.conn, 'acct', 10)

    def reserve(self, key='k1', amount=3, payload=None, **extra):
        payload = payload or {'shot': 's1', 'seconds': 4}
        return ledger.reserve(
            self.conn,
            idempotency_key=key,
            account_id='acct',
            channel_id='api-main',
            request_hash=ledger.request_hash(payload),
            kind='video',
            amount=amount,
            requested_duration=4,
            **extra,
        )

    def test_reserve_and_available(self):
        row = self.reserve()
        self.assertEqual(row['status'], 'reserved')
        self.assertEqual(ledger.budget_state(self.conn, 'acct')['available'], 7)

    def test_idempotent_reserve_same_request(self):
        first = self.reserve()
        again = self.reserve()
        self.assertEqual(first['created_at'], again['created_at'])
        self.assertEqual(ledger.budget_state(self.conn, 'acct')['reserved'], 3)

    def test_duplicate_key_different_request(self):
        self.reserve(payload={'shot': 's1'})
        with self.assertRaises(ledger.DuplicateSubmission):
            self.reserve(payload={'shot': 's2'})

    def test_insufficient_budget(self):
        with self.assertRaises(ledger.InsufficientBudget):
            self.reserve(amount=11)

    def test_success_moves_reserve_to_spent(self):
        self.reserve()
        ledger.mark_submitted(self.conn, 'k1', 'task-1')
        ledger.confirm_success(self.conn, 'k1', actual_amount=2.5)
        state = ledger.budget_state(self.conn, 'acct')
        self.assertEqual(state['reserved'], 0)
        self.assertEqual(state['spent'], 2.5)
        self.assertEqual(state['available'], 7.5)

    def test_failure_releases_reservation(self):
        self.reserve()
        ledger.confirm_failure(self.conn, 'k1')
        state = ledger.budget_state(self.conn, 'acct')
        self.assertEqual(state['reserved'], 0)
        self.assertEqual(state['spent'], 0)
        self.assertEqual(state['available'], 10)

    def test_unknown_acceptance_blocks_resubmit(self):
        payload = {'shot': 's1'}
        self.reserve(payload=payload)
        ledger.mark_submitted(self.conn, 'k1', 'task-maybe')
        ledger.mark_unknown(self.conn, 'k1')
        digest = ledger.request_hash(payload)
        with self.assertRaises(ledger.UnknownAcceptance):
            ledger.assert_can_submit(self.conn, 'k1', digest)
        with self.assertRaises(ledger.UnknownAcceptance):
            self.reserve(payload=payload)
        # After confirmed failure, a new key can be reserved.
        ledger.confirm_failure(self.conn, 'k1')
        row = self.reserve(key='k2', payload=payload)
        self.assertEqual(row['status'], 'reserved')

    def test_succeeded_submit_is_not_repeated(self):
        payload = {'shot': 's1'}
        self.reserve(payload=payload)
        ledger.confirm_success(self.conn, 'k1')
        with self.assertRaises(ledger.DuplicateSubmission):
            ledger.assert_can_submit(self.conn, 'k1', ledger.request_hash(payload))

    def test_no_secrets_in_schema_or_rows(self):
        self.reserve()
        names = {row[1] for row in self.conn.execute('PRAGMA table_info(submissions)')}
        names |= {row[1] for row in self.conn.execute('PRAGMA table_info(budget)')}
        for forbidden in ('cookie', 'secret', 'token', 'password', 'credential'):
            self.assertTrue(all(forbidden not in name.lower() for name in names))
        blob = ' '.join(str(v) for row in self.conn.execute('SELECT * FROM submissions') for v in row)
        self.assertNotIn('sk-', blob)


if __name__ == '__main__':
    unittest.main()
