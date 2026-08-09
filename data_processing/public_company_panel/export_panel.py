"""CSV/JSON/documentation exports for the public-company panel."""

from __future__ import annotations

import csv
import json
from pathlib import Path


PANEL_COLUMNS = [
    "company_id",
    "CIK",
    "sec_entity_name",
    "input_public_parent_company",
    "ticker",
    "exchange",
    "merchant_count",
    "merchant_names",
    "fiscal_year",
    "fiscal_quarter",
    "fiscal_period",
    "period_start",
    "period_end",
    "duration_days",
    "calendar_year",
    "calendar_quarter",
    "revenue",
    "gross_profit",
    "cogs",
    "operating_income",
    "net_income",
    "gross_margin",
    "operating_margin",
    "net_margin",
    "revenue_growth_yoy",
    "revenue_growth_qoq",
    "total_assets",
    "total_liabilities",
    "stockholders_equity",
    "cash_and_cash_equivalents",
    "total_debt",
    "sga_expense",
    "inventory",
    "accounts_receivable",
    "current_assets",
    "current_liabilities",
    "diluted_eps",
    "weighted_average_diluted_shares",
    "capital_expenditures",
    "currency",
    "revenue_tag",
    "gross_profit_tag",
    "cogs_tag",
    "operating_income_tag",
    "net_income_tag",
    "revenue_source_type",
    "gross_profit_source_type",
    "operating_income_source_type",
    "net_income_source_type",
    "form",
    "filing_date",
    "accession_number",
    "amended_filing_flag",
    "restatement_flag",
    "concept_transition_flag",
    "unusual_duration_flag",
    "core_data_quality_flag",
    "manual_review_required",
    "retrieved_at",
]

CROSSWALK_COLUMNS = [
    "CIK",
    "unique_company_id",
    "sec_entity_name",
    "input_public_parent_company",
    "ticker",
    "exchange",
    "merchant_names",
    "canonical_merchant_names",
    "merchant_count",
    "input_public_merchant_rows",
    "bnpl_providers",
    "companyfacts_status",
    "submissions_status",
    "sec_companyfacts_url",
    "sec_submissions_url",
]

SOURCE_AUDIT_COLUMNS = [
    "CIK",
    "company",
    "ticker",
    "fiscal_year",
    "fiscal_quarter",
    "variable_name",
    "selected_value",
    "unit",
    "taxonomy",
    "selected_tag",
    "start",
    "end",
    "fy",
    "fp",
    "form",
    "filed",
    "accn",
    "frame",
    "source_type",
    "restatement_flag",
    "validation_notes",
    "component_accessions",
]

VARIABLE_DEFINITION_COLUMNS = [
    "variable",
    "definition",
    "source",
    "preferred_xbrl_concepts",
    "unit",
    "reported_or_derived",
    "calculation_formula",
]


def write_csv(path, rows, columns=None):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if columns is None:
        columns = sorted({key for row in rows for key in row.keys()})
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_json(path, payload):
    Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_methodology_readme(output_dir: Path):
    text = """# Public Company SEC Financial Panel

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
export SEC_USER_AGENT=\"BNPL Merchant Research your-email@example.com\"
```

Then run:

```bash
python3 data_processing/public_company_panel/build_public_company_panel.py
```
"""
    (Path(output_dir) / "README.md").write_text(text, encoding="utf-8")
