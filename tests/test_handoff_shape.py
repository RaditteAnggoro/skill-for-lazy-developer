"""Policy and scorer checks for the final answer shape, resume, and compaction rules."""

from pathlib import Path
import unittest

import yaml

from scripts.run_routing_evals import load_cases, score_final_answer


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".agents/skills"
ADAPTIVE = SKILLS / "adaptive-workflow/SKILL.md"
ORCHESTRATION = SKILLS / "adaptive-workflow/references/phase-orchestration.md"
RESEARCH = SKILLS / "research-plan-implement/SKILL.md"
HANDOFF = SKILLS / "research-plan-implement/references/handoff-template.md"
FINAL_CASES = ROOT / "tests/final_answer_cases.yaml"


def normalized(path):
    return " ".join(path.read_text(encoding="utf-8").split()).casefold()


class FinalAnswerShapeTests(unittest.TestCase):
    def test_scorer_matches_every_sample_answer(self):
        cases = yaml.safe_load(FINAL_CASES.read_text(encoding="utf-8"))["cases"]
        self.assertGreaterEqual(len(cases), 6)
        for case in cases:
            differences = score_final_answer(case["answer"], case["expectations"])
            with self.subTest(case=case["id"]):
                if case["valid"]:
                    self.assertEqual(differences, [])
                else:
                    self.assertTrue(differences)
                    self.assertTrue(any(case["reason"] in item for item in differences))

    def test_router_limits_trace_table_to_multi_phase_work(self):
        text = normalized(ADAPTIVE)
        self.assertIn("phase trace table only when the task actually ran two or more phases", text)
        self.assertIn("single-phase task", text)
        self.assertIn("one evidence sentence instead of a table", text)
        self.assertNotIn("close with the phase trace, not only a success sentence", text)

    def test_router_puts_pending_user_action_last(self):
        text = normalized(ADAPTIVE)
        order = [text.index(label) for label in ("**result:**", "**evidence:**", "**excluded:**", "**waiting on the user:**")]
        self.assertEqual(order, sorted(order))
        self.assertIn("as the last line", text)

    def test_research_skill_matches_trace_and_resume_rules(self):
        text = normalized(RESEARCH)
        self.assertIn("task ran two or more phases", text)
        self.assertIn("single-phase task gets one evidence sentence instead of a table", text)
        self.assertIn("every phase boundary", text)
        self.assertIn("without re-routing", text)

    def test_handoff_template_records_phase_status(self):
        text = normalized(HANDOFF)
        self.assertIn("id, primary skill, status, and closing evidence", text)
        self.assertIn("next phase id", text)


class ResumeAndCompactionTests(unittest.TestCase):
    def test_router_resumes_short_continue_commands_without_rerouting(self):
        text = normalized(ADAPTIVE)
        for phrase in ("`lanjut`", "`gas`", "`next`", "active handoff record", "do not re-route and do not ask"):
            self.assertIn(phrase, text)

    def test_orchestration_reference_survives_compaction(self):
        text = normalized(ORCHESTRATION)
        for phrase in ("compaction", "every phase boundary", "phase id", "status", "evidence", "do not re-route the task and do not ask"):
            self.assertIn(phrase, text)

    def test_router_links_orchestration_reference_instead_of_inlining_it(self):
        raw = ADAPTIVE.read_text(encoding="utf-8")
        self.assertIn("references/phase-orchestration.md", raw)
        self.assertNotIn("Typical mixed backend/UI sequence", raw)
        self.assertLess(len(raw.encode("utf-8")), 13000)

    def test_resume_routing_cases_ship_a_handoff_file(self):
        resume = [case for case in load_cases() if case["id"].startswith("id-casual-resume")]
        self.assertEqual(len(resume), 2)
        for case in resume:
            files = case["workspace_files"]
            self.assertTrue(any(path.endswith("handoff.md") for path in files), case["id"])
            self.assertEqual(case["interaction"], "automatic")
            self.assertEqual(case["message_expectations"]["question"], "forbidden")


class HostSkillOverlapTests(unittest.TestCase):
    def test_router_defers_to_named_host_skills_only(self):
        text = normalized(ADAPTIVE)
        self.assertIn("when the user names a host skill or command, follow it", text)
        self.assertIn("otherwise use this pack", text)
        self.assertIn("never load both for the same task", text)


class CasualIndonesianCorpusTests(unittest.TestCase):
    def test_corpus_has_everyday_indonesian_requests(self):
        cases = [
            case for case in load_cases()
            if case.get("message_expectations", {}).get("language") == "id"
        ]
        self.assertGreaterEqual(len(cases), 10)
        self.assertTrue(all(case["message_expectations"].get("table") == "forbidden"
                            for case in cases if case["id"].startswith("id-casual")))


if __name__ == "__main__":
    unittest.main()
