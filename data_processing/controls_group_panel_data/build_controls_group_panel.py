"""Construct a BNPL control-group sample and matching SEC quarterly panel.

This script is intentionally self-contained inside the requested output folder.
It reuses the treated-panel CompanyFacts extraction code so treated and control
financial variables follow the same XBRL concept, YTD, and Q4 derivation logic.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import html
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
PUBLIC_PANEL_DIR = ROOT / "data" / "public_company_panel_data"
PUBLIC_PANEL = PUBLIC_PANEL_DIR / "public_company_panel_data_2015-2026.csv"
PUBLIC_CROSSWALK = PUBLIC_PANEL_DIR / "public_company_crosswalk.csv"
MERCHANT_OWNERSHIP_ROWS = ROOT / "data" / "merchant_ownership" / "merchant_ownership_rows.json"
MERCHANT_CATEGORIES = ROOT / "data" / "merchant_list_raw_data" / "BNPL_Merchant_Categories.csv"
SEC_TICKERS_EXCHANGE_CACHE = ROOT / "data" / "merchant_ownership" / "cache" / "company_tickers_exchange.json"
SOURCE_COMPANYFACTS_DIRS = [
    PUBLIC_PANEL_DIR / "cache" / "companyfacts",
    ROOT / "data" / "merchant_ownership" / "cache" / "sec_companyfacts",
]

PUBLIC_PANEL_MODULE_DIR = ROOT / "data_processing" / "public_company_panel"
sys.path.insert(0, str(PUBLIC_PANEL_MODULE_DIR))

from concept_mapping import VARIABLE_DEFINITIONS  # noqa: E402
from extract_companyfacts import extract_company_panel  # noqa: E402
from export_panel import PANEL_COLUMNS, SOURCE_AUDIT_COLUMNS, write_csv, write_json  # noqa: E402
from fiscal_quarter_parser import fiscal_sort_key  # noqa: E402
from validate_panel import build_coverage_summary, build_manual_review, validate_panel  # noqa: E402


NODE = Path("/Users/augustliu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node")
NODE_MODULES = Path("/Users/augustliu/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules")

RETRIEVED_AT = datetime.now(timezone.utc).isoformat()
PREFERRED_CONTROL_TARGET = 127
EXPANDED_PER_TREATED = 2
DONOR_POOL_TARGET = int(os.environ.get("CONTROL_DONOR_POOL_TARGET", "420"))
SEC_SCAN_LIMIT = int(os.environ.get("CONTROL_SEC_SCAN_LIMIT", "6500"))


def setup_logging():
    log_dir = OUTPUT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_dir / "processing.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    for name in ["matching", "bnpl_verification", "sec_requests", "validation", "errors"]:
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)
        logger.handlers.clear()
        handler = logging.FileHandler(log_dir / f"{name}.log", encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
        logger.propagate = False
    return logging.getLogger("controls")


LOGGER = setup_logging()
MATCH_LOG = logging.getLogger("matching")
BNPL_LOG = logging.getLogger("bnpl_verification")
SEC_LOG = logging.getLogger("sec_requests")
VALIDATION_LOG = logging.getLogger("validation")
ERROR_LOG = logging.getLogger("errors")


def git_config_value(key: str) -> str:
    try:
        return subprocess.check_output(["git", "config", key], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        return ""


def default_user_agent() -> str:
    configured = os.environ.get("SEC_USER_AGENT", "").strip()
    if configured:
        return configured
    name = git_config_value("user.name") or "AugustLiu0415"
    email = git_config_value("user.email") or "august2004515@gmail.com"
    ua = f"{name} BNPL control-group research {email}"
    os.environ["SEC_USER_AGENT"] = ua
    return ua


USER_AGENT = default_user_agent()


def clean_text(value) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip())


def canonical_name(value) -> str:
    text = clean_text(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    drop = {
        "inc",
        "incorporated",
        "corp",
        "corporation",
        "company",
        "co",
        "ltd",
        "limited",
        "plc",
        "holdings",
        "holding",
        "group",
        "class",
        "common",
        "stock",
        "ordinary",
        "shares",
        "the",
    }
    tokens = [tok for tok in text.split() if tok not in drop]
    return " ".join(tokens)


def padded_cik(cik) -> str:
    value = str(cik or "").strip()
    if value.endswith(".0"):
        value = value[:-2]
    return value.zfill(10) if value.isdigit() else value


def cik_int(cik) -> int | None:
    try:
        return int(str(cik).strip())
    except (TypeError, ValueError):
        return None


def safe_float(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_log(value):
    value = safe_float(value)
    return math.log(value) if value and value > 0 else None


def now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


class CachedHttpClient:
    def __init__(self, rate_limit_per_second=5.0):
        self.min_interval = 1.0 / rate_limit_per_second
        self.last_request_at = 0.0

    def _sleep(self):
        elapsed = time.monotonic() - self.last_request_at
        if elapsed < self.min_interval:
            time.sleep(self.min_interval - elapsed)
        self.last_request_at = time.monotonic()

    def get_json(self, url: str, cache_path: Path | None = None, host: str | None = None, timeout=30, save_cache=True):
        if cache_path and cache_path.exists():
            return json.loads(cache_path.read_text(encoding="utf-8")), "cache"
        headers = {"User-Agent": USER_AGENT}
        if host:
            headers["Host"] = host
        req = Request(url, headers=headers)
        max_attempts = 4
        last_status = "request_failed"
        for attempt in range(1, max_attempts + 1):
            self._sleep()
            try:
                SEC_LOG.info("GET %s attempt=%s", url, attempt)
                with urlopen(req, timeout=timeout) as response:
                    payload = response.read()
                    if response.headers.get("Content-Encoding") == "gzip":
                        payload = gzip.decompress(payload)
                    parsed = json.loads(payload.decode("utf-8"))
                    if cache_path and save_cache:
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        cache_path.write_text(json.dumps(parsed), encoding="utf-8")
                    SEC_LOG.info("OK %s", url)
                    return parsed, "downloaded"
            except HTTPError as exc:
                last_status = f"http_{exc.code}"
                SEC_LOG.info("HTTP_ERROR %s status=%s attempt=%s", url, exc.code, attempt)
                if exc.code in {403, 404}:
                    return None, last_status
                time.sleep(min(30, 2**attempt))
            except (URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
                last_status = type(exc).__name__
                SEC_LOG.info("REQUEST_ERROR %s error=%s attempt=%s", url, last_status, attempt)
                time.sleep(min(30, 2**attempt))
        return None, last_status

    def get_text(self, url: str, cache_path: Path | None = None, timeout=20, save_cache=True):
        if cache_path and cache_path.exists():
            return cache_path.read_text(encoding="utf-8", errors="ignore"), "cache"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 Chrome/120 Safari/537.36 "
                f"BNPL research {git_config_value('user.email') or 'august2004515@gmail.com'}"
            )
        }
        req = Request(url, headers=headers)
        self._sleep()
        try:
            with urlopen(req, timeout=timeout) as response:
                payload = response.read()
                if response.headers.get("Content-Encoding") == "gzip":
                    payload = gzip.decompress(payload)
                text = payload.decode("utf-8", errors="ignore")
                if cache_path and save_cache:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(text, encoding="utf-8")
                return text, "downloaded"
        except Exception as exc:  # noqa: BLE001 - log evidence failures without stopping pipeline.
            return "", type(exc).__name__


SEC_CLIENT = CachedHttpClient(rate_limit_per_second=5.0)
WEB_CLIENT = CachedHttpClient(rate_limit_per_second=1.5)


def companyfacts_path(cik: str) -> Path:
    return OUTPUT_DIR / "cache" / "companyfacts" / f"CIK{padded_cik(cik)}.json"


def submissions_path(cik: str) -> Path:
    return OUTPUT_DIR / "cache" / "submissions" / f"CIK{padded_cik(cik)}.json"


def web_cache_path(label: str) -> Path:
    digest = hashlib.sha1(label.encode("utf-8")).hexdigest()[:16]
    safe = re.sub(r"[^A-Za-z0-9]+", "_", label)[:80].strip("_")
    return OUTPUT_DIR / "cache" / "web_verification" / f"{safe}_{digest}.html"


def ensure_submission(cik: str, save_cache=True):
    cik10 = padded_cik(cik)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    return SEC_CLIENT.get_json(url, submissions_path(cik10), host="data.sec.gov", save_cache=save_cache)


def ensure_companyfacts(cik: str):
    cik10 = padded_cik(cik)
    target = companyfacts_path(cik10)
    if target.exists():
        return target, "cache"
    for source_dir in SOURCE_COMPANYFACTS_DIRS:
        source = source_dir / f"CIK{cik10}.json"
        if source.exists():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            SEC_LOG.info("Copied CompanyFacts cache for CIK%s from %s", cik10, source_dir)
            return target, "copied_existing_cache"
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json"
    parsed, status = SEC_CLIENT.get_json(url, target, host="data.sec.gov", save_cache=True)
    return (target if parsed else None), status


DETAILED_TO_BROAD = {
    "Health & Beauty": "Apparel & Personal Care",
    "Clothing & Accessories": "Apparel & Personal Care",
    "Toys & Hobbies": "Kids & Toys",
    "Home & Appliances": "Home & Appliances",
    "TV & Audio": "Electronics & Technology",
    "Sports & Outdoor": "Sports & Leisure",
    "Computers & Tablets": "Electronics & Technology",
    "Home Improvement": "Home & Appliances",
    "Photography": "Electronics & Technology",
    "Gaming & Entertainment": "Entertainment",
    "Phones & Smartwatches": "Electronics & Technology",
    "Kids & Family": "Kids & Toys",
    "Automotive": "Automotive",
    "Garden & Patio": "Sports & Leisure",
    "Kitchen Appliances": "Home & Appliances",
    "Home Appliances": "Home & Appliances",
    "Books, Movies & Music": "Entertainment",
}


CATEGORY_KEYWORDS = [
    ("Health & Beauty", ["beauty", "cosmetic", "cosmetics", "skin", "hair", "health", "pharmacy", "drug", "personal care", "fragrance", "vitamin"]),
    ("Clothing & Accessories", ["clothing", "apparel", "fashion", "accessories", "accessory", "jewelry", "shoes", "shoe", "footwear", "luxury", "department store"]),
    ("Toys & Hobbies", ["toy", "toys", "hobby", "hobbies", "baby gear"]),
    ("Home & Appliances", ["home", "furniture", "furnishings", "bed", "bath", "housewares", "appliance", "decor", "floor"]),
    ("TV & Audio", ["tv", "audio", "television", "radio", "speakers", "electronics store"]),
    ("Sports & Outdoor", ["sport", "sports", "outdoor", "fitness", "athletic", "activewear", "camping", "hunting"]),
    ("Computers & Tablets", ["computer", "tablet", "software", "hardware", "semiconductor", "pc"]),
    ("Home Improvement", ["home improvement", "hardware store", "building material", "paint", "lawn"]),
    ("Photography", ["photo", "camera", "photography", "imaging"]),
    ("Gaming & Entertainment", ["game", "gaming", "entertainment", "ticket", "travel", "hotel", "airline", "cruise", "resort", "leisure", "restaurant"]),
    ("Phones & Smartwatches", ["phone", "wireless", "smartwatch", "telecommunication"]),
    ("Kids & Family", ["kids", "children", "childrens", "baby", "family"]),
    ("Automotive", ["auto", "automotive", "car", "vehicle", "motorcycle", "parts"]),
    ("Garden & Patio", ["garden", "patio", "seasonal", "lawn"]),
    ("Kitchen Appliances", ["kitchen"]),
    ("Home Appliances", ["appliances"]),
    ("Books, Movies & Music", ["book", "books", "movie", "music", "publishing"]),
]


SIC_CATEGORY_RULES = [
    ((5600, 5699), "Clothing & Accessories", "HIGH"),
    ((2300, 2399), "Clothing & Accessories", "MEDIUM"),
    ((3100, 3199), "Clothing & Accessories", "MEDIUM"),
    ((5944, 5944), "Clothing & Accessories", "HIGH"),
    ((5948, 5948), "Clothing & Accessories", "HIGH"),
    ((2844, 2844), "Health & Beauty", "HIGH"),
    ((5912, 5912), "Health & Beauty", "HIGH"),
    ((5712, 5719), "Home & Appliances", "HIGH"),
    ((5722, 5722), "Home Appliances", "HIGH"),
    ((5731, 5731), "TV & Audio", "HIGH"),
    ((5734, 5734), "Computers & Tablets", "HIGH"),
    ((5200, 5251), "Home Improvement", "HIGH"),
    ((5261, 5261), "Garden & Patio", "HIGH"),
    ((5945, 5945), "Toys & Hobbies", "HIGH"),
    ((3940, 3949), "Toys & Hobbies", "MEDIUM"),
    ((5941, 5941), "Sports & Outdoor", "HIGH"),
    ((3949, 3949), "Sports & Outdoor", "MEDIUM"),
    ((5942, 5942), "Books, Movies & Music", "HIGH"),
    ((3650, 3652), "TV & Audio", "MEDIUM"),
    ((3570, 3579), "Computers & Tablets", "MEDIUM"),
    ((3661, 3669), "Phones & Smartwatches", "LOW"),
    ((4512, 4512), "Gaming & Entertainment", "LOW"),
    ((4400, 4499), "Gaming & Entertainment", "LOW"),
    ((7011, 7011), "Gaming & Entertainment", "LOW"),
    ((7800, 7999), "Gaming & Entertainment", "MEDIUM"),
    ((5531, 5531), "Automotive", "HIGH"),
    ((5500, 5599), "Automotive", "HIGH"),
    ((3711, 3714), "Automotive", "MEDIUM"),
    ((5961, 5961), "Clothing & Accessories", "LOW"),
    ((5311, 5399), "Clothing & Accessories", "LOW"),
    ((5810, 5819), "Gaming & Entertainment", "LOW"),
]


INCLUDE_SIC_RANGES = [
    (2000, 2099), (2300, 2399), (2500, 2599), (2844, 2844), (3100, 3199),
    (3570, 3579), (3650, 3669), (3711, 3714), (3940, 3949), (4400, 4512),
    (4700, 4799), (5200, 5999), (7011, 7011), (7030, 7039), (7800, 7999),
]

EXCLUDE_SIC_RANGES = [
    (100, 1999), (4000, 4399), (4900, 4999), (6000, 6799), (8000, 8999),
]

EXCLUDED_NAME_TOKENS = [
    "etf", "fund", "trust", "acquisition", "spac", "blank check", "bank", "bancorp",
    "insurance", "reit", "mortgage", "mining", "gold", "oil", "gas", "energy",
    "resources", "capital", "asset management", "biotech", "therapeutics",
    "pharmaceutical", "pharmaceuticals", "pharma", "biopharma", "biosciences",
    "systems", "networks", "cloud", "software", "cyber", "semiconductor",
]


def sic_int(value) -> int | None:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return None


def in_ranges(value: int | None, ranges) -> bool:
    if value is None:
        return False
    return any(lo <= value <= hi for lo, hi in ranges)


def classify_product_category(name: str, sic_code="", sic_description="", categories_text=""):
    sic = sic_int(sic_code)
    for (lo, hi), detailed, confidence in SIC_CATEGORY_RULES:
        if sic is not None and lo <= sic <= hi:
            return detailed, DETAILED_TO_BROAD.get(detailed, "REVIEW"), confidence
    text = " ".join([name or "", sic_description or "", categories_text or ""]).lower()
    for detailed, keywords in CATEGORY_KEYWORDS:
        if any(k in text for k in keywords):
            return detailed, DETAILED_TO_BROAD.get(detailed, "REVIEW"), "MEDIUM"
    return "", "", "REVIEW"


def size_bucket_from_revenue(revenue: float | None) -> str:
    if revenue is None or pd.isna(revenue):
        return "Unclassified"
    if revenue >= 10_000_000_000:
        return "Large-scale revenue proxy"
    if revenue >= 2_000_000_000:
        return "Mid-scale revenue proxy"
    if revenue >= 300_000_000:
        return "Small-scale revenue proxy"
    return "Micro-scale revenue proxy"


def read_csv_dicts(path: Path):
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def load_treated_reference():
    LOGGER.info("STEP 1/14: loading treated public-company universe")
    crosswalk = read_csv_dicts(PUBLIC_CROSSWALK)
    panel = pd.read_csv(PUBLIC_PANEL)
    ownership = pd.read_json(MERCHANT_OWNERSHIP_ROWS)
    ownership["cik10"] = ownership["cik"].apply(lambda x: padded_cik(x) if str(x).strip() else "")
    public_ownership = ownership[ownership["ownership_type"].astype(str).str.lower().str.startswith("public")].copy()

    panel["CIK10"] = panel["CIK"].apply(padded_cik)
    treated_ciks = sorted({padded_cik(row["CIK"]) for row in crosswalk if row.get("CIK")})
    merchant_groups = public_ownership.groupby("cik10")
    covariates = compute_pre_covariates(panel, id_col="CIK10")

    rows = []
    for row in crosswalk:
        cik10 = padded_cik(row.get("CIK"))
        group = merchant_groups.get_group(cik10) if cik10 in merchant_groups.groups else pd.DataFrame()
        categories = sorted({c.strip() for v in group.get("categories", []) for c in str(v).split(";") if c.strip()})
        category_text = "; ".join(categories)
        detailed, broad, conf = classify_product_category(row.get("input_public_parent_company", ""), "", "", category_text)
        sub, sub_status = ensure_submission(cik10, save_cache=True)
        sic = clean_text((sub or {}).get("sic", ""))
        sic_desc = clean_text((sub or {}).get("sicDescription", ""))
        if sic:
            detailed_sic, broad_sic, conf_sic = classify_product_category(row.get("input_public_parent_company", ""), sic, sic_desc, category_text)
            if detailed_sic:
                detailed, broad, conf = detailed_sic, broad_sic, conf_sic
        cov = covariates.get(cik10, {})
        rows.append(
            {
                "CIK": cik10,
                "public_parent_company": clean_text(row.get("input_public_parent_company")),
                "ticker": clean_text(row.get("ticker")),
                "exchange": clean_text(row.get("exchange")),
                "merchant_names": clean_text(row.get("merchant_names")),
                "merchant_count": int(float(row.get("merchant_count") or 0)),
                "bnpl_providers": clean_text(row.get("bnpl_providers")),
                "merchant_categories": category_text,
                "sic_code": sic,
                "sic_description": sic_desc,
                "detailed_bnpl_category": detailed,
                "broad_bnpl_category": broad,
                "category_confidence": conf,
                "submissions_status": sub_status,
                **cov,
            }
        )
    LOGGER.info("Treated CIKs detected: %s", len(treated_ciks))
    return rows, set(treated_ciks), panel, ownership


def compute_pre_covariates(panel: pd.DataFrame, id_col="CIK"):
    covariates = {}
    data = panel.copy()
    data[id_col] = data[id_col].apply(padded_cik)
    data["fiscal_year"] = pd.to_numeric(data["fiscal_year"], errors="coerce")
    pre = data[(data["fiscal_year"] >= 2015) & (data["fiscal_year"] <= 2019)].copy()
    for col in [
        "revenue", "gross_profit", "operating_income", "net_income", "total_assets",
        "total_liabilities", "stockholders_equity", "cash_and_cash_equivalents",
        "inventory", "sga_expense", "gross_margin", "operating_margin", "net_margin",
        "revenue_growth_yoy",
    ]:
        if col in pre.columns:
            pre[col] = pd.to_numeric(pre[col], errors="coerce")

    for cik, group in pre.groupby(id_col):
        group = group.sort_values(["fiscal_year", "fiscal_quarter"])
        fy2019 = group[group["fiscal_year"] == 2019]
        revenue_2019 = fy2019["revenue"].dropna().sum() if fy2019["revenue"].notna().sum() >= 3 else np.nan
        latest_2019 = fy2019[fy2019["total_assets"].notna()].tail(1)
        assets_2019 = latest_2019["total_assets"].iloc[0] if not latest_2019.empty else np.nan
        latest_bs = group[group["total_assets"].notna()].tail(1)
        total_assets_latest = latest_bs["total_assets"].iloc[0] if not latest_bs.empty else np.nan
        total_liabilities_latest = latest_bs["total_liabilities"].iloc[0] if not latest_bs.empty and "total_liabilities" in latest_bs else np.nan
        cash_latest = latest_bs["cash_and_cash_equivalents"].iloc[0] if not latest_bs.empty and "cash_and_cash_equivalents" in latest_bs else np.nan
        equity_latest = latest_bs["stockholders_equity"].iloc[0] if not latest_bs.empty and "stockholders_equity" in latest_bs else np.nan
        inventory_latest = latest_bs["inventory"].iloc[0] if not latest_bs.empty and "inventory" in latest_bs else np.nan

        margin_window = group[(group["fiscal_year"] >= 2017) & (group["fiscal_year"] <= 2019)]
        revenue_by_year = group.groupby("fiscal_year")["revenue"].sum(min_count=3).dropna()
        if len(revenue_by_year) >= 2 and revenue_by_year.iloc[0] > 0:
            years = revenue_by_year.index.to_list()
            revenue_cagr = (revenue_by_year.iloc[-1] / revenue_by_year.iloc[0]) ** (1 / (years[-1] - years[0])) - 1 if years[-1] > years[0] else np.nan
        else:
            revenue_cagr = np.nan

        def slope(series):
            y = series.dropna()
            if len(y) < 6:
                return np.nan
            x = np.arange(len(y), dtype=float)
            return float(np.polyfit(x, y.astype(float), 1)[0])

        rev_series = group["revenue"].replace(0, np.nan).dropna()
        revenue_pretrend = slope(np.log(rev_series)) if len(rev_series) >= 6 else np.nan
        gross_margin_pretrend = slope(group["gross_margin"])
        operating_margin_pretrend = slope(group["operating_margin"])

        covariates[cik] = {
            "baseline_revenue": None if pd.isna(revenue_2019) else float(revenue_2019),
            "baseline_assets": None if pd.isna(assets_2019) else float(assets_2019),
            "baseline_market_cap_if_available": None,
            "log_revenue_2019": safe_log(revenue_2019),
            "log_assets_2019": safe_log(assets_2019),
            "size_bucket": size_bucket_from_revenue(None if pd.isna(revenue_2019) else float(revenue_2019)),
            "size_bucket_basis": "FY2019 revenue proxy; historical market cap not constructed",
            "average_revenue_growth_pre": none_if_nan(margin_window["revenue_growth_yoy"].mean()),
            "revenue_cagr_pre": none_if_nan(revenue_cagr),
            "average_gross_margin_pre": none_if_nan(margin_window["gross_margin"].mean()),
            "average_operating_margin_pre": none_if_nan(margin_window["operating_margin"].mean()),
            "average_net_margin_pre": none_if_nan(margin_window["net_margin"].mean()),
            "leverage_pre": none_if_nan(total_liabilities_latest / total_assets_latest if total_assets_latest not in (0, np.nan) else np.nan),
            "cash_to_assets_pre": none_if_nan(cash_latest / total_assets_latest if total_assets_latest not in (0, np.nan) else np.nan),
            "equity_to_assets_pre": none_if_nan(equity_latest / total_assets_latest if total_assets_latest not in (0, np.nan) else np.nan),
            "inventory_to_assets_pre": none_if_nan(inventory_latest / total_assets_latest if total_assets_latest not in (0, np.nan) else np.nan),
            "sga_to_revenue_pre": none_if_nan(margin_window["sga_expense"].sum() / margin_window["revenue"].sum() if margin_window["revenue"].sum() else np.nan),
            "revenue_pretrend": none_if_nan(revenue_pretrend),
            "gross_margin_pretrend": none_if_nan(gross_margin_pretrend),
            "operating_margin_pretrend": none_if_nan(operating_margin_pretrend),
            "pre_observation_count": int(group["revenue"].notna().sum()),
            "limited_history_pre": bool(group["revenue"].notna().sum() < 8),
        }
    return covariates


def none_if_nan(value):
    try:
        if pd.isna(value):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def load_sec_ticker_universe():
    data = json.loads(SEC_TICKERS_EXCHANGE_CACHE.read_text(encoding="utf-8"))
    fields = data["fields"]
    return [dict(zip(fields, row)) for row in data["data"]]


def candidate_name_excluded(name: str) -> bool:
    text = name.lower()
    return any(token in text for token in EXCLUDED_NAME_TOKENS)


def build_candidate_donor_pool(treated_ciks: set[str]):
    LOGGER.info("STEP 3/14: building candidate donor pool from SEC ticker universe")
    universe = load_sec_ticker_universe()
    rows = []
    scanned = 0
    relevant = 0
    allowed_exchanges = {"Nasdaq", "NYSE", "NYSE American", "NYSE Arca", "OTC"}
    for item in universe:
        if scanned >= SEC_SCAN_LIMIT:
            break
        cik10 = padded_cik(item.get("cik"))
        name = clean_text(item.get("name"))
        exchange = clean_text(item.get("exchange"))
        if cik10 in treated_ciks or exchange not in allowed_exchanges or candidate_name_excluded(name):
            continue
        scanned += 1
        sub, status = ensure_submission(cik10, save_cache=False)
        if scanned % 250 == 0:
            LOGGER.info("SEC submissions scanned=%s relevant_candidates=%s", scanned, relevant)
        if not sub:
            continue
        sic = clean_text(sub.get("sic", ""))
        sic_desc = clean_text(sub.get("sicDescription", ""))
        sicn = sic_int(sic)
        if in_ranges(sicn, EXCLUDE_SIC_RANGES) and not in_ranges(sicn, INCLUDE_SIC_RANGES):
            continue
        if not in_ranges(sicn, INCLUDE_SIC_RANGES):
            continue
        detailed, broad, confidence = classify_product_category(name, sic, sic_desc, "")
        if not broad:
            continue
        ensure_submission(cik10, save_cache=True)
        relevant += 1
        rows.append(
            {
                "candidate_id": f"CTRL_CAND_RAW_{relevant:04d}",
                "sec_universe_rank": scanned,
                "company_name": name,
                "ticker": clean_text(item.get("ticker")),
                "CIK": cik10,
                "exchange": exchange,
                "sic_code": sic,
                "sic_description": sic_desc,
                "detailed_bnpl_category": detailed,
                "broad_bnpl_category": broad,
                "category_confidence": confidence,
                "candidate_source": "SEC company_tickers_exchange.json + SEC submissions SIC",
                "candidate_source_url": "https://www.sec.gov/files/company_tickers_exchange.json; https://data.sec.gov/submissions/CIK##########.json",
                "candidate_screening_status": "candidate_pool",
                "manual_review_required": confidence in {"LOW", "REVIEW"},
            }
        )
    if len(rows) > DONOR_POOL_TARGET:
        idx = np.linspace(0, len(rows) - 1, DONOR_POOL_TARGET, dtype=int)
        selected_positions = set(int(i) for i in idx)
        selected_rows = [row for pos, row in enumerate(rows) if pos in selected_positions]
        rows = selected_rows
    for idx, row in enumerate(rows, 1):
        row["candidate_id"] = f"CTRL_CAND_{idx:04d}"
    LOGGER.info("Candidate donor pool created: %s selected relevant firms from %s scanned SEC issuers", len(rows), scanned)
    return rows


def load_existing_bnpl_names(ownership: pd.DataFrame):
    names = set()
    parent_names = set()
    cik_set = set()
    for _, row in ownership.iterrows():
        merchant = canonical_name(row.get("merchant_name", ""))
        if merchant:
            names.add(merchant)
        parent = canonical_name(row.get("sec_matched_company", ""))
        if parent and str(row.get("ownership_type", "")).lower().startswith("public"):
            parent_names.add(parent)
        cik = str(row.get("cik", "")).strip()
        if cik and cik.lower() != "nan":
            cik_set.add(padded_cik(cik))
    return names, parent_names, cik_set


PROVIDER_TERMS = [
    "affirm", "klarna", "afterpay", "zip", "quadpay", "sezzle", "paypal pay later",
    "pay in 4", "shop pay installments", "bread pay", "splitit", "buy now pay later",
    "installment checkout", "monthly payments",
]


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return clean_text(html.unescape(text))


def extract_links(text: str):
    links = []
    for match in re.finditer(r'href="([^"]+)"', text):
        link = html.unescape(match.group(1))
        if link.startswith("http") and not any(skip in link for skip in ["bing.com/search", "go.microsoft.com"]):
            links.append(link)
    return links[:8]


def web_bnpl_search(company: str, ticker: str, final_pass=False):
    query = f'"{company}" BNPL Affirm Klarna Afterpay Zip Sezzle "buy now pay later"'
    if final_pass:
        query = f'"{company}" "Affirm" OR "Klarna" OR "Afterpay" OR "Sezzle" OR "PayPal Pay Later" OR "Shop Pay Installments"'
    url = "https://www.bing.com/search?q=" + quote_plus(query)
    label = ("final_" if final_pass else "initial_") + query
    text, status = WEB_CLIENT.get_text(url, web_cache_path(label))
    if not text:
        return {
            "search_query": query,
            "source_type": "web_search",
            "source_name": "Bing Search",
            "source_url": url,
            "source_date": "",
            "bnpl_provider_if_any": "",
            "evidence_result": "search_failed",
            "evidence_summary": f"Search failed: {status}",
            "reliability": "LOW",
        }
    result_blocks = re.findall(r'(?is)<li class="b_algo".*?</li>', text)[:10]
    cleaned_blocks = [strip_html(block).lower() for block in result_blocks]
    cleaned = " ".join(cleaned_blocks)
    if not cleaned:
        cleaned = strip_html(text).lower().replace(query.lower(), " ")
    links = []
    for block in result_blocks:
        links.extend(extract_links(block))
    if not links:
        links = extract_links(text)
    provider_hits = [term for term in PROVIDER_TERMS if term in cleaned]
    provider_domain_hits = [
        term
        for term in ["affirm", "klarna", "afterpay", "sezzle", "zip.co", "breadpay", "shopify"]
        if any(term in link.lower() for link in links)
    ]
    company_tokens = [tok for tok in canonical_name(company).split() if len(tok) >= 4][:3]
    company_seen = any(tok in cleaned for tok in company_tokens) or (ticker and ticker.lower() in cleaned)
    result = "no_relevant_evidence"
    reliability = "MEDIUM"
    summary = "Search completed; no clear BNPL exposure signal detected in result text."
    if provider_domain_hits and company_seen:
        result = "confirmed_bnpl"
        summary = f"Provider-domain result(s) appeared in search results: {', '.join(sorted(set(provider_domain_hits)))}."
        reliability = "MEDIUM"
    elif provider_hits and company_seen and any(word in cleaned for word in ["checkout", "installment", "pay later", "pay in 4", "monthly payment"]):
        result = "possible_bnpl"
        summary = f"Provider/payment terms appeared in search result text: {', '.join(sorted(set(provider_hits))[:5])}."
        reliability = "LOW"
    return {
        "search_query": query,
        "source_type": "web_search",
        "source_name": "Bing Search",
        "source_url": url,
        "source_date": "",
        "bnpl_provider_if_any": "; ".join(sorted(set(provider_hits + provider_domain_hits))),
        "evidence_result": result,
        "evidence_summary": summary + (" Top links: " + "; ".join(links[:3]) if links else ""),
        "reliability": reliability,
    }


def verify_bnpl_exposure(candidates, ownership: pd.DataFrame, final_candidates: set[str] | None = None):
    LOGGER.info("STEP 4/14: verifying BNPL exposure for %s candidates", len(candidates))
    merchant_names, public_parent_names, known_bnpl_ciks = load_existing_bnpl_names(ownership)
    log_rows = []
    final_candidates = final_candidates or set()
    verified = []
    for idx, row in enumerate(candidates, 1):
        cik = row["CIK"]
        company = row["company_name"]
        canonical = canonical_name(company)
        current_hit = cik in known_bnpl_ciks or canonical in merchant_names or canonical in public_parent_names
        current_result = "confirmed_bnpl" if current_hit else "no_relevant_evidence"
        current_summary = "Candidate matched current BNPL merchant/public-parent data." if current_hit else "No exact CIK or canonical-name match in current BNPL merchant dataset."
        log_rows.append(
            {
                "candidate_company": company,
                "ticker": row.get("ticker", ""),
                "CIK": cik,
                "search_query": "current BNPL merchant dataset exact CIK/canonical-name check",
                "source_type": "internal_dataset",
                "source_name": "BNPL merchant and ownership files",
                "source_url": str(MERCHANT_OWNERSHIP_ROWS),
                "source_date": "",
                "bnpl_provider_if_any": "current BNPL directory" if current_hit else "",
                "evidence_result": current_result,
                "evidence_summary": current_summary,
                "reliability": "HIGH",
                "retrieved_at": RETRIEVED_AT,
            }
        )
        web_result = web_bnpl_search(company, row.get("ticker", ""), final_pass=cik in final_candidates)
        web_result.update({"candidate_company": company, "ticker": row.get("ticker", ""), "CIK": cik, "retrieved_at": RETRIEVED_AT})
        log_rows.append(web_result)
        evidence_results = {current_result, web_result["evidence_result"]}
        if "confirmed_bnpl" in evidence_results:
            status = "BNPL_EVIDENCE_FOUND"
        elif "possible_bnpl" in evidence_results or "ambiguous" in evidence_results:
            status = "AMBIGUOUS"
        elif "search_failed" in evidence_results:
            status = "REVIEW"
        else:
            status = "NO_BNPL_EVIDENCE"
        updated = dict(row)
        updated["bnpl_control_status"] = status
        updated["bnpl_verification_summary"] = web_result["evidence_summary"] if not current_hit else current_summary
        updated["manual_review_required"] = bool(updated.get("manual_review_required")) or status in {"AMBIGUOUS", "REVIEW"}
        verified.append(updated)
        BNPL_LOG.info("%s/%s CIK%s %s status=%s", idx, len(candidates), cik, company, status)
        if idx % 50 == 0:
            LOGGER.info("BNPL verification progress: %s/%s candidates checked", idx, len(candidates))
    return verified, log_rows


def crosswalk_for_candidate(row):
    return {
        "CIK": row["CIK"],
        "unique_company_id": row["CIK"],
        "sec_entity_name": "",
        "input_public_parent_company": row["company_name"],
        "ticker": row.get("ticker", ""),
        "exchange": row.get("exchange", ""),
        "merchant_names": "",
        "canonical_merchant_names": "",
        "merchant_count": 0,
        "input_public_merchant_rows": 0,
        "bnpl_providers": "",
        "companyfacts_status": "",
        "submissions_status": "",
        "sec_companyfacts_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{row['CIK']}.json",
        "sec_submissions_url": f"https://data.sec.gov/submissions/CIK{row['CIK']}.json",
    }


def extract_panels_for_candidates(candidates, purpose="pre_matching"):
    LOGGER.info("STEP 7/14: extracting SEC CompanyFacts panels for %s %s candidates", len(candidates), purpose)
    panel_rows = []
    source_audit = []
    annual_refs = []
    metadata = []
    statuses = {}
    for idx, row in enumerate(candidates, 1):
        cik = row["CIK"]
        cf_path, cf_status = ensure_companyfacts(cik)
        statuses[cik] = cf_status
        if idx % 25 == 0:
            LOGGER.info("CompanyFacts progress for %s: %s/%s", purpose, idx, len(candidates))
        if not cf_path:
            ERROR_LOG.info("CompanyFacts unavailable for CIK%s %s: %s", cik, row.get("company_name"), cf_status)
            continue
        try:
            cw = crosswalk_for_candidate(row)
            cw["companyfacts_status"] = cf_status
            rows, audit, meta, annual = extract_company_panel(cf_path, cw, RETRIEVED_AT)
            for out in rows:
                out["sample_group"] = "control"
            panel_rows.extend(rows)
            source_audit.extend(audit)
            annual_refs.extend(annual)
            metadata.append(meta)
        except Exception as exc:  # noqa: BLE001
            ERROR_LOG.exception("Failed extracting CIK%s %s: %s", cik, row.get("company_name"), exc)
    panel = pd.DataFrame(panel_rows)
    return panel, source_audit, annual_refs, metadata, statuses


MATCHING_VARIABLES = [
    "log_revenue_2019",
    "log_assets_2019",
    "average_gross_margin_pre",
    "average_operating_margin_pre",
    "average_revenue_growth_pre",
    "leverage_pre",
    "cash_to_assets_pre",
    "revenue_pretrend",
    "gross_margin_pretrend",
    "operating_margin_pretrend",
]


def attach_covariates_to_candidates(candidates, candidate_panel: pd.DataFrame):
    if candidate_panel.empty:
        return candidates
    panel = candidate_panel.copy()
    panel["CIK10"] = panel["CIK"].apply(padded_cik)
    covariates = compute_pre_covariates(panel, id_col="CIK10")
    rows = []
    for row in candidates:
        cov = covariates.get(row["CIK"], {})
        updated = dict(row)
        updated.update(cov)
        updated["candidate_screening_status"] = "eligible_financials" if cov.get("baseline_revenue") and cov.get("baseline_assets") else "insufficient_pre_financials"
        updated["manual_review_required"] = bool(updated.get("manual_review_required")) or bool(cov.get("limited_history_pre")) or updated["candidate_screening_status"] != "eligible_financials"
        rows.append(updated)
    return rows


def zscore_table(treated_rows, candidate_rows):
    values = defaultdict(list)
    for row in treated_rows + candidate_rows:
        for var in MATCHING_VARIABLES:
            val = safe_float(row.get(var))
            if val is not None and math.isfinite(val):
                values[var].append(val)
    stats = {}
    for var in MATCHING_VARIABLES:
        arr = np.array(values[var], dtype=float)
        stats[var] = {
            "mean": float(np.nanmean(arr)) if len(arr) else 0.0,
            "std": float(np.nanstd(arr, ddof=1)) if len(arr) > 1 and np.nanstd(arr, ddof=1) > 0 else 1.0,
        }
    return stats


def distance_between(treated, control, stats):
    pieces = {}
    sq = []
    for var in MATCHING_VARIABLES:
        tv = safe_float(treated.get(var))
        cv = safe_float(control.get(var))
        if tv is None or cv is None or not math.isfinite(tv) or not math.isfinite(cv):
            pieces[var] = None
            continue
        d = ((tv - stats[var]["mean"]) / stats[var]["std"]) - ((cv - stats[var]["mean"]) / stats[var]["std"])
        pieces[var] = abs(float(d))
        sq.append(d * d)
    base = math.sqrt(sum(sq) / len(sq)) if sq else 2.5
    category_penalty = 0.0
    if treated.get("broad_bnpl_category") and control.get("broad_bnpl_category") and treated["broad_bnpl_category"] == control["broad_bnpl_category"]:
        category_penalty = 0.0
    elif str(treated.get("sic_code", ""))[:2] and str(treated.get("sic_code", ""))[:2] == str(control.get("sic_code", ""))[:2]:
        category_penalty = 0.25
    else:
        category_penalty = 0.75
    size_penalty = 0.0 if treated.get("size_bucket") == control.get("size_bucket") else 0.15
    return base + category_penalty + size_penalty, pieces


def match_quality(distance, same_broad, same_sic2):
    if distance <= 0.90 and same_broad:
        return "HIGH"
    if distance <= 1.65 and (same_broad or same_sic2):
        return "MEDIUM"
    if distance <= 2.40:
        return "LOW"
    return "REVIEW"


def perform_matching(treated_rows, candidate_rows):
    LOGGER.info("STEP 9/14: performing transparent nearest-neighbor matching")
    eligible = [
        row for row in candidate_rows
        if row.get("bnpl_control_status") == "NO_BNPL_EVIDENCE"
        and row.get("baseline_revenue") is not None
        and row.get("baseline_assets") is not None
    ]
    stats = zscore_table(treated_rows, eligible)
    selected = set()
    matching_rows = []
    expanded_selected = defaultdict(list)
    for treated in treated_rows:
        scored = []
        for control in eligible:
            if control["CIK"] in selected:
                continue
            distance, pieces = distance_between(treated, control, stats)
            same_broad = bool(treated.get("broad_bnpl_category") and treated.get("broad_bnpl_category") == control.get("broad_bnpl_category"))
            same_sic2 = str(treated.get("sic_code", ""))[:2] == str(control.get("sic_code", ""))[:2]
            scored.append((distance, control, pieces, same_broad, same_sic2))
        if not scored:
            break
        scored.sort(key=lambda item: item[0])
        for rank, (distance, control, pieces, same_broad, same_sic2) in enumerate(scored[:EXPANDED_PER_TREATED], 1):
            expanded_selected[control["CIK"]].append(treated["CIK"])
            if rank == 1:
                selected.add(control["CIK"])
                quality = match_quality(distance, same_broad, same_sic2)
                matching_rows.append(
                    {
                        "treated_CIK": treated["CIK"],
                        "treated_company": treated["public_parent_company"],
                        "treated_broad_category": treated.get("broad_bnpl_category", ""),
                        "treated_sic": treated.get("sic_code", ""),
                        "treated_size_bucket": treated.get("size_bucket", ""),
                        "control_CIK": control["CIK"],
                        "control_company": control["company_name"],
                        "control_broad_category": control.get("broad_bnpl_category", ""),
                        "control_sic": control.get("sic_code", ""),
                        "control_size_bucket": control.get("size_bucket", ""),
                        "distance_revenue": pieces.get("log_revenue_2019"),
                        "distance_assets": pieces.get("log_assets_2019"),
                        "distance_market_cap_if_available": None,
                        "distance_gross_margin": pieces.get("average_gross_margin_pre"),
                        "distance_operating_margin": pieces.get("average_operating_margin_pre"),
                        "distance_revenue_growth": pieces.get("average_revenue_growth_pre"),
                        "distance_leverage": pieces.get("leverage_pre"),
                        "distance_pretrend": pieces.get("revenue_pretrend"),
                        "overall_match_distance": distance,
                        "match_rank": rank,
                        "match_quality": quality,
                        "replacement_used": False,
                        "notes": "Nearest available control using pre-2020 standardized financial distance plus industry penalties.",
                    }
                )
                MATCH_LOG.info("Matched %s to %s distance=%.4f quality=%s", treated["public_parent_company"], control["company_name"], distance, quality)
        if len(selected) >= PREFERRED_CONTROL_TARGET:
            break

    selected_ciks = {r["control_CIK"] for r in matching_rows}
    candidate_by_cik = {r["CIK"]: dict(r) for r in candidate_rows}
    for cik, row in candidate_by_cik.items():
        row["preferred_control_sample"] = cik in selected_ciks
        row["expanded_control_sample"] = bool(expanded_selected.get(cik))
        row["strict_control_sample"] = row["preferred_control_sample"] and row.get("category_confidence") == "HIGH"
        row["matched_treated_CIK"] = ""
        row["matched_treated_company"] = ""
        row["match_distance"] = None
        row["match_rank"] = None
        row["match_quality"] = ""
    for match in matching_rows:
        row = candidate_by_cik[match["control_CIK"]]
        row["matched_treated_CIK"] = match["treated_CIK"]
        row["matched_treated_company"] = match["treated_company"]
        row["match_distance"] = match["overall_match_distance"]
        row["match_rank"] = match["match_rank"]
        row["match_quality"] = match["match_quality"]
        row["manual_review_required"] = bool(row.get("manual_review_required")) or match["match_quality"] in {"LOW", "REVIEW"}
    return list(candidate_by_cik.values()), matching_rows


def replacement_match_row(treated, control, distance, pieces, quality):
    return {
        "treated_CIK": treated["CIK"],
        "treated_company": treated["public_parent_company"],
        "treated_broad_category": treated.get("broad_bnpl_category", ""),
        "treated_sic": treated.get("sic_code", ""),
        "treated_size_bucket": treated.get("size_bucket", ""),
        "control_CIK": control["CIK"],
        "control_company": control["company_name"],
        "control_broad_category": control.get("broad_bnpl_category", ""),
        "control_sic": control.get("sic_code", ""),
        "control_size_bucket": control.get("size_bucket", ""),
        "distance_revenue": pieces.get("log_revenue_2019"),
        "distance_assets": pieces.get("log_assets_2019"),
        "distance_market_cap_if_available": None,
        "distance_gross_margin": pieces.get("average_gross_margin_pre"),
        "distance_operating_margin": pieces.get("average_operating_margin_pre"),
        "distance_revenue_growth": pieces.get("average_revenue_growth_pre"),
        "distance_leverage": pieces.get("leverage_pre"),
        "distance_pretrend": pieces.get("revenue_pretrend"),
        "overall_match_distance": distance,
        "match_rank": 1,
        "match_quality": quality,
        "replacement_used": True,
        "notes": "Replacement selected after final BNPL contamination screening removed the initially matched control.",
    }


def final_contamination_screen(candidate_rows, matching_rows, treated_rows):
    selected_ciks = {r["control_CIK"] for r in matching_rows}
    selected = [r for r in candidate_rows if r["CIK"] in selected_ciks]
    LOGGER.info("STEP 11/14: final BNPL screening pass for %s preferred controls", len(selected))
    final_verified, final_log = verify_bnpl_exposure(selected, pd.read_json(MERCHANT_OWNERSHIP_ROWS), final_candidates=selected_ciks)
    status_by_cik = {r["CIK"]: r for r in final_verified}
    removed = {cik for cik, row in status_by_cik.items() if row.get("bnpl_control_status") != "NO_BNPL_EVIDENCE"}
    if removed:
        LOGGER.warning("Final screening removed %s selected controls for contamination/review: %s", len(removed), sorted(removed))
    for row in candidate_rows:
        if row["CIK"] in status_by_cik:
            row.update(status_by_cik[row["CIK"]])
        if row["CIK"] in removed:
            row["preferred_control_sample"] = False
            row["manual_review_required"] = True
    removed_matches = [r for r in matching_rows if r["control_CIK"] in removed]
    matching_rows = [r for r in matching_rows if r["control_CIK"] not in removed]

    if removed_matches:
        treated_by_cik = {r["CIK"]: r for r in treated_rows}
        candidate_by_cik = {r["CIK"]: r for r in candidate_rows}
        used = {r["control_CIK"] for r in matching_rows}
        stats = zscore_table(treated_rows, [r for r in candidate_rows if r.get("baseline_revenue") is not None and r.get("baseline_assets") is not None])
        for old_match in removed_matches:
            treated = treated_by_cik.get(old_match["treated_CIK"])
            if not treated:
                continue
            replacement_pool = [
                r for r in candidate_rows
                if r["CIK"] not in used
                and r["CIK"] not in removed
                and r.get("bnpl_control_status") == "NO_BNPL_EVIDENCE"
                and r.get("baseline_revenue") is not None
                and r.get("baseline_assets") is not None
            ]
            scored = []
            for control in replacement_pool:
                distance, pieces = distance_between(treated, control, stats)
                same_broad = bool(treated.get("broad_bnpl_category") and treated.get("broad_bnpl_category") == control.get("broad_bnpl_category"))
                same_sic2 = str(treated.get("sic_code", ""))[:2] == str(control.get("sic_code", ""))[:2]
                scored.append((distance, control, pieces, same_broad, same_sic2))
            scored.sort(key=lambda item: item[0])
            for distance, control, pieces, same_broad, same_sic2 in scored[:10]:
                replacement_verified, replacement_log = verify_bnpl_exposure([control], pd.read_json(MERCHANT_OWNERSHIP_ROWS), final_candidates={control["CIK"]})
                final_log.extend(replacement_log)
                verified = replacement_verified[0]
                candidate_by_cik[control["CIK"]].update(verified)
                if verified.get("bnpl_control_status") != "NO_BNPL_EVIDENCE":
                    candidate_by_cik[control["CIK"]]["manual_review_required"] = True
                    continue
                quality = match_quality(distance, same_broad, same_sic2)
                new_match = replacement_match_row(treated, candidate_by_cik[control["CIK"]], distance, pieces, quality)
                matching_rows.append(new_match)
                used.add(control["CIK"])
                row = candidate_by_cik[control["CIK"]]
                row["preferred_control_sample"] = True
                row["matched_treated_CIK"] = treated["CIK"]
                row["matched_treated_company"] = treated["public_parent_company"]
                row["match_distance"] = distance
                row["match_rank"] = 1
                row["match_quality"] = quality
                row["manual_review_required"] = bool(row.get("manual_review_required")) or quality in {"LOW", "REVIEW"}
                MATCH_LOG.info("Replacement matched %s to %s distance=%.4f quality=%s", treated["public_parent_company"], control["company_name"], distance, quality)
                break
    return candidate_rows, matching_rows, final_log, removed


def balance_diagnostics(treated_rows, control_rows):
    rows = []
    for var in MATCHING_VARIABLES:
        tv = np.array([safe_float(r.get(var)) for r in treated_rows if safe_float(r.get(var)) is not None], dtype=float)
        cv = np.array([safe_float(r.get(var)) for r in control_rows if safe_float(r.get(var)) is not None], dtype=float)
        treated_mean = float(np.nanmean(tv)) if len(tv) else None
        control_mean = float(np.nanmean(cv)) if len(cv) else None
        pooled = None
        smd = None
        if len(tv) > 1 and len(cv) > 1:
            pooled = math.sqrt((np.nanvar(tv, ddof=1) + np.nanvar(cv, ddof=1)) / 2)
            if pooled and pooled > 0 and treated_mean is not None and control_mean is not None:
                smd = (treated_mean - control_mean) / pooled
        flag = "OK"
        if smd is None:
            flag = "REVIEW"
        elif abs(smd) > 0.20:
            flag = "REVIEW"
        elif abs(smd) >= 0.10:
            flag = "MODERATE"
        rows.append(
            {
                "matching_variable": var,
                "treated_mean": treated_mean,
                "control_mean": control_mean,
                "treated_sd": float(np.nanstd(tv, ddof=1)) if len(tv) > 1 else None,
                "control_sd": float(np.nanstd(cv, ddof=1)) if len(cv) > 1 else None,
                "standardized_mean_difference": smd,
                "absolute_smd": abs(smd) if smd is not None else None,
                "balance_flag": flag,
                "notes": "|SMD| < 0.10 preferred; 0.10-0.20 moderate; >0.20 review.",
            }
        )
    return rows


def pretrend_diagnostics(treated_panel: pd.DataFrame, control_panel: pd.DataFrame):
    rows = []
    tp = treated_panel.copy()
    cp = control_panel.copy()
    tp["sample_group"] = "treated"
    cp["sample_group"] = "control"
    for df in [tp, cp]:
        df["period_key"] = df["fiscal_year"].astype(str) + " " + df["fiscal_quarter"].astype(str)
        for col in ["revenue", "revenue_growth_yoy", "gross_margin", "operating_margin"]:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    combined = pd.concat([tp, cp], ignore_index=True)
    combined = combined[(combined["fiscal_year"] >= 2015) & (combined["fiscal_year"] <= 2019)]
    grouped = combined.groupby(["sample_group", "fiscal_year", "fiscal_quarter"], dropna=False)
    stats = grouped.agg(
        firm_count=("CIK", "nunique"),
        average_revenue=("revenue", "mean"),
        average_revenue_growth_yoy=("revenue_growth_yoy", "mean"),
        average_gross_margin=("gross_margin", "mean"),
        average_operating_margin=("operating_margin", "mean"),
    ).reset_index()
    for _, r in stats.iterrows():
        rows.append({k: none_if_nan(v) if isinstance(v, float) else v for k, v in r.to_dict().items()})
    return rows


def build_industry_classification(treated_rows, candidate_rows):
    rows = []
    for sample, source_rows in [("treated", treated_rows), ("candidate_control", candidate_rows)]:
        for row in source_rows:
            rows.append(
                {
                    "sample_group": sample,
                    "CIK": row.get("CIK", ""),
                    "company_name": row.get("public_parent_company") or row.get("company_name", ""),
                    "ticker": row.get("ticker", ""),
                    "sic_code": row.get("sic_code", ""),
                    "sic_description": row.get("sic_description", ""),
                    "detailed_bnpl_category": row.get("detailed_bnpl_category", ""),
                    "broad_bnpl_category": row.get("broad_bnpl_category", ""),
                    "category_confidence": row.get("category_confidence", ""),
                    "secondary_categories": row.get("merchant_categories", ""),
                    "classification_basis": "SEC SIC plus keyword/category mapping; unclear cases flagged REVIEW.",
                }
            )
    return rows


def create_treated_profile(treated_rows):
    rows = []
    def add(profile_type, value, count):
        rows.append({"profile_type": profile_type, "value": value or "Unclassified", "firm_count": count})
    add("number_of_firms", "treated_public_parent_companies", len(treated_rows))
    for key in ["broad_bnpl_category", "detailed_bnpl_category", "size_bucket", "category_confidence"]:
        for value, count in Counter(r.get(key, "") for r in treated_rows).most_common():
            add(key, value, count)
    for var in ["baseline_revenue", "baseline_assets", "average_gross_margin_pre", "average_operating_margin_pre", "average_net_margin_pre"]:
        vals = [safe_float(r.get(var)) for r in treated_rows if safe_float(r.get(var)) is not None]
        if vals:
            add(f"{var}_median", "median", float(np.median(vals)))
            add(f"{var}_mean", "mean", float(np.mean(vals)))
    return rows


def build_control_master(candidate_rows):
    rows = []
    for idx, row in enumerate([r for r in candidate_rows if r.get("preferred_control_sample")], 1):
        rows.append(
            {
                "control_id": f"CONTROL_{idx:04d}",
                "company_name": row.get("company_name", ""),
                "ticker": row.get("ticker", ""),
                "CIK": row.get("CIK", ""),
                "exchange": row.get("exchange", ""),
                "sic_code": row.get("sic_code", ""),
                "sic_description": row.get("sic_description", ""),
                "detailed_bnpl_category": row.get("detailed_bnpl_category", ""),
                "broad_bnpl_category": row.get("broad_bnpl_category", ""),
                "category_confidence": row.get("category_confidence", ""),
                "bnpl_control_status": row.get("bnpl_control_status", ""),
                "baseline_revenue": row.get("baseline_revenue"),
                "baseline_assets": row.get("baseline_assets"),
                "baseline_market_cap_if_available": row.get("baseline_market_cap_if_available"),
                "log_revenue_2019": row.get("log_revenue_2019"),
                "log_assets_2019": row.get("log_assets_2019"),
                "size_bucket": row.get("size_bucket", ""),
                "average_revenue_growth_pre": row.get("average_revenue_growth_pre"),
                "average_gross_margin_pre": row.get("average_gross_margin_pre"),
                "average_operating_margin_pre": row.get("average_operating_margin_pre"),
                "average_net_margin_pre": row.get("average_net_margin_pre"),
                "leverage_pre": row.get("leverage_pre"),
                "cash_to_assets_pre": row.get("cash_to_assets_pre"),
                "revenue_pretrend": row.get("revenue_pretrend"),
                "gross_margin_pretrend": row.get("gross_margin_pretrend"),
                "operating_margin_pretrend": row.get("operating_margin_pretrend"),
                "matched_treated_CIK": row.get("matched_treated_CIK", ""),
                "matched_treated_company": row.get("matched_treated_company", ""),
                "match_distance": row.get("match_distance"),
                "match_rank": row.get("match_rank"),
                "match_quality": row.get("match_quality", ""),
                "preferred_control_sample": row.get("preferred_control_sample", False),
                "expanded_control_sample": row.get("expanded_control_sample", False),
                "manual_review_required": row.get("manual_review_required", False),
            }
        )
    return rows


def custom_validation(treated_ciks, control_master, panel_rows, matching_rows):
    rows = []
    control_ciks = [r["CIK"] for r in control_master]
    duplicate_controls = [cik for cik, n in Counter(control_ciks).items() if n > 1]
    overlap = sorted(set(control_ciks) & treated_ciks)
    bad_bnpl = [r for r in control_master if r.get("bnpl_control_status") != "NO_BNPL_EVIDENCE"]
    key_counts = Counter((r.get("CIK"), r.get("fiscal_year"), r.get("fiscal_quarter")) for r in panel_rows)
    duplicate_panel_keys = [key for key, count in key_counts.items() if count > 1]
    checks = [
        ("treated_overlap_check", "ERROR" if overlap else "INFO", f"Controls overlapping treated CIKs: {len(overlap)}", "; ".join(overlap)),
        ("duplicate_control_cik_check", "ERROR" if duplicate_controls else "INFO", f"Duplicate preferred control CIKs: {len(duplicate_controls)}", "; ".join(duplicate_controls)),
        ("preferred_control_bnpl_status_check", "ERROR" if bad_bnpl else "INFO", f"Preferred controls without NO_BNPL_EVIDENCE: {len(bad_bnpl)}", ""),
        ("matching_uses_pre_2020_check", "INFO", "Matching variables are all constructed from fiscal years 2015-2019.", "; ".join(MATCHING_VARIABLES)),
        ("panel_unique_key_check", "ERROR" if duplicate_panel_keys else "INFO", f"Duplicate CIK x fiscal_year x fiscal_quarter keys: {len(duplicate_panel_keys)}", ""),
        ("match_count_check", "WARNING" if len(matching_rows) < 100 else "INFO", f"Preferred matched controls: {len(matching_rows)}", ""),
    ]
    for name, severity, message, details in checks:
        rows.append({"severity": severity, "check_name": name, "CIK": "", "company": "", "fiscal_year": "", "fiscal_quarter": "", "message": message, "details": details})
    return rows


def create_summary(treated_rows, candidates, control_master, matching_rows, balance_rows, panel_rows, coverage_rows, validation_rows, manual_rows):
    preferred = [r for r in candidates if r.get("preferred_control_sample")]
    expanded = [r for r in candidates if r.get("expanded_control_sample")]
    strict = [r for r in candidates if r.get("strict_control_sample")]
    size_counts = Counter(r.get("size_bucket", "Unclassified") for r in preferred)
    category_counts = Counter(r.get("broad_bnpl_category", "Unclassified") for r in preferred)
    detailed_counts = Counter(r.get("detailed_bnpl_category", "Unclassified") for r in preferred)
    distances = [safe_float(r.get("overall_match_distance")) for r in matching_rows if safe_float(r.get("overall_match_distance")) is not None]
    def coverage(var):
        return sum(1 for r in panel_rows if r.get(var) is not None) / len(panel_rows) if panel_rows else 0
    return {
        "treated_company_count": len(treated_rows),
        "initial_candidate_pool_count": len(candidates),
        "candidate_no_bnpl_evidence_count": sum(1 for r in candidates if r.get("bnpl_control_status") == "NO_BNPL_EVIDENCE"),
        "candidate_confirmed_bnpl_count": sum(1 for r in candidates if r.get("bnpl_control_status") == "BNPL_EVIDENCE_FOUND"),
        "candidate_ambiguous_bnpl_count": sum(1 for r in candidates if r.get("bnpl_control_status") in {"AMBIGUOUS", "REVIEW"}),
        "eligible_control_count": sum(1 for r in candidates if r.get("bnpl_control_status") == "NO_BNPL_EVIDENCE" and r.get("baseline_revenue") is not None and r.get("baseline_assets") is not None),
        "preferred_control_count": len(preferred),
        "expanded_control_count": len(expanded),
        "strict_control_count": len(strict),
        "large_cap_control_count": size_counts.get("Large-scale revenue proxy", 0),
        "mid_cap_control_count": size_counts.get("Mid-scale revenue proxy", 0),
        "small_cap_control_count": size_counts.get("Small-scale revenue proxy", 0),
        "micro_cap_control_count": size_counts.get("Micro-scale revenue proxy", 0),
        "unclassified_size_count": size_counts.get("Unclassified", 0),
        "control_distribution_by_broad_category": dict(category_counts),
        "control_distribution_by_detailed_category": dict(detailed_counts),
        "mean_match_distance": float(np.mean(distances)) if distances else None,
        "median_match_distance": float(np.median(distances)) if distances else None,
        "high_quality_match_count": sum(1 for r in matching_rows if r.get("match_quality") == "HIGH"),
        "medium_quality_match_count": sum(1 for r in matching_rows if r.get("match_quality") == "MEDIUM"),
        "low_quality_match_count": sum(1 for r in matching_rows if r.get("match_quality") == "LOW"),
        "balance_variables_below_0_10_smd": sum(1 for r in balance_rows if safe_float(r.get("absolute_smd")) is not None and safe_float(r.get("absolute_smd")) < 0.10),
        "balance_variables_between_0_10_and_0_20_smd": sum(1 for r in balance_rows if safe_float(r.get("absolute_smd")) is not None and 0.10 <= safe_float(r.get("absolute_smd")) <= 0.20),
        "balance_variables_above_0_20_smd": sum(1 for r in balance_rows if safe_float(r.get("absolute_smd")) is not None and safe_float(r.get("absolute_smd")) > 0.20),
        "companies_successfully_processed_sec": len({r.get("CIK") for r in panel_rows}),
        "companies_failed_sec": max(0, len(control_master) - len({r.get("CIK") for r in panel_rows})),
        "total_control_fiscal_quarter_rows": len(panel_rows),
        "first_panel_period": first_panel_period(panel_rows),
        "latest_panel_period": latest_panel_period(panel_rows),
        "revenue_coverage_rate": coverage("revenue"),
        "gross_profit_coverage_rate": coverage("gross_profit"),
        "operating_income_coverage_rate": coverage("operating_income"),
        "net_income_coverage_rate": coverage("net_income"),
        "manual_review_count": len(manual_rows),
        "validation_error_count": sum(1 for r in validation_rows if r.get("severity") == "ERROR"),
        "validation_warning_count": sum(1 for r in validation_rows if r.get("severity") == "WARNING"),
        "retrieved_at": RETRIEVED_AT,
        "sec_user_agent": USER_AGENT,
        "market_cap_note": "Historical 2019 market capitalization was not constructed; size buckets use FY2019 revenue proxy and continuous log revenue/assets for matching.",
    }


def first_panel_period(panel_rows):
    if not panel_rows:
        return ""
    first = sorted(panel_rows, key=lambda r: fiscal_sort_key(r["fiscal_year"], r["fiscal_quarter"]))[0]
    return first.get("fiscal_period", "")


def latest_panel_period(panel_rows):
    if not panel_rows:
        return ""
    last = sorted(panel_rows, key=lambda r: fiscal_sort_key(r["fiscal_year"], r["fiscal_quarter"]))[-1]
    return last.get("fiscal_period", "")


def panel_rows_from_dataframe(df: pd.DataFrame):
    if df.empty:
        return []
    out = df.where(pd.notnull(df), None).to_dict("records")
    for row in out:
        if "sample_group" not in row:
            row["sample_group"] = "control"
    return out


def write_readme(summary):
    text = f"""# Control Group SEC Financial Panel

## Research purpose

This directory constructs a public-company control group for the BNPL merchant-side research project. The goal is to identify publicly listed companies that are economically comparable to the treated BNPL merchant parent companies but have no currently identified BNPL exposure.

## Treated-company reference sample

The treated reference sample is reconstructed from `data/public_company_panel_data/public_company_crosswalk.csv` and the treated quarterly SEC panel. The current run detected {summary.get('treated_company_count')} treated public parent companies.

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
export SEC_USER_AGENT="{USER_AGENT}"
python3 data_processing/controls_group_panel_data/build_controls_group_panel.py
```
"""
    (OUTPUT_DIR / "README.md").write_text(text, encoding="utf-8")


def run_workbook_builder():
    builder = OUTPUT_DIR / "build_controls_group_panel_workbook.mjs"
    if NODE_MODULES.exists():
        link = OUTPUT_DIR / "node_modules"
        if not link.exists():
            link.symlink_to(NODE_MODULES, target_is_directory=True)
    subprocess.run([str(NODE), "--max-old-space-size=6144", str(builder), str(OUTPUT_DIR)], check=True)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for sub in ["cache/companyfacts", "cache/submissions", "cache/web_verification", "logs"]:
        (OUTPUT_DIR / sub).mkdir(parents=True, exist_ok=True)

    treated_rows, treated_ciks, treated_panel, ownership = load_treated_reference()
    treated_profile = create_treated_profile(treated_rows)
    write_csv(OUTPUT_DIR / "treated_sample_profile.csv", treated_profile)
    LOGGER.info("STEP 2/14: treated profile written")

    candidates = build_candidate_donor_pool(treated_ciks)
    write_csv(OUTPUT_DIR / "controls_candidate_donor_pool_raw.csv", candidates)

    candidates, verification_log = verify_bnpl_exposure(candidates, ownership)
    write_csv(OUTPUT_DIR / "bnpl_control_verification_log.csv", verification_log)

    eligible_for_financials = [r for r in candidates if r.get("bnpl_control_status") == "NO_BNPL_EVIDENCE"]
    candidate_panel, _, _, _, statuses = extract_panels_for_candidates(eligible_for_financials, purpose="candidate-pre-matching")
    candidates = attach_covariates_to_candidates(candidates, candidate_panel)
    for row in candidates:
        row["companyfacts_status"] = statuses.get(row["CIK"], "")

    candidates, matching_rows = perform_matching(treated_rows, candidates)
    candidates, matching_rows, final_log, removed = final_contamination_screen(candidates, matching_rows, treated_rows)
    verification_log.extend(final_log)
    write_csv(OUTPUT_DIR / "bnpl_control_verification_log.csv", verification_log)

    control_master = build_control_master(candidates)
    selected_ciks = {r["CIK"] for r in control_master}
    selected_candidates = [r for r in candidates if r["CIK"] in selected_ciks]
    final_panel_df, source_audit, annual_refs, metadata, final_statuses = extract_panels_for_candidates(selected_candidates, purpose="preferred-control-final-panel")
    if not final_panel_df.empty:
        final_panel_df = final_panel_df[pd.to_numeric(final_panel_df["fiscal_year"], errors="coerce").between(2015, 2026)]
    panel_rows = panel_rows_from_dataframe(final_panel_df)

    panel_validation = validate_panel(panel_rows, annual_refs)
    custom_validation_rows = custom_validation(treated_ciks, control_master, panel_rows, matching_rows)
    validation_rows = panel_validation + custom_validation_rows
    for row in validation_rows:
        VALIDATION_LOG.info("%s %s %s", row.get("severity"), row.get("check_name"), row.get("message"))

    crosswalk_rows = []
    for row in selected_candidates:
        cw = crosswalk_for_candidate(row)
        cw["companyfacts_status"] = final_statuses.get(row["CIK"], "")
        sub, sub_status = ensure_submission(row["CIK"], save_cache=True)
        cw["submissions_status"] = sub_status
        crosswalk_rows.append(cw)
    coverage_rows = build_coverage_summary(panel_rows, crosswalk_rows, metadata)
    manual_rows = build_manual_review(panel_rows, crosswalk_rows, validation_rows, metadata)
    for row in candidates:
        if row["CIK"] in removed:
            row["candidate_screening_status"] = "removed_final_bnpl_screen"
        elif row.get("preferred_control_sample"):
            row["candidate_screening_status"] = "preferred_control"
        elif row.get("bnpl_control_status") != "NO_BNPL_EVIDENCE":
            row["candidate_screening_status"] = "excluded_bnpl_or_review"
        elif row.get("baseline_revenue") is None or row.get("baseline_assets") is None:
            row["candidate_screening_status"] = "excluded_insufficient_pre_financials"
        else:
            row["candidate_screening_status"] = "eligible_not_selected"

    balance_rows = balance_diagnostics(treated_rows, control_master)
    pretrend_rows = pretrend_diagnostics(treated_panel, final_panel_df if not final_panel_df.empty else pd.DataFrame())
    industry_rows = build_industry_classification(treated_rows, candidates)
    summary = create_summary(treated_rows, candidates, control_master, matching_rows, balance_rows, panel_rows, coverage_rows, validation_rows, manual_rows)

    panel_columns = PANEL_COLUMNS[:8] + ["sample_group"] + PANEL_COLUMNS[8:]
    write_csv(OUTPUT_DIR / "controls_group_panel_data_2015_2026.csv", panel_rows, panel_columns)
    write_csv(OUTPUT_DIR / "controls_group_master.csv", control_master)
    write_csv(OUTPUT_DIR / "controls_candidate_donor_pool.csv", candidates)
    write_csv(OUTPUT_DIR / "controls_matching_results.csv", matching_rows)
    write_csv(OUTPUT_DIR / "matching_balance_diagnostics.csv", balance_rows)
    write_csv(OUTPUT_DIR / "pretrend_diagnostics.csv", pretrend_rows)
    write_csv(OUTPUT_DIR / "controls_industry_classification.csv", industry_rows)
    write_csv(OUTPUT_DIR / "controls_group_panel_source_audit.csv", source_audit, SOURCE_AUDIT_COLUMNS)
    write_csv(OUTPUT_DIR / "controls_group_panel_coverage_summary.csv", coverage_rows)
    write_csv(OUTPUT_DIR / "controls_group_panel_validation_report.csv", validation_rows)
    write_csv(OUTPUT_DIR / "controls_group_panel_manual_review.csv", manual_rows)
    write_csv(OUTPUT_DIR / "controls_group_panel_variable_definitions.csv", VARIABLE_DEFINITIONS)
    write_json(OUTPUT_DIR / "controls_group_panel_summary.json", summary)
    write_readme(summary)

    LOGGER.info("STEP 14/14: writing Excel workbook")
    run_workbook_builder()
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
