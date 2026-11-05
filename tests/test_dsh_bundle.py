from pathlib import Path
import json
import shutil
import subprocess
import unittest

from scripts.verify_dsh_memory_bundle import BUNDLE, validate_bundle


class DshMemoryBundleTests(unittest.TestCase):
    def test_bundle_manifest_is_a_loadable_dsh_bundle(self):
        result = validate_bundle(BUNDLE)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["mcp"]["serverName"], "engram")
        self.assertEqual(result["mcp"]["transport"], "stdio")
        self.assertEqual(result["mcp"]["command"], "engram")
        self.assertFalse(result["mcp"]["failOnStartupError"])
        self.assertIn("mcp", result["mcp"]["args"])

    def test_bundle_has_guard_policy_and_display_metadata(self):
        package = json.loads((BUNDLE / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["dsh"]["bundle"]["patch"], "./cordis.patch.yml")
        self.assertIn("./locale/*.json", package["exports"])
        self.assertIn("./icon", package["exports"])
        self.assertTrue((BUNDLE / "index.js").is_file())
        text = (BUNDLE / "index.js").read_text(encoding="utf-8")
        self.assertIn("tools.guard", text)
        self.assertIn("systemPrompt.section", text)
        self.assertIn("mem_save", text)

    @unittest.skipUnless(shutil.which("node"), "node is unavailable")
    def test_lifecycle_hooks_recall_remember_optout_and_handoff(self):
        completed = subprocess.run(
            [shutil.which("node"), str(BUNDLE / "test_lifecycle.mjs")],
            cwd=str(BUNDLE),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=60,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("lifecycle ok", completed.stdout)

    @unittest.skipUnless(shutil.which("node"), "node is unavailable")
    def test_guard_blocks_sensitive_writes(self):
        completed = subprocess.run(
            [shutil.which("node"), str(BUNDLE / "test_guard.mjs")],
            cwd=str(BUNDLE),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("guard ok", completed.stdout)

    def test_bundle_does_not_contain_obvious_secrets(self):
        for path in BUNDLE.rglob("*"):
            if path.is_file() and path.suffix in {".js", ".json", ".yml", ".yaml", ".md", ".svg"}:
                text = path.read_text(encoding="utf-8", errors="replace")
                self.assertNotIn("sk-test-CANARY", text)
                self.assertNotIn("BEGIN PRIVATE KEY", text)


if __name__ == "__main__":
    unittest.main()
