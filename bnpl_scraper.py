#!/usr/bin/env python3
"""
Scrape merchant directories for selected BNPL providers.

The script intentionally assigns categories from the category URL/API request
that produced the merchant, not from generic provider tags such as "All".
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Any, Iterable


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"
)

PROVIDER_ORDER = ["affirm", "klarna", "afterpay", "zip", "sezzle"]

AFFIRM_BROWSE_URL = "https://www.affirm.com/u/shop/browse?category=all"
KLARNA_STORE_URL = "https://www.klarna.com/us/store/"
ZIP_SHOP_ALL_URL = "https://zip.co/us/shop/shop-all"
SEZZLE_HOME_URL = "https://sezzle.com/"


AFFIRM_CATEGORIES = [
    ("Accessories", ["accessories"]),
    ("Apparel", ["apparel"]),
    ("Auto", ["auto"]),
    ("Beauty", ["beauty-and-health"]),
    ("Electronics", ["electronics"]),
    ("Fitness & Gear", ["fitness-and-gear"]),
    ("Home & Furniture", ["home-and-furniture"]),
    ("Luxury", ["luxury"]),
    ("Shoes", ["shoes"]),
    ("Travel & Events", ["travel", "events-experiences"]),
]

KLARNA_CATEGORIES = [
    ("Health & Beauty", {"tree_id": "10", "tree_slug": "Health-Beauty", "store_category": "health_beauty"}),
    ("Clothing & Accessories", {"tree_id": "141", "tree_slug": "Clothing-Accessories", "store_category": "fashion"}),
    ("Toys & Hobbies", {"tree_id": "1493", "tree_slug": "Toys-Hobbies", "store_category": "marketplaces"}),
    ("Home & Appliances", {"tree_id": "34", "tree_slug": "Home-Appliances", "store_category": "home_more"}),
    ("TV & Audio", {"tree_id": "1", "tree_slug": "TV-Audio", "store_category": "electronics"}),
    ("Sports & Outdoor", {"tree_id": "27", "tree_slug": "Sports-Outdoor", "store_category": "sports"}),
    ("Computers & Tablets", {"tree_id": "2", "tree_slug": "Computers-Tablets", "store_category": "electronics"}),
    ("Home Improvement", {"tree_id": "182", "tree_slug": "Home-Improvement", "store_category": "home_more"}),
    ("Photography", {"tree_id": "17", "tree_slug": "Photography", "store_category": "electronics"}),
    ("Gaming & Entertainment", {"tree_id": "19", "tree_slug": "Gaming-Entertainment", "store_category": "electronics"}),
    ("Phones & Smartwatches", {"tree_id": "4", "tree_slug": "Phones-Smartwatches", "store_category": "electronics"}),
    ("Kids & Family", {"tree_id": "35", "tree_slug": "Kids-Family", "store_category": "marketplaces"}),
    ("Automotive", {"tree_id": "11", "tree_slug": "Automotive", "search_query": "auto"}),
    ("Garden & Patio", {"tree_id": "1424", "tree_slug": "Garden-Patio", "store_category": "home_more"}),
    ("Kitchen Appliances", {"tree_id": "14", "tree_slug": "Kitchen-Appliances", "store_category": "home_more"}),
    ("Home Appliances", {"tree_id": "3", "tree_slug": "Home-Appliances", "store_category": "home_more"}),
    ("Books, Movies & Music", {"tree_id": "40", "tree_slug": "Books-Movies-Music", "store_category": "marketplaces"}),
]

AFTERPAY_CATEGORIES = [
    ("Fashion", ["womens-clothing"]),
    ("Men's fashion", ["mens-clothing"]),
    ("Kids & Baby", ["kids"]),
    ("Home & Garden", ["home"]),
    ("Health & Beauty", ["beauty", "health"]),
    ("Electronics & Devices", ["tech"]),
    ("Travel & Entertainment", ["travel", "tickets"]),
]

ZIP_CATEGORIES = [
    ("Bills", "bills"),
    ("Electronics & Appliances", "appliances-electronics"),
    ("Fitness", "fitness"),
    ("Home & Furniture", "home-furniture"),
    ("Jewelry & Accessories", "jewelry-accessories"),
    ("Pets", "pets"),
    ("Shoes", "shoes"),
    ("Travel & Entertainment", "travel-entertainment"),
    ("TVs", "tvs"),
    ("Education", "education"),
    ("Food & Beverage", "food-beverage"),
    ("Flights", "flights"),
    ("Hotels", "hotels"),
    ("Kids & Babies", "kids-babies"),
    ("Phones", "phones"),
    ("Sports & Outdoors", "sports-outdoors"),
]

ZIP_CATEGORY_ALIASES = {
    "Electronics": "Electronics & Appliances",
    "Appliances & Electronics": "Electronics & Appliances",
    "Travel": "Travel & Entertainment",
    "Trending Now": "Trending",
}

SEZZLE_CATEGORIES = [
    ("Activewear", [("womens-activewear", 13)]),
    ("Clothing", [("womens-clothing", 67), ("mens-clothing", 69)]),
    (
        "Jewelry",
        [
            ("womens-jewelry-and-accessories", 68),
            ("mens-jewelry-and-accessories", 22),
        ],
    ),
    ("Shoes", [("womens-shoes", 16), ("mens-shoes", 26)]),
    ("Swimwear", [("womens-swimwear", 15)]),
    ("Baby Gear", [("baby-gear", 42)]),
    ("Cosmetics", [("cosmetics", 19)]),
    ("Hair", [("hair", 31)]),
    ("Self Care", [("self-care", 46)]),
    ("Fitness", [("fitness", 30)]),
    ("Vitamins & Supplements", [("vitamins-and-supplements", 28)]),
    ("Outdoor", [("outdoor", 72)]),
    ("Sporting Goods", [("sporting-goods", 73)]),
    ("Sportsman's", [("sportsmans", 74)]),
    ("Bed & Bath", [("bed-and-bath", 56)]),
    ("Furniture & Decor", [("furniture-and-decor", 50)]),
    ("Outdoor & Seasonal", [("outdoor-and-seasonal", 71)]),
    ("Pets", [("pets", 10)]),
    ("Toys & Games", [("toys-and-games", 66)]),
]


@dataclass
class ScrapedMerchant:
    provider: str
    merchant_name: str
    category: str
    source_url: str
    merchant_url: str = ""


@dataclass
class AggregatedMerchant:
    provider: str
    merchant_name: str
    categories: set[str] = field(default_factory=set)
    source_urls: set[str] = field(default_factory=set)
    merchant_urls: set[str] = field(default_factory=set)


@dataclass
class ProviderResult:
    provider: str
    raw_hits: int = 0
    error: str = ""


class HttpClient:
    def __init__(
        self,
        timeout: int = 30,
        insecure: bool = False,
        delay: float = 0.25,
        retries: int = 2,
        verbose: bool = False,
    ) -> None:
        self.timeout = timeout
        self.delay = delay
        self.retries = retries
        self.verbose = verbose
        self._last_request_at = 0.0
        self.context = self._build_ssl_context(insecure)
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(CookieJar()),
            urllib.request.HTTPSHandler(context=self.context),
        )

    @staticmethod
    def _build_ssl_context(insecure: bool) -> ssl.SSLContext:
        if insecure:
            return ssl._create_unverified_context()

        try:
            import certifi  # type: ignore

            return ssl.create_default_context(cafile=certifi.where())
        except Exception:
            return ssl.create_default_context()

    def get_text(self, url: str, headers: dict[str, str] | None = None) -> str:
        if self.verbose:
            print(f"GET {url}", file=sys.stderr)

        request_headers = {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        if headers:
            request_headers.update(headers)

        for attempt in range(self.retries + 1):
            self._polite_sleep()
            req = urllib.request.Request(url, headers=request_headers)
            try:
                with self.opener.open(req, timeout=self.timeout) as response:
                    charset = response.headers.get_content_charset() or "utf-8"
                    return response.read().decode(charset, errors="replace")
            except urllib.error.HTTPError as exc:
                body = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and attempt < self.retries:
                    retry_after = exc.headers.get("Retry-After")
                    try:
                        wait = float(retry_after) if retry_after else 5.0 * (attempt + 1)
                    except ValueError:
                        wait = 5.0 * (attempt + 1)
                    progress(f"[http] 429 rate limited; sleeping {wait:.1f}s before retry")
                    time.sleep(wait)
                    continue
                if attempt >= self.retries:
                    raise RuntimeError(f"HTTP {exc.code} for {url}: {body[:200]}") from exc
            except urllib.error.URLError as exc:
                if attempt >= self.retries:
                    raise RuntimeError(f"Request failed for {url}: {exc}") from exc

            time.sleep(1.0 + attempt)

        raise RuntimeError(f"Request failed for {url}")

    def get_json(self, url: str, headers: dict[str, str] | None = None) -> Any:
        return json.loads(self.get_text(url, headers=headers))

    def _polite_sleep(self) -> None:
        if self.delay <= 0:
            return
        elapsed = time.monotonic() - self._last_request_at
        wait = self.delay - elapsed
        if wait > 0:
            time.sleep(wait)
        self._last_request_at = time.monotonic()


def normalize_name(name: str) -> str:
    name = html.unescape(name or "")
    name = re.sub(r"\s+", " ", name).strip()
    return name


def canonical_name(name: str) -> str:
    normalized = normalize_name(name).casefold()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def clean_url(url: str | None, base: str = "") -> str:
    if not url:
        return ""
    url = html.unescape(str(url)).strip()
    if not url:
        return ""
    if base:
        return urllib.parse.urljoin(base, url)
    return url


def walk_dicts(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_dicts(child)


def progress(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def approved_zip_categories(raw_categories: Iterable[str], fallback: str) -> set[str]:
    approved = set(ordered_categories("zip"))
    categories: set[str] = set()
    for category in raw_categories:
        normalized = ZIP_CATEGORY_ALIASES.get(category, category)
        if normalized in approved:
            categories.add(normalized)
    if not categories and fallback:
        categories.add(fallback)
    return categories


def extract_gatsby_page_data_path(page_url: str) -> str:
    parsed = urllib.parse.urlparse(page_url)
    path = parsed.path.strip("/")
    if not path:
        return "/page-data/index/page-data.json"
    return f"/page-data/{path}/page-data.json"


def scrape_affirm(http: HttpClient, args: argparse.Namespace) -> list[ScrapedMerchant]:
    rows: list[ScrapedMerchant] = []
    base = "https://www.affirm.com"

    progress(f"[affirm] directory entry: {AFFIRM_BROWSE_URL}")
    for idx, (category, slugs) in enumerate(AFFIRM_CATEGORIES, start=1):
        before_category = len(rows)
        progress(f"[affirm] {idx}/{len(AFFIRM_CATEGORIES)} {category}: fetching page-data")
        for slug in slugs:
            source_url = f"{base}/shopping/{slug}"
            page_data_url = urllib.parse.urljoin(base, extract_gatsby_page_data_path(source_url))
            data = http.get_json(page_data_url)
            before_slug = len(rows)

            for node in walk_dicts(data):
                name_obj = node.get("name")
                merchant_name = ""
                if isinstance(name_obj, dict):
                    merchant_name = normalize_name(str(name_obj.get("name") or ""))
                elif isinstance(name_obj, str):
                    merchant_name = normalize_name(name_obj)

                if not merchant_name:
                    continue
                if not (node.get("ari") or node.get("logoImage") or node.get("featuredImage")):
                    continue

                merchant_url = clean_url(node.get("linkOverride"), base)
                rows.append(
                    ScrapedMerchant(
                        provider="affirm",
                        merchant_name=merchant_name,
                        category=category,
                        source_url=source_url,
                        merchant_url=merchant_url,
                    )
                )
            progress(f"[affirm] {category}/{slug}: +{len(rows) - before_slug} raw hits")
        progress(f"[affirm] {category}: subtotal +{len(rows) - before_category} raw hits")
    return rows


def extract_klarna_listing(html_text: str) -> dict[str, Any]:
    match = re.search(
        r'<script[^>]+id="initial_payload"[^>]*>(.*?)</script>',
        html_text,
        flags=re.S,
    )
    if not match:
        raise ValueError("Could not find Klarna initial_payload script")

    payload = json.loads(html.unescape(match.group(1)))
    queries = payload.get("__DEHYDRATED_QUERY_STATE__", {}).get("queries", [])
    for query in queries:
        query_key = query.get("queryKey") or []
        if query_key and query_key[0] == "STORE_DIRECTORY_LISTING":
            return query.get("state", {}).get("data", {}).get("pages", [{}])[0]
    raise ValueError("Could not find Klarna STORE_DIRECTORY_LISTING query")


def scrape_klarna(http: HttpClient, args: argparse.Namespace) -> list[ScrapedMerchant]:
    rows: list[ScrapedMerchant] = []
    api_base = "https://www.klarna.com/us/api/store-edge-rest/public/stores/directory/search/US"
    page_size = 24
    cache: dict[tuple[str, str], list[dict[str, Any]]] = {}

    progress(f"[klarna] directory entry: {KLARNA_STORE_URL}")

    def fetch_stores(
        store_category: str,
        search_query: str,
        source_url: str,
        category: str,
    ) -> list[dict[str, Any]]:
        key = (store_category, search_query)
        filter_label = f"category={store_category}" if store_category else f"q={search_query}"
        if key in cache:
            progress(f"[klarna] {category}: reusing cached {filter_label} ({len(cache[key])} stores)")
            return cache[key]

        page = 1
        total_hits = None
        stores_for_filter: list[dict[str, Any]] = []
        progress(f"[klarna] {category}: fetching {filter_label}")
        while True:
            offset = (page - 1) * page_size
            params = {
                "sort": "RANK",
                "cashback": "false",
                "categories": store_category,
                "klarnaIntegrated": "false",
                "applePay": "false",
                "googlePay": "false",
                "inStore": "false",
                "q": search_query,
                "otcEnabled": "false",
                "offset": str(offset),
                "size": str(page_size),
            }
            api_url = api_base + "?" + urllib.parse.urlencode(params)
            listing = http.get_json(
                api_url,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Referer": source_url,
                    "x-client-service": "owp",
                    "x-forwarded-proto": "https",
                    "x-owp-client-version": "scraper",
                    "X-Klarna-Market": "US",
                    "X-Market": "US",
                },
            )
            stores = listing.get("stores") or []
            stores_for_filter.extend(stores)
            if total_hits is None:
                total_hits = int(listing.get("totalHits") or 0)
                progress(f"[klarna] {category}: totalHits={total_hits}")

            progress(f"[klarna] {category}: page {page}, +{len(stores)} stores")
            if not stores or len(stores) < page_size:
                break
            if args.max_pages and page >= args.max_pages:
                break
            if total_hits and offset + len(stores) >= total_hits:
                break
            page += 1

        cache[key] = stores_for_filter
        return stores_for_filter

    for idx, (category, config) in enumerate(KLARNA_CATEGORIES, start=1):
        store_category = config.get("store_category", "")
        search_query = config.get("search_query", "")
        source_url = (
            f"https://www.klarna.com/us/shopping/t/{config['tree_id']}/{config['tree_slug']}/"
        )
        filter_label = f"category={store_category}" if store_category else f"q={search_query}"
        progress(
            f"[klarna] {idx}/{len(KLARNA_CATEGORIES)} {category}: assigning stores from {filter_label}"
        )
        before = len(rows)
        for store in fetch_stores(store_category, search_query, source_url, category):
            name = normalize_name(str(store.get("displayName") or ""))
            if not name:
                continue
            merchant_url = clean_url(store.get("storeUrl"), "https://www.klarna.com")
            rows.append(
                ScrapedMerchant(
                    provider="klarna",
                    merchant_name=name,
                    category=category,
                    source_url=source_url,
                    merchant_url=merchant_url,
                )
            )
        progress(f"[klarna] {category}: +{len(rows) - before} raw merchant-category hits")

    return rows


def scrape_afterpay(http: HttpClient, args: argparse.Namespace) -> list[ScrapedMerchant]:
    rows: list[ScrapedMerchant] = []
    api_base = "https://store-directory-api.afterpay.com/api/v1/categories"
    page_base = "https://www.afterpay.com/en-US/categories"

    for idx, (category, slugs) in enumerate(AFTERPAY_CATEGORIES, start=1):
        progress(f"[afterpay] {idx}/{len(AFTERPAY_CATEGORIES)} {category}: {', '.join(slugs)}")
        for slug in slugs:
            source_url = f"{page_base}/{slug}"
            page = 1
            offset = 0
            per_page = args.page_size
            slug_total = 0
            while True:
                params = {
                    "locale": "en-US",
                    "publisher": "AP",
                    "offset": str(offset),
                    "per_page": str(per_page),
                }
                url = f"{api_base}/{slug}/stores?" + urllib.parse.urlencode(params)
                data = http.get_json(url)
                stores = data.get("data") or []

                for store in stores:
                    attributes = store.get("attributes") or {}
                    name = normalize_name(str(attributes.get("name") or ""))
                    if not name:
                        continue
                    merchant_url = clean_url(attributes.get("merchant_outbound_url"))
                    rows.append(
                        ScrapedMerchant(
                            provider="afterpay",
                            merchant_name=name,
                            category=category,
                            source_url=source_url,
                            merchant_url=merchant_url,
                        )
                    )
                    slug_total += 1

                next_url = (data.get("links") or {}).get("next")
                progress(f"[afterpay] {category}/{slug}: page {page}, +{len(stores)} stores")
                if not stores or not next_url:
                    break
                if args.max_pages and page >= args.max_pages:
                    break
                offset += per_page
                page += 1
            progress(f"[afterpay] {category}/{slug}: subtotal {slug_total}")

    return rows


def extract_zip_apollo_objects(html_text: str) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    pos = 0
    while True:
        marker = html_text.find("ApolloSSRDataTransport", pos)
        if marker < 0:
            break
        push_start = html_text.find("push(", marker)
        object_start = html_text.find("{", push_start)
        if push_start < 0 or object_start < 0:
            break

        depth = 0
        in_string = False
        escaped = False
        for idx in range(object_start, len(html_text)):
            char = html_text[idx]
            if in_string:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == '"':
                    in_string = False
            else:
                if char == '"':
                    in_string = True
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        raw = html_text[object_start : idx + 1]
                        objects.append(json.loads(html.unescape(raw)))
                        pos = idx + 1
                        break
        else:
            break
    return objects


def extract_zip_merchants(html_text: str) -> list[dict[str, Any]]:
    merchants: list[dict[str, Any]] = []
    seen: set[str] = set()
    for obj in extract_zip_apollo_objects(html_text):
        for node in walk_dicts(obj):
            if node.get("__typename") != "Merchant":
                continue
            name = normalize_name(str(node.get("display") or ""))
            if not name:
                continue
            key = str(node.get("merchant_slug") or canonical_name(name))
            if key in seen:
                continue
            seen.add(key)
            merchants.append(node)
    return merchants


def scrape_zip(http: HttpClient, args: argparse.Namespace) -> list[ScrapedMerchant]:
    rows: list[ScrapedMerchant] = []
    base = "https://zip.co"

    progress(f"[zip] directory entry: {ZIP_SHOP_ALL_URL}")
    for merchant in extract_zip_merchants(http.get_text(ZIP_SHOP_ALL_URL)):
        name = normalize_name(str(merchant.get("display") or ""))
        if not name:
            continue
        merchant_url = clean_url(merchant.get("url"))
        for category in approved_zip_categories(merchant.get("categories") or [], ""):
            rows.append(
                ScrapedMerchant(
                    provider="zip",
                    merchant_name=name,
                    category=category,
                    source_url=ZIP_SHOP_ALL_URL,
                    merchant_url=merchant_url,
                )
            )
    progress(f"[zip] shop-all seed: {len(rows)} approved raw merchant-category hits")

    for idx, (category, slug) in enumerate(ZIP_CATEGORIES, start=1):
        source_url = f"{base}/us/shop/{slug}"
        progress(f"[zip] {idx}/{len(ZIP_CATEGORIES)} {category}: fetching page")
        html_text = http.get_text(source_url)
        page_hits = 0
        for merchant in extract_zip_merchants(html_text):
            name = normalize_name(str(merchant.get("display") or ""))
            if not name:
                continue
            merchant_url = clean_url(merchant.get("url"))
            for approved_category in approved_zip_categories(
                merchant.get("categories") or [],
                category,
            ):
                rows.append(
                    ScrapedMerchant(
                        provider="zip",
                        merchant_name=name,
                        category=approved_category,
                        source_url=source_url,
                        merchant_url=merchant_url,
                    )
                )
                page_hits += 1
        progress(f"[zip] {category}: +{page_hits} approved raw merchant-category hits")

    return rows


def scrape_sezzle(http: HttpClient, args: argparse.Namespace) -> list[ScrapedMerchant]:
    rows: list[ScrapedMerchant] = []
    api_base = "https://api.directory.sezzle.com/v4/search"

    progress(f"[sezzle] directory entry: {SEZZLE_HOME_URL}")
    for idx, (category, slug_codes) in enumerate(SEZZLE_CATEGORIES, start=1):
        progress(f"[sezzle] {idx}/{len(SEZZLE_CATEGORIES)} {category}: starting API pagination")
        for slug, type_code in slug_codes:
            source_url = f"https://sezzle.com/shop/{slug}/"
            page = 1
            slug_total = 0
            while True:
                params = {
                    "limit": str(args.page_size),
                    "page": str(page),
                    "type-code": str(type_code),
                    "locale": "en-US",
                }
                url = api_base + "?" + urllib.parse.urlencode(params)
                data = http.get_json(url)
                stores = data.get("results") or []

                for store in stores:
                    name = normalize_name(str(store.get("name") or ""))
                    if not name:
                        continue
                    merchant_url = clean_url(store.get("website") or store.get("affiliate_link"))
                    rows.append(
                        ScrapedMerchant(
                            provider="sezzle",
                            merchant_name=name,
                            category=category,
                            source_url=source_url,
                            merchant_url=merchant_url,
                        )
                    )
                    slug_total += 1

                meta = data.get("meta") or {}
                total_pages = int(meta.get("total_pages") or page)
                progress(
                    f"[sezzle] {category}/{slug}: page {page}/{total_pages}, +{len(stores)} stores"
                )
                if not stores or page >= total_pages:
                    break
                if args.max_pages and page >= args.max_pages:
                    break
                page += 1
            progress(f"[sezzle] {category}/{slug}: subtotal {slug_total}")

    return rows


SCRAPERS = {
    "affirm": scrape_affirm,
    "klarna": scrape_klarna,
    "afterpay": scrape_afterpay,
    "zip": scrape_zip,
    "sezzle": scrape_sezzle,
}


def aggregate(rows: Iterable[ScrapedMerchant]) -> dict[tuple[str, str], AggregatedMerchant]:
    aggregated: dict[tuple[str, str], AggregatedMerchant] = {}

    for row in rows:
        name = normalize_name(row.merchant_name)
        if not name:
            continue
        key = (row.provider, canonical_name(name))
        if key not in aggregated:
            aggregated[key] = AggregatedMerchant(provider=row.provider, merchant_name=name)

        entry = aggregated[key]
        if len(name) > len(entry.merchant_name):
            entry.merchant_name = name
        entry.categories.add(row.category)
        entry.source_urls.add(row.source_url)
        if row.merchant_url:
            entry.merchant_urls.add(row.merchant_url)

    return aggregated


def ordered_categories(provider: str) -> list[str]:
    if provider == "affirm":
        return [category for category, _ in AFFIRM_CATEGORIES]
    if provider == "klarna":
        return [category for category, _ in KLARNA_CATEGORIES]
    if provider == "afterpay":
        return [category for category, _ in AFTERPAY_CATEGORIES]
    if provider == "zip":
        return [category for category, _ in ZIP_CATEGORIES]
    if provider == "sezzle":
        return [category for category, _ in SEZZLE_CATEGORIES]
    return []


def sort_categories(provider: str, categories: Iterable[str]) -> list[str]:
    order = {category: idx for idx, category in enumerate(ordered_categories(provider))}
    return sorted(categories, key=lambda category: (order.get(category, 9999), category))


def wide_rows(aggregated: dict[tuple[str, str], AggregatedMerchant]) -> list[dict[str, str]]:
    provider_rank = {provider: idx for idx, provider in enumerate(PROVIDER_ORDER)}
    output = []

    for entry in sorted(
        aggregated.values(),
        key=lambda item: (provider_rank.get(item.provider, 999), item.merchant_name.casefold()),
    ):
        output.append(
            {
                "merchant_name": entry.merchant_name,
                "categories": "; ".join(sort_categories(entry.provider, entry.categories)),
                "bnpl_provider": entry.provider,
                "source_urls": "; ".join(sorted(entry.source_urls)),
                "merchant_urls": "; ".join(sorted(entry.merchant_urls)),
            }
        )
    return output


def long_rows(aggregated: dict[tuple[str, str], AggregatedMerchant]) -> list[dict[str, str]]:
    provider_rank = {provider: idx for idx, provider in enumerate(PROVIDER_ORDER)}
    rows = []

    for entry in sorted(
        aggregated.values(),
        key=lambda item: (provider_rank.get(item.provider, 999), item.merchant_name.casefold()),
    ):
        for category in sort_categories(entry.provider, entry.categories):
            rows.append(
                {
                    "merchant_name": entry.merchant_name,
                    "category": category,
                    "bnpl_provider": entry.provider,
                    "source_urls": "; ".join(sorted(entry.source_urls)),
                    "merchant_urls": "; ".join(sorted(entry.merchant_urls)),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict[str, str]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "row_count": len(rows),
        "rows": rows,
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_summary(
    path: Path,
    provider_results: list[ProviderResult],
    wide: list[dict[str, str]],
    long: list[dict[str, str]],
    errors: dict[str, str],
    output_files: dict[str, str],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wide_counts = Counter(row["bnpl_provider"] for row in wide)
    long_counts = Counter(row["bnpl_provider"] for row in long)
    payload = {
        "scraped_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": output_files,
        "providers": [
            {
                "provider": result.provider,
                "raw_merchant_category_hits": result.raw_hits,
                "merchant_provider_rows": wide_counts.get(result.provider, 0),
                "merchant_category_rows": long_counts.get(result.provider, 0),
                "error": result.error,
            }
            for result in provider_results
        ],
        "totals": {
            "raw_merchant_category_hits": sum(result.raw_hits for result in provider_results),
            "merchant_provider_rows": len(wide),
            "merchant_category_rows": len(long),
            "provider_errors": errors,
        },
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_providers(value: str) -> list[str]:
    providers = [part.strip().lower() for part in value.split(",") if part.strip()]
    unknown = [provider for provider in providers if provider not in SCRAPERS]
    if unknown:
        raise argparse.ArgumentTypeError(f"Unknown providers: {', '.join(unknown)}")
    return providers


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Scrape BNPL merchant names, user-approved categories, and provider names."
    )
    parser.add_argument(
        "--providers",
        type=parse_providers,
        default=PROVIDER_ORDER,
        help="Comma-separated providers to scrape. Default: all.",
    )
    parser.add_argument(
        "--out",
        default="data/merchant_list_raw_data/BNPL_Merchant_List.csv",
        help="Wide CSV output path.",
    )
    parser.add_argument(
        "--long-out",
        default="data/merchant_list_raw_data/BNPL_Merchant_Categories.csv",
        help="Long merchant-category CSV output path.",
    )
    parser.add_argument(
        "--json-out",
        default="data/merchant_list_raw_data/bnpl_merchants.json",
        help="JSON output path.",
    )
    parser.add_argument(
        "--summary-out",
        default="data/merchant_list_raw_data/scrape_summary.json",
        help="JSON scrape summary output path.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=0,
        help="Limit paginated categories to this many pages. 0 means all pages.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=100,
        help="API page size where configurable. Klarna pages are fixed at 24.",
    )
    parser.add_argument("--delay", type=float, default=0.25, help="Delay between requests.")
    parser.add_argument("--timeout", type=int, default=30, help="Request timeout in seconds.")
    parser.add_argument("--retries", type=int, default=4, help="Retries per HTTP request.")
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification if local certificates are broken.",
    )
    parser.add_argument("--fail-fast", action="store_true", help="Stop on the first provider error.")
    parser.add_argument("--verbose", action="store_true", help="Print request/progress details.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_pages <= 0:
        args.max_pages = None

    http = HttpClient(
        timeout=args.timeout,
        insecure=args.insecure,
        delay=args.delay,
        retries=args.retries,
        verbose=args.verbose,
    )

    all_rows: list[ScrapedMerchant] = []
    errors: dict[str, str] = {}
    provider_results: list[ProviderResult] = []

    for provider in args.providers:
        result = ProviderResult(provider=provider)
        try:
            progress(f"[{provider}] scraping started")
            provider_rows = SCRAPERS[provider](http, args)
            all_rows.extend(provider_rows)
            result.raw_hits = len(provider_rows)
            progress(f"[{provider}] completed: {len(provider_rows)} raw merchant-category hits")
        except Exception as exc:
            errors[provider] = str(exc)
            result.error = str(exc)
            progress(f"[{provider}] ERROR: {exc}")
            if args.fail_fast:
                return 1
        provider_results.append(result)

    aggregated = aggregate(all_rows)
    wide = wide_rows(aggregated)
    long = long_rows(aggregated)
    write_csv(
        Path(args.out),
        wide,
        ["merchant_name", "categories", "bnpl_provider", "source_urls", "merchant_urls"],
    )

    if args.long_out:
        write_csv(
            Path(args.long_out),
            long,
            ["merchant_name", "category", "bnpl_provider", "source_urls", "merchant_urls"],
        )

    if args.json_out:
        write_json(Path(args.json_out), wide)

    if args.summary_out:
        output_files = {
            "wide_csv": args.out,
            "long_csv": args.long_out,
            "json": args.json_out,
            "summary_json": args.summary_out,
        }
        write_summary(Path(args.summary_out), provider_results, wide, long, errors, output_files)

    progress(f"[output] Wrote {len(wide)} merchant-provider rows to {args.out}")
    if args.long_out:
        progress(f"[output] Wrote {len(long)} merchant-category rows to {args.long_out}")
    if args.json_out:
        progress(f"[output] Wrote JSON copy to {args.json_out}")
    if args.summary_out:
        progress(f"[output] Wrote scrape summary to {args.summary_out}")
    if errors:
        progress("[output] Completed with provider errors:")
        for provider, message in errors.items():
            progress(f"  {provider}: {message}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
