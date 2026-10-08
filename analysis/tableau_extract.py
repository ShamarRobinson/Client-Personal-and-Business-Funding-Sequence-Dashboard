"""Build the Tableau-ready regression workbook from bureau_regression.py outputs.

Adds ready-made label and status columns so the Tableau sheets need no calculated fields.
Writes data/tableau/Tableau_Regression_Data.xlsx with sheets:
  State_Likelihood, State_Likelihood_Long, Lender_State_Wide, Effects, Model_Fit
"""
from pathlib import Path

import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data" / "tableau"
SHORT = {"Experian": "EX", "Equifax": "EQ", "TransUnion": "TU"}


def pct(x):
    return f"{round(100 * x):d}%"


def main():
    st = pd.read_csv(OUT / "regression_state.csv")
    st["Close Call Status"] = st.apply(
        lambda r: r["Model Confidence"] if r["Close Call"] == "Yes" else "Not a close call", axis=1)
    st["Map Label"] = st.apply(
        lambda r: f'{r.StateAbbr} EX {pct(r.P_Experian)} EQ {pct(r.P_Equifax)} TU {pct(r.P_TransUnion)}'
        if r["Close Call"] == "Yes" else r.StateAbbr, axis=1)
    st["Summary"] = st.apply(
        lambda r: f'{r["Most Likely Bureau"]} {pct(r["Lead Probability"])}, ahead of {r["Runner-up Bureau"]} '
                  f'by {r["Lead Margin (pts)"]:.0f} pts; leader held in {pct(r["Leader Holds in Resamples"])} of resamples', axis=1)

    lg = pd.read_csv(OUT / "regression_state_long.csv")
    lg["Pct Label"] = lg["Predicted Likelihood"].map(pct)
    lg["Range Label"] = lg.apply(lambda r: f'{pct(r["Predicted Likelihood"])} ({pct(r["Low 90"])} to {pct(r["High 90"])})', axis=1)
    lg = lg.drop(columns=["Close Call Status"], errors="ignore").merge(st[["State", "Close Call Status"]], on="State")

    ls = pd.read_csv(OUT / "regression_lender_state.csv")
    w = ls.pivot_table(index=["State", "StateAbbr", "Lender", "Lender Datapoints in State", "Close Call State"],
                       columns="Bureau", values="Predicted Likelihood").reset_index()
    w.columns.name = None
    w = w.rename(columns={b: f"P_{b}" for b in SHORT})
    pcols = [f"P_{b}" for b in SHORT]
    w["Most Likely Bureau"] = w[pcols].idxmax(axis=1).str[2:]
    w["Lead Probability"] = w[pcols].max(axis=1)
    w["Cell Label"] = w.apply(lambda r: f'{SHORT[r["Most Likely Bureau"]]} {pct(r["Lead Probability"])}', axis=1)
    w["Evidence"] = w["Lender Datapoints in State"].map(lambda n: "Lender seen in this state" if n > 0 else "Estimated from other states")

    eff = pd.read_csv(OUT / "regression_effects.csv")
    fit = pd.read_csv(OUT / "regression_fit.csv")

    with pd.ExcelWriter(OUT / "Tableau_Regression_Data.xlsx") as xw:
        st.to_excel(xw, sheet_name="State_Likelihood", index=False)
        lg.to_excel(xw, sheet_name="State_Likelihood_Long", index=False)
        w.to_excel(xw, sheet_name="Lender_State_Wide", index=False)
        eff.to_excel(xw, sheet_name="Effects", index=False)
        fit.to_excel(xw, sheet_name="Model_Fit", index=False)
    st.to_csv(OUT / "regression_state.csv", index=False)
    lg.to_csv(OUT / "regression_state_long.csv", index=False)
    w.to_csv(OUT / "regression_lender_state_wide.csv", index=False)
    # compact JSON for the website's Likelihood page
    import json
    r3 = lambda v: round(float(v), 3)
    site = {
        "fit": [{"model": r["Model"], "logloss": r3(r["CV Log Loss"]), "acc": r3(r["CV Accuracy"])} for _, r in fit.iterrows()],
        "states": [{
            "st": r.State, "ab": r.StateAbbr,
            "p": [r3(r.P_Experian), r3(r.P_Equifax), r3(r.P_TransUnion)],
            "lo": [r3(r.Experian_Low90), r3(r.Equifax_Low90), r3(r.TransUnion_Low90)],
            "hi": [r3(r.Experian_High90), r3(r.Equifax_High90), r3(r.TransUnion_High90)],
            "obs": [r3(r["Observed Experian Share"]), r3(r["Observed Equifax Share"]), r3(r["Observed TransUnion Share"])],
            "lead": r["Most Likely Bureau"], "wins": r3(r["Leader Holds in Resamples"]), "conf": r["Model Confidence"],
            "close": r["Close Call"] == "Yes", "obsLead": r["Observed Leader"], "obsGap": float(r["Observed Gap (pts)"]),
            "n": int(r.Datapoints)} for _, r in st.iterrows()],
        "lenders": [{"st": r.State, "l": r.Lender, "p": [r3(r.P_Experian), r3(r.P_Equifax), r3(r.P_TransUnion)],
                     "n": int(r["Lender Datapoints in State"])} for _, r in w.iterrows()],
    }
    (OUT.parent / "regression.json").write_text(json.dumps(site, separators=(",", ":")))
    print(st[st["Close Call"] == "Yes"][["State", "Map Label", "Close Call Status"]].to_string())


if __name__ == "__main__":
    main()
