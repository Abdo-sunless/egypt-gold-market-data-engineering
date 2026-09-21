# Egypt Gold Market Data Engineering Project

A real-world **Data Engineering project** for collecting, storing, transforming, and orchestrating data related to the Egyptian gold market.

The project starts from a set of research questions and builds a reliable data platform that can support the statistical analysis later.

---

## Research Questions

### Main Question

> **Is public interest in gold, interest in investing in gold, searches for gold-investment platforms, and actual investment activity associated with movements in gold prices in Egypt over time?**

### Supporting Questions

1. **Does interest in investing in gold and searching for gold purchases move alongside changes in gold prices, or do these variables show different patterns over time?**

2. **Is interest in gold-investment platforms and products, such as Thndr, Sabika, and Azimut-related products, associated with actual investment activity in gold funds?**

3. **Are there periods when increased search interest in investment platforms and products coincides with increased investment activity, or do these variables behave differently?**

4. **How do gold prices, public search interest, platform interest, and actual investment activity move over time, including possible lead/lag relationships?**

The project does **not** assume causality in advance. The engineering layer prepares the data needed to investigate these questions; statistical analysis and interpretation are performed later.

---

## Project Overview

The project combines heterogeneous real-world sources into a reproducible Data Engineering pipeline:

```text
GoldAPI + Frankfurter API
Google Trends
FRA investment data
Platform event data
        ↓
Python ingestion
        ↓
PostgreSQL raw layer
        ↓
dbt staging → intermediate → marts
        ↓
Future statistical analysis
        ↓
Pandas / EDA / Power BI
```

Kestra is used for workflow orchestration, while Docker provides the local infrastructure.

---

## Architecture

![Egypt Gold Market Data Engineering Architecture](docs/architecture.png)

The architecture shows the complete flow from external data sources to ingestion, PostgreSQL storage, dbt transformations, Kestra orchestration, and the later analytics layer.

---

## Project Scope

### Current Data Engineering scope

- Historical ingestion of gold prices.
- Historical ingestion of USD/EGP exchange rates.
- Google Trends extraction for gold, investment, and platform/product-related searches.
- Loading FRA gold-investment data and platform-event data.
- Persistent storage in PostgreSQL.
- Incremental daily updates.
- dbt staging, intermediate models, and marts.
- Data quality tests.
- Workflow orchestration with Kestra.
- Containerized local infrastructure with Docker Compose.

### Future Analysis scope

The statistical/analytical phase will be completed separately after studying statistics, Pandas, and EDA.

Planned analysis includes:

- Exploratory Data Analysis.
- Gold-price growth/returns rather than relying only on raw price levels.
- Pearson and Spearman correlation.
- Lag analysis in both directions.
- Seasonality and autocorrelation checks.
- Outlier investigation.
- Event-window analysis around important platform events.

Simple correlation or lag relationships will **not** be treated as proof of causality.

---

# Data Sources

| Source | Data | Role in the project |
|---|---|---|
| GoldAPI | Historical gold prices in XAU/USD | Core gold-price series |
| Frankfurter API | USD/EGP exchange rates | Convert gold USD prices to EGP |
| Google Trends | Relative search interest in Egypt | Measure public search interest over time |
| FRA dataset | Gold-investment activity | Measure actual investment activity |
| Platform events dataset | Platform/product events | Provide event context for platform-interest analysis |

---

# High-Level Architecture

```text
GoldAPI ────────────────┐
                        │
Frankfurter API ────────┤
                        │
Google Trends ──────────┤──> Python ingestion ──> PostgreSQL raw
                        │
FRA / Platform files ──┘
                                  │
                                  ▼
                               dbt
                                  │
                    ┌─────────────┼─────────────┐
                    ▼             ▼             ▼
                 staging      intermediate     marts
                    │             │             │
                    └─────────────┴─────────────┘
                                  │
                                  ▼
                            Future analysis
                                  │
                              Pandas / EDA
                                  │
                              Power BI

Kestra orchestrates the recurring workflow.
Docker provides the reproducible local infrastructure.
```

---

# Repository Structure

```text
Gold_hsitorydata_p/
│
├── backfill.py
├── pipeline.py
├── source.py
├── trend.py
├── fra_platforms_data.py
├── platforms_events.py
│
├── compose.yaml
├── dockerfile
├── pyproject.toml
├── uv.lock
├── .python-version
│
├── dbt/
│   ├── gold_project/
│   │   ├── dbt_project.yml
│   │   └── models/
│   │       ├── sources.yml
│   │       ├── schema.yml
│   │       ├── staging/
│   │       ├── intermediate/
│   │       └── marts/
│   └── logs/
│
├── Golden_historical_data/
├── logs/
├── docs/
│   └── architecture.png
└── README.md
```

Secrets such as API keys and database credentials should remain outside the public repository.

---

# 1. Historical Backfill

`backfill.py` is responsible for the **one-time historical load**.

Historical API requests are divided into approximately 90-day chunks instead of requesting the entire multi-year period in one request.

### Why use chunks?

A very large historical request can be more fragile, slower, or limited by an API. Smaller chunks make the process easier to monitor and reduce the risk of one oversized request failing.

The logic is:

```text
START_DATE
    ↓
process up to 90 days
    ↓
move to the next day after the chunk
    ↓
repeat
    ↓
END_DATE
```

The backfill uses `append` because it is a historical loading step intended to run once rather than a recurring daily job.

---

# 2. Daily Incremental Pipeline

`pipeline.py` is intentionally separate from the historical backfill.

The daily pipeline:

1. Reads the latest stored date for each source table.
2. Starts from `last_date + 1 day`.
3. Requests only the missing period.
4. Deduplicates according to the actual grain of each source.
5. Upserts or safely inserts the new observations.

### Why separate the two pipelines?

The historical problem and the recurring production-like problem are different:

```text
Backfill
→ load a large historical range once

Daily pipeline
→ load only data newer than the current watermark
```

Keeping them separate makes the intended operational behavior clear.

---

# 3. Raw Data Design

The raw layer preserves source-level observations instead of applying analytical assumptions too early.

Current raw tables include:

- `gold_prices`
- `exchange_rates`
- `google_trends`
- `platform_events`
- `fra_gold_investments`

## Gold price grain

`gold_prices` is intended to contain one gold-price observation per day.

Therefore, the incremental pipeline deduplicates by `date` and uses an upsert on `date`.

## Exchange-rate grain

`exchange_rates` is different.

The source can contain more than one USD/EGP observation for the same day. The project encountered multiple distinct rates on the same date.

### Decision

The raw layer keeps the distinct source observations.

We do **not** delete same-day observations simply because there is more than one rate.

Instead, the daily aggregation required to convert gold prices to EGP happens later in the intermediate layer.

This preserves source information while keeping downstream models at a clean analytical grain.

---

# 4. Gold Price Conversion

The gold API provides gold prices in USD, while the project needs a gold-price series in EGP.

The conversion is:

```text
Gold price in USD
        ×
Daily USD/EGP rate
        ↓
Gold price in EGP
```

The intermediate model `int_gold_price_egp` first calculates a daily average USD/EGP rate when multiple observations exist on the same day, then joins that daily rate to the daily gold price.

### Why average the exchange rate here instead of deleting raw duplicates?

Because these are two different responsibilities:

```text
Raw layer
→ preserve what the source reported

Intermediate layer
→ create the single daily rate needed for the gold-price conversion
```

This avoids multiplying one gold-price row into multiple output rows while keeping the original observations available.

---

# 5. Google Trends Design

Google Trends is one of the most important design decisions in the project because the goal is not to measure only generic interest in gold.

The search terms are divided into four analytical batches.

### Batch 1 — General gold interest

```text
سعر الذهب
الذهب اليوم
عيار 21
```

### Batch 2 — Gold investment intent

```text
استثمار الذهب
شراء الذهب
صندوق الذهب
```

### Batch 3 — Thndr interest

```text
ثاندر
تطبيق ثاندر
```

### Batch 4 — Other platform/product interest

```text
تطبيق سبيكة
صندوق ازيموت
ازيموت جولد
دهب ثاندر
```

The batches are intentionally kept separate.

---

# 6. Why We Did NOT Use a Common Anchor Across All Batches

This was one of the main analytical design decisions in the project.

At one point, a common anchor such as:

```text
ذهب
```

was considered for every Google Trends batch so the batches would share a common reference term.

## Why was the common anchor attractive?

A shared anchor appears useful because it seems to provide a common reference point between different groups of keywords.

For example:

```text
سعر الذهب + الذهب
استثمار الذهب + الذهب
ثاندر + الذهب
```

could appear to make the four groups easier to compare.

## Why did we reject it?

The project contains very different types of search terms:

```text
General gold terms
        ↓
high-volume broad searches

Investment-intent terms
        ↓
more specific searches

Platform/product terms
        ↓
smaller and more volatile signals
```

A broad anchor such as `ذهب` can dominate the comparison context because it is a much broader concept than a platform-specific term.

During the project design, the shared-anchor approach made the weaker platform signals less informative for the question we actually wanted to investigate: **how platform-specific search interest changes over time.**

In practical terms, the broad anchor could suppress or flatten the visible variation of smaller signals instead of helping us understand their time behavior.

## Another important reason: Google Trends is relative

Google Trends provides **relative search interest**, not absolute search counts.

A value of `100` represents the peak relative interest within the relevant comparison context. It does **not** mean 100 searches and does not mean 100% of Egyptians searched for the term.

Therefore:

> A common anchor would not magically convert the four batches into absolute, directly comparable search-volume measurements.

It would only change the comparison context used to generate the relative scores.

## Final decision

We kept the four batches independent and preserved the comparison context using `batch_id`.

That means:

```text
Batch 1 → compare terms within Batch 1
Batch 2 → compare terms within Batch 2
Batch 3 → compare terms within Batch 3
Batch 4 → compare terms within Batch 4
```

We intentionally **do not compare raw `interest` magnitudes across different batches as if they were on one common scale**.

Any later cross-batch comparison must use an explicit statistical normalization or another justified analytical method.

### Why this decision fits the research question

The project is interested in the **time movement of each type of signal**, especially platform-specific signals, rather than creating a visually convenient but potentially misleading common scale.

Keeping the batches independent preserves the within-batch temporal variation that is useful for later correlation and lag analysis.

---

# 7. Google Trends Long Format

Google Trends naturally returns multiple keywords as separate columns (wide format).

For example:

```text
Date       سعر الذهب   الذهب اليوم   عيار 21
2019-01    50          30            20
```

The database is designed in long format:

```text
Date       batch_id   geo   keyword        interest
2019-01    1          EG    سعر الذهب      50
2019-01    1          EG    الذهب اليوم    30
2019-01    1          EG    عيار 21        20
```

This conversion is performed with Pandas `melt()`.

### Why?

The long format gives a clear grain:

> **One row = one date + one batch + one geography + one keyword.**

It also makes SQL, dbt, filtering, grouping, and future statistical analysis easier.

The project converts each batch to long format **before** combining the batches. This prevents unrelated keywords from becoming columns in one giant wide table filled with `NaN` values.

---

# 8. Google Trends Duplicate Protection

The target grain is enforced with a unique key:

```text
(date, batch_id, keyword, geo)
```

The loader uses:

```sql
ON CONFLICT (date, batch_id, keyword, geo)
DO NOTHING
```

### Why?

If the extraction script is run again, already-loaded observations should not be inserted twice.

This makes the loading step duplicate-safe.

---

# 9. Why `isPartial` Is Removed

Google Trends can return an `isPartial` field indicating that a period is not fully completed.

The project removes this field from the stored analytical table because it is metadata about the returned period rather than one of the core analytical fields in the current model.

---

# 10. Source Layer (`source.py`)

`source.py` isolates external API communication from pipeline orchestration.

It contains separate functions for:

```text
get_gold_chunk()
        ↓
GoldAPI

get_frankfurter_chunk()
        ↓
Frankfurter API
```

Each function:

1. Builds the API URL.
2. Sends the request.
3. Validates the HTTP response with `raise_for_status()`.
4. Parses JSON.
5. Returns a Pandas DataFrame.

### Why separate this logic?

The source layer answers:

> **How do I get the data?**

while the pipeline layer answers:

> **When should I get it, for what date range, and where should I load it?**

This separation keeps extraction logic independent from orchestration and loading logic.

---

# 11. dbt Architecture

The dbt project follows three logical layers.

## Staging

Purpose:

- Read raw source tables.
- Rename or lightly clean fields when justified.
- Keep source-specific logic close to the source.

## Intermediate

Purpose:

- Combine sources.
- Apply business/analytical preparation.
- Resolve grain problems created by multi-source joins.

Current examples:

- `int_gold_price_egp`
- `int_google_trends`

## Marts

Purpose:

- Create analysis-ready business-facing models.

Current mart:

- `mart_gold_monthly`

It aggregates daily EGP gold prices into a monthly metric because the project needs a monthly gold-price series for alignment with monthly Google Trends data.

The mart uses the **average daily gold price within each month**.

Growth, returns, correlations, and lag analysis are intentionally left for the later Python/statistics stage rather than embedding all statistical analysis inside dbt.

---

# 12. Why Google Trends Does Not Get Another Monthly Aggregation

The long-term Google Trends extraction is already monthly.

Therefore, the project does not apply an unnecessary `AVG()` or `SUM()` to the `interest` values.

Instead, `int_google_trends` makes the monthly grain explicit by converting the date to the first day of the month.

This preserves the original Trends values rather than creating another derived monthly statistic.

---

# 13. Data Grain Is a Core Design Rule

Before joining or aggregating data, the project explicitly asks:

> **What does one row represent?**

Examples:

```text
gold_prices
→ one gold-price observation per day

exchange_rates
→ one source exchange-rate observation

int_gold_price_egp
→ one converted gold-price observation per day

google_trends
→ one keyword observation per date/batch/geo

mart_gold_monthly
→ one monthly gold-price observation
```

Defining the grain before joins prevents accidental row multiplication and incorrect aggregations.

---

# 14. Kestra Architecture

Kestra is used as the workflow orchestrator.

There are deliberately two PostgreSQL services:

```text
postgres
→ project data

kestra_postgres
→ Kestra's own metadata/repository/queue data
```

This keeps the orchestration system's data separate from the project's analytical database.

Kestra configuration includes:

- PostgreSQL datasource.
- PostgreSQL repository.
- PostgreSQL queue.
- Local storage.
- Task temporary directory.
- Basic authentication.

The PostgreSQL service has a healthcheck using `pg_isready`.

Kestra is configured to wait for the PostgreSQL service to become **healthy**, not merely for its container to start.

---

# 15. Docker Design

The project uses Docker Compose for local infrastructure:

```text
PostgreSQL
Kestra PostgreSQL
Kestra
```

Named volumes provide persistent storage for databases, Kestra storage, and temporary working data.

A shared Docker network (`GD_network`) allows services to communicate by service name.

For the Python application image, dependencies are managed with `uv` and `uv.lock`.

The Dockerfile copies dependency files before application code to improve Docker layer caching:

```text
Dependency files
      ↓
uv sync
      ↓
Application code
```

This means changing a Python source file does not unnecessarily rebuild the dependency installation layer.

---

# 16. Why `uv` Is Copied From Its Official Image

The Python application image starts from Python 3.13.2.

Instead of installing `uv` through the package manager, the Dockerfile copies the `uv` executable from the official `uv` image.

Conceptually:

```text
Official uv image
      ↓
copy /uv
      ↓
Python application image
```

This provides the standalone `uv` binary without adding a separate installation step for it.

The project also uses `uv.lock` with `--locked` so dependency resolution remains reproducible.

---

# 17. Reliability Decisions

Several reliability decisions were added while building the project.

### Required environment variables

A helper function validates required variables and fails early with a clear error instead of producing a later connection failure.

### HTTP error handling

API clients use:

```python
response.raise_for_status()
```

so failed API requests are detected immediately.

### Google Trends batch isolation

Each Trends batch has its own `try/except`, so one failed batch does not automatically prevent the remaining batches from being attempted.

### Rate-limit protection

The Trends loader waits briefly between batches to reduce the chance of sending requests too rapidly.

### Duplicate protection

Database unique constraints and conflict handling are used where the source grain requires them.

### Transactional loading

SQLAlchemy `engine.begin()` is used around loading operations so successful work is committed and failures can be rolled back.

---

# 18. Problems Encountered and How They Were Handled

This section documents the practical problems that shaped the final design.

### Problem: historical APIs should not be requested as one huge range

**Decision:** split backfill requests into approximately 90-day chunks.

### Problem: gold and exchange-rate sources do not necessarily have identical grain

**Decision:** keep raw observations and resolve the exchange-rate multiplicity in the intermediate model.

### Problem: joining daily gold prices to multiple same-day FX rows can multiply records

**Decision:** aggregate FX to one daily rate before joining to gold.

### Problem: Google Trends terms represent very different concepts and signal strengths

**Decision:** divide the terms into four analytical batches.

### Problem: a common anchor such as `ذهب` made platform-specific signals less informative

**Decision:** remove the shared anchor, keep independent batches, and preserve `batch_id`.

### Problem: Google Trends returns keywords in wide format

**Decision:** use `melt()` to create one row per keyword observation before combining batches.

### Problem: rerunning the Trends loader could create duplicates

**Decision:** use the unique grain `(date, batch_id, keyword, geo)` and `ON CONFLICT DO NOTHING`.

### Problem: a running Docker container does not guarantee the database inside it is ready

**Decision:** use a PostgreSQL healthcheck with `pg_isready` and make Kestra depend on `service_healthy`.

### Problem: development environments can drift when dependencies change

**Decision:** use `uv.lock`, `--locked`, and Docker layer caching around dependency installation.

---

# 19. Validation and Testing

The dbt project includes model descriptions and data quality tests.

At the current project checkpoint:

```text
22 tests passed
0 warnings
0 errors
0 skipped
```

The tests cover important properties such as non-null and unique fields where the model grain requires them.

The pipeline scripts also print basic observability information such as extracted row counts and counts by Google Trends batch.

---

# 20. What This Project Does NOT Claim

This project is designed to investigate relationships, not to assume causation.

For example:

```text
Search interest increases
        ↓
Gold price increases
```

does **not** automatically mean:

```text
Search interest caused the price increase.
```

Price changes may affect search behavior, while other events and factors may influence both variables.

The later statistical phase will therefore consider directionality, lags, seasonality, autocorrelation, and other possible confounders before making interpretations.

---

# 21. Main Engineering Lessons

This project was built around several practical lessons:

- Define data grain before designing joins.
- Preserve raw source observations instead of deleting inconvenient values too early.
- Separate extraction, orchestration, transformation, and analysis responsibilities.
- Treat historical backfills and incremental pipelines as different operational problems.
- Make duplicate handling match the actual grain of each source.
- Do not treat Google Trends values as absolute search volume.
- Do not force unrelated Trends keywords onto one shared scale just for convenient comparison.
- Use dbt intermediate models to solve real multi-source transformation problems.
- Create marts when there is a real analytical need instead of creating models mechanically.
- Keep causal claims separate from correlation and descriptive analysis.

---

# Current Status

## Data Engineering

- [x] Historical ingestion
- [x] Incremental ingestion
- [x] PostgreSQL raw layer
- [x] Google Trends ingestion
- [x] FRA investment data ingestion
- [x] Platform event ingestion
- [x] dbt staging
- [x] dbt intermediate models
- [x] Monthly gold mart
- [x] dbt tests
- [x] Docker infrastructure
- [x] Kestra orchestration setup

## Analysis

- [ ] Statistics preparation
- [ ] EDA
- [ ] Return/change analysis
- [ ] Correlation analysis
- [ ] Lag analysis
- [ ] Event-window analysis
- [ ] Final Power BI analytical dashboard

---

# Final Project Goal

Build a reliable and reproducible Data Engineering pipeline that turns heterogeneous real-world data into an analysis-ready foundation for studying **gold prices, public interest, gold-investment intent, platform interest, and actual investment activity in Egypt**.

The engineering layer is designed first; statistical conclusions come later.
