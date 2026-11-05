"""Run a repeatable, local-only memory provider bake-off.

The runner treats providers as interchangeable stores behind the contract in
``scripts/memory_contract.py``. It never downloads or installs a provider; pass
already-installed binaries explicitly. All provider data, home directories, and
exports live under the selected artifact directory.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.memory_contract import (  # noqa: E402
    ContractError,
    is_automatic_context_eligible,
    parse_record,
    render_record,
    validate_record,
)


CASES = ROOT / "tests/memory_bakeoff_cases.yaml"
DEFAULT_ARTIFACTS = ROOT / ".agents/artifacts/phase2/bakeoff"
PROVIDER_VERSIONS = {
    "ai-memory": "3.4.0",
    "engram": "3.6.2",
}


class ProviderError(RuntimeError):
    """Raised when a provider command or local service fails."""


def utc_now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def free_port():
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def load_cases(path=CASES):
    with Path(path).open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        raise ValueError("bake-off cases must be a mapping")
    if not data.get("records") or not data.get("queries"):
        raise ValueError("bake-off cases require records and queries")
    return data


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "does", "for", "from",
    "how", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "use", "what", "when", "where", "which", "who", "why", "with",
}


def expanded_query(query):
    """Use an OR expression for natural-language queries on FTS5."""
    terms = re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]+", query)
    meaningful = []
    for term in terms:
        normalized = term.casefold()
        if normalized not in STOPWORDS and len(term) > 2 and term not in meaningful:
            meaningful.append(term)
    if len(meaningful) <= 1:
        return query
    return " OR ".join(meaningful)


def make_record(raw, workspace):
    record = {
        "schema_version": 1,
        "id": raw["id"],
        "kind": raw["kind"],
        "topic": raw["topic"],
        "scope": {
            "workspace": workspace,
            "project": raw["project"],
        },
        "title": raw["title"],
        "content": raw["content"],
        "provenance": {
            "source": raw["source"],
            "observed_at": raw.get("observed_at", raw["created_at"]),
            "evidence": list(raw["evidence"]),
        },
        "confidence": float(raw["confidence"]),
        "status": raw["status"],
        "trust": raw["trust"],
        "created_at": raw["created_at"],
        "updated_at": raw["updated_at"],
    }
    for field in ("supersedes", "superseded_by", "review_after", "tags", "repository_anchors"):
        if field in raw:
            record[field] = raw[field]
    errors = validate_record(record)
    if errors:
        raise ContractError("{}: {}".format(record["id"], "; ".join(errors)))
    return record


def build_records(cases):
    records = [make_record(raw, cases["workspace"]) for raw in cases["records"]]
    records.extend(
        make_record(raw, cases["workspace"]) for raw in cases.get("beta_records", [])
    )
    return records


def provider_environment(root, **extra):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(("AI_MEMORY_", "ENGRAM_"))
    }
    env["HOME"] = str(root / "home")
    env.update(extra)
    return env


class ProviderAdapter:
    name = "provider"
    supports_import = False
    export_format = "unknown"

    def __init__(self, root, binary, workspace, project):
        self.root = Path(root)
        self.binary = Path(binary)
        self.workspace = workspace
        self.project = project
        self.home = self.root / "home"
        self.data_dir = self.root / "data"
        self.cwd = self.root / "project"
        for path in (self.home, self.cwd):
            path.mkdir(parents=True, exist_ok=True)
        self.process = None
        self.port = None

    def env(self):
        return provider_environment(self.root)

    def start(self):
        raise NotImplementedError

    def stop(self):
        if self.process is None:
            return
        process = self.process
        self.process = None
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def restart(self):
        self.stop()
        self.start()

    def version(self):
        completed = self._run([str(self.binary), "--version"], timeout=20)
        return completed.stdout.strip().splitlines()[0] if completed.stdout.strip() else "unknown"

    def write_record(self, record):
        errors = validate_record(record)
        if errors:
            raise ContractError("; ".join(errors))

    def recall(self, project, query, limit=8):
        raise NotImplementedError

    def delete(self, record_id):
        raise NotImplementedError

    def restore_deleted(self, record_id, token):
        raise NotImplementedError

    def export(self, path):
        raise NotImplementedError

    def import_export(self, path):
        return False

    def scan_store(self, needle):
        if not self.data_dir.exists():
            return False
        needle_bytes = needle.encode("utf-8")
        for path in self.data_dir.rglob("*"):
            if path.is_file():
                try:
                    if needle_bytes in path.read_bytes():
                        return True
                except OSError:
                    continue
        return False

    def store_bytes(self):
        total = 0
        for path in self.data_dir.rglob("*") if self.data_dir.exists() else []:
            if path.is_file():
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
        return total

    def _run(self, command, input_text=None, timeout=60, check=True):
        completed = subprocess.run(
            command,
            cwd=str(self.cwd),
            env=self.env(),
            input=input_text,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            check=False,
        )
        if check and completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise ProviderError(
                "{} failed ({}): {}".format(
                    " ".join(command[:2]), completed.returncode, detail[-1200:]
                )
            )
        return completed

    def _http(self, path, method="GET", body=None, timeout=30):
        if not self.port:
            raise ProviderError("{} server is not running".format(self.name))
        url = "http://127.0.0.1:{}{}".format(self.port, path)
        headers = {"Accept": "application/json"}
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise ProviderError(
                "{} returned HTTP {}: {}".format(path, exc.code, detail[:1200])
            )
        except URLError as exc:
            raise ProviderError("{} request failed: {}".format(path, exc.reason))
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProviderError("{} returned invalid JSON: {}".format(path, exc))

    def _wait_http(self, path="/health", timeout=30):
        deadline = time.monotonic() + timeout
        url = "http://127.0.0.1:{}{}".format(self.port, path)
        while time.monotonic() < deadline:
            if self.process is not None and self.process.poll() is not None:
                raise ProviderError("{} exited before becoming ready".format(self.name))
            try:
                with urlopen(url, timeout=1):
                    return
            except HTTPError:
                return
            except URLError:
                time.sleep(0.2)
        raise ProviderError("{} did not become ready in {}s".format(self.name, timeout))


class EngramAdapter(ProviderAdapter):
    name = "engram"
    supports_import = True
    export_format = "engram-json-0.2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ids = {}
        self.search_limit = 8

    def start(self):
        self.port = free_port()
        log = self.root / "engram.log"
        self.process = subprocess.Popen(
            [str(self.binary), "serve", str(self.port)],
            cwd=str(self.cwd),
            env=self.env(),
            stdout=log.open("w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        self._wait_http("/health", timeout=30)

    def env(self):
        return provider_environment(
            self.root,
            ENGRAM_DATA_DIR=str(self.data_dir),
            ENGRAM_PROJECT=self.project,
        )

    def write_record(self, record):
        super().write_record(record)
        type_map = {
            "fact": "fact",
            "decision": "decision",
            "lesson": "pattern",
            "handoff": "session_summary",
            "preference": "preference",
        }
        completed = self._run(
            [
                str(self.binary), "save", record["title"], render_record(record),
                "--type", type_map[record["kind"]],
                "--project", record["scope"]["project"],
                "--scope", "project",
            ],
            timeout=60,
        )
        match = re.search(r"#(\d+)", completed.stdout)
        if match is None:
            raise ProviderError("engram save returned no observation id: {}".format(completed.stdout[-500:]))
        self.ids[record["id"]] = int(match.group(1))

    def recall(self, project, query, limit=8):
        params = urlencode(
            {
                "q": query,
                "project": project,
                "limit": str(limit),
                "match_mode": "any",
            }
        )
        payload = self._http("/search?" + params)
        rows = payload.get("results", []) if isinstance(payload, dict) else payload
        results = []
        seen = set()
        for row in rows or []:
            observation_id = row.get("id")
            if observation_id is None:
                continue
            observation = self._http("/observations/{}".format(observation_id))
            content = observation.get("content") or ""
            try:
                parsed = parse_record(content)
            except ContractError:
                continue
            meta = parsed["meta"]
            record = {
                "id": meta["id"],
                "kind": meta.get("kind"),
                "status": meta.get("status"),
                "trust": meta.get("trust"),
                "confidence": float(meta.get("confidence", 0)),
                "scope": {"project": (meta.get("scope") or {}).get("project")},
                "content": parsed["content"],
            }
            if record["id"] in seen:
                continue
            if not is_automatic_context_eligible(
                record, project, min_confidence=0.5
            ):
                continue
            seen.add(record["id"])
            results.append(record)
        return results

    def delete(self, record_id):
        observation_id = self.ids.get(record_id)
        if observation_id is None:
            raise ProviderError("no stored observation id for {}".format(record_id))
        export_path = self.root / "recovery-{}.json".format(record_id)
        self.export(export_path)
        self._http(
            "/observations/{}?{}".format(
                observation_id,
                urlencode({"hard": "true", "expected_project": self.project}),
            ),
            method="DELETE",
        )
        return {"export": str(export_path)}

    def restore_deleted(self, record_id, token):
        self.import_export(token["export"])

    def export(self, path):
        payload = self._http("/export?" + urlencode({"project": self.project}))
        Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return Path(path)

    def import_export(self, path):
        body = Path(path).read_bytes()
        payload = self._http("/import", method="POST", body=body)
        return isinstance(payload, dict)


class AiMemoryAdapter(ProviderAdapter):
    name = "ai-memory"
    supports_import = False
    export_format = "okf-0.2"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._initialized = False
        self._token = "phase2-bench-token-0123456789abcdef"

    def env(self):
        return provider_environment(
            self.root,
            AI_MEMORY_DATA_DIR=str(self.data_dir),
            AI_MEMORY_EMBEDDING_PROVIDER="none",
            AI_MEMORY_AUTH_TOKEN=self._token,
            AI_MEMORY_SERVER_URL="http://127.0.0.1:{}".format(self.port or 0),
        )

    def start(self):
        if not self._initialized:
            self._run([str(self.binary), "init"], timeout=60)
            self._initialized = True
        self.port = free_port()
        log = self.root / "ai-memory.log"
        self.process = subprocess.Popen(
            [
                str(self.binary), "serve",
                "--transport", "http",
                "--bind", "127.0.0.1:{}".format(self.port),
                "--no-watcher",
            ],
            cwd=str(self.cwd),
            env=self.env(),
            stdout=log.open("w", encoding="utf-8"),
            stderr=subprocess.STDOUT,
        )
        self._wait_http("/health", timeout=60)

    def write_record(self, record):
        super().write_record(record)
        kind_map = {
            "fact": "fact",
            "decision": "decision",
            "lesson": "gotcha",
            "handoff": "fact",
            "preference": "rule",
        }
        self._run(
            [
                str(self.binary), "write-page",
                "--path", "memory/{}.md".format(record["id"]),
                "--body", "-",
                "--title", record["title"],
                "--kind", kind_map[record["kind"]],
                "--workspace", record["scope"]["workspace"],
                "--project", record["scope"]["project"],
                "--tag", "phase2",
            ],
            input_text=render_record(record),
            timeout=60,
        )

    def recall(self, project, query, limit=8):
        completed = self._run(
            [
                str(self.binary), "search", expanded_query(query),
                "--workspace", self.workspace,
                "--project", project,
                "--json",
                "--limit", str(limit),
            ],
            timeout=60,
        )
        try:
            rows = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise ProviderError("ai-memory search returned invalid JSON: {}".format(exc))
        results = []
        seen = set()
        for row in rows:
            path = row.get("path")
            if not path:
                continue
            page = self._run(
                [
                    str(self.binary), "read-page",
                    "--path", path,
                    "--workspace", self.workspace,
                    "--project", project,
                    "--json",
                ],
                timeout=60,
            )
            try:
                payload = json.loads(page.stdout)
            except json.JSONDecodeError as exc:
                raise ProviderError("ai-memory read-page returned invalid JSON: {}".format(exc))
            try:
                parsed = parse_record(payload.get("body") or "")
            except ContractError:
                continue
            meta = parsed["meta"]
            record = {
                "id": meta["id"],
                "kind": meta.get("kind"),
                "status": meta.get("status"),
                "trust": meta.get("trust"),
                "confidence": float(meta.get("confidence", 0)),
                "scope": {"project": (meta.get("scope") or {}).get("project")},
                "content": parsed["content"],
            }
            if record["id"] in seen:
                continue
            if not is_automatic_context_eligible(
                record, project, min_confidence=0.5
            ):
                continue
            seen.add(record["id"])
            results.append(record)
        return results

    def delete(self, record_id):
        checkpoints = self._run(
            [
                str(self.binary), "checkpoints",
                "--json",
                "--data-dir", str(self.data_dir),
            ],
            timeout=60,
        )
        try:
            latest = json.loads(checkpoints.stdout)[0]["oid"]
        except (json.JSONDecodeError, IndexError, KeyError) as exc:
            raise ProviderError("cannot read ai-memory checkpoint: {}".format(exc))
        self._run(
            [
                str(self.binary), "delete-page",
                "--path", "memory/{}.md".format(record_id),
                "--workspace", self.workspace,
                "--project", self.project,
            ],
            timeout=60,
        )
        return {"checkpoint": latest}

    def restore_deleted(self, record_id, token):
        self._run(
            [
                str(self.binary), "restore-page",
                "--path", "memory/{}.md".format(record_id),
                "--from", token["checkpoint"],
                "--workspace", self.workspace,
                "--project", self.project,
                "--json",
            ],
            timeout=60,
        )

    def export(self, path):
        self._run(
            [
                str(self.binary), "export-okf",
                "--workspace", self.workspace,
                "--project", self.project,
                "--to", str(path),
            ],
            timeout=60,
        )
        if not Path(path).exists():
            raise ProviderError("ai-memory export was not created")
        return Path(path)


def _adapter_for(name, root, binary, cases):
    if name == "engram":
        return EngramAdapter(root, binary, cases["workspace"], cases["project"])
    if name == "ai-memory":
        return AiMemoryAdapter(root, binary, cases["workspace"], cases["project"])
    raise ValueError("unknown provider: {}".format(name))


def _probe_record(cases, workspace):
    probe = cases["privacy_probe"]
    return {
        "schema_version": 1,
        "id": "privacy-canary",
        "kind": "fact",
        "topic": "security/privacy-probe",
        "scope": {"workspace": workspace, "project": cases["project"]},
        "title": "Privacy probe",
        "content": probe["content"],
        "provenance": {
            "source": "user",
            "observed_at": "2026-11-05T03:30:00Z",
            "evidence": ["Synthetic canary used by the bake-off"],
        },
        "confidence": 0.99,
        "status": "active",
        "trust": "unverified",
        "created_at": "2026-11-05T03:30:00Z",
        "updated_at": "2026-11-05T03:30:00Z",
    }


def run_provider(name, binary, cases, artifacts):
    provider_root = Path(artifacts) / name
    if provider_root.exists():
        shutil.rmtree(provider_root)
    provider_root.mkdir(parents=True, exist_ok=True)
    adapter = _adapter_for(name, provider_root, binary, cases)
    result = {
        "provider": name,
        "version": PROVIDER_VERSIONS.get(name, "unknown"),
        "error": None,
        "queries": [],
        "privacy": {},
        "recovery": {},
        "timings": {},
        "gates": {},
    }
    try:
        started = time.monotonic()
        adapter.start()
        result["timings"]["setup_ms"] = round((time.monotonic() - started) * 1000, 1)
        result["version"] = adapter.version()

        records = build_records(cases)
        for record in records:
            adapter.write_record(record)
        result["records_written"] = len(records)

        query_times = []
        context_lengths = []
        stale_leaks = 0
        isolation_leaks = 0
        recall_passed = 0
        for query in cases["queries"]:
            started = time.monotonic()
            hits = adapter.recall(query["project"], query["query"], limit=8)
            elapsed = (time.monotonic() - started) * 1000
            query_times.append(elapsed)
            ids = [hit["id"] for hit in hits]
            expected = set(query.get("expect", []))
            forbidden = set(query.get("forbid", []))
            missing = sorted(expected - set(ids))
            forbidden_hits = sorted(forbidden & set(ids))
            passed = not missing and not forbidden_hits
            recall_passed += int(passed)
            if query["id"].startswith("isolation-"):
                isolation_leaks += len(forbidden_hits)
            else:
                stale_leaks += len(forbidden_hits)
            context_lengths.append(sum(len(hit.get("content", "")) for hit in hits))
            result["queries"].append(
                {
                    "id": query["id"],
                    "project": query["project"],
                    "query": query["query"],
                    "expected": sorted(expected),
                    "forbidden": sorted(forbidden),
                    "returned": ids,
                    "missing": missing,
                    "forbidden_hits": forbidden_hits,
                    "passed": passed,
                    "latency_ms": round(elapsed, 1),
                    "context_chars": context_lengths[-1],
                }
            )

        result["recall"] = {
            "passed": recall_passed,
            "total": len(cases["queries"]),
            "rate": recall_passed / len(cases["queries"]) if cases["queries"] else 0,
        }
        result["stale_leaks"] = stale_leaks
        result["isolation_leaks"] = isolation_leaks
        result["timings"]["query_ms_median"] = round(statistics.median(query_times), 1) if query_times else 0
        result["context_chars_median"] = round(statistics.median(context_lengths), 1) if context_lengths else 0

        probe = _probe_record(cases, cases["workspace"])
        canary = cases["privacy_probe"]["canary"]
        rejected = False
        try:
            adapter.write_record(probe)
        except ContractError:
            rejected = True
        canary_in_store = adapter.scan_store(canary)
        privacy_export = provider_root / "privacy-export"
        try:
            adapter.export(privacy_export)
            if privacy_export.is_file():
                canary_in_store = canary_in_store or canary.encode() in privacy_export.read_bytes()
        except ProviderError:
            pass
        result["privacy"] = {
            "canary_rejected": rejected,
            "canary_in_store": canary_in_store,
        }

        export_before = provider_root / (
            "memory-export.json" if adapter.supports_import else "memory-export.tar.gz"
        )
        adapter.export(export_before)
        export_bytes = export_before.stat().st_size if export_before.exists() else 0
        result["export"] = {
            "format": adapter.export_format,
            "bytes": export_bytes,
            "import_supported": adapter.supports_import,
        }

        token = adapter.delete("lesson-retry")
        after_delete = adapter.recall(cases["project"], "RETRY-EVENT-ID", limit=8)
        deletion_removed = "lesson-retry" not in {hit["id"] for hit in after_delete}
        adapter.restore_deleted("lesson-retry", token)
        after_restore = adapter.recall(cases["project"], "RETRY-EVENT-ID", limit=8)
        delete_recovered = "lesson-retry" in {hit["id"] for hit in after_restore}

        adapter.restart()
        after_restart = adapter.recall(cases["project"], "BILLING-DB-POSTGRES", limit=8)
        restart_recovered = "dec-billing-db" in {hit["id"] for hit in after_restart}

        imported = adapter.import_export(export_before) if adapter.supports_import else False
        result["recovery"] = {
            "delete_removed": deletion_removed,
            "delete_recovered": delete_recovered,
            "restart_recovered": restart_recovered,
            "import_supported": adapter.supports_import,
            "import_succeeded": bool(imported),
        }
        result["store_bytes"] = adapter.store_bytes()
        result["gates"] = {
            "recall": result["recall"]["rate"] >= cases["gates"]["min_recall_rate"],
            "stale": stale_leaks <= cases["gates"]["max_stale_leaks"],
            "isolation": isolation_leaks <= cases["gates"]["max_isolation_leaks"],
            "privacy": rejected and not canary_in_store,
            "delete_recovery": deletion_removed and delete_recovered,
            "restart_recovery": restart_recovered,
        }
        result["passed"] = all(result["gates"].values())
    except (ProviderError, ContractError, OSError, subprocess.TimeoutExpired) as exc:
        result["error"] = str(exc)
        result["passed"] = False
    finally:
        adapter.stop()
    return result


def recommend(results):
    passed = [result for result in results if result.get("passed")]
    if not passed:
        return "No provider met the Phase 2 hard gates; keep Phase 3 blocked."
    if len(passed) == 1:
        return "Use {} for the first runtime adapter; it is the only provider that met the hard gates.".format(
            passed[0]["provider"]
        )
    def sort_key(result):
        return (
            not result["export"]["import_supported"],
            result["timings"].get("setup_ms", 0),
            result["timings"].get("query_ms_median", 0),
        )
    chosen = sorted(passed, key=sort_key)[0]
    return (
        "Both providers met the hard gates. Use {} for the first Phase 3 adapter: "
        "it has the smaller operational setup among the passing providers{}."
    ).format(
        chosen["provider"],
        " and supports portable import" if chosen["export"]["import_supported"] else "",
    )


def format_report(result):
    lines = [
        "# Memory provider bake-off",
        "",
        "Run at: `{}`".format(result["run_at"]),
        "",
        "| Provider | Version | Recall | Stale | Isolation | Privacy | Delete recovery | Restart | Import | Setup ms | Query ms | Context chars | Store bytes | Gate |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for provider in result["providers"]:
        if provider.get("error"):
            lines.append(
                "| {} | {} | — | — | — | — | — | — | — | — | — | — | — | error: {} |".format(
                    provider["provider"], provider.get("version", "?"), provider["error"].replace("|", "\\|")
                )
            )
            continue
        recall = "{}/{}".format(provider["recall"]["passed"], provider["recall"]["total"])
        recovery = provider.get("recovery", {})
        lines.append(
            "| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
                provider["provider"],
                provider.get("version", "?"),
                recall,
                provider.get("stale_leaks", "?"),
                provider.get("isolation_leaks", "?"),
                "pass" if provider.get("privacy", {}).get("canary_rejected") and not provider.get("privacy", {}).get("canary_in_store") else "FAIL",
                "pass" if recovery.get("delete_removed") and recovery.get("delete_recovered") else "FAIL",
                "pass" if recovery.get("restart_recovered") else "FAIL",
                "yes" if recovery.get("import_succeeded") else "no",
                provider.get("timings", {}).get("setup_ms", "?"),
                provider.get("timings", {}).get("query_ms_median", "?"),
                provider.get("context_chars_median", "?"),
                provider.get("store_bytes", "?"),
                "PASS" if provider.get("passed") else "FAIL",
            )
        )
    lines.extend(["", "## Recommendation", "", result["recommendation"], ""])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--provider", action="append", choices=["engram", "ai-memory"])
    parser.add_argument("--engram-bin", default=os.environ.get("ENGRAM_BIN"))
    parser.add_argument("--ai-memory-bin", default=os.environ.get("AI_MEMORY_BIN"))
    parser.add_argument("--artifacts", type=Path, default=DEFAULT_ARTIFACTS)
    parser.add_argument("--cases", type=Path, default=CASES)
    args = parser.parse_args(argv)

    cases = load_cases(args.cases)
    artifacts = args.artifacts.resolve()
    artifacts.mkdir(parents=True, exist_ok=True)
    selected = args.provider or ["engram", "ai-memory"]
    binaries = {
        "engram": args.engram_bin,
        "ai-memory": args.ai_memory_bin,
    }
    results = []
    for name in selected:
        binary = binaries.get(name)
        if not binary:
            results.append(
                {
                    "provider": name,
                    "version": PROVIDER_VERSIONS.get(name, "unknown"),
                    "error": "binary not supplied; pass --{}-bin".format(name),
                    "passed": False,
                }
            )
            continue
        if not Path(binary).is_file():
            results.append(
                {
                    "provider": name,
                    "version": PROVIDER_VERSIONS.get(name, "unknown"),
                    "error": "binary not found: {}".format(binary),
                    "passed": False,
                }
            )
            continue
        print("Running {} ...".format(name), flush=True)
        results.append(run_provider(name, binary, cases, artifacts))

    output = {
        "schema_version": 1,
        "run_at": utc_now(),
        "artifacts": str(artifacts),
        "providers": results,
        "recommendation": recommend(results),
    }
    result_path = artifacts / "result.json"
    result_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = artifacts / "result.md"
    report_path.write_text(format_report(output) + "\n", encoding="utf-8")
    print(format_report(output))
    print("Wrote {} and {}".format(result_path, report_path))
    return 0 if any(result.get("passed") for result in results) else 1


if __name__ == "__main__":
    sys.exit(main())
