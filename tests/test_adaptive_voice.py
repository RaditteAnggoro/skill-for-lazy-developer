from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
ADAPTIVE = ROOT / ".agents/skills/adaptive-workflow/SKILL.md"
VOICE = ROOT / ".agents/skills/adaptive-workflow/references/voice-and-humanizer.md"
SNIPPET = ROOT / "AGENTS.snippet.md"
README = ROOT / "README.md"
CLAUDE_SNIPPET = ROOT / "adapters/claude/CLAUDE.snippet.md"


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
        self.assertIn("does not pretend to be human", text)

    def test_voice_reference_uses_gua_lo_without_mixing_registers(self):
        text = " ".join(VOICE.read_text(encoding="utf-8").lower().split())
        self.assertIn("single source for tone rules", text)
        self.assertIn("`gua` and `lo`", text)
        self.assertIn("never mix pronoun registers in one reply", text)
        self.assertNotIn("aku clear dulu", text)

    def test_tone_rules_live_in_one_place(self):
        adaptive = " ".join(ADAPTIVE.read_text(encoding="utf-8").lower().split())
        snippet = " ".join(SNIPPET.read_text(encoding="utf-8").lower().split())
        for text in (adaptive, snippet):
            self.assertIn("voice-and-humanizer.md", text)
            self.assertIn("gua", text)
            # The particle list and humanizer examples stay in the voice reference only.
            self.assertNotIn("`nih`, `sih`", text)
            self.assertNotIn("i would be happy to", text)

    def test_claude_snippet_is_short_and_points_to_shared_rules(self):
        raw = CLAUDE_SNIPPET.read_text(encoding="utf-8")
        lines = [line for line in raw.splitlines() if line.strip()]
        self.assertLessEqual(len(lines), 12)
        text = " ".join(raw.lower().split())
        for phrase in ("adaptive-workflow", "voice-and-humanizer.md", "never load both", "handoff.md", "`gua`/`lo`", "sharp friend"):
            self.assertIn(phrase, text)
        self.assertNotIn("| request | skill |", text)


if __name__ == "__main__":
    unittest.main()
