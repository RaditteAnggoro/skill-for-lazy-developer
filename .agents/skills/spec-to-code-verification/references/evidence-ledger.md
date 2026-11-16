# Grounded evidence ledger

Use the source's exact identifiers and wording where possible. Each row carries:

| Field | Meaning |
| --- | --- |
| `requirement_id` | Stable ID from the source |
| `source_ref` | File, section, line, or URL |
| `implementation_refs` | Code or contract locations |
| `test_refs` | Executed checks and results |
| `status` | COVERED, PARTIAL, MISSING, UNCLEAR, NOT_TESTED, NOT_APPLICABLE |
| `confidence` | high, medium, low, or unknown |
| `notes` | Assumptions, conflicts, gaps |

Keep source statement, verified implementation, inference, pending business decision, and
test status separate. A screenshot is not backend proof. A `@Transactional` annotation is
not proof of idempotency; inspect deduplication/tests. Never turn missing vendor details
into invented requirements. Do not copy proprietary source into public fixtures.
