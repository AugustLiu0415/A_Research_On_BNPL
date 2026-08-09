import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, "..", "..");
const dataDir = path.join(repoRoot, "data");
const outputDir = __dirname;

const providerOrder = ["affirm", "klarna", "afterpay", "zip", "sezzle"];
const providerLabels = {
  affirm: "Affirm",
  klarna: "Klarna",
  afterpay: "Afterpay",
  zip: "Zip",
  sezzle: "Sezzle",
};
const checkMark = "✓";

const sourceListFiles = [
  "merchant_list_raw_data/BNPL_Merchant_List.csv",
  "merchant_list_raw_data/bnpl_merchants.csv",
  "BNPL_Merchant_List.csv",
  "bnpl_merchants.csv",
];
const sourceCategoryFiles = [
  "merchant_list_raw_data/BNPL_Merchant_Categories.csv",
  "merchant_list_raw_data/bnpl_merchants_long.csv",
  "BNPL_Merchant_Categories.csv",
  "bnpl_merchants_long.csv",
];

const categoryOrder = [
  "Accessories",
  "Apparel",
  "Auto",
  "Beauty",
  "Electronics",
  "Fitness & Gear",
  "Home & Furniture",
  "Luxury",
  "Shoes",
  "Travel & Events",
  "Health & Beauty",
  "Clothing & Accessories",
  "Toys & Hobbies",
  "Home & Appliances",
  "TV & Audio",
  "Sports & Outdoor",
  "Computers & Tablets",
  "Home Improvement",
  "Photography",
  "Gaming & Entertainment",
  "Phones & Smartwatches",
  "Kids & Family",
  "Automotive",
  "Garden & Patio",
  "Kitchen Appliances",
  "Home Appliances",
  "Books, Movies & Music",
  "Fashion",
  "Men's fashion",
  "Kids & Baby",
  "Home & Garden",
  "Electronics & Devices",
  "Travel & Entertainment",
  "Bills",
  "Electronics & Appliances",
  "Fitness",
  "Jewelry & Accessories",
  "Pets",
  "TVs",
  "Education",
  "Food & Beverage",
  "Flights",
  "Hotels",
  "Kids & Babies",
  "Phones",
  "Sports & Outdoors",
  "Activewear",
  "Clothing",
  "Jewelry",
  "Swimwear",
  "Baby Gear",
  "Cosmetics",
  "Hair",
  "Self Care",
  "Vitamins & Supplements",
  "Outdoor",
  "Sporting Goods",
  "Sportsman's",
  "Bed & Bath",
  "Furniture & Decor",
  "Outdoor & Seasonal",
  "Toys & Games",
];

const categoryTabs = [
  {
    name: "Fashion & Accessories",
    categories: {
      affirm: ["Accessories", "Apparel", "Shoes"],
      klarna: ["Clothing & Accessories"],
      afterpay: ["Fashion", "Men's fashion"],
      zip: ["Jewelry & Accessories", "Shoes"],
      sezzle: ["Activewear", "Clothing", "Jewelry", "Shoes", "Swimwear"],
    },
  },
  {
    name: "Health & Beauty",
    categories: {
      affirm: ["Beauty"],
      klarna: ["Health & Beauty"],
      afterpay: ["Health & Beauty"],
      zip: [],
      sezzle: ["Cosmetics", "Hair", "Self Care", "Vitamins & Supplements"],
    },
  },
  {
    name: "Electronics & Devices",
    categories: {
      affirm: ["Electronics"],
      klarna: [
        "TV & Audio",
        "Computers & Tablets",
        "Photography",
        "Gaming & Entertainment",
        "Phones & Smartwatches",
      ],
      afterpay: ["Electronics & Devices"],
      zip: ["Electronics & Appliances", "TVs", "Phones"],
      sezzle: [],
    },
  },
  {
    name: "Home & Furniture",
    categories: {
      affirm: ["Home & Furniture"],
      klarna: [
        "Home & Appliances",
        "Home Improvement",
        "Garden & Patio",
        "Kitchen Appliances",
        "Home Appliances",
      ],
      afterpay: ["Home & Garden"],
      zip: ["Home & Furniture"],
      sezzle: ["Bed & Bath", "Furniture & Decor", "Outdoor & Seasonal"],
    },
  },
  {
    name: "Sports & Fitness",
    categories: {
      affirm: ["Fitness & Gear"],
      klarna: ["Sports & Outdoor"],
      afterpay: [],
      zip: ["Fitness", "Sports & Outdoors"],
      sezzle: ["Fitness", "Outdoor", "Sporting Goods", "Sportsman's"],
    },
  },
  {
    name: "Travel & Entertainment",
    categories: {
      affirm: ["Travel & Events"],
      klarna: ["Gaming & Entertainment", "Books, Movies & Music"],
      afterpay: ["Travel & Entertainment"],
      zip: ["Travel & Entertainment", "Flights", "Hotels"],
      sezzle: [],
    },
  },
  {
    name: "Kids Baby & Toys",
    categories: {
      affirm: [],
      klarna: ["Toys & Hobbies", "Kids & Family"],
      afterpay: ["Kids & Baby"],
      zip: ["Kids & Babies"],
      sezzle: ["Baby Gear", "Toys & Games"],
    },
  },
  {
    name: "Automotive",
    categories: {
      affirm: ["Auto"],
      klarna: ["Automotive"],
      afterpay: [],
      zip: [],
      sezzle: [],
    },
  },
  {
    name: "Luxury",
    categories: {
      affirm: ["Luxury"],
      klarna: [],
      afterpay: [],
      zip: [],
      sezzle: [],
    },
  },
  {
    name: "Pets",
    categories: {
      affirm: [],
      klarna: [],
      afterpay: [],
      zip: ["Pets"],
      sezzle: ["Pets"],
    },
  },
  {
    name: "Bills",
    categories: {
      affirm: [],
      klarna: [],
      afterpay: [],
      zip: ["Bills"],
      sezzle: [],
    },
  },
  {
    name: "Education",
    categories: {
      affirm: [],
      klarna: [],
      afterpay: [],
      zip: ["Education"],
      sezzle: [],
    },
  },
  {
    name: "Food & Beverage",
    categories: {
      affirm: [],
      klarna: [],
      afterpay: [],
      zip: ["Food & Beverage"],
      sezzle: [],
    },
  },
];

function log(message) {
  console.log(`[process] ${message}`);
}

async function firstExisting(names) {
  for (const name of names) {
    const fullPath = path.join(dataDir, name);
    try {
      await fs.access(fullPath);
      return fullPath;
    } catch {
      // Try the next compatible filename.
    }
  }
  throw new Error(`None of these input files exist in ${dataDir}: ${names.join(", ")}`);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch !== "\r") {
      field += ch;
    }
  }

  if (field.length || row.length) {
    row.push(field);
    rows.push(row);
  }

  if (!rows.length) return [];
  const headers = rows[0].map((h) => h.trim());
  return rows.slice(1).filter((r) => r.some((v) => v !== "")).map((r) => {
    const out = {};
    headers.forEach((h, idx) => {
      out[h] = r[idx] ?? "";
    });
    return out;
  });
}

async function readCsv(filePath) {
  const text = await fs.readFile(filePath, "utf8");
  return parseCsv(text);
}

function normalizeCategory(category) {
  return String(category ?? "")
    .replace(/[’‘]/g, "'")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

function normalizeMerchantName(name) {
  let normalized = String(name ?? "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[’‘]/g, "'")
    .replace(/[“”]/g, '"')
    .replace(/[®™©]/g, "")
    .replace(/&/g, " and ")
    .replace(/\+/g, " plus ")
    .replace(/\([^)]*\)/g, " ")
    .toLowerCase();

  normalized = normalized.replace(/^the\s+/, " ");
  normalized = normalized.replace(
    /\b(inc|llc|ltd|co|company|corp|corporation|incorporated|official|store|shop|online)\b\.?/g,
    " ",
  );
  normalized = normalized.replace(/[^a-z0-9]+/g, "");
  return normalized || String(name ?? "").trim().toLowerCase();
}

function cleanMerchantName(name) {
  return String(name ?? "").replace(/\s+/g, " ").trim();
}

function splitCategories(value) {
  return String(value ?? "")
    .split(";")
    .map((part) => part.replace(/[’‘]/g, "'").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function categorySorter(a, b) {
  const ranks = new Map(categoryOrder.map((cat, idx) => [normalizeCategory(cat), idx]));
  const rankA = ranks.has(normalizeCategory(a)) ? ranks.get(normalizeCategory(a)) : 9999;
  const rankB = ranks.has(normalizeCategory(b)) ? ranks.get(normalizeCategory(b)) : 9999;
  if (rankA !== rankB) return rankA - rankB;
  return a.localeCompare(b);
}

function bestDisplayName(names) {
  const counts = new Map();
  for (const name of names) {
    counts.set(name, (counts.get(name) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort((a, b) => {
      if (b[1] !== a[1]) return b[1] - a[1];
      if (a[0].length !== b[0].length) return a[0].length - b[0].length;
      return a[0].localeCompare(b[0]);
    })[0][0];
}

function getOrCreateMerchantGroup(groups, merchantName) {
  const cleanedName = cleanMerchantName(merchantName);
  const key = normalizeMerchantName(cleanedName);
  if (!groups.has(key)) {
    groups.set(key, {
      key,
      names: [],
      categories: new Set(),
      providers: new Map(),
    });
  }
  const group = groups.get(key);
  group.names.push(cleanedName);
  return group;
}

function addProviderHit(group, provider, categories = []) {
  if (!group.providers.has(provider)) {
    group.providers.set(provider, new Set());
  }
  for (const category of categories) {
    group.categories.add(category);
    group.providers.get(provider).add(category);
  }
}

function buildMerchantGroups(listRows) {
  const groups = new Map();
  for (const row of listRows) {
    const provider = String(row.bnpl_provider ?? "").trim().toLowerCase();
    if (!providerOrder.includes(provider)) continue;

    const merchantName = cleanMerchantName(row.merchant_name);
    if (!merchantName) continue;

    const group = getOrCreateMerchantGroup(groups, merchantName);
    addProviderHit(group, provider, splitCategories(row.categories));
  }
  return groups;
}

function toOverlapRows(groups) {
  return [...groups.values()]
    .filter((group) => group.providers.size >= 2)
    .map((group) => {
      const categories = [...group.categories].sort(categorySorter).join("; ");
      return [
        bestDisplayName(group.names),
        categories,
        group.providers.size,
        ...providerOrder.map((provider) => (group.providers.has(provider) ? checkMark : "")),
      ];
    })
    .sort((a, b) => {
      if (b[2] !== a[2]) return b[2] - a[2];
      return String(a[0]).localeCompare(String(b[0]));
    });
}

function buildCategoryLookup() {
  const lookup = new Map();
  for (const tab of categoryTabs) {
    for (const provider of providerOrder) {
      for (const category of tab.categories[provider] ?? []) {
        const key = `${provider}|${normalizeCategory(category)}`;
        if (!lookup.has(key)) lookup.set(key, []);
        lookup.get(key).push(tab.name);
      }
    }
  }
  return lookup;
}

function buildCategoryGroups(categoryRows) {
  const lookup = buildCategoryLookup();
  const groupsByTab = new Map(categoryTabs.map((tab) => [tab.name, new Map()]));
  const unmapped = new Set();

  for (const row of categoryRows) {
    const provider = String(row.bnpl_provider ?? "").trim().toLowerCase();
    if (!providerOrder.includes(provider)) continue;

    const merchantName = cleanMerchantName(row.merchant_name);
    if (!merchantName) continue;

    const sourceCategory = String(row.category ?? "").replace(/[’‘]/g, "'").trim();
    const tabNames = lookup.get(`${provider}|${normalizeCategory(sourceCategory)}`) ?? [];
    if (!tabNames.length) {
      unmapped.add(`${provider}: ${sourceCategory}`);
      continue;
    }

    for (const tabName of tabNames) {
      const tabGroups = groupsByTab.get(tabName);
      const group = getOrCreateMerchantGroup(tabGroups, merchantName);
      addProviderHit(group, provider, [sourceCategory]);
    }
  }

  const rowsByTab = new Map();
  for (const tab of categoryTabs) {
    const tabGroups = groupsByTab.get(tab.name);
    const rows = [...tabGroups.values()]
      .map((group) => [
        bestDisplayName(group.names),
        group.providers.size,
        ...providerOrder.map((provider) => (group.providers.has(provider) ? checkMark : "")),
      ])
      .sort((a, b) => {
        if (b[1] !== a[1]) return b[1] - a[1];
        return String(a[0]).localeCompare(String(b[0]));
      });
    if (rows.length) rowsByTab.set(tab.name, rows);
  }

  return { rowsByTab, unmapped: [...unmapped].sort() };
}

function safeTableName(prefix, sheetName) {
  return `${prefix}_${sheetName}`.replace(/[^A-Za-z0-9_]/g, "_").slice(0, 250);
}

function applySheetFormatting(sheet, rangeAddress, checkColumns) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);

  const usedRange = sheet.getRange(rangeAddress);
  usedRange.format = {
    font: { name: "Arial", size: 11, color: "#111827" },
    borders: {
      insideHorizontal: { style: "thin", color: "#E5E7EB" },
      insideVertical: { style: "thin", color: "#E5E7EB" },
      bottom: { style: "thin", color: "#D1D5DB" },
    },
  };

  const header = sheet.getRange(rangeAddress.replace(/\d+$/, "1"));
  header.format = {
    fill: "#111827",
    font: { bold: true, color: "#FFFFFF", size: 12 },
    horizontalAlignment: "Center",
    verticalAlignment: "Center",
  };
  header.format.rowHeight = 28;

  for (const col of checkColumns) {
    sheet.getRange(`${col}:${col}`).format = {
      horizontalAlignment: "Center",
      verticalAlignment: "Center",
    };
  }
}

function setOverlapColumnWidths(sheet) {
  sheet.getRange("A:A").format.columnWidth = 32;
  sheet.getRange("B:B").format.columnWidth = 90;
  sheet.getRange("C:C").format.columnWidth = 22;
  sheet.getRange("D:H").format.columnWidth = 13;
}

function setCategoryColumnWidths(sheet) {
  sheet.getRange("A:A").format.columnWidth = 34;
  sheet.getRange("B:B").format.columnWidth = 22;
  sheet.getRange("C:G").format.columnWidth = 13;
}

function createOverlapWorkbook(overlapRows) {
  const workbook = Workbook.create();
  const sheet = workbook.worksheets.add("Overlap Merchant List");
  const headers = [
    "Merchant Name",
    "Categories",
    "Number of Platforms",
    "Affirm",
    "Klarna",
    "Afterpay",
    "Zip",
    "Sezzle",
  ];
  const values = [headers, ...overlapRows];
  const rowCount = values.length;
  sheet.getRangeByIndexes(0, 0, rowCount, headers.length).values = values;
  const rangeAddress = `A1:H${rowCount}`;
  sheet.tables.add(rangeAddress, true, "OverlapMerchantTable");
  applySheetFormatting(sheet, rangeAddress, ["D", "E", "F", "G", "H"]);
  setOverlapColumnWidths(sheet);
  sheet.getRange(`B2:B${rowCount}`).format = { wrapText: true };
  sheet.getRange(`C2:H${rowCount}`).format = {
    horizontalAlignment: "Center",
    verticalAlignment: "Center",
  };
  sheet.getRange(rangeAddress).format.autofitRows();
  return workbook;
}

function createCategoryWorkbook(rowsByTab) {
  const workbook = Workbook.create();
  const headers = [
    "Merchant Name",
    "Number of Platforms",
    "Affirm",
    "Klarna",
    "Afterpay",
    "Zip",
    "Sezzle",
  ];

  for (const [tabName, rows] of rowsByTab.entries()) {
    const sheet = workbook.worksheets.add(tabName);
    const values = [headers, ...rows];
    const rowCount = values.length;
    sheet.getRangeByIndexes(0, 0, rowCount, headers.length).values = values;
    const rangeAddress = `A1:G${rowCount}`;
    sheet.tables.add(rangeAddress, true, safeTableName("Category", tabName));
    applySheetFormatting(sheet, rangeAddress, ["C", "D", "E", "F", "G"]);
    setCategoryColumnWidths(sheet);
    sheet.getRange(`B2:G${rowCount}`).format = {
      horizontalAlignment: "Center",
      verticalAlignment: "Center",
    };
  }

  return workbook;
}

async function verifyWorkbook(workbook, sheetNames, rangeEndColumn) {
  const errors = await workbook.inspect({
    kind: "match",
    searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
    options: { useRegex: true, maxResults: 300 },
    summary: "formula error scan",
  });
  log(`Formula error scan: ${errors.ndjson.includes('"match"') ? "review needed" : "no visible errors"}`);

  for (const sheetName of sheetNames) {
    const preview = await workbook.render({
      sheetName,
      range: `A1:${rangeEndColumn}20`,
      scale: 1,
      format: "png",
    });
    const bytes = new Uint8Array(await preview.arrayBuffer());
    if (!bytes.length) throw new Error(`Rendered preview is empty for sheet ${sheetName}`);
  }
  log(`Rendered preview check completed for ${sheetNames.length} sheet(s).`);
}

async function main() {
  log("Starting BNPL overlap/category processing.");
  await fs.mkdir(outputDir, { recursive: true });

  const listFile = await firstExisting(sourceListFiles);
  const categoryFile = await firstExisting(sourceCategoryFiles);
  log(`Using merchant list input: ${path.relative(repoRoot, listFile)}`);
  log(`Using category input: ${path.relative(repoRoot, categoryFile)}`);

  const listRows = await readCsv(listFile);
  const categoryRows = await readCsv(categoryFile);
  log(`Loaded ${listRows.length.toLocaleString()} merchant-provider rows.`);
  log(`Loaded ${categoryRows.length.toLocaleString()} merchant-category rows.`);

  const merchantGroups = buildMerchantGroups(listRows);
  const overlapRows = toOverlapRows(merchantGroups);
  log(`Identified ${overlapRows.length.toLocaleString()} merchants appearing on 2+ platforms.`);

  const { rowsByTab, unmapped } = buildCategoryGroups(categoryRows);
  log(`Built ${rowsByTab.size} category tab(s).`);
  for (const [tabName, rows] of rowsByTab.entries()) {
    log(`Category tab "${tabName}": ${rows.length.toLocaleString()} unique merchants.`);
  }
  if (unmapped.length) {
    log(`Unmapped provider/category values skipped: ${unmapped.join("; ")}`);
  } else {
    log("All provider/category values were mapped into category tabs.");
  }

  const overlapWorkbook = createOverlapWorkbook(overlapRows);
  const categoryWorkbook = createCategoryWorkbook(rowsByTab);

  await verifyWorkbook(overlapWorkbook, ["Overlap Merchant List"], "H");
  await verifyWorkbook(categoryWorkbook, [...rowsByTab.keys()], "G");

  const overlapPath = path.join(outputDir, "BNPL_Merchant_Overlap_List.xlsx");
  const categoryPath = path.join(outputDir, "BNPL_Merchant_with_Category_List.xlsx");

  const overlapOutput = await SpreadsheetFile.exportXlsx(overlapWorkbook);
  await overlapOutput.save(overlapPath);

  const categoryOutput = await SpreadsheetFile.exportXlsx(categoryWorkbook);
  await categoryOutput.save(categoryPath);

  log(`Saved ${path.relative(repoRoot, overlapPath)}.`);
  log(`Saved ${path.relative(repoRoot, categoryPath)}.`);
  log("Done.");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
