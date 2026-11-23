# Java and SQL source review

The original declaration mode stays available. Source mode parses explicit local
files and emits rule, classification, source file, line, method or SQL statement,
reason and a proposed verification. The scanner neither imports project classes nor
executes SQL. Run it from the repository root for stable relative source names.

```sh
python scripts/check_transaction_safety.py --json \
  --source tests/enhancement/fixtures/financial-review/BatchLoanWriter.java \
  --source tests/enhancement/fixtures/financial-review/finalize.sql
```

| Mechanism | Coverage and limits |
| --- | --- |
| JDK Compiler Tree API | Annotations and modifier shapes, same-instance annotated calls, checked exception policies, `REQUIRES_NEW`, writer catches, broad retry/skip, multi-write methods, conditional read-before-write, literal `BigDecimal`, unbounded reads and unscoped JDBC resources. Review class proxy type, aliases, runtime manager and branch conditions separately. |
| SQL lexical statements | Offset pagination, posting inserts requiring uniqueness evidence, staging fences, opposed explicit lock order, and migration hazards. Quoted text and comments are opaque. Verify PL/SQL/PLpgSQL bodies, procedural generated SQL, query plans, multi-file ordering and actual deployed constraints independently. |
| Dispositions | A confirmed finding proves a source construct, such as binary-floating literal construction or destructive DDL text. Likely risks and runtime questions require further evidence. A reviewer may attach a `FALSE_POSITIVE` disposition only with matching file, line, method, rule and evidence. |

The [positive and negative cases](../../tests/test_financial_source.py) cover each
rule, including a safe decimal string, `try`-with-resources, a guarded SQL update, a
unique journal key and ordered locking. The SQL lock rule compares patterns in one
file and conservatively reports opposing order. The Java catch rule checks for a
direct rethrow and may flag a correct framework-mediated recovery. Keep the finding
and research the runtime path. For reviewed dispositions, pass `--reviewed` a JSON
array of `{rule, file, line, method, evidence}` objects for the same source snapshot.

Detection success means the scanner produced observations. Use executed fixture
assertions to decide whether the financial transaction itself remains correct.
