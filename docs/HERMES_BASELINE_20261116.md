# Hermes evolution baseline — 2026-11-16

- Repository commit: `938a4af` (`feat: add adaptive tool routing and phase orchestration`)
- Working tree: preserved local `.engram/`, `.serena/`, and an AGENTS backup; excluded
  from the evidence and not modified by this implementation.
- Skills: **17** `SKILL.md` identities, validated.
- Baseline command: `.venv/bin/python scripts/validate_skills.py` → 17 skills valid.
- Baseline tests: `.venv/bin/python -m unittest discover -s tests -q` → **213 passed**.
- Baseline routing/tool/phase/orchestration/packaging/memory/UI tests are preserved.
- Baseline evidence boundaries:
  - several enhancement/model trials print `isolation preflight failed` and are
    intentionally blocked, not passes;
  - no live Claude lifecycle or host role dispatch is established here;
  - UI screenshots are local Chrome/font dependent;
  - static contracts do not prove agent behavior.
- New work must preserve the 17 identities, the single adaptive router, all memory
  adapters, and portable-pack behavior.

Historical enhancement-v3 baseline details are retained in
[ENHANCEMENT_BASELINE.md](ENHANCEMENT_BASELINE.md).
