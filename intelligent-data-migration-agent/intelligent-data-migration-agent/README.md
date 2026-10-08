# Intelligent Data Migration Agent

AI-assisted migration of a legacy **SQL Server** data platform to **Snowflake + dbt**.
LLMs handle reasoning, classification and generation; deterministic code handles parsing, dependency resolution and validation.

> Status: **source platform defined** (this commit). Agent, RAG, dbt generation and validation come next.

## What is in the repo right now

A synthetic retail order-to-cash platform in T-SQL, built as the benchmark the agent will be evaluated against.

| Object type | Count | Notes |
|---|---|---|
| Tables | 24 | landing, staging, reference, SCD1/SCD2 dimensions, facts, aggregate, ETL control |
| Views | 5 | reporting; window functions, multi-CTE cohort retention |
| Functions | 5 | 4 scalar UDFs + 1 inline table-valued function |
| Stored procedures | 16 | trivial → extreme; 3 deliberately extreme |
| Sequences | 1 | batch id |

```
data/
  source/                 # the legacy platform (deployable)
    deploy.sql            # SQLCMD script: schemas → tables → seeds → FKs → functions → views → procs
    schemas/ sequences/ tables/<schema>/ seed/ constraints/ functions/ views/ procedures/<schema>/
  expected/
    object_catalog.yaml   # hand-labelled ground truth: complexity, dependencies, constructs, target
data/generator/profiles.yaml   # volume profiles + every ratio / defect rate
docs/source-platform.md   # lineage, complexity map, migration traps, known legacy behaviours
docs/data-volumes.md      # row counts per table (built from the generated manifests)
scripts/check_source_platform.py   # static checks
scripts/generate_data.py  # synthetic data at a chosen volume profile (initial + incremental loads)
scripts/load_data.py      # CSV -> SQL Server landing tables
scripts/make_volume_doc.py
```

## Deploying the source platform

Requires SQL Server 2017+ (uses `STRING_AGG`, `STRING_SPLIT`, `CREATE OR ALTER`, `OPENJSON`).

```bash
# empty database first, then from data/source/
sqlcmd -S localhost -d MigrationSource -E -i deploy.sql
```

## Data

```bash
python scripts/generate_data.py --profile medium   # tiny | small | medium; deterministic for a given seed
python scripts/load_data.py --profile medium --phase initial --conn "<odbc connection string>"
# EXEC etl.usp_run_daily_load;
python scripts/load_data.py --profile medium --phase incremental --conn "<odbc connection string>"
# EXEC etl.usp_run_daily_load;   then compare table counts with data/generated/medium/manifest.json
```

The default `medium` profile is ~50k customers, ~2k products and ~320k orders (~2M landing rows). See `docs/data-volumes.md`.
Only landing tables are loaded; the stored procedures populate everything else, and `manifest.json` records the counts they should produce.

## Static checks (no database needed)

```bash
pip install pyyaml sqlglot
python scripts/check_source_platform.py
```

Verifies that every schema-qualified reference resolves, the catalog agrees with the code, the pipeline seed points at real procedures, BEGIN/END, TRY/CATCH, parentheses and transactions balance, and any generated CSV headers match the table DDL.
It **does not prove the T-SQL runs** - deploy against a real instance for that.

## Design principle

The LLM is never the final authority on data correctness. Anything that can be checked deterministically (SQL parses, schemas match, row counts and aggregates agree) is checked by software.

## Roadmap

1. ✅ Synthetic source platform + ground-truth catalog
2. ✅ Sample-data generator and loader · ⏳ run on SQL Server to confirm the expected counts in `manifest.json`
3. Parser, metadata extraction, dependency graph, rule-based assessment (the no-LLM baseline)
4. LLM transformation with Pydantic structured outputs, validated by the parser
5. dbt model / `schema.yml` / test generation
6. Validation engine (row counts, aggregates, checksums) + fault injection + root-cause analysis
7. Evaluation harness: baseline vs AI, with real numbers
8. RAG over migration patterns, as a measured add-on
