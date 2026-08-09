import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const outDir = path.join(repoRoot, "data", "merchant_ownership");
const rowsPath = path.join(outDir, "merchant_ownership_rows.json");
const outputPath = path.join(outDir, "BNPL_Merchant_Ownership_List.xlsx");

const publicHeaders = [
  "Merchant Name",
  "Categories",
  "BNPL Providers",
  "Number of Platforms",
  "Ownership Type",
  "SEC Matched Company",
  "Ticker",
  "CIK",
  "Exchange",
  "Company Size",
  "Market Cap 2026-07-31",
  "Close Price 2026-07-31",
  "Price Date",
  "Shares Outstanding",
  "Shares Date",
  "Match Method",
  "Match Score",
  "Market Cap Source",
  "Shares Source",
  "Market Data Notes",
  "SEC Company Page",
  "SEC Ticker Source",
  "Market Price Source",
];

const privateHeaders = [
  "Merchant Name",
  "Categories",
  "BNPL Providers",
  "Number of Platforms",
  "Ownership Type",
  "Match Method",
  "SEC Ticker Source",
];

const sheetDefinitions = [
  {
    name: "public company",
    headers: publicHeaders,
    filter: (row) => row.ownership_type === "Public company",
    tableName: "PublicCompanyTable",
  },
  {
    name: "private company",
    headers: privateHeaders,
    filter: (row) => row.ownership_type !== "Public company",
    tableName: "PrivateCompanyTable",
  },
  {
    name: "large-cap company",
    headers: publicHeaders,
    filter: (row) => row.ownership_type === "Public company" && row.company_size === "Large-cap",
    tableName: "LargeCapCompanyTable",
  },
  {
    name: "mid-cap company",
    headers: publicHeaders,
    filter: (row) => row.ownership_type === "Public company" && row.company_size === "Mid-cap",
    tableName: "MidCapCompanyTable",
  },
  {
    name: "small-cap company",
    headers: publicHeaders,
    filter: (row) => row.ownership_type === "Public company" && row.company_size === "Small-cap",
    tableName: "SmallCapCompanyTable",
  },
];

const fieldByHeader = new Map([
  ["Merchant Name", "merchant_name"],
  ["Categories", "categories"],
  ["BNPL Providers", "bnpl_providers"],
  ["Number of Platforms", "number_of_platforms"],
  ["Ownership Type", "ownership_type"],
  ["SEC Matched Company", "sec_matched_company"],
  ["Ticker", "ticker"],
  ["CIK", "cik"],
  ["Exchange", "exchange"],
  ["Company Size", "company_size"],
  ["Market Cap 2026-07-31", "market_cap_2026_07_31"],
  ["Close Price 2026-07-31", "close_price_2026_07_31"],
  ["Price Date", "price_date"],
  ["Shares Outstanding", "shares_outstanding"],
  ["Shares Date", "shares_date"],
  ["Match Method", "match_method"],
  ["Match Score", "match_score"],
  ["Market Cap Source", "market_cap_source"],
  ["Shares Source", "shares_source"],
  ["Market Data Notes", "market_data_notes"],
  ["SEC Company Page", "sec_company_page"],
  ["SEC Ticker Source", "sec_company_tickers_source"],
  ["Market Price Source", "market_price_source"],
]);

function log(message) {
  console.log(`[workbook] ${message}`);
}

function valueFor(row, header) {
  const field = fieldByHeader.get(header);
  const value = row[field];
  return value === undefined || value === null ? "" : value;
}

function sortRows(rows) {
  return [...rows].sort((a, b) => {
    const capA = Number(a.market_cap_2026_07_31 ?? -1);
    const capB = Number(b.market_cap_2026_07_31 ?? -1);
    if (capA !== capB && (capA >= 0 || capB >= 0)) return capB - capA;
    return String(a.merchant_name).localeCompare(String(b.merchant_name));
  });
}

function colLetter(index) {
  let n = index + 1;
  let out = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    out = String.fromCharCode(65 + rem) + out;
    n = Math.floor((n - 1) / 26);
  }
  return out;
}

function applyBaseFormatting(sheet, rowCount, colCount) {
  const endCol = colLetter(colCount - 1);
  const fullRange = sheet.getRange(`A1:${endCol}${Math.max(rowCount, 1)}`);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(1);

  fullRange.format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
      insideVertical: { style: "thin", color: "#E5E7EB" },
      bottom: { style: "thin", color: "#D1D5DB" },
    },
  };

  sheet.getRange(`A1:${endCol}1`).format = {
    fill: "#111827",
    font: { bold: true, color: "#FFFFFF", size: 11 },
    horizontalAlignment: "Center",
    verticalAlignment: "Center",
    wrapText: true,
  };
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 34;
}

function applyColumnWidths(sheet, headers) {
  headers.forEach((header, index) => {
    const col = colLetter(index);
    let width = 18;
    if (header === "Merchant Name") width = 32;
    if (header === "Categories") width = 48;
    if (header === "BNPL Providers") width = 24;
    if (header === "Ownership Type") width = 26;
    if (header === "SEC Matched Company") width = 34;
    if (header === "Company Size") width = 18;
    if (header === "Match Method") width = 34;
    if (header.includes("Source") || header.includes("Notes") || header.includes("Page")) width = 42;
    if (["Ticker", "CIK", "Exchange", "Match Score"].includes(header)) width = 13;
    sheet.getRange(`${col}:${col}`).format.columnWidth = width;
  });
}

function applyNumberFormats(sheet, headers, rowCount) {
  if (rowCount < 2) return;
  headers.forEach((header, index) => {
    const col = colLetter(index);
    const range = sheet.getRange(`${col}2:${col}${rowCount}`);
    if (header === "Number of Platforms" || header === "Match Score") {
      range.format = { horizontalAlignment: "Center", numberFormat: "#,##0" };
    }
    if (header === "Market Cap 2026-07-31") {
      range.format = { horizontalAlignment: "Right", numberFormat: "$#,##0" };
    }
    if (header === "Close Price 2026-07-31") {
      range.format = { horizontalAlignment: "Right", numberFormat: "$0.00" };
    }
    if (header === "Shares Outstanding") {
      range.format = { horizontalAlignment: "Right", numberFormat: "#,##0" };
    }
    if (header === "Price Date" || header === "Shares Date") {
      range.format = { horizontalAlignment: "Center" };
    }
    if (header === "Categories" || header === "Match Method" || header.includes("Source") || header.includes("Notes")) {
      range.format = { wrapText: true, verticalAlignment: "Top" };
    }
  });
}

function addSheet(workbook, definition, allRows) {
  const rows = sortRows(allRows.filter(definition.filter));
  const sheet = workbook.worksheets.add(definition.name);
  const matrix = [
    definition.headers,
    ...rows.map((row) => definition.headers.map((header) => valueFor(row, header))),
  ];
  const rowCount = matrix.length;
  const colCount = definition.headers.length;
  sheet.getRangeByIndexes(0, 0, rowCount, colCount).values = matrix;
  const endCol = colLetter(colCount - 1);
  sheet.tables.add(`A1:${endCol}${rowCount}`, true, definition.tableName);
  applyBaseFormatting(sheet, rowCount, colCount);
  applyColumnWidths(sheet, definition.headers);
  applyNumberFormats(sheet, definition.headers, rowCount);
  log(`${definition.name}: ${rows.length.toLocaleString()} row(s).`);
}

async function verifyWorkbook(workbook) {
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  log(`Formula error scan: ${errors.ndjson.includes('"match"') ? "review needed" : "no visible errors"}.`);

  for (const definition of sheetDefinitions) {
    const endCol = colLetter(Math.min(definition.headers.length, 12) - 1);
    const preview = await workbook.render({
      sheetName: definition.name,
      range: `A1:${endCol}20`,
      scale: 1,
      format: "png",
    });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    if (!bytes.length) throw new Error(`Rendered preview is empty for ${definition.name}`);
  }
  log(`Rendered preview check completed for ${sheetDefinitions.length} sheet(s).`);
}

async function main() {
  const rows = JSON.parse(await fs.readFile(rowsPath, "utf8"));
  const workbook = Workbook.create();
  log(`Loaded ${rows.length.toLocaleString()} merchant ownership row(s).`);

  for (const definition of sheetDefinitions) {
    addSheet(workbook, definition, rows);
  }

  await verifyWorkbook(workbook);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  log(`Saved ${path.relative(repoRoot, outputPath)}.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
