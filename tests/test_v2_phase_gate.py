from pathlib import Path
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "tests/v2_phase_gate.yaml"


class V2PhaseGateTests(unittest.TestCase):
    def setUp(self):
        self.data = yaml.safe_load(GATE.read_text(encoding="utf-8"))
        self.phases = self.data["phases"]
        self.capabilities = self.data["capabilities"]

    def test_phase_ids_are_ordered_and_dependencies_are_sequential(self):
        ids = [phase["id"] for phase in self.phases]
        self.assertEqual(ids, list(range(8)))
        for phase in self.phases:
            expected = [] if phase["id"] == 0 else [phase["id"] - 1]
            self.assertEqual(phase["depends_on"], expected)

    def test_only_current_or_completed_phases_are_unblocked(self):
        current = self.data["current_phase"]
        for phase in self.phases:
            if phase["id"] < current:
                self.assertEqual(phase["status"], "complete")
            elif phase["id"] == current:
                self.assertIn(phase["status"], {"in-progress", "complete"})
            else:
                self.assertIn(phase["status"], {"blocked", "complete"})

    def test_phase_zero_has_explicit_quality_gates(self):
        phase = self.phases[0]
        self.assertEqual(
            set(phase["required_checks"]),
            {"repository-validator", "unit-tests", "routing-model-evaluation"},
        )
        self.assertGreaterEqual(len(phase["exit_criteria"]), 4)

    def test_current_phase_has_explicit_quality_gates(self):
        phase = self.phases[self.data["current_phase"]]
        self.assertGreaterEqual(len(phase["required_checks"]), 4)
        self.assertGreaterEqual(len(phase["exit_criteria"]), 4)

    def test_always_on_companion_policy_stays_within_context_budget(self):
        text = (ROOT / "AGENTS.snippet.md").read_text(encoding="utf-8")
        section = text.split("## Working relationship", 1)[1]
        words = section.split()
        self.assertLessEqual(len(words), 200)
        self.assertGreaterEqual(len(words), 100)
        self.assertLessEqual(len(text.split()), 640)

    def test_capabilities_have_bounded_ownership(self):
        ids = set()
        phase_ids = {phase["id"] for phase in self.phases}
        allowed = {
            "existing-skill",
            "extend-skill",
            "new-skill",
            "optional-domain-skill",
            "supporting-reference",
            "core-policy",
            "runtime-service",
            "runtime-integration",
            "evaluation-harness",
        }
        for capability in self.capabilities:
            self.assertNotIn(capability["id"], ids)
            ids.add(capability["id"])
            self.assertIn(capability["phase"], phase_ids)
            self.assertIn(capability["disposition"], allowed)
            for field in ("owner", "trigger", "non_goal"):
                self.assertIsInstance(capability[field], str)
                self.assertTrue(capability[field].strip())

    def test_runtime_concerns_do_not_become_user_facing_skills(self):
        runtime_ids = {
            "memory-contract",
            "seamless-memory-runtime",
            "continuous-learning",
            "context-budget",
            "tool-output-filtering",
        }
        by_id = {item["id"]: item for item in self.capabilities}
        for capability_id in runtime_ids:
            self.assertEqual(by_id[capability_id]["disposition"], "runtime-service")

    def test_every_installed_skill_has_capability_ownership(self):
        installed = {
            path.parent.name
            for path in (ROOT / ".agents/skills").glob("*/SKILL.md")
        }
        skill_dispositions = {
            "existing-skill", "extend-skill", "new-skill", "optional-domain-skill"
        }
        owned = {
            item["owner"]
            for item in self.capabilities
            if item["disposition"] in skill_dispositions
        }
        self.assertTrue(installed <= owned)

    def test_phase_two_has_memory_contract_and_bakeoff_evidence(self):
        phase = self.phases[2]
        self.assertGreaterEqual(self.data["current_phase"], 2)
        self.assertEqual(phase["status"], "complete")
        required = set(phase["required_checks"])
        self.assertTrue(
            {"memory-contract-tests", "provider-bakeoff", "privacy-recovery"}
            <= required
        )
        for relative in (
            "docs/V2_MEMORY_CONTRACT.md",
            "docs/V2_PHASE2_EVIDENCE.md",
            "docs/schemas/memory_record.schema.json",
            "docs/schemas/memory_bundle.schema.json",
            "tests/memory_bakeoff_cases.yaml",
            "tests/memory_bakeoff_evidence.yaml",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_phase_two_records_two_passing_provider_trials(self):
        evidence = yaml.safe_load(
            (ROOT / "tests/memory_bakeoff_evidence.yaml").read_text(encoding="utf-8")
        )
        providers = {item["name"]: item for item in evidence["providers"]}
        self.assertEqual(set(providers), {"engram", "ai-memory"})
        for provider in providers.values():
            self.assertEqual(provider["gate"], "pass")
            self.assertEqual(provider["recall_passed"], provider["recall_total"])
            self.assertEqual(provider["stale_leaks"], 0)
            self.assertEqual(provider["isolation_leaks"], 0)
            self.assertEqual(provider["privacy"], "pass")
            self.assertEqual(provider["restart_recovery"], "pass")
            self.assertEqual(provider["delete_recovery"], "pass")
        self.assertEqual(evidence["recommendation"]["provider"], "engram")

    def test_dsh_adapter_is_groundwork_for_completed_phase_three(self):
        self.assertEqual(self.phases[3]["status"], "complete")
        for relative in (
            "docs/ADAPTERS.md",
            "adapters/dsh/AGENTS.dsh.md",
            "scripts/dsh_adapter.py",
            "scripts/run_dsh_routing_evals.py",
            "integrations/dsh/companion-memory/package.json",
            "integrations/dsh/companion-memory/cordis.patch.yml",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_phase_three_has_a_codex_vertical_slice(self):
        self.assertGreaterEqual(self.data["current_phase"], 3)
        phase = self.phases[3]
        self.assertEqual(phase["status"], "complete")
        self.assertEqual(phase["verification"], "verified-with-deferred-claude")
        self.assertIn("claude-live-verification", phase["deferred"])
        required = set(phase["required_checks"])
        self.assertTrue(
            {
                "codex-hook-installer",
                "codex-lifecycle-evaluation",
                "dsh-hook-installer",
                "dsh-lifecycle-evaluation",
                "claude-hook-installer",
                "claude-hook-contract",
                "fail-open",
                "user-controls",
                "memory-privacy",
            }
            <= required
        )
        for relative in (
            "integrations/codex/memory_runtime.py",
            "scripts/install_codex_adapter.py",
            "tests/test_codex_adapter.py",
            "integrations/dsh/companion-memory/test_lifecycle.mjs",
            "scripts/install_claude_adapter.py",
            "adapters/claude/README.md",
            "tests/test_claude_adapter.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_memory_runtime_is_not_repackaged_as_a_skill(self):
        self.assertFalse(
            (ROOT / ".agents/skills/persistent-project-memory").exists()
        )
        self.assertFalse((ROOT / ".agents/skills/context-budget-manager").exists())
        by_id = {item["id"]: item for item in self.capabilities}
        self.assertEqual(by_id["memory-contract"]["disposition"], "runtime-service")
        self.assertEqual(
            by_id["memory-provider-bakeoff"]["disposition"], "evaluation-harness"
        )

    def test_phase_four_retains_evidence_but_waits_for_runtime_verification(self):
        self.assertGreaterEqual(self.data["current_phase"], 4)
        phase = self.phases[4]
        self.assertEqual(phase["status"], "in-progress")
        self.assertEqual(phase["verification"], "partial")
        self.assertIn("runtime", phase["verification_reason"])
        self.assertGreaterEqual(len(phase["required_checks"]), 4)
        criteria = " ".join(phase["exit_criteria"]).lower()
        self.assertIn("30 percent", criteria)
        self.assertIn("correctness", criteria)
        self.assertIn("raw evidence", criteria)
        self.assertTrue((ROOT / "tests/token_optimization_evidence.yaml").is_file())
        self.assertTrue((ROOT / "tests/test_context_optimizer.py").is_file())

    def test_phase_five_is_complete_with_visual_interaction_evidence(self):
        phase = self.phases[5]
        self.assertEqual(phase["status"], "complete")
        self.assertEqual(phase["verification"], "verified")
        self.assertGreaterEqual(len(phase["required_checks"]), 8)
        criteria = " ".join(phase["exit_criteria"]).lower()
        self.assertIn("screenshots", criteria)
        self.assertIn("keyboard", criteria)
        self.assertIn("not only a successful build", criteria)
        for relative in (
            "tests/ui/evidence.yaml",
            "tests/test_ui_phase.py",
            "tests/ui/fixtures/plain/index.html",
            "tests/ui/fixtures/react/src/main.jsx",
            "tests/ui/fixtures/next/app/page.jsx",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_phase_six_has_domain_spec_security_and_transaction_evidence(self):
        phase = self.phases[6]
        self.assertEqual(phase["status"], "complete")
        self.assertEqual(phase["verification"], "verified")
        self.assertGreaterEqual(len(phase["required_checks"]), 7)
        criteria = " ".join(phase["exit_criteria"]).lower()
        self.assertIn("never auto-installed", criteria)
        self.assertIn("unsafe fixtures are rejected", criteria)
        for relative in (
            "tests/phase6_evidence.yaml",
            "tests/test_phase6.py",
            "scripts/run_phase6_evals.py",
            "scripts/scan_skill_security.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_phase_seven_closes_cross_agent_packaging(self):
        phase = self.phases[7]
        self.assertEqual(phase["status"], "complete")
        self.assertEqual(phase["verification"], "verified")
        self.assertGreaterEqual(len(phase["required_checks"]), 8)
        criteria = " ".join(phase["exit_criteria"]).lower()
        self.assertIn("rollback restores", criteria)
        self.assertIn("path traversal", criteria)
        self.assertIn("license inventory", criteria)
        for relative in (
            "tests/phase7_evidence.yaml",
            "tests/test_phase7.py",
            "scripts/package_skill_pack.py",
            "docs/PORTABLE_PACK.md",
            "adapters/portable/README.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_overlap_decisions_reference_known_capabilities_once(self):
        capability_ids = {item["id"] for item in self.capabilities}
        pairs = set()
        for overlap in self.data["overlap_decisions"]:
            self.assertIn(overlap["left"], capability_ids)
            self.assertIn(overlap["right"], capability_ids)
            pair = tuple(sorted((overlap["left"], overlap["right"])))
            self.assertNotIn(pair, pairs)
            pairs.add(pair)
            self.assertTrue(overlap["decision"].strip())


if __name__ == "__main__":
    unittest.main()
