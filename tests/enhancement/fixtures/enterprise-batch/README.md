# Enterprise financial fixture

Run from the repository root with JDK 17 or 21 and Maven:

```sh
mvn -B -ntp -f tests/enhancement/fixtures/enterprise-batch/pom.xml test
```

This optional test suite downloads pinned dependencies and starts a temporary
loopback PostgreSQL server under the invoking user. `initdb` needs a non-root
account. The fixture owns its datasource, schema reset, metadata and synthetic
records. The separate crash worker requires a nonce created inside that fixture
before it can write. The path-filtered workflow exercises the suite on JDK 17/21
without a Docker daemon. Maven `target/` and local benchmark output are ignored.

[Scenario coverage and boundaries](../../../../docs/enterprise-financial-engineering/FAILURE_INJECTION_RESULTS.md).
