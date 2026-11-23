"""Token-aware context selection with lossless raw-evidence recovery."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import re
import statistics
import tempfile


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "by", "do", "does",
    "for", "from", "how", "in", "is", "it", "of", "on", "or", "that", "the",
    "this", "to", "was", "were", "what", "when", "where", "which", "why",
    "with", "should", "would", "could", "please", "tell",
}
SIGNAL = re.compile(
    r"(?i)\b(error|failed|failure|warning|constraint|approval|approve|security|"
    r"privacy|payment|invoice|ledger|reconcil|idempot|rollback|mismatch|"
    r"blocked|denied|must|never|cannot|required|pii|customer|audit)\b"
)
CONSTRAINT = re.compile(
    r"(?i)\b(must|never|do not|approval|security|privacy|financial|ledger|"
    r"payment|idempot|pii|customer data|audit)\b"
)

FINANCIAL_SCOPE = re.compile(
    r'\b(loan|repayment|payment|refund|financial|ledger|settlement|reconciliation|idempotenc\w*|posting|'
    r'pinjaman|angsuran|pelunasan|pembayaran|keuangan|jurnal|rekonsiliasi|saldo)\b|double[ -]entry|duplicate[ -]payment', re.I,
)
FINANCIAL_RISK = re.compile(
    r'spring\s*batch|\b(batch|chunk|checkpoint|restart|retry|retries|replay|duplicate|claim|lease|staging|ledger|posting|'
    r'settlement|reconcil\w*|cashflow|idempotenc\w*|rollback|rounding|debit|credit|balance|reversal|'
    r'explain|migrat\w*|audit|rekonsiliasi|saldo|jurnal|transaksi|duplikat)\b', re.I,
)
FINANCIAL_REFERENCES = (
    ('spring-batch-safety.md', re.compile(r'spring\s*batch|JobRepository|ItemReader|ItemWriter|ExecutionContext|\bchunk\b', re.I)),
    ('staging-posting-pipeline.md', re.compile(r'claim|staging|posting|lease|outbox|settlement|retry|replay|idempotenc', re.I)),
    ('ledger-invariants.sql', re.compile(r'ledger|reconcil|balance|debit|credit|reversal|jurnal|rekonsiliasi|saldo', re.I)),
    ('sql-performance-and-change-safety.md', re.compile(r'EXPLAIN|performance|query plan|DDL|migra|backfill|audit|retention', re.I)),
)


def select_financial_references(task, source=''):
    """Select allowlisted references for an observed transaction-integrity scope."""
    if not (FINANCIAL_SCOPE.search(task) and FINANCIAL_RISK.search(task)):
        return []
    observed = task + '\n' + source
    return [name for name, signals in FINANCIAL_REFERENCES if signals.search(observed)]


def useful_financial_memory(record, project_fingerprint, observed_at):
    if record.get('trust') != 'verified' or record.get('status', 'active') != 'active':
        return False
    if project_fingerprint is not None and record.get('project_fingerprint') != project_fingerprint:
        return False
    review_after = record.get('review_after')
    if review_after is None:
        return True
    try:
        normalized = review_after[:-1] + '+00:00' if review_after.endswith('Z') else review_after
        deadline = datetime.fromisoformat(normalized)
        return deadline.tzinfo is not None and deadline > observed_at
    except (AttributeError, TypeError, ValueError):
        return False


class RawEvidenceStore:
    """Write full evidence to disk and return stable opaque references."""

    def __init__(self, root):
        self.root = Path(root)

    @staticmethod
    def digest(name, text):
        return hashlib.sha256((name + '\0' + text).encode('utf-8')).hexdigest()[:20]

    def put(self, name, text):
        digest = self.digest(name, text)
        path = self.root / (digest + '.json')
        if self.root.is_symlink() or path.is_symlink():
            raise ValueError('evidence store cannot use symlinks')
        self.root.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.root, delete=False) as stream:
                temporary = Path(stream.name)
                json.dump({'name': name, 'text': text}, stream, ensure_ascii=False)
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return "raw://" + digest

    def get(self, reference):
        if not isinstance(reference, str) or not reference.startswith("raw://"):
            raise ValueError("invalid raw evidence reference")
        digest = reference[len("raw://"):]
        if not re.fullmatch(r"[a-f0-9]{20}", digest):
            raise ValueError("invalid raw evidence reference")
        item = self.root / (digest + '.json')
        legacy = self.root / (digest + '.txt')
        if self.root.is_symlink() or item.is_symlink() or legacy.is_symlink():
            raise ValueError('evidence store cannot use symlinks')
        if not item.exists():
            return legacy.read_text(encoding='utf-8')
        record = json.loads(item.read_text(encoding='utf-8'))
        if (not isinstance(record, dict) or not isinstance(record.get('name'), str)
                or not isinstance(record.get('text'), str) or digest != self.digest(record['name'], record['text'])):
            raise ValueError('raw evidence digest mismatch')
        return record['text']


def words(text):
    return [
        word.casefold()
        for word in re.findall(r"[A-Za-z0-9_-]{3,}", text)
        if word.casefold() not in STOPWORDS
    ]


def count_tokens(text):
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("o200k_base")
        return len(encoding.encode(text)), "tiktoken:o200k_base"
    except Exception:
        return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE)), "lexical-fallback"


def _relevant_lines(text, task_words, max_lines):
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    ranked = []
    for index, line in enumerate(lines):
        lowered = line.casefold()
        overlap = sum(1 for word in task_words if word in lowered)
        if overlap or SIGNAL.search(line):
            ranked.append((overlap + (2 if SIGNAL.search(line) else 0), index, line))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    chosen = {index for _, index, _ in ranked[:max_lines]}
    return [line for index, line in enumerate(lines) if index in chosen]


def _memory_score(record, task_words):
    text = " ".join(
        str(record.get(key, ""))
        for key in ("title", "content", "topic", "kind")
    ).casefold()
    return sum(1 for word in task_words if word in text)


def _optimized_case(case, store, max_lines, max_chars):
    task = case["task"]
    project = case["project"]
    task_words = list(dict.fromkeys(words(task)))
    memory = [
        record for record in case.get("memory", [])
        if (record.get("scope") or {}).get("project") == project
    ]
    financial_references = select_financial_references(task, case.get('source', ''))
    if financial_references:
        observed_at = datetime.now(timezone.utc)
        memory = [record for record in memory if useful_financial_memory(record, case.get('project_fingerprint'), observed_at)]
    ranked = sorted(
        memory,
        key=lambda record: (-_memory_score(record, task_words), record.get("id", "")),
    )
    selected_memory = ranked[:2]
    selected_ids = {record.get("id") for record in selected_memory}

    baseline = [
        "TASK\n" + task,
        "MEMORY\n" + "\n\n".join(
            "[{}|{}] {}\n{}".format(
                record.get("kind"), record.get("trust"),
                record.get("title"), record.get("content"),
            )
            for record in memory
        ),
        "TOOL OUTPUT\n" + case.get("tool_output", ""),
        "SOURCE\n" + case.get("source", ""),
    ]

    memory_lines = []
    for record in selected_memory:
        body = " ".join(str(record.get("content", "")).split())
        memory_lines.append(
            "- [{}|{}] {}: {} (id: {})".format(
                record.get("kind"), record.get("trust"), record.get("title"),
                body[:240], record.get("id"),
            )
        )

    # Preserve unfamiliar facts and ordering; only collapse repeated identical
    # debug lines. Source is left intact because line filtering can break context.
    tool_lines = []
    seen_debug = set()
    for line in case.get("tool_output", "").splitlines():
        if line.strip().casefold().startswith("debug:"):
            if line in seen_debug:
                continue
            seen_debug.add(line)
        tool_lines.append(line)
    source_lines = case.get("source", "").splitlines()
    constraints = list(dict.fromkeys(case.get("constraints", [])))

    raw_tool = store.put(case["id"] + ":tool", case.get("tool_output", ""))
    raw_source = store.put(case["id"] + ":source", case.get("source", ""))
    memory_text = '\n'.join(memory_lines) if memory_lines else '(none)'
    body = [
        "TASK\n" + task,
        "SELECTED MEMORY\n" + memory_text,
        "RELEVANT EVIDENCE\n" + "\n".join(tool_lines + source_lines),
        "FINANCIAL REFERENCES\n" + "\n".join(financial_references) if financial_references else '',
        "CRITICAL CONSTRAINTS (VERBATIM)\n" + "\n".join(constraints),
        "RAW EVIDENCE\n{} (tool)\n{} (source)".format(raw_tool, raw_source),
    ]
    optimized = "\n\n".join(part for part in body if part.strip())
    return {
        "id": case["id"],
        "project": project,
        "baseline": "\n\n".join(baseline),
        "optimized": optimized,
        "selected_memory": sorted(selected_ids),
        "omitted_memory": sorted(
            record.get("id") for record in memory if record.get("id") not in selected_ids
        ),
        "raw_refs": [raw_tool, raw_source],
        "raw_tool": case.get("tool_output", ""),
        "raw_source": case.get("source", ""),
        "must_include": list(case.get("must_include", [])),
        "constraints": constraints,
        "max_chars": max_chars,
        "financial_references": financial_references,
    }, selected_memory, memory_text


def optimize_case(case, store, max_lines=18, max_chars=6000):
    """Return baseline/optimized context and verification metadata."""
    result, _, _ = _optimized_case(case, store, max_lines, max_chars)
    return result


ROUTINE_DEBUG = re.compile(
    r'debug: (?:request accepted|cache warm|worker heartbeat(?: worker=[A-Z0-9]+ sequence=\d+ state=idle)?|queue depth \d+|config loaded|'
    r'trace span complete|connection pool ready|retry budget available)', re.I,
)
SNIPPET_START = re.compile(r'^(?:(?:async )?def |class |const |//|/\*)')
SOURCE_CONDITION = re.compile(r'\b(assert|unless|except|require\w*|raise|throw|deny|approval|rollback)\b', re.I)


def select_captured_snippets(source, task):
    """Select from an explicitly supplied collection of snippets, never rewrite a source file."""
    chunks = []
    for line in source.splitlines():
        if not chunks or SNIPPET_START.match(line):
            chunks.append([])
        chunks[-1].append(line)
    query = set(words(task))
    included = []
    for chunk in dict.fromkeys('\n'.join(lines) for lines in chunks):
        if query.intersection(words(chunk)) or SOURCE_CONDITION.search(chunk):
            included.append(chunk)
    return '\n'.join(included) if included else source


def compact_case(case, store, *, retrieve=True, compact=True):
    """Prepare a reversible packet while keeping complete source and logs available."""
    result, selected_records, memory_text = _optimized_case(case, store, 18, 6000)
    if not retrieve and not compact:
        return result
    source = result['raw_source']
    if retrieve and case.get('source_kind') == 'captured_snippets':
        source = select_captured_snippets(source, case['task'])
    rules = result['constraints']
    lines = result['raw_tool'].splitlines()
    if compact:
        query = set(words(case['task']))
        lines = [line for line in lines if line not in rules and not
                 (ROUTINE_DEBUG.fullmatch(line.strip()) and not query.intersection(words(line)[1:]))]
    debug = set()
    tool_lines = []
    for line in lines:
        if line.strip().casefold().startswith('debug:'):
            if line in debug:
                continue
            debug.add(line)
        tool_lines.append(line)
    selected = {id(record) for record in selected_records}
    memory = [record for record in case.get('memory', []) if id(record) in selected]
    context = ['Task: ' + case['task'], 'Constraints:\n' + '\n'.join(rules)]
    if compact:
        # Legacy fixture records have independent IDs. Preserve complete selected facts, including titles.
        context.extend(f"Memory [{record.get('trust')}]: {record.get('title')} — {record.get('content')}"
                       for record in memory)
    else:
        context.append(memory_text)
    context.extend(['Observations:\n' + '\n'.join(tool_lines), 'Source excerpts:\n' + source])
    if result['financial_references']:
        context.append('References: ' + ', '.join(result['financial_references']))
    if source != result['raw_source'] or tool_lines != result['raw_tool'].splitlines():
        context.append('Full source and log remain in the evidence store. Expand before relying on incomplete evidence.')
    result['optimized'] = '\n\n'.join(context)
    return result


def evaluate(optimized_case):
    text = optimized_case["optimized"]
    missing = [needle for needle in optimized_case["must_include"] if needle.casefold() not in text.casefold()]
    missing_constraints = [
        constraint for constraint in optimized_case["constraints"]
        if constraint not in text
    ]
    baseline_tokens, encoding = count_tokens(optimized_case["baseline"])
    optimized_tokens, _ = count_tokens(text)
    reduction = 0.0 if baseline_tokens == 0 else (1 - optimized_tokens / baseline_tokens) * 100
    return {
        "baseline_tokens": baseline_tokens,
        "optimized_tokens": optimized_tokens,
        "reduction_percent": round(reduction, 2),
        "encoding": encoding,
        "missing_facts": missing,
        "missing_constraints": missing_constraints,
        "correct": not missing,
        "constraints_preserved": not missing_constraints,
    }


def run(cases, evidence_root):
    store = RawEvidenceStore(evidence_root)
    results = []
    for case in cases:
        optimized = optimize_case(case, store)
        metrics = evaluate(optimized)
        tool = store.get(optimized["raw_refs"][0])
        source = store.get(optimized["raw_refs"][1])
        metrics["raw_tool_recovered"] = tool == optimized["raw_tool"]
        metrics["raw_source_recovered"] = source == optimized["raw_source"]
        metrics["id"] = case["id"]
        metrics["optimized_chars"] = len(optimized["optimized"])
        metrics["selected_memory"] = optimized["selected_memory"]
        metrics["omitted_memory"] = optimized["omitted_memory"]
        metrics["raw_refs"] = optimized["raw_refs"]
        results.append(metrics)
    return results


def summarize(results):
    reductions = [item["reduction_percent"] for item in results]
    return {
        "cases": len(results),
        "median_reduction_percent": round(statistics.median(reductions), 2) if reductions else 0,
        "min_reduction_percent": min(reductions) if reductions else 0,
        "correct_cases": all(item["correct"] for item in results),
        "constraints_preserved": all(item["constraints_preserved"] for item in results),
        "raw_tool_recovered": all(item["raw_tool_recovered"] for item in results),
        "raw_source_recovered": all(item["raw_source_recovered"] for item in results),
        "encoding": results[0]["encoding"] if results else "unknown",
        "gate_pass": (
            bool(results)
            and statistics.median(reductions) >= 30
            and all(item["correct"] for item in results)
            and all(item["constraints_preserved"] for item in results)
            and all(item["raw_tool_recovered"] for item in results)
            and all(item["raw_source_recovered"] for item in results)
        ),
    }
