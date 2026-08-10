import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const outputDir = process.argv[2] || path.resolve("data_processing/controls_group_panel_data");
const workbookPath = path.join(outputDir, "controls_group_panel_data_2015_2026.xlsx");

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
  if (/^(CIK|company_id|unique_company_id|treated_CIK|control_CIK|matched_treated_CIK)$/i.test(header)) {
    const n = Number(value);
    return Number.isNaN(n) ? value : n;
  }
  if (/date|period_start|period_end|retrieved_at|filed|source_date/i.test(header) && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    const d = new Date(`${value.slice(0, 10)}T00:00:00Z`);
    if (!Number.isNaN(d.getTime())) return d;
  }
  if (/^(true|false)$/i.test(value) && /flag|required|sample|used|history/i.test(header)) {
    return /^true$/i.test(value);
  }
  if (/count|rows|rank|year|quarter|duration_days|firm_count|companies|number_of/i.test(header)) {
    const n = Number(value);
    if (!Number.isNaN(n)) return n;
  }
  if (/revenue|profit|income|assets|liabilities|equity|cash|debt|expense|inventory|receivable|shares|expenditures|margin|growth|coverage|missingness|distance|smd|mean|median|value|eps|rate|cap|log_|trend|leverage/i.test(header)) {
    const n = Number(value);
    if (!Number.isNaN(n)) return n;
  }
  return value;
}

async function loadCsvMatrix(fileName, maxRows = null) {
  const filePath = path.join(outputDir, fileName);
  const text = await fs.readFile(filePath, "utf8");
  const rows = parseCsv(text);
  if (!rows.length) return [["No data"]];
  const headers = rows[0];
  const dataRows = maxRows ? rows.slice(1, maxRows + 1) : rows.slice(1);
  return [headers, ...dataRows.map((row) => headers.map((header, idx) => coerceValue(row[idx] ?? "", header)))];
}

function writeSheet(workbook, sheetName, matrix, options = {}) {
  const sheet = workbook.worksheets.add(sheetName);
  sheet.showGridLines = false;
  const rowCount = Math.max(matrix.length, 1);
  const colCount = Math.max(...matrix.map((r) => r.length), 1);
  const normalized = matrix.map((row) => {
    const out = row.slice();
    while (out.length < colCount) out.push(null);
    return out;
  });
  const range = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  range.values = normalized;
  sheet.freezePanes.freezeRows(1);

  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format.fill.color = "#174A5C";
  header.format.font.color = "#FFFFFF";
  header.format.font.bold = true;
  header.format.wrapText = true;
  header.format.rowHeight = 34;

  if (rowCount > 1) {
    const body = sheet.getRangeByIndexes(1, 0, rowCount - 1, colCount);
    body.format.font.color = "#111827";
  }

  const used = sheet.getRangeByIndexes(0, 0, rowCount, colCount);
  used.format.borders = { preset: "inside", style: "thin", color: "#E5E7EB" };
  used.format.autofitColumns();
  used.format.autofitRows();

  const headers = normalized[0];
  for (let c = 0; c < headers.length; c++) {
    const h = String(headers[c] || "");
    const column = sheet.getRangeByIndexes(1, c, Math.max(rowCount - 1, 1), 1);
    if (/^(CIK|company_id|unique_company_id|treated_CIK|control_CIK|matched_treated_CIK)$/i.test(h)) column.setNumberFormat("0000000000");
    if (/date|period_start|period_end|retrieved_at|filed|source_date/i.test(h)) column.setNumberFormat("yyyy-mm-dd");
    if (/margin|growth|coverage|missingness|rate|smd|leverage|assets_pre|to_assets|trend/i.test(h)) column.setNumberFormat("0.0%");
    if (/revenue|profit|income|assets|liabilities|equity|cash|debt|expense|inventory|receivable|expenditures|selected_value|market_cap/i.test(h)) column.setNumberFormat('#,##0;[Red](#,##0);-');
    if (/eps/i.test(h)) column.setNumberFormat('$0.00;[Red]($0.00);-');
    if (/shares|count|rows|quarters|duration_days|rank/i.test(h)) column.setNumberFormat("#,##0");
    if (/distance|log_/i.test(h)) column.setNumberFormat("0.000");
  }

  const widths = options.widths || {};
  for (const [idx, width] of Object.entries(widths)) {
    sheet.getRangeByIndexes(0, Number(idx), rowCount, 1).format.columnWidth = width;
  }
  return sheet;
}

const workbook = Workbook.create();

const sheetSpecs = [
  ["Control_Panel_Quarterly", "controls_group_panel_data_2015_2026.csv", null, { 2: 28, 3: 28, 8: 14 }],
  ["Control_Master", "controls_group_master.csv", null, { 1: 30, 7: 28, 8: 28, 11: 28 }],
  ["Candidate_Donor_Pool", "controls_candidate_donor_pool.csv", null, { 1: 30, 8: 28, 9: 28, 13: 38, 30: 38 }],
  ["Matching_Results", "controls_matching_results.csv", null, { 1: 30, 6: 30, 25: 55 }],
  ["Balance_Diagnostics", "matching_balance_diagnostics.csv", null, { 0: 28, 8: 55 }],
  ["Pretrend_Diagnostics", "pretrend_diagnostics.csv", null, { 0: 18 }],
  ["Industry_Classification", "controls_industry_classification.csv", null, { 2: 30, 5: 38, 6: 30, 7: 28, 10: 70 }],
  ["BNPL_Verification", "bnpl_control_verification_log.csv", null, { 0: 30, 3: 58, 6: 70, 9: 28, 10: 70 }],
  ["Coverage_Summary", "controls_group_panel_coverage_summary.csv", null, { 1: 30, 2: 28 }],
  ["Source_Audit", "controls_group_panel_source_audit.csv", 5000, { 1: 28, 9: 42, 17: 24, 21: 55 }],
  ["Validation_Report", "controls_group_panel_validation_report.csv", null, { 1: 32, 6: 62, 7: 62 }],
  ["Manual_Review", "controls_group_panel_manual_review.csv", null, { 1: 30, 3: 32, 5: 72 }],
  ["Treated_Sample_Profile", "treated_sample_profile.csv", null, { 0: 32, 1: 38 }],
];

for (const [sheetName, fileName, maxRows, widths] of sheetSpecs) {
  const matrix = await loadCsvMatrix(fileName, maxRows);
  writeSheet(workbook, sheetName, matrix, { widths });
}

const summaryJson = JSON.parse(await fs.readFile(path.join(outputDir, "controls_group_panel_summary.json"), "utf8"));
const summaryMatrix = [
  ["metric", "value"],
  ...Object.entries(summaryJson).map(([k, v]) => [k, typeof v === "object" ? JSON.stringify(v) : v]),
];
writeSheet(workbook, "Processing_Summary", summaryMatrix, { widths: { 0: 42, 1: 70 } });

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
});
console.log(errors.ndjson);

const previewDir = path.join(outputDir, "logs", "workbook_previews");
await fs.mkdir(previewDir, { recursive: true });
for (const [sheetName] of [...sheetSpecs, ["Processing_Summary"]]) {
  const preview = await workbook.render({ sheetName, range: "A1:H30", scale: 1, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(workbookPath);
await fs.rm(`${workbookPath}.inspect.ndjson`, { force: true });
console.log(`Saved ${workbookPath}`);
