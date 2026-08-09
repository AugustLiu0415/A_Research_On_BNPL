"""Centralized SEC XBRL concept mapping for the public-company panel.

The order of tags is intentional: earlier concepts are preferred when multiple
standardized concepts are available for the same company-period.
"""

FLOW_VARIABLES = {
    "revenue",
    "gross_profit",
    "cogs",
    "operating_income",
    "net_income",
    "sga_expense",
    "capital_expenditures",
}

PER_SHARE_DIRECT_ONLY_VARIABLES = {"diluted_eps", "weighted_average_diluted_shares"}

STOCK_VARIABLES = {
    "total_assets",
    "total_liabilities",
    "stockholders_equity",
    "cash_and_cash_equivalents",
    "inventory",
    "accounts_receivable",
    "current_assets",
    "current_liabilities",
    "total_debt",
    "debt_current_component",
    "debt_noncurrent_component",
}

CONCEPT_MAP = {
    "revenue": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax"),
            ("us-gaap", "SalesRevenueNet"),
            ("us-gaap", "Revenues"),
            ("us-gaap", "SalesRevenueGoodsNet"),
            ("ifrs-full", "Revenue"),
        ],
    },
    "gross_profit": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "GrossProfit"),
            ("ifrs-full", "GrossProfit"),
        ],
    },
    "cogs": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "CostOfRevenue"),
            ("us-gaap", "CostOfGoodsAndServicesSold"),
            ("us-gaap", "CostOfGoodsSold"),
            ("ifrs-full", "CostOfSales"),
        ],
    },
    "operating_income": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "OperatingIncomeLoss"),
            ("ifrs-full", "ProfitLossFromOperatingActivities"),
        ],
    },
    "net_income": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "NetIncomeLoss"),
            ("ifrs-full", "ProfitLoss"),
        ],
    },
    "total_assets": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "Assets"),
            ("ifrs-full", "Assets"),
        ],
    },
    "total_liabilities": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "Liabilities"),
            ("ifrs-full", "Liabilities"),
        ],
    },
    "stockholders_equity": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "StockholdersEquity"),
            ("us-gaap", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"),
            ("ifrs-full", "Equity"),
        ],
    },
    "cash_and_cash_equivalents": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "CashAndCashEquivalentsAtCarryingValue"),
            ("ifrs-full", "CashAndCashEquivalents"),
        ],
    },
    "total_debt": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "LongTermDebtAndFinanceLeaseObligations"),
            ("us-gaap", "LongTermDebt"),
            ("ifrs-full", "Borrowings"),
        ],
    },
    "debt_current_component": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "LongTermDebtAndFinanceLeaseObligationsCurrent"),
            ("us-gaap", "LongTermDebtCurrent"),
            ("us-gaap", "ShortTermBorrowings"),
            ("ifrs-full", "CurrentBorrowings"),
        ],
    },
    "debt_noncurrent_component": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "LongTermDebtAndFinanceLeaseObligationsNoncurrent"),
            ("us-gaap", "LongTermDebtNoncurrent"),
            ("ifrs-full", "NoncurrentBorrowings"),
        ],
    },
    "sga_expense": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "SellingGeneralAndAdministrativeExpense"),
        ],
    },
    "inventory": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "InventoryNet"),
            ("ifrs-full", "Inventories"),
        ],
    },
    "accounts_receivable": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "AccountsReceivableNetCurrent"),
            ("ifrs-full", "TradeAndOtherCurrentReceivables"),
        ],
    },
    "current_assets": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "AssetsCurrent"),
            ("ifrs-full", "CurrentAssets"),
        ],
    },
    "current_liabilities": {
        "type": "stock",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "LiabilitiesCurrent"),
            ("ifrs-full", "CurrentLiabilities"),
        ],
    },
    "diluted_eps": {
        "type": "flow_direct_only",
        "preferred_units": ["USD/shares", "USD/shares", "EUR/shares", "GBP/shares", "CAD/shares"],
        "concepts": [
            ("us-gaap", "EarningsPerShareDiluted"),
            ("ifrs-full", "DilutedEarningsLossPerShare"),
        ],
    },
    "weighted_average_diluted_shares": {
        "type": "flow_direct_only",
        "preferred_units": ["shares"],
        "concepts": [
            ("us-gaap", "WeightedAverageNumberOfDilutedSharesOutstanding"),
            ("ifrs-full", "WeightedAverageNumberOfDilutedSharesOutstanding"),
        ],
    },
    "capital_expenditures": {
        "type": "flow",
        "preferred_units": ["USD", "EUR", "GBP", "JPY", "CAD", "HKD"],
        "concepts": [
            ("us-gaap", "PaymentsToAcquirePropertyPlantAndEquipment"),
            ("ifrs-full", "PurchaseOfPropertyPlantAndEquipmentClassifiedAsInvestingActivities"),
        ],
    },
}

PANEL_FINANCIAL_VARIABLES = [
    "revenue",
    "gross_profit",
    "cogs",
    "operating_income",
    "net_income",
    "total_assets",
    "total_liabilities",
    "stockholders_equity",
    "cash_and_cash_equivalents",
    "total_debt",
    "sga_expense",
    "inventory",
    "accounts_receivable",
    "current_assets",
    "current_liabilities",
    "diluted_eps",
    "weighted_average_diluted_shares",
    "capital_expenditures",
]

CORE_VARIABLES = ["revenue", "gross_profit", "operating_income", "net_income"]

FLOW_DERIVABLE_VARIABLES = [
    "revenue",
    "gross_profit",
    "cogs",
    "operating_income",
    "net_income",
    "sga_expense",
    "capital_expenditures",
]

ALLOWED_FORMS = {
    "10-Q",
    "10-Q/A",
    "10-K",
    "10-K/A",
    "20-F",
    "20-F/A",
    "40-F",
    "40-F/A",
    "6-K",
}

DOMESTIC_FORMS = {"10-Q", "10-Q/A", "10-K", "10-K/A"}
FOREIGN_FORMS = {"20-F", "20-F/A", "40-F", "40-F/A", "6-K"}


VARIABLE_DEFINITIONS = [
    {
        "variable": "revenue",
        "definition": "Consolidated quarterly top-line revenue.",
        "source": "SEC CompanyFacts standardized XBRL facts.",
        "preferred_xbrl_concepts": "RevenueFromContractWithCustomerExcludingAssessedTax; SalesRevenueNet; Revenues; SalesRevenueGoodsNet; ifrs-full Revenue",
        "unit": "Reporting currency, preferably USD where available.",
        "reported_or_derived": "Reported quarter preferred; Q2/Q3 may be derived from YTD; Q4 may be derived from fiscal-year annual value.",
        "calculation_formula": "Reported value, or YTD current period minus prior YTD; Q4 = FY - Q1 - Q2 - Q3 when valid.",
    },
    {
        "variable": "gross_profit",
        "definition": "Quarterly gross profit.",
        "source": "SEC CompanyFacts, or revenue minus COGS when GrossProfit is unavailable.",
        "preferred_xbrl_concepts": "GrossProfit; ifrs-full GrossProfit",
        "unit": "Same reporting currency as revenue.",
        "reported_or_derived": "Reported quarter preferred; may be derived from revenue - cogs or YTD/FY arithmetic.",
        "calculation_formula": "GrossProfit, or revenue - cogs when both are available in the same currency.",
    },
    {
        "variable": "operating_income",
        "definition": "Quarterly operating income or loss.",
        "source": "SEC CompanyFacts standardized XBRL facts.",
        "preferred_xbrl_concepts": "OperatingIncomeLoss; ifrs-full ProfitLossFromOperatingActivities",
        "unit": "Reporting currency.",
        "reported_or_derived": "Reported quarter preferred; Q2/Q3 or Q4 derivation when period-consistent.",
        "calculation_formula": "Reported value, or YTD/annual arithmetic when valid.",
    },
    {
        "variable": "net_income",
        "definition": "Quarterly net income or loss.",
        "source": "SEC CompanyFacts standardized XBRL facts.",
        "preferred_xbrl_concepts": "NetIncomeLoss; ifrs-full ProfitLoss",
        "unit": "Reporting currency.",
        "reported_or_derived": "Reported quarter preferred; Q2/Q3 or Q4 derivation when period-consistent.",
        "calculation_formula": "Reported value, or YTD/annual arithmetic when valid.",
    },
    {
        "variable": "gross_margin",
        "definition": "Gross profit divided by revenue.",
        "source": "Derived from selected panel values.",
        "preferred_xbrl_concepts": "N/A",
        "unit": "Ratio.",
        "reported_or_derived": "Derived.",
        "calculation_formula": "gross_profit / revenue when both are available and same currency.",
    },
    {
        "variable": "operating_margin",
        "definition": "Operating income divided by revenue.",
        "source": "Derived from selected panel values.",
        "preferred_xbrl_concepts": "N/A",
        "unit": "Ratio.",
        "reported_or_derived": "Derived.",
        "calculation_formula": "operating_income / revenue when both are available and same currency.",
    },
    {
        "variable": "net_margin",
        "definition": "Net income divided by revenue.",
        "source": "Derived from selected panel values.",
        "preferred_xbrl_concepts": "N/A",
        "unit": "Ratio.",
        "reported_or_derived": "Derived.",
        "calculation_formula": "net_income / revenue when both are available and same currency.",
    },
    {
        "variable": "revenue_growth_yoy",
        "definition": "Same-fiscal-quarter year-over-year revenue growth.",
        "source": "Derived from panel revenue.",
        "preferred_xbrl_concepts": "N/A",
        "unit": "Ratio.",
        "reported_or_derived": "Derived.",
        "calculation_formula": "revenue_t / revenue_same_fiscal_quarter_previous_year - 1.",
    },
    {
        "variable": "revenue_growth_qoq",
        "definition": "Sequential fiscal-quarter revenue growth.",
        "source": "Derived from panel revenue.",
        "preferred_xbrl_concepts": "N/A",
        "unit": "Ratio.",
        "reported_or_derived": "Derived.",
        "calculation_formula": "revenue_t / revenue_previous_fiscal_quarter - 1.",
    },
]


def concept_priority(variable, taxonomy, tag):
    mapping = CONCEPT_MAP[variable]["concepts"]
    try:
        return mapping.index((taxonomy, tag))
    except ValueError:
        return 999


def preferred_unit_priority(variable, unit):
    preferred = CONCEPT_MAP[variable].get("preferred_units", [])
    try:
        return preferred.index(unit)
    except ValueError:
        return len(preferred) + 10
