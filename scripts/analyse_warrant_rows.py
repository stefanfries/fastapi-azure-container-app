"""
Deep-dive analysis of warrant data rows (skipping ad rows).

Run with:
    uv run python -m scripts.analyse_warrant_rows
"""

from bs4 import BeautifulSoup

HTML_FILE = "scripts/warrant_finder_response.html"

with open(HTML_FILE, encoding="utf-8") as f:
    soup = BeautifulSoup(f, "html.parser")

table = soup.find("table", class_="table--comparison")
rows = table.find_all("tr")

# Identify real warrant rows — they have a <td> with data-id attribute OR
# have the expected number of columns (skip ad rows / header)
warrant_rows = []
for row in rows:
    tds = row.find_all("td")
    # Ad rows have colspan, real rows have many individual cells
    if len(tds) >= 8 and not row.find("td", colspan=True):
        warrant_rows.append(row)

print(f"Real warrant rows found: {len(warrant_rows)}\n")

if not warrant_rows:
    # Fall back: show all rows with td count
    print("Row td counts:")
    for i, row in enumerate(rows):
        tds = row.find_all("td")
        colspan_tds = row.find_all("td", colspan=True)
        print(f"  row[{i}]: tds={len(tds)}, colspan_tds={len(colspan_tds)}")
    raise SystemExit

# ── Inspect first real warrant row ───────────────────────────────────────────
row = warrant_rows[0]
print("=== FIRST WARRANT ROW RAW HTML ===")
print(row.prettify()[:8000])

print("\n=== ALL CELLS ===")
for i, td in enumerate(row.find_all(["td", "th"])):
    text = td.get_text(" ", strip=True)
    data_attrs = {k: v for k, v in td.attrs.items()}
    links = [(a.get_text(strip=True), a.get("href", "")) for a in td.find_all("a", href=True)]
    spans = [(s.get_text(strip=True), s.attrs) for s in td.find_all("span") if s.attrs]
    print(f"\n  cell[{i}]")
    print(f"    text  = {text!r}")
    print(f"    attrs = {data_attrs}")
    if links:
        print(f"    links = {links}")
    if spans:
        print(f"    spans = {spans[:3]}")

# ── Check for pagination ──────────────────────────────────────────────────────
print("\n=== PAGINATION ===")
pager = soup.find("div", class_="pagination")
if pager:
    print(pager.prettify()[:2000])
else:
    print("No pagination div found")
    # try other patterns
    for tag in soup.find_all(attrs={"class": lambda c: c and "pag" in " ".join(c).lower()}):
        print(f"  possible pager: <{tag.name} class={tag.get('class')}> text={tag.get_text(strip=True)[:80]!r}")
