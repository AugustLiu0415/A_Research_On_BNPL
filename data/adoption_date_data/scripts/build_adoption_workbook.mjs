import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..", "..");
const outDir = path.join(repoRoot, "data", "adoption_date_data");
const outputPath = path.join(outDir, "BNPL_Merchant_Adoption_Date.xlsx");

const paths = {
  master: path.join(outDir, "adoption_master_rows.json"),
  first: path.join(outDir, "merchant_first_bnpl_rows.json"),
  evidence: path.join(outDir, "evidence_log_rows.json"),
  manual: path.join(outDir, "manual_review_rows.json"),
  summary: path.join(outDir, "adoption_date_summary.json"),
};

const sheetDefs = [
  {
    name: "Adoption_Master",
    tableName: "AdoptionMasterTable",
    source: "master",
    headers: [
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
    ],
  },
  {
    name: "Merchant_First_BNPL",
    tableName: "MerchantFirstBNPLTable",
    source: "first",
    headers: [
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
    ],
  },
  {
    name: "Evidence_Log",
    tableName: "EvidenceLogTable",
    source: "evidence",
    headers: [
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
    ],
  },
  {
    name: "Manual_Review",
    tableName: "ManualReviewTable",
    source: "manual",
    headers: ["merchant", "provider", "problem_type", "reason", "recommended_manual_action"],
  },
];

function log(message) {
  console.log(`[workbook] ${message}`);
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

function valueFor(row, header) {
  const value = row[header];
  return value === undefined || value === null ? "" : value;
}

function columnWidth(header) {
  if (header.includes("merchant_name") || header === "merchant") return 28;
  if (header.includes("parent_company")) return 32;
  if (header.includes("source_url") || header.includes("wayback_url") || header.includes("url")) return 48;
  if (header.includes("evidence") || header.includes("notes") || header.includes("summary") || header.includes("interpretation") || header.includes("action") || header === "reason") return 56;
  if (header.includes("date") || header.includes("period")) return 18;
  if (header.includes("precision") || header.includes("confidence") || header.includes("eligible") || header.includes("sample") || header.includes("flag")) return 18;
  if (header === "provider" || header === "ticker" || header === "CIK" || header === "exchange") return 14;
  return 20;
}

function applyFormatting(sheet, rowCount, headers) {
  const colCount = headers.length;
  const endCol = colLetter(colCount - 1);
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  sheet.freezePanes.freezeColumns(2);
  const range = sheet.getRange(`A1:${endCol}${Math.max(rowCount, 1)}`);
  range.format = {
    font: { name: "Arial", size: 10, color: "#111827" },
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
      insideVertical: { style: "thin", color: "#E5E7EB" },
      bottom: { style: "thin", color: "#D1D5DB" },
    },
  };
  sheet.getRange(`A1:${endCol}1`).format = {
    fill: "#111827",
    font: { bold: true, color: "#FFFFFF", size: 10 },
    horizontalAlignment: "Center",
    verticalAlignment: "Center",
    wrapText: true,
  };
  sheet.getRange(`A1:${endCol}1`).format.rowHeight = 42;

  headers.forEach((header, index) => {
    const col = colLetter(index);
    sheet.getRange(`${col}:${col}`).format.columnWidth = columnWidth(header);
    if (
      header.includes("url") ||
      header.includes("evidence") ||
      header.includes("notes") ||
      header.includes("summary") ||
      header.includes("interpretation") ||
      header.includes("action") ||
      header === "reason"
    ) {
      sheet.getRange(`${col}:${col}`).format = { wrapText: true, verticalAlignment: "Top" };
    }
    if (header === "number_of_current_platforms" || header === "CIK") {
      sheet.getRange(`${col}:${col}`).format = { horizontalAlignment: "Center", numberFormat: "#,##0" };
    }
  });
}

function addDataSheet(workbook, def, rows) {
  const sheet = workbook.worksheets.add(def.name);
  const matrix = [def.headers, ...rows.map((row) => def.headers.map((header) => valueFor(row, header)))];
  const rowCount = matrix.length;
  const colCount = def.headers.length;
  sheet.getRangeByIndexes(0, 0, rowCount, colCount).values = matrix;
  const endCol = colLetter(colCount - 1);
  sheet.tables.add(`A1:${endCol}${rowCount}`, true, def.tableName);
  applyFormatting(sheet, rowCount, def.headers);
  log(`${def.name}: ${(rowCount - 1).toLocaleString()} row(s).`);
}

function addSummarySheet(workbook, summary) {
  const sheet = workbook.worksheets.add("Summary");
  const rows = [
    ["Metric", "Value"],
    ["Retrieved at", String(summary.retrieved_at ?? "").replace("T", " ").replace("+00:00", " UTC")],
    ["Total public merchants", summary.total_public_merchants],
    ["Merchant-provider rows", summary.merchant_provider_rows],
    ["Evidence log rows", summary.evidence_log_rows],
    ["Manual review rows", summary.manual_review_rows],
    ["Multi-platform merchants", summary.multi_platform_merchants],
    ["Main regression eligible merchants", summary.main_regression_eligible_merchants],
    ["Earlier external BNPL rows", summary.earlier_external_bnpl_rows],
    ["", ""],
    ["Provider distribution", ""],
    ...Object.entries(summary.provider_distribution ?? {}).map(([k, v]) => [k, v]),
    ["", ""],
    ["Provider-level confidence", ""],
    ...Object.entries(summary.confidence_distribution_provider_level ?? {}).map(([k, v]) => [k, v]),
    ["", ""],
    ["Provider-level date precision", ""],
    ...Object.entries(summary.date_precision_distribution_provider_level ?? {}).map(([k, v]) => [k, v]),
    ["", ""],
    ["Merchant first BNPL confidence", ""],
    ...Object.entries(summary.merchant_first_confidence_distribution ?? {}).map(([k, v]) => [k, v]),
  ];
  sheet.getRangeByIndexes(0, 0, rows.length, 2).values = rows;
  sheet.tables.add(`A1:B${rows.length}`, true, "SummaryTable");
  applyFormatting(sheet, rows.length, ["Metric", "Value"]);
  sheet.getRange("A:A").format.columnWidth = 36;
  sheet.getRange("B:B").format.columnWidth = 28;
  log("Summary: 1 sheet.");
}

async function verifyWorkbook(workbook) {
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "final formula error scan",
  });
  log(`Formula error scan: ${errors.ndjson.includes('"match"') ? "review needed" : "no visible errors"}.`);
  for (const sheetName of ["Adoption_Master", "Merchant_First_BNPL", "Evidence_Log", "Manual_Review", "Summary"]) {
    const preview = await workbook.render({ sheetName, range: "A1:J20", scale: 1, format: "png" });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    if (!bytes.length) throw new Error(`Rendered preview is empty for ${sheetName}`);
  }
  log("Rendered preview check completed for all sheets.");
}

async function main() {
  const data = {
    master: JSON.parse(await fs.readFile(paths.master, "utf8")),
    first: JSON.parse(await fs.readFile(paths.first, "utf8")),
    evidence: JSON.parse(await fs.readFile(paths.evidence, "utf8")),
    manual: JSON.parse(await fs.readFile(paths.manual, "utf8")),
    summary: JSON.parse(await fs.readFile(paths.summary, "utf8")),
  };
  const workbook = Workbook.create();
  for (const def of sheetDefs) {
    addDataSheet(workbook, def, data[def.source]);
  }
  addSummarySheet(workbook, data.summary);
  await verifyWorkbook(workbook);
  const output = await SpreadsheetFile.exportXlsx(workbook);
  await output.save(outputPath);
  log(`Saved ${path.relative(repoRoot, outputPath)}.`);
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
