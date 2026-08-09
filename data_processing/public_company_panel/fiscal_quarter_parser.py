"""Utilities for fiscal-period handling in SEC CompanyFacts data."""

from __future__ import annotations

from datetime import date, datetime, timedelta


QUARTER_ORDER = {"Q1": 1, "Q2": 2, "Q3": 3, "Q4": 4}
ORDER_QUARTER = {v: k for k, v in QUARTER_ORDER.items()}


def parse_date(value):
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return None


def date_to_iso(value):
    d = parse_date(value)
    return d.isoformat() if d else ""


def days_between(start, end):
    s = parse_date(start)
    e = parse_date(end)
    if not s or not e:
        return None
    return (e - s).days


def next_day(value):
    d = parse_date(value)
    if not d:
        return ""
    return (d + timedelta(days=1)).isoformat()


def fiscal_sort_key(fiscal_year, fiscal_quarter):
    return int(fiscal_year) * 4 + QUARTER_ORDER.get(fiscal_quarter, 0)


def previous_fiscal_period(fiscal_year, fiscal_quarter):
    q = QUARTER_ORDER.get(fiscal_quarter)
    if not q:
        return None
    if q == 1:
        return int(fiscal_year) - 1, "Q4"
    return int(fiscal_year), ORDER_QUARTER[q - 1]


def calendar_quarter_from_date(end_date):
    d = parse_date(end_date)
    if not d:
        return "", ""
    return d.year, f"Q{((d.month - 1) // 3) + 1}"


def fact_duration_kind(fact):
    """Classify a duration fact as quarter, ytd, annual, or invalid.

    CompanyFacts exposes both quarter-only and cumulative YTD facts. This
    function deliberately uses a wide range to accommodate 52/53-week calendars
    without silently accepting 6-month or 9-month facts as quarters.
    """

    fp = str(fact.get("fp") or "").upper()
    duration = days_between(fact.get("start"), fact.get("end"))
    if duration is None:
        return "not_duration"
    if fp == "FY":
        if 300 <= duration <= 390:
            return "annual"
        return "annual_unusual"
    if fp in {"Q1", "Q2", "Q3", "Q4"}:
        if 45 <= duration <= 125:
            return "quarter"
        if fp == "Q2" and 126 <= duration <= 220:
            return "ytd"
        if fp == "Q3" and 221 <= duration <= 310:
            return "ytd"
        if fp == "Q4" and 300 <= duration <= 390:
            return "annual"
        return "duration_unusual"
    return "unresolved"


def is_unusual_quarter_duration(duration):
    if duration is None:
        return False
    return not (60 <= duration <= 115)
