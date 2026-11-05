"""Token-aware context selection with lossless raw-evidence recovery."""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import re
import statistics


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


class RawEvidenceStore:
    """Write full evidence to disk and return stable opaque references."""

    def __init__(self, root):
        self.root = Path(root)

    def put(self, name, text):
        digest = hashlib.sha256((name + "\0" + text).encode("utf-8")).hexdigest()[:20]
        path = self.root / (digest + ".txt")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return "raw://" + digest

    def get(self, reference):
        if not isinstance(reference, str) or not reference.startswith("raw://"):
            raise ValueError("invalid raw evidence reference")
        digest = reference[len("raw://"):]
        if not re.fullmatch(r"[a-f0-9]{20}", digest):
            raise ValueError("invalid raw evidence reference")
        return (self.root / (digest + ".txt")).read_text(encoding="utf-8")


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


def optimize_case(case, store, max_lines=18, max_chars=6000):
    """Return baseline/optimized context and verification metadata."""
    task = case["task"]
    project = case["project"]
    task_words = list(dict.fromkeys(words(task)))
    memory = [
        record for record in case.get("memory", [])
        if (record.get("scope") or {}).get("project") == project
    ]
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
    body = [
        "TASK\n" + task,
        "SELECTED MEMORY\n" + ("\n".join(memory_lines) if memory_lines else "(none)"),
        "RELEVANT EVIDENCE\n" + "\n".join(tool_lines + source_lines),
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
    }


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
