import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.install_claude_adapter import check, install, rollback, uninstall


FAKE_ENGRAM = r'''#!/usr/bin/env python3
import json, os, sys
log = os.environ.get("FAKE_ENGRAM_LOG", "/tmp/claude-adapter-engram.log")
with open(log, "a", encoding="utf-8") as handle:
    handle.write(json.dumps(sys.argv[1:]) + "\n")
if len(sys.argv) > 1 and sys.argv[1] == "context":
    print("Previous session: RECALL-TOKEN-7319")
elif len(sys.argv) > 1 and sys.argv[1] == "save":
    print("Memory saved")
'''


class ClaudeAdapterTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.home = self.root / "claude-home"
        self.project = self.root / "project"
        (self.project / ".engram").mkdir(parents=True)
        (self.project / ".engram/config.json").write_text('{"project_name":"demo"}\n', encoding="utf-8")
        self.engram = self.root / "bin/engram"
        self.engram.parent.mkdir()
        self.engram.write_text(FAKE_ENGRAM, encoding="utf-8")
        self.engram.chmod(0o755)
        self.log = self.root / "engram.log"

    def runtime(self, command, event):
        runtime = self.home / "companion-memory/memory_runtime.py"
        env = {
            **dict(os.environ),
            "CODEX_MEMORY_CONFIG": str(self.home / "companion-memory/config.json"),
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

    def test_install_check_idempotent_uninstall_and_preserve_settings(self):
        settings = self.home / "settings.json"
        settings.parent.mkdir(parents=True)
        settings.write_text(json.dumps({"hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "echo keep"}]}]}}), encoding="utf-8")
        first = install(self.home, str(self.engram))
        self.assertTrue(first["changed"])
        self.assertTrue(check(self.home, project=self.project)["ok"])
        before = settings.read_text(encoding="utf-8")
        self.assertIn("echo keep", before)
        self.assertIn('"SessionStart"', before)
        second = install(self.home, str(self.engram))
        self.assertFalse(second["changed"])
        self.assertEqual(before, settings.read_text(encoding="utf-8"))
        uninstall(self.home)
        after = settings.read_text(encoding="utf-8")
        self.assertIn("echo keep", after)
        self.assertNotIn("memory_runtime.py", after)

    def test_rollback_restores_edited_settings(self):
        install(self.home, str(self.engram))
        settings = self.home / "settings.json"
        data = json.loads(settings.read_text(encoding="utf-8"))
        data["hooks"]["PreToolUse"] = [{"hooks": [{"type": "command", "command": "echo keep"}]}]
        data["hooks"].pop("Stop")
        settings.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        edited = settings.read_text(encoding="utf-8")
        result = install(self.home, str(self.engram))
        self.assertTrue(result["backup"])
        rollback(self.home, result["backup"])
        self.assertEqual(edited, settings.read_text(encoding="utf-8"))

    def test_check_rejects_missing_engram_and_uninitialized_project(self):
        install(self.home, str(self.engram))
        self.engram.unlink()
        self.assertFalse(check(self.home, project=self.project)["ok"])
        install(self.home, str(self.engram))
        (self.project / ".engram/config.json").unlink()
        self.assertFalse(check(self.home, project=self.project)["ok"])

    def test_runtime_recall_remember_opt_out_handoff_and_fail_open(self):
        install(self.home, str(self.engram))
        started = self.runtime("session-start", {"cwd": str(self.project), "hook_event_name": "SessionStart", "source": "startup"})
        self.assertIn("RECALL-TOKEN-7319", started.stdout)
        remembered = self.runtime("user-prompt", {"cwd": str(self.project), "prompt": "Remember this: Claude uses project memory"})
        self.assertIn("Saved to project memory", remembered.stdout)
        stopped = self.runtime("stop", {"cwd": str(self.project), "last_assistant_message": "Implemented the Claude adapter and verified the hook flow."})
        self.assertEqual(stopped.stdout.strip(), "{}")
        log = self.log.read_text(encoding="utf-8")
        self.assertIn("session_summary", log)
        self.assertIn("handoff/demo", log)
        opted = self.runtime("user-prompt", {"cwd": str(self.project), "prompt": "Do not remember this project"})
        self.assertIn("Memory is disabled", opted.stdout)
        started = self.runtime("session-start", {"cwd": str(self.project), "hook_event_name": "SessionStart", "source": "startup"})
        self.assertEqual(started.stdout.strip(), "")
        config = self.home / "companion-memory/config.json"
        data = json.loads(config.read_text(encoding="utf-8"))
        data["engram_bin"] = str(self.root / "missing")
        config.write_text(json.dumps(data), encoding="utf-8")
        stopped = self.runtime("stop", {"cwd": str(self.project), "last_assistant_message": "A sufficiently long handoff message."})
        self.assertEqual(stopped.returncode, 0)
        self.assertEqual(stopped.stdout.strip(), "{}")


if __name__ == "__main__":
    unittest.main()
