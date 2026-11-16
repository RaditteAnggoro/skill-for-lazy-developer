from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTIVE = ROOT / ".agents/skills/adaptive-workflow/SKILL.md"
VOICE = ROOT / ".agents/skills/adaptive-workflow/references/voice-and-humanizer.md"
SNIPPET = ROOT / "AGENTS.snippet.md"
README = ROOT / "README.md"


class AdaptiveVoiceTests(unittest.TestCase):
    def test_default_voice_allows_natural_slang_and_code_switching(self):
        text = " ".join(ADAPTIVE.read_text(encoding="utf-8").lower().split())
        for phrase in ("sharp friend", "slang", "code-switching", "formal", "drop the jokes", "never forced"):
            self.assertIn(phrase, text)

    def test_voice_reference_has_casual_and_formal_examples(self):
        text = VOICE.read_text(encoding="utf-8").lower()
        self.assertIn("indonesian casual", text)
        self.assertIn("indonesian formal", text)
        self.assertIn("english casual", text)
        self.assertIn("do not humanize", text)
        self.assertIn("duplicate posting", text)

    def test_snippet_updates_tone_but_stays_within_budget(self):
        text = " ".join(SNIPPET.read_text(encoding="utf-8").lower().split())
        self.assertIn("use slang naturally when it fits", text)
        self.assertLessEqual(len(text.split()), 640)

    def test_readme_describes_threads_style_without_fake_identity(self):
        text = " ".join(README.read_text(encoding="utf-8").lower().split())
        self.assertIn("threads conversation", text)
        self.assertIn("slang naturally", text)
        self.assertIn("doesn't pretend to be human", text)


if __name__ == "__main__":
    unittest.main()
