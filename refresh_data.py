#!/usr/bin/env python3
"""
Daily refresh script for Seamless Ads Dashboard.
Fetches all Google Sheet tabs and rebuilds index.html with fresh data.
Run by GitHub Actions every day at 9AM Eastern.
"""

import os
import re
import csv
import io
import json
import time
import urllib.request
import urllib.parse

# ── Config ──────────────────────────────────────────────────────────────────
SHEET_ID = os.environ.get("SHEET_ID", "14C_1qBb2JjN8Rjyam_x45St7QHdQBcDSKL9FjP-MryE")

TABS = [
    "Campaign Data",
    "Adset Data",
    "Ad Data",
    "Trials Started",
    "Booked Demos",
    "Held Demos - On Opp level",
    "New Closed Won",
    "Recurring",
]

# ── Fetch ────────────────────────────────────────────────────────────────────
def fetch_tab(tab, retries=4, delay=5):
    url = (
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
        f"/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(tab)}"
    )
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = list(csv.reader(io.StringIO(resp.read().decode("utf-8"))))
                if rows and "DNS" in rows[0][0]:
                    raise ValueError("DNS cache overflow")
                print(f"  ✓ {tab}: {len(rows)-1} rows")
                return rows
        except Exception as exc:
            print(f"  ✗ {tab} attempt {attempt+1}: {exc}")
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError(f"Failed to fetch tab: {tab}")


def clean(value):
    if isinstance(value, str):
        return value.replace("\n", " ").replace("\r", " ").strip()
    return value


# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("Fetching Google Sheet tabs...")
    all_data = {}
    for tab in TABS:
        rows = fetch_tab(tab)
        all_data[tab] = [[clean(c) for c in row] for row in rows]

    # Keep 'Held Demos' as alias for the new tab name
    all_data["Held Demos"] = all_data["Held Demos - On Opp level"]

    # Serialise
    data_json = json.dumps(all_data, ensure_ascii=True)
    data_json = data_json.replace("</script>", "<\\/script>")
    assert "\n" not in data_json, "JSON must be single-line"

    # Read template
    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Replace embedded SHEET_DATA
    new_content = re.sub(
        r"const SHEET_DATA = \{.*?\};",
        f"const SHEET_DATA = {data_json};",
        content,
        flags=re.DOTALL,
    )

    if new_content == content:
        print("WARNING: SHEET_DATA pattern not found — index.html may not be correct.")
    else:
        print("✓ SHEET_DATA replaced")

    # Write back
    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    print(f"✓ index.html updated ({len(new_content):,} bytes)")
    print("Done.")


if __name__ == "__main__":
    main()
