from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class HostIntegrationStatusTests(unittest.TestCase):
    def test_observed_codex_scope_and_unavailable_host_statuses(self):
        data = yaml.safe_load((ROOT / "tests/host_integration_status.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(data["hosts"]), {"codex", "claude", "dsh"})
        codex = data["hosts"]["codex"]
        self.assertEqual(codex["host_role_dispatch"], "pass")
        self.assertEqual(codex["evidence_level"], "HOST_INTEGRATION")
        self.assertEqual(codex["transport"], "app-server")
        self.assertEqual(codex["role"], "ld-codebase-explorer")
        self.assertEqual(data["hosts"]["claude"]["host_role_dispatch"], "AUTH_REQUIRED")
        self.assertEqual(data["hosts"]["dsh"]["host_role_dispatch"], "UNSUPPORTED")


if __name__ == "__main__":
    unittest.main()
