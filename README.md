# BNPL Partnership Announcements: Shareholder Value Creation and Value Allocation

## Overview

This project examines how equity markets respond when BNPL platforms and
merchants announce partnerships. Its primary empirical design links dated
partnership information to historical securities, local trading sessions,
market benchmarks and contemporaneous-news audits. It estimates platform-
and merchant-side abnormal returns and compares both sides of the same
announcement where observable. Planned extensions examine combined abnormal
shareholder wealth and differences across firm and partnership characteristics.

Merchant-network datasets, accounting panels and regulatory-event work are
retained as supporting or historical modules. Initial AR/CAR diagnostics have
been computed, but the project has not yet established causal effects,
realized operating gains or total welfare changes.

## Primary Research Question

> Do BNPL platform–merchant partnership announcements create shareholder value, how are the associated gains and losses distributed between platforms and merchants, and how do these valuation responses vary with firm and partnership characteristics?

## Four Research Questions

1. **RQ1 — Do BNPL partnership announcements create value?**

   Are partnership announcements associated with positive or negative abnormal
   shareholder returns for BNPL platforms and their merchant partners?

2. **RQ2 — Who captures the value, or bears the loss?**

   How are announcement-associated gains and losses distributed between the
   platform and the merchant in the same partnership event?

3. **RQ3 — Net combined value or redistribution?**

   “Does the partnership create total economic value, or merely redistribute it?”

   In this design, the measurable object is combined abnormal shareholder
   wealth for the observed participating firms, not total economy-wide value
   or welfare. Operationally: Are the partners’ combined abnormal wealth
   changes consistent with net gains, net losses, or offsetting gains and
   losses between their shareholders?

4. **RQ4 — When is value creation strongest?**

   How do the direction and magnitude of individual and joint valuation
   responses vary with firm and partnership characteristics?

RQ4 retains seven dimensions: **industry, BNPL platform, merchant size,
exclusivity, multi-homing, partnership type and competitive importance**.
Multi-homing means use of multiple BNPL providers. Competitive importance
must be measured through observable scope, network reach, outside options
or relative dependence, not subsequent returns. Characteristics must be known
before or at the announcement; current directories cannot automatically be
projected backward, and silence does not establish exclusivity.

## Working Mechanisms and Planned Tests

- Incremental demand and network benefits may generate value when they
  outweigh fees, integration/financing costs and risks.
- Bargaining power, outside options and relative dependence may shape
  asymmetric gains and losses.
- Exposure, merchant economics and partnership characteristics may condition
  valuation responses.

These are working propositions, not established findings or finalized
directional hypotheses. Diagnostics have already been observed; this wording
is dated to the current documentation revision, not preregistered or backdated.
It is not derived from the signs of particular pilot CARs. No claim that all
partnerships create positive value is imposed. Where direction remains
unsettled, the project retains a research question rather than inventing a
prediction. In particular, size may combine exposure/dilution and bargaining
channels, and size, exclusivity and multi-homing have no imposed CAR sign.

## Current Empirical Objectives and Limits

| Question | Outcome/evidence | Current status | What remains |
| --- | --- | --- | --- |
| RQ1: Announcement value | Platform and merchant/public-parent CAR | Initial event-level diagnostics exist | Define eligible inference samples and uncertainty; no industry-wide effect established |
| RQ2: Who captures value or bears loss? | Both sides of the same event; planned dollar wealth and mechanism evidence | Some paired percentage-return diagnostics exist | Pre-event capitalization, comparable amounts, bargaining and dependence evidence |
| RQ3: Combined value or redistribution? | Planned combined abnormal shareholder wealth | Not calculated | Capitalization, share-class/ownership scope, pre-event FX convention and measurement/inference decisions |
| RQ4: When is value creation strongest? | Individual and planned joint responses across seven characteristics | Heterogeneity analysis planned; some characteristics exist | Complete historical covariates, specify tests and address dependence and limited samples |

Initial-information dates differ from operational rollout dates. Historical
tradability and local calendars matter. A source-quality grade does not
establish a clean information shock. The current price-index diagnostics are
not the final matched-total-return specification. Repeated platforms, bundles,
overlapping windows and the small pilot limit inference.

A larger percentage CAR does not establish a larger dollar gain or contractual
surplus share. An unobservable private-merchant return is missing, not zero.
Opposite signs, a near-zero joint estimate or failure to reject zero would
not establish pure redistribution. No question is treated as already answered.

See the [verified checkpoint](#latest-checkpoint) for existing counts and
[Research Questions and Design](docs/RESEARCH_QUESTIONS.md) for units,
eligible samples, planned wealth measurement, mechanism–evidence mapping
and the dated framing decision.

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

The analysis distinguishes three units:

- **Event evidence:** a distinct partnership-information announcement/bundle,
  with its merchant links.
- **Market observation:** event × security/side × local reaction session/window,
  retaining the specification and timing scenario.
- **Paired comparison:** the same event with both securities observable and
  eligible, retaining each side's local reaction interval.

Where a platform or merchant is observed through a listed parent, the return
measures that parent's valuation response, not a separately measured BNPL
subsidiary or merchant-brand return.

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
| `README.md` | Published current framing, research checkpoint and documentation |
| `docs/RESEARCH_QUESTIONS.md` | Canonical active questions, evidence map and framing decision |
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
CLI help was verified in the preceding documentation update; the current
framing revision uses read-only documentation and summary checks.
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

## Research Evolution and Module Hierarchy

**Stage A — Original merchant-accounting design.** The original question
concerned short- and long-run revenue growth, gross margins and operating
margins after BNPL adoption, with industry, scale/exposure and bargaining-power
hypotheses. The researcher's supplied account reported a placebo standard
deviation of approximately 3.06%, an implied minimum detectable revenue effect
of approximately 8.6%, and a plausible consolidated-revenue range of 1–6%.
The last range was a plausibility assessment, not an estimated treatment
effect. These considerations motivated aggregation and power concerns;
they did not prove that BNPL has no merchant effect.

**Stage B — Intermediate platform-focused proposal.** The broader framework
asked how merchant-network composition and regulatory shocks shape value
creation, surplus allocation and risk incidence in BNPL platforms. Its three
proposed modules were H1 Merchant Portfolio Economics, H2 Partnership Surplus
Allocation and H3 Regulatory Incidence. This was the researcher's proposal
and request for advice, not a claim that a supervisor approved the exact
current wording. No email date is inferred or private correspondence reproduced.

**Stage C — Current primary empirical focus.** The partnership-announcement
event study develops **Stage B's H2—Partnership Surplus Allocation** through
bilateral valuation responses and planned abnormal dollar wealth and
heterogeneity analysis. The broader agenda remains, with a clear hierarchy:

- **Primary:** partnership announcements, bilateral valuation responses,
  planned joint abnormal shareholder wealth and planned heterogeneity.
- **Supporting:** merchant-network composition and platform-quarter economics
  as context, mechanism or robustness work if historical data permit.
- **Secondary:** regulatory-event feasibility/robustness; earlier tests were
  reported as mixed/noisy, not decisive partnership evidence.
- **Legacy/exploratory:** merchant accounting DiD and private-company financial
  recovery.

The [canonical research-question document](docs/RESEARCH_QUESTIONS.md#research-evolution)
preserves the two historical H1–H3 systems separately. They are not current
directional CAR hypotheses, and supporting modules are not all complete.

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
