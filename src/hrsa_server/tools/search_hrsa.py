"""Bounded HRSA lookup functions for the approved November 11 snapshot."""

import csv
import hashlib
import io
from pathlib import Path
from .display_hrsa import format_hrsa_result

DATA_FILE = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "Health_Center_Service_Delivery_and_LookAlike_Sites.csv"
)
BASELINE_SHA256 = (
    "142e198931ff3f23802ddba071eda45a"
    "bb10778af115d0c7c6841210d9f99f37"
)
DATASET_TITLE = "HRSA Health Center Sites"
MOBILE_SEASONAL_CAUTION = (
    "The listed address may not be where or when services are delivered; "
    "verify with the provider."
)
SETTING_STATEMENT = "The dataset does not establish who may use this site."
DEFAULT_LIMIT = 5
MAX_LIMIT = 10


def _load_verified_snapshot():
    """Hash and parse the exact same bytes; reject other snapshots."""
    content = DATA_FILE.read_bytes()
    actual_hash = hashlib.sha256(content).hexdigest()
    if actual_hash != BASELINE_SHA256:
        raise ValueError("HRSA dataset integrity check failed")
    rows = list(csv.DictReader(io.StringIO(content.decode("utf-8-sig"), newline="")))
    return rows, actual_hash


def load_hrsa_rows():
    """Retain the existing entry point used by check_hrsa_dataset."""
    rows, _ = _load_verified_snapshot()
    return rows


def get_hrsa_snapshot_sha256():
    """Return the hash of the actual verified snapshot bytes."""
    _, actual_hash = _load_verified_snapshot()
    return actual_hash


def _provenance(rows, actual_hash):
    dates = sorted({
        row.get("Data Warehouse Record Create Date", "").strip()
        for row in rows
        if row.get("Data Warehouse Record Create Date", "").strip()
    })
    return {
        "dataset_title": DATASET_TITLE,
        "record_create_date": dates[0] if len(dates) == 1 else None,
        "record_create_dates": dates,
        "sha256": actual_hash,
        "dataset_record_count": len(rows),
    }


def _site(row):
    location_type = row.get("Health Center Location Type Description", "").strip()
    calendar = row.get("Health Center Operating Calendar", "").strip()
    setting = row.get("Health Center Service Delivery Site Location Setting Description", "").strip()
    website = row.get("Site Web Address", "").strip()
    if website.casefold() in {"", "n/a", "na", "none", "null", "not available"}:
        website = None
    mobile_or_seasonal = (
        "mobile" in location_type.casefold()
        or "seasonal" in location_type.casefold()
        or "seasonal" in calendar.casefold()
    )
    restricted_setting = "school" in setting.casefold() or "correction" in setting.casefold()
    return {
        "bphc_id": row.get("BPHC Assigned Number", "").strip(),
        "site_name": row.get("Site Name", "").strip(),
        "organization": row.get("Health Center Name", "").strip(),
        "site_type": row.get("Health Center Type Description", "").strip(),
        "site_status": row.get("Site Status Description", "").strip(),
        "location_type": location_type,
        "setting": setting,
        "address": row.get("Site Address", "").strip(),
        "city": row.get("Site City", "").strip(),
        "state": row.get("Site State Abbreviation", "").strip(),
        "zip": row.get("Site Postal Code", "").strip(),
        "phone": row.get("Site Telephone Number", "").strip() or None,
        "website_raw": website,
        "location_caution": MOBILE_SEASONAL_CAUTION if mobile_or_seasonal else None,
        "setting_statement": SETTING_STATEMENT if restricted_setting else None,
    }


def _failure(status, query, message):
    result = {
        "status": status,
        "query": query,
        "total_matches": None,
        "returned_count": 0,
        "sites": [],
        "provenance": None,
        "message": message,
    }
    result["display_text"] = format_hrsa_result(result)
    return result


def _search(query, matches_row, limit):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_LIMIT:
        return _failure("invalid_input", query, "limit must be an integer from 1 to 10")
    try:
        rows, actual_hash = _load_verified_snapshot()
    except (OSError, UnicodeError, ValueError, csv.Error):
        return _failure("source_unavailable", query, "HRSA dataset unavailable or integrity check failed; no listings returned")

    located = [row for row in rows if matches_row(row)]
    excluded_admin_count = sum(
        row.get("Health Center Type Description", "").strip().casefold() == "administrative"
        for row in located
    )
    eligible = [
        row for row in located
        if row.get("Health Center Type Description", "").strip().casefold() != "administrative"
    ]
    eligible.sort(key=lambda row: (
        row.get("Site Name", "").casefold(),
        row.get("BPHC Assigned Number", ""),
    ))
    returned = eligible[:limit]
    result = {
        "status": "ok" if eligible else "no_match",
        "query": query,
        "total_matches": len(eligible),
        "returned_count": len(returned),
        "result_limit": limit,
        "excluded_administrative_count": excluded_admin_count,
        "sites": [_site(row) for row in returned],
        "provenance": _provenance(rows, actual_hash),
        "message": (
            "HRSA listings do not establish current availability, eligibility, or payer acceptance."
            if eligible else "No matching non-administrative sites in this snapshot; no other locations inferred."
        ),
    }
    result["display_text"] = format_hrsa_result(result)
    return result


def search_city_state(city: str, state: str, limit: int = DEFAULT_LIMIT) -> dict:
    """Search by city AND two-letter state; defaults to five, maximum ten sites."""
    city_clean = city.strip() if isinstance(city, str) else ""
    state_clean = state.strip().upper() if isinstance(state, str) else ""
    query = {"city": city_clean, "state": state_clean}
    if not city_clean or len(state_clean) != 2 or not state_clean.isalpha():
        return _failure("invalid_input", query, "A city and two-letter state abbreviation are required")
    return _search(
        query,
        lambda row: row.get("Site City", "").strip().casefold() == city_clean.casefold()
        and row.get("Site State Abbreviation", "").strip().upper() == state_clean,
        limit,
    )


def search_zip5(zip5: str, limit: int = DEFAULT_LIMIT) -> dict:
    """Search by five-digit ZIP, preserving leading zeros; maximum ten sites."""
    zip_clean = zip5.strip() if isinstance(zip5, str) else ""
    query = {"zip5": zip_clean}
    if len(zip_clean) != 5 or not zip_clean.isascii() or not zip_clean.isdigit():
        return _failure("invalid_input", query, "ZIP must contain exactly five digits")
    return _search(
        query,
        lambda row: row.get("Site Postal Code", "").strip()[:5] == zip_clean,
        limit,
    )
