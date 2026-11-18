"""Deterministic presentation of HRSA search results."""


def format_hrsa_result(result: dict) -> str:
    status = result.get("status", "unknown")
    query = result.get("query") or {}

    lines = [
        "HRSA Health Center Sites",
        "Search: " + ", ".join(f"{k}={v}" for k, v in query.items()),
        f"Status: {status}",
    ]

    if result.get("total_matches") is not None:
        lines.extend(
            [
                f"Eligible matches: {result['total_matches']}",
                f"Records returned: {result['returned_count']}",
                f"Result limit: {result.get('result_limit', 'not supplied')}",
                (
                    "Administrative-only sites excluded: "
                    f"{result.get('excluded_administrative_count', 0)}"
                ),
            ]
        )

    for number, site in enumerate(result.get("sites", []), 1):
        lines.extend(
            [
                "",
                f"{number}. {site['site_name']}",
                f"BPHC ID: {site['bphc_id']}",
                f"Organization: {site['organization']}",
                (
                    f"Address: {site['address']}, {site['city']}, "
                    f"{site['state']} {site['zip']}"
                ),
                f"Site type: {site['site_type']}",
                f"Site status: {site['site_status']}",
                f"Location type: {site['location_type']}",
                f"Setting: {site['setting']}",
            ]
        )

        for key, label in [
            ("phone", "Phone"),
            ("website_raw", "Website (as recorded)"),
            ("location_caution", "Location caution"),
            ("setting_statement", "Setting statement"),
        ]:
            if site.get(key):
                lines.append(f"{label}: {site[key]}")

    if result.get("message"):
        lines.extend(["", result["message"]])

    provenance = result.get("provenance")
    if provenance:
        lines.extend(
            [
                "",
                f"Dataset: {provenance['dataset_title']}",
                "Record date: "
                + str(
                    provenance.get("record_create_date")
                    or ", ".join(provenance.get("record_create_dates", []))
                    or "Not established"
                ),
                f"Dataset records: {provenance['dataset_record_count']}",
                f"SHA-256: {provenance['sha256']}",
            ]
        )

    return "\n".join(lines)
