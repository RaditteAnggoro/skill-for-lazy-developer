import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import unittest

from scripts.memory_contract import (
    ContractError,
    apply_repository_check,
    bundle_checksum,
    make_bundle,
    parse_record,
    render_context_block,
    render_record,
    scan_sensitive,
    select_context,
    validate_bundle,
    validate_record,
)


def record(record_id="dec-billing-db", **overrides):
    value = {
        "schema_version": 1,
        "id": record_id,
        "kind": "decision",
        "topic": "billing/database",
        "scope": {"workspace": "phase2", "project": "billing-alpha"},
        "title": "Billing database",
        "content": "Billing uses PostgreSQL 16.",
        "provenance": {
            "source": "user",
            "observed_at": "2026-11-05T03:00:00Z",
            "evidence": ["Approved in the billing design review"],
        },
        "confidence": 0.9,
        "status": "active",
        "trust": "verified",
        "created_at": "2026-11-05T03:00:00Z",
        "updated_at": "2026-11-05T03:00:00Z",
        "tags": ["billing"],
        "repository_anchors": ["services/billing/main.py"],
    }
    value.update(overrides)
    return value


ROOT = Path(__file__).resolve().parents[1]


class MemoryContractTests(unittest.TestCase):
    def test_schema_required_fields_match_the_validator_contract(self):
        schema = json.loads(
            (ROOT / "docs/schemas/memory_record.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(schema["required"]),
            {
                "schema_version", "id", "kind", "topic", "scope", "title",
                "content", "provenance", "confidence", "status", "trust",
                "created_at", "updated_at",
            },
        )
        self.assertTrue(set(record()) <= set(schema["properties"]))
        bundle = json.loads(
            (ROOT / "docs/schemas/memory_bundle.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            set(bundle["required"]),
            {"schema_version", "exported_at", "scope", "records", "checksum"},
        )
    def test_accepts_a_complete_record(self):
        self.assertEqual(validate_record(record()), [])

    def test_rejects_malformed_provenance_without_crashing(self):
        self.assertIn(
            "provenance must be an object",
            validate_record(record(provenance=[])),
        )

    def test_rejects_unknown_fields_and_bad_timestamps(self):
        self.assertIn(
            "unknown fields: extra",
            validate_record(record(extra="value"))[0],
        )
        invalid = record(updated_at="2026-11-05T02:00:00Z")
        self.assertIn("updated_at must not precede created_at", validate_record(invalid))

    def test_rejects_sensitive_content_before_storage(self):
        for content in (
            "OPENAI_API_KEY=sk-test-CANARY-7f3a9c2e1d4b8f6a",
            "Contact customer-canary@example.invalid",
            "Card 4242 4242 4242 4242",
        ):
            self.assertTrue(scan_sensitive(content), content)
            self.assertTrue(validate_record(record(content=content)), content)

    def test_rejects_untrusted_active_and_unsupported_verified_inference(self):
        self.assertIn(
            "an untrusted record cannot be active",
            validate_record(record(trust="untrusted")),
        )
        inferred = record(
            provenance={
                "source": "agent-inference",
                "observed_at": "2026-11-05T03:00:00Z",
                "evidence": ["Model guess"],
            }
        )
        self.assertIn(
            "agent-inference content cannot be verified without external evidence",
            validate_record(inferred),
        )

    def test_rejects_superseded_record_without_replacement(self):
        errors = validate_record(record(status="superseded"))
        self.assertIn("a superseded record requires superseded_by", errors)

    def test_render_and_parse_preserve_metadata(self):
        text = render_record(record())
        parsed = parse_record(text)
        self.assertEqual(parsed["meta"]["id"], "dec-billing-db")
        self.assertEqual(parsed["meta"]["confidence"], 0.9)
        self.assertEqual(parsed["meta"]["scope"]["project"], "billing-alpha")
        self.assertEqual(parsed["title"], "Billing database")
        self.assertEqual(parsed["content"], "Billing uses PostgreSQL 16.")

    def test_parse_rejects_unmarked_text(self):
        with self.assertRaises(ContractError):
            parse_record("# Not a memory record")

    def test_bundle_checksum_scope_and_supersession(self):
        active = record()
        old = record(
            "dec-billing-db-mysql",
            title="Previous database",
            content="Billing previously used MySQL 8.",
            created_at="2026-10-20T03:00:00Z",
            updated_at="2026-11-05T03:00:00Z",
            status="superseded",
            superseded_by="dec-billing-db",
        )
        active["supersedes"] = ["dec-billing-db-mysql"]
        bundle = make_bundle(
            [active, old], "2026-11-05T03:01:00Z", "phase2", "billing-alpha"
        )
        self.assertEqual(validate_bundle(bundle), [])
        tampered = copy.deepcopy(bundle)
        tampered["records"][0]["content"] = "Tampered"
        self.assertIn("bundle checksum does not match", validate_bundle(tampered))

    def bundle(self, records, workspace="phase2", project="billing-alpha"):
        return {
            "schema_version": 1,
            "exported_at": "2026-11-05T03:01:00Z",
            "scope": {"workspace": workspace, "project": project},
            "records": records,
            "checksum": bundle_checksum(records),
        }

    def test_bundle_rejects_duplicate_active_topics(self):
        second = record("dec-billing-db-two", title="Second active decision")
        bundle = self.bundle([record(), second])
        self.assertIn(
            "multiple active records for topic billing/database",
            validate_bundle(bundle, verify_checksum=False),
        )

    def test_bundle_rejects_broken_supersession_links(self):
        old = record(
            "dec-billing-db-mysql",
            status="superseded",
            superseded_by="dec-billing-db",
        )
        bundle = self.bundle([record(), old])
        # The replacement does not list the superseded record.
        self.assertIn(
            "dec-billing-db-mysql is not listed in its replacement's supersedes",
            validate_bundle(bundle, verify_checksum=False),
        )

    def test_bundle_rejects_records_outside_its_scope(self):
        other = record(
            "fact-other",
            topic="billing/other",
            scope={"workspace": "phase2", "project": "billing-beta"},
        )
        bundle = self.bundle([other])
        self.assertIn(
            "record fact-other is outside the bundle project",
            validate_bundle(bundle, verify_checksum=False),
        )

    def test_checksum_is_deterministic_across_key_order(self):
        first = record()
        second = dict(reversed(list(first.items())))
        self.assertEqual(bundle_checksum([first]), bundle_checksum([second]))

    def test_repository_check_demotes_missing_anchor_without_mutating_input(self):
        original = record()
        missing = apply_repository_check(original, lambda anchor: False)
        self.assertEqual(missing["status"], "stale")
        self.assertEqual(missing["trust"], "unverified")
        self.assertEqual(original["status"], "active")
        present = apply_repository_check(original, lambda anchor: True)
        self.assertEqual(present["status"], "active")
        no_anchor = record(repository_anchors=[])
        self.assertEqual(
            apply_repository_check(no_anchor, lambda anchor: False)["status"], "active"
        )

    def test_context_selection_excludes_stale_untrusted_and_low_confidence(self):
        active = record()
        stale = record("stale-old", status="stale", topic="billing/old")
        low = record("low-confidence", topic="billing/low", confidence=0.2)
        other_project = record(
            "other-project",
            topic="billing/other",
            scope={"workspace": "phase2", "project": "billing-beta"},
        )
        expired = record(
            "expired",
            topic="billing/expired",
            review_after="2026-10-01T00:00:00Z",
        )
        selected = select_context(
            [active, stale, low, other_project, expired],
            "billing-alpha",
            now=datetime(2026, 11, 5, 4, 0, tzinfo=timezone.utc),
        )
        self.assertEqual([item["id"] for item in selected], ["dec-billing-db"])

    def test_context_block_is_bounded(self):
        records = [
            record("record-{}".format(index), topic="billing/topic-{}".format(index))
            for index in range(20)
        ]
        selected = select_context(records, "billing-alpha", max_chars=150)
        rendered = "\n".join(render_context_block(item) for item in selected)
        self.assertLessEqual(len(rendered), 150)
        self.assertLessEqual(len(selected), 20)
        self.assertNotIn("stale", {item["status"] for item in selected})


if __name__ == "__main__":
    unittest.main()
