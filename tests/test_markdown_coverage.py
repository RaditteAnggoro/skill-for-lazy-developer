from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {
    ".git", ".venv", "venv", "node_modules", ".next", "dist", "artifacts",
    ".agents/artifacts", ".engram", ".serena", "__pycache__", ".npm-cache",
}
# Files that are intentionally standalone/generated and are covered by dedicated tests.
STANDALONE = (
    ".github/",
    ".claude/agents/",
    "tests/enhancement/fixtures/",
    "tests/fixtures/security/",
    "tests/roles/",
    "tests/ui/",
    # Developer evidence is intentionally not linked from the public README.
    "docs/VALIDATION.md",
)


def distributed_markdown():
    files = []
    for path in ROOT.rglob("*.md"):
        relative = path.relative_to(ROOT)
        if any(part in EXCLUDED for part in relative.parts):
            continue
        files.append(relative.as_posix())
    return sorted(files)


def inbound(relative):
    name = Path(relative).name
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.relative_to(ROOT).as_posix() == relative:
            continue
        relative_path = path.relative_to(ROOT)
        if any(part in EXCLUDED for part in relative_path.parts):
            continue
        if path.suffix not in {".md", ".py", ".yaml", ".yml", ".json", ".js", ".mjs", ".toml", ".txt"}:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if relative in text or name in text:
            return relative_path.as_posix()
    return None


class MarkdownCoverageTests(unittest.TestCase):
    def test_distributed_markdown_is_linked_or_explicit_standalone(self):
        files = distributed_markdown()
        self.assertGreaterEqual(len(files), 90)
        orphans = []
        for relative in files:
            if relative.startswith(STANDALONE):
                continue
            if Path(relative).name in {"README.md", "AGENTS.md", "AGENTS.snippet.md", "CONTRIBUTING.md", "NOTICE.md", "SECURITY.md", "CHANGELOG.md", "THIRD_PARTY_NOTICES.md"}:
                continue
            if inbound(relative) is None:
                orphans.append(relative)
        self.assertEqual(orphans, [])

    def test_every_skill_identity_has_a_skill_file(self):
        skills = list((ROOT / ".agents/skills").glob("*/SKILL.md"))
        self.assertEqual(len(skills), 17)

    def test_phase_evidence_docs_are_linked(self):
        report = (ROOT / "docs/HERMES_IMPLEMENTATION_REPORT.md").read_text(encoding="utf-8")
        for name in ("PHASE1_HERMES_EVIDENCE.md", "PHASE2_3_EVIDENCE.md", "PHASE4_EVIDENCE.md", "PHASE5_EVIDENCE.md", "PHASE6_EVIDENCE.md"):
            self.assertIn(name, report)


if __name__ == "__main__":
    unittest.main()
