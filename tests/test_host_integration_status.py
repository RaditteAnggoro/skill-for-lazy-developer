from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


class HostIntegrationStatusTests(unittest.TestCase):
    def test_unavailable_hosts_are_not_passed(self):
        data = yaml.safe_load((ROOT / "tests/host_integration_status.yaml").read_text(encoding="utf-8"))
        self.assertEqual(set(data["hosts"]), {"codex", "claude", "dsh"})
        self.assertEqual(data["hosts"]["codex"]["host_role_dispatch"], "NOT_RUN")
        self.assertEqual(data["hosts"]["claude"]["host_role_dispatch"], "AUTH_REQUIRED")
        self.assertEqual(data["hosts"]["dsh"]["host_role_dispatch"], "UNSUPPORTED")
        for host, status in data["hosts"].items():
            self.assertNotEqual(status["host_role_dispatch"], "pass", host)


if __name__ == "__main__":
    unittest.main()
