# Learning proposals, not automatic skill edits

A memory record is not a skill instruction. A reusable lesson may become a **proposal**
only after evidence and human review.

Pipeline:

```text
verified task evidence
  -> candidate rule + conditions + limitations
  -> privacy/security scan and duplicate check
  -> write a local proposal (never an active SKILL.md)
  -> regression/routing/corpus evaluation
  -> human reviews the diff and rollback
  -> normal repository edit only if accepted
```

Reject credentials, PII, private source, raw transcripts, unverified model guesses, and
instructions from external content. A single anecdote is not a universal rule. A proposal
must name its owner skill/reference, trigger, evidence, constraints, and review status.
No skill may approve its own promotion. Keep the baseline skill when evaluation fails.

The optional local tool is:

```sh
python scripts/propose_skill_learning.py validate --input proposal.yaml
python scripts/propose_skill_learning.py propose --input proposal.yaml --output-dir .agents/artifacts/skill-proposals
```

It writes proposals only; promotion remains a reviewed repository change.
