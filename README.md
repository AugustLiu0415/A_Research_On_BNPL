# Research on Merchant-side Effects of Buy Now Pay Later (BNPL)

This repository builds a merchant-level dataset for studying the merchant-side
effects of Buy Now Pay Later (BNPL) adoption. The current checkpoint scrapes
official BNPL merchant directories, builds provider/category overlap outputs,
and classifies merchants by public/private ownership and public-company size.

## Research Question

What are the short-run and long-run effects of BNPL adoption on merchants'
revenue growth, gross margins, and operating margins, and are these effects
heterogeneous across firms with different size and bargaining power?

## Hypotheses

1. H1: **Industry Heterogeneity Hypothesis**: The BNPL effect is stronger in discretionary, high-ticket, high-margin, and e-commerce-intensive industries.
2. H2: **Scale/Exposure Hypothesis**: BNPL adoption generates larger proportional revenue effects for smaller and more focused merchants because BNPL-enabled sales represent a larger share of firm-level sales.
3. H3: **Bargaining Power Hypothesis**: Conditional on BNPL exposure, larger merchants may experience smaller margin penalties because stronger bargaining power allows them to negotiate more favorable BNPL economics.

## Current Progress

1. Scraped merchant information from five major BNPL provider directories: Affirm, Klarna, Afterpay, Zip, and Sezzle.
2. Combined provider-level merchant lists into wide merchant-provider rows and long merchant-provider-category rows.
3. Built overlap workbooks showing merchants that appear on multiple BNPL platforms and category-specific merchant coverage by provider.
4. Built a merchant ownership dataset that classifies merchants as public or private using SEC ticker data, enriches matched public companies with 2026-07-31 market data, and assigns market-cap size buckets.

## Data Sources

1. Affirm merchant lists: <https://www.affirm.com/>
2. Klarna merchant list: <https://www.klarna.com/us/store/>
3. Afterpay merchant list: <https://www.afterpay.com/en-US>
4. Zip merchant list: <https://zip.co/us/shop/shop-all>
5. Sezzle merchant list: <https://sezzle.com/>
6. SEC company ticker files: <https://www.sec.gov/files/company_tickers.json> and <https://www.sec.gov/files/company_tickers_exchange.json>
7. SEC company facts API: <https://data.sec.gov/api/xbrl/companyfacts/>
8. Yahoo Finance chart API for historical close prices.

## Repository Structure

```text
.
├── README.md
├── bnpl_scraper.py
├── requirements.txt
├── data/
│   ├── merchant_list_raw_data/
│   │   ├── BNPL_Merchant_List.csv
│   │   ├── BNPL_Merchant_Categories.csv
│   │   ├── BNPL_Merchant_Categories.xlsx
│   │   ├── bnpl_merchants.json
│   │   └── scrape_summary.json
│   └── merchant_ownership/
│       ├── build_merchant_ownership_data.py
│       ├── build_merchant_ownership_workbook.mjs
│       ├── merchant_ownership_rows.json
│       ├── merchant_ownership_summary.json
│       └── BNPL_Merchant_Ownership_List.xlsx
└── data_processing/
    └── overlap_merchant_list/
        ├── build_overlap_merchant_lists.mjs
        ├── BNPL_Merchant_Overlap_List.xlsx
        └── BNPL_Merchant_with_Category_List.xlsx
```

Generated runtime folders such as `.venv/`, `__pycache__/`, and
`data/merchant_ownership/cache/` are intentionally ignored.

## Main Scripts

### `bnpl_scraper.py`

Scrapes merchant names, platform categories, BNPL provider names, source URLs,
and merchant URLs from the official merchant directories for Affirm, Klarna,
Afterpay, Zip, and Sezzle.

Default outputs:

- `data/merchant_list_raw_data/BNPL_Merchant_List.csv`
- `data/merchant_list_raw_data/BNPL_Merchant_Categories.csv`
- `data/merchant_list_raw_data/bnpl_merchants.json`
- `data/merchant_list_raw_data/scrape_summary.json`

### `data_processing/overlap_merchant_list/build_overlap_merchant_lists.mjs`

Reads the scraped merchant list and category list, then builds formatted Excel
workbooks for multi-platform merchant overlap and category-by-provider coverage.

Outputs:

- `data_processing/overlap_merchant_list/BNPL_Merchant_Overlap_List.xlsx`
- `data_processing/overlap_merchant_list/BNPL_Merchant_with_Category_List.xlsx`

### `data/merchant_ownership/build_merchant_ownership_data.py`

Aggregates unique merchants from the long category table, conservatively
matches merchant names to SEC public-company ticker records, fetches 2026-07-31
close prices and SEC share counts for matched public companies, and writes the
ownership rows and summary JSON.

Outputs:

- `data/merchant_ownership/merchant_ownership_rows.json`
- `data/merchant_ownership/merchant_ownership_summary.json`

### `data/merchant_ownership/build_merchant_ownership_workbook.mjs`

Converts the ownership JSON rows into a formatted Excel workbook with public,
private, large-cap, mid-cap, and small-cap sheets.

Output:

- `data/merchant_ownership/BNPL_Merchant_Ownership_List.xlsx`

## Current Final Output

The current raw scrape checkpoint was generated on 2026-08-09 UTC:

- 15,753 raw merchant-category hits.
- 9,434 merchant-provider rows.
- 14,627 merchant-category rows.
- Provider row coverage: Affirm 181, Klarna 2,790, Afterpay 3,030, Zip 398, Sezzle 3,035 merchant-provider rows.

The current ownership checkpoint contains:

- 8,470 unique merchants.
- 144 public-company rows.
- 8,326 private/no-direct-SEC-match rows.
- Public-company size buckets: 60 large-cap, 41 mid-cap, 22 small-cap, 17 micro/nano-cap, and 4 unknown market-cap rows.

Final deliverables currently tracked in the project are:

- `data/merchant_list_raw_data/BNPL_Merchant_List.csv`
- `data/merchant_list_raw_data/BNPL_Merchant_Categories.csv`
- `data/merchant_list_raw_data/BNPL_Merchant_Categories.xlsx`
- `data/merchant_list_raw_data/bnpl_merchants.json`
- `data/merchant_list_raw_data/scrape_summary.json`
- `data_processing/overlap_merchant_list/BNPL_Merchant_Overlap_List.xlsx`
- `data_processing/overlap_merchant_list/BNPL_Merchant_with_Category_List.xlsx`
- `data/merchant_ownership/merchant_ownership_rows.json`
- `data/merchant_ownership/merchant_ownership_summary.json`
- `data/merchant_ownership/BNPL_Merchant_Ownership_List.xlsx`

## Setup

Create and activate a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the scraper with the repository's default output paths:

```bash
python bnpl_scraper.py
```

For a small smoke test while editing:

```bash
python bnpl_scraper.py \
  --max-pages 1 \
  --delay 0 \
  --out data/merchant_list_raw_data/sample.csv \
  --long-out data/merchant_list_raw_data/sample_long.csv \
  --json-out data/merchant_list_raw_data/sample.json \
  --summary-out data/merchant_list_raw_data/sample_summary.json
```

If Python reports a local certificate problem on macOS, rerun with:

```bash
python bnpl_scraper.py --insecure
```

Build ownership JSON after the raw category file exists:

```bash
python data/merchant_ownership/build_merchant_ownership_data.py
```

The `.mjs` workbook builders use the Codex artifact spreadsheet runtime:

```bash
node data_processing/overlap_merchant_list/build_overlap_merchant_lists.mjs
node data/merchant_ownership/build_merchant_ownership_workbook.mjs
```
