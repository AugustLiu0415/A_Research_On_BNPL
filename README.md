# Research of Merchant-side Effect of Buy Now Pay Later, BNPL

This repository builds a merchant-level dataset for studying the merchant-side
effects of Buy Now Pay Later (BNPL) adoption. The current project checkpoint
focuses on scraping official BNPL merchant directories, combining provider-level
merchant lists, and classifying merchants using each platform's own category
system.

## Research Question

What are the short-run and long-run effects of BNPL adoption on merchants'
revenue growth, gross margins, and operating margins, and are these effects
heterogenous across firms with different size and bargaining power?

## Hypothesis

1. H1: Industry Heterogeneity Hypothesis: The BNPL effect is stronger in discretionary, high-ticket, high-margin, and e-commerce-intensive industries.
2. H2: Firm Size Hypothesis: BNPL effects are more detectable among small- and mid-cap focused retailers than among large diversified merchants.

## Current Progress

1. Scraped merchant info from five major BNPL provider directories: Affirm, Klarna, Afterpay, Zip, Sezzle and combined them into a long merchant info table.
2. Classified merchants into different categories based on platform's categories.

## Data Sources

1. Affirm merchant lists: <https://www.affirm.com/>
2. Klarna merchant list: <https://www.klarna.com/us/store/>
3. Afterpay merchant list: <https://www.afterpay.com/en-US>
4. Zip merchant list: <https://zip.co/us/shop/shop-all>
5. Sezzle merchant list: <https://sezzle.com/>

## Repository Structure

```text
.
├── README.md
├── bnpl_scraper.py
├── requirements.txt
└── data/
    ├── BNPL_Merchant_List_Classified.csv
    ├── BNPL_Merchant_List_Classified.xlsx
    ├── BNPL_Merchant_list.csv
    ├── bnpl_merchants.csv
    ├── bnpl_merchants.json
    ├── bnpl_merchants_long.csv
    └── sample.json
```

## Main Scripts

### `bnpl_scraper.py`

Scrapes merchant names, platform categories, BNPL provider names, source URLs,
and merchant URLs from the official merchant directories for Affirm, Klarna,
Afterpay, Zip, and Sezzle.

The script produces:

- a wide merchant-provider table, where categories are combined into one field;
- a long merchant-provider-category table, where each category is one row;
- an optional JSON copy of the wide output.

## Current Final Output

Current output files in the project folder:

- `data/bnpl_merchants.csv`: wide merchant-provider table.
- `data/bnpl_merchants_long.csv`: long merchant-provider-category table.
- `data/bnpl_merchants.json`: JSON version of the wide merchant-provider table.
- `data/BNPL_Merchant_list.csv`: current combined merchant list file.
- `data/BNPL_Merchant_List_Classified.csv`: current classified merchant-category table.
- `data/BNPL_Merchant_List_Classified.xlsx`: Excel version of the classified merchant-category table.
- `data/sample.json`: small smoke-test JSON output.

## Setup

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run the current scraper:

```bash
python bnpl_scraper.py \
  --out data/bnpl_merchants.csv \
  --json-out data/bnpl_merchants.json \
  --long-out data/bnpl_merchants_long.csv
```

For a small smoke test while editing:

```bash
python bnpl_scraper.py \
  --max-pages 1 \
  --delay 0 \
  --out data/sample.csv \
  --json-out data/sample.json \
  --long-out data/sample_long.csv
```

If Python reports a local certificate problem on macOS, rerun with:

```bash
python bnpl_scraper.py --insecure
```
