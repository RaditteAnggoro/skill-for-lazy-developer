from pathlib import Path
import unittest

import tomli
import yaml

from scripts.render_agent_adapters import rendered, output_path


ROOT = Path(__file__).resolve().parents[1]


class RoleAdapterRenderTests(unittest.TestCase):
    def test_codex_wrappers_parse_and_are_deterministic(self):
        generated = rendered("codex")
        self.assertEqual(len(generated), 4)
        for role_id, text in generated.items():
            path = output_path("codex", role_id)
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            data = tomli.loads(text)
            self.assertEqual(data["name"], role_id)
            self.assertIn("developer_instructions", data)
            self.assertNotIn("model", data)
            self.assertNotIn("sandbox_mode", data)

    def test_claude_wrappers_parse_and_are_read_only(self):
        generated = rendered("claude")
        self.assertEqual(len(generated), 4)
        for role_id, text in generated.items():
            path = output_path("claude", role_id)
            self.assertEqual(path.read_text(encoding="utf-8"), text)
            frontmatter = text.split("---", 2)[1]
            data = yaml.safe_load(frontmatter)
            self.assertEqual(data["name"], role_id)
            self.assertEqual(data["tools"], "Read, Grep, Glob")
            self.assertNotIn("Write", data["tools"])
            self.assertNotIn("Bash", data["tools"])

    def test_wrappers_do_not_home_install_or_include_secrets(self):
        for host in ("codex", "claude"):
            for role_id, text in rendered(host).items():
                self.assertNotIn("~/.codex", text)
                self.assertNotIn("~/.claude", text)
                self.assertNotIn("sk-", text)


if __name__ == "__main__":
    unittest.main()
