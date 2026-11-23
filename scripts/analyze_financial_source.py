"""Produce source-anchored Java and SQL review findings from explicit local files."""

import json
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote, urlsplit


JAVA = Path(__file__).with_name('FinancialJavaScan.java')
RULES = {
    'JAVA_PROXY_VISIBILITY': ('LIKELY_RISK', 'Method visibility or modifiers can prevent proxy interception.', 'Identify proxy type and exercise an external proxied call with rollback.'),
    'JAVA_SELF_INVOCATION': ('LIKELY_RISK', 'A same-instance call targets a transaction-annotated sibling.', 'Trace the caller through the actual proxy and assert the transaction state.'),
    'JAVA_CHECKED_ROLLBACK': ('NEEDS_RUNTIME_EVIDENCE', 'A declared checked exception lacks a local rollbackFor rule.', 'Inspect global and class defaults, then assert database state after this exception.'),
    'JAVA_REQUIRES_NEW': ('NEEDS_RUNTIME_EVIDENCE', 'An independent transaction can survive an outer rollback.', 'Inject failure after the inner commit and reconcile the durable effects.'),
    'JAVA_SPLIT_WRITES': ('NEEDS_RUNTIME_EVIDENCE', 'Several writes occur with no method or class transaction annotation.', 'Trace the actual transaction manager and inject failure between writes.'),
    'JAVA_BATCH_POLICY': ('LIKELY_RISK', 'A broad skip/retry class or a noRollback configuration needs classification.', 'Assert a failed posting aborts the chunk and inspect retry bounds and exception policies.'),
    'JAVA_UNBOUNDED_READ': ('NEEDS_RUNTIME_EVIDENCE', 'An unrestricted read occurs in a financial method.', 'Measure result cardinality and peak retained memory using production-shaped synthetic data.'),
    'JAVA_CHECK_INSERT': ('LIKELY_RISK', 'A read-before-write branch can race with a competing writer.', 'Verify database uniqueness and run two simultaneous commits using the same payload key.'),
    'JAVA_SWALLOWED_WRITE': ('LIKELY_RISK', 'A catch block has no direct rethrow in a transactional or financial method.', 'Trace all exception exits and inject a writer failure to check rollback status.'),
    'JAVA_DECIMAL_FLOAT': ('CONFIRMED', 'BigDecimal is constructed from a binary floating-point literal.', 'Use exact decimal input and assert the rounding policy at boundary values.'),
    'JAVA_RESOURCE': ('NEEDS_RUNTIME_EVIDENCE', 'An allocated JDBC resource is outside a recognized resource scope.', 'Trace ownership and close behavior on normal, exception, and retry paths.'),
    'SQL_OFFSET': ('NEEDS_RUNTIME_EVIDENCE', 'Offset navigation can shift across changes to the result set.', 'Exercise restart and concurrent mutations with deterministic ordering and a stable scope.'),
    'SQL_POSTING_UNIQUENESS': ('NEEDS_RUNTIME_EVIDENCE', 'A posting INSERT needs evidence of a database-enforced business identity.', 'Inspect deployed DDL and exercise same-key/same-payload and conflicting replay.'),
    'SQL_CLAIM_FENCE': ('LIKELY_RISK', 'A posting-stage update lacks a visible owner and claim-version match.', 'Expire, reclaim, and then try a stale worker against the same row.'),
    'SQL_LOCK_ORDER': ('LIKELY_RISK', 'Explicit row locks appear in opposite table order.', 'Run concurrent transactions on the actual engine and verify bounded retry and lock ordering.'),
    'SQL_MIGRATION_LOCK': ('NEEDS_RUNTIME_EVIDENCE', 'DDL can block writers or rewrite data, depending on the engine.', 'Measure locks and duration in a disposable database and rehearse cutover and forward recovery.'),
    'SQL_MIGRATION_DESTRUCTIVE': ('CONFIRMED', 'A destructive DDL statement is present in the source.', 'Verify change authorization, backup recovery, and exact affected objects before use.'),
}

# Strings, quoted identifiers, and comments remain opaque to the rule matcher.
TOKEN = re.compile(r"--[^\n]*|/\*[\s\S]*?\*/|(?P<dollar>\$[A-Za-z0-9_]*\$)[\s\S]*?(?P=dollar)|"
                   r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"|[A-Za-z_][A-Za-z0-9_$]*|\d+|[^\s]")


def finding(rule, path, line, method):
    classification, reason, verification = RULES[rule]
    return {'rule': rule, 'file': str(path), 'line': line, 'method': method,
            'classification': classification, 'reason': reason, 'verification': verification}


def statements(source):
    words = []
    start = 1
    previous = 0
    line = 1
    for match in TOKEN.finditer(source):
        line += source.count('\n', previous, match.start())
        previous = match.start()
        value = match.group()
        if value.startswith(('--', '/*')):
            continue
        if value == ';':
            if words:
                yield start, words
            words = []
            continue
        if not words:
            start = line
        words.append('?' if value.startswith(("'", '"', '$')) else value.upper())
    if words:
        yield start, words


def sql_findings(path):
    locks = []
    orders = set()
    parsed = list(statements(path.read_text(encoding='utf-8')))
    unique_events = {words[2] for _, words in parsed if words[:2] == ['CREATE', 'TABLE'] and len(words) > 4
                    and any(sequence in ' '.join(words) for sequence in ('PRIMARY KEY ( EVENT_KEY )', 'UNIQUE ( EVENT_KEY )'))}
    for line, words in parsed:
        method = f'statement:{line}'
        if words[0] == 'SELECT' and 'OFFSET' in words:
            yield finding('SQL_OFFSET', path, line, method)
        if (words[:2] == ['INSERT', 'INTO'] and len(words) > 2 and words[2] not in unique_events
                and any(part in words[2] for part in ('JOURNAL', 'POSTING'))):
            yield finding('SQL_POSTING_UNIQUENESS', path, line, method)
        if words[:2] == ['UPDATE', 'FINANCIAL_STAGE'] and 'SET' in words:
            split = words.index('WHERE') if 'WHERE' in words else len(words)
            assignments, where = words[2:split], words[split + 1:]
            # Values are opaque. Flag state transitions that clear ownership and finish a claim.
            if 'STATE' in assignments and 'OWNER_ID' in assignments and 'NULL' in assignments:
                for required in ('OWNER_ID', 'CLAIM_VERSION'):
                    if not any(where[i:i + 2] == [required, '='] for i in range(len(where))):
                        yield finding('SQL_CLAIM_FENCE', path, line, method)
                        break
        if words[0] in {'COMMIT', 'ROLLBACK'}:
            locks.clear()
        if words[0] == 'SELECT' and 'FROM' in words and 'FOR UPDATE' in ' '.join(words):
            index = words.index('FROM') + 1
            if index < len(words):
                table = words[index]
                for first in locks:
                    if (table, first) in orders:
                        yield finding('SQL_LOCK_ORDER', path, line, method)
                        break
                orders.update((first, table) for first in locks if first != table)
                locks.append(table)
        if words[0] == 'TRUNCATE' or words[:2] in (['DROP', 'TABLE'], ['DROP', 'SCHEMA']):
            yield finding('SQL_MIGRATION_DESTRUCTIVE', path, line, method)
        if words[:2] == ['ALTER', 'TABLE'] or ('INDEX' in words[:3] and words[0] == 'CREATE' and 'CONCURRENTLY' not in words):
            yield finding('SQL_MIGRATION_LOCK', path, line, method)


def analyze(paths, java='java', reviewed=None):
    paths = [Path(path).resolve(strict=True) for path in paths]
    if not 1 <= len(paths) <= 48 or len(set(paths)) != len(paths):
        raise ValueError('provide one to 48 distinct source files')
    for path in paths:
        if not path.is_file() or path.suffix not in {'.java', '.sql'} or path.stat().st_size > 256 * 1024:
            raise ValueError('sources must be Java or SQL regular files of at most 256 KiB')
    results = [item for path in paths if path.suffix == '.sql' for item in sql_findings(path)]
    java_paths = [str(path) for path in paths if path.suffix == '.java']
    if java_paths:
        run = subprocess.run([java, '--source', '17', str(JAVA), *java_paths], capture_output=True,
                             text=True, timeout=40, check=False)
        if run.returncode:
            raise ValueError('Java AST scan did not complete; check JDK 17+ and source syntax')
        for line in run.stdout.splitlines():
            rule, uri, number, method = line.split('\t')
            results.append(finding(rule, Path(unquote(urlsplit(uri).path)), int(number), method))
    for item in results:
        item['file'] = str(Path(item['file']).relative_to(Path.cwd())) if Path(item['file']).is_relative_to(Path.cwd()) else Path(item['file']).name
    if reviewed is not None:
        dispositions = json.loads(Path(reviewed).read_text(encoding='utf-8'))
        by_key = {(row['rule'], row['file'], row['line'], row['method']): row for row in results}
        for row in dispositions:
            key = (row['rule'], row['file'], row['line'], row['method'])
            if key not in by_key or not isinstance(row.get('evidence'), str) or not row['evidence'].strip():
                raise ValueError('false-positive disposition needs a matching finding and explicit evidence')
            by_key[key].update(classification='FALSE_POSITIVE', review_evidence=row['evidence'])
    return sorted(results, key=lambda row: (row['file'], row['line'], row['rule']))
