"""
Analyse the saved warrant finder HTML to understand table structure.

Run with:
    uv run python -m scripts.analyse_warrant_html
"""

from bs4 import BeautifulSoup

HTML_FILE = "scripts/warrant_finder_response.html"

with open(HTML_FILE, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

# ── Find result tables ────────────────────────────────────────────────────────
tables = soup.find_all("table")
print(f"Total <table> elements: {len(tables)}")
for i, t in enumerate(tables):
    classes = t.get("class", [])
    rows = t.find_all("tr")
    print(f"  [{i}] class={classes}  rows={len(rows)}")

print()

# ── Focus on comparison table ─────────────────────────────────────────────────
table = soup.find("table", class_="table--comparison")
if not table:
    # try without class constraint
    table = tables[0] if tables else None
    print("No table--comparison found, using first table")
else:
    print("Found table--comparison")

if not table:
    print("No tables at all — page may be empty or requires auth")
    raise SystemExit(1)

rows = table.find_all("tr")
print(f"Rows in table: {len(rows)}\n")

# ── Header row ────────────────────────────────────────────────────────────────
header_row = table.find("tr")
headers = [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]
print("Column headers:")
for i, h in enumerate(headers):
    print(f"  [{i}] {h!r}")

print()

# ── First data row — raw HTML ─────────────────────────────────────────────────
data_rows = [r for r in rows if r.find("td")]
if not data_rows:
    print("No data rows found")
    raise SystemExit(1)

print(f"Data rows: {len(data_rows)}")
print()
print("=== FIRST DATA ROW RAW HTML ===")
print(data_rows[0].prettify()[:6000])

print()
print("=== FIRST DATA ROW CELL TEXT ===")
cells = data_rows[0].find_all(["td", "th"])
for i, cell in enumerate(cells):
    print(f"  [{i}] text={cell.get_text(strip=True)!r}")
    # Show all attributes and links
    for a in cell.find_all("a", href=True):
        print(f"       <a href={a['href']!r}>")
    for span in cell.find_all("span"):
        attrs = {k: v for k, v in span.attrs.items() if k != "class"}
        if attrs:
            print(f"       <span attrs={attrs}>")
