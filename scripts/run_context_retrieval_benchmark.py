"""Measure native retrieval, source expansion, and index cost on disposable fixtures."""

import argparse
import json
from pathlib import Path
import sqlite3
import statistics
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.context_intelligence import ContextIndex, EvidenceUnavailable  # noqa: E402


FIXTURES = {
    'ReleaseService.java': ('SettlementCoordinator', 'transactionManager.rollback(status);'),
    'jobrepository.xml': ('batchRestartRepository', '<property name="isolationLevelForCreate" value="ISOLATION_SERIALIZABLE"/>'),
    'posting.sql': ('loanPostingClaim', 'FOR UPDATE SKIP LOCKED;'),
    'Dashboard.tsx': ('BalanceDisclosure', 'aria-expanded={detailsOpen}'),
    'session.md': ('invoiceReconcileContext', 'Keep the original invoice row when retrying.'),
    'replay.py': ('restart_safe_replay', 'assert prior_request_id == request_id'),
}


def median(samples):
    return round(statistics.median(samples), 4)


def elapsed_ms(start):
    return (time.perf_counter() - start) * 1000


def write_fixture(root):
    for name, (symbol, guard) in FIXTURES.items():
        prefix = f'def {symbol}():\n' if name.endswith('.py') else f'{symbol}\n'
        indent = '    ' if name.endswith('.py') else ''
        body = ''.join(f'{indent}# step {line}\n' for line in range(33))
        (root / name).write_text(prefix + body + indent + guard + '\n', encoding='utf-8')
    for number in range(60):
        (root / f'worker-{number:02d}.md').write_text(
            ''.join(f'worker cycle {cycle} owns a task receipt\n' for cycle in range(75)), encoding='utf-8')
    return sorted(path.name for path in root.iterdir())


def trial(profile):
    with tempfile.TemporaryDirectory(prefix='ld-context-retrieval-') as tmp:
        root = Path(tmp)
        paths = write_fixture(root)
        db = root / 'index.sqlite' if profile == 'balanced' else ':memory:'
        started = time.perf_counter()
        with ContextIndex(root, db, use_fts=profile != 'lexical-control') as index:
            report = index.refresh(paths)
            build = elapsed_ms(started)
            hits, guard_hits, lookups = 0, 0, []
            for _ in range(7):
                for name, (query, guard) in FIXTURES.items():
                    start = time.perf_counter()
                    found = index.search(query, limit=1)
                    if found and found[0].file == name:
                        hits += 1
                        if guard not in index.hydrate(found[0]) and guard in index.hydrate(found[0], full=True):
                            guard_hits += 1
                    lookups.append(elapsed_ms(start))
            path = root / 'replay.py'
            anchor = index.search('restart_safe_replay', limit=1)[0]
            path.write_text(path.read_text(encoding='utf-8').replace('prior_request_id', 'committed_request_id'),
                            encoding='utf-8')
            stale_rejected = False
            try:
                index.hydrate(anchor, full=True)
            except EvidenceUnavailable:
                stale_rejected = True
            started = time.perf_counter()
            delta = index.refresh(paths)
            update = elapsed_ms(started)
            recovered = 'committed_request_id' in index.hydrate(index.search('restart_safe_replay', 1)[0], full=True)
            engine = 'fts5' if index.use_fts else 'lexical'
        reopen = None
        if profile == 'balanced':
            started = time.perf_counter()
            with ContextIndex(root, db) as index:
                recovered = recovered and bool(index.search('restart_safe_replay', 1))
            reopen = elapsed_ms(started)
        return {'engine': engine, 'documents': len(report['indexed']), 'queries': len(lookups),
                'hits': hits, 'guard_hits': guard_hits, 'stale_rejected': stale_rejected, 'recovered': recovered,
                'incremental_files': delta['indexed'], 'build_ms': build, 'lookup_ms': median(lookups),
                'update_ms': update, 'reopen_ms': reopen, 'cache_bytes': db.stat().st_size if profile == 'balanced' else 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trials', type=int, default=9)
    args = parser.parse_args()
    if not 3 <= args.trials <= 30:
        parser.error('choose 3 to 30 trials')
    profiles, passed = {}, True
    for profile in ('lexical-control', 'light', 'balanced'):
        results = [trial(profile) for _ in range(args.trials)]
        profiles[profile] = {
            'engine': results[0]['engine'], 'documents': results[0]['documents'],
            'top1_hits_and_queries': [sum(row[key] for row in results) for key in ('hits', 'queries')],
            'guard_expansions': sum(row['guard_hits'] for row in results),
            'stale_rejections': sum(row['stale_rejected'] for row in results),
            'recoveries': sum(row['recovered'] for row in results),
            'single_file_updates': sum(row['incremental_files'] == ['replay.py'] for row in results),
            **{key: median(row[key] for row in results) for key in ('build_ms', 'lookup_ms', 'update_ms', 'cache_bytes')},
        }
        if profile == 'balanced':
            profiles[profile]['reopen_ms'] = median(row['reopen_ms'] for row in results)
        passed &= all(row['hits'] == row['guard_hits'] == row['queries'] and row['stale_rejected'] and
                      row['recovered'] and row['incremental_files'] == ['replay.py'] for row in results)
    print(json.dumps({'sqlite': sqlite3.sqlite_version, 'trials': args.trials, 'pass': passed,
                      'profiles': profiles}, indent=2))
    return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
