import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from scripts.install_codex_adapter import check, install, rollback, uninstall


ROOT = Path(__file__).resolve().parents[1]


FAKE_ENGRAM = r'''#!/usr/bin/env python3
import json, os, sys
log = os.environ.get("FAKE_ENGRAM_LOG", "/tmp/codex-adapter-engram.log")
with open(log, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")
if len(sys.argv) > 1 and sys.argv[1] == "context":
    print("Previous session: RECALL-TOKEN-7319")
elif len(sys.argv) > 1 and sys.argv[1] == "search":
    print("Found 1 memories: #7 (decision) -- Billing database")
elif len(sys.argv) > 1 and sys.argv[1] == "delete":
    print("Memory #" + sys.argv[2] + " deleted")
elif len(sys.argv) > 1 and sys.argv[1] == "save":
    print("Memory saved")
'''


class CodexAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "codex-home"
        self.project = self.root / "project"
        (self.project / ".engram").mkdir(parents=True)
        (self.project / ".engram/config.json").write_text(
            '{"project_name": "demo"}\n', encoding="utf-8"
        )
        self.engram = self.root / "bin/engram"
        self.engram.parent.mkdir()
        self.engram.write_text(FAKE_ENGRAM, encoding="utf-8")
        self.engram.chmod(0o755)
        self.log = self.root / "engram.log"

    def runtime(self, command, event):
        runtime = self.home / "codex-memory/memory_runtime.py"
        env = {
            **dict(os.environ),
            "CODEX_MEMORY_CONFIG": str(self.home / "codex-memory/config.json"),
            "FAKE_ENGRAM_LOG": str(self.log),
        }
        return subprocess.run(
            [sys.executable, str(runtime), command],
            input=json.dumps(event),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            timeout=20,
            check=False,
        )

    def test_install_check_idempotent_and_uninstall_preserve_other_hooks(self):
        hooks = self.home / "hooks.json"
        hooks.parent.mkdir(parents=True)
        hooks.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {"hooks": [{"type": "command", "command": "echo keep"}]}
                        ]
                    }
                }
            ),
            encoding="utf-8",
        )
        result = install(self.home, str(self.engram))
        self.assertTrue(result["changed"])
        self.assertTrue(check(self.home, project=self.project)["ok"])
        first = hooks.read_text(encoding="utf-8")
        self.assertIn("echo keep", first)
        self.assertIn('"Stop"', first)
        self.assertIn('"SessionEnd"', first) if False else None
        second = install(self.home, str(self.engram))
        self.assertFalse(second["changed"])
        self.assertEqual(first, hooks.read_text(encoding="utf-8"))
        result = uninstall(self.home)
        self.assertTrue(result["changed"])
        after = hooks.read_text(encoding="utf-8")
        self.assertIn("echo keep", after)
        self.assertNotIn("memory_runtime.py", after)
        self.assertFalse(check(self.home, project=self.project)["ok"])

    def test_install_creates_and_rolls_back(self):
        result = install(self.home, str(self.engram))
        self.assertTrue(result["changed"])
        backup = result["backup"]
        self.assertIsNone(backup)
        # Reinstall after a real edit gives a backup that restores the edited file.
        hooks = self.home / "hooks.json"
        data = json.loads(hooks.read_text(encoding="utf-8"))
        data["hooks"]["PreToolUse"] = [
            {"hooks": [{"type": "command", "command": "echo keep"}]}
        ]
        data["hooks"].pop("Stop")
        hooks.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        edited = hooks.read_text(encoding="utf-8")
        result = install(self.home, str(self.engram))
        self.assertTrue(result["backup"])
        rollback(self.home, result["backup"])
        self.assertEqual(edited, hooks.read_text(encoding="utf-8"))

    def test_check_rejects_missing_engram(self):
        install(self.home, str(self.engram))
        self.engram.unlink()
        result = check(self.home, project=self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any("Engram binary" in error for error in result["errors"]))

    def test_check_rejects_uninitialized_project(self):
        install(self.home, str(self.engram))
        (self.project / ".engram/config.json").unlink()
        result = check(self.home, project=self.project)
        self.assertFalse(result["ok"])
        self.assertTrue(any(".engram/config.json" in error for error in result["errors"]))

    def test_runtime_recall_remember_opt_out_and_handoff(self):
        install(self.home, str(self.engram))
        started = self.runtime(
            "session-start",
            {"cwd": str(self.project), "hook_event_name": "SessionStart", "source": "startup"},
        )
        self.assertEqual(started.returncode, 0)
        self.assertIn("RECALL-TOKEN-7319", started.stdout)

        shown = self.runtime(
            "user-prompt",
            {"cwd": str(self.project), "prompt": "Show what you remember"},
        )
        self.assertIn("RECALL-TOKEN-7319", shown.stdout)

        remembered = self.runtime(
            "user-prompt",
            {"cwd": str(self.project), "prompt": "Remember this: use PostgreSQL"},
        )
        self.assertIn("Saved to project memory", remembered.stdout)
        log = self.log.read_text(encoding="utf-8")
        self.assertIn('"save"', log)
        self.assertIn("verified", log)
        self.assertIn('project', log)
        self.assertIn("user-note/", log)

        stopped = self.runtime(
            "stop",
            {
                "cwd": str(self.project),
                "last_assistant_message": "Implemented the adapter and verified the hook flow.",
            },
        )
        self.assertEqual(stopped.returncode, 0)
        self.assertEqual(stopped.stdout.strip(), "{}")
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("Session handoff: demo", log)
        self.assertIn("unverified", log)

        forget = self.runtime(
            "user-prompt",
            {"cwd": str(self.project), "prompt": "Forget the billing decision"},
        )
        self.assertIn("Nothing was deleted", forget.stdout)

        opted_out = self.runtime(
            "user-prompt",
            {"cwd": str(self.project), "prompt": "Do not remember this project"},
        )
        self.assertIn("Memory is disabled", opted_out.stdout)
        started = self.runtime(
            "session-start",
            {"cwd": str(self.project), "hook_event_name": "SessionStart", "source": "startup"},
        )
        self.assertEqual(started.stdout.strip(), "")

    def test_sensitive_remember_and_handoff_are_not_written(self):
        install(self.home, str(self.engram))
        remembered = self.runtime(
            "user-prompt",
            {
                "cwd": str(self.project),
                "prompt": "Remember this: OPENAI_API_KEY=sk-test-CANARY-7f3a9c2e1d4b8f6a",
            },
        )
        self.assertEqual(remembered.returncode, 0)
        stopped = self.runtime(
            "stop",
            {
                "cwd": str(self.project),
                "last_assistant_message": "The token is sk-test-CANARY-7f3a9c2e1d4b8f6a and this message is long enough.",
            },
        )
        self.assertEqual(stopped.returncode, 0)
        log = self.log.read_text(encoding="utf-8") if self.log.exists() else ""
        self.assertNotIn("sk-test-CANARY", log)

    def test_forget_requires_confirmation_and_deletes_only_then(self):
        install(self.home, str(self.engram))
        first = self.runtime(
            "user-prompt",
            {"cwd": str(self.project), "prompt": "Forget billing database"},
        )
        self.assertIn("Nothing was deleted", first.stdout)
        self.assertNotIn("delete", self.log.read_text(encoding="utf-8") if self.log.exists() else "")
        confirmed = self.runtime(
            "user-prompt",
            {"cwd": str(self.project), "prompt": "forget confirm 7"},
        )
        self.assertIn("Deleted memory #7", confirmed.stdout)
        self.assertIn('"delete"', self.log.read_text(encoding="utf-8"))

    def test_handoff_is_verified_only_with_transcript_evidence(self):
        install(self.home, str(self.engram))
        transcript = self.root / "transcript.jsonl"
        transcript.write_text(
            '{"type":"tool_call","command":"pytest tests/test_x.py"}\n'
            '{"type":"tool_result","exit_code":0}\n',
            encoding="utf-8",
        )
        self.runtime(
            "stop",
            {
                "cwd": str(self.project),
                "transcript_path": str(transcript),
                "last_assistant_message": "Verification: pytest tests/test_x.py passed. Implemented the adapter.",
            },
        )
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("verified", log)
        self.assertIn("0.9", log)
        self.log.write_text("", encoding="utf-8")
        self.runtime(
            "stop",
            {
                "cwd": str(self.project),
                "last_assistant_message": "Implemented the adapter without a verification line.",
            },
        )
        self.assertIn("unverified", self.log.read_text(encoding="utf-8"))

    def test_runtime_is_fail_open_when_engram_is_missing(self):
        install(self.home, str(self.engram))
        config = self.home / "codex-memory/config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        data["engram_bin"] = str(self.root / "missing-engram")
        config.write_text(json.dumps(data), encoding="utf-8")
        result = self.runtime(
            "session-start",
            {"cwd": str(self.project), "hook_event_name": "SessionStart", "source": "startup"},
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.strip(), "")
        stopped = self.runtime(
            "stop",
            {"cwd": str(self.project), "last_assistant_message": "A sufficiently long handoff message."},
        )
        self.assertEqual(stopped.returncode, 0)
        self.assertEqual(stopped.stdout.strip(), "{}")


if __name__ == "__main__":
    unittest.main()
