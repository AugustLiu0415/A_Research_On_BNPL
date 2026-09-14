# BNPL Platform–Merchant Partnership Announcement Event Study

## Overview

This project studies shareholder valuation responses to BNPL
platform–merchant partnership announcements. The main empirical design pairs
the platform and the merchant, or its event-date public parent, around the
same information event.

The latest checkpoint is a completed **local real-data AR/CAR diagnostic**,
dated 14 September 2026. Eligible observations have actual market-model
estimates and abnormal returns. Other observations remain explicitly blocked
or not applicable. Completion of this diagnostic does not imply completion
of the full research design.

Earlier merchant accounting DiD, private-company financial-data collection,
merchant-directory, ownership, adoption-date and matched-control work remain
historical or supporting modules. The regulatory-event smoke test provides
secondary feasibility evidence, not evidence about the partnership sample.

## Current Research Questions

1. How do platform and merchant shareholder valuations respond around
   partnership announcements?
2. How do the two sides of the **same event** differ, conditional on valid
   historical security mappings, timing and comparable specifications?
3. With future pre-event market-capitalization and FX data, what is the
   combined abnormal shareholder wealth change?
4. How might responses vary across partnership type, exclusivity, multi-homing,
   platform, merchant size, industry and other pre-event characteristics?

These are research questions, not established findings. CARs are not realized
sales or profits, total social welfare, causal proof, or established
value-capture shares. Adding two percentage CARs does not measure joint wealth.

## Latest Checkpoint

The saved run is `local_20260914T193653Z_62c00494`, completed on
14 September 2026, with status `PARTIAL_DIAGNOSTIC_RESULTS`.
The inherited analysis cutoff remains **2026-07-04**.

Counts below were checked against the saved canonical CSV/JSON outputs and
the three local workbooks during this documentation update.

| Counting unit | Count |
| --- | ---: |
| Fixed platform-shock units | 20 |
| Retained partnership links | 21 |
| Event-side records | 42 |
| Side × window × timing rows | 174 |
| Estimated readiness rows | 80 |
| Blocked readiness rows | 85 |
| `NOT_APPLICABLE` private-counterparty rows | 9 |
| Fitted OLS models | 29 |
| Daily abnormal-return records | 133 |
| CAR estimates | 80 |
| Paired window/scenario records | 16 |

The 80 CAR estimates are classified separately:

| Diagnostic classification | Records |
| --- | ---: |
| Accepted primary anchor, main window | 12 |
| Window robustness at accepted anchors | 24 |
| Timing sensitivity | 44 |

The 12 primary-anchor/main-window records comprise **8 platform results and
4 merchant results across 9 event IDs**. The platform results comprise
**7 Affirm and 1 Zip** observations.

The saved validation report records **53 tests passed, 0 failed and 0 skipped**
at 2026-09-14 19:37:19 UTC, and successful reconciliation of all three
workbooks. The prior run also recorded independent numerical verification
of its models, daily ARs and CARs. These are saved execution results:
**the analysis and 53-test suite were not rerun for this documentation update**.

A current provenance check found that the three XLSX files no longer match
their hashes in the saved run manifest. The other 108 recorded output files,
all 40 recorded input files and all 5 recorded analysis-code files still
match. A separate read-only check reconciled all current workbook detail-table
values and cached summaries with the saved workbook payload, and the requested
counts and paired results with the canonical CSVs. The workbook files have later modification times than the
saved run; the cause of the byte changes has not been established. The saved
test pass must not be treated as a byte-level certification of those current
XLSX versions. No workbook or manifest was rewritten during this documentation
update. Reconciliation of this workbook-version discrepancy remains open.

## Sample and Counting Units

The wider frozen inventory contains 96 records: 81 included information events
and 15 preserved exclusions. The current diagnostic uses the already fixed
20-shock/21-link pilot, not all 81 included events. Missing prices and
contaminated windows do not cause replacement of pilot candidates.

A shock is different from a partnership link, security, fitted model or
window-specific result. The Zip–Fanatics/Fiserv bundle remains **one platform
shock with two partnership links**. Platform fits and weights are deduplicated;
all merchant links are retained. Repeated securities and overlapping event
windows do not become independent observations because row IDs differ.

The 16 paired rows span **5 partnerships**, with repeated windows or timing
scenarios. Only **3 partnerships** have an accepted-anchor, main-window paired
result: Affirm–Walmart, Affirm–Hotels.com/Expedia and Affirm–Shopify in 2025.
Zip–Qantas timing scenarios remain sensitivities. Zip–Peloton cross-market
specifications are not pooled into comparable same-specification means.

The 29 models are not 29 companies, the 80 CAR rows are not 80 independent
events, and the 16 paired rows are not 16 independent paired events.

## Data and Method

### Local inputs and coverage

The actual supplied-input directory is:

```text
data_partnership/merchant_stock_price/
```

It is at the project root. The earlier requested
`data/data_partnership/merchant_stock_price/` did not exist at this checkpoint
and is not the canonical supplied-input location documented here.

The run imported **19 supplied stock CSVs and 1 FRED CSV**, and reused
**1 verified Australian index cache**: **21 available price series** in total.
The 19 stocks comprise 4 platform securities and 15 merchant/public-parent
securities. Availability does not guarantee event-specific eligibility.
Historical POSH prices remain absent.

Original filenames and bytes are retained. Copy-suffix aliases are resolved
with schema, coverage and hash checks. Historical identities preserve, among
other distinctions, Block's SQ/XYZ history, Zip's Z1P/ZIP history, Shopify's
event-date U.S. listing, and Sezzle's Nasdaq shares versus ASX CDIs.

Quality handling includes:

- The FRED file has 1,551 rows: 1,495 numeric levels and 56 blank rows on
  confirmed closed days. Its actual endpoint is 2025-05-23.
- SEZL has 753 supplied rows. The 50 rows beyond the frozen cutoff were not
  analyzed; the original history is preserved.
- Delivered records are retained for confirmed Zip halt dates and separately
  flagged stale zero-volume quotes. Those observations invalidate the affected
  daily return and the next scheduled-session return. The halt/stale-quote QA
  revision followed an initial numerical draft,
  which was archived; this is not a claim of fully blinded preregistration.
- The reused ASX200 cache has a missing level on 2019-10-03. Neither it nor
  other missing scheduled prices is filled or bridged.
- Missing estimates are null with reasons, not zero. Large returns are not
  removed or winsorized merely because of their size.

The completed local diagnostic made **zero price API requests**. No new Yahoo
or WRDS download was required to read supplied files.

### Return and benchmark specification

Each security is paired independently with its own market benchmark.
There is no global complete-case intersection across all stocks.

| Market | Diagnostic specification | Benchmark |
| --- | --- | --- |
| United States | `fred_price_proxy_adjclose_diagnostic_v1` | `FRED_SP500_PRICE` |
| Australia | `asx200_price_proxy_adjclose_diagnostic_v1` | `BM-AU-ASX200-PRICE` |

Stock returns use adjacent scheduled-session Yahoo **Adj Close** ratios minus
one. Market returns use adjacent scheduled-session **price-index** ratios
minus one. FRED SP500 excludes dividends; adjusted stock prices reflect
applicable split and distribution adjustments. This deliberately mixed basis
is a diagnostic limitation, **not the final matched-total-return specification**.
U.S. FRED and Australian ASX200 results remain separate.

France retains the CAC All-Tradable mapping and Hong Kong the Hang Seng mapping.
Neither missing benchmark is replaced with FRED, an ETF or a derivative.

Definitions recorded with the local analysis are available from
[FRED SP500](https://fred.stlouisfed.org/series/SP500),
[Yahoo historical adjusted prices](https://help.yahoo.com/kb/SLN28256.html)
and [S&P/ASX 200](https://www.spglobal.com/spdji/en/indices/equity/sp-asx-200/).
These references do not confer redistribution rights.

### Estimation, timing and audit gates

All offsets are exchange trading sessions:

- Preparation prices: `[-301,+10]`.
- Estimation returns: `[-250,-30]`, intended 221 observations, minimum
  **200 valid security–benchmark return pairs**.
- Main event window: `[-1,+1]`, exactly 3 daily returns.
- Robustness windows: `[0,+1]` and `[-2,+2]`, exactly 2 and 5 returns.

For each eligible shock, security, anchor and specification, the pipeline fits
an OLS market model **with an intercept** using estimation-window data only:

```text
R_stock,t = alpha + beta × R_market,t + epsilon_t
AR_t      = R_stock,t − (alpha_hat + beta_hat × R_market,t)
CAR[a,b]  = sum of all required AR_t from a through b
```

A fit is reused across eligible windows of the same model. CAR is a sum of
abnormal returns, not a compounded return or raw market-adjusted return.
Missing observations do not compress event time or produce incomplete sums.

The latest v2 corrected audit and alignment are joined by event, side,
security, reaction session, timing scenario and window, with evidence and
audit identifiers retained. Historical identity, accepted timing, relevant
`CleanEvent=1`, return definitions, coverage and numerical estimability are
checked independently for each side/window/scenario. MAIN sample membership
does not override a negative or unresolved audit. Corrected macro-event
timezones and final-close boundaries are retained.

Bounded unresolved timing scenarios remain separately labelled sensitivities,
including a provisional anchor named `primary`. A `primary` window label is
not itself proof that the timing anchor is accepted. Failure of one window,
side or foreign benchmark does not block unrelated eligible observations.

## Diagnostic Findings and Limitations

The three accepted-anchor `[-1,+1]` paired cases use reaction sessions
2023-12-19 (Walmart), 2024-08-20 (Hotels.com/Expedia) and 2025-02-20
(Shopify). **All six models in this particular comparison have 221 estimation
observations.** That is not true of every fitted model.

The paired numerical values and the Hotels.com/Expedia `[0,+1]` comparison
were checked in the local `Paired_CAR` output. The latter illustrates window
sensitivity, not proof of information leakage. The main window has not been
changed to obtain a preferred sign. No positive-only subset is substituted
for the complete three-case comparison.

**Public disclosure of the numerical CAR table remains unreviewed.** This
documentation release therefore publishes workflow, counts and limitations,
but withholds CAR magnitudes and the detailed comparison table. Complete
signed results remain in the local workbooks and canonical CSV files; their
omission here does not mean that estimation was not performed.

The pilot is small and concentrated, especially in Affirm. Audit exclusions,
missing data, repeated securities, overlapping windows, timing sensitivity and
mixed return bases limit interpretation. No pooled significance claims,
heterogeneity findings, joint abnormal wealth amounts or value-capture shares
have been established. Observed CARs describe announcement-associated
shareholder valuation reactions, not operating outcomes or causal effects.

## Repository Layout

The following describes the **local research workspace**, not a promise that
every listed item is distributed in the GitHub checkout.

| Relative path | Role and distribution status |
| --- | --- |
| `README.md` | Published research checkpoint and documentation |
| `data_partnership/merchant_stock_price/` | Supplied raw CSVs; local only |
| `data/data_processing/AR_CAR mock test/` | Current generated results; local only |
| `data/mock_test_#1/` | Frozen pilot and calendar snapshots; local research inputs |
| `data/mock_test_#1/continuation_v2/` | Corrected audit, alignment and evidence; local research inputs |
| `data_partnership/` | Earlier inventory, sample, historical mapping and review assets |
| `data/platform_securities_stock_market_price/` | Local historical caches and benchmark mapping |
| `scripts/run_local_ar_car_mock_test.py` | Local diagnostic CLI |
| `src/partnership_event_study/` | Local research implementation |
| `tests/test_local_ar_car_mock_test.py` | Local regression and output checks |
| `data_processing/` | Historical accounting-panel, overlap and control-group modules |
| `data/regulatory/`, `src/regulatory_event_study/`, `reports/` | Supporting regulatory feasibility work |

The current output folder normalizes the requested label “AR/CAR mock test”
to the single directory name **`AR_CAR mock test`**. It is under
`data/data_processing/`, not root-level `data_processing/`.

The following are **generated locally, not distributed in the repository**:

- `data_validation_v1.xlsx`: inventory, identity, sessions, price basis and benchmarks.
- `ar_car_readiness_v1.xlsx`: pilot, side/window eligibility, audit links and missing data.
- `ar_car_results_v1.xlsx`: models, daily AR, CAR, paired results, sensitivities and exclusions.
- `input_manifest.json`, `analysis_spec_v1.json` and `run_manifest.json`.
- `cleaned/`, `matched/` and `results/` canonical data, including
  `results/not_estimated_reasons.csv`.
- `reports/run_summary.md`, `reports/validation_report.json` and saved QA/test records.

All paths in this list are relative to the current output folder. They are
plain-text local references, not download links to ignored artifacts.

## Reproduction

Run from the project root of an **authorized, configured local research
workspace**. This documentation-only publication does not add the untracked
research scripts, source code, tests or dependency updates to GitHub.
A clean clone of this documentation commit is therefore **not a self-contained
reproduction package**.

The local implementation requires its frozen pilot/calendar snapshots,
historical security mapping, corrected v2 audit files, supplied CSVs and
verified Australian cache. Numerical verification uses NumPy and openpyxl.
Workbook export additionally uses Node.js and `@oai/artifact-tool` through
the existing local runtime configuration. The current exporter resolves a
machine-specific runtime internally; a portable exporter setup is still
pending and was not changed in this documentation task. Installing the
published requirements file alone does not establish this environment.

Inspect the CLI without running analysis:

```bash
python3 scripts/run_local_ar_car_mock_test.py --help
```

The authorized local rerun command uses the **actual input directory**:

```bash
python3 scripts/run_local_ar_car_mock_test.py \
  --input-dir "data_partnership/merchant_stock_price" \
  --output-dir "data/data_processing/AR_CAR mock test" \
  --phase all
```

The CLI exposes `ingest`, `clean`, `pair`, `audit-join`, `estimate`,
`export` and `all`. The complete workflow performs those operations in order.
Calling `estimate` directly still enforces eligibility. Unchanged completed
runs can be resumed; changed inputs or code trigger versioned archives rather
than silently overwriting earlier results.

The run command is documented here, **not executed by this README update**.
Only CLI help and read-only documentation checks were executed for this task.
The full execution and test claims above refer to the saved September 14 run.

## Missing Data and Next Steps

Unresolved inputs and gates include historical POSH prices, CAC All-Tradable
and Hang Seng benchmarks, inadequate history, material confounders and
unresolved announcement timing. The local missing-data table records exact
required intervals, all reason codes, action owners and next actions.

NEGG has **119 valid estimation pairs**, below the 200 minimum. The fixed
window and threshold have not been shortened, and predecessor histories have
not been spliced to manufacture observations. Its missing history does not
block the independently eligible Affirm side.

Recovering the Hong Kong benchmark alone will **not** make the Cathay
observations eligible: their negative confounder audit remains binding.
Data recovery must not override exclusions.

Next research steps are to:

1. Review daily contributions and the existing window/timing sensitivities
   without choosing dates or windows on the basis of observed CARs.
2. Recover missing data where it can add genuinely eligible observations,
   retaining unchanged security identities and audit decisions.
3. Validate a more comparable return/benchmark specification and assess
   differences transparently rather than assuming the mixed basis is immaterial.
4. Expand beyond this pilot under a fixed, documented design, preserving
   exclusions and avoiding selection on observed results.
5. Complete publication and redistribution review and prepare a separately
   reviewed, portable reproduction package.
6. Only later conduct appropriately designed formal inference and
   heterogeneity analysis, accounting for dependence and sample concentration.
7. Obtain pre-event market capitalization and FX inputs before calculating
   joint abnormal shareholder wealth in consistent monetary units.

## Historical/Supporting Modules

- **Merchant directories (9 August 2026 checkpoint):** official provider
  directories support merchant/provider/category coverage and overlap work.
  Ownership and conservative adoption-date evidence support historical
  mapping; uncertain adoption dates remain explicit.
- **Accounting-panel and control work (earlier supporting design):** quarterly
  SEC treated and matched-control panels support possible merchant accounting
  DiD. They are not daily stock prices, and they do not supply the market
  capitalization or FX inputs needed for joint abnormal wealth.
- **Private-company financial-data feasibility:** Companies House,
  OpenCorporates and SEC configuration remains a separate supporting workflow.
  Each provider is enabled independently. Local `.env` values belong beside
  the README and must never be committed; example placeholders must be empty.
  This checkpoint did not rerun those APIs or restart a private-company panel.
- **Regulatory feasibility (13 and 17 August 2026 checkpoints):** the prior
  regulatory inventory and provider CAR smoke test tested a separate event
  design. They do not establish partnership effects or enlarge this pilot.
- **Partnership sample preparation (12 September 2026 freeze):** the earlier
  Round-2 milestone froze the sample and prepared local price coverage without
  partnership CAR estimation. That historical no-CAR status is superseded by
  the September 14 real-data diagnostic, not asserted as the current state.

These modules and their existing assets are preserved. This documentation
update does not rerun them or change their results.

## Data Sharing

Local diagnostic processing, formal publication readiness and redistribution
permission are separate decisions. The saved manifest authorizes local
diagnostic processing, marks publication **`NOT_REVIEWED`**, and does not
authorize redistribution.

This documentation release contains no raw market data, cleaned prices,
daily returns, daily AR, research workbooks, restricted CSV/Parquet/JSON
outputs, data-containing screenshots, credentials or private machine paths.
Specific CAR magnitudes are also withheld pending disclosure review.
The concise workflow and counting-unit discussion is not a raw-data release.

Existing local ignore rules protect the supplied price directories, the
current output tree and credentials. Explicit documentation-only staging is
still required: ignore rules do not make tracked history safe or confer
data rights. Historical assets already present in the repository are not
relicensed by this checkpoint.
