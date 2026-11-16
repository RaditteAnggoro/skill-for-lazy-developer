# REST and GraphQL failure isolation

Reproduce one authorized request and record the endpoint, expected response, environment,
and redacted identifiers. Do not invoke payment, disbursement, posting, or other
side-effecting endpoints without a safe fixture and explicit authorization.

Check layers in order: DNS/route/firewall, TLS/certificate, authentication,
authorization, request encoding, schema/contract, application behavior, downstream
call, then persistence effect. Follow correlation and request IDs where available; a
single HTTP status does not identify the cause.

For GraphQL, distinguish HTTP transport success from an `errors` payload and partial
data. Treat retries, idempotency, rate limits, and timeout-after-commit as separate
questions. Report confirmed causes separately from hypotheses and name the minimum
next check.

Native terminal, existing tests, or browser network evidence may be sufficient. A REST
MCP is never mandatory.
