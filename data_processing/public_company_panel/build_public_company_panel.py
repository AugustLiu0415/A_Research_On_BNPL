"""Build the BNPL public-company quarterly SEC financial panel."""

from __future__ import annotations

import argparse
import json
import logging
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from concept_mapping import FLOW_DERIVABLE_VARIABLES, VARIABLE_DEFINITIONS
from export_panel import (
    CROSSWALK_COLUMNS,
    PANEL_COLUMNS,
    SOURCE_AUDIT_COLUMNS,
    VARIABLE_DEFINITION_COLUMNS,
    write_csv,
    write_json,
    write_methodology_readme,
)
from extract_companyfacts import extract_company_panel
from fiscal_quarter_parser import fiscal_sort_key
from sec_client import SECClient
from validate_panel import build_coverage_summary, build_manual_review, validate_crosswalk, validate_panel


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "data" / "merchant_ownership" / "merchant_ownership_rows.json"
OUTPUT_DIR = ROOT / "data" / "public_company_panel_data"
SOURCE_COMPANYFACTS_CACHE = ROOT / "data" / "merchant_ownership" / "cache" / "sec_companyfacts"
NODE = Path("/Users/augustliu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")


def setup_logging(output_dir: Path):
    log_dir = output_dir / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "processing.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    request_logger = logging.getLogger("sec_requests")
    request_logger.setLevel(logging.INFO)
    request_handler = logging.FileHandler(log_dir / "sec_requests.log", encoding="utf-8")
    request_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    request_logger.handlers.clear()
    request_logger.addHandler(request_handler)
    request_logger.propagate = False

    validation_logger = logging.getLogger("validation")
    validation_logger.setLevel(logging.INFO)
    validation_handler = logging.FileHandler(log_dir / "validation.log", encoding="utf-8")
    validation_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    validation_logger.handlers.clear()
    validation_logger.addHandler(validation_handler)
    validation_logger.propagate = False

    error_logger = logging.getLogger("errors")
    error_logger.setLevel(logging.INFO)
    error_handler = logging.FileHandler(log_dir / "errors.log", encoding="utf-8")
    error_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    error_logger.handlers.clear()
    error_logger.addHandler(error_handler)
    error_logger.propagate = False
    return logging.getLogger("panel"), request_logger, validation_logger, error_logger


def _norm_list(value):
    if not value:
        return []
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return [part.strip() for part in str(value).split(";") if part.strip()]


def load_public_crosswalk(input_path: Path):
    rows = json.loads(Path(input_path).read_text(encoding="utf-8"))
    public_rows = [
        row for row in rows
        if str(row.get("ownership_type", "")).lower().startswith("public") and row.get("cik")
    ]
    grouped = defaultdict(list)
    for row in public_rows:
        cik = str(row["cik"]).strip().zfill(10)
        grouped[cik].append(row)

    crosswalk = []
    for cik, group in sorted(grouped.items()):
        merchant_names = sorted({r.get("merchant_name", "").strip() for r in group if r.get("merchant_name")})
        canonical = sorted({r.get("merchant_key", "").strip() for r in group if r.get("merchant_key")})
        providers = sorted({p for r in group for p in _norm_list(r.get("bnpl_providers"))})
        parent_candidates = [r.get("sec_matched_company", "") for r in group if r.get("sec_matched_company")]
        ticker_candidates = [r.get("ticker", "") for r in group if r.get("ticker")]
        exchange_candidates = [r.get("exchange", "") for r in group if r.get("exchange")]
        parent = sorted(parent_candidates, key=lambda x: (-parent_candidates.count(x), x))[0] if parent_candidates else ""
        ticker = sorted(ticker_candidates, key=lambda x: (-ticker_candidates.count(x), x))[0] if ticker_candidates else ""
        exchange = sorted(exchange_candidates, key=lambda x: (-exchange_candidates.count(x), x))[0] if exchange_candidates else ""
        crosswalk.append(
            {
                "CIK": cik,
                "unique_company_id": cik,
                "sec_entity_name": "",
                "input_public_parent_company": parent,
                "ticker": ticker,
                "exchange": exchange,
                "merchant_names": "; ".join(merchant_names),
                "canonical_merchant_names": "; ".join(canonical),
                "merchant_count": len(merchant_names),
                "input_public_merchant_rows": len(group),
                "bnpl_providers": "; ".join(providers),
                "companyfacts_status": "",
                "submissions_status": "",
                "sec_companyfacts_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
                "sec_submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
            }
        )
    return public_rows, crosswalk


def write_checkpoint(output_dir, processed, failed, pending, last_successful_company=""):
    write_json(
        output_dir / "processing_checkpoint.json",
        {
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "processed_CIKs": sorted(processed),
            "failed_CIKs": sorted(failed),
            "pending_CIKs": sorted(pending),
            "last_successful_company": last_successful_company,
        },
    )


def add_growth(panel_rows):
    rows_by_cik = defaultdict(list)
    for row in panel_rows:
        rows_by_cik[row["CIK"]].append(row)
    for cik, rows in rows_by_cik.items():
        keyed = {(r["fiscal_year"], r["fiscal_quarter"]): r for r in rows}
        ordered = sorted(rows, key=lambda r: fiscal_sort_key(r["fiscal_year"], r["fiscal_quarter"]))
        for row in ordered:
            prev_yoy = keyed.get((row["fiscal_year"] - 1, row["fiscal_quarter"]))
            q_idx = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}[row["fiscal_quarter"]]
            prev_seq = keyed.get((row["fiscal_year"] - 1, "Q4")) if q_idx == 1 else keyed.get((row["fiscal_year"], f"Q{q_idx - 1}"))
            row["revenue_growth_yoy"] = None
            if prev_yoy and row.get("revenue") is not None and prev_yoy.get("revenue") not in (None, 0):
                row["revenue_growth_yoy"] = row["revenue"] / prev_yoy["revenue"] - 1
            row["revenue_growth_qoq"] = None
            if prev_seq and row.get("revenue") is not None and prev_seq.get("revenue") not in (None, 0):
                row["revenue_growth_qoq"] = row["revenue"] / prev_seq["revenue"] - 1


def create_summary(
    public_rows,
    crosswalk,
    panel_rows,
    source_audit,
    coverage_summary,
    validation_rows,
    manual_review_rows,
    company_metadata,
    retrieved_at,
):
    fiscal_periods = sorted(
        {(r["fiscal_year"], r["fiscal_quarter"]) for r in panel_rows},
        key=lambda item: fiscal_sort_key(item[0], item[1]),
    )
    period_ends = sorted({r.get("period_end") for r in panel_rows if r.get("period_end")})
    def coverage(var):
        return sum(1 for r in panel_rows if r.get(var) is not None) / len(panel_rows) if panel_rows else 0

    source_counts = defaultdict(int)
    for row in source_audit:
        source_counts[row.get("source_type", "")] += 1

    return {
        "retrieved_at": retrieved_at,
        "input_public_merchant_rows": len(public_rows),
        "unique_public_parent_companies": len({r.get("input_public_parent_company") for r in crosswalk if r.get("input_public_parent_company")}),
        "unique_CIKs": len(crosswalk),
        "companies_successfully_processed": len({r.get("CIK") for r in panel_rows}),
        "companies_failed": len([r for r in crosswalk if r.get("companyfacts_status") not in {"cache", "copied_existing_cache", "downloaded"}]),
        "companies_requiring_manual_review": len({r.get("CIK") for r in manual_review_rows if r.get("CIK")}),
        "total_fiscal_quarter_rows": len(panel_rows),
        "first_panel_period": f"FY{fiscal_periods[0][0]} {fiscal_periods[0][1]}" if fiscal_periods else "",
        "latest_panel_period": f"FY{fiscal_periods[-1][0]} {fiscal_periods[-1][1]}" if fiscal_periods else "",
        "earliest_period_end": period_ends[0] if period_ends else "",
        "latest_period_end": period_ends[-1] if period_ends else "",
        "revenue_coverage_rate": coverage("revenue"),
        "gross_profit_coverage_rate": coverage("gross_profit"),
        "operating_income_coverage_rate": coverage("operating_income"),
        "net_income_coverage_rate": coverage("net_income"),
        "direct_reported_value_count": source_counts.get("direct_companyfacts", 0),
        "derived_ytd_value_count": source_counts.get("derived_from_ytd", 0),
        "derived_q4_value_count": source_counts.get("derived_q4_from_fy", 0),
        "US_GAAP_company_count": sum(1 for m in company_metadata if m.get("us_gaap_company")),
        "IFRS_company_count": sum(1 for m in company_metadata if m.get("ifrs_company")),
        "foreign_issuer_count": sum(1 for m in company_metadata if m.get("foreign_issuer")),
        "restatement_flag_count": sum(1 for r in panel_rows if r.get("restatement_flag")),
        "concept_transition_flag_count": sum(1 for r in panel_rows if r.get("concept_transition_flag")),
        "unusual_duration_flag_count": sum(1 for r in panel_rows if r.get("unusual_duration_flag")),
        "validation_error_count": sum(1 for r in validation_rows if r.get("severity") == "ERROR"),
        "validation_warning_count": sum(1 for r in validation_rows if r.get("severity") == "WARNING"),
        "companyfacts_cache_files": len(list((OUTPUT_DIR / "cache" / "companyfacts").glob("CIK*.json"))),
        "submissions_cache_files": len(list((OUTPUT_DIR / "cache" / "submissions").glob("CIK*.json"))),
        "sec_user_agent_configured": bool(__import__("os").environ.get("SEC_USER_AGENT", "").strip()),
    }


def run_workbook_builder(output_dir):
    builder = Path(__file__).with_name("build_public_company_panel_workbook.mjs")
    if not builder.exists():
        raise FileNotFoundError(builder)
    subprocess.run([str(NODE), "--max-old-space-size=6144", str(builder), str(output_dir)], check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default=str(DEFAULT_INPUT))
    parser.add_argument("--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--skip-workbook", action="store_true")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    logger, request_logger, validation_logger, error_logger = setup_logging(output_dir)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    logger.info("Loading public-company sample from %s", args.input)
    public_rows, crosswalk = load_public_crosswalk(Path(args.input))
    validation_rows = validate_crosswalk(crosswalk)
    for row in validation_rows:
        validation_logger.info("%s %s %s", row["severity"], row["check_name"], row["message"])

    if args.smoke_test:
        preferred = ["0000320193", "0000027419", "0000039911", "0000997248", "0000016988"]
        picked = [row for cik in preferred for row in crosswalk if row["CIK"] == cik]
        if len(picked) < 5:
            picked.extend([row for row in crosswalk if row not in picked][: 5 - len(picked)])
        crosswalk = picked[:5]
        logger.info("Smoke test mode: processing %s companies", len(crosswalk))

    client = SECClient(
        output_dir=output_dir,
        source_companyfacts_dir=SOURCE_COMPANYFACTS_CACHE,
        refresh=args.refresh,
        logger=logger,
        request_logger=request_logger,
    )
    if not client.can_request_sec():
        logger.warning("SEC_USER_AGENT is not configured. No new SEC requests will be made; local cache only.")

    panel_rows = []
    source_audit = []
    annual_refs = []
    company_metadata = []
    processed = set()
    failed = set()
    pending = {r["CIK"] for r in crosswalk}
    last_successful = ""

    for idx, row in enumerate(crosswalk, 1):
        cik = row["CIK"]
        logger.info("[%s/%s] Processing CIK%s %s", idx, len(crosswalk), cik, row.get("input_public_parent_company", ""))
        cf_path, cf_status = client.ensure_companyfacts(cik)
        row["companyfacts_status"] = cf_status
        sub_path, sub_status = client.ensure_submissions(cik)
        row["submissions_status"] = sub_status
        if not cf_path:
            failed.add(cik)
            pending.discard(cik)
            error_logger.info("CompanyFacts unavailable for CIK%s: %s", cik, cf_status)
            write_checkpoint(output_dir, processed, failed, pending, last_successful)
            continue
        try:
            rows, audit, meta, annual = extract_company_panel(cf_path, row, retrieved_at)
            if rows:
                row["sec_entity_name"] = rows[0].get("sec_entity_name", "")
            elif meta.get("sec_entity_name"):
                row["sec_entity_name"] = meta.get("sec_entity_name", "")
            panel_rows.extend(rows)
            source_audit.extend(audit)
            annual_refs.extend(annual)
            company_metadata.append(meta)
            processed.add(cik)
            pending.discard(cik)
            last_successful = row.get("input_public_parent_company", "")
            logger.info("CIK%s extracted rows=%s audit_facts=%s", cik, len(rows), len(audit))
        except Exception as exc:
            failed.add(cik)
            pending.discard(cik)
            error_logger.exception("Failed to extract CIK%s: %s", cik, exc)
        write_checkpoint(output_dir, processed, failed, pending, last_successful)

    add_growth(panel_rows)
    panel_validation = validate_panel(panel_rows, annual_refs)
    validation_rows.extend(panel_validation)
    for row in panel_validation:
        validation_logger.info("%s %s %s", row["severity"], row["check_name"], row["message"])

    coverage_summary = build_coverage_summary(panel_rows, crosswalk, company_metadata)
    manual_review_rows = build_manual_review(panel_rows, crosswalk, validation_rows, company_metadata)
    summary = create_summary(
        public_rows,
        crosswalk,
        panel_rows,
        source_audit,
        coverage_summary,
        validation_rows,
        manual_review_rows,
        company_metadata,
        retrieved_at,
    )

    write_csv(output_dir / "public_company_panel_data_2015-2026.csv", panel_rows, PANEL_COLUMNS)
    write_csv(output_dir / "public_company_crosswalk.csv", crosswalk, CROSSWALK_COLUMNS)
    write_csv(output_dir / "public_company_panel_source_audit.csv", source_audit, SOURCE_AUDIT_COLUMNS)
    write_csv(output_dir / "public_company_panel_coverage_summary.csv", coverage_summary)
    write_csv(output_dir / "public_company_panel_validation_report.csv", validation_rows)
    write_csv(output_dir / "public_company_panel_manual_review.csv", manual_review_rows)
    write_csv(output_dir / "public_company_panel_variable_definitions.csv", VARIABLE_DEFINITIONS, VARIABLE_DEFINITION_COLUMNS)
    write_json(output_dir / "public_company_panel_summary.json", summary)
    write_methodology_readme(output_dir)
    logger.info("Wrote CSV/JSON outputs to %s", output_dir)

    if not args.skip_workbook:
        run_workbook_builder(output_dir)
        logger.info("Workbook export complete")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
