#!/usr/bin/env python3
"""Build a conservative first-pass BNPL adoption-date research dataset.

This script intentionally prefers missing dates over fabricated treatment timing.
It reads public merchants from data/merchant_ownership/merchant_ownership_rows.json,
scrapes current merchant/provider pages, queries Wayback CDX for provider-specific
listing pages, and exports auditable CSV/JSON tables.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import html
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT_JSON = REPO_ROOT / "data" / "merchant_ownership" / "merchant_ownership_rows.json"
OUT_DIR = REPO_ROOT / "data" / "adoption_date_data"
CACHE_DIR = OUT_DIR / "cache"
LOG_DIR = OUT_DIR / "logs"

MASTER_CSV = OUT_DIR / "BNPL_Merchant_Adoption_Date.csv"
FIRST_CSV = OUT_DIR / "BNPL_Merchant_First_BNPL.csv"
EVIDENCE_CSV = OUT_DIR / "BNPL_Adoption_Evidence.csv"
SUMMARY_JSON = OUT_DIR / "adoption_date_summary.json"
MASTER_JSON = OUT_DIR / "adoption_master_rows.json"
FIRST_JSON = OUT_DIR / "merchant_first_bnpl_rows.json"
EVIDENCE_JSON = OUT_DIR / "evidence_log_rows.json"
MANUAL_JSON = OUT_DIR / "manual_review_rows.json"
METHODOLOGY_MD = OUT_DIR / "BNPL_Adoption_Date_Methodology.md"

RETRIEVED_AT = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()

PROVIDERS = ["affirm", "klarna", "afterpay", "zip", "sezzle"]
PROVIDER_LABEL = {
    "affirm": "Affirm",
    "klarna": "Klarna",
    "afterpay": "Afterpay",
    "zip": "Zip",
    "sezzle": "Sezzle",
}
PROVIDER_DOMAINS = {
    "affirm": ["affirm.com"],
    "klarna": ["klarna.com"],
    "afterpay": ["afterpay.com", "afterpay.com/en-US"],
    "zip": ["zip.co"],
    "sezzle": ["sezzle.com"],
}
PROVIDER_KEYWORDS = {
    "affirm": ["affirm"],
    "klarna": ["klarna"],
    "afterpay": ["afterpay", "after pay"],
    "zip": ["zip", "quadpay", "quad pay"],
    "sezzle": ["sezzle"],
}
EXTERNAL_BNPL_KEYWORDS = [
    "paypal pay later",
    "paypal pay in 4",
    "shop pay installments",
    "splitit",
    "bread pay",
    "bread financing",
    "quadpay",
]
GENERIC_BNPL_KEYWORDS = [
    "buy now pay later",
    "bnpl",
    "installments",
    "installment payments",
    "monthly payments",
    "pay over time",
]
PAYMENT_PAGE_MARKERS = [
    "payment method",
    "payment methods",
    "accepted payment",
    "accepted forms of payment",
    "we accept",
    "visa",
    "mastercard",
    "american express",
    "paypal",
]
CURRENT_LAUNCH_PHRASES = [
    "now available",
    "is now available",
    "are now available",
    "customers can now",
    "shoppers can now",
    "launches today",
    "launched today",
    "has launched",
    "have launched",
    "introduces",
    "introduced",
]
FUTURE_LAUNCH_PHRASES = [
    "will launch",
    "expected to launch",
    "plans to launch",
    "will be available",
    "expect to launch",
    "coming soon",
]

OFFICIAL_PROVIDER_HOSTS = ["affirm.com", "klarna.com", "afterpay.com", "zip.co", "sezzle.com"]
SKIP_FETCH_HOSTS = [
    "anrdoezrs.net",
    "tkqlhce.com",
    "linksynergy.com",
    "rstyle.me",
    "sovrn.co",
]
MERCHANT_PAYMENT_PATHS = [
    "",
    "/payment",
    "/payments",
    "/payment-methods",
    "/help/payment",
    "/help/payments",
    "/faq",
    "/financing",
    "/buy-now-pay-later",
]


def log(message: str) -> None:
    print(f"[adoption] {message}", flush=True)


def ensure_dirs() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def normalize_key(value: str) -> str:
    value = (value or "").replace("&", " and ")
    value = re.sub(r"[^A-Za-z0-9]+", "", value).lower()
    return value


def slug(value: str, max_len: int = 90) -> str:
    clean = re.sub(r"[^A-Za-z0-9._-]+", "_", value or "").strip("_")
    if len(clean) > max_len:
        clean = clean[:max_len]
    digest = hashlib.sha1((value or "").encode("utf-8")).hexdigest()[:10]
    return f"{clean}_{digest}" if clean else digest


def cache_path_for_url(kind: str, url: str, ext: str = "json") -> Path:
    return CACHE_DIR / kind / f"{slug(url)}.{ext}"


def request_url(url: str, *, timeout: int = 12, accept: str = "text/html,application/xhtml+xml") -> tuple[int, str, dict[str, str], str]:
    headers = {
        "User-Agent": "BNPL adoption-date research bot; academic research; contact: augustliu@example.com",
        "Accept": accept,
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as response:
        raw = response.read()
        content_type = response.headers.get("content-type", "")
        charset = "utf-8"
        match = re.search(r"charset=([^;]+)", content_type, flags=re.I)
        if match:
            charset = match.group(1).strip()
        return response.status, raw.decode(charset, errors="ignore"), dict(response.headers), response.geturl()


def cached_text(url: str, *, refresh: bool = False, timeout: int = 4) -> dict[str, Any]:
    path = cache_path_for_url("pages", url, "json")
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    record: dict[str, Any] = {
        "url": url,
        "retrieved_at": RETRIEVED_AT,
        "status": "",
        "final_url": "",
        "headers": {},
        "text": "",
        "error": "",
    }
    try:
        status, text, headers, final_url = request_url(url, timeout=timeout)
        record.update({"status": status, "text": text[:1_500_000], "headers": headers, "final_url": final_url})
    except Exception as exc:  # noqa: BLE001 - record technical failures for audit.
        record["error"] = repr(exc)
    path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.05)
    return record


def cached_json_url(url: str, *, refresh: bool = False, timeout: int = 20) -> dict[str, Any] | list[Any]:
    path = cache_path_for_url("json", url, "json")
    if path.exists() and not refresh:
        return json.loads(path.read_text(encoding="utf-8"))
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        status, text, _headers, _final_url = request_url(url, timeout=timeout, accept="application/json")
        if status >= 400:
            data: dict[str, Any] = {"error": f"HTTP {status}", "url": url}
        else:
            data = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        data = {"error": repr(exc), "url": url}
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(0.08)
    return data


def strip_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>", " ", text or "")
    text = re.sub(r"(?is)<style.*?</style>", " ", text)
    text = re.sub(r"(?is)<noscript.*?</noscript>", " ", text)
    text = re.sub(r"(?is)<[^>]+>", " ", text)
    return normalize_text(text)


def extract_source_date(url: str, html_text: str, headers: dict[str, str]) -> str:
    patterns = [
        r'<meta[^>]+property=["\']article:published_time["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']date["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+name=["\']publish-date["\'][^>]+content=["\']([^"\']+)["\']',
        r'<time[^>]+datetime=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, html_text or "", flags=re.I)
        if match:
            date = parse_date_text(match.group(1))
            if date:
                return date
    url_match = re.search(r"/(20[0-2][0-9])[/_-]([01][0-9])[/_-]([0-3][0-9])/", url)
    if url_match:
        candidate = "-".join(url_match.groups())
        if parse_date_text(candidate):
            return candidate
    last_modified = headers.get("Last-Modified") or headers.get("last-modified") or ""
    if last_modified:
        date = parse_date_text(last_modified)
        if date:
            return date
    return ""


def parse_date_text(text: str) -> str:
    if not text:
        return ""
    text = text.strip()
    iso = re.search(r"(20[0-2][0-9])[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12][0-9]|3[01])", text)
    if iso:
        y, m, d = iso.groups()
        try:
            return dt.date(int(y), int(m), int(d)).isoformat()
        except ValueError:
            return ""
    months = "January|February|March|April|May|June|July|August|September|October|November|December|Jan\\.?|Feb\\.?|Mar\\.?|Apr\\.?|Jun\\.?|Jul\\.?|Aug\\.?|Sep\\.?|Sept\\.?|Oct\\.?|Nov\\.?|Dec\\.?"
    match = re.search(rf"({months})\s+([0-3]?[0-9]),?\s+(20[0-2][0-9])", text, flags=re.I)
    if match:
        month_text, day, year = match.groups()
        month = month_number(month_text)
        try:
            return dt.date(int(year), month, int(day)).isoformat()
        except ValueError:
            return ""
    match = re.search(rf"([0-3]?[0-9])\s+({months})\s+(20[0-2][0-9])", text, flags=re.I)
    if match:
        day, month_text, year = match.groups()
        month = month_number(month_text)
        try:
            return dt.date(int(year), month, int(day)).isoformat()
        except ValueError:
            return ""
    return ""


def month_number(month_text: str) -> int:
    month_text = month_text.lower().strip(".")[:3]
    return {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }[month_text]


def quarter_for_date(date_text: str) -> str:
    if not date_text:
        return ""
    try:
        date = dt.date.fromisoformat(date_text[:10])
    except ValueError:
        return ""
    return f"{date.year}Q{((date.month - 1) // 3) + 1}"


def contains_any(text: str, keywords: list[str]) -> bool:
    low = text.lower()
    return any(keyword.lower() in low for keyword in keywords)


def evidence_snippet(text: str, keywords: list[str], width: int = 260) -> str:
    low = text.lower()
    positions = [low.find(keyword.lower()) for keyword in keywords if keyword.lower() in low]
    if not positions:
        return normalize_text(text[:width])
    pos = min(p for p in positions if p >= 0)
    start = max(pos - width // 2, 0)
    end = min(pos + width // 2, len(text))
    return normalize_text(text[start:end])


def provider_from_url(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc.lower()
    for provider, domains in PROVIDER_DOMAINS.items():
        if any(domain in host for domain in domains):
            return provider
    return ""


def is_provider_url(url: str, provider: str | None = None) -> bool:
    detected = provider_from_url(url)
    return detected == provider if provider else bool(detected)


def should_skip_url(url: str) -> bool:
    host = urllib.parse.urlparse(url).netloc.lower()
    return any(skip in host for skip in SKIP_FETCH_HOSTS)


def canonical_root_url(url: str) -> str:
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def merchant_candidate_urls(merchant_row: dict[str, Any], limit: int = 1) -> list[str]:
    urls: list[str] = []
    raw = merchant_row.get("merchant_urls") or ""
    for part in raw.split(";"):
        url = part.strip()
        if not url or should_skip_url(url) or is_provider_url(url):
            continue
        root = canonical_root_url(url)
        if not root:
            continue
        for path in MERCHANT_PAYMENT_PATHS:
            candidate = root + path
            if candidate not in urls:
                urls.append(candidate)
        if len(urls) >= limit:
            break
    return urls[:limit]


def provider_candidate_urls(merchant_row: dict[str, Any], provider: str) -> list[str]:
    urls: list[str] = []
    for column in ["merchant_urls", "source_urls"]:
        raw = merchant_row.get(column) or ""
        for part in raw.split(";"):
            url = part.strip()
            if url and is_provider_url(url, provider) and not should_skip_url(url) and url not in urls:
                urls.append(url)
    return urls[:3]


def wayback_cdx(url: str, refresh: bool = False) -> list[dict[str, str]]:
    encoded = urllib.parse.quote(url, safe="")
    cdx_url = (
        "https://web.archive.org/cdx"
        f"?url={encoded}&from=20180101&to=20260731&output=json"
        "&fl=timestamp,original,statuscode,mimetype,digest&filter=statuscode:200&collapse=digest"
    )
    data = cached_json_url(cdx_url, refresh=refresh, timeout=25)
    if isinstance(data, dict) and data.get("error"):
        return []
    if not isinstance(data, list) or len(data) < 2:
        return []
    headers = data[0]
    rows = []
    for values in data[1:]:
        row = dict(zip(headers, values))
        if "html" not in (row.get("mimetype") or "").lower():
            continue
        rows.append(row)
    return rows


def fetch_wayback_snapshot(timestamp: str, url: str, refresh: bool = False) -> dict[str, Any]:
    archived_url = f"https://web.archive.org/web/{timestamp}id_/{url}"
    return cached_text(archived_url, refresh=refresh, timeout=20)


def selected_snapshots(cdx_rows: list[dict[str, str]], max_snapshots: int = 8) -> list[dict[str, str]]:
    if len(cdx_rows) <= max_snapshots:
        return cdx_rows
    selected = [cdx_rows[0], cdx_rows[-1]]
    if max_snapshots > 2:
        step = (len(cdx_rows) - 1) / (max_snapshots - 1)
        for idx in range(1, max_snapshots - 1):
            selected.append(cdx_rows[round(idx * step)])
    seen = set()
    out = []
    for row in sorted(selected, key=lambda r: r["timestamp"]):
        if row["timestamp"] not in seen:
            seen.add(row["timestamp"])
            out.append(row)
    return out


@dataclass
class ProviderResearch:
    merchant: dict[str, Any]
    provider: str
    evidence: list[dict[str, Any]] = field(default_factory=list)
    first_confirmed_bnpl_date: str = ""
    last_confirmed_no_bnpl_date: str = ""
    announcement_date: str = ""
    announcement_date_precision: str = ""
    adoption_date_exact: str = ""
    adoption_month: str = ""
    adoption_quarter: str = ""
    adoption_year: str = ""
    adoption_period_start: str = ""
    adoption_period_end: str = ""
    adoption_date_best: str = ""
    adoption_period_best: str = ""
    date_precision: str = "unknown"
    confidence: str = "UNKNOWN"
    primary_evidence_type: str = ""
    primary_source_url: str = ""
    secondary_source_url: str = ""
    wayback_url: str = ""
    wayback_status: str = "not_checked"
    evidence_summary: str = ""
    research_notes: str = ""
    earlier_external_bnpl_detected: bool = False
    external_bnpl_provider: str = ""
    external_bnpl_adoption_period: str = ""
    provider_end_date: str = ""
    provider_end_precision: str = ""
    replacement_provider: str = ""
    manual_review_required: bool = True


def add_evidence(
    research: ProviderResearch,
    *,
    source_type: str,
    source_name: str,
    source_url: str,
    evidence_direction: str,
    evidence_text: str,
    interpretation: str,
    reliability_tier: str,
    source_date: str = "",
    archived_url_if_applicable: str = "",
    wayback_snapshot_date: str = "",
) -> None:
    research.evidence.append(
        {
            "merchant_id": research.merchant["merchant_id"],
            "merchant_name": research.merchant["merchant_name"],
            "provider": PROVIDER_LABEL[research.provider],
            "source_type": source_type,
            "source_name": source_name,
            "source_url": source_url,
            "source_date": source_date,
            "archived_url_if_applicable": archived_url_if_applicable,
            "wayback_snapshot_date": wayback_snapshot_date,
            "evidence_direction": evidence_direction,
            "evidence_text": evidence_text,
            "interpretation": interpretation,
            "reliability_tier": reliability_tier,
            "retrieved_at": RETRIEVED_AT,
        }
    )


def inspect_current_url(research: ProviderResearch, url: str, refresh: bool = False) -> None:
    record = cached_text(url, refresh=refresh, timeout=4)
    if record.get("error"):
        add_evidence(
            research,
            source_type="current_webpage_error",
            source_name=urllib.parse.urlparse(url).netloc,
            source_url=url,
            evidence_direction="inconclusive",
            evidence_text=record["error"][:280],
            interpretation="Technical error; not interpreted as evidence of BNPL absence.",
            reliability_tier="technical_log",
        )
        return

    plain = strip_html(record.get("text", ""))
    provider_keywords = PROVIDER_KEYWORDS[research.provider]
    source_date = extract_source_date(url, record.get("text", ""), record.get("headers", {}))
    provider_present = contains_any(plain, provider_keywords)
    generic_present = contains_any(plain, GENERIC_BNPL_KEYWORDS)
    external_present = contains_any(plain, EXTERNAL_BNPL_KEYWORDS)
    is_provider_page = is_provider_url(url, research.provider)

    if is_provider_page or provider_present:
        direction = "supports_bnpl_present"
        snippet = evidence_snippet(plain or url, provider_keywords + GENERIC_BNPL_KEYWORDS)
        add_evidence(
            research,
            source_type="current_provider_or_merchant_page",
            source_name=urllib.parse.urlparse(url).netloc,
            source_url=url,
            source_date=source_date,
            evidence_direction=direction,
            evidence_text=snippet or url,
            interpretation="Current page supports that this provider is presently associated with the merchant, but current listing is not treated as adoption date.",
            reliability_tier="Tier 1" if not is_provider_page else "Tier 4",
        )

        low = plain.lower()
        if source_date and any(phrase in low for phrase in CURRENT_LAUNCH_PHRASES) and not any(phrase in low for phrase in FUTURE_LAUNCH_PHRASES):
            research.announcement_date = source_date
            research.announcement_date_precision = "exact_day"
            research.adoption_date_exact = source_date
            research.adoption_date_best = source_date
            research.adoption_year = source_date[:4]
            research.adoption_month = source_date[:7]
            research.adoption_quarter = quarter_for_date(source_date)
            research.date_precision = "exact_day"
            research.confidence = "MEDIUM"
            research.primary_evidence_type = "current launch language on dated official page"
            research.primary_source_url = url
            research.evidence_summary = snippet
            research.manual_review_required = False

    if external_present:
        research.earlier_external_bnpl_detected = True
        research.external_bnpl_provider = "; ".join([kw for kw in EXTERNAL_BNPL_KEYWORDS if kw in plain.lower()][:3])
        snippet = evidence_snippet(plain, EXTERNAL_BNPL_KEYWORDS)
        add_evidence(
            research,
            source_type="current_external_bnpl_page",
            source_name=urllib.parse.urlparse(url).netloc,
            source_url=url,
            source_date=source_date,
            evidence_direction="supports_bnpl_present",
            evidence_text=snippet,
            interpretation="Current page mentions a BNPL-like provider outside the five-platform sample; timing still requires review.",
            reliability_tier="Tier 2",
        )
    elif generic_present and not provider_present:
        add_evidence(
            research,
            source_type="current_generic_bnpl_page",
            source_name=urllib.parse.urlparse(url).netloc,
            source_url=url,
            source_date=source_date,
            evidence_direction="supports_bnpl_present",
            evidence_text=evidence_snippet(plain, GENERIC_BNPL_KEYWORDS),
            interpretation="Current page mentions generic BNPL/installments language; provider and timing require manual review.",
            reliability_tier="Tier 2",
        )


def inspect_wayback_for_provider_url(research: ProviderResearch, url: str, refresh: bool = False) -> None:
    rows = wayback_cdx(url, refresh=refresh)
    if not rows:
        research.wayback_status = "no_snapshots"
        return
    research.wayback_status = "checked"
    if is_provider_url(url, research.provider):
        first = sorted(rows, key=lambda r: r["timestamp"])[0]
        timestamp = first["timestamp"]
        snap_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
        archived_url = f"https://web.archive.org/web/{timestamp}/{url}"
        research.first_confirmed_bnpl_date = snap_date
        research.wayback_url = archived_url
        if not research.primary_source_url:
            research.primary_source_url = archived_url
            research.primary_evidence_type = "Wayback first observed provider-directory page"
            research.evidence_summary = (
                f"Wayback CDX first observed the provider-directory/listing URL on {snap_date}. "
                "This is an upper-bound/current-listing signal, not an exact operational adoption date."
            )
        add_evidence(
            research,
            source_type="wayback_cdx_provider_directory",
            source_name="Internet Archive CDX",
            source_url=url,
            archived_url_if_applicable=archived_url,
            wayback_snapshot_date=snap_date,
            evidence_direction="supports_bnpl_present",
            evidence_text=f"Provider-specific URL first archived on {snap_date}: {url}",
            interpretation="Provider-directory/listing URL observed in Wayback. Not used as exact adoption date without operational launch evidence.",
            reliability_tier="Tier 4",
        )
        return
    provider_keywords = PROVIDER_KEYWORDS[research.provider]
    first_present = ""
    first_present_url = ""
    last_absent = ""
    last_absent_url = ""
    saw_inconclusive = False

    for row in selected_snapshots(rows):
        timestamp = row["timestamp"]
        snap_date = f"{timestamp[:4]}-{timestamp[4:6]}-{timestamp[6:8]}"
        snap = fetch_wayback_snapshot(timestamp, url, refresh=refresh)
        archived_url = f"https://web.archive.org/web/{timestamp}/{url}"
        if snap.get("error"):
            saw_inconclusive = True
            continue
        plain = strip_html(snap.get("text", ""))
        present = is_provider_url(url, research.provider) or contains_any(plain, provider_keywords)
        informative_no = (
            contains_any(plain, PAYMENT_PAGE_MARKERS)
            and not contains_any(plain, provider_keywords)
            and not is_provider_url(url)
        )
        if present and not first_present:
            first_present = snap_date
            first_present_url = archived_url
            add_evidence(
                research,
                source_type="wayback_snapshot",
                source_name="Internet Archive",
                source_url=url,
                archived_url_if_applicable=archived_url,
                wayback_snapshot_date=snap_date,
                evidence_direction="supports_bnpl_present",
                evidence_text=evidence_snippet(plain or url, provider_keywords + GENERIC_BNPL_KEYWORDS),
                interpretation="Archived page shows provider-associated page or provider keyword. Used as first observed presence, not automatically as exact adoption date.",
                reliability_tier="Tier 1" if not is_provider_url(url) else "Tier 4",
            )
        elif informative_no:
            last_absent = snap_date
            last_absent_url = archived_url
            add_evidence(
                research,
                source_type="wayback_snapshot",
                source_name="Internet Archive",
                source_url=url,
                archived_url_if_applicable=archived_url,
                wayback_snapshot_date=snap_date,
                evidence_direction="supports_bnpl_absent",
                evidence_text=evidence_snippet(plain, PAYMENT_PAGE_MARKERS),
                interpretation="Archived payment/help page enumerates payment methods without this provider.",
                reliability_tier="Tier 1",
            )

    if saw_inconclusive and research.wayback_status == "checked":
        research.wayback_status = "partially_inconclusive"
    if first_present:
        research.first_confirmed_bnpl_date = first_present
        research.wayback_url = first_present_url
        if not research.primary_source_url:
            research.primary_source_url = first_present_url
            research.primary_evidence_type = "Wayback first observed BNPL presence"
            research.evidence_summary = f"First observed archived provider evidence on {first_present}."
    if last_absent:
        research.last_confirmed_no_bnpl_date = last_absent
        if not research.secondary_source_url:
            research.secondary_source_url = last_absent_url
    if first_present and last_absent and last_absent < first_present:
        research.adoption_period_start = last_absent
        research.adoption_period_end = first_present
        research.adoption_period_best = f"{last_absent} < T <= {first_present}"
        research.date_precision = "interval"
        same_quarter = quarter_for_date(last_absent) == quarter_for_date(first_present)
        research.confidence = "MEDIUM" if same_quarter else "LOW"
        if same_quarter:
            research.adoption_quarter = quarter_for_date(first_present)
        research.manual_review_required = True


def treatment_scope(row: dict[str, Any]) -> tuple[str, str]:
    merchant_key = normalize_key(row.get("merchant_name", ""))
    parent_key = normalize_key(row.get("sec_matched_company", ""))
    if merchant_key and parent_key and (merchant_key in parent_key or parent_key in merchant_key):
        return "parent_core_business", "TRUE"
    # A brand-level match to a public parent should be reviewed before parent-level treatment.
    if row.get("match_method", "").startswith("manual high-confidence brand/parent alias"):
        return "major_brand_or_subsidiary", "REVIEW"
    return "unclear", "REVIEW"


def build_merchant_master(public_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merchants = []
    for idx, row in enumerate(sorted(public_rows, key=lambda r: (r.get("ticker", ""), r.get("merchant_name", ""))), start=1):
        merchant_id = f"M{idx:04d}"
        scope, eligible = treatment_scope(row)
        providers = [p.strip().lower() for p in (row.get("bnpl_providers") or "").split(";") if p.strip()]
        merchants.append(
            {
                **row,
                "merchant_id": merchant_id,
                "canonical_merchant_name": row.get("merchant_name", ""),
                "public_parent_company": row.get("sec_matched_company", ""),
                "providers": [p for p in providers if p in PROVIDERS],
                "treatment_scope": scope,
                "parent_treatment_eligible": eligible,
            }
        )
    return merchants


def research_provider(merchant: dict[str, Any], provider: str, refresh: bool = False) -> ProviderResearch:
    research = ProviderResearch(merchant=merchant, provider=provider)
    provider_urls = provider_candidate_urls(merchant, provider)
    merchant_urls = merchant_candidate_urls(merchant, limit=1)

    for url in provider_urls:
        inspect_current_url(research, url, refresh=refresh)
        inspect_wayback_for_provider_url(research, url, refresh=refresh)

    for url in merchant_urls:
        inspect_current_url(research, url, refresh=refresh)

    if not research.evidence:
        research.evidence_summary = "No reliable public web evidence found by automated first-pass scraper."
        research.research_notes = "Manual review required: search official newsroom/help/payment pages, SEC filings, high-quality news, and Wayback payment pages."
    else:
        if not research.evidence_summary:
            present_count = sum(1 for ev in research.evidence if ev["evidence_direction"] == "supports_bnpl_present")
            inconclusive_count = sum(1 for ev in research.evidence if ev["evidence_direction"] == "inconclusive")
            research.evidence_summary = (
                f"Automated scraper logged {present_count} present/current evidence item(s) and "
                f"{inconclusive_count} technical/inconclusive item(s). No operational adoption date assigned unless explicitly supported."
            )
        research.research_notes = "Automated first-pass evidence only; manual validation required before econometric treatment coding."

    if research.date_precision == "unknown":
        research.confidence = "UNKNOWN"
        research.manual_review_required = True

    return research


def research_all(refresh: bool = False, max_merchants: int | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows = json.loads(INPUT_JSON.read_text(encoding="utf-8"))
    public_rows = [row for row in rows if row.get("ownership_type") == "Public company"]
    merchants = build_merchant_master(public_rows)
    if max_merchants:
        merchants = merchants[:max_merchants]
    total_pairs = sum(len(m["providers"]) for m in merchants)
    log(f"Loaded {len(public_rows):,} public merchants from ownership dataset.")
    log(f"Research queue: {len(merchants):,} merchants and {total_pairs:,} merchant-provider rows.")

    master_rows: list[dict[str, Any]] = []
    evidence_rows: list[dict[str, Any]] = []
    pair_counter = 0
    for m_idx, merchant in enumerate(merchants, start=1):
        log(f"Merchant {m_idx:,}/{len(merchants):,}: {merchant['merchant_name']} ({'; '.join(PROVIDER_LABEL[p] for p in merchant['providers'])})")
        for provider in merchant["providers"]:
            pair_counter += 1
            log(f"  Provider {pair_counter:,}/{total_pairs:,}: {PROVIDER_LABEL[provider]}")
            research = research_provider(merchant, provider, refresh=refresh)
            evidence_rows.extend(research.evidence)
            master_rows.append(provider_research_to_row(research))

    mark_first_ever(master_rows)
    first_rows = build_first_rows(merchants, master_rows)
    manual_rows = build_manual_review_rows(master_rows, first_rows)
    summary = build_summary(merchants, master_rows, first_rows, evidence_rows, manual_rows)
    return master_rows, first_rows, evidence_rows, manual_rows, summary


def provider_research_to_row(research: ProviderResearch) -> dict[str, Any]:
    m = research.merchant
    return {
        "merchant_id": m["merchant_id"],
        "merchant_name": m["merchant_name"],
        "canonical_merchant_name": m["canonical_merchant_name"],
        "public_parent_company": m["public_parent_company"],
        "ticker": m.get("ticker", ""),
        "CIK": m.get("cik", ""),
        "exchange": m.get("exchange", ""),
        "industry": "",
        "provider": PROVIDER_LABEL[research.provider],
        "currently_listed_with_provider": "TRUE",
        "announcement_date": research.announcement_date,
        "announcement_date_precision": research.announcement_date_precision,
        "last_confirmed_no_bnpl_date": research.last_confirmed_no_bnpl_date,
        "first_confirmed_bnpl_date": research.first_confirmed_bnpl_date,
        "adoption_date_exact": research.adoption_date_exact,
        "adoption_month": research.adoption_month,
        "adoption_quarter": research.adoption_quarter,
        "adoption_year": research.adoption_year,
        "adoption_period_start": research.adoption_period_start,
        "adoption_period_end": research.adoption_period_end,
        "adoption_date_best": research.adoption_date_best,
        "adoption_period_best": research.adoption_period_best,
        "date_precision": research.date_precision,
        "confidence": research.confidence,
        "first_ever_bnpl_flag": "FALSE",
        "treatment_scope": m["treatment_scope"],
        "parent_treatment_eligible": m["parent_treatment_eligible"],
        "provider_end_date": research.provider_end_date,
        "provider_end_precision": research.provider_end_precision,
        "replacement_provider": research.replacement_provider,
        "earlier_external_bnpl_detected": "TRUE" if research.earlier_external_bnpl_detected else "FALSE",
        "external_bnpl_provider": research.external_bnpl_provider,
        "external_bnpl_adoption_period": research.external_bnpl_adoption_period,
        "primary_evidence_type": research.primary_evidence_type,
        "primary_source_url": research.primary_source_url,
        "secondary_source_url": research.secondary_source_url,
        "wayback_url": research.wayback_url,
        "wayback_status": research.wayback_status,
        "evidence_summary": research.evidence_summary,
        "research_notes": research.research_notes,
        "manual_review_required": "TRUE" if research.manual_review_required else "FALSE",
        "main_quarterly_sample": "FALSE",
        "year_only_sample": "FALSE",
        "interval_timing_sample": "TRUE" if research.date_precision == "interval" else "FALSE",
        "unknown_timing_sample": "TRUE" if research.date_precision == "unknown" else "FALSE",
    }


def date_sort_key(row: dict[str, Any]) -> str:
    return (
        row.get("adoption_date_exact")
        or row.get("adoption_month")
        or row.get("adoption_quarter")
        or row.get("adoption_year")
        or row.get("adoption_period_end")
        or "9999"
    )


def mark_first_ever(master_rows: list[dict[str, Any]]) -> None:
    by_merchant: dict[str, list[dict[str, Any]]] = {}
    for row in master_rows:
        if row["date_precision"] != "unknown":
            by_merchant.setdefault(row["merchant_id"], []).append(row)
    for rows in by_merchant.values():
        first = sorted(rows, key=date_sort_key)[0]
        first["first_ever_bnpl_flag"] = "TRUE"


def build_first_rows(merchants: list[dict[str, Any]], master_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_merchant: dict[str, list[dict[str, Any]]] = {}
    for row in master_rows:
        by_merchant.setdefault(row["merchant_id"], []).append(row)
    first_rows = []
    for merchant in merchants:
        rows = by_merchant.get(merchant["merchant_id"], [])
        known = [row for row in rows if row["date_precision"] != "unknown"]
        first = sorted(known, key=date_sort_key)[0] if known else None
        confidence = first["confidence"] if first else "UNKNOWN"
        precision = first["date_precision"] if first else "unknown"
        parent_eligible = merchant["parent_treatment_eligible"]
        main_quarterly = (
            first is not None
            and confidence in {"HIGH", "MEDIUM"}
            and precision in {"exact_day", "month", "quarter"}
            and parent_eligible == "TRUE"
        )
        first_rows.append(
            {
                "merchant_id": merchant["merchant_id"],
                "merchant_name": merchant["merchant_name"],
                "public_parent_company": merchant["public_parent_company"],
                "ticker": merchant.get("ticker", ""),
                "CIK": merchant.get("cik", ""),
                "first_bnpl_provider": first["provider"] if first else "",
                "first_bnpl_adoption_exact": first["adoption_date_exact"] if first else "",
                "first_bnpl_adoption_month": first["adoption_month"] if first else "",
                "first_bnpl_adoption_quarter": first["adoption_quarter"] if first else "",
                "first_bnpl_adoption_year": first["adoption_year"] if first else "",
                "first_bnpl_period_start": first["adoption_period_start"] if first else "",
                "first_bnpl_period_end": first["adoption_period_end"] if first else "",
                "first_bnpl_precision": precision,
                "first_bnpl_confidence": confidence,
                "number_of_current_platforms": len(merchant["providers"]),
                "earlier_external_bnpl_detected": "TRUE" if any(r["earlier_external_bnpl_detected"] == "TRUE" for r in rows) else "FALSE",
                "treatment_scope": merchant["treatment_scope"],
                "parent_treatment_eligible": parent_eligible,
                "main_regression_eligible": "TRUE" if main_quarterly else "FALSE",
                "main_quarterly_sample": "TRUE" if main_quarterly else "FALSE",
                "year_only_sample": "TRUE" if first and precision == "year" else "FALSE",
                "interval_timing_sample": "TRUE" if first and precision == "interval" else "FALSE",
                "unknown_timing_sample": "TRUE" if not first else "FALSE",
                "manual_review_required": "TRUE" if not main_quarterly else "FALSE",
            }
        )
    return first_rows


def build_manual_review_rows(master_rows: list[dict[str, Any]], first_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in master_rows:
        problems = []
        if row["date_precision"] == "unknown":
            problems.append(("unknown_timing", "No credible operational adoption date found by automated first-pass scraper."))
        if row["parent_treatment_eligible"] == "REVIEW":
            problems.append(("subsidiary_parent_scope", "Merchant-level BNPL availability may not imply parent-level treatment."))
        if row["earlier_external_bnpl_detected"] == "TRUE":
            problems.append(("possible_external_bnpl", "Evidence mentions BNPL outside the five-platform sample."))
        if row["wayback_status"] in {"partially_inconclusive", "no_snapshots"}:
            problems.append(("wayback_incomplete", f"Wayback status: {row['wayback_status']}."))
        for problem_type, reason in problems:
            rows.append(
                {
                    "merchant": row["merchant_name"],
                    "provider": row["provider"],
                    "problem_type": problem_type,
                    "reason": reason,
                    "recommended_manual_action": "Review official newsroom/help/payment pages, provider announcements, SEC filings, major news, and targeted Wayback payment-page snapshots.",
                }
            )
    for row in first_rows:
        if row["unknown_timing_sample"] == "TRUE":
            rows.append(
                {
                    "merchant": row["merchant_name"],
                    "provider": "ANY",
                    "problem_type": "merchant_first_bnpl_unknown",
                    "reason": "No provider-level adoption timing was identified for this public merchant.",
                    "recommended_manual_action": "Prioritize if merchant is important to regression sample or has multiple current platforms.",
                }
            )
    return rows


def build_summary(
    merchants: list[dict[str, Any]],
    master_rows: list[dict[str, Any]],
    first_rows: list[dict[str, Any]],
    evidence_rows: list[dict[str, Any]],
    manual_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    def counts(items: list[dict[str, Any]], key: str) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in items:
            value = item.get(key) or "(blank)"
            out[value] = out.get(value, 0) + 1
        return dict(sorted(out.items()))

    return {
        "retrieved_at": RETRIEVED_AT,
        "total_public_merchants": len(merchants),
        "merchant_provider_rows": len(master_rows),
        "evidence_log_rows": len(evidence_rows),
        "manual_review_rows": len(manual_rows),
        "confidence_distribution_provider_level": counts(master_rows, "confidence"),
        "date_precision_distribution_provider_level": counts(master_rows, "date_precision"),
        "provider_distribution": counts(master_rows, "provider"),
        "merchant_first_confidence_distribution": counts(first_rows, "first_bnpl_confidence"),
        "merchant_first_precision_distribution": counts(first_rows, "first_bnpl_precision"),
        "multi_platform_merchants": sum(1 for row in first_rows if int(row["number_of_current_platforms"]) > 1),
        "earlier_external_bnpl_rows": sum(1 for row in master_rows if row["earlier_external_bnpl_detected"] == "TRUE"),
        "main_regression_eligible_merchants": sum(1 for row in first_rows if row["main_regression_eligible"] == "TRUE"),
    }


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


MASTER_FIELDS = [
    "merchant_id",
    "merchant_name",
    "canonical_merchant_name",
    "public_parent_company",
    "ticker",
    "CIK",
    "exchange",
    "industry",
    "provider",
    "currently_listed_with_provider",
    "announcement_date",
    "announcement_date_precision",
    "last_confirmed_no_bnpl_date",
    "first_confirmed_bnpl_date",
    "adoption_date_exact",
    "adoption_month",
    "adoption_quarter",
    "adoption_year",
    "adoption_period_start",
    "adoption_period_end",
    "adoption_date_best",
    "adoption_period_best",
    "date_precision",
    "confidence",
    "first_ever_bnpl_flag",
    "treatment_scope",
    "parent_treatment_eligible",
    "provider_end_date",
    "provider_end_precision",
    "replacement_provider",
    "earlier_external_bnpl_detected",
    "external_bnpl_provider",
    "external_bnpl_adoption_period",
    "primary_evidence_type",
    "primary_source_url",
    "secondary_source_url",
    "wayback_url",
    "wayback_status",
    "evidence_summary",
    "research_notes",
    "manual_review_required",
    "main_quarterly_sample",
    "year_only_sample",
    "interval_timing_sample",
    "unknown_timing_sample",
]

FIRST_FIELDS = [
    "merchant_id",
    "merchant_name",
    "public_parent_company",
    "ticker",
    "CIK",
    "first_bnpl_provider",
    "first_bnpl_adoption_exact",
    "first_bnpl_adoption_month",
    "first_bnpl_adoption_quarter",
    "first_bnpl_adoption_year",
    "first_bnpl_period_start",
    "first_bnpl_period_end",
    "first_bnpl_precision",
    "first_bnpl_confidence",
    "number_of_current_platforms",
    "earlier_external_bnpl_detected",
    "treatment_scope",
    "parent_treatment_eligible",
    "main_regression_eligible",
    "main_quarterly_sample",
    "year_only_sample",
    "interval_timing_sample",
    "unknown_timing_sample",
    "manual_review_required",
]

EVIDENCE_FIELDS = [
    "merchant_id",
    "merchant_name",
    "provider",
    "source_type",
    "source_name",
    "source_url",
    "source_date",
    "archived_url_if_applicable",
    "wayback_snapshot_date",
    "evidence_direction",
    "evidence_text",
    "interpretation",
    "reliability_tier",
    "retrieved_at",
]

MANUAL_FIELDS = ["merchant", "provider", "problem_type", "reason", "recommended_manual_action"]


def validate(master_rows: list[dict[str, Any]], first_rows: list[dict[str, Any]]) -> list[str]:
    errors = []
    seen = set()
    for row in master_rows:
        key = (row["merchant_id"], row["provider"])
        if key in seen:
            errors.append(f"Duplicate merchant_id x provider: {key}")
        seen.add(key)
        if row["date_precision"] == "unknown" and row["adoption_date_exact"]:
            errors.append(f"Unknown precision has exact date: {key}")
        if row["date_precision"] == "year" and (row["adoption_month"] or row["adoption_date_exact"]):
            errors.append(f"Year precision has unsupported month/day: {key}")
        if row["last_confirmed_no_bnpl_date"] and row["first_confirmed_bnpl_date"]:
            if row["last_confirmed_no_bnpl_date"] >= row["first_confirmed_bnpl_date"]:
                errors.append(f"Invalid Wayback interval order: {key}")
        if row["date_precision"] != "unknown" and not row["evidence_summary"]:
            errors.append(f"Known timing missing evidence summary: {key}")
    for row in first_rows:
        if row["main_regression_eligible"] == "TRUE" and row["first_bnpl_precision"] not in {"exact_day", "month", "quarter"}:
            errors.append(f"Main regression eligible row lacks quarterly precision: {row['merchant_id']}")
    return errors


def write_methodology(summary: dict[str, Any]) -> None:
    text = f"""# BNPL Adoption Date Methodology

Generated at: {RETRIEVED_AT}

## Operational Definition

BNPL adoption is defined as the earliest date on which a BNPL payment option was operationally available to consumers purchasing from the merchant.

The dataset does not treat partnership announcements, merchant-directory listings, contract dates, or the 2026 scraped directory date as adoption dates unless the evidence explicitly supports operational payment availability.

## Input

The script reads public merchants from `data/merchant_ownership/merchant_ownership_rows.json`, derived from `BNPL_Merchant_Ownership_List.xlsx`.

## Automated First-Pass Search Procedure

For each public merchant and each currently listed BNPL provider, the scraper checks:

1. Provider-specific URLs already captured in the merchant directory dataset.
2. Current merchant webpages inferred from available merchant URLs.
3. Generic payment/help/FAQ/financing paths on merchant domains.
4. Wayback CDX metadata for provider-specific URLs.

The automated process records evidence, errors, and inconclusive results. It does not interpret HTTP failures, JavaScript failures, or missing text on arbitrary pages as evidence of non-adoption.

## Evidence Hierarchy

Tier 1 evidence includes official merchant/provider operational launch pages and informative Wayback payment-page evidence.

Tier 2 evidence includes SEC filings, investor materials, and official social media.

Tier 3 evidence includes major business press.

Tier 4 evidence includes provider directories and other current-listing evidence. Tier 4 evidence can support current provider membership but is not sufficient by itself for adoption timing.

## Date Precision Rules

Allowed precision values are `exact_day`, `month`, `quarter`, `year`, `interval`, and `unknown`.

The automated first pass leaves timing as `unknown` unless source text or Wayback bounds support a narrower period. It never converts year-only or month-only information into artificial exact dates.

## Wayback Rules

Wayback absence is coded only when an archived payment/help page appears informative and enumerates payment methods without the provider. Arbitrary missing keywords on a homepage are not coded as confirmed absence.

## Multi-Platform Rule

The master dataset is merchant x provider. Merchant-level first BNPL adoption is calculated only from credible provider-level timing evidence. Rows with unknown timing remain preserved.

## Subsidiary-Parent Rule

Merchant-level BNPL adoption is kept distinct from public-parent treatment. `parent_treatment_eligible` is set conservatively and often requires manual review when brand-parent scope is ambiguous.

## Missing-Date Policy

If no reliable evidence is found, the treatment date remains blank with `date_precision = unknown` and `confidence = UNKNOWN`.

## Validation

The script validates duplicate merchant-provider rows, unsupported exact dates under unknown/year precision, invalid Wayback interval ordering, and missing evidence summaries for known timing.

## Summary

```json
{json.dumps(summary, indent=2)}
```

## Manual Review Procedure

Manual review should prioritize:

- high-value public parents;
- merchants with multiple current BNPL platforms;
- possible subsidiary-parent ambiguity;
- possible earlier external BNPL providers;
- unknown timing with current provider membership;
- any interval timing spanning multiple quarters.
"""
    METHODOLOGY_MD.write_text(text, encoding="utf-8")


def write_outputs(master_rows: list[dict[str, Any]], first_rows: list[dict[str, Any]], evidence_rows: list[dict[str, Any]], manual_rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    write_csv(MASTER_CSV, master_rows, MASTER_FIELDS)
    write_csv(FIRST_CSV, first_rows, FIRST_FIELDS)
    write_csv(EVIDENCE_CSV, evidence_rows, EVIDENCE_FIELDS)
    write_csv(OUT_DIR / "BNPL_Adoption_Manual_Review.csv", manual_rows, MANUAL_FIELDS)
    MASTER_JSON.write_text(json.dumps(master_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    FIRST_JSON.write_text(json.dumps(first_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    EVIDENCE_JSON.write_text(json.dumps(evidence_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    MANUAL_JSON.write_text(json.dumps(manual_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    write_methodology(summary)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Refresh HTTP cache.")
    parser.add_argument("--max-merchants", type=int, default=None, help="Optional smoke-test limit.")
    args = parser.parse_args()
    ensure_dirs()
    master_rows, first_rows, evidence_rows, manual_rows, summary = research_all(refresh=args.refresh, max_merchants=args.max_merchants)
    errors = validate(master_rows, first_rows)
    if errors:
        (LOG_DIR / "validation_errors.log").write_text("\n".join(errors), encoding="utf-8")
        raise SystemExit(f"Validation failed with {len(errors)} error(s); see logs/validation_errors.log")
    write_outputs(master_rows, first_rows, evidence_rows, manual_rows, summary)
    log(f"Wrote {MASTER_CSV.relative_to(REPO_ROOT)} ({len(master_rows):,} rows).")
    log(f"Wrote {FIRST_CSV.relative_to(REPO_ROOT)} ({len(first_rows):,} rows).")
    log(f"Wrote {EVIDENCE_CSV.relative_to(REPO_ROOT)} ({len(evidence_rows):,} rows).")
    log(f"Wrote summary: {json.dumps(summary, ensure_ascii=False, sort_keys=True)}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Interrupted.")
        sys.exit(130)
