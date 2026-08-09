#!/usr/bin/env python3
"""Build BNPL merchant public/private ownership data.

Inputs:
  data/merchant_list_raw_data/BNPL_Merchant_Categories.csv

Outputs:
  data/merchant_ownership/merchant_ownership_rows.json
  data/merchant_ownership/merchant_ownership_summary.json

Method:
  1. Aggregate unique merchants from the merchant-category long table.
  2. Match merchant names conservatively to SEC company_tickers/company_tickers_exchange.
  3. For matched public issuers, fetch 2026-07-31 close prices from Yahoo Finance
     chart data and shares outstanding from SEC companyfacts.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "merchant_list_raw_data"
OUT_DIR = REPO_ROOT / "data" / "merchant_ownership"
CACHE_DIR = OUT_DIR / "cache"

RAW_CATEGORY_CSV = RAW_DIR / "BNPL_Merchant_Categories.csv"
OUT_ROWS_JSON = OUT_DIR / "merchant_ownership_rows.json"
OUT_SUMMARY_JSON = OUT_DIR / "merchant_ownership_summary.json"

SEC_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_EXCHANGE_URL = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"
YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

TARGET_DATE = dt.date(2026, 7, 31)
CURRENT_DATE = dt.date(2026, 8, 9)

PROVIDER_ORDER = ["affirm", "klarna", "afterpay", "zip", "sezzle"]

SEC_USER_AGENT = os.environ.get(
    "SEC_USER_AGENT",
    "BNPL Merchant Research augustliu@example.com",
)


LEGAL_SUFFIXES = {
    "inc",
    "incorporated",
    "corp",
    "corporation",
    "co",
    "company",
    "cos",
    "companies",
    "limited",
    "ltd",
    "llc",
    "lp",
    "plc",
    "nv",
    "sa",
    "se",
    "ag",
    "gmbh",
    "holding",
    "holdings",
    "group",
    "international",
    "de",
    "new",
}

MERCHANT_SUFFIXES = {
    "official",
    "usa",
    "us",
}

BRAND_ALIASES = {
    # High-confidence merchant-brand aliases whose SEC registrant name is different.
    # These are intentionally sparse and auditable.
    "google": "alphabet",
    "youtube": "alphabet",
    "facebook": "meta platforms",
    "instagram": "meta platforms",
    "whatsapp": "meta platforms",
    "microsoft store": "microsoft",
    "amazon": "amazon com",
    "zappos": "amazon com",
    "whole foods market": "amazon com",
    "old navy": "gap",
    "banana republic": "gap",
    "athleta": "gap",
    "gap factory": "gap",
    "coach": "tapestry",
    "coach outlet": "tapestry",
    "kate spade": "tapestry",
    "kate spade outlet": "tapestry",
    "ugg": "deckers outdoor",
    "hoka": "deckers outdoor",
    "the north face": "vf",
    "vans": "vf",
    "timberland": "vf",
    "dick's sporting goods": "dicks sporting goods",
    "dicks sporting goods": "dicks sporting goods",
    "ulta": "ulta beauty",
    "bath and body works": "bath body works",
    "booking.com": "booking holdings",
    "priceline": "booking holdings",
    "vrbo": "expedia",
    "hotels.com": "expedia",
    "nike": "nike",
    "converse": "nike",
    "jordan": "nike",
    "walmart": "walmart",
    "sams club": "walmart",
    "target": "target",
    "macy's": "macys",
    "macys": "macys",
    "bloomingdale's": "macys",
    "bloomingdales": "macys",
    "oshkosh": "carters",
    "graco": "newell brands",
    "columbia": "columbia sportswear",
    "saks off 5th": "saks global",
}

BLOCKED_PUBLIC_MATCHES = {
    "barnes and noble",
    "champion",
    "equipment",
    "harmonica",
    "intelligent shop",
    "nautilus",
    "reeds",
    "universal store",
    "white pearl",
    "white pearl spa",
}


def log(message: str) -> None:
    print(f"[ownership] {message}", flush=True)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_request(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> dict:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": SEC_USER_AGENT,
    }
    if headers:
        request_headers.update(headers)
    req = urllib.request.Request(url, headers=request_headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def cached_json(
    url: str,
    cache_path: Path,
    *,
    refresh: bool = False,
    headers: dict[str, str] | None = None,
    timeout: int = 30,
    sleep_after_fetch: float = 0.0,
) -> dict:
    if cache_path.exists() and not refresh:
        with cache_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    data = json_request(url, headers=headers, timeout=timeout)
    with cache_path.open("w", encoding="utf-8") as handle:
        json.dump(data, handle)
    if sleep_after_fetch:
        time.sleep(sleep_after_fetch)
    return data


def normalize_text(value: str) -> str:
    value = value or ""
    value = value.replace("&", " and ")
    value = value.replace("+", " plus ")
    value = value.replace("@", " at ")
    value = value.replace("'", "")
    value = value.replace("’", "")
    value = value.replace("‘", "")
    value = value.replace(".", " ")
    value = re.sub(r"/.*?/", " ", value)
    value = re.sub(r"\([^)]*\)", " ", value)
    value = re.sub(r"[^A-Za-z0-9]+", " ", value).strip().lower()
    return re.sub(r"\s+", " ", value)


def trim_suffix_tokens(tokens: list[str], suffixes: set[str]) -> list[str]:
    trimmed = list(tokens)
    while trimmed and trimmed[-1] in suffixes:
        trimmed.pop()
    return trimmed


def normalized_name(value: str, *, for_merchant: bool = False) -> str:
    text = normalize_text(value)
    tokens = text.split()
    tokens = trim_suffix_tokens(tokens, LEGAL_SUFFIXES)
    if for_merchant:
        tokens = trim_suffix_tokens(tokens, MERCHANT_SUFFIXES)
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    return "".join(tokens)


def normalized_words(value: str, *, for_merchant: bool = False) -> str:
    text = normalize_text(value)
    tokens = text.split()
    tokens = trim_suffix_tokens(tokens, LEGAL_SUFFIXES)
    if for_merchant:
        tokens = trim_suffix_tokens(tokens, MERCHANT_SUFFIXES)
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]
    return " ".join(tokens)


def clean_merchant_name(name: str) -> str:
    return re.sub(r"\s+", " ", (name or "").strip())


def aggregate_merchants(category_rows: list[dict[str, str]]) -> list[dict]:
    groups: dict[str, dict] = {}
    for row in category_rows:
        merchant_name = clean_merchant_name(row.get("merchant_name", ""))
        if not merchant_name:
            continue
        key = normalized_name(merchant_name, for_merchant=True)
        if not key:
            continue
        if key not in groups:
            groups[key] = {
                "merchant_key": key,
                "merchant_names": Counter(),
                "categories": set(),
                "providers": set(),
                "source_urls": set(),
                "merchant_urls": set(),
            }
        group = groups[key]
        group["merchant_names"][merchant_name] += 1
        category = (row.get("category") or "").replace("’", "'").strip()
        provider = (row.get("bnpl_provider") or "").strip().lower()
        if category:
            group["categories"].add(category)
        if provider:
            group["providers"].add(provider)
        for column, target in [("source_urls", "source_urls"), ("merchant_urls", "merchant_urls")]:
            for url in (row.get(column) or "").split(";"):
                url = url.strip()
                if url:
                    group[target].add(url)

    merchants = []
    for group in groups.values():
        display_name = sorted(
            group["merchant_names"].items(),
            key=lambda item: (-item[1], len(item[0]), item[0].lower()),
        )[0][0]
        providers = sorted(group["providers"], key=lambda p: PROVIDER_ORDER.index(p) if p in PROVIDER_ORDER else 99)
        merchants.append(
            {
                "merchant_name": display_name,
                "merchant_key": group["merchant_key"],
                "categories": "; ".join(sorted(group["categories"], key=str.lower)),
                "bnpl_providers": "; ".join(providers),
                "number_of_platforms": len(providers),
                "source_urls": "; ".join(sorted(group["source_urls"])),
                "merchant_urls": "; ".join(sorted(group["merchant_urls"])),
            }
        )
    return sorted(merchants, key=lambda row: row["merchant_name"].lower())


def load_sec_issuers(refresh: bool = False) -> list[dict]:
    tickers = cached_json(SEC_TICKERS_URL, CACHE_DIR / "company_tickers.json", refresh=refresh)
    exchange_json = cached_json(SEC_EXCHANGE_URL, CACHE_DIR / "company_tickers_exchange.json", refresh=refresh)

    exchange_by_key: dict[tuple[int, str], str] = {}
    fields = exchange_json.get("fields", [])
    for row in exchange_json.get("data", []):
        record = dict(zip(fields, row))
        exchange_by_key[(int(record["cik"]), str(record["ticker"]).upper())] = record.get("exchange", "")

    issuers = []
    for entry in tickers.values():
        cik = int(entry["cik_str"])
        ticker = str(entry["ticker"]).upper()
        title = str(entry["title"])
        norm = normalized_name(title)
        words = normalized_words(title)
        issuers.append(
            {
                "cik": cik,
                "ticker": ticker,
                "title": title,
                "exchange": exchange_by_key.get((cik, ticker), ""),
                "normalized": norm,
                "normalized_words": words,
            }
        )
    return issuers


def build_sec_indexes(
    issuers: list[dict],
) -> tuple[dict[str, list[dict]], dict[str, dict], dict[str, list[dict]], dict[str, list[dict]], list[dict]]:
    by_norm: dict[str, list[dict]] = defaultdict(list)
    by_ticker: dict[str, dict] = {}
    by_first_token: dict[str, list[dict]] = defaultdict(list)
    by_prefix: dict[str, list[dict]] = defaultdict(list)
    for issuer in issuers:
        if issuer["normalized"]:
            by_norm[issuer["normalized"]].append(issuer)
            by_prefix[issuer["normalized"][:6]].append(issuer)
        tokens = issuer["normalized_words"].split()
        if tokens:
            by_first_token[tokens[0]].append(issuer)
        by_ticker.setdefault(issuer["ticker"], issuer)
    return by_norm, by_ticker, by_first_token, by_prefix, issuers


def choose_issuer(candidates: list[dict]) -> dict:
    return sorted(
        candidates,
        key=lambda issuer: (
            0 if issuer.get("exchange") in {"Nasdaq", "NYSE"} else 1,
            len(issuer.get("title", "")),
        ),
    )[0]


def match_merchant(
    merchant: dict,
    by_norm: dict[str, list[dict]],
    by_ticker: dict[str, dict],
    by_first_token: dict[str, list[dict]],
    by_prefix: dict[str, list[dict]],
) -> dict | None:
    merchant_name = merchant["merchant_name"]
    merchant_norm = normalized_name(merchant_name, for_merchant=True)
    merchant_words = normalized_words(merchant_name, for_merchant=True)

    alias_words = BRAND_ALIASES.get(merchant_words)
    alias_norm = normalized_name(alias_words) if alias_words else ""
    if alias_norm and alias_norm in by_norm:
        issuer = choose_issuer(by_norm[alias_norm])
        return {
            **issuer,
            "match_method": "manual high-confidence brand/parent alias + SEC exact",
            "match_score": 100,
            "matched_on": alias_words,
        }

    if merchant_words in BLOCKED_PUBLIC_MATCHES:
        return None

    if merchant_norm in by_norm:
        issuer = choose_issuer(by_norm[merchant_norm])
        return {
            **issuer,
            "match_method": "SEC exact normalized company-name match",
            "match_score": 100,
            "matched_on": merchant_words,
        }

    candidate_map = {}
    tokens = merchant_words.split()
    if tokens:
        for issuer in by_first_token.get(tokens[0], []):
            candidate_map[(issuer["cik"], issuer["ticker"])] = issuer
    if len(merchant_norm) >= 6:
        for issuer in by_prefix.get(merchant_norm[:6], []):
            candidate_map[(issuer["cik"], issuer["ticker"])] = issuer

    best = None
    best_score = 0
    for issuer in candidate_map.values():
        sec_norm = issuer["normalized"]
        if not merchant_norm or not sec_norm:
            continue
        if len(merchant_norm) >= 8 and sec_norm.startswith(merchant_norm):
            score = 92
        else:
            ratio = SequenceMatcher(None, merchant_norm, sec_norm).ratio()
            score = int(round(ratio * 100))
            if score < 94:
                continue
        if score > best_score:
            best = issuer
            best_score = score

    if best and best_score >= 91:
        return {
            **best,
            "match_method": "SEC fuzzy normalized company-name match",
            "match_score": best_score,
            "matched_on": merchant_words,
        }

    return None


def yahoo_close_price(ticker: str, refresh: bool = False) -> tuple[float | None, str, str, str]:
    start = int(dt.datetime(TARGET_DATE.year, TARGET_DATE.month, TARGET_DATE.day, tzinfo=dt.timezone.utc).timestamp())
    end = int((dt.datetime(TARGET_DATE.year, TARGET_DATE.month, TARGET_DATE.day, tzinfo=dt.timezone.utc) + dt.timedelta(days=5)).timestamp())
    url = (
        YAHOO_CHART_URL.format(ticker=urllib.parse.quote(ticker))
        + f"?period1={start}&period2={end}&interval=1d&events=history"
    )
    cache_path = CACHE_DIR / "yahoo_chart" / f"{ticker.replace('/', '_')}_{TARGET_DATE.isoformat()}.json"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        data = cached_json(url, cache_path, refresh=refresh, headers=headers, timeout=20)
    except Exception as exc:
        return None, "", "", f"Yahoo chart error: {exc}"

    chart = data.get("chart", {})
    if chart.get("error"):
        return None, "", "", f"Yahoo chart error: {chart['error']}"
    results = chart.get("result") or []
    if not results:
        return None, "", "", "Yahoo chart returned no result"

    result = results[0]
    timestamps = result.get("timestamp") or []
    closes = (result.get("indicators", {}).get("quote") or [{}])[0].get("close") or []
    currency = (result.get("meta") or {}).get("currency", "")

    selected = None
    for timestamp, close in zip(timestamps, closes):
        if close is None:
            continue
        date = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc).date()
        if date <= TARGET_DATE:
            selected = (date, float(close))
        elif selected is None:
            selected = (date, float(close))
            break

    if not selected:
        return None, "", currency, "No close price found near target date"
    return selected[1], selected[0].isoformat(), currency, ""


def iter_fact_values(companyfacts: dict, taxonomy: str, tag: str) -> list[dict]:
    facts = companyfacts.get("facts", {}).get(taxonomy, {}).get(tag, {}).get("units", {})
    rows = []
    for unit, values in facts.items():
        if unit.lower() != "shares":
            continue
        for value in values:
            if value.get("val") is None or not value.get("end"):
                continue
            try:
                end_date = dt.date.fromisoformat(value["end"])
            except ValueError:
                continue
            filed_text = value.get("filed") or value.get("acceptanceDatetime", "")[:10]
            try:
                filed_date = dt.date.fromisoformat(filed_text) if filed_text else dt.date.min
            except ValueError:
                filed_date = dt.date.min
            if end_date <= TARGET_DATE and filed_date <= CURRENT_DATE:
                rows.append(
                    {
                        "end": end_date,
                        "filed": filed_date,
                        "val": float(value["val"]),
                        "form": value.get("form", ""),
                        "fy": value.get("fy", ""),
                        "fp": value.get("fp", ""),
                    }
                )
    return rows


def sec_shares(cik: int, refresh: bool = False) -> tuple[float | None, str, str, str]:
    url = SEC_COMPANYFACTS_URL.format(cik=cik)
    cache_path = CACHE_DIR / "sec_companyfacts" / f"CIK{cik:010d}.json"
    try:
        data = cached_json(url, cache_path, refresh=refresh, timeout=30, sleep_after_fetch=0.12)
    except urllib.error.HTTPError as exc:
        return None, "", "", f"SEC companyfacts HTTP error: {exc.code}"
    except Exception as exc:
        return None, "", "", f"SEC companyfacts error: {exc}"

    tag_priority = [
        ("dei", "EntityCommonStockSharesOutstanding", "SEC EntityCommonStockSharesOutstanding"),
        ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding", "SEC weighted-average diluted shares fallback"),
        ("us-gaap", "WeightedAverageNumberOfSharesOutstandingBasic", "SEC weighted-average basic shares fallback"),
    ]
    for taxonomy, tag, source_label in tag_priority:
        values = iter_fact_values(data, taxonomy, tag)
        if values:
            chosen = sorted(values, key=lambda row: (row["end"], row["filed"], row["val"]))[-1]
            return (
                chosen["val"],
                chosen["end"].isoformat(),
                f"{source_label}; filed {chosen['filed'].isoformat()}; form {chosen['form']}; {chosen['fy']} {chosen['fp']}",
                "",
            )
    return None, "", "", "No SEC shares tag found before target date"


def classify_size(market_cap: float | None) -> str:
    if market_cap is None or not math.isfinite(market_cap):
        return "Unknown market cap"
    if market_cap >= 10_000_000_000:
        return "Large-cap"
    if market_cap >= 2_000_000_000:
        return "Mid-cap"
    if market_cap >= 300_000_000:
        return "Small-cap"
    return "Micro/Nano-cap"


def enrich_public_market_data(rows: list[dict], refresh: bool = False) -> None:
    public_rows = [row for row in rows if row["ownership_type"] == "Public company"]
    tickers = sorted({row["ticker"] for row in public_rows if row.get("ticker")})
    log(f"Fetching market data for {len(tickers):,} unique public ticker(s).")

    market_data = {}
    for idx, ticker in enumerate(tickers, start=1):
        if idx == 1 or idx % 25 == 0 or idx == len(tickers):
            log(f"Market data progress: {idx:,}/{len(tickers):,} tickers.")
        close_price, price_date, currency, price_error = yahoo_close_price(ticker, refresh=refresh)
        market_data[ticker] = {
            "close_price": close_price,
            "price_date": price_date,
            "currency": currency,
            "price_error": price_error,
        }

    ciks = sorted({int(row["cik"]) for row in public_rows if row.get("cik")})
    share_data = {}
    for idx, cik in enumerate(ciks, start=1):
        if idx == 1 or idx % 25 == 0 or idx == len(ciks):
            log(f"SEC shares progress: {idx:,}/{len(ciks):,} CIKs.")
        shares, shares_date, shares_source, shares_error = sec_shares(cik, refresh=refresh)
        share_data[cik] = {
            "shares_outstanding": shares,
            "shares_date": shares_date,
            "shares_source": shares_source,
            "shares_error": shares_error,
        }

    for row in public_rows:
        ticker_data = market_data.get(row["ticker"], {})
        cik_data = share_data.get(int(row["cik"]), {})
        close_price = ticker_data.get("close_price")
        shares = cik_data.get("shares_outstanding")
        market_cap = close_price * shares if close_price is not None and shares is not None else None

        row["close_price_2026_07_31"] = close_price
        row["price_date"] = ticker_data.get("price_date", "")
        row["price_currency"] = ticker_data.get("currency", "")
        row["shares_outstanding"] = shares
        row["shares_date"] = cik_data.get("shares_date", "")
        row["market_cap_2026_07_31"] = market_cap
        row["company_size"] = classify_size(market_cap)
        row["market_cap_source"] = (
            "Yahoo Finance chart close price x SEC shares outstanding/fallback shares"
            if market_cap is not None
            else ""
        )
        row["shares_source"] = cik_data.get("shares_source", "")
        row["market_data_notes"] = "; ".join(
            note for note in [ticker_data.get("price_error", ""), cik_data.get("shares_error", "")] if note
        )


def build_rows(refresh: bool = False) -> tuple[list[dict], dict]:
    category_rows = read_csv(RAW_CATEGORY_CSV)
    merchants = aggregate_merchants(category_rows)
    log(f"Loaded {len(category_rows):,} merchant-category rows.")
    log(f"Aggregated {len(merchants):,} unique merchant names.")

    issuers = load_sec_issuers(refresh=refresh)
    by_norm, by_ticker, by_first_token, by_prefix, issuer_list = build_sec_indexes(issuers)
    log(f"Loaded {len(issuer_list):,} SEC issuer/ticker records.")

    rows = []
    for idx, merchant in enumerate(merchants, start=1):
        if idx == 1 or idx % 1000 == 0 or idx == len(merchants):
            log(f"SEC matching progress: {idx:,}/{len(merchants):,} merchants.")
        match = match_merchant(merchant, by_norm, by_ticker, by_first_token, by_prefix)
        base = {
            **merchant,
            "ownership_type": "Public company" if match else "Private company",
            "sec_matched_company": match["title"] if match else "",
            "ticker": match["ticker"] if match else "",
            "cik": match["cik"] if match else "",
            "exchange": match["exchange"] if match else "",
            "match_method": match["match_method"] if match else "No direct SEC company-ticker match",
            "match_score": match["match_score"] if match else "",
            "matched_on": match["matched_on"] if match else "",
            "sec_company_page": f"https://www.sec.gov/edgar/browse/?CIK={match['cik']}" if match else "",
            "sec_company_tickers_source": SEC_TICKERS_URL,
            "market_price_source": "",
            "close_price_2026_07_31": None,
            "price_date": "",
            "price_currency": "",
            "shares_outstanding": None,
            "shares_date": "",
            "shares_source": "",
            "market_cap_2026_07_31": None,
            "market_cap_source": "",
            "company_size": "",
            "market_data_notes": "",
        }
        if match:
            base["market_price_source"] = YAHOO_CHART_URL.format(ticker=urllib.parse.quote(match["ticker"]))
        rows.append(base)

    public_count = sum(1 for row in rows if row["ownership_type"] == "Public company")
    private_count = len(rows) - public_count
    log(f"SEC matched public companies: {public_count:,}; private/no direct match: {private_count:,}.")

    enrich_public_market_data(rows, refresh=refresh)

    summary = Counter()
    summary["total_unique_merchants"] = len(rows)
    summary["public_company_rows"] = public_count
    summary["private_company_rows"] = private_count
    for row in rows:
        if row["ownership_type"] == "Public company":
            summary[row["company_size"]] += 1

    return rows, dict(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Ignore cached SEC/Yahoo responses.")
    args = parser.parse_args()

    if not RAW_CATEGORY_CSV.exists():
        raise FileNotFoundError(f"Missing input file: {RAW_CATEGORY_CSV}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    rows, summary = build_rows(refresh=args.refresh)

    with OUT_ROWS_JSON.open("w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    with OUT_SUMMARY_JSON.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    log(f"Wrote {OUT_ROWS_JSON.relative_to(REPO_ROOT)}.")
    log(f"Wrote {OUT_SUMMARY_JSON.relative_to(REPO_ROOT)}.")
    log("Summary: " + json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted.")
        sys.exit(130)
