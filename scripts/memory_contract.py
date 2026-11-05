"""Validate and serialize provider-neutral companion memory records.

The module deliberately uses only the Python standard library. Providers own storage
and retrieval; this contract owns meaning, provenance, lifecycle, privacy, and
portable export.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys


SCHEMA_VERSION = 1
KINDS = {"fact", "decision", "lesson", "handoff", "preference"}
STATUSES = {"active", "superseded", "stale"}
TRUST_LEVELS = {"verified", "unverified", "untrusted"}
SOURCES = {"user", "repository", "test", "tool", "agent-inference", "import"}
NAME_RE = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")
TOPIC_RE = re.compile(r"[a-z0-9]+(?:[/-][a-z0-9]+)*\Z")
TAG_RE = re.compile(r"[a-z0-9][a-z0-9-]*\Z")
HEADER_RE = re.compile(
    r"\A<!-- memory-record:v1 (?P<meta>\{.*?\}) -->\n",
    re.DOTALL,
)

SENSITIVE_PATTERNS = (
    ("openai-style key", re.compile(r"\bsk-(?:proj-|test-)?[A-Za-z0-9_-]{16,}\b")),
    ("github token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("aws access key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("bearer token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~-]{20,}")),
    (
        "secret assignment",
        re.compile(
            r"(?i)(?:password|passwd|secret|api[_-]?key|access[_-]?token|auth[_-]?token)"
            r"\s*[:=]\s*\S{6,}"
        ),
    ),
    (
        "email address",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
    ),
)
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")


class ContractError(ValueError):
    """Raised when a record or bundle violates the memory contract."""


def _parse_time(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ContractError("{} must be a nonempty RFC 3339 timestamp".format(field))
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        raise ContractError("{} must be an RFC 3339 timestamp".format(field))
    if parsed.tzinfo is None:
        raise ContractError("{} must include a timezone".format(field))
    return parsed.astimezone(timezone.utc)


def _luhn(number):
    digits = [int(value) for value in number if value.isdigit()]
    if not digits:
        return False
    checksum = 0
    parity = len(digits) % 2
    for index, digit in enumerate(digits):
        if index % 2 == parity:
            digit *= 2
            if digit > 9:
                digit -= 9
        checksum += digit
    return checksum % 10 == 0


def scan_sensitive(text):
    """Return labels for likely credentials or personal data in *text*."""
    if not isinstance(text, str) or not text:
        return []
    labels = []
    for label, pattern in SENSITIVE_PATTERNS:
        if pattern.search(text):
            labels.append(label)
    for match in CARD_RE.finditer(text):
        if _luhn(match.group(0)):
            labels.append("payment card number")
            break
    return labels


def _safe_relative(value):
    if not isinstance(value, str) or not value.strip():
        return False
    return not value.startswith(("/", "\\")) and ".." not in Path(value).parts


def _check_string(errors, record, field, pattern=None, max_length=None, required=True):
    value = record.get(field)
    if value is None:
        if required:
            errors.append("{} is required".format(field))
        return
    if not isinstance(value, str) or not value.strip():
        errors.append("{} must be a nonempty string".format(field))
        return
    if max_length is not None and len(value) > max_length:
        errors.append("{} must contain at most {} characters".format(field, max_length))
    if pattern is not None and pattern.fullmatch(value) is None:
        errors.append("{} has an invalid format".format(field))


def validate_record(record):
    """Return a list of contract errors for one record."""
    errors = []
    if not isinstance(record, dict):
        return ["record must be an object"]
    allowed = {
        "schema_version", "id", "kind", "topic", "scope", "title", "content",
        "provenance", "confidence", "status", "trust", "created_at", "updated_at",
        "supersedes", "superseded_by", "review_after", "tags", "repository_anchors",
    }
    unknown = sorted(set(record) - allowed)
    if unknown:
        errors.append("unknown fields: {}".format(", ".join(unknown)))
    if record.get("schema_version") != SCHEMA_VERSION:
        errors.append("schema_version must be {}".format(SCHEMA_VERSION))
    _check_string(errors, record, "id", NAME_RE, 96)
    if record.get("kind") not in KINDS:
        errors.append("kind must be one of {}".format(sorted(KINDS)))
    _check_string(errors, record, "topic", TOPIC_RE, 120)
    _check_string(errors, record, "title", max_length=160)
    _check_string(errors, record, "content", max_length=4000)

    scope = record.get("scope")
    if not isinstance(scope, dict):
        errors.append("scope must be an object")
    else:
        scope_allowed = {"workspace", "project", "paths"}
        unknown = sorted(set(scope) - scope_allowed)
        if unknown:
            errors.append("unknown scope fields: {}".format(", ".join(unknown)))
        for field in ("workspace", "project"):
            _check_string(errors, scope, field, TOPIC_RE, 120)
        paths = scope.get("paths")
        if paths is not None:
            if not isinstance(paths, list) or len(paths) > 20:
                errors.append("scope.paths must be an array of at most 20 paths")
            else:
                for path in paths:
                    if not _safe_relative(path) or len(path) > 300:
                        errors.append("scope.paths contains an unsafe path")
                        break
                    if isinstance(path, str) and scan_sensitive(path):
                        errors.append("scope.paths contains sensitive data")
                        break

    provenance = record.get("provenance")
    if not isinstance(provenance, dict):
        errors.append("provenance must be an object")
    else:
        provenance_allowed = {"source", "session_id", "observed_at", "evidence"}
        unknown = sorted(set(provenance) - provenance_allowed)
        if unknown:
            errors.append("unknown provenance fields: {}".format(", ".join(unknown)))
        if provenance.get("source") not in SOURCES:
            errors.append("provenance.source is invalid")
        if "session_id" in provenance:
            _check_string(errors, provenance, "session_id", max_length=128)
        try:
            _parse_time(provenance.get("observed_at"), "provenance.observed_at")
        except ContractError as exc:
            errors.append(str(exc))
        evidence = provenance.get("evidence")
        if not isinstance(evidence, list) or not 1 <= len(evidence) <= 8:
            errors.append("provenance.evidence must contain 1 to 8 references")
        else:
            for item in evidence:
                if not isinstance(item, str) or not item.strip() or len(item) > 500:
                    errors.append("provenance.evidence items must be 1 to 500 characters")
                    break

    confidence = record.get("confidence")
    if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
        errors.append("confidence must be a number from 0 to 1")
    elif not 0 <= confidence <= 1:
        errors.append("confidence must be a number from 0 to 1")

    if record.get("status") not in STATUSES:
        errors.append("status must be one of {}".format(sorted(STATUSES)))
    if record.get("trust") not in TRUST_LEVELS:
        errors.append("trust must be one of {}".format(sorted(TRUST_LEVELS)))

    try:
        created = _parse_time(record.get("created_at"), "created_at")
        updated = _parse_time(record.get("updated_at"), "updated_at")
        if updated < created:
            errors.append("updated_at must not precede created_at")
    except ContractError as exc:
        errors.append(str(exc))
    review_after = record.get("review_after")
    if review_after is not None:
        try:
            _parse_time(review_after, "review_after")
        except ContractError as exc:
            errors.append(str(exc))

    supersedes = record.get("supersedes")
    if supersedes is not None:
        if not isinstance(supersedes, list) or len(supersedes) > 10:
            errors.append("supersedes must be an array of at most 10 record ids")
        else:
            for item in supersedes:
                if not isinstance(item, str) or NAME_RE.fullmatch(item) is None:
                    errors.append("supersedes contains an invalid record id")
                    break
                if item == record.get("id"):
                    errors.append("a record cannot supersede itself")
                    break
    superseded_by = record.get("superseded_by")
    if superseded_by is not None:
        if not isinstance(superseded_by, str) or NAME_RE.fullmatch(superseded_by) is None:
            errors.append("superseded_by must be a record id or null")
    if record.get("status") == "superseded" and superseded_by is None:
        errors.append("a superseded record requires superseded_by")
    if record.get("status") == "active" and superseded_by is not None:
        errors.append("an active record cannot have superseded_by")
    if record.get("status") == "active" and record.get("trust") == "untrusted":
        errors.append("an untrusted record cannot be active")
    if isinstance(provenance, dict) and provenance.get("source") == "agent-inference":
        if record.get("trust") == "verified":
            errors.append("agent-inference content cannot be verified without external evidence")

    tags = record.get("tags")
    if tags is not None:
        if not isinstance(tags, list) or len(tags) > 12:
            errors.append("tags must be an array of at most 12 values")
        else:
            for tag in tags:
                if not isinstance(tag, str) or TAG_RE.fullmatch(tag) is None or len(tag) > 48:
                    errors.append("tags contains an invalid value")
                    break

    anchors = record.get("repository_anchors")
    if anchors is not None:
        if not isinstance(anchors, list) or len(anchors) > 20:
            errors.append("repository_anchors must be an array of at most 20 values")
        else:
            for anchor in anchors:
                if not _safe_relative(anchor) or len(anchor) > 300:
                    errors.append("repository_anchors contains an unsafe path or symbol")
                    break
                if isinstance(anchor, str) and scan_sensitive(anchor):
                    errors.append("repository_anchors contains sensitive data")
                    break

    for field in ("title", "content"):
        value = record.get(field)
        if isinstance(value, str):
            labels = scan_sensitive(value)
            if labels:
                errors.append("{} contains sensitive data: {}".format(field, ", ".join(labels)))
    if isinstance(provenance, dict):
        for item in provenance.get("evidence") or []:
            if isinstance(item, str):
                labels = scan_sensitive(item)
                if labels:
                    errors.append(
                        "provenance.evidence contains sensitive data: {}".format(
                            ", ".join(labels)
                        )
                    )
    return errors


def canonical_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def bundle_checksum(records):
    digest = hashlib.sha256(canonical_json(records).encode("utf-8")).hexdigest()
    return "sha256:" + digest


def validate_bundle(bundle, verify_checksum=True):
    """Return a list of contract errors for a portable bundle."""
    errors = []
    if not isinstance(bundle, dict):
        return ["bundle must be an object"]
    allowed = {"schema_version", "exported_at", "scope", "records", "checksum"}
    unknown = sorted(set(bundle) - allowed)
    if unknown:
        errors.append("unknown bundle fields: {}".format(", ".join(unknown)))
    if bundle.get("schema_version") != SCHEMA_VERSION:
        errors.append("bundle schema_version must be {}".format(SCHEMA_VERSION))
    try:
        _parse_time(bundle.get("exported_at"), "exported_at")
    except ContractError as exc:
        errors.append(str(exc))
    scope = bundle.get("scope")
    if not isinstance(scope, dict):
        errors.append("bundle scope must be an object")
        scope = {}
    else:
        for field in ("workspace", "project"):
            _check_string(errors, scope, field, TOPIC_RE, 120)
    records = bundle.get("records")
    if not isinstance(records, list):
        errors.append("bundle records must be an array")
        return errors

    by_id = {}
    for index, record in enumerate(records):
        record_errors = validate_record(record)
        errors.extend(
            "records[{}]: {}".format(index, error) for error in record_errors
        )
        if not isinstance(record, dict):
            continue
        record_id = record.get("id")
        if isinstance(record_id, str):
            if record_id in by_id:
                errors.append("duplicate record id: {}".format(record_id))
            by_id[record_id] = record
        record_scope = record.get("scope")
        if isinstance(record_scope, dict) and isinstance(scope, dict):
            if record_scope.get("workspace") != scope.get("workspace"):
                errors.append("record {} is outside the bundle workspace".format(record_id))
            if record_scope.get("project") != scope.get("project"):
                errors.append("record {} is outside the bundle project".format(record_id))

    active_topics = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        record_id = record.get("id")
        if record.get("status") == "superseded":
            target = by_id.get(record.get("superseded_by"))
            if not isinstance(target, dict):
                errors.append("{} has a missing superseded_by target".format(record_id))
            elif record_id not in (target.get("supersedes") or []):
                errors.append(
                    "{} is not listed in its replacement's supersedes".format(record_id)
                )
        for superseded_id in record.get("supersedes") or []:
            if not isinstance(superseded_id, str):
                continue
            target = by_id.get(superseded_id)
            if not isinstance(target, dict):
                errors.append("{} supersedes a missing record {}".format(record_id, superseded_id))
            elif target.get("superseded_by") != record_id:
                errors.append(
                    "{} does not point back to its replacement {}".format(
                        superseded_id, record_id
                    )
                )
            elif target.get("status") != "superseded":
                errors.append("{} must be marked superseded".format(superseded_id))
        if (
            record.get("status") == "active"
            and isinstance(record.get("scope"), dict)
            and isinstance(record.get("topic"), str)
        ):
            key = (
                record["scope"].get("workspace"),
                record["scope"].get("project"),
                record.get("topic"),
            )
            if key in active_topics:
                errors.append("multiple active records for topic {}".format(record.get("topic")))
            active_topics[key] = record_id

    if verify_checksum:
        expected = bundle.get("checksum")
        actual = bundle_checksum(records)
        if expected != actual:
            errors.append("bundle checksum does not match")
    return errors


def make_bundle(records, exported_at, workspace, project):
    bundle = {
        "schema_version": SCHEMA_VERSION,
        "exported_at": exported_at,
        "scope": {"workspace": workspace, "project": project},
        "records": records,
        "checksum": bundle_checksum(records),
    }
    errors = validate_bundle(bundle)
    if errors:
        raise ContractError("; ".join(errors))
    return bundle


def write_bundle(path, bundle):
    errors = validate_bundle(bundle)
    if errors:
        raise ContractError("; ".join(errors))
    Path(path).write_text(
        json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_bundle(path):
    try:
        bundle = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError("cannot read bundle: {}".format(exc))
    errors = validate_bundle(bundle)
    if errors:
        raise ContractError("; ".join(errors))
    return bundle


def render_record(record):
    """Encode a record as provider-neutral markdown with a parseable header."""
    errors = validate_record(record)
    if errors:
        raise ContractError("; ".join(errors))
    meta = {
        "id": record["id"],
        "kind": record["kind"],
        "topic": record["topic"],
        "status": record["status"],
        "trust": record["trust"],
        "confidence": record["confidence"],
        "scope": {
            "workspace": record["scope"]["workspace"],
            "project": record["scope"]["project"],
        },
    }
    header = canonical_json(meta)
    return "<!-- memory-record:v1 {} -->\n# {}\n\n{}\n".format(
        header, record["title"], record["content"].rstrip()
    )


def parse_record(text):
    """Extract the provider-neutral metadata and body from stored markdown."""
    if not isinstance(text, str):
        raise ContractError("stored record must be text")
    match = HEADER_RE.match(text)
    if match is None:
        raise ContractError("stored record has no memory-record:v1 header")
    try:
        meta = json.loads(match.group("meta"))
    except json.JSONDecodeError as exc:
        raise ContractError("stored record header is invalid JSON: {}".format(exc))
    if not isinstance(meta, dict):
        raise ContractError("stored record header must be an object")
    for field in ("id", "kind", "status", "trust", "scope"):
        if field not in meta:
            raise ContractError("stored record header is missing {}".format(field))
    if not isinstance(meta["scope"], dict):
        raise ContractError("stored record header scope must be an object")
    body = text[match.end():]
    lines = body.splitlines()
    title = ""
    if lines and lines[0].startswith("# "):
        title = lines[0][2:].strip()
        lines = lines[1:]
    content = "\n".join(lines).strip()
    return {"meta": meta, "title": title, "content": content}


def apply_repository_check(record, anchor_exists):
    """Demote a record to stale when none of its repository anchors still exist."""
    if record.get("status") != "active":
        return dict(record)
    anchors = record.get("repository_anchors") or []
    if not anchors:
        return dict(record)
    if any(bool(anchor_exists(anchor)) for anchor in anchors):
        return dict(record)
    result = dict(record)
    result["status"] = "stale"
    result["trust"] = "unverified"
    return result


def is_automatic_context_eligible(record, project, now=None, min_confidence=0.5):
    if record.get("status") != "active":
        return False
    scope = record.get("scope") or {}
    if scope.get("project") != project:
        return False
    if record.get("trust") == "untrusted":
        return False
    if record.get("confidence", 0) < min_confidence:
        return False
    review_after = record.get("review_after")
    if review_after:
        current = now or datetime.now(timezone.utc)
        try:
            if _parse_time(review_after, "review_after") < current:
                return False
        except ContractError:
            return False
    return True


def select_context(records, project, max_chars=2000, min_confidence=0.5, now=None):
    """Select a bounded, active, project-scoped context set."""
    selected = [
        record for record in records
        if is_automatic_context_eligible(record, project, now, min_confidence)
    ]
    selected.sort(
        key=lambda record: (
            -float(record.get("confidence", 0)),
            record.get("topic", ""),
            record.get("id", ""),
        )
    )
    result = []
    used = 0
    for record in selected:
        block = render_context_block(record)
        if len(block) > max_chars or used + len(block) > max_chars:
            continue
        result.append(record)
        used += len(block)
    return result


def render_context_block(record):
    provenance = record.get("provenance") or {}
    return (
        "[{kind}|{status}|{trust}] {title} ({topic})\n"
        "{content}\n"
        "Evidence: {source}, {observed_at}\n"
    ).format(
        kind=record.get("kind"),
        status=record.get("status"),
        trust=record.get("trust"),
        title=record.get("title"),
        topic=record.get("topic"),
        content=record.get("content"),
        source=provenance.get("source"),
        observed_at=provenance.get("observed_at"),
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    record_parser = subparsers.add_parser("validate-record")
    record_parser.add_argument("path", type=Path)
    bundle_parser = subparsers.add_parser("validate-bundle")
    bundle_parser.add_argument("path", type=Path)
    scan_parser = subparsers.add_parser("scan")
    scan_parser.add_argument("path", type=Path)
    args = parser.parse_args()

    try:
        if args.command == "validate-record":
            record = json.loads(args.path.read_text(encoding="utf-8"))
            errors = validate_record(record)
        elif args.command == "validate-bundle":
            errors = validate_bundle(
                json.loads(args.path.read_text(encoding="utf-8"))
            )
        else:
            labels = scan_sensitive(args.path.read_text(encoding="utf-8"))
            errors = ["sensitive data: {}".format(", ".join(labels))] if labels else []
    except (OSError, json.JSONDecodeError) as exc:
        print("FAIL {}".format(exc), file=sys.stderr)
        return 2

    if errors:
        for error in errors:
            print("FAIL " + error, file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
