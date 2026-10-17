"""Rebuild the Tableau Story "Which Bureau Will They Pull" from the published workbook.

Input:  tableau/source/published_2026-10-08.twbx (downloaded from Tableau Public)
Output: tableau/Client_Personal_and_Business_Funding_Sequence_Dashboard.twbx

What it does
- Adds the cards the story was missing: an introduction (context, purpose, sources, update
  cadence and data limits), market context, two KPI definition cards, where the numbers come
  from (with clickable sources) and a recommendation for each stakeholder.
- Rebuilds the busy diagram cards as clean images (story_images.py) and the close-call card as an
  interactive dashboard: click a state and the side panel shows that state's result.
- Gives each bureau one color everywhere (Experian blue, Equifax orange, TransUnion green), on the
  maps and as bold colored text wherever a bureau is named.
"""
import csv, html, json, re, shutil, sys, uuid, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import story_images as IMG
from titlecase import tc

SRC = ROOT / "tableau" / "source" / "published_2026-10-08.twbx"
OUT = ROOT / "tableau" / "Client_Personal_and_Business_Funding_Sequence_Dashboard.twbx"
WORK = ROOT / "tableau" / "_build"
DT = ROOT / "data" / "tableau"
ASOF = "October 7, 2026"
esc = lambda s: html.escape(str(s), quote=True)

EXP, EQ, TU = IMG.BUREAU["Experian"], IMG.BUREAU["Equifax"], IMG.BUREAU["TransUnion"]
NAVY, BODY, MUTED, LABEL = "#08306b", "#1f2937", "#4a5568", "#2e6ca8"

# ------------------------------------------------------------------ data
db = json.load(open(ROOT / "data" / "db.json"))
ss = [r for r in csv.DictReader(open(DT / "state_summary.csv")) if r["DataSet"] == "All data"]
tot = {b: sum(int(r[b]) for r in ss) for b in ("Experian", "Equifax", "TransUnion")}
TOTAL = sum(tot.values())
st = {r["State"]: r for r in ss}
top_counts = {}
for r in ss:
    top_counts[r["Top Bureau"]] = top_counts.get(r["Top Bureau"], 0) + 1
ties = sum(v for k, v in top_counts.items() if k.startswith("Tie"))
sb = [r for r in csv.DictReader(open(DT / "scorecard_bars.csv")) if r["Part"] == "Share"]
habit = {}
for r in sb:
    b = {"% EXPERIAN": "Experian", "% EQUIFAX": "Equifax", "% TRANSUNION": "TransUnion"}[r["Panel"]]
    habit.setdefault(r["Item"], {})[b] = float(r["Value"])
lenders = list(csv.DictReader(open(DT / "lenders.csv")))
conf = {k: sum(1 for l in lenders if l["Confidence"] == k) for k in ("High", "Medium", "Low")}
lowdoc = sum(1 for l in lenders if l["LowNoDoc"] == "Yes")
reg = json.load(open(DT / "regression_summary.json"))
fit = {f["Model"].split(" (")[0]: f for f in reg["fit"]}
LL_FULL, LL_BASE = fit["Full model"]["CV Log Loss"], fit["National shares only"]["CV Log Loss"]
ACC_FULL, ACC_BASE = fit["Full model"]["CV Accuracy"], fit["National shares only"]["CV Accuracy"]
rs = {r["State"]: r for r in csv.DictReader(open(DT / "regression_state.csv"))}
close_n = sum(1 for r in rs.values() if r["Close Call"] == "Yes")
status_n = {}
for r in rs.values():
    status_n[r["Close Call Status"]] = status_n.get(r["Close Call Status"], 0) + 1
tossups = sorted(r["State"] for r in rs.values() if r["Close Call Status"] == "Toss-up")
cats = {}
for r in db["states"]:
    cats[r["cat"]] = cats.get(r["cat"], 0) + 1
CONF_ROWS, PART_ROWS = cats["Confirmed by state data"], cats["Partly confirmed by state data"]
FIT_ROWS = cats["Fits national pattern"] + cats.get("Partly fits national pattern", 0)
CHECKED = CONF_ROWS + PART_ROWS + FIT_ROWS
pct = lambda a, b: f"{a / b:.0%}"
def share(state, b): return int(st[state][b]) / int(st[state]["Total Datapoints"])
tx = sorted(((share("Texas", b), b) for b in ("Experian", "Equifax", "TransUnion")), reverse=True)
TX_MARGIN = round((tx[0][0] - tx[1][0]) * 100)

CONTEXT_SOURCES = [
    ("myFICO: Do Credit Inquiries Lower Your FICO Score?", "https://www.myfico.com/crediteducation/CreditChecks.aspx", "Undated, read Oct 2026"),
    ("FTC: In FTC Study, Five Percent of Consumers Had Errors on Their Credit Reports", "https://www.ftc.gov/news-events/news/press-releases/2013/02/ftc-study-five-percent-consumers-had-errors-their-credit-reports-could-result-less-favorable-terms", "Feb 2013"),
    ("CFPB: Analysis of Differences between Consumer- and Creditor-Purchased Credit Scores", "https://files.consumerfinance.gov/f/201209_Analysis_Differences_Consumer_Credit.pdf", "Sep 2012"),
]

# ------------------------------------------------------------------ text helpers
def run(text, size=10, color=BODY, bold=False):
    b = " bold='true'" if bold else ""
    return f"<run{b} fontcolor='{color}' fontsize='{int(round(size))}'>{esc(text)}</run>"
NL = "<run>Æ&#10;</run>"
def para(*runs): return "".join(runs)
def labeled(pairs, size=9.5):
    """[(label, text)] -> runs with a bold label and body text, one pair per line."""
    out = []
    for i, (l, t) in enumerate(pairs):
        out.append((NL if i else "") + run(f"{l}: ", size, BODY, True) + run(t, size, BODY))
    return "".join(out)
def box(title, body_runs, title_color=LABEL, size=11):
    return run(title, size, title_color, True) + NL + body_runs

ZID = [100]
def nid(): ZID[0] += 1; return ZID[0]
W, H = 1000, 800                       # every story dashboard is 1000 x 800 px
def geo(x, y, w, h): return f"h='{int(h * 100000 / H)}' w='{int(w * 100000 / W)}' x='{int(x * 100000 / W)}' y='{int(y * 100000 / H)}'"
def zstyle(margin=4, padding=4, bg=None, border=None):
    b = f"<format attr='border-color' value='{border}' /><format attr='border-style' value='solid' /><format attr='border-width' value='1' />" if border else ""
    bgx = f"<format attr='background-color' value='{bg}' />" if bg else ""
    return f"<zone-style>{b}<format attr='margin' value='{margin}' /><format attr='padding' value='{padding}' />{bgx}</zone-style>"
def tzone(x, y, w, h, runs, bg=None, border=None, padding=6):
    return f"<zone forceUpdate='true' {geo(x, y, w, h)} id='{nid()}' type-v2='text'><formatted-text>{runs}</formatted-text>{zstyle(2, padding, bg, border)}</zone>"
def izone(x, y, w, h, img):
    return f"<zone {geo(x, y, w, h)} id='{nid()}' is-scaled='1' param='Image/{img}' type-v2='bitmap'>{zstyle(0, 0)}</zone>"
def szone(x, y, w, h, sheet, title=False):
    return f"<zone {geo(x, y, w, h)} id='{nid()}' name='{esc(sheet)}' show-title='{'true' if title else 'false'}'>{zstyle(2, 2)}</zone>"
def header(title, sub, h=78):
    return tzone(20, 6, 960, h, run(tc(title), 20, NAVY, True) + NL + run(sub, 10, MUTED))
def dashboard(name, zones):
    return (f"<dashboard enable-sort-zone-taborder='true' name='{esc(name)}'><style /><size maxheight='{H}' maxwidth='{W}' minheight='{H}' minwidth='{W}' />"
            f"<zones><zone h='100000' id='{nid()}' type-v2='layout-basic' w='100000' x='0' y='0'>{''.join(zones)}"
            f"<zone-style><format attr='background-color' value='#ffffff' /></zone-style></zone></zones>"
            f"<simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' /></dashboard>")

# ------------------------------------------------------------------ images (pixel sizes match their zones)
IMG.OUT = WORK / "Image"
if WORK.exists(): shutil.rmtree(WORK)
(WORK / "Image").mkdir(parents=True)
I = {}
I["roadmap"] = IMG.roadmap(370, 700, [
    ("POINT 1", "Introduction", "Context, purpose, sources and limits", "#08306B"),
    ("POINT 2", "Who It Serves", "Stakeholders, scope and key terms", "#08306B"),
    ("POINTS 3 TO 5", "Context and KPIs", "Market context, then ten KPIs with formulas", "#2E6CA8"),
    ("POINT 6", "Data and Method", "355 rows checked against 670 datapoints", "#2E6CA8"),
    ("POINTS 7 TO 10", "The Maps", "Lender map, then Experian, Equifax and TransUnion shares", EXP),
    ("POINT 11", "Close Calls", "Click a state for the model's best forecast", "#5B3FA8"),
    ("POINTS 12 AND 13", "Your Moves", "Decision tree and the funding ladder", "#5B3FA8"),
    ("POINT 14", "Scorecard", "Headline numbers and each issuer's habit", "#4A5568"),
    ("POINTS 15 AND 16", "Check and Decide", "Every source, then a move for each stakeholder", "#4A5568"),
])
I["stake"] = IMG.stakeholders(960, 200,
    [("Personal credit clients", "Apply where their strongest report gets pulled."),
     ("Business credit clients", "Many business cards still check the owner's personal report."),
     ("Credit consulting companies", "Plan disputes and space out inquiries by bureau."),
     ("Business funding companies", "Line up approvals without piling inquiries on one report.")],
    [("Funding advisors and brokers", "Look up the likely bureau before each client applies."),
     ("Analysts and reviewers", "Trace every number back to its source."),
     ("Lenders and partners", "Receive applications from people who fit."),
     ("Everyone", "A planning guide, not financial advice.")])
I["scope"] = IMG.scope(960, 250,
    [("Which bureau a lender pulls", "Experian, Equifax and TransUnion, in every state and Washington, DC."),
     ("Personal and business funding", "Cards, lines, loans, SBA, auto, equipment and real estate."),
     ("Facts about each lender", f"Funding type, typical score and paperwork level for 204 lenders ({lowdoc} low or no doc)."),
     ("A funding sequence", "An application order for seven score ranges, 500-549 to 800+.")],
    [("Approval odds", "It does not predict whether anyone will be approved."),
     ("Business credit bureaus", "Business files such as D&B are not mapped by state."),
     ("Soft pulls and live rates", "Prequalification checks and current rates are left out."),
     ("Advice", "Nothing here is legal, tax or financial advice.")])
I["market"] = IMG.market_chart(540, 360, {b: (tot[b], tot[b] / TOTAL) for b in ("Experian", "Equifax", "TransUnion")},
    [("Experian", top_counts.get("Experian", 0), EXP), ("Equifax", top_counts.get("Equifax", 0), EQ),
     ("TransUnion", top_counts.get("TransUnion", 0), TU), ("Ties", ties, "#9AA3B2")], TOTAL)
I["facts"] = IMG.fact_tiles(410, 360, [
    ("<5 pts", "What one more hard inquiry usually takes off a FICO Score. It counts for a year and stays on the report for two.", "myFICO"),
    ("1 in 5", "consumers had an error on at least one of their three credit reports.", "FTC, Feb 2013"),
    ("Up to 27%", "of consumers land in a different credit-quality category depending on which score is used.", "CFPB, Sep 2012"),
    ("0", "lenders in this database publish which bureau they pull by state, so every datapoint is consumer-reported.", "This database, Oct 2026"),
])
I["kpi1"] = IMG.kpi_tiles(960, 118, "KPIs 1 to 5 at a Glance", "Shares, margins, close calls and issuer habits", [
    ("KPI 1", f"{share('Florida', 'Experian'):.0%}", "Experian share in Florida", EXP),
    ("KPI 2", f"{tot['Experian'] / TOTAL:.0%}", "Experian share of all recorded pulls", EXP),
    ("KPI 3", f"{TX_MARGIN} pts", "Experian's lead in Texas", NAVY),
    ("KPI 4", f"{close_n}", "close-call states out of 49", NAVY),
    ("KPI 5", f"{habit['American Express']['Experian']:.0%}", "American Express pulls on Experian", EXP)], "info_kpi1")
I["kpi2"] = IMG.kpi_tiles(960, 118, "KPIs 6 to 10 at a Glance", "The model and the evidence behind it", [
    ("KPI 6", f"{float(rs['Alabama']['P_Experian']):.0%}", "chance of Experian in Alabama", EXP),
    ("KPI 7", f"{float(rs['Connecticut']['Leader Holds in Resamples']):.0%}", "of refits keep Connecticut's leader", NAVY),
    ("KPI 8", f"{1 - LL_FULL / LL_BASE:.0%}", "lower error than national shares", NAVY),
    ("KPI 9", "0", f"rows contradicted, of {CHECKED} checked", NAVY),
    ("KPI 10", f"{conf['High']}", "lenders with High confidence", NAVY)], "info_kpi2")
I["enrich"] = IMG.flow(960, 150, "From One Table to a Checked Database", [
    ("1. ORIGINAL TABLE", [("rows", "355"), ("states", "16"), ("columns", "State, Bank and three bureau marks")]),
    ("2. CLEAN AND MATCH", [("spellings", "229"), ("lenders", "102"), ("unknown", "11 kept and labeled")]),
    ("3. ENRICH", [("added", "funding type"), ("added", "score needed"), ("added", "paperwork level")]),
    ("4. CROSS-CHECK", [("datapoints", "670"), ("sources", "56"), ("years", "2008 to 2026")]),
    ("5. RESULT", [("confirmed", f"{CONF_ROWS} (+{PART_ROWS} partly)"), ("national fit", f"{FIT_ROWS}"), ("contradicted", "0")]),
], "info_enrich", result_head="#2E6CA8")
I["etl"] = IMG.flow(960, 172, "How It Was Built: Extract, Transform, Load", [
    ("1. EXTRACT", [("read", "original workbook, All States & Banks tab"), ("read", "issuer state tables, 2008 to 2017"), ("read", "myFICO grid (2023) and 2025-2026 posts"), ("read", "lender pages for scores and rules")]),
    ("2. TRANSFORM", [("match", "229 spellings to 102 lenders"), ("normalize", "x, blanks, counts to pulled or not"), ("join", "each row to outside data by lender and state"), ("reshape", "one row per state, lender and bureau")]),
    ("3. LOAD", [("excel", "six-tab workbook with live totals"), ("web", "seven-page site on GitHub Pages"), ("tableau", "maps, regression and this story"), ("model", "weighted datapoints for the regression")]),
], "info_etl")
I["equation"] = IMG.equation(960, 290, [
    ("Utah", "Experian", 4, 7, {b: int(st["Utah"][b]) for b in ("Experian", "Equifax", "TransUnion")}, "Only 7 pulls, so treat it as a hint."),
    ("Florida", "Experian", 466, 885, {b: int(st["Florida"][b]) for b in ("Experian", "Equifax", "TransUnion")}, "885 pulls make this very reliable."),
    ("Georgia", "TransUnion", 37, 116, {b: int(st["Georgia"][b]) for b in ("Experian", "Equifax", "TransUnion")}, "About 1 in 3 Georgia pulls landed on TransUnion."),
])
whatif = [r for r in csv.DictReader(open(DT / "regression_lender_state.csv"))] if (DT / "regression_lender_state.csv").exists() else []
I["tree"] = IMG.decision_tree(960, 392, [
    ("Experian", "pulled most often, so most lenders will see it",
     "favor Experian-first issuers", [("Amex", f"{habit['American Express']['Experian']:.0%} Experian"), ("BofA", f"{habit['Bank of America']['Experian']:.0%} Experian")]),
    ("Equifax", "few lenders lead with Equifax, so choose on purpose",
     "favor Citi and Chase", [("Citi", f"{habit['Citi']['Equifax']:.0%} Equifax"), ("Chase", f"{habit['Chase']['Equifax']:.0%} Equifax")]),
    ("TransUnion", f"least-pulled bureau overall, about {tot['TransUnion'] / TOTAL:.0%}",
     "favor TransUnion-first issuers", [("Synchrony", f"{habit['Synchrony']['TransUnion']:.0%} TransUnion"), ("U.S. Bank", f"{habit['U.S. Bank']['TransUnion']:.0%} TransUnion")]),
], [("you live in a close-call state", "check the Close Calls card (point 11) first"),
    ("your score is under 650", "start on the lower steps of the funding ladder"),
    ("one report already has new inquiries", "switch to issuers that pull a different bureau")])
I["whatif"] = IMG.whatif_table(960, 250, [
    ("American Express in Kansas", "Experian", {"Experian": .84, "Equifax": .05, "TransUnion": .11}, "Amex picks Experian almost everywhere, even in a toss-up state."),
    ("Chase in Florida", "Experian", {"Experian": .43, "Equifax": .37, "TransUnion": .21}, "Florida has 189 Chase datapoints, and Equifax is a close second."),
    ("Capital One in Virginia", "Equifax", {"Experian": .29, "Equifax": .45, "TransUnion": .26}, "Capital One leans Equifax here, but only 3 datapoints back it up."),
    ("Synchrony in Ohio", "TransUnion", {"Experian": .26, "Equifax": .09, "TransUnion": .65}, "Synchrony is a rare lender that leads with TransUnion."),
])
I["ladder"] = IMG.ladder(960, 410, [
    ("500-549", "Repair first", "Fix errors, then use a builder loan."), ("550-599", "Start small", "Prequalify, then open a starter card."),
    ("600-649", "Go unsecured", "Add mainstream cards and a low-doc line."), ("650-699", "Enter the majors", "Apply to Chase first, then to Amex."),
    ("700-749", "Build the stack", "Open 0% business cards over six rounds."), ("750-799", "Add the banks", "Add bank lines and SBA loans."),
    ("800+", "Go biggest first", "Lead with the largest bank facilities.")])
order = ["All lenders", "American Express", "Bank of America", "Citi", "Chase", "Wells Fargo", "Capital One", "Synchrony", "U.S. Bank"]
order = ["All lenders"] + sorted(order[1:], key=lambda k: -habit[k]["Experian"])
I["score"] = IMG.scorecard(960, 500, [
    ("355", "original rows, every one cross-checked", NAVY), ("0", "rows contradicted by published data", NAVY),
    ("670", "outside datapoints added state by state", NAVY), ("204", "lenders profiled, 102 newly added", NAVY),
    (f"{tot['Experian'] / TOTAL:.0%}", "of all recorded pulls landed on Experian", EXP), (f"{close_n}", "close-call states sorted out by the model", NAVY)],
    [(k, habit[k]) for k in order])
I["pipe"] = IMG.pipeline(960, 108, [
    ("SOURCES", "56 cited sources plus the original 355-row table"), ("CLEAN", "Python matches names and normalizes marks"),
    ("CHECK", "every row compared with outside data"), ("MODEL", "regression with cross-validation and 150 refits"),
    ("PUBLISH", "Excel, website, Tableau and the deck read the same files")])
I["groups"] = IMG.bureau_groups(475, 230, [
    ("Experian", ["Chase", "Amex", "Wells Fargo", "Bank of America", "PNC, TD, FNBO"]),
    ("Equifax", ["Truist", "Citizens", "PenFed", "Huntington", "KeyBank, DCU"]),
    ("TransUnion", ["U.S. Bank", "Barclays", "Synchrony", "Navy Federal", "Elan"]),
    ("All three", ["Capital One", "apply last"])])

# ------------------------------------------------------------------ dashboards
D = {}
D["1 Introduction"] = dashboard("1 Introduction", [
    header("Introduction: Context, Purpose, Sources and Limits", f"Lender patterns as of {ASOF}. Use the arrows or the cards above to move through the story."),
    tzone(20, 88, 585, 168, box("Context", para(run(
        "Every hard inquiry lands on one of three credit reports: Experian, Equifax or TransUnion. The same person can have a strong report at one "
        "bureau and a weaker one at another, and lenders do not publish which bureau they pull or how that changes by state. One more inquiry usually "
        "costs less than five points and counts for a year (myFICO), but several on the same report add up, and one in five consumers has an error on "
        "at least one report (FTC).", 9.5)))),
    tzone(20, 258, 585, 168, box("Purpose", labeled([
        ("The question", "Which bureau is a lender most likely to pull in a given state, and in what order should a client apply so approvals stack up without piling inquiries on one report?"),
        ("What you get", "16 numbered cards that move from context to a decision: who this serves, market context, ten KPIs with formulas, the data method, "
                         "four maps, a close-call explorer, a decision tree, the funding ladder, a scorecard, every source and a move for each stakeholder.")]))),
    tzone(20, 428, 585, 182, box("Where the Data Comes From and How It Is Updated", labeled([
        ("Sources", "A 355-row inquiry table from 16 states plus 670 outside state datapoints from 56 cited sources: Doctor of Credit issuer tables (2008 to 2019), "
                    "the myFICO Forums state grid (July 2023) and 2025 to 2026 forum posts, MyBankTracker, CardRight, StackEasy, and lender and review pages for minimum scores."),
        ("As of", f"Research completed {ASOF}."),
        ("Updates", "Lender minimums are reviewed every quarter. Each new inquiry datapoint reruns the cleaning, maps and regression from the same scripts.")]))),
    tzone(20, 612, 585, 182, box("Data Limits", labeled([
        ("Consumer-reported", "No lender publishes its bureau by state, so every datapoint is someone's reported inquiry."),
        ("Uneven in age", "The largest tables cover 2008 to 2016; the newest datapoints are from 2025 and 2026."),
        ("Thin states", "Some states rest on fewer than 10 pulls, so their colors are hints, not findings."),
        ("Estimates, not promises", "Minimum scores are published floors or community estimates; income, utilization and recent inquiries decide approvals as much as the score. Not financial advice.")]))),
    izone(615, 92, 370, 700, "info_roadmap.png"),
])
D["2 Who It Serves"] = dashboard("2 Who It Serves", [
    header("Who It Serves, What It Covers and Key Terms", "Four primary stakeholders, four who benefit, and what this story does and does not answer."),
    izone(20, 86, 960, 200, "info_stakeholders.png"),
    izone(20, 294, 960, 250, "info_scope.png"),
    tzone(20, 552, 960, 242, box("Key Terms", labeled([
        ("Bureau (credit reporting agency)", "Experian, Equifax or TransUnion; each keeps one of your three credit reports."),
        ("Hard inquiry (hard pull)", "a lender's check of one report when you apply; it can lower a score slightly. A soft pull, such as prequalification, does not."),
        ("Choropleth map", "a map that colors each state by a number. Regression: a model that weighs several factors at once to estimate an outcome."),
        ("Close call", "a state where the top two bureaus are within 20 points. Low doc / no doc: applications that skip tax returns up front."),
        ("SBA / CDFI", "Small Business Administration / Community Development Financial Institution, a mission lender for underserved borrowers.")], 9))),
])
D["3 Market Context"] = dashboard("3 Market Context", [
    header("Market Context: Three Reports, One Pull", f"{TOTAL:,} recorded bureau pulls, all lenders combined, as of {ASOF}."),
    izone(20, 86, 540, 360, "info_market.png"),
    izone(575, 86, 410, 360, "info_facts.png"),
    tzone(20, 456, 960, 338, box("What This Means", labeled([
        ("One bureau dominates", f"Experian received {tot['Experian'] / TOTAL:.0%} of recorded pulls and leads {top_counts.get('Experian', 0)} of 49 states with data, so most applications will see the Experian report."),
        ("But not everywhere", f"Equifax leads {top_counts.get('Equifax', 0)} states and TransUnion {top_counts.get('TransUnion', 0)}; {ties} more are ties. Issuers also have habits: Synchrony lands on TransUnion {habit['Synchrony']['TransUnion']:.0%} of the time."),
        ("Why it costs money", "Every misplaced application spends an inquiry on the wrong report, and errors or thin files on that report can mean a decline or a higher rate."),
        ("Sources", "myFICO, Do Credit Inquiries Lower Your FICO Score?; FTC, In FTC Study, Five Percent of Consumers Had Errors on Their Credit Reports (Feb 2013); "
                    "CFPB, Analysis of Differences between Consumer- and Creditor-Purchased Credit Scores (Sep 2012); this database. Links are on point 15.")]))),
])
def kpi_runs(items):
    out = []
    for i, (n, name, tells, formula, ex) in enumerate(items):
        out.append(tzone(20 + (i % 2) * 485, 210 + (i // 2) * 196, 475, 190,
                         box(f"KPI {n}. {tc(name)}", labeled([("What it tells you", tells), ("Formula", formula), ("Example", ex)], 9.5))))
    return out
K1 = [(1, "Bureau share of pulls", "how likely a pull in one state is to land on one bureau, all lenders combined.",
       "pulls on one bureau in a state ÷ all bureau pulls in that state.", f"Florida, Experian: 466 ÷ 885 = {466 / 885:.0%}."),
      (2, "National share of pulls", "which bureau lenders use most across the country.",
       f"one bureau's pulls ÷ all {TOTAL:,} recorded pulls.", f"Experian {tot['Experian']:,} ÷ {TOTAL:,} = {tot['Experian'] / TOTAL:.0%}; Equifax {tot['Equifax'] / TOTAL:.0%}; TransUnion {tot['TransUnion'] / TOTAL:.0%}."),
      (3, "Lead margin", "how far the top bureau is ahead in a state.",
       "top bureau share − second bureau share, in percentage points.", f"Texas: Experian {tx[0][0]:.0%} − {tx[1][1]} {tx[1][0]:.0%} = {TX_MARGIN} points."),
      (4, "Close call", "where the map alone cannot decide.",
       "a state whose lead margin is under 20 points in the recorded pulls.", f"{close_n} of 49 states. In Alabama, Experian and Equifax are tied at {share('Alabama', 'Experian'):.0%} (0 points)."),
      (5, "Issuer bureau habit", "how predictable one lender is.",
       "an issuer's pulls on one bureau ÷ that issuer's recorded pulls.",
       f"American Express {habit['American Express']['Experian']:.0%} Experian; Synchrony {habit['Synchrony']['TransUnion']:.0%} TransUnion; Capital One splits {habit['Capital One']['Experian']:.0%} / {habit['Capital One']['Equifax']:.0%} / {habit['Capital One']['TransUnion']:.0%}.")]
K2 = [(6, "Predicted likelihood", "the chance each bureau is pulled for a typical application, after weighing state, lender and data era together.",
       "multinomial logistic regression probability; the three chances add up to 100%.",
       f"Alabama: Experian {float(rs['Alabama']['P_Experian']):.0%}, Equifax {float(rs['Alabama']['P_Equifax']):.0%}, TransUnion {float(rs['Alabama']['P_TransUnion']):.0%}."),
      (7, "Leader stability", "how sure the model is about the top bureau.",
       "refits (out of 150) where the same bureau stays on top; at least 90% is a clear lean, at least 70% a moderate lean.",
       f"Connecticut {float(rs['Connecticut']['Leader Holds in Resamples']):.0%} (clear lean); Alabama {float(rs['Alabama']['Leader Holds in Resamples']):.0%} (moderate lean)."),
      (8, "Model lift", "how much better the model is than national shares alone.",
       "1 − (model log loss ÷ baseline log loss), from 5-fold cross-validation.",
       f"1 − ({LL_FULL:.3f} ÷ {LL_BASE:.3f}) = {1 - LL_FULL / LL_BASE:.0%} lower error; accuracy {ACC_FULL:.0%} versus {ACC_BASE:.0%}."),
      (9, "Cross-check result", "how much of the original table outside data supports.",
       "rows confirmed, partly confirmed or fitting the national pattern ÷ rows that had outside data to check.",
       f"{CHECKED} of 355 rows could be checked ({CONF_ROWS} + {PART_ROWS} + {FIT_ROWS}), and 0 were contradicted."),
      (10, "Lender confidence mix", "how much evidence stands behind each lender profile.",
       "lenders at each confidence level ÷ 204 lenders.",
       f"{conf['High']} High ({conf['High'] / 204:.0%}), {conf['Medium']} Medium ({conf['Medium'] / 204:.0%}), {conf['Low']} Low ({conf['Low'] / 204:.0%}).")]
D["4 KPIs"] = dashboard("4 KPIs", [header("KPI (Key Performance Indicator) Definitions, Part 1: Shares and Close Calls", f"Each formula is worked with the {ASOF} numbers."),
                                   izone(20, 86, 960, 118, "info_kpi1.png")] + kpi_runs(K1))
D["5 KPIs 2"] = dashboard("5 KPIs 2", [header("KPI Definitions, Part 2: The Model and the Evidence", f"Each formula is worked with the {ASOF} numbers."),
                                       izone(20, 86, 960, 118, "info_kpi2.png")] + kpi_runs(K2))
D["6 Data and Method"] = dashboard("6 Data and Method", [
    header("Where the Data Came From", "355 inquiries, cleaned, enriched and checked against 670 datapoints from 56 sources. Read each row left to right."),
    izone(20, 88, 960, 150, "info_enrich.png"),
    izone(20, 246, 960, 172, "info_etl.png"),
    tzone(20, 428, 960, 366, box("Messy Data That Was Cleaned", labeled([
        ("One lender, many spellings", '"Capital One", "Capital One Bank USA" and "Capital One NA" are the same company, so 229 spellings were matched to 102 lenders.'),
        ("Mixed markers", "bureau columns held x marks, blanks, zeros and counts as high as 211, so each became pulled or not pulled, with counts kept as weights."),
        ("Look-alikes", "early rules confused USAA with Apple, so the rules were reordered and every match was checked by hand."),
        ("Unknowns kept", "11 names could not be identified; they are labeled instead of being forced into a match."),
        ("Non-lenders", "mortgage report resellers and tenant screeners were tagged so they do not count as lender pulls.")], 10.5))),
])
D["8 Reading the Maps"] = dashboard("8 Reading the Maps", [
    header("How to Read a Share Map", "A share is a part out of a whole. Each map uses its bureau's color; darker means a bigger share."),
    izone(20, 90, 960, 290, "info_equation.png"),
    tzone(20, 390, 960, 404, box("Three Things to Watch For", labeled([
        ("1. Small samples", "a percentage built on 7 pulls can swing a lot when one new datapoint arrives, while one built on 885 pulls barely moves. Hover over a state to see how many pulls are behind its color."),
        ("2. All lenders are mixed together", "American Express and Chase have the most datapoints, and Amex almost always pulls Experian, so the maps lean toward Experian overall."),
        ("3. Different years", "the datapoints run from 2008 to 2026, and a lender can change its bureau over time, so newer datapoints are worth more when you plan."),
        ("The three shares", "Experian, Equifax and TransUnion shares in a state always add up to about 100%.")], 10.5))),
])
D["11 Close Calls"] = dashboard("11 Close Calls", [
    header("Close Calls: Pick a State to See the Model's Best Forecast",
           f"In {close_n} states the top two bureaus are within 20 points. Click any state to see the chance of each bureau."),
    szone(20, 88, 600, 706, "CC Map"),
    tzone(632, 88, 348, 40, run("Click a state; click it again to see all states.", 10, LABEL, True), bg="#f3f6fb", padding=6),
    szone(632, 132, 348, 214, "CC State Panel"),
    szone(632, 350, 348, 196, "CC Chance Bars"),
    f"<zone {geo(632, 552, 348, 104)} id='{nid()}' name='CC Map' pane-specification-id='0' param='[federated.1cc5tate0ab1cd2ef3gh4ij5kl6m].[none:Close Call Status:nk]' type-v2='color'>{zstyle(2, 2)}</zone>",
    tzone(632, 660, 348, 134, box("How the Model Works", para(run(
        f"A multinomial logistic regression on 2,901 datapoints from 862 reports weighs state, lender and data era at once. It is right {ACC_FULL:.0%} of the time "
        f"versus {ACC_BASE:.0%} for national shares alone, and it is refit 150 times to test how stable each leader is (KPIs 6 to 8).", 9)), size=10)),
])
D["12 Decision Tree"] = dashboard("12 Decision Tree", [
    header("Decision Tree: If / Then Moves From Your Strongest Report",
           "Start with your strongest report and follow its branch. The table shows four real cases from the regression."),
    izone(20, 88, 960, 392, "info_tree.png"),
    izone(20, 486, 960, 250, "info_whatif.png"),
    tzone(20, 742, 960, 52, run("Sources: issuer habits are KPI 5 (share of each issuer's recorded pulls); the what-if chances are KPI 6 (regression, typical application). Not financial advice.", 9, MUTED)),
])
D["13 Funding Ladder"] = dashboard("13 Funding Ladder", [
    header("The Funding Ladder: One Step at a Time", "Each step is a score range. Finish the move on your step, let the score rise, then climb."),
    izone(20, 88, 960, 410, "info_ladder.png"),
    tzone(20, 506, 960, 288, box("Four Rules for Climbing Safely", labeled([
        ("1. Spread applications across bureaus", "every hard inquiry lands on one report. Mix Experian-, Equifax- and TransUnion-leaning lenders so no single report fills up."),
        ("2. Apply to the strictest lender first", "Chase (5/24), then Amex, then U.S. Bank, Wells Fargo, Bank of America and regionals. Capital One goes last because it checks all three."),
        ("3. Use soft pulls before hard pulls", "prequalification does not hurt the score. Apply for real only when the offer looks good."),
        ("4. The 700 to 749 step is where stacking starts", "opening several 0% business cards in planned rounds makes sense here. Below it, build history first.")]))),
])
D["14 Scorecard"] = dashboard("14 Scorecard", [
    header("Scorecard: What the Data Adds Up To", "Six headline numbers, then each big issuer's bureau habit."),
    izone(20, 86, 960, 500, "info_scorecard.png"),
    tzone(20, 594, 960, 200, box("Reading the Scorecard", labeled([
        ("Predictable issuers", f"American Express sent {habit['American Express']['Experian']:.0%} of its recorded pulls to Experian; Synchrony sent {habit['Synchrony']['TransUnion']:.0%} to TransUnion."),
        ("Plan for any bureau", f"Capital One splits its pulls ({habit['Capital One']['Experian']:.0%} Experian, {habit['Capital One']['Equifax']:.0%} Equifax, {habit['Capital One']['TransUnion']:.0%} TransUnion), so any report could be checked."),
        ("How sure are we", f"Of 204 lenders, {conf['High']} have High confidence, {conf['Medium']} Medium and {conf['Low']} Low (KPI 10)."),
        ("What this cannot tell you", "the data is consumer-reported from 2008 to 2026, so a lender can change its habits at any time. Treat every number as a likelihood, not a rule.")], 9.5))),
])
SRC_TEXT = [
    ("Points 1 to 3", "Counts from the workbook; context facts from myFICO, the FTC and the CFPB; market shares = bureau pulls ÷ all recorded pulls (horizontal bar chart)."),
    ("Points 4 and 5", "Every KPI formula is worked on the card with the numbers as of " + ASOF + "."),
    ("Point 6", "Row counts from the cross-check columns of the All States & Banks tab."),
    ("Points 7 to 10", "Filled (choropleth) maps: bureau pulls ÷ all pulls in each state; the lender map shows each lender's most-pulled bureau. One color per bureau."),
    ("Point 11", "Multinomial logistic regression with 5-fold cross-validation (whole reports held out) and 150 refits for stability."),
    ("Points 12 to 14", "Issuer habits (KPI 5), regression what-ifs (KPI 6), and a 57-step sequence built from lender minimums and application rules."),
    ("Refresh", "Lender minimums are reviewed every quarter; a new datapoint reruns every step from the same scripts."),
]
D["15 Number Sources"] = dashboard("15 Number Sources", [
    header("Where the Numbers Come From", f"As of {ASOF}. Click a source name on the right to open it."),
    izone(20, 84, 960, 108, "info_pipe.png"),
    tzone(20, 200, 600, 400, box("How Each Card Is Calculated", labeled(SRC_TEXT, 10.5))),
    szone(632, 200, 348, 594, "Sources List", title=True),
])
REC = [("A. Personal credit clients", [
            ("Best move", "pull all three reports first, then apply with lenders that pull your strongest report in your state."),
            ("Choose this when", "one report is clearly stronger or cleaner than the other two."),
            ("Why", f"Experian gets {tot['Experian'] / TOTAL:.0%} of pulls, but issuers have habits: American Express lands on Experian {habit['American Express']['Experian']:.0%} of the time, Synchrony on TransUnion {habit['Synchrony']['TransUnion']:.0%}."),
            ("Next move", "check your lender on the map at point 7 and prequalify before any hard inquiry.")]),
       ("B. Business credit clients", [
            ("Best move", "treat business card applications as personal inquiries; most check the owner's personal report."),
            ("Choose this when", "you apply for business cards or lines as an owner of a small company."),
            ("Why", "Capital One checks all three bureaus and most of its business cards report to personal credit."),
            ("Next move", f"build the business file in parallel (entity, EIN, D-U-N-S, business checking, 3 to 5 net-30 vendors) and review the {lowdoc} low or no doc lenders.")]),
       ("C. Credit consulting companies", [
            ("Best move", "plan disputes and inquiry spacing bureau by bureau."),
            ("Choose this when", "a client's three reports disagree or carry errors."),
            ("Why", "one in five consumers has an error on at least one report (FTC), and each inquiry counts for a year (myFICO)."),
            ("Next move", "clean the report the client's target lenders pull first, then schedule applications after the fix posts.")]),
       ("D. Business funding companies", [
            ("Best move", "stack in strictest-rule order and spread each round across bureau groups."),
            ("Choose this when", "a client is at 700 or higher and ready for a multi-card or line stack."),
            ("Why", "Chase (5/24) first, then Amex, U.S. Bank, Wells Fargo, Bank of America and regionals; Capital One last because it hits all three."),
            ("Next move", "use the funding ladder (point 13) for the client's step and one lender from each group per round.")]),
       ("E. Funding advisors and brokers", [
            ("Best move", "run the close-call check before advising a client in one of the close-call states."),
            ("Choose this when", f"the client lives in one of the {close_n} close-call states."),
            ("Why", f"Experian is the best forecast in all {close_n}, but only {status_n.get('Clear lean', 0)} are clear leans; {len(tossups)} are toss-ups ({', '.join(tossups[:-1])} and {tossups[-1]})."),
            ("Next move", "in toss-up states, plan for any of the three bureaus and keep inquiries spread.")])]
REC_COL = ["#08306B", "#08306B", "#2E6CA8", "#2E6CA8", "#5B3FA8"]
rz = []
for i, ((t, rows), c) in enumerate(zip(REC, REC_COL)):
    x = 20 if i < 3 else 505
    y = 86 + (i if i < 3 else i - 3) * 236
    rz.append(tzone(x, y, 475, 230, box(t, labeled(rows, 9.5), title_color=c, size=12)))
D["16 Recommendations"] = dashboard("16 Recommendations", [
    header("Recommendations: The Best Move for Each Stakeholder", "Find your type, then read its best move. Every number traces back to a KPI or an earlier card.")] + rz +
    [izone(505, 562, 475, 230, "info_groups.png")])

# ------------------------------------------------------------------ worksheets and datasources for the interactive and source cards
from tableauhyperapi import HyperProcess, Telemetry, Connection, CreateMode, TableDefinition, SqlType, TableName, Inserter
def hyper(fname, cols, rows):
    p = WORK / "Data" / "Extracts" / fname
    p.parent.mkdir(parents=True, exist_ok=True)
    stp = {"string": SqlType.text(), "integer": SqlType.big_int(), "real": SqlType.double()}
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hp:
        with Connection(hp.endpoint, str(p), CreateMode.CREATE_AND_REPLACE) as cx:
            cx.catalog.create_schema("Extract")
            td = TableDefinition(TableName("Extract", "Extract"), [TableDefinition.Column(c, stp[t]) for c, t in cols])
            cx.catalog.create_table(td)
            cv = {"string": lambda v: v, "integer": lambda v: int(float(v)) if v not in ("", None) else None, "real": lambda v: float(v) if v not in ("", None) else None}
            with Inserter(cx, td) as ins:
                ins.add_rows([[cv[t](r[c]) for c, t in cols] for r in rows]); ins.execute()

def datasource(key, caption, fname, cols, rows, extra_cols="", dsname=None):
    (WORK / "Data" / "data").mkdir(parents=True, exist_ok=True)
    with open(WORK / "Data" / "data" / fname, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=[c for c, _ in cols]); w.writeheader(); [w.writerow({c: r[c] for c, _ in cols}) for r in rows]
    hyp = fname.replace(".csv", ".hyper"); hyper(hyp, cols, rows)
    tcode = {"string": 129, "integer": 20, "real": 5}
    oid = f"{fname}_{uuid.uuid4().hex.upper()}"
    colxml = "".join(f"<column datatype='{t}' name='{esc(c)}' ordinal='{i}' />" for i, (c, t) in enumerate(cols))
    fam = fname.replace(".csv", "#csv")
    rel = f"<relation connection='textscan.{key}' name='{fname}' table='[{fam}]' type='table'><columns character-set='UTF-8' header='yes' locale='en_US' separator=','>{colxml}</columns></relation>"
    def rec(c, t, i, ext):
        coll = "<collation flag='0' name='LEN_RUS' />" if t == "string" else ""
        if ext:
            return (f"<metadata-record class='column'><remote-name>{esc(c)}</remote-name><remote-type>{tcode[t]}</remote-type><local-name>[{esc(c)}]</local-name>"
                    f"<parent-name>[Extract]</parent-name><remote-alias>{esc(c)}</remote-alias><ordinal>{i}</ordinal><family>{fname}</family><local-type>{t}</local-type>"
                    f"<aggregation>{'Count' if t == 'string' else 'Sum'}</aggregation><approx-count>{len(rows)}</approx-count><contains-null>true</contains-null>{coll}<object-id>[{oid}]</object-id></metadata-record>")
        return (f"<metadata-record class='column'><remote-name>{esc(c)}</remote-name><remote-type>{tcode[t]}</remote-type><local-name>[{esc(c)}]</local-name>"
                f"<parent-name>[{fname}]</parent-name><remote-alias>{esc(c)}</remote-alias><ordinal>{i}</ordinal><local-type>{t}</local-type>"
                f"<aggregation>{'Count' if t == 'string' else 'Sum'}</aggregation>{'<scale>1</scale><width>1073741823</width>' if t == 'string' else ''}<contains-null>true</contains-null>{coll}<object-id>[{oid}]</object-id></metadata-record>")
    meta = "".join(rec(c, t, i, False) for i, (c, t) in enumerate(cols))
    emeta = "".join(rec(c, t, i, True) for i, (c, t) in enumerate(cols))
    fields = ""
    for c, t in cols:
        if t == "string":
            sem = " semantic-role='[State].[Name]'" if c == "State" else ""
            fields += f"<column datatype='string' name='[{esc(c)}]' role='dimension'{sem} type='nominal' />"
        else:
            fmt = " default-format='p0%'" if c in ("Predicted Likelihood", "Observed Share", "Leader Holds in Resamples") else ""
            fields += f"<column datatype='{t}'{fmt} name='[{esc(c)}]' role='measure' type='quantitative' />"
    fields += f"<column caption='{fname}' datatype='table' name='[__tableau_internal_object_id__].[{oid}]' role='measure' type='quantitative' />"
    extract = (f"<extract count='-1' enabled='true' object-id='{oid}' units='records' user-specific='false'><connection authentication='auth-none' author-locale='en_US' class='hyper' "
               f"dbname='Data/Extracts/{hyp}' default-settings='yes' schema='Extract' tablename='Extract' update-time='10/17/2026 06:30:00 AM'>"
               f"<relation name='Extract' table='[Extract].[Extract]' type='table' /><refresh><refresh-event add-from-file-path='{caption}' increment-value='%null%' "
               f"refresh-type='create' rows-inserted='{len(rows)}' timestamp-start='2026-10-17 06:30:00.000' /></refresh>"
               f"<metadata-records>{emeta}</metadata-records></connection></extract>")
    graph = (f"<object-graph><objects><object caption='{fname}' id='{oid}'><properties context=''>{rel}</properties>"
             f"<properties context='extract'><relation name='Extract' table='[Extract].[Extract]' type='table' /></properties></object></objects></object-graph>")
    return (f"<datasource caption='{esc(caption)}' inline='true' name='{dsname or 'federated.' + key}' version='18.1'><connection class='federated'><named-connections>"
            f"<named-connection caption='{esc(caption)}' name='textscan.{key}'><connection class='textscan' directory='Data/data' /></named-connection>"
            f"</named-connections>{rel}<metadata-records>{meta}</metadata-records></connection><aliases enabled='yes' />{fields}{extra_cols}{extract}"
            f"<layout dim-ordering='alphabetic' measure-ordering='alphabetic' show-structure='true' />"
            f"<semantic-values><semantic-value key='[Country].[Name]' value='&quot;United States&quot;' /></semantic-values>{graph}</datasource>")

cc_rows = list(csv.DictReader(open(DT / "regression_state_long.csv")))
for r in cc_rows:
    r["Result"] = rs[r["State"]]["Summary"]
    r["Sample Note"] = rs[r["State"]]["Sample Note"]
cc_cols = [("State", "string"), ("StateAbbr", "string"), ("Bureau", "string"), ("Predicted Likelihood", "real"), ("Observed Share", "real"),
           ("Close Call", "string"), ("Close Call Status", "string"), ("Datapoints", "integer"), ("Pct Label", "string"), ("Result", "string"), ("Sample Note", "string")]
CC = "federated.1cc5tate0ab1cd2ef3gh4ij5kl6m"
cc_calc = ("<column caption='Map Label' datatype='string' name='[Calc_cc_label]' role='dimension' type='nominal'>"
           "<calculation class='tableau' formula='IF [Close Call] = &quot;Yes&quot; THEN [StateAbbr] END' /></column>")
PANEL = {"Calc_p_title": f"IF COUNTD([State]) &gt; 1 THEN &quot;Pick a State&quot; ELSE ATTR([State]) END",
         "Calc_p_status": f"IF COUNTD([State]) &gt; 1 THEN &quot;All 49 states with data&quot; ELSE ATTR([Close Call Status]) END",
         "Calc_p_result": f"IF COUNTD([State]) &gt; 1 THEN &quot;The map is colored by verdict. Click a state to see its result; the bars show the average chance across all states until you do.&quot; ELSE ATTR([Result]) END",
         "Calc_p_note": f"IF COUNTD([State]) &gt; 1 THEN &quot;&quot; ELSE &quot;Based on &quot; + STR(INT(AVG([Datapoints]))) + &quot; recorded pulls; sample: &quot; + ATTR([Sample Note]) END"}
cc_calc += "".join(f"<column caption='{k}' datatype='string' name='[{k}]' role='measure' type='nominal'><calculation class='tableau' formula='{v}' /></column>" for k, v in PANEL.items())
STATUS_COL = {"Clear lean": "#5B3FA8", "Moderate lean": "#A796DC", "Toss-up": "#E0B43A", "Thin data (national pattern)": "#C3C8D1", "Not a close call": "#EEF0F3"}
BUREAU_COL = {"Experian": EXP, "Equifax": EQ, "TransUnion": TU}
ds_cc = datasource("0cc5tate0ab1cd2ef3gh4ij5kl6m", "Close Calls by State", "close_calls_state.csv", cc_cols, cc_rows, cc_calc, dsname=CC)
ds_cc = ds_cc.replace("<semantic-values>", "<style><style-rule element='mark'>"
    + "<encoding attr='color' field='[none:Close Call Status:nk]' type='palette'>" + "".join(f"<map to='{c}'><bucket>&quot;{esc(k)}&quot;</bucket></map>" for k, c in STATUS_COL.items()) + "</encoding>"
    + "<encoding attr='color' field='[none:Bureau:nk]' type='palette'>" + "".join(f"<map to='{c}'><bucket>&quot;{k}&quot;</bucket></map>" for k, c in BUREAU_COL.items()) + "</encoding>"
    + "</style-rule></style><semantic-values>", 1)
ds_cc = ds_cc.replace("<extract ", "<column-instance column='[Close Call Status]' derivation='None' name='[none:Close Call Status:nk]' pivot='key' type='nominal' />"
                      "<column-instance column='[Bureau]' derivation='None' name='[none:Bureau:nk]' pivot='key' type='nominal' /><extract ", 1)

src_rows = []
for i, s in enumerate(db["sources"], 1):
    if s[4]:
        src_rows.append({"n": str(len(src_rows) + 1), "Source": s[1], "Dated": s[3], "url": s[4]})
for name, url, dated in CONTEXT_SOURCES:
    src_rows.append({"n": str(len(src_rows) + 1), "Source": name, "Dated": dated, "url": url})
SR = "federated.1st0rysrc0ab1cd2ef3gh4ij5kl6"
ds_src = datasource("0st0rysrc0ab1cd2ef3gh4ij5kl6", "Story Sources", "story_sources.csv", [("n", "integer"), ("Source", "string"), ("Dated", "string"), ("url", "string")], src_rows, dsname=SR)

def deps(ds, cols, instances, extra=""):
    used = set(re.findall(r"column='\[([^\]]+)\]'", "".join(instances)))
    cols = [(n, t) for n, t in cols if n in used]
    if extra:  # only the calculated columns this sheet uses
        keep = [m.group(0) for m in re.finditer(r"<column caption='[^']*' datatype='[^']*' name='\[([^\]]+)\]'.*?</column>", extra) if m.group(1) in used]
        extra = "".join(keep)
    c = "".join(f"<column datatype='{t}' name='[{esc(n)}]' role='{'dimension' if t == 'string' else 'measure'}'{' semantic-role=&apos;[State].[Name]&apos;' if n == 'State' else ''} type='{'nominal' if t == 'string' else 'quantitative'}' />" for n, t in cols)
    c = c.replace("&apos;", "'")
    return f"<datasource-dependencies datasource='{ds}'>{c}{extra}{''.join(instances)}</datasource-dependencies>"
def inst(col, kind):
    if kind == "nk": return f"<column-instance column='[{esc(col)}]' derivation='None' name='[none:{esc(col)}:nk]' pivot='key' type='nominal' />"
    if kind == "ok": return f"<column-instance column='[{esc(col)}]' derivation='None' name='[none:{esc(col)}:ok]' pivot='key' type='ordinal' />"
    d = {"sum": "Sum", "avg": "Avg"}[kind]
    return f"<column-instance column='[{esc(col)}]' derivation='{d}' name='[{kind}:{esc(col)}:qk]' pivot='key' type='quantitative' />"
def worksheet(name, title_runs, ds, caption, dep, body, rows_, cols_, style="", show_title=True):
    t = f"<layout-options><title><formatted-text>{title_runs or '<run> </run>'}</formatted-text></title></layout-options>"
    return (f"<worksheet name='{esc(name)}'>{t}<table><view><datasources><datasource caption='{esc(caption)}' name='{ds}' /></datasources>"
            f"{'<mapsources><mapsource name=&apos;Tableau&apos; /></mapsources>'.replace('&apos;', chr(39)) if 'Geometry' in body else ''}{dep}<aggregation value='true' /></view>"
            + (f"<style>{style}</style>" if style else "<style />") + f"<panes>{body}</panes>" + (f"<rows>{rows_}</rows>" if rows_ else "<rows />") + (f"<cols>{cols_}</cols>" if cols_ else "<cols />") + "</table>"
            +
            f"<simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' /></worksheet>")

ccdeps = lambda inst_list, extra="": deps(CC, cc_cols, inst_list, extra)
WS = {}
WS["CC Map"] = worksheet("CC Map", "", CC, "Close Calls by State",
    ccdeps([inst("State", "nk"), inst("Close Call Status", "nk"), "<column-instance column='[Calc_cc_label]' derivation='None' name='[none:Calc_cc_label:nk]' pivot='key' type='nominal' />"], cc_calc),
    f"<pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view><mark class='Multipolygon' /><encodings>"
    f"<color column='[{CC}].[none:Close Call Status:nk]' /><lod column='[{CC}].[none:State:nk]' /><text column='[{CC}].[none:Calc_cc_label:nk]' />"
    f"<geometry column='[{CC}].[Geometry (generated)]' /></encodings>"
    f"<customized-label><formatted-text><run bold='true' fontalignment='1' fontcolor='#1f2937' fontsize='8'>&lt;[{CC}].[none:Calc_cc_label:nk]&gt;</run></formatted-text></customized-label>"
    f"<style><style-rule element='mark'><format attr='mark-labels-show' value='true' /><format attr='mark-labels-cull' value='false' /></style-rule></style></pane>",
    f"[{CC}].[Latitude (generated)]", f"[{CC}].[Longitude (generated)]",
    style=(f"<style-rule element='axis'><encoding attr='space' class='0' field='[{CC}].[Longitude (generated)]' field-type='quantitative' max='-7300000' min='-13950000' projection='EPSG:3857' range-type='fixed' scope='cols' type='space' />"
           f"<encoding attr='space' class='0' field='[{CC}].[Latitude (generated)]' field-type='quantitative' max='6500000' min='2750000' projection='EPSG:3857' range-type='fixed' scope='rows' type='space' /></style-rule>"
           f"<style-rule element='map'><format attr='washout' value='0.0' /></style-rule>"))
WS["CC State Panel"] = worksheet("CC State Panel", "", CC, "Close Calls by State",
    ccdeps(["<column-instance column='[%s]' derivation='User' name='[usr:%s:nk]' pivot='key' type='nominal' />" % (k, k) for k in PANEL], cc_calc),
    f"<pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view><mark class='Text' /><encodings>"
    + "".join(f"<text column='[{CC}].[usr:{k}:nk]' />" for k in PANEL) + "</encodings>"
    f"<customized-label><formatted-text><run bold='true' fontcolor='{NAVY}' fontsize='18'>&lt;[{CC}].[usr:Calc_p_title:nk]&gt;</run><run>Æ&#10;</run>"
    f"<run bold='true' fontcolor='#5B3FA8' fontsize='11'>&lt;[{CC}].[usr:Calc_p_status:nk]&gt;</run><run>Æ&#10;</run>"
    f"<run fontcolor='{BODY}' fontsize='10'>&lt;[{CC}].[usr:Calc_p_result:nk]&gt;</run><run>Æ&#10;</run>"
    f"<run fontcolor='{MUTED}' fontsize='9'>&lt;[{CC}].[usr:Calc_p_note:nk]&gt;</run></formatted-text></customized-label>"
    f"<style><style-rule element='mark'><format attr='mark-labels-show' value='true' /></style-rule><style-rule element='cell'><format attr='text-align' value='left' /><format attr='vertical-align' value='top' /></style-rule></style></pane>",
    "", "")
WS["CC Chance Bars"] = worksheet("CC Chance Bars", run("Chance of Each Bureau (Typical Application)", 10, NAVY, True), CC, "Close Calls by State",
    ccdeps([inst("Bureau", "nk"), inst("Predicted Likelihood", "avg")]).replace("</datasource-dependencies>", "</datasource-dependencies>"
        f"<sort class='manual' column='[{CC}].[none:Bureau:nk]' direction='ASC'><dictionary><bucket>&quot;Experian&quot;</bucket><bucket>&quot;Equifax&quot;</bucket><bucket>&quot;TransUnion&quot;</bucket></dictionary></sort>"),
    f"<pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view><mark class='Bar' /><encodings>"
    f"<color column='[{CC}].[none:Bureau:nk]' /><text column='[{CC}].[avg:Predicted Likelihood:qk]' /></encodings>"
    f"<customized-label><formatted-text><run bold='true' fontcolor='#1f2937' fontsize='10'>&lt;[{CC}].[avg:Predicted Likelihood:qk]&gt;</run></formatted-text></customized-label>"
    f"<style><style-rule element='mark'><format attr='mark-labels-show' value='true' /><format attr='size' value='0.75' /></style-rule></style></pane>",
    f"[{CC}].[none:Bureau:nk]", f"[{CC}].[avg:Predicted Likelihood:qk]",
    style=(f"<style-rule element='axis'><encoding attr='space' class='0' field='[{CC}].[avg:Predicted Likelihood:qk]' field-type='quantitative' max='1' min='0' range-type='fixed' scope='cols' type='space' />"
           f"<format attr='display' class='0' field='[{CC}].[avg:Predicted Likelihood:qk]' scope='cols' value='false' /></style-rule>"
           f"<style-rule element='header'><format attr='width' field='[{CC}].[none:Bureau:nk]' value='90' /></style-rule>"
           f"<style-rule element='gridline'><format attr='stroke-size' scope='cols' value='0' /></style-rule>"))
WS["Sources List"] = worksheet("Sources List", run("Sources (Click a Name to Open It)", 11, NAVY, True), SR, "Story Sources",
    deps(SR, [("n", "integer"), ("Source", "string"), ("Dated", "string"), ("url", "string")], [inst("n", "ok"), inst("Source", "nk"), inst("Dated", "nk"), inst("url", "nk")]),
    f"<pane selection-relaxation-option='selection-relaxation-allow'><view><breakdown value='auto' /></view><mark class='Text' /><encodings>"
    f"<text column='[{SR}].[none:Dated:nk]' /><lod column='[{SR}].[none:url:nk]' /></encodings>"
    f"<style><style-rule element='mark'><format attr='mark-labels-show' value='true' /></style-rule></style></pane>",
    f"([{SR}].[none:n:ok] / [{SR}].[none:Source:nk])", "",
    style=(f"<style-rule element='header'><format attr='display' class='0' field='[{SR}].[none:n:ok]' scope='rows' value='false' /><format attr='width' field='[{SR}].[none:Source:nk]' value='250' /></style-rule>"
           f"<style-rule element='label'><format attr='display' field='[{SR}].[none:n:ok]' value='false' /></style-rule>"
           f"<style-rule element='worksheet'><format attr='display-field-labels' scope='rows' value='false' /></style-rule>"
           f"<style-rule element='label'><format attr='color' field='[{SR}].[none:Source:nk]' value='{LABEL}' /><format attr='font-size' field='[{SR}].[none:Source:nk]' value='9' /></style-rule>"))
ACTIONS = (f"<action caption='Pick a state' name='[Action_ccpick]'><activation auto-clear='true' type='on-select' />"
           f"<source dashboard='11 Close Calls' type='sheet' worksheet='CC Map' /><command command='tsc:tsl-filter'>"
           f"<param name='special-fields' value='all' /><param name='target' value='11 Close Calls' /></command></action>"
           f"<action caption='Open source' name='[Action_srcurl]'><activation auto-clear='true' type='on-select' />"
           f"<source dashboard='15 Number Sources' type='sheet' worksheet='Sources List' />"
           f"<link caption='' delimiter=',' escape='\\' expression='&lt;url&gt;' include-null='true' multi-select='false' url-escape='false' /></action>")

# ------------------------------------------------------------------ assemble
zin = zipfile.ZipFile(SRC)
twb_name = [n for n in zin.namelist() if n.endswith(".twb")][0]
s = zin.read(twb_name).decode("utf-8")

def remove_block(s, tag, name):
    i = s.find(f"<{tag} name='{name}'")
    if i < 0:
        i = s.find(f"<{tag} enable-sort-zone-taborder='true' name='{name}'")
    if i < 0: return s
    j = s.find(f"</{tag}>", i) + len(f"</{tag}>")
    k = s.rfind("\n", 0, i)
    return s[:k] + s[j:]
OLD_DASH = ["1 Start Here", "2 Data and Method", "4 Reading the Maps", "7 Close Calls", "8 If Then", "9 Funding Ladder", "10 Scorecard"]
OLD_WS = ["D1 Stakeholders", "D2 Scope", "D3 Enrichment", "D4 ETL", "D5 Equation", "D6 Regression", "D7 Ladder", "D8 KPIs", "D9 Decision Tree", "D10 What If", "Scorecard Bars", "Regression Close Calls"]
for n in OLD_DASH: s = remove_block(s, "dashboard", n)
for n in OLD_WS: s = remove_block(s, "worksheet", n)
for n in OLD_DASH + OLD_WS:
    s = re.sub(r"\s*<window class='(?:dashboard|worksheet)'[^>]*name='" + re.escape(n) + r"'(?: [^>]*)?>.*?</window>", "", s, flags=re.S)
s = re.sub(r"\s*<actions>.*?</actions>", "", s, flags=re.S)
# drop the diagram datasources (their sheets are gone)
for cap in ("Story Diagrams", "Scorecard Bars", "Regression Bars"):
    s = re.sub(r"\s*<datasource caption='" + cap + r"' inline='true'.*?</datasource>", "", s, count=1, flags=re.S)

# the maps used a published Tableau Server data source, which Tableau Public Desktop cannot open:
# embed the same table (data/tableau/lender_state.csv) as an extract under the same data source name
m = re.search(r"<datasource caption='Funding Lender State Bureau Pulls' inline='true' name='(sqlproxy[^']*)'.*?\n    </datasource>", s, re.S)
SQLNAME = m.group(1)
calcs = {}
for c in re.finditer(r"<column caption='[^']*' datatype='[^']*' name='(\[Calculation_\d+\])'[^>]*>\s*<calculation[^>]*/>\s*</column>", s):
    calcs.setdefault(c.group(1), re.sub(r"\s*\n\s*", "", c.group(0)))
ls_rows = list(csv.DictReader(open(DT / "lender_state.csv")))
ls_cols = [("State", "string"), ("StateAbbr", "string"), ("Lender", "string"), ("Industry", "string"), ("Experian", "integer"), ("Equifax", "integer"),
           ("TransUnion", "integer"), ("Top Bureau", "string"), ("Total Datapoints", "integer"), ("Bureaus Reported", "string")]
ds_pulls = datasource("lenderstate", "Funding Lender State Bureau Pulls", "lender_state.csv", ls_cols, ls_rows,
                      "".join(calcs.values()) + "<column-instance column='[Top Bureau]' derivation='None' name='[none:Top Bureau:nk]' pivot='key' type='nominal' />", dsname=SQLNAME)
s = s[:m.start()] + ds_pulls + s[m.end():]
s = re.sub(r"\s*<datasource [^>]*formatted-name='Funding Lender State Bureau Pulls'.*?</datasource>", "", s, flags=re.S)

# map colors: one hue per bureau
RAMP = {"Experian": ["#f1f1f1", "#d6e4f5", "#bad3ee", "#9cc0e7", "#7eacdf", "#5f97d6", "#4384cc", "#2f70bb", "#2261a6", "#17518e", "#0b3d73"],
        "Equifax": ["#f1f1f1", "#fbe0cf", "#f8cbae", "#f4b48c", "#ef9c6a", "#e9854b", "#df6e30", "#ca5a1f", "#b04a17", "#933c12", "#74300e"],
        "TransUnion": ["#f1f1f1", "#d3eee2", "#b3e2cd", "#90d4b6", "#6dc59f", "#4db487", "#32a06f", "#228b5c", "#17754c", "#0f5f3d", "#094a2f"]}
for b, ramp in RAMP.items():
    i = s.find(f"<worksheet name='{b} Share of Pulls'"); j = s.find("</worksheet>", i)
    x = s[i:j]
    x = re.sub(r"<color-palette custom='true' name='' type='ordered-sequential'>.*?</color-palette>",
               "<color-palette custom='true' name='' type='ordered-sequential'>" + "".join(f"<color>{c}</color>" for c in ramp) + "</color-palette>", x, flags=re.S)
    x = x.replace("<run><![CDATA[<Sheet Name>", f"<run bold='true' fontcolor='{BUREAU_COL[b]}'>{b}</run><run><![CDATA[ Share of Pulls")
    s = s[:i] + x + s[j:]
TOPMAP = {"Experian": EXP, "Equifax": EQ, "TransUnion": TU, "Tie: Experian / Equifax": "#8F97B8", "Tie: Experian / TransUnion": "#7FA8A0",
          "Tie: Equifax / TransUnion": "#B8A48A", "Tie: Experian / Equifax / TransUnion": "#C3C8D1"}
s = s.replace(f"<semantic-values>", "<style><style-rule element='mark'><encoding attr='color' field='[none:Top Bureau:nk]' type='palette'></encoding></style-rule></style><semantic-values>", 1) if "field='[none:Top Bureau:nk]' type='palette'" not in s else s
s = re.sub(r"(<encoding attr='color' field='\[none:Top Bureau:nk\]' type='palette'>).*?(</encoding>)",
           lambda m: m.group(1) + "".join(f"<map to='{c}'><bucket>&quot;{esc(k)}&quot;</bucket></map>" for k, c in TOPMAP.items()) + m.group(2), s, flags=re.S)

for b in ("Experian", "Equifax", "TransUnion"):
    s = s.replace(f"caption='SUM([{b}])/SUM([Total Datapoints])'", f"caption='{b} Share of Pulls'")
# card 9 heading in Title Case
s = s.replace(">EXPERIAN AND EQUIFAX, SIDE BY SIDE<", ">Experian and Equifax, Side by Side<")

# new datasources, worksheets, dashboards
s = s.replace("</datasources>\n  <worksheets>", ds_cc + ds_src + "</datasources>\n  <worksheets>", 1) if "</datasources>\n  <worksheets>" in s else s.replace("</datasources>", ds_cc + ds_src + "</datasources>", 1)
s = s.replace("</worksheets>", "".join(WS.values()) + "</worksheets>", 1)
s = s.replace("<dashboards>", "<dashboards>" + "".join(D.values()), 1)
s = s.replace("<worksheets>", f"<actions>{ACTIONS}</actions><worksheets>", 1)

STORY = [("1 Introduction", "Introduction: context, purpose, sources and limits."),
         ("2 Who It Serves", "Who it serves, what it covers and key terms."),
         ("3 Market Context", f"Market context: Experian gets {tot['Experian'] / TOTAL:.0%} of recorded pulls."),
         ("4 KPIs", "KPIs, part 1: shares, margins and close calls."),
         ("5 KPIs 2", "KPIs, part 2: the model and the evidence."),
         ("6 Data and Method", "Data and method: 355 rows checked against 670 datapoints."),
         ("Top Bureau by State, by Lender", "Pick a lender: each state shows the bureau it pulls most."),
         ("8 Reading the Maps", "How to read a share map: one simple equation."),
         ("5 Experian and Equifax", "Experian and Equifax side by side: Experian leads most states."),
         ("TransUnion Share of Pulls", "TransUnion is rarely the leader, but it matters in a few states."),
         ("11 Close Calls", "Close calls: pick a state to see the model's best forecast."),
         ("12 Decision Tree", "Decision tree: start from your strongest report."),
         ("13 Funding Ladder", "The funding ladder: climb one score step at a time."),
         ("14 Scorecard", "Scorecard: the headline numbers and each issuer's habit."),
         ("15 Number Sources", "Where the numbers come from."),
         ("16 Recommendations", "Recommendations: the best move for each stakeholder.")]
pts = "".join(f"<story-point caption='{i}. {esc(tc(c))}' captured-sheet='{esc(n)}' id='{100 + i}' />" for i, (n, c) in enumerate(STORY, 1))
s = re.sub(r"<story-points>.*?</story-points>", f"<story-points>{pts}</story-points>", s, flags=re.S)
s = re.sub(r"<flipboard active-id='\d+'", "<flipboard active-id='101'", s)
# story title: plain Title Case text instead of the boxed sheet name
s = s.replace("<zone h='3527' id='3' type-v2='title' w='98426' x='787' y='830' />",
              "<zone h='3527' id='3' type-v2='title' w='98426' x='787' y='830'><zone-style><format attr='border-style' value='none' /><format attr='border-width' value='0' /></zone-style></zone>")

# windows: dashboards visible, every worksheet hidden (no clutter of sheet tabs)
VIEWS = {"11 Close Calls": ["CC Map", "CC State Panel", "CC Chance Bars"], "15 Number Sources": ["Sources List"]}
ZOOM = {"Sources List": "fit-width"}
new_windows = "".join(f"<window class='dashboard' name='{esc(n)}'><viewpoints>{''.join(f'<viewpoint name={chr(39)}{v}{chr(39)}><zoom type={chr(39)}{ZOOM.get(v, chr(101)+'ntire-view')}{chr(39)} /></viewpoint>' for v in VIEWS.get(n, []))}</viewpoints>"
                      f"<active id='-1' /><simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' /></window>" for n in D)
new_windows += "".join(f"<window class='worksheet' name='{esc(n)}'><cards><edge name='left'><strip size='160'><card type='pages' /><card type='filters' /><card type='marks' /></strip></edge>"
                       f"<edge name='top'><strip size='31'><card type='columns' /></strip><strip size='31'><card type='rows' /></strip><strip size='31'><card type='title' /></strip></edge></cards>"
                       f"<simple-id uuid='{{{str(uuid.uuid4()).upper()}}}' /></window>" for n in WS)
s = s.replace("</windows>", new_windows + "</windows>", 1)
s = re.sub(r"<window class='worksheet'(?! hidden)", "<window class='worksheet' hidden='true'", s)

# ------------------------------------------------------------------ bureau names: bold, in their color, in every text run
BW = re.compile(r"(Experian|Equifax|TransUnion)")
def color_runs(block):
    def fix(m):
        attrs, body = m.group(1), m.group(2)
        cdata = body.startswith("<![CDATA[")
        text = body[9:-3] if cdata else body
        if "<[" in text or "&lt;[" in text or not BW.search(text):
            return m.group(0)
        if re.search(r"fontcolor='(" + "|".join(re.escape(c) for c in BUREAU_COL.values()) + ")'", attrs) and BW.fullmatch(text.strip()):
            return m.group(0)
        a = dict(re.findall(r"(\w+)='([^']*)'", attrs))
        out = []
        for part in BW.split(text):
            if not part: continue
            aa = dict(a)
            if part in BUREAU_COL:
                aa["bold"] = "true"; aa["fontcolor"] = BUREAU_COL[part]
            at = "".join(f" {k}='{v}'" for k, v in sorted(aa.items()))
            out.append(f"<run{at}>" + (f"<![CDATA[{part}]]>" if cdata else part) + "</run>")
        return "".join(out)
    return re.sub(r"<run((?: \w+='[^']*')*)>(.*?)</run>", fix, block, flags=re.S)
def apply_formatted(s):
    return re.sub(r"<formatted-text>.*?</formatted-text>", lambda m: color_runs(m.group(0)) if "customized-tooltip" not in m.group(0) else m.group(0), s, flags=re.S)
s = apply_formatted(s)

# ------------------------------------------------------------------ package
OUT.parent.mkdir(exist_ok=True)
drop = ("Story Diagrams.csv", "Scorecard Bars.csv", "Regression Bars.csv")
with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr(twb_name, s)
    keep_ext = set()
    for n in zin.namelist():
        if n == twb_name or any(n.endswith(d) for d in drop): continue
        if n.startswith("Data/Extracts/"):
            hy = n.split("/")[-1]
            if hy.replace(".hyper", "") not in s: continue
        z.writestr(n, zin.read(n))
    for p in (WORK / "Data").rglob("*"):
        if p.is_file(): z.write(p, str(p.relative_to(WORK)))
    for p in (WORK / "Image").glob("*.png"):
        z.write(p, f"Image/{p.name}")
(ROOT / "tableau" / "story_points.md").write_text("# Tableau Story Points\n\n" + "\n".join(f"{i}. {tc(c)}" for i, (n, c) in enumerate(STORY, 1)) + "\n")
print("wrote", OUT, OUT.stat().st_size, "bytes;", len(STORY), "story points")
