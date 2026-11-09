"""Conservative comparison of the original dashboard's KAP holdings and Fonoloji.

This is cross-source reconciliation, NOT a trading-activity inference.
Never derives paid/unpaid status from holdings or disclosure titles.
"""
import hashlib
import json
import math
import re
from collections import defaultdict

CODE_RE=re.compile(r"^[A-Z0-9]{3,16}$")
GENERIC_CODES={"BPP","TRY","USD","EUR","TL","ALTIN","GOLD","CASH","NAKIT"}

def ticker(value):
    s=str(value or "").strip().upper()
    return s if CODE_RE.fullmatch(s) and s not in GENERIC_CODES else None

def finite_weight(value):
    try:
        if isinstance(value,bool):return None
        w=float(value)
        return round(w,6) if math.isfinite(w) and -100<=w<=100 else None
    except (ValueError,TypeError,OverflowError):
        return None

def original_positions(rows,code):
    out=defaultdict(list)
    for row in rows:
        if not isinstance(row,(list,tuple)) or len(row)<7 or row[0]!=code:continue
        key=ticker(row[2])
        weight=finite_weight(row[6])
        if key and weight is not None:out[key].append(weight)
    return out

def latest_positions(items):
    out=defaultdict(list)
    for item in items:
        if not isinstance(item,dict):continue
        code=ticker(item.get("asset_code"))
        weight=finite_weight(item.get("weight"))
        if code and weight is not None:out[code].append(weight)
    return out

def fingerprint(items):
    """Hash of source composition only; not a price-change or trade signal."""
    if not isinstance(items,list):raise ValueError("KAP holdings must be a list")
    canon=[]
    for item in items:
        if not isinstance(item,dict):continue
        weight=finite_weight(item.get("weight"))
        canon.append([str(item.get("asset_code") or ""),
                      str(item.get("asset_type") or ""),
                      weight])
    canon.sort(key=lambda v:json.dumps(v,ensure_ascii=False))
    return hashlib.sha256(json.dumps(canon,ensure_ascii=False,separators=(",",":"),allow_nan=False).encode()).hexdigest()

def compare_portfolios(original_rows,code,kap_items,kap_period):
    old=original_positions(original_rows,code)
    new=latest_positions(kap_items)
    overlap=sorted(set(old)&set(new))
    unique=[k for k in overlap if len(old[k])==1 and len(new[k])==1]
    ambiguous=[k for k in overlap if k not in unique]
    changes=[]
    for key in unique:
        delta=round(new[key][0]-old[key][0],4)
        if abs(delta)>=0.1:
            changes.append({"asset_code":key,
                            "original_weight_pct":round(old[key][0],4),
                            "latest_weight_pct":round(new[key][0],4),
                            "difference_percentage_points":delta})
    changes.sort(key=lambda item:-abs(item["difference_percentage_points"]))
    status="CROSS_SOURCE_REFERENCE_ONLY" if unique else "INSUFFICIENT_COMPARABLE_CODES"
    return {
        "status":status,
        "original_portfolio_period":"UNKNOWN",
        "latest_kap_period":kap_period,
        "periods_confirmed_equal":False,
        "distinct_original_codes":len(old),
        "distinct_kap_codes":len(new),
        "comparable_unique_codes":len(unique),
        "ambiguous_duplicate_codes":ambiguous[:20],
        "different_source_only_codes":{
            "only_original":sorted(set(old)-set(new))[:15],
            "only_kap":sorted(set(new)-set(old))[:15]
        },
        "top_weight_differences":changes[:20],
        "difference_unit":"percentage_points",
        "methodology":"Only exact unique asset-code matches are compared. Missing/duplicate codes are not inferred. Original report period is unknown. Differences may be valuation/reporting/source differences; NEVER inferred trades, defaults or payments.",
    }
