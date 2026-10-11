"""Data for the Tableau Story infographics: diagram grids, scorecard bars and regression bars.

Diagram engine: each diagram is a grid of cells (Col x Row). Tableau draws each cell as a
square mark filling the cell (highlight-table style), shaded on a white to navy scale, with up
to three text lines. Light cells (Shade < 0.5) carry dark text fields (*D); dark cells carry
light text fields (*L), so labels always contrast with the fill.

Outputs (data/tableau/):
  story_diagrams.csv   Diagram, Col, Row, Kind, Shade, TitleD, TitleL, L1D, L1L, L2D, L2L
  scorecard_bars.csv   Panel, Item, ItemOrder, Part, Value, Shade, LabelL, LabelD
  regression_bars.csv  StateLabel, StateOrder, Bureau, Value, Shade, LabelL, LabelD, Verdict
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "tableau"
rows = []


def cell(diagram, col, row, title="", l1="", l2="", shade=0.15, kind="Box"):
    dark = shade >= 0.5
    rows.append({
        "Diagram": diagram, "Col": col, "Row": row, "Kind": kind, "Shade": shade,
        "TitleD": "" if dark else title, "TitleL": title if dark else "",
        "L1D": "" if dark else l1, "L1L": l1 if dark else "",
        "L2D": "" if dark else l2, "L2L": l2 if dark else "",
    })


def arrow(diagram, col, row, glyph="➔"):
    cell(diagram, col, row, glyph, "", "", 0.0, "Arrow")


# 1. Stakeholders ---------------------------------------------------------------
D = "1 Stakeholders"
for c, (t, a, b) in enumerate([
    ("Personal credit clients", "Apply where the strongest", "report is pulled"),
    ("Business credit clients", "Which business cards check", "the owner's personal report"),
    ("Credit consulting companies", "Plan disputes, rebuilding", "and inquiry spacing"),
    ("Business funding companies", "Stack approvals without", "stacking one report"),
], start=1):
    cell(D, c, 1, t, a, b, 1.0)
for c, (t, a, b) in enumerate([
    ("Funding advisors and brokers", "Run the lookup", "for each client"),
    ("Analysts and reviewers", "Trace every figure", "back to its source"),
    ("Lenders and partners", "Receive fewer", "mismatched applications"),
    ("Everyone", "Planning reference,", "not financial advice"),
], start=1):
    cell(D, c, 2, t, a, b, 0.2)

# 2. Scope ----------------------------------------------------------------------
D = "2 Scope"
cell(D, 1, 1, "IN SCOPE", "What this story answers", "", 1.0)
cell(D, 2, 1, "OUT OF SCOPE", "What it does not answer", "", 0.6)
ins = [("Bureau pulled by lender", "Experian, Equifax, TransUnion", "by U.S. state and DC"),
       ("Personal and business funding", "Cards, lines, loans, SBA,", "auto, equipment, real estate"),
       ("Lender attributes", "Funding type, typical score,", "low or no doc options"),
       ("Funding sequence", "Seven score tiers,", "500-549 through 800+"),
       ("Evidence window", "Original 355-row table plus", "public datapoints 2008-2026")]
outs = [("Approval odds", "No prediction of whether", "a client is approved"),
        ("Business bureau files", "D&B, Experian Business and", "Equifax Business not mapped"),
        ("Soft pulls", "Prequalification and", "account reviews excluded"),
        ("Live rates and terms", "Minimums are a snapshot", "as of October 2026"),
        ("Advice", "Not legal, tax or", "financial advice")]
for r, (a, b) in enumerate(zip(ins, outs), start=2):
    cell(D, 1, r, *a, 0.12)
    cell(D, 2, r, *b, 0.05)

# 3. Enrichment flow --------------------------------------------------------------
D = "3 Enrichment"
steps = [("1. ORIGINAL TABLE", "355 rows, 16 states", "229 raw lender spellings", 0.1),
         ("2. CLEAN AND MATCH", "229 spellings to 102 lenders", "markers normalized", 0.3),
         ("3. ENRICH", "Funding type, score, doc level", "102 more lenders (204 total)", 0.55),
         ("4. CROSS-CHECK", "670 outside state datapoints", "56 sources, 2008-2026", 0.8),
         ("5. RESULT", "84 confirmed, 6 partly", "102 fit national, 0 contradicted", 1.0)]
for i, (t, a, b, s) in enumerate(steps):
    cell(D, 2 * i + 1, 1, t, a, b, s)
    if i < len(steps) - 1:
        arrow(D, 2 * i + 2, 1)

# 4. ETL flow ----------------------------------------------------------------------
D = "4 ETL"
cell(D, 1, 1, "EXTRACT", "Read every source", "", 0.35)
cell(D, 3, 1, "TRANSFORM", "Clean, join, categorize", "", 0.7)
cell(D, 5, 1, "LOAD", "Publish to every output", "", 1.0)
ext = [("Original workbook", "All States & Banks tab", ""),
       ("Issuer state tables", "Doctor of Credit, 2008-2017", "MyBankTracker"),
       ("myFICO forum grid", "July 2023 plus", "2025-2026 posts"),
       ("Lender pages", "Minimums, products,", "documentation rules")]
trf = [("Name matching", "229 spellings to 102 lenders", "ordered rules, reviewed"),
       ("Normalize markers", "x, blanks, zeros, counts", "to pulled or not pulled"),
       ("Join and compare", "Each row vs outside data", "by lender and state"),
       ("Categorize and reshape", "Cross-check, confidence,", "long format for maps")]
lod = [("Excel workbook", "Six tabs with", "live totals"),
       ("Website", "Seven pages on", "GitHub Pages"),
       ("Tableau Public", "Maps, regression", "and this story"),
       ("Regression inputs", "Weighted reports", "for the model")]
for r, (a, b, c) in enumerate(zip(ext, trf, lod), start=2):
    cell(D, 1, r, *a, 0.12)
    arrow(D, 2, r)
    cell(D, 3, r, *b, 0.25)
    arrow(D, 4, r)
    cell(D, 5, r, *c, 0.4)

# 5. Share equation ------------------------------------------------------------------
D = "5 Equation"
cell(D, 1, 1, "Bureau pulls in the state", "Experian, Equifax or TransUnion", "all lenders combined", 0.6)
arrow(D, 2, 1, "÷")
cell(D, 3, 1, "All bureau pulls in the state", "Experian + Equifax + TransUnion", "", 0.3)
arrow(D, 4, 1, "=")
cell(D, 5, 1, "Bureau share", "Chance a recorded pull", "landed on that bureau", 1.0)
for r, (st, n, tot, pct) in enumerate([("Utah, Experian", 4, 7, "57%"),
                                        ("Florida, Experian", 466, 885, "53%"),
                                        ("Georgia, TransUnion", 37, 116, "32%")], start=2):
    cell(D, 1, r, f"{n}", st, "pulls", 0.12)
    arrow(D, 2, r, "÷")
    cell(D, 3, r, f"{tot}", "all bureau pulls", "", 0.06)
    arrow(D, 4, r, "=")
    cell(D, 5, r, pct, "share", "", 0.35)

# 6. Regression flow ----------------------------------------------------------------
D = "6 Regression"
cell(D, 1, 1, "INPUTS", "2,901 pull datapoints", "862 reports", 0.3)
cell(D, 3, 1, "MODEL", "Multinomial logistic", "regression", 0.6)
cell(D, 5, 1, "OUTPUT", "Likelihood per bureau", "for each state", 0.8)
cell(D, 7, 1, "VERDICT", "24 close-call states", "top two within 20 pts", 1.0)
inp = [("State", "50 states and DC", ""), ("Lender", "14 named issuers", "plus industry groups"),
       ("Data era", "2008-2017, 2023 grid,", "original list"), ("Lender in state", "Issuer rules that", "change by state")]
mod = [("L2 penalty", "Thin states lean to", "the national pattern"), ("Cross-validated", "Log loss 0.903", "55% vs 50% baseline"),
       ("Weights capped", "10 datapoints per report", "so no list dominates"), ("150 bootstrap refits", "How often the leader", "stays the leader")]
outp = [("P(Experian)", "Typical application", "national lender mix"), ("P(Equifax)", "With 90% ranges", ""),
        ("P(TransUnion)", "With 90% ranges", ""), ("Lender by state", "Likelihood for each", "major issuer")]
ver = [("10 clear lean", "Experian holds in", "90%+ of refits", 1.0), ("5 moderate lean", "Holds in 70%+", "of refits", 0.8),
       ("4 toss-ups", "HI, KS, SC, VA", "", 0.55), ("5 thin data", "Under 10 datapoints", "national pattern", 0.3)]
for r in range(4):
    cell(D, 1, r + 2, *inp[r], 0.1)
    arrow(D, 2, r + 2)
    cell(D, 3, r + 2, *mod[r], 0.2)
    arrow(D, 4, r + 2)
    cell(D, 5, r + 2, *outp[r], 0.3)
    arrow(D, 6, r + 2)
    t, a, b, s = ver[r]
    cell(D, 7, r + 2, t, a, b, s)

# 7. Funding ladder ---------------------------------------------------------------
D = "7 Ladder"
tiers = [("500-549", "Repair and build", "Disputes, builder loan,", "no-check secured card"),
         ("550-599", "Starter credit", "Prequalify, starter card,", "CDFI microloan"),
         ("600-649", "First unsecured", "Mainstream cards,", "low-doc business line"),
         ("650-699", "Enter the majors", "Chase first, then Amex", "cards and line"),
         ("700-749", "Full 0% stack", "Chase, Amex, U.S. Bank,", "Wells Fargo, BofA"),
         ("750-799", "Stack plus banks", "Citi, Barclays,", "bank lines and SBA"),
         ("800+", "Largest facilities", "Relationship lines,", "SBA, then card stack")]
for c, (t, head, a, b) in enumerate(tiers, start=1):
    s = round(min(0.15 + c * 0.125, 1.0), 3)
    top = 8 - c                      # higher tiers climb higher: a staircase
    cell(D, c, top, t, head, "", s)
    for r in range(top + 1, 8):      # the step's riser, same shade, no text
        cell(D, c, r, "", "", "", s, "Step")
    cell(D, c, 8, a, b, "", 0.06)

# 8. Scorecard KPIs -----------------------------------------------------------------
D = "8 KPIs"
for c, (n, a, b) in enumerate([("355", "original rows", "cross-checked"), ("0", "rows contradicted", "by published data"),
                               ("670", "outside state", "datapoints added"), ("204", "lenders profiled", "102 added"),
                               ("54%", "of all pulls", "landed on Experian"), ("24", "close-call states", "resolved by regression")], start=1):
    cell(D, c, 1, n, a, b, 1.0 if c in (1, 5) else 0.8 if c in (3, 6) else 0.6)

diag = pd.DataFrame(rows)
diag.to_csv(OUT / "story_diagrams.csv", index=False)

# Scorecard bars: share of pulls by bureau, overall and for the busiest lenders -------
p = pd.read_csv(OUT / "pulls_long.csv")
p = p[p.Industry != "Credit Report Resellers & Screening (Not Lenders)"]
short = {"American Express": "American Express", "Citibank (Citi Cards / CBNA)": "Citi",
         "JPMorgan Chase (Chase Card Services)": "Chase", "Bank of America": "Bank of America",
         "U.S. Bank": "U.S. Bank", "Wells Fargo (Card Services)": "Wells Fargo", "Capital One": "Capital One",
         "Synchrony Bank (Amazon, PayPal, Lowe's, Old Navy, HSN, CareCredit and others)": "Synchrony"}
tab = p.groupby(["Lender", "Bureau"]).Datapoints.sum().unstack(fill_value=0)
items = [("All lenders", tab.sum())] + [(short[k], tab.loc[k]) for k in short]
bars = []
for order, (name, s) in enumerate(items, start=1):
    tot = s.sum()
    for b in ["Experian", "Equifax", "TransUnion"]:
        v = s[b] / tot
        lab = f"{round(100 * v)}%"
        bars.append({"Panel": f"% {b.upper()}", "Item": name, "ItemOrder": order, "Part": "Share", "Value": v, "Shade": 1.0,
                     "LabelL": lab if v >= 0.12 else "", "LabelD": "" if v >= 0.12 else lab})
        bars.append({"Panel": f"% {b.upper()}", "Item": name, "ItemOrder": order, "Part": "Rest", "Value": 1 - v, "Shade": 0.08,
                     "LabelL": "", "LabelD": ""})
pd.DataFrame(bars).to_csv(OUT / "scorecard_bars.csv", index=False)

# Regression bars: predicted likelihood in the close-call states ----------------------
st = pd.read_csv(OUT / "regression_state.csv")
c = st[st["Close Call"] == "Yes"].copy()
rank = {"Clear lean": 1, "Moderate lean": 2, "Toss-up": 3, "Thin data (national pattern)": 4}
c["r"] = c["Model Confidence"].map(rank)
c = c.sort_values(["r", "Lead Margin (pts)"], ascending=[True, False]).reset_index(drop=True)
rb = []
shade = {"Experian": 1.0, "Equifax": 0.55, "TransUnion": 0.2}
for i, r in c.iterrows():
    verdict = r["Model Confidence"].replace(" (national pattern)", "")
    for b in ["Experian", "Equifax", "TransUnion"]:
        v = r[f"P_{b}"]
        lab = f"{b[:2].upper() if b != 'TransUnion' else 'TU'} {round(100 * v)}%"
        lab = lab.replace("EX", "EX").replace("EQ", "EQ")
        rb.append({"StateLabel": f"{r.State} ({verdict})", "StateOrder": i + 1, "Bureau": b, "Value": v,
                   "Shade": shade[b], "LabelL": lab if shade[b] >= 0.5 else "", "LabelD": "" if shade[b] >= 0.5 else lab,
                   "Verdict": verdict})
pd.DataFrame(rb).to_csv(OUT / "regression_bars.csv", index=False)
print(diag.groupby("Diagram").size(), len(bars), len(rb))
