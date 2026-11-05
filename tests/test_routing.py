from pathlib import Path
import re
import unittest
import json

import yaml

from scripts.validate_skills import FRONTMATTER, read_mapping


ROOT = Path(__file__).resolve().parents[1]
SKILLS_ROOT = ROOT / ".agents/skills"
CASES = ROOT / "tests/routing_cases.yaml"


def installed_skills():
    names = set()
    for entry in SKILLS_ROOT.glob("*/SKILL.md"):
        match = FRONTMATTER.match(entry.read_text(encoding="utf-8"))
        if match:
            names.add(read_mapping(match.group(1))["name"])
    return names


class RoutingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.skills = installed_skills()
        self.cases = yaml.safe_load(CASES.read_text(encoding="utf-8"))["cases"]

    def test_adaptive_router_is_installed(self):
        self.assertIn("adaptive-workflow", self.skills)

    def test_routing_cases_reference_installed_skills(self):
        for case in self.cases:
            selected = [case["primary"], *case.get("supporting", [])]
            self.assertTrue(set(selected) <= self.skills, case["id"])

    def test_routing_cases_use_natural_prompts_and_small_chains(self):
        ids = set()
        for case in self.cases:
            self.assertNotIn(case["id"], ids)
            ids.add(case["id"])
            self.assertNotRegex(case["prompt"], r"\$[a-z0-9-]+")
            self.assertIn(case["kind"], {"direct", "contextual", "negative-control"})
            self.assertIn(case["interaction"], {"automatic", "choice", "question"})
            accepted = case.get("accepted_interactions", [case["interaction"]])
            self.assertIn(case["interaction"], accepted)
            self.assertTrue(set(accepted) <= {"automatic", "choice", "question"})
            if len(accepted) > 1:
                self.assertNotIn("automatic", accepted)
            self.assertLessEqual(len(case.get("supporting", [])), 2)

    def test_corpus_covers_automatic_choice_and_question_routes(self):
        interactions = {case["interaction"] for case in self.cases}
        self.assertEqual(interactions, {"automatic", "choice", "question"})

    def test_corpus_has_a_small_representative_baseline(self):
        self.assertGreaterEqual(len(self.cases), 20)
        kinds = {case["kind"] for case in self.cases}
        self.assertEqual(kinds, {"direct", "contextual", "negative-control"})

    def test_companion_cases_define_bounded_message_expectations(self):
        companion_cases = [case for case in self.cases if "message_expectations" in case]
        self.assertGreaterEqual(len(companion_cases), 8)
        languages = set()
        for case in companion_cases:
            expected = case["message_expectations"]
            languages.add(expected["language"])
            self.assertIn(expected["language"], {"en", "id"})
            self.assertIn(expected["question"], {"required", "forbidden", "optional"})
            self.assertGreaterEqual(expected["max_words"], 20)
            self.assertLessEqual(expected["max_words"], 100)
        self.assertEqual(languages, {"en", "id"})

    def test_every_installed_workflow_has_a_primary_case(self):
        covered = {case["primary"] for case in self.cases}
        self.assertEqual(covered, self.skills)

    def test_consuming_instructions_define_interactive_routing(self):
        text = (ROOT / "AGENTS.snippet.md").read_text(encoding="utf-8")
        for phrase in (
            "adaptive-workflow",
            "High confidence",
            "materially different outcomes",
            "outcome-based",
            "no more than two supporting skills",
        ):
            self.assertIn(phrase, text)

    def test_companion_policy_is_approachable_without_false_identity(self):
        text = (ROOT / "AGENTS.snippet.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split()).casefold()
        for phrase in (
            "trusted, approachable friend",
            "not a formal support agent",
            "comfortable to ask a basic question",
            "do not force slang",
            "Never claim human identity",
        ):
            self.assertIn(phrase.casefold(), normalized)

    def test_router_mentions_every_peer_workflow(self):
        text = (SKILLS_ROOT / "adaptive-workflow/SKILL.md").read_text(encoding="utf-8")
        peers = self.skills - {"adaptive-workflow"}
        missing = sorted(name for name in peers if not re.search(r"`" + re.escape(name) + r"`", text))
        self.assertEqual(missing, [])

    def test_router_avoids_vague_and_redundant_routes(self):
        text = (SKILLS_ROOT / "adaptive-workflow/SKILL.md").read_text(
            encoding="utf-8"
        )
        normalized = " ".join(text.split())
        self.assertIn(
            "neither an identifiable target nor an observed symptom", normalized
        )
        self.assertIn("do not add `lean-senior-engineering`", normalized)

    def test_routing_result_schema_lists_installed_skills(self):
        schema = json.loads((ROOT / "tests/routing_result.schema.json").read_text(encoding="utf-8"))
        primary = set(schema["properties"]["primary"]["enum"])
        supporting = set(schema["properties"]["supporting"]["items"]["enum"])
        self.assertEqual(primary, self.skills)
        self.assertEqual(supporting, self.skills - {"adaptive-workflow"})


if __name__ == "__main__":
    unittest.main()
