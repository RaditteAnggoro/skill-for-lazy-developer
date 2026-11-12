"""Intentionally unsafe synthetic repayment for isolated benchmark use only."""
import sqlite3


def setup(path):
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE IF NOT EXISTS postings (event TEXT, account TEXT, amount INTEGER)')


def post(path, event, amount):
    if not event or not isinstance(amount, int) or amount <= 0:
        raise ValueError('event and positive integer amount required')
    with sqlite3.connect(path) as db:
        db.executemany('INSERT INTO postings VALUES (?, ?, ?)', [
            (event, 'receivable', -amount), (event, 'cash', amount),
        ])


def postings(path):
    with sqlite3.connect(path) as db:
        return db.execute('SELECT event, account, amount FROM postings ORDER BY rowid').fetchall()
