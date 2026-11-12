"""Contract examples for tool selection; simulation, not live MCP or agent execution."""
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / '.agents/skills/adaptive-workflow/references/tool-selection.md'


def simulate(case):
    """Tiny test-only host model: count a provider probe only when it could help."""
    native_ok = case['native_ok']
    if native_ok and not case['gain']:
        return 'native', 0
    if case['need'] == 'database' and (case.get('db_env') != 'development'
                                       or not case.get('db_readonly')
                                       or not case.get('db_authorized')):
        return ('native' if native_ok else 'blocked'), 0
    if case['state'] == 'working':
        return case['provider'], 1
    return ('native' if native_ok else 'blocked'), 1


class ToolSelectionContractTests(unittest.TestCase):
    def test_simulated_scenarios(self):
        cases = yaml.safe_load((ROOT / 'tests/tool_selection_cases.yaml').read_text())['cases']
        self.assertEqual(len({case['id'] for case in cases}), len(cases))
        for case in cases:
            with self.subTest(case=case['id']):
                selected, probes = simulate(case)
                self.assertEqual(selected, case['expected'])
                if selected not in ('native', 'blocked'):
                    self.assertEqual(case['state'], 'working')
                if case['id'] in ('small-edit', 'simple-class', 'production-db'):
                    self.assertEqual(probes, 0)

    def test_relevant_capability_states_and_boundaries_are_documented(self):
        text = REFERENCE.read_text(encoding='utf-8').casefold()
        for phrase in ('serena', 'context7', 'playwright', 'chrome devtools', 'dbhub',
                       'github', 'disconnected', 'authentication required', 'disabled',
                       'unsupported', 'missing dependency', 'invocation failure', 'unknown',
                       'read-only credentials', 'side-effecting', 'explain', 'production',
                       'native fallback', 'diagnosis-only', 'not runtime enforcement'):
            self.assertIn(phrase, text, phrase)

    def test_router_loads_reference_selectively(self):
        text = (ROOT / '.agents/skills/adaptive-workflow/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('references/tool-selection.md', text)
        self.assertIn('only when relevant', text)
        self.assertIn('Tool choices do not count as additional skills', text)


if __name__ == '__main__':
    unittest.main()
