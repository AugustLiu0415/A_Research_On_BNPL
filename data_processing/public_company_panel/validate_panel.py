"""Validation checks for the BNPL public-company financial panel."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import date

from concept_mapping import CORE_VARIABLES
from fiscal_quarter_parser import QUARTER_ORDER, fiscal_sort_key, parse_date


def add_validation(rows, severity, check_name, CIK="", company="", fiscal_year="", fiscal_quarter="", message="", details=""):
    rows.append(
        {
            "severity": severity,
            "check_name": check_name,
            "CIK": CIK,
            "company": company,
            "fiscal_year": fiscal_year,
            "fiscal_quarter": fiscal_quarter,
            "message": message,
            "details": details,
        }
    )


def validate_crosswalk(crosswalk_rows, expected_unique_ciks=127):
    validation = []
    by_cik = defaultdict(list)
    missing_cik = []
    for row in crosswalk_rows:
        cik = row.get("CIK", "")
        if cik:
            by_cik[cik].append(row)
        else:
            missing_cik.append(row)

    if missing_cik:
        add_validation(validation, "ERROR", "missing_cik", message=f"{len(missing_cik)} public rows lack CIK.")

    unique_ciks = len(by_cik)
    if abs(unique_ciks - expected_unique_ciks) > 5:
        add_validation(
            validation,
            "WARNING",
            "unique_cik_count",
            message=f"Unique CIK count {unique_ciks} differs materially from expected ~{expected_unique_ciks}.",
        )
    else:
        add_validation(
            validation,
            "INFO",
            "unique_cik_count",
            message=f"Unique CIK count confirmed: {unique_ciks}.",
        )

    for cik, rows in by_cik.items():
        tickers = {r.get("ticker", "") for r in rows if r.get("ticker")}
        parents = {r.get("input_public_parent_company", "") for r in rows if r.get("input_public_parent_company")}
        if len(tickers) > 1:
            add_validation(validation, "WARNING", "ticker_conflict", CIK=cik, message="Multiple tickers mapped to one CIK.", details="; ".join(sorted(tickers)))
        if len(parents) > 1:
            add_validation(validation, "INFO", "multiple_parent_labels_one_cik", CIK=cik, message="Multiple parent-name labels mapped to one CIK.", details="; ".join(sorted(parents)))
        if len(rows) > 1:
            add_validation(validation, "INFO", "multiple_merchants_one_cik", CIK=cik, message=f"{len(rows)} merchant rows map to this CIK.")
    return validation


def validate_panel(panel_rows, annual_refs=None):
    validation = []
    annual_refs = annual_refs or []
    key_counts = Counter((r.get("CIK"), r.get("fiscal_year"), r.get("fiscal_quarter")) for r in panel_rows)
    for key, count in key_counts.items():
        if count > 1:
            add_validation(validation, "ERROR", "duplicate_company_quarter_key", CIK=key[0], fiscal_year=key[1], fiscal_quarter=key[2], message=f"Duplicate key appears {count} times.")

    today = date.today()
    for row in panel_rows:
        cik = row.get("CIK", "")
        company = row.get("sec_entity_name", "")
        fy = row.get("fiscal_year", "")
        fq = row.get("fiscal_quarter", "")
        if fq not in QUARTER_ORDER:
            add_validation(validation, "ERROR", "invalid_fiscal_quarter", cik, company, fy, fq, "Invalid fiscal quarter label.")

        end = parse_date(row.get("period_end"))
        if end and end > today:
            add_validation(validation, "ERROR", "future_period_end", cik, company, fy, fq, "Period end is after today's date.", row.get("period_end", ""))

        for margin, numerator in [
            ("gross_margin", "gross_profit"),
            ("operating_margin", "operating_income"),
            ("net_margin", "net_income"),
        ]:
            if row.get(margin) is not None and row.get("revenue") not in (None, 0):
                expected = row.get(numerator) / row.get("revenue")
                if abs(row.get(margin) - expected) > 1e-9:
                    add_validation(validation, "ERROR", "margin_consistency", cik, company, fy, fq, f"{margin} does not equal {numerator}/revenue.")

        if row.get("revenue") is not None and row.get("revenue") < 0:
            add_validation(validation, "WARNING", "negative_revenue", cik, company, fy, fq, "Negative revenue flagged for review.")
        if row.get("total_assets") is not None and row.get("total_assets") < 0:
            add_validation(validation, "WARNING", "negative_assets", cik, company, fy, fq, "Negative total assets flagged for review.")
        if row.get("gross_margin") is not None and (row["gross_margin"] > 1.5 or row["gross_margin"] < -1):
            add_validation(validation, "WARNING", "suspicious_gross_margin", cik, company, fy, fq, "Gross margin outside expected review bounds.", str(row["gross_margin"]))
        if row.get("operating_margin") is not None and (row["operating_margin"] > 1 or row["operating_margin"] < -2):
            add_validation(validation, "WARNING", "suspicious_operating_margin", cik, company, fy, fq, "Operating margin outside expected review bounds.", str(row["operating_margin"]))
        if row.get("revenue_growth_yoy") is not None and abs(row["revenue_growth_yoy"]) > 5:
            add_validation(validation, "WARNING", "extreme_revenue_growth_yoy", cik, company, fy, fq, "Extreme YoY revenue growth flagged.", str(row["revenue_growth_yoy"]))

        missing_core = [v for v in ["revenue", "gross_profit", "operating_income"] if row.get(v) is None]
        if missing_core:
            add_validation(validation, "WARNING", "missing_core_outcomes", cik, company, fy, fq, "Core outcome variables missing.", "; ".join(missing_core))

        if row.get("revenue_source_type") == "direct_companyfacts" and row.get("fiscal_quarter") in {"Q2", "Q3"}:
            dur = row.get("duration_days")
            if dur and dur > 125:
                add_validation(validation, "ERROR", "q2_q3_ytd_misclassified", cik, company, fy, fq, "Direct Q2/Q3 revenue appears cumulative rather than standalone.", str(dur))

    add_validation(validation, "INFO", "panel_row_count", message=f"Panel rows: {len(panel_rows)}")
    return validation


def build_manual_review(panel_rows, crosswalk_rows, validation_rows, company_metadata):
    manual = []
    ciks_with_rows = {r.get("CIK") for r in panel_rows}
    ciks_with_revenue = {r.get("CIK") for r in panel_rows if r.get("revenue") is not None}
    meta_by_cik = {m.get("CIK"): m for m in company_metadata}
    for row in crosswalk_rows:
        cik = row.get("CIK")
        meta = meta_by_cik.get(cik, {})
        if row.get("companyfacts_status") not in {"cache", "copied_existing_cache", "downloaded"}:
            manual.append(
                {
                    "CIK": cik,
                    "company": row.get("input_public_parent_company", ""),
                    "ticker": row.get("ticker", ""),
                    "issue_type": "missing_companyfacts",
                    "severity": "ERROR",
                    "notes": f"CompanyFacts unavailable: {row.get('companyfacts_status')}",
                }
            )
        elif cik not in ciks_with_rows:
            manual.append(
                {
                    "CIK": cik,
                    "company": row.get("input_public_parent_company", ""),
                    "ticker": row.get("ticker", ""),
                    "issue_type": "no_quarterly_panel_rows",
                    "severity": "WARNING",
                    "notes": "No fiscal-quarter rows were extracted from standardized CompanyFacts.",
                }
            )
        elif cik not in ciks_with_revenue:
            manual.append(
                {
                    "CIK": cik,
                    "company": row.get("input_public_parent_company", ""),
                    "ticker": row.get("ticker", ""),
                    "issue_type": "no_revenue_coverage",
                    "severity": "WARNING",
                    "notes": "No selected quarterly revenue observations.",
                }
            )
        if meta.get("foreign_issuer"):
            manual.append(
                {
                    "CIK": cik,
                    "company": row.get("input_public_parent_company", ""),
                    "ticker": row.get("ticker", ""),
                    "issue_type": "foreign_issuer_review",
                    "severity": "INFO",
                    "notes": "Foreign issuer or IFRS taxonomy/forms detected; review reporting frequency and concept mappings.",
                }
            )
    for val in validation_rows:
        if val.get("severity") in {"ERROR"}:
            manual.append(
                {
                    "CIK": val.get("CIK", ""),
                    "company": val.get("company", ""),
                    "ticker": "",
                    "issue_type": val.get("check_name", ""),
                    "severity": val.get("severity", ""),
                    "notes": val.get("message", "") + (" " + val.get("details", "") if val.get("details") else ""),
                }
            )
    return manual


def build_coverage_summary(panel_rows, crosswalk_rows, company_metadata):
    rows_by_cik = defaultdict(list)
    for row in panel_rows:
        rows_by_cik[row.get("CIK")].append(row)
    meta_by_cik = {m.get("CIK"): m for m in company_metadata}
    output = []
    for cw in crosswalk_rows:
        cik = cw.get("CIK")
        rows = sorted(rows_by_cik.get(cik, []), key=lambda r: fiscal_sort_key(r["fiscal_year"], r["fiscal_quarter"]))
        if rows:
            first = rows[0]
            last = rows[-1]
            expected = fiscal_sort_key(last["fiscal_year"], last["fiscal_quarter"]) - fiscal_sort_key(first["fiscal_year"], first["fiscal_quarter"]) + 1
            count = len(rows)
            def coverage(var):
                return sum(1 for r in rows if r.get(var) is not None) / count if count else 0
            missingness = 1 - (sum(sum(1 for var in CORE_VARIABLES if r.get(var) is not None) for r in rows) / (count * len(CORE_VARIABLES)))
            meta = meta_by_cik.get(cik, {})
            if meta.get("foreign_issuer"):
                status = "foreign_issuer_partial_history"
            elif first["fiscal_year"] > 2015:
                status = "post_ipo_partial_history"
            else:
                status = "complete_available_history"
            output.append(
                {
                    "CIK": cik,
                    "sec_entity_name": first.get("sec_entity_name", ""),
                    "input_public_parent_company": cw.get("input_public_parent_company", ""),
                    "ticker": cw.get("ticker", ""),
                    "exchange": cw.get("exchange", ""),
                    "merchant_count": cw.get("merchant_count", 0),
                    "first_available_quarter": first.get("fiscal_period", ""),
                    "last_available_quarter": last.get("fiscal_period", ""),
                    "number_of_quarters": count,
                    "expected_available_quarters": expected,
                    "revenue_coverage": coverage("revenue"),
                    "gross_profit_coverage": coverage("gross_profit"),
                    "operating_income_coverage": coverage("operating_income"),
                    "net_income_coverage": coverage("net_income"),
                    "balance_sheet_coverage": sum(1 for r in rows if r.get("total_assets") is not None) / count if count else 0,
                    "missingness_rate": missingness,
                    "coverage_status": status,
                }
            )
        else:
            output.append(
                {
                    "CIK": cik,
                    "sec_entity_name": "",
                    "input_public_parent_company": cw.get("input_public_parent_company", ""),
                    "ticker": cw.get("ticker", ""),
                    "exchange": cw.get("exchange", ""),
                    "merchant_count": cw.get("merchant_count", 0),
                    "first_available_quarter": "",
                    "last_available_quarter": "",
                    "number_of_quarters": 0,
                    "expected_available_quarters": 0,
                    "revenue_coverage": 0,
                    "gross_profit_coverage": 0,
                    "operating_income_coverage": 0,
                    "net_income_coverage": 0,
                    "balance_sheet_coverage": 0,
                    "missingness_rate": 1,
                    "coverage_status": "sec_error" if cw.get("companyfacts_status") not in {"cache", "copied_existing_cache", "downloaded"} else "xbrl_missing",
                }
            )
    return output
