# Public Company SEC Financial Panel

## Research purpose

This directory contains a reproducible firm by fiscal-quarter SEC financial panel for publicly listed parent companies associated with the BNPL merchant sample. It is designed for later merger with BNPL adoption timing, but it intentionally contains no treatment indicators.

## Company sample construction

The sample starts from `data/merchant_ownership/merchant_ownership_rows.json`. Public merchant rows are grouped by zero-padded CIK. Merchant-brand mappings are preserved in `public_company_crosswalk.csv`.

## SEC data sources

Primary source: SEC CompanyFacts API, `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json`.

Secondary identity/filing-history source: SEC Submissions API, `https://data.sec.gov/submissions/CIK##########.json`.

If `SEC_USER_AGENT` is not configured, the pipeline does not make new SEC requests and uses only existing local cache files.

## CompanyFacts methodology

The parser uses standardized `us-gaap` and selected `ifrs-full` concepts from CompanyFacts. Concept selection is centralized in `data_processing/public_company_panel/concept_mapping.py`.

## Fiscal-quarter construction

Rows are keyed by `CIK`, `fiscal_year`, and `fiscal_quarter` using SEC `fy` and `fp` metadata. Calendar-year and calendar-quarter columns are informational only and are based on `period_end`.

## YTD-to-quarter conversion

For flow variables, quarter-only CompanyFacts observations are preferred. Q2 and Q3 values are derived from cumulative YTD facts only when the same concept and unit are available and period alignment is valid.

## Q4 derivation

Q4 flow values are derived from annual fiscal-year facts only when Q1, Q2, and Q3 are available using the same accounting concept and unit. Balance-sheet variables are never differenced.

## XBRL concept mapping

Revenue, gross profit, operating income, net income, balance-sheet items, SG&A, diluted EPS, diluted shares, capex, and optional working-capital variables use ordered fallback lists. The selected tag is preserved in the source audit.

## Foreign-issuer treatment

Foreign issuers and IFRS filers are retained. If quarterly standardized facts are unavailable, the company remains in the crosswalk and is flagged in coverage/manual-review outputs.

## Amendments and restatements

When multiple facts exist for a company/concept/period/unit, the latest filed valid fact is selected and restatement/amendment flags are preserved.

## Missing-data policy

Missing observations are left missing. The pipeline never forward fills, interpolates, divides annual values by four, or fabricates quarters.

## Data-quality flags

`core_data_quality_flag` is `HIGH` when core variables are directly reported and clean, `MEDIUM` when reliable derivations are used, `LOW` when important core fields are missing, and `REVIEW` when period/currency/identity issues require attention.

## Output files

The main workbook is `public_company_panel_data_2015-2026.xlsx`. CSV outputs include the quarterly panel, company crosswalk, source audit, coverage summary, validation report, and manual-review list.

## Known limitations

This run may rely on existing cached SEC responses if `SEC_USER_AGENT` is missing. In that case, missing cache files and skipped Submissions API validation are explicitly recorded.

## Rerun instructions

Set an identifiable user agent before fetching new SEC data:

```bash
export SEC_USER_AGENT="BNPL Merchant Research your-email@example.com"
```

Then run:

```bash
python3 data_processing/public_company_panel/build_public_company_panel.py
```
