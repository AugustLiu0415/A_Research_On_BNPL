# Control Group SEC Financial Panel

## Research purpose

This directory constructs a public-company control group for the BNPL merchant-side research project. The goal is to identify publicly listed companies that are economically comparable to the treated BNPL merchant parent companies but have no currently identified BNPL exposure.

## Treated-company reference sample

The treated reference sample is reconstructed from `data/public_company_panel_data/public_company_crosswalk.csv` and the treated quarterly SEC panel. The current run detected 127 treated public parent companies.

## Donor-pool construction

The candidate donor pool starts from the SEC company ticker universe cached in the project, then uses SEC Submissions SIC codes to keep consumer-facing, retail, travel/leisure, durable-goods, and related firms. Banks, insurers, utilities, extractive firms, funds, SPACs, and other clearly unsuitable firms are excluded.

## Control eligibility

Candidate firms are not labeled "never BNPL." The defensible status variable is `bnpl_control_status`. Preferred controls require `NO_BNPL_EVIDENCE`, valid CIK/ticker information, sufficient pre-2020 SEC financial data, and a reasonable match to a treated firm.

## BNPL exposure verification

Verification combines an exact check against the existing BNPL merchant/ownership files with targeted web-search evidence for BNPL provider terms. Search failures are not treated as proof of no BNPL exposure and are flagged for review.

## Industry classification

The primary economic industry signal is SEC SIC (`sic_code`, `sic_description`). Product-market categories use the Klarna-style 17-category taxonomy requested for this project, plus broad BNPL category groupings for matching.

## Size measurement

Matching uses pre-2020 size variables: `log_revenue_2019` and `log_assets_2019`. Historical 2019 market capitalization was not constructed in this run, so `size_bucket` is a FY2019 revenue-scale proxy rather than a market-cap bucket.

## Pre-period definition

All matching covariates and pre-trend diagnostics use fiscal years 2015-2019 only. No 2020-2026 outcomes are used to select controls.

## Matching variables

Matching uses standardized pre-period variables: log revenue, log assets, gross margin, operating margin, revenue growth, leverage, cash/assets, revenue pretrend, gross-margin pretrend, and operating-margin pretrend.

## Matching algorithm

The preferred sample uses transparent nearest-neighbor matching without replacement. Distance is standardized Euclidean distance on pre-2020 financial variables plus penalties for broad-category and SIC mismatch.

## Pre-trend construction

Company-level pretrends are simple linear slopes over 2015-2019 quarters. Revenue pretrend uses log revenue; margin pretrends use the reported/derived quarterly margin series.

## Balance diagnostics

`matching_balance_diagnostics.csv` reports treated mean, control mean, standard deviations, and standardized mean difference for each matching variable. Values above 0.20 are flagged for review.

## Final sample construction

After matching, preferred controls receive a final BNPL contamination screening pass. Contaminated or ambiguous firms are removed from the preferred control sample.

## SEC XBRL methodology

The quarterly panel uses the same CompanyFacts extraction modules as the treated-company panel, including concept priorities, YTD-to-quarter conversion, Q4 derivation, restatement flags, and missing-data policy.

## Output files

The main workbook is `controls_group_panel_data_2015_2026.xlsx`. CSV outputs include the quarterly panel, control master, donor pool, matching results, balance diagnostics, pretrend diagnostics, industry classifications, BNPL verification evidence, coverage summary, source audit, validation report, manual review file, and summary JSON.

## Limitations

No precise firm-level BNPL adoption dates are inferred here. A `NO_BNPL_EVIDENCE` control status means no identifiable BNPL exposure was found in the project files or web-search evidence used in this run; it does not prove historical non-adoption.

## Reproduction instructions

From the repository root:

```bash
export SEC_USER_AGENT="AugustLiu0415 BNPL control-group research august2004515@gmail.com"
python3 data_processing/controls_group_panel_data/build_controls_group_panel.py
```
