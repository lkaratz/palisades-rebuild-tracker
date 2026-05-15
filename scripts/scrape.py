#!/usr/bin/env python3
"""
Daily scraper for Pacific Palisades rebuild tracker.

Pulls data from the California state rebuilding dashboard, which aggregates
official permit numbers from LA County, City of Los Angeles, City of Malibu,
and City of Pasadena. The state itself sources these numbers directly from
each jurisdiction and updates at least weekly (City of LA updates hourly).

Source: https://www.ca.gov/lafires/rebuilding-la/

IMPORTANT: This scraper MERGES into the existing data/current.json so that
hand-curated fields (milestones, neighborhoods, resources, under_construction,
certificates_of_occupancy, context) are preserved across runs. Only the
fields the state dashboard provides are updated.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

STATE_URL = "https://www.ca.gov/lafires/rebuilding-la/"

JURISDICTIONS = {
    "City of Los Angeles": "city_of_la",
    "Los Angeles County": "la_county",
    "City of Malibu": "city_of_malibu",
    "City of Pasadena": "city_of_pasadena",
}

METRIC_ICONS = {
    "icon-permits-received.svg": "applications_received",
    "icon-permits-issued.svg": "permits_issued",
    "icon-calendar-permit.svg": "avg_days_to_permit",
    "icon-calendar.svg": "avg_days_in_review",
}


def first_int(text: str):
    """Extract the first integer (with optional comma thousands) from text."""
    if not text:
        return None
    m = re.search(r"\d{1,3}(?:,\d{3})+|\d+", text)
    return int(m.group().replace(",", "")) if m else None


def parse_jurisdiction_section(section_elements):
    """Parse the metric icons and their values for one jurisdiction."""
    result = {}
    pending_metric = None

    for el in section_elements:
        for img in el.find_all("img") if hasattr(el, "find_all") else []:
            src = img.get("src", "")
            for icon_name, metric_key in METRIC_ICONS.items():
                if icon_name in src:
                    pending_metric = metric_key
                    break

        if pending_metric:
            text = el.get_text(" ", strip=True) if hasattr(el, "get_text") else str(el)
            value = first_int(text)
            if value is not None and pending_metric not in result:
                result[pending_metric] = value
                pending_metric = None

    return result


def scrape():
    """Fetch the state page and return the scraped jurisdiction data."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    resp = requests.get(STATE_URL, headers=headers, timeout=30)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    data = {}

    for heading in soup.find_all(["h2", "h3", "h4"]):
        name = heading.get_text(strip=True)
        if name not in JURISDICTIONS:
            continue

        section_elements = []
        for sib in heading.next_siblings:
            if getattr(sib, "name", None) in ("h2", "h3", "h4"):
                break
            section_elements.append(sib)

        parsed = parse_jurisdiction_section(section_elements)
        if parsed:
            data[JURISDICTIONS[name]] = parsed

    if not data:
        raise RuntimeError(
            "No jurisdiction data found on state page. "
            "Page structure may have changed."
        )

    return data


def main():
    out_path = Path(__file__).resolve().parent.parent / "data" / "current.json"
    out_path.parent.mkdir(exist_ok=True)

    # CRITICAL: read existing data so we preserve hand-curated fields like
    # milestones, neighborhoods, resources, under_construction, etc.
    existing = {}
    if out_path.exists():
        try:
            existing = json.loads(out_path.read_text())
        except json.JSONDecodeError:
            print(
                "Warning: existing data file is invalid JSON; starting fresh.",
                file=sys.stderr,
            )
            existing = {}

    try:
        scraped_jurisdictions = scrape()
    except Exception as exc:
        # On failure, leave existing data in place and exit non-zero.
        # The site keeps showing the last good numbers.
        print(f"ERROR: scrape failed: {exc}", file=sys.stderr)
        sys.exit(1)

    # Merge: update only the fields the state dashboard provides; preserve
    # everything else (milestones, neighborhoods, resources, context,
    # under_construction, certificates_of_occupancy, etc.)
    existing["last_updated"] = datetime.now(timezone.utc).isoformat()
    existing["source"] = STATE_URL
    existing["source_note"] = (
        "Numbers sourced from California state rebuilding dashboard, which "
        "aggregates official data from each jurisdiction. The City of Los "
        "Angeles section reflects Palisades Fire rebuilding within City limits."
    )

    # Merge jurisdictions (don't wipe the whole dict — update each key)
    if "jurisdictions" not in existing or not isinstance(
        existing.get("jurisdictions"), dict
    ):
        existing["jurisdictions"] = {}
    for juris_key, juris_data in scraped_jurisdictions.items():
        existing["jurisdictions"][juris_key] = juris_data

    out_path.write_text(json.dumps(existing, indent=2) + "\n")
    print(f"Wrote {out_path}")
    print(json.dumps(scraped_jurisdictions, indent=2))


if __name__ == "__main__":
    main()
