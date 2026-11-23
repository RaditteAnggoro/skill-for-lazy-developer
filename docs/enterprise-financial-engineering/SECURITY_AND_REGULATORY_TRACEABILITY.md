# Security and regulatory traceability

The fixture uses invented keys and a private loopback database. The reporting path
retains synthetic counts and source anchors. Use project-scoped memories and verify
their current applicability before applying a saved decision. Keep names, NIK,
account identifiers, customer amounts, connection credentials and unmasked tool
logs out of artifacts. Keep the posting identity stable while masking identifiers.

| Accountability property | Evidence and follow-up |
| --- | --- |
| Who initiated and approved | Independent actor labels in fixture audit. Live systems must bind identities, delegated authority and scope to IAM and an approval decision. |
| When and why | System timestamp, business/value dates, reason and correlation across stage, journal and outbox. The audit query detects missing evidence and inconsistent business dates. |
| Before and after | Immutable fingerprint and state/claim version link one effect to inputs. Store minimized before/after values or separate protected evidence when appropriate. |
| Access, retention and tamper evidence | Evaluate append-only authorization, write isolation, trace retention, restore and evidentiary integrity in the deployed environment. The disposable schema does not model an IAM system. |
| Recovery and reconciliation | Record the last durable state, affected key scope, compensating decision and independent closure checks. Preserve unknown outcomes until reconciled. |

OJK and BI SNAP applicability depends on the consuming institution, regulated
activity and actual payment interface. This generic synthetic fixture has no
defined jurisdictional or product obligations. A compliance assessment requires
the exact applicable instrument, provision, effective date, control owner and
verifiable execution evidence. Sector and personal-data obligations need an
independently reviewed scope before a compliance claim.

The existing [financial-integrity reviewer](../../.agents/roles/ld-financial-integrity-reviewer.yaml)
already covers independent reconciliation, duplicate effects and auditability.
Use it optionally in an authorized, read-only scope where consequence warrants an
independent assessment. A separate audit or reconciliation role has no demonstrated
additional purpose in this fixture.
