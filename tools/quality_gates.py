#!/usr/bin/env python3
"""
tools/quality_gates.py

WP-H: Quality Gates & Manifest Alarms.
Enforces pre-send quality gates to prevent low-signal, dominated, or boilerplate issues.
"""

import logging
from typing import Dict, List, Set, Tuple

logger = logging.getLogger("quality_gates")


def count_by_source_type(payload: Dict[str, list]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for sec, items in payload.items():
        for it in items:
            stype = it.get("source_type", "rss")
            counts[stype] = counts.get(stype, 0) + 1
    return counts


def total_items_count(payload: Dict[str, list]) -> int:
    return sum(len(items) for items in payload.values())


def gate_single_source_domination(payload: Dict[str, list]) -> Tuple[bool, str]:
    tot = total_items_count(payload)
    if tot == 0:
        return (False, "Issue is empty")
    counts = count_by_source_type(payload)
    max_count = max(counts.values()) if counts else 0
    if (max_count / tot) > 0.5:
        max_type = max(counts, key=counts.get)
        return (False, f"Single source domination: '{max_type}' represents {max_count}/{tot} ({max_count/tot*100:.1f}%) of items.")
    return (True, "OK")


def gate_min_total_items(payload: Dict[str, list]) -> Tuple[bool, str]:
    tot = total_items_count(payload)
    if tot < 5:
        return (False, f"Thin issue: total items ({tot}) is below minimum threshold of 5.")
    return (True, "OK")


def gate_no_null_required_fields(payload: Dict[str, list]) -> Tuple[bool, str]:
    for sec, items in payload.items():
        for it in items:
            for k, v in it.items():
                if v is None or (isinstance(v, str) and not v.strip() and k not in ["getting_started", "author"]):
                    return (False, f"Null or empty required field '{k}' in section '{sec}' for title '{it.get('title')}'")
    return (True, "OK")


def gate_no_duplicate_ids(payload: Dict[str, list]) -> Tuple[bool, str]:
    seen: Set[str] = set()
    for sec, items in payload.items():
        for it in items:
            iid = it.get("id")
            if iid:
                if iid in seen:
                    return (False, f"Duplicate ID '{iid}' found across sections.")
                seen.add(iid)
    return (True, "OK")


def gate_boilerplate_check(payload: Dict[str, list]) -> Tuple[bool, str]:
    # Extract fix and angle fields
    fixes: List[str] = []
    for sec, items in payload.items():
        for it in items:
            fix = it.get("automation_fix") or it.get("your_angle")
            if fix:
                fixes.append(fix)

    def text_tokens(t: str) -> Set[str]:
        return {w.lower() for w in t.split() if len(w) > 2}

    # Pairwise similarity
    for i in range(len(fixes)):
        for j in range(i + 1, len(fixes)):
            t1 = text_tokens(fixes[i])
            t2 = text_tokens(fixes[j])
            if t1 and t2:
                sim = len(t1 & t2) / len(t1 | t2)
                if sim >= 0.8:
                    return (False, f"Boilerplate detected: similarity {sim:.2f} between fixes: '{fixes[i][:40]}' and '{fixes[j][:40]}'")

    return (True, "OK")


def gate_all_urls_hydrated(payload: Dict[str, list]) -> Tuple[bool, str]:
    for sec, items in payload.items():
        for it in items:
            url = it.get("url") or it.get("html_url")
            if not url or not url.startswith("http"):
                return (False, f"Unhydrated or invalid URL in section '{sec}': '{url}'")
    return (True, "OK")


def run_all_quality_gates(payload: Dict[str, list]) -> Tuple[bool, List[str]]:
    gates = [
        ("single_source_domination", gate_single_source_domination),
        ("min_total_items", gate_min_total_items),
        ("no_null_required_fields", gate_no_null_required_fields),
        ("no_duplicate_ids", gate_no_duplicate_ids),
        ("boilerplate_check", gate_boilerplate_check),
        ("all_urls_hydrated", gate_all_urls_hydrated)
    ]

    errors = []
    for name, gate_func in gates:
        ok, msg = gate_func(payload)
        if not ok:
            logger.error(f"QUALITY GATE FAILURE [{name}]: {msg}")
            errors.append(f"[{name}] {msg}")
        else:
            logger.info(f"QUALITY GATE PASSED [{name}]")

    return (len(errors) == 0, errors)
