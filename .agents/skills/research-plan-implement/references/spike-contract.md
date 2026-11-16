# Time-boxed technical spike

Use a spike only when an uncertain technical choice materially changes architecture.

```yaml
question: one decision-changing question
max_scope: one isolated fixture; no production files
hypotheses: [A, B]
success_metric: observable evidence
prohibited: [production services, unapproved dependencies, irreversible changes]
exit: decision + evidence + limitations
cleanup: remove disposable experiment unless the user asked to keep it
```

No fake timing guarantee. The time box is an effort bound agreed with the task. A spike
does not become production architecture without follow-up tests and a decision record.
Do not install a dependency merely to complete the spike.
