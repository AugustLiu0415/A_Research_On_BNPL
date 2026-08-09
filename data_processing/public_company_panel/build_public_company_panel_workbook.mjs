import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = process.argv[2] || path.resolve("data/public_company_panel_data");
const workbookPath = path.join(outputDir, "public_company_panel_data_2015-2026.xlsx");

function parseCsv(text) {
  const rows = [];
  let row = [];
  let cell = "";
  let inQuotes = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];
    if (ch === '"' && inQuotes && next === '"') {
      cell += '"';
      i++;
    } else if (ch === '"') {
      inQuotes = !inQuotes;
    } else if (ch === "," && !inQuotes) {
      row.push(cell);
      cell = "";
    } else if ((ch === "\n" || ch === "\r") && !inQuotes) {
      if (ch === "\r" && next === "\n") i++;
      row.push(cell);
      if (row.some((v) => v !== "")) rows.push(row);
      row = [];
      cell = "";
    } else {
      cell += ch;
    }
  }
  row.push(cell);
  if (row.some((v) => v !== "")) rows.push(row);
  return rows;
}

function coerceValue(value, header) {
  if (value === "") return null;
  if (/^(CIK|company_id|unique_company_id)$/i.test(header)) {
    const n = Number(value);
    if (!Number.isNaN(n)) return n;
    return value;
  }
  if (/^retrieved_at$/i.test(header)) return value;
  if (/date|period_start|period_end|retrieved_at|filed/i.test(header) && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    const dateOnly = value.slice(0, 10);
    const d = new Date(`${dateOnly}T00:00:00Z`);
    if (!Number.isNaN(d.getTime())) return d;
  }
  if (/flag|required|configured/i.test(header) && /^(true|false)$/i.test(value)) return /^true$/i.test(value);
  if (/^(fiscal_year|calendar_year|merchant_count|input_public_merchant_rows|number_of_quarters|expected_available_quarters|duration_days|companies_|unique_|total_|.*count|.*rows)$/i.test(header)) {
    const n = Number(value);
    if (!Number.isNaN(n)) return n;
  }
  if (/revenue|profit|income|assets|liabilities|equity|cash|debt|expense|inventory|receivable|shares|expenditures|margin|growth|coverage|missingness|value|eps|rate|price|cap/i.test(header)) {
    const n = Number(value);
    if (!Number.isNaN(n)) return n;
  }
  return value;
}

async function loadCsvMatrix(filePath, maxRows = null) {
  const text = await fs.readFile(filePath, "utf8");
  const rows = parseCsv(text);
  if (!rows.length) return [["No data"]];
  const headers = rows[0];
  const dataRows = maxRows ? rows.slice(1, maxRows + 1) : rows.slice(1);
  return [headers, ...dataRows.map((row) => headers.map((header, idx) => coerceValue(row[idx] ?? "", header)))];
}

function colName(n) {
  let name = "";
  while (n > 0) {
    const rem = (n - 1) % 26;
    name = String.fromCharCode(65 + rem) + name;
    n = Math.floor((n - 1) / 26);
  }
  return name;
}

function writeSheet(workbook, sheetName, matrix, options = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const rowCount = matrix.length;
  const colCount = Math.max(...matrix.map((r) => r.length));
  const normalized = matrix.map((row) => {
    const out = row.slice();
    while (out.length < colCount) out.push(null);
    return out;
  });
  const range = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  range.values = normalized;
  sheet.freezePanes.freezeRows(1);
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format.fill.color = "#1F4E78";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.wrapText = true;
  header.format.rowHeight = 34;
  if (rowCount > 1) {
    const body = sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount);
    body.format.font.color = "#000000";
  }
  const used = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  used.format.borders = { preset: "inside", style: "thin", color: "#E1E5EA" };
  used.format.autofitColumns();
  used.format.autofitRows();

  const headers = normalized[0];
  for (let c = 0; c < headers.length; c++) {
    const h = String(headers[c] || "");
    const column = sheet.getRangeByIndexes(1, c, Math.max(rowCount - 1, 1), 1);
    if (/^(CIK|company_id|unique_company_id)$/i.test(h)) column.setNumberFormat("0000000000");
    if (/date|period_start|period_end|retrieved_at|filed/i.test(h)) column.setNumberFormat("yyyy-mm-dd");
    if (/margin|growth|coverage|missingness|rate/i.test(h)) column.setNumberFormat("0.0%");
    if (/revenue|profit|income|assets|liabilities|equity|cash|debt|expense|inventory|receivable|expenditures|selected_value/i.test(h)) column.setNumberFormat('#,##0;[Red](#,##0);-');
    if (/eps/i.test(h)) column.setNumberFormat('$0.00;[Red]($0.00);-');
    if (/shares|count|rows|quarters|duration_days/i.test(h)) column.setNumberFormat("#,##0");
  }

  const widths = options.widths || {};
  for (const [idx, width] of Object.entries(widths)) {
    sheet.getRangeByIndexes(0, Number(idx), rowCount, 1).format.columnWidth = width;
  }
  return sheet;
}

const workbook = Workbook.create();

const sheets = [
  ["Panel_Quarterly", "public_company_panel_data_2015-2026.csv", null, { 1: 14, 2: 28, 3: 28, 7: 45, 10: 16 }],
  ["Company_Crosswalk", "public_company_crosswalk.csv", null, { 2: 28, 3: 28, 6: 55, 7: 42, 12: 54, 13: 54 }],
  ["Variable_Definitions", "public_company_panel_variable_definitions.csv", null, { 0: 24, 1: 48, 2: 34, 3: 62, 6: 55 }],
  ["Coverage_Summary", "public_company_panel_coverage_summary.csv", null, { 1: 30, 2: 30 }],
  ["Source_Audit", "public_company_panel_source_audit.csv", 5000, { 1: 28, 9: 42, 17: 24, 21: 50 }],
  ["Validation_Report", "public_company_panel_validation_report.csv", null, { 1: 30, 6: 60, 7: 60 }],
  ["Manual_Review", "public_company_panel_manual_review.csv", null, { 1: 30, 3: 32, 5: 70 }],
];

for (const [sheetName, fileName, maxRows, widths] of sheets) {
  const matrix = await loadCsvMatrix(path.join(outputDir, fileName), maxRows);
  writeSheet(workbook, sheetName, matrix, { widths });
}

const summaryJson = JSON.parse(await fs.readFile(path.join(outputDir, "public_company_panel_summary.json"), "utf8"));
const summaryMatrix = [
  ["metric", "value"],
  ...Object.entries(summaryJson).map(([k, v]) => [k, k === "retrieved_at" ? `UTC ${v}` : v]),
];
writeSheet(workbook, "Processing_Summary", summaryMatrix, { widths: { 0: 36, 1: 40 } });

const errorScan = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errorScan.ndjson);

const previewDir = path.join(outputDir, "logs", "workbook_previews");
await fs.mkdir(previewDir, { recursive: true });
for (const sheetName of ["Panel_Quarterly", "Company_Crosswalk", "Variable_Definitions", "Coverage_Summary", "Source_Audit", "Validation_Report", "Manual_Review", "Processing_Summary"]) {
  const png = await workbook.render({ sheetName, range: "A1:H30", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await png.arrayBuffer()));
}

await fs.mkdir(outputDir, { recursive: true });
const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);
await fs.rm(`${workbookPath}.inspect.ndjson`, { force: true });
console.log(`Saved ${workbookPath}`);
