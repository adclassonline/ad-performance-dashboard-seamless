#!/usr/bin/env python3
"""
Daily refresh script for Seamless Ads Dashboard.
Run by GitHub Actions every day at 9AM Eastern.
"""

import os, csv, io, json, time, urllib.request, urllib.parse
from datetime import datetime, timezone

SHEET_ID = os.environ.get("SHEET_ID", "14C_1qBb2JjN8Rjyam_x45St7QHdQBcDSKL9FjP-MryE")

TABS = [
    "Campaign Data", "Adset Data", "Ad Data",
    "NEW Trials Started", "Booked Demos",
    "Held Demos - On Opp level", "New Closed Won", "Recurring",
]

def fetch_tab(tab, retries=4):
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(tab)}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = list(csv.reader(io.StringIO(resp.read().decode("utf-8"))))
                if rows and "DNS" in rows[0][0]: raise ValueError("DNS cache overflow")
                print(f"  ✓ {tab}: {len(rows)-1} rows")
                return rows
        except Exception as exc:
            print(f"  ✗ {tab} attempt {attempt+1}: {exc}")
            if attempt < retries - 1: time.sleep(5)
    raise RuntimeError(f"Failed to fetch: {tab}")

def clean(v):
    return v.replace("\n", " ").replace("\r", " ").strip() if isinstance(v, str) else v

def main():
    print("Fetching Google Sheet tabs...")
    all_data = {}
    for tab in TABS:
        rows = fetch_tab(tab)
        all_data[tab] = [[clean(c) for c in row] for row in rows]

    all_data["Held Demos"] = all_data["Held Demos - On Opp level"]
    all_data["Trials Started"] = all_data["NEW Trials Started"]

    data_json = json.dumps(all_data, ensure_ascii=True)
    data_json = data_json.replace("</script>", "<\\/script>")

    html_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(html_path, "r", encoding="utf-8") as fh:
        content = fh.read()

    # Use string split/join instead of regex to avoid escape issues
    marker = "const SHEET_DATA = "
    end_marker = "};"
    
    start_idx = content.find(marker)
    if start_idx == -1:
        raise RuntimeError("SHEET_DATA marker not found in index.html")
    
    # Find the end of the SHEET_DATA block by counting braces
    brace_start = content.find("{", start_idx)
    depth = 0
    end_idx = brace_start
    for i in range(brace_start, len(content)):
        if content[i] == "{": depth += 1
        elif content[i] == "}":
            depth -= 1
            if depth == 0:
                end_idx = i + 1
                # consume optional semicolon
                if end_idx < len(content) and content[end_idx] == ";":
                    end_idx += 1
                break

    new_content = content[:start_idx] + marker + data_json + ";" + content[end_idx:]
    print("✓ SHEET_DATA replaced")

    # Inject timestamp
    now = datetime.now(timezone.utc)
    ts = now.strftime("%-m/%-d/%Y, %-I:%M %p") + " ET"
    new_content = new_content.replace("<!--LAST_UPDATED-->", ts)

    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(new_content)

    print(f"✓ index.html updated ({len(new_content):,} bytes)")
    print(f"✓ Timestamp: {ts}")
    print("Done.")

if __name__ == "__main__":
    main()
