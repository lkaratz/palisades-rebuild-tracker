#!/usr/bin/env python3
"""
Weekly digest for the Palisades rebuild tracker.

Reads data/current.json and compares to data/snapshot_last_week.json.
Outputs a GitHub-flavored markdown summary to stdout if any tracked
metrics changed. Updates the snapshot at the end of each run so next
week compares against this week's numbers.

The companion workflow .github/workflows/weekly-digest.yml runs this
every Monday morning and creates a GitHub Issue (which emails the
repo owner) when there's content to report.
"""
import json
import sys
from pathlib import Path
from datetime import datetime, timezone


REPO_ROOT = Path(__file__).resolve().parent.parent
CURRENT_PATH = REPO_ROOT / "data" / "current.json"
SNAPSHOT_PATH = REPO_ROOT / "data" / "snapshot_last_week.json"


METRICS = [
    ("Applications received",     ("jurisdictions", "city_of_la", "applications_received")),
    ("Permits issued",            ("jurisdictions", "city_of_la", "permits_issued")),
    ("Avg days, app → permit",    ("jurisdictions", "city_of_la", "avg_days_to_permit")),
    ("Avg days in agency review", ("jurisdictions", "city_of_la", "avg_days_in_review")),
    ("Under construction",        ("under_construction",)),
    ("Certificates of occupancy", ("certificates_of_occupancy",)),
]


def get_value(data, path):
    cur = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def fmt_delta(current, previous):
    if current is None and previous is None:
        return "— (no data)"
    if previous is None:
        return f"{current:,} (new field)"
    if current is None:
        return f"missing (was {previous:,})"
    if current == previous:
        return f"{current:,} (unchanged)"
    diff = current - previous
    sign = "+" if diff > 0 else ""
    return f"{previous:,} → {current:,} ({sign}{diff:,})"


def main():
    if not CURRENT_PATH.exists():
        print("# ERROR: data/current.json missing", file=sys.stderr)
        sys.exit(1)

    current = json.loads(CURRENT_PATH.read_text())
    today = datetime.now(timezone.utc).strftime("%B %d, %Y")
    site_url = "https://lkaratz.github.io/palisades-rebuild-tracker"

    # First run: snapshot doesn't exist. Seed it and announce activation.
    if not SNAPSHOT_PATH.exists():
        SNAPSHOT_PATH.write_text(CURRENT_PATH.read_text())

        lines = [
            f"## Weekly digest activated — {today}",
            "",
            "The weekly digest is now running. Every Monday morning, you'll get a comparison",
            "of this week's permit numbers vs. last week's whenever anything changes.",
            "",
            "Current baseline:",
            "",
            "| Metric | Value |",
            "| --- | --- |",
        ]
        for label, path in METRICS:
            cur_val = get_value(current, path)
            if cur_val is not None:
                lines.append(f"| {label} | {cur_val:,} |")
        lines += [
            "",
            f"Site: {site_url}",
            "",
            "_Close this issue to dismiss. Next digest: next Monday morning._",
        ]
        print("\n".join(lines))
        return

    # Normal run: compare current to snapshot
    previous = json.loads(SNAPSHOT_PATH.read_text())

    rows = []
    any_change = False
    for label, path in METRICS:
        cur_val = get_value(current, path)
        prev_val = get_value(previous, path)
        if cur_val != prev_val:
            any_change = True
        rows.append((label, cur_val, prev_val))

    # Always advance the snapshot so next week compares against this week
    SNAPSHOT_PATH.write_text(CURRENT_PATH.read_text())

    if not any_change:
        # Output a comment line — the workflow won't create an issue for this
        print(f"# No changes detected for the week of {today}.")
        return

    lines = [
        f"## Weekly digest — {today}",
        "",
        "Comparing this week's numbers to last week's snapshot:",
        "",
        "| Metric | Change |",
        "| --- | --- |",
    ]
    for label, cur_val, prev_val in rows:
        lines.append(f"| {label} | {fmt_delta(cur_val, prev_val)} |")

    lines += [
        "",
        f"Site: {site_url}",
        "",
        "_Close this issue to dismiss. Next digest: next Monday._",
    ]

    print("\n".join(lines))


if __name__ == "__main__":
    main()
