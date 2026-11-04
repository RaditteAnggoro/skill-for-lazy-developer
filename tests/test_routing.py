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
            self.assertIn(case["interaction"], {"automatic", "choice", "question"})
            self.assertLessEqual(len(case.get("supporting", [])), 2)

    def test_corpus_covers_automatic_choice_and_question_routes(self):
        interactions = {case["interaction"] for case in self.cases}
        self.assertEqual(interactions, {"automatic", "choice", "question"})

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

    def test_router_mentions_every_peer_workflow(self):
        text = (SKILLS_ROOT / "adaptive-workflow/SKILL.md").read_text(encoding="utf-8")
        peers = self.skills - {"adaptive-workflow"}
        missing = sorted(name for name in peers if not re.search(r"`" + re.escape(name) + r"`", text))
        self.assertEqual(missing, [])

    def test_routing_result_schema_lists_installed_skills(self):
        schema = json.loads((ROOT / "tests/routing_result.schema.json").read_text(encoding="utf-8"))
        primary = set(schema["properties"]["primary"]["enum"])
        supporting = set(schema["properties"]["supporting"]["items"]["enum"])
        self.assertEqual(primary, self.skills)
        self.assertEqual(supporting, self.skills - {"adaptive-workflow"})


if __name__ == "__main__":
    unittest.main()
