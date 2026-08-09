"""Extract a clean fiscal-quarter financial panel from SEC CompanyFacts JSON."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from concept_mapping import (
    ALLOWED_FORMS,
    CONCEPT_MAP,
    CORE_VARIABLES,
    FLOW_DERIVABLE_VARIABLES,
    FOREIGN_FORMS,
    PANEL_FINANCIAL_VARIABLES,
    concept_priority,
    preferred_unit_priority,
)
from fiscal_quarter_parser import (
    QUARTER_ORDER,
    calendar_quarter_from_date,
    days_between,
    fact_duration_kind,
    fiscal_sort_key,
    is_unusual_quarter_duration,
    next_day,
    parse_date,
)


def load_companyfacts(path: Path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _clean_form(form):
    return str(form or "").upper()


def _as_number(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def iter_mapped_facts(companyfacts, variable):
    mapping = CONCEPT_MAP[variable]
    facts_root = companyfacts.get("facts", {})
    for taxonomy, tag in mapping["concepts"]:
        tag_meta = facts_root.get(taxonomy, {}).get(tag)
        if not tag_meta:
            continue
        label = tag_meta.get("label", "")
        description = tag_meta.get("description", "")
        for unit, facts in tag_meta.get("units", {}).items():
            for fact in facts:
                if _clean_form(fact.get("form")) not in ALLOWED_FORMS:
                    continue
                value = _as_number(fact.get("val"))
                if value is None:
                    continue
                record = {
                    "variable_name": variable,
                    "selected_value": value,
                    "unit": unit,
                    "taxonomy": taxonomy,
                    "selected_tag": tag,
                    "label": label,
                    "description": description,
                    "start": fact.get("start", ""),
                    "end": fact.get("end", ""),
                    "fy": fact.get("fy", ""),
                    "fp": str(fact.get("fp") or "").upper(),
                    "form": _clean_form(fact.get("form")),
                    "filed": fact.get("filed", ""),
                    "accn": fact.get("accn", ""),
                    "frame": fact.get("frame", ""),
                    "concept_priority": concept_priority(variable, taxonomy, tag),
                    "unit_priority": preferred_unit_priority(variable, unit),
                    "source_type": "direct_companyfacts",
                    "validation_notes": "",
                }
                record["duration_days"] = days_between(record["start"], record["end"])
                record["duration_kind"] = fact_duration_kind(record)
                record["amended_filing_flag"] = record["form"].endswith("/A")
                yield record


def _selection_sort_key(record):
    filed = record.get("filed") or "0000-00-00"
    accn = record.get("accn") or ""
    return (
        record.get("unit_priority", 99),
        record.get("concept_priority", 999),
        filed,
        accn,
    )


def select_latest(records):
    if not records:
        return None
    best_unit = min(r.get("unit_priority", 99) for r in records)
    unit_group = [r for r in records if r.get("unit_priority", 99) == best_unit]
    best_concept = min(r.get("concept_priority", 999) for r in unit_group)
    concept_group = [r for r in unit_group if r.get("concept_priority", 999) == best_concept]
    selected = deepcopy(sorted(concept_group, key=lambda r: (r.get("filed") or "0000-00-00", r.get("accn") or ""))[-1])
    selected["restatement_flag"] = len({r.get("accn") for r in records if r.get("accn")}) > 1
    selected["original_accession"] = sorted((r.get("accn") or "" for r in records))[0] if records else ""
    selected["selected_accession"] = selected.get("accn", "")
    return selected


def _same_concept_unit(*facts):
    filtered = [f for f in facts if f]
    if len(filtered) != len(facts):
        return False
    tags = {(f.get("taxonomy"), f.get("selected_tag"), f.get("unit")) for f in filtered}
    return len(tags) == 1


def _derived_fact(base, value, source_type, start, end, notes, components):
    derived = deepcopy(base)
    derived["selected_value"] = value
    derived["start"] = start or ""
    derived["end"] = end or ""
    derived["duration_days"] = days_between(start, end)
    derived["source_type"] = source_type
    derived["validation_notes"] = notes
    derived["component_accessions"] = "; ".join([c.get("accn", "") for c in components if c])
    derived["restatement_flag"] = any(bool(c.get("restatement_flag")) for c in components if c)
    derived["amended_filing_flag"] = any(bool(c.get("amended_filing_flag")) for c in components if c)
    return derived


def _extract_flow_variable(companyfacts, variable):
    facts = list(iter_mapped_facts(companyfacts, variable))
    quarter_candidates = {}
    ytd_candidates = {}
    annual_candidates = {}
    all_candidate_groups = {}

    for record in facts:
        fy = record.get("fy")
        fp = record.get("fp")
        if not fy:
            continue
        key_base = (int(fy), fp)
        all_candidate_groups.setdefault(key_base, []).append(record)
        kind = record.get("duration_kind")
        if fp in {"Q1", "Q2", "Q3", "Q4"} and kind == "quarter":
            quarter_candidates.setdefault((int(fy), fp), []).append(record)
        elif fp in {"Q2", "Q3"} and kind == "ytd":
            ytd_candidates.setdefault((int(fy), fp), []).append(record)
        elif kind == "annual":
            annual_candidates.setdefault(int(fy), []).append(record)

    selected = {}
    annual_selected = {fy: select_latest(group) for fy, group in annual_candidates.items()}

    for key, group in quarter_candidates.items():
        picked = select_latest(group)
        if picked:
            picked["source_type"] = "direct_companyfacts"
            selected[key] = picked

    for fy in sorted({k[0] for k in ytd_candidates}):
        q1 = selected.get((fy, "Q1"))
        q2_ytd = select_latest(ytd_candidates.get((fy, "Q2"), []))
        if (fy, "Q2") not in selected and q1 and q2_ytd and _same_concept_unit(q1, q2_ytd):
            selected[(fy, "Q2")] = _derived_fact(
                q2_ytd,
                q2_ytd["selected_value"] - q1["selected_value"],
                "derived_from_ytd",
                next_day(q1.get("end")),
                q2_ytd.get("end"),
                "Q2 derived as H1 YTD minus Q1.",
                [q2_ytd, q1],
            )

        q3_ytd = select_latest(ytd_candidates.get((fy, "Q3"), []))
        if (fy, "Q3") not in selected and q2_ytd and q3_ytd and _same_concept_unit(q2_ytd, q3_ytd):
            selected[(fy, "Q3")] = _derived_fact(
                q3_ytd,
                q3_ytd["selected_value"] - q2_ytd["selected_value"],
                "derived_from_ytd",
                next_day(q2_ytd.get("end")),
                q3_ytd.get("end"),
                "Q3 derived as nine-month YTD minus H1 YTD.",
                [q3_ytd, q2_ytd],
            )
        elif (fy, "Q3") not in selected and q3_ytd and all((fy, q) in selected for q in ["Q1", "Q2"]):
            q1 = selected[(fy, "Q1")]
            q2 = selected[(fy, "Q2")]
            if _same_concept_unit(q1, q2, q3_ytd):
                selected[(fy, "Q3")] = _derived_fact(
                    q3_ytd,
                    q3_ytd["selected_value"] - q1["selected_value"] - q2["selected_value"],
                    "derived_from_ytd",
                    next_day(q2.get("end")),
                    q3_ytd.get("end"),
                    "Q3 derived as nine-month YTD minus Q1 and Q2 because H1 YTD was unavailable.",
                    [q3_ytd, q1, q2],
                )

    for fy, annual in annual_selected.items():
        if (fy, "Q4") in selected or not annual:
            continue
        q1 = selected.get((fy, "Q1"))
        q2 = selected.get((fy, "Q2"))
        q3 = selected.get((fy, "Q3"))
        if q1 and q2 and q3 and _same_concept_unit(annual, q1, q2, q3):
            selected[(fy, "Q4")] = _derived_fact(
                annual,
                annual["selected_value"] - q1["selected_value"] - q2["selected_value"] - q3["selected_value"],
                "derived_q4_from_fy",
                next_day(q3.get("end")),
                annual.get("end"),
                "Q4 derived as fiscal-year annual value minus Q1, Q2, and Q3.",
                [annual, q1, q2, q3],
            )

    return selected, annual_selected, facts


def _extract_direct_only_flow_variable(companyfacts, variable):
    facts = list(iter_mapped_facts(companyfacts, variable))
    selected = {}
    for record in facts:
        fy = record.get("fy")
        fp = record.get("fp")
        if not fy or fp not in {"Q1", "Q2", "Q3", "Q4"}:
            continue
        if record.get("duration_kind") != "quarter":
            continue
        selected.setdefault((int(fy), fp), []).append(record)
    return {key: select_latest(group) for key, group in selected.items()}, {}, facts


def _extract_stock_variable(companyfacts, variable):
    facts = list(iter_mapped_facts(companyfacts, variable))
    selected_candidates = {}
    for record in facts:
        fy = record.get("fy")
        fp = record.get("fp")
        if not fy or record.get("start"):
            continue
        if fp == "FY":
            fp = "Q4"
        if fp not in {"Q1", "Q2", "Q3", "Q4"}:
            continue
        selected_candidates.setdefault((int(fy), fp), []).append(record)
    return {key: select_latest(group) for key, group in selected_candidates.items()}, {}, facts


def _merge_period_anchor(selected_by_variable, key):
    preferred = ["revenue", "gross_profit", "operating_income", "net_income", "cogs", "sga_expense"]
    for variable in preferred:
        fact = selected_by_variable.get(variable, {}).get(key)
        if fact:
            return fact
    for variable_facts in selected_by_variable.values():
        fact = variable_facts.get(key)
        if fact:
            return fact
    return {}


def _build_source_audit_row(companyfacts, crosswalk_row, key, variable, fact):
    fy, fq = key
    return {
        "CIK": crosswalk_row["CIK"],
        "company": companyfacts.get("entityName", ""),
        "ticker": crosswalk_row.get("ticker", ""),
        "fiscal_year": fy,
        "fiscal_quarter": fq,
        "variable_name": variable,
        "selected_value": fact.get("selected_value"),
        "unit": fact.get("unit", ""),
        "taxonomy": fact.get("taxonomy", ""),
        "selected_tag": fact.get("selected_tag", ""),
        "start": fact.get("start", ""),
        "end": fact.get("end", ""),
        "fy": fact.get("fy", ""),
        "fp": fact.get("fp", ""),
        "form": fact.get("form", ""),
        "filed": fact.get("filed", ""),
        "accn": fact.get("accn", ""),
        "frame": fact.get("frame", ""),
        "source_type": fact.get("source_type", ""),
        "restatement_flag": bool(fact.get("restatement_flag")),
        "validation_notes": fact.get("validation_notes", ""),
        "component_accessions": fact.get("component_accessions", ""),
    }


def _derive_gross_profit_from_revenue_cogs(selected_by_variable):
    for key, revenue in list(selected_by_variable.get("revenue", {}).items()):
        if selected_by_variable.get("gross_profit", {}).get(key):
            continue
        cogs = selected_by_variable.get("cogs", {}).get(key)
        if not cogs or revenue.get("unit") != cogs.get("unit"):
            continue
        base = deepcopy(revenue)
        base["selected_value"] = revenue["selected_value"] - cogs["selected_value"]
        base["variable_name"] = "gross_profit"
        base["selected_tag"] = "Revenue minus COGS"
        base["taxonomy"] = "derived"
        base["source_type"] = "derived_revenue_less_cogs"
        base["validation_notes"] = "Gross profit derived because standardized GrossProfit was unavailable."
        base["component_accessions"] = "; ".join([revenue.get("accn", ""), cogs.get("accn", "")])
        selected_by_variable.setdefault("gross_profit", {})[key] = base


def _derive_total_debt(selected_by_variable):
    current = selected_by_variable.get("debt_current_component", {})
    noncurrent = selected_by_variable.get("debt_noncurrent_component", {})
    total = selected_by_variable.setdefault("total_debt", {})
    for key, cur in current.items():
        if key in total:
            continue
        noncur = noncurrent.get(key)
        if not noncur or cur.get("unit") != noncur.get("unit"):
            continue
        base = deepcopy(cur)
        base["selected_value"] = cur["selected_value"] + noncur["selected_value"]
        base["variable_name"] = "total_debt"
        base["taxonomy"] = "derived"
        base["selected_tag"] = f"{cur.get('selected_tag')} + {noncur.get('selected_tag')}"
        base["source_type"] = "derived_debt_components"
        base["validation_notes"] = "Total debt derived as current plus noncurrent debt components."
        base["component_accessions"] = "; ".join([cur.get("accn", ""), noncur.get("accn", "")])
        total[key] = base


def _same_currency(a, b):
    return bool(a) and bool(b) and a == b


def _safe_ratio(numerator, denominator):
    if numerator is None or denominator in (None, 0):
        return None
    return numerator / denominator


def _quality_flag(row):
    if row.get("manual_review_required"):
        return "REVIEW"
    missing_core = [v for v in ["revenue", "operating_income", "net_income"] if row.get(v) is None]
    if missing_core:
        return "LOW"
    if row.get("gross_profit") is None:
        return "LOW"
    source_types = [
        row.get("revenue_source_type"),
        row.get("gross_profit_source_type"),
        row.get("operating_income_source_type"),
        row.get("net_income_source_type"),
    ]
    if any(source and source != "direct_companyfacts" for source in source_types):
        return "MEDIUM"
    return "HIGH"


def _forms_seen(companyfacts):
    seen = set()
    for taxonomy in companyfacts.get("facts", {}).values():
        for meta in taxonomy.values():
            for facts in meta.get("units", {}).values():
                for fact in facts:
                    form = _clean_form(fact.get("form"))
                    if form:
                        seen.add(form)
    return seen


def extract_company_panel(companyfacts_path: Path, crosswalk_row: dict, retrieved_at: str):
    companyfacts = load_companyfacts(companyfacts_path)
    selected_by_variable = {}
    annual_by_variable = {}
    raw_fact_count = 0

    for variable, mapping in CONCEPT_MAP.items():
        variable_type = mapping["type"]
        if variable_type == "flow":
            selected, annual, raw_facts = _extract_flow_variable(companyfacts, variable)
        elif variable_type == "flow_direct_only":
            selected, annual, raw_facts = _extract_direct_only_flow_variable(companyfacts, variable)
        else:
            selected, annual, raw_facts = _extract_stock_variable(companyfacts, variable)
        selected_by_variable[variable] = selected
        annual_by_variable[variable] = annual
        raw_fact_count += len(raw_facts)

    _derive_gross_profit_from_revenue_cogs(selected_by_variable)
    _derive_total_debt(selected_by_variable)

    all_keys = set()
    for variable in PANEL_FINANCIAL_VARIABLES:
        all_keys.update(selected_by_variable.get(variable, {}).keys())
    all_keys = {key for key in all_keys if key[1] in QUARTER_ORDER and _period_end_after_2015(selected_by_variable, key)}

    source_audit = []
    panel_rows = []
    forms = _forms_seen(companyfacts)
    taxonomy_keys = set(companyfacts.get("facts", {}).keys())
    foreign_issuer = bool(forms & FOREIGN_FORMS) or ("ifrs-full" in taxonomy_keys and "us-gaap" not in taxonomy_keys)

    for key in sorted(all_keys, key=lambda item: fiscal_sort_key(item[0], item[1])):
        fy, fq = key
        anchor = _merge_period_anchor(selected_by_variable, key)
        cal_year, cal_quarter = calendar_quarter_from_date(anchor.get("end"))
        row = {
            "company_id": crosswalk_row["CIK"],
            "CIK": crosswalk_row["CIK"],
            "sec_entity_name": companyfacts.get("entityName", ""),
            "input_public_parent_company": crosswalk_row.get("input_public_parent_company", ""),
            "ticker": crosswalk_row.get("ticker", ""),
            "exchange": crosswalk_row.get("exchange", ""),
            "merchant_count": crosswalk_row.get("merchant_count", 0),
            "merchant_names": crosswalk_row.get("merchant_names", ""),
            "fiscal_year": fy,
            "fiscal_quarter": fq,
            "fiscal_period": f"FY{fy} {fq}",
            "period_start": anchor.get("start", ""),
            "period_end": anchor.get("end", ""),
            "duration_days": anchor.get("duration_days"),
            "calendar_year": cal_year,
            "calendar_quarter": cal_quarter,
            "currency": "",
            "form": anchor.get("form", ""),
            "filing_date": anchor.get("filed", ""),
            "accession_number": anchor.get("accn", ""),
            "amended_filing_flag": False,
            "restatement_flag": False,
            "concept_transition_flag": False,
            "unusual_duration_flag": False,
            "manual_review_required": False,
            "retrieved_at": retrieved_at,
        }

        for variable in PANEL_FINANCIAL_VARIABLES:
            fact = selected_by_variable.get(variable, {}).get(key)
            row[variable] = fact.get("selected_value") if fact else None
            if variable in CORE_VARIABLES or variable == "cogs":
                row[f"{variable}_tag"] = fact.get("selected_tag", "") if fact else ""
            if variable in CORE_VARIABLES:
                row[f"{variable}_source_type"] = fact.get("source_type", "") if fact else ""
            if fact:
                source_audit.append(_build_source_audit_row(companyfacts, crosswalk_row, key, variable, fact))
                row["amended_filing_flag"] = bool(row["amended_filing_flag"] or fact.get("amended_filing_flag"))
                row["restatement_flag"] = bool(row["restatement_flag"] or fact.get("restatement_flag"))
                if fact.get("duration_days") and variable in FLOW_DERIVABLE_VARIABLES:
                    row["unusual_duration_flag"] = bool(
                        row["unusual_duration_flag"] or is_unusual_quarter_duration(fact.get("duration_days"))
                    )
                if not row["currency"] and fact.get("unit") and variable in CORE_VARIABLES + ["cogs"]:
                    row["currency"] = fact.get("unit", "")

        row["gross_margin"] = _safe_ratio(row.get("gross_profit"), row.get("revenue"))
        row["operating_margin"] = _safe_ratio(row.get("operating_income"), row.get("revenue"))
        row["net_margin"] = _safe_ratio(row.get("net_income"), row.get("revenue"))

        if row.get("revenue") in (None, 0) and any(row.get(v) is not None for v in ["gross_profit", "operating_income", "net_income"]):
            row["manual_review_required"] = True
        row["core_data_quality_flag"] = _quality_flag(row)
        panel_rows.append(row)

    _add_growth_and_transition_flags(panel_rows)

    metadata = {
        "CIK": crosswalk_row["CIK"],
        "sec_entity_name": companyfacts.get("entityName", ""),
        "taxonomy_keys": "; ".join(sorted(taxonomy_keys)),
        "forms_seen": "; ".join(sorted(forms)),
        "foreign_issuer": foreign_issuer,
        "ifrs_company": "ifrs-full" in taxonomy_keys,
        "us_gaap_company": "us-gaap" in taxonomy_keys,
        "raw_mapped_fact_count": raw_fact_count,
    }

    annual_refs = []
    for variable, annuals in annual_by_variable.items():
        for fy, fact in annuals.items():
            if fact:
                annual_refs.append({"CIK": crosswalk_row["CIK"], "variable_name": variable, "fiscal_year": fy, **fact})

    return panel_rows, source_audit, metadata, annual_refs


def _period_end_after_2015(selected_by_variable, key):
    anchor = _merge_period_anchor(selected_by_variable, key)
    end = parse_date(anchor.get("end"))
    if not end:
        return False
    return end.year >= 2015


def _add_growth_and_transition_flags(panel_rows):
    rows_by_key = {(r["fiscal_year"], r["fiscal_quarter"]): r for r in panel_rows}
    previous_tags = {}
    for row in sorted(panel_rows, key=lambda r: fiscal_sort_key(r["fiscal_year"], r["fiscal_quarter"])):
        fy = row["fiscal_year"]
        fq = row["fiscal_quarter"]
        prior_yoy = rows_by_key.get((fy - 1, fq))
        prior_seq_key = None
        if fq == "Q1":
            prior_seq_key = (fy - 1, "Q4")
        else:
            prior_seq_key = (fy, f"Q{QUARTER_ORDER[fq] - 1}")
        prior_seq = rows_by_key.get(prior_seq_key)
        row["revenue_growth_yoy"] = _safe_ratio(row.get("revenue"), prior_yoy.get("revenue") if prior_yoy else None)
        if row["revenue_growth_yoy"] is not None:
            row["revenue_growth_yoy"] -= 1
        row["revenue_growth_qoq"] = _safe_ratio(row.get("revenue"), prior_seq.get("revenue") if prior_seq else None)
        if row["revenue_growth_qoq"] is not None:
            row["revenue_growth_qoq"] -= 1

        transition = False
        for variable in CORE_VARIABLES:
            tag = row.get(f"{variable}_tag", "")
            prev = previous_tags.get(variable)
            if tag and prev and tag != prev:
                transition = True
            if tag:
                previous_tags[variable] = tag
        row["concept_transition_flag"] = transition
