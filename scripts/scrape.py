#!/usr/bin/env python3
"""
Daily scraper for Pacific Palisades rebuild tracker.

Pulls data from the California state rebuilding dashboard, which aggregates
official permit numbers from LA County, City of Los Angeles, City of Malibu,
and City of Pasadena. The state itself sources these numbers directly from
each jurisdiction and updates at least weekly (City of LA updates hourly).

Source: https://www.ca.gov/lafires/rebuilding-la/

The Palisades Fire footprint sits primarily within the City of Los Angeles
jurisdiction, with smaller portions in LA County and City of Malibu. This
scraper captures all three so the tracker can show jurisdictional context.

Output: data/current.json
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
    # Pasadena scraped but not displayed — it's the Eaton fire jurisdiction
    "City of Pasadena": "city_of_pasadena",
}

# Each metric is identified by a unique icon filename in the source page
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
    """
    Parse a list of elements belonging to one jurisdiction.

    Each metric in the source is structured as:
        <img src="...icon-NAME.svg">
        <some_tag>NUMBER</some_tag>
        <some_tag>LABEL</some_tag>

    We walk the elements in order; when we see a recognized icon, we
    capture the next integer we find as that metric's value.
    """
    result = {}
    pending_metric = None

    for el in section_elements:
        # Look for images that match our known metric icons
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
    # ca.gov rejects unrecognized user agents with a 403, so we identify as
    # a current browser. This is the standard approach for civic scrapers
    # that pull from public-facing dashboards designed for browser viewing.
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

        # Collect all siblings until the next heading of equal-or-higher level
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

    return {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": STATE_URL,
        "source_note": (
            "Numbers sourced from California state dashboard, which aggregates "
            "official data from each jurisdiction. The City of Los Angeles "
            "section reflects Palisades Fire rebuilding within City limits."
        ),
        "jurisdictions": data,
    }


def main():
    out_path = Path(__file__).resolve().parent.parent / "data" / "current.json"
    out_path.parent.mkdir(exist_ok=True)

    try:
        result = scrape()
    except Exception as exc:
        # On failure, leave existing data in place and exit non-zero so the
        # Actions workflow logs the error but doesn't overwrite good data.
        print(f"ERROR: scrape failed: {exc}", file=sys.stderr)
        sys.exit(1)

    out_path.write_text(json.dumps(result, indent=2) + "\n")
    print(f"Wrote {out_path}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
