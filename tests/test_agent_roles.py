from pathlib import Path
import unittest

import yaml

from scripts.build_release import PATHS
from scripts.validate_roles import EXPECTED, load_roles, validate_all, validate_role


ROOT = Path(__file__).resolve().parents[1]
ROLES = ROOT / ".agents/roles"


class AgentRoleTests(unittest.TestCase):
    def test_four_roles_validate_strictly(self):
        self.assertEqual(validate_all(ROLES), [])
        self.assertEqual({data["id"] for _, data in load_roles(ROLES)}, EXPECTED)

    def test_roles_are_read_only_and_do_not_overlap_capabilities(self):
        for path, role in load_roles(ROLES):
            self.assertFalse(role["write_permission"], path)
            self.assertFalse(role["external_side_effects"], path)
            denied = set(role["denied_capabilities"])
            self.assertIn("filesystem-write", denied)
            self.assertIn("remote-push", denied)
            self.assertFalse((set(role["allowed_capabilities"]) | set(role["optional_capabilities"])) & denied)

    def test_invalid_fixture_is_rejected_without_crashing(self):
        invalid = yaml.safe_load((ROOT / "tests/roles/invalid-role.yaml").read_text(encoding="utf-8"))
        errors = validate_role(invalid, "invalid-role.yaml")
        self.assertTrue(errors)
        self.assertTrue(any("write_permission" in error for error in errors))
        self.assertTrue(any("unknown fields" in error for error in errors))

    def test_unknown_keys_are_rejected(self):
        role = load_roles(ROLES)[0][1]
        broken = dict(role)
        broken["surprise"] = True
        self.assertTrue(validate_role(broken, "broken.yaml"))

    def test_output_contract_and_fallback_are_explicit(self):
        for _, role in load_roles(ROLES):
            self.assertTrue(role["fallback"])
            self.assertTrue(role["output_contract"]["cite_source_locations"])
            self.assertTrue(role["output_contract"]["sections"])
            self.assertIn("BLOCKED", role["output_contract"]["status"])

    def test_release_includes_role_layer_and_wrappers(self):
        for relative in (".agents/roles", ".codex", ".claude"):
            self.assertIn(relative, PATHS)

    def test_role_docs_explain_policy_is_not_sandbox(self):
        text = " ".join((ROLES / "README.md").read_text(encoding="utf-8").lower().split())
        self.assertIn("not a sandbox", text)
        self.assertIn("single-agent fallback", text)
        self.assertIn("execution_mode=single-agent-role-guided", text)


if __name__ == "__main__":
    unittest.main()
