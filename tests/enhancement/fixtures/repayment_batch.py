"""Disposable SQLite worker for chunk commit and process-restart checks."""

import argparse
from contextlib import closing
import os
import sqlite3


def setup(path, size):
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript('''
            CREATE TABLE staging (
                event INTEGER PRIMARY KEY,
                amount INTEGER NOT NULL CHECK(amount > 0),
                applied INTEGER NOT NULL DEFAULT 0 CHECK(applied IN (0, 1))
            );
            CREATE INDEX pending ON staging(event) WHERE applied = 0;
            CREATE TABLE postings (
                event INTEGER NOT NULL REFERENCES staging(event),
                account TEXT NOT NULL,
                amount INTEGER NOT NULL,
                PRIMARY KEY(event, account)
            );
        ''')
        db.executemany('INSERT INTO staging(event, amount) VALUES (?, ?)',
                       ((event, event % 97 + 1) for event in range(1, size + 1)))


def process_chunk(db, size, crash):
    with db:
        db.execute('BEGIN IMMEDIATE')
        batch = db.execute('SELECT event, amount FROM staging WHERE applied = 0 ORDER BY event LIMIT ?',
                           (size,)).fetchall()
        for event, amount in batch:
            db.execute('INSERT INTO postings VALUES (?, ?, ?)', (event, 'receivable', -amount))
            if crash == 'between-postings':
                os._exit(91)
            db.execute('INSERT INTO postings VALUES (?, ?, ?)', (event, 'cash', amount))
            db.execute('UPDATE staging SET applied = 1 WHERE event = ?', (event,))
    if batch and crash == 'after-commit':
        os._exit(92)
    return bool(batch)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database')
    parser.add_argument('--chunk-size', required=True, type=int)
    parser.add_argument('--crash', choices=('between-postings', 'after-commit'))
    args = parser.parse_args()
    if args.chunk_size < 1:
        parser.error('chunk size must be positive')
    with closing(sqlite3.connect(args.database, timeout=3)) as db:
        db.execute('PRAGMA foreign_keys = ON')
        while process_chunk(db, args.chunk_size, args.crash):
            pass


if __name__ == '__main__':
    main()
