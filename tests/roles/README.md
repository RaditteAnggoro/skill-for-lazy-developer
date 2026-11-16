# Role fixtures

`invalid-role.yaml` is deliberately invalid: empty triggers, unknown scope, write access,
external side effects, missing denied capabilities, an invalid status, missing source
citations, and an unknown field. Tests must reject it without crashing.

Valid contracts live in `.agents/roles/`.
