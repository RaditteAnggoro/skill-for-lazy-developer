"""Verify the DSH companion-memory bundle against a real Engram MCP server.

The test is local-only and disposable. It checks the bundle manifest, initializes two
isolated Engram projects, exercises save/search/context/restart/delete, proves project
isolation, and distinguishes provider-native privacy behaviour from the adapter guard.
"""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import yaml


ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "integrations/dsh/companion-memory"
GUARD_TEST = BUNDLE / "test_guard.mjs"


class VerifyError(RuntimeError):
    pass


def _json_from_result(response):
    result = response.get("result") or {}
    content = result.get("content") or []
    if not content:
        raise VerifyError("MCP result has no content")
    text = content[0].get("text", "")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text, "isError": result.get("isError", False)}


class McpSession:
    def __init__(self, binary, cwd, data_dir, home):
        self.binary = Path(binary)
        self.cwd = Path(cwd)
        self.data_dir = Path(data_dir)
        self.home = Path(home)
        self.process = None
        self.next_id = 0
        self.stderr_path = None

    def start(self):
        self.process = subprocess.Popen(
            [str(self.binary), "mcp", "--tools=agent,admin"],
            cwd=str(self.cwd),
            env=self._env(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        self._request(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "dsh-bundle-verifier", "version": "1"},
            },
        )
        self._notify("notifications/initialized")
        return self

    def _env(self):
        env = dict(os.environ)
        env["HOME"] = str(self.home)
        env["ENGRAM_DATA_DIR"] = str(self.data_dir)
        return env

    def _notify(self, method):
        self.process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": method}) + "\n")
        self.process.stdin.flush()

    def _request(self, method, params=None):
        self.next_id += 1
        request = {"jsonrpc": "2.0", "id": self.next_id, "method": method}
        if params is not None:
            request["params"] = params
        self.process.stdin.write(json.dumps(request) + "\n")
        self.process.stdin.flush()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            line = self.process.stdout.readline()
            if not line:
                break
            try:
                response = json.loads(line)
            except json.JSONDecodeError:
                continue
            if response.get("id") == self.next_id:
                if "error" in response:
                    raise VerifyError("MCP error: {}".format(response["error"]))
                return response
        detail = ""
        if self.process.stderr is not None:
            detail = self.process.stderr.read()[-1000:]
        raise VerifyError("MCP request timed out: {} {}".format(method, detail))

    def tool(self, name, arguments):
        response = self._request(
            "tools/call", {"name": name, "arguments": arguments}
        )
        data = _json_from_result(response)
        if (response.get("result") or {}).get("isError"):
            return data, True
        return data, False

    def stop(self):
        if self.process is None:
            return
        self.process.terminate()
        try:
            self.process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.process = None


def _run(command, cwd, env=None, timeout=60):
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise VerifyError(
            "{} failed: {}".format(" ".join(command[:3]), (completed.stderr or completed.stdout)[-1200:])
        )
    return completed


def validate_bundle(path):
    path = Path(path)
    package = json.loads((path / "package.json").read_text(encoding="utf-8"))
    patch = yaml.safe_load((path / "cordis.patch.yml").read_text(encoding="utf-8"))
    rows = patch[0]["insert"] if isinstance(patch, list) else []
    by_id = {row.get("id"): row for row in rows}
    errors = []
    if package.get("dsh", {}).get("bundle", {}).get("patch") != "./cordis.patch.yml":
        errors.append("package is not a DSH bundle")
    mcp = by_id.get("engram-mcp", {}).get("config", {})
    if mcp.get("serverName") != "engram":
        errors.append("MCP serverName must be engram")
    if mcp.get("transport") != "stdio":
        errors.append("MCP transport must be stdio")
    if mcp.get("command") != "engram":
        errors.append("MCP command must be engram")
    if mcp.get("failOnStartupError") is not False:
        errors.append("MCP startup must fail open")
    if "mcp" not in (mcp.get("args") or []):
        errors.append("MCP args must run the mcp subcommand")
    if "engram-guard" not in by_id:
        errors.append("guard plugin row is missing")
    for relative in ("locale/en.json", "icon.svg", "index.js"):
        if not (path / relative).is_file():
            errors.append("missing {}".format(relative))
    return {
        "ok": not errors,
        "errors": errors,
        "mcp": mcp,
        "guard": by_id.get("engram-guard"),
    }


def run_guard_test(node):
    completed = subprocess.run(
        [str(node), str(GUARD_TEST)],
        cwd=str(BUNDLE),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
        check=False,
    )
    return {
        "ok": completed.returncode == 0 and "guard ok" in completed.stdout,
        "stdout": completed.stdout.strip(),
        "stderr": completed.stderr.strip(),
    }


def verify(engram_bin, node_bin, artifacts):
    artifacts = Path(artifacts)
    artifacts.mkdir(parents=True, exist_ok=True)
    root = artifacts / "engram-mcp-verification"
    if root.exists():
        import shutil
        shutil.rmtree(root)
    home = root / "home"
    data = root / "data"
    alpha = root / "alpha"
    beta = root / "beta"
    for path in (home, alpha, beta):
        path.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "HOME": str(home),
        "ENGRAM_DATA_DIR": str(data),
    }
    _run([str(engram_bin), "init", "alpha"], alpha, env)
    _run([str(engram_bin), "init", "beta"], beta, env)

    result = {
        "schema_version": 1,
        "run_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "bundle": validate_bundle(BUNDLE),
        "guard": run_guard_test(node_bin),
        "operations": {},
        "privacy": {},
        "isolation": {},
        "restart": {},
    }

    alpha_session = McpSession(engram_bin, alpha, data, home).start()
    try:
        current, _ = alpha_session.tool("mem_current_project", {})
        result["operations"]["current_project"] = current
        save, _ = alpha_session.tool(
            "mem_save",
            {
                "title": "Alpha memory",
                "content": "Alpha uses token ALPHA-MEMORY-7319 for the adapter check.",
                "type": "decision",
                "capture_prompt": False,
            },
        )
        result["operations"]["save"] = save
        observation_id = save.get("id")
        search, _ = alpha_session.tool(
            "mem_search",
            {"query": "ALPHA-MEMORY-7319", "response_format": "compact"},
        )
        search_ids = [item.get("id") for item in search.get("results", [])]
        result["operations"]["search"] = {
            "ids": search_ids,
            "found": observation_id in search_ids,
        }
        context, _ = alpha_session.tool(
            "mem_context", {"project": "alpha", "max_bytes": 4096}
        )
        result["operations"]["context"] = {
            "contains_token": "ALPHA-MEMORY-7319" in json.dumps(context),
        }

        alpha_session.stop()
        alpha_session = McpSession(engram_bin, alpha, data, home).start()
        restarted, _ = alpha_session.tool(
            "mem_search",
            {"query": "ALPHA-MEMORY-7319", "response_format": "compact"},
        )
        result["restart"] = {
            "found": observation_id
            in [item.get("id") for item in restarted.get("results", [])]
        }

        beta_session = McpSession(engram_bin, beta, data, home).start()
        try:
            beta_leak, _ = beta_session.tool(
                "mem_search",
                {"query": "ALPHA-MEMORY-7319", "response_format": "compact"},
            )
            beta_save, _ = beta_session.tool(
                "mem_save",
                {
                    "title": "Beta memory",
                    "content": "Beta uses token BETA-MEMORY-8421.",
                    "type": "decision",
                    "capture_prompt": False,
                },
            )
            beta_search, _ = beta_session.tool(
                "mem_search",
                {"query": "BETA-MEMORY-8421", "response_format": "compact"},
            )
            result["isolation"]["alpha_token_in_beta"] = bool(
                beta_leak.get("results")
            )
            result["isolation"]["beta_token_found"] = any(
                item.get("id") == beta_save.get("id")
                for item in beta_search.get("results", [])
            )
        finally:
            beta_session.stop()

        alpha_after_beta, _ = alpha_session.tool(
            "mem_search",
            {"query": "BETA-MEMORY-8421", "response_format": "compact"},
        )
        result["isolation"]["beta_token_in_alpha"] = bool(
            alpha_after_beta.get("results")
        )

        canary_save, _ = alpha_session.tool(
            "mem_save",
            {
                "title": "Privacy canary",
                "content": "OPENAI_API_KEY=sk-test-CANARY-7f3a9c2e1d4b8f6a",
                "capture_prompt": False,
            },
        )
        canary_id = canary_save.get("id")
        canary_search, _ = alpha_session.tool(
            "mem_search",
            {"query": "CANARY-7f3a9c2e1d4b8f6a", "response_format": "compact"},
        )
        result["privacy"] = {
            "provider_accepted_canary": bool(canary_search.get("results")),
            "guard_blocks_canary": result["guard"]["ok"],
            "provider_canary_removed": False,
        }
        if canary_id is not None:
            delete, _ = alpha_session.tool(
                "mem_delete",
                {
                    "id": canary_id,
                    "expected_project": "alpha",
                    "hard_delete": True,
                },
            )
            result["privacy"]["delete"] = delete
        after_canary, _ = alpha_session.tool(
            "mem_search",
            {"query": "CANARY-7f3a9c2e1d4b8f6a", "response_format": "compact"},
        )
        result["privacy"]["provider_canary_removed"] = not bool(
            after_canary.get("results")
        )

        delete, _ = alpha_session.tool(
            "mem_delete",
            {
                "id": observation_id,
                "expected_project": "alpha",
                "hard_delete": True,
            },
        )
        deleted, _ = alpha_session.tool(
            "mem_search",
            {"query": "ALPHA-MEMORY-7319", "response_format": "compact"},
        )
        result["operations"]["delete"] = {
            "delete": delete,
            "removed": not bool(deleted.get("results")),
        }
    finally:
        alpha_session.stop()

    checks = {
        "bundle_manifest": result["bundle"]["ok"],
        "guard": result["guard"]["ok"],
        "save_search": result["operations"].get("search", {}).get("found", False),
        "context": result["operations"].get("context", {}).get("contains_token", False),
        "restart": result["restart"].get("found", False),
        "delete": result["operations"].get("delete", {}).get("removed", False),
        "isolation": not result["isolation"].get("alpha_token_in_beta", True)
        and not result["isolation"].get("beta_token_in_alpha", True)
        and result["isolation"].get("beta_token_found", False),
        "privacy_guard": result["privacy"].get("guard_blocks_canary", False)
        and result["privacy"].get("provider_canary_removed", False),
        "fail_open_config": result["bundle"]["mcp"].get("failOnStartupError") is False,
    }
    result["checks"] = checks
    result["ok"] = all(checks.values())
    (artifacts / "dsh-memory-verification.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engram-bin", type=Path, required=True)
    parser.add_argument("--node", type=Path, default=Path("node"))
    parser.add_argument("--artifacts", type=Path, default=ROOT / ".agents/artifacts/dsh-memory")
    args = parser.parse_args(argv)
    if not args.engram_bin.is_file():
        print("Engram binary not found: {}".format(args.engram_bin), file=sys.stderr)
        return 2
    try:
        result = verify(args.engram_bin, args.node, args.artifacts)
    except (OSError, VerifyError, subprocess.TimeoutExpired) as exc:
        print("DSH memory verification failed: {}".format(exc), file=sys.stderr)
        return 1
    print(json.dumps(result["checks"], indent=2))
    print("DSH memory verification: {}".format("PASS" if result["ok"] else "FAIL"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
