"""Multiple regression: which credit bureau is pulled, by state.

Model: multinomial logistic regression (Experian / Equifax / TransUnion) with
state, lender, data era and lender-in-state (for the named major lenders) as predictors, L2-penalized so states with few
datapoints lean toward the national pattern. Each state-lender-source report
counts for at most CAP datapoints so one heavy list cannot swamp the rest.

Outputs (data/tableau/):
  regression_state.csv          predicted likelihood per state, 90% intervals, close-call flag
  regression_state_long.csv     same, one row per state x bureau (for small multiples)
  regression_lender_state.csv   predicted likelihood per state x major lender x bureau
  regression_effects.csv        odds ratios for each predictor level
  regression_fit.csv            model checks (cross-validated log loss and accuracy vs baselines)
  Tableau_Regression_Data.xlsx  all of the above as sheets
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupKFold

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "tableau"
BUREAUS = ["Experian", "Equifax", "TransUnion"]
CAP = 10            # max effective datapoints per state-lender-source report
CLOSE_GAP = 0.20    # observed top-two share gap that counts as a close call
N_BOOT = 150
SEED = 7
CURRENT_ERA = "2023 grid"

MAJOR = {
    "JPMorgan Chase (Chase Card Services)": "Chase",
    "Bank of America": "Bank of America",
    "Citibank (Citi Cards / CBNA)": "Citi",
    "American Express": "American Express",
    "U.S. Bank": "U.S. Bank",
    "Wells Fargo (Card Services)": "Wells Fargo",
    "Capital One": "Capital One",
    "Synchrony Bank (Amazon, PayPal, Lowe's, Old Navy, HSN, CareCredit and others)": "Synchrony",
    "Discover (now part of Capital One)": "Discover",
    "Elan Financial Services (U.S. Bank subsidiary)": "Elan",
    "Navy Federal Credit Union": "Navy Federal",
    "Comenity / Bread Financial (Sephora, BJ's, Wayfair and others)": "Comenity / Bread",
    "Apple Card (Goldman Sachs Bank USA, moving to Chase)": "Apple Card",
    "Barclays Bank Delaware": "Barclays",
}
EXCLUDE_IND = {"Credit Report Resellers & Screening (Not Lenders)", "Other / Non-Lender Inquiries"}


def era(row):
    if row.DataSet == "Original list":
        return "Original list"
    p = str(row.Period)
    if "2023" in p or "2026" in p:
        return "2023 grid"
    return "2008-2017 tables"


def load():
    d = pd.read_csv(OUT / "pulls_long.csv")
    d = d[~d.Industry.isin(EXCLUDE_IND)].copy()
    d["LenderGroup"] = d.Lender.map(MAJOR).fillna("Other: " + d.Industry)
    d["Era"] = d.apply(era, axis=1)
    # cap each state-lender-source report at CAP effective datapoints, keeping its bureau mix
    tot = d.groupby(["State", "Lender", "Source"]).Datapoints.transform("sum")
    d["Weight"] = d.Datapoints * np.minimum(1.0, CAP / tot)
    d["Cell"] = d.State + "|" + d.Lender + "|" + d.Source
    return d.reset_index(drop=True)


def lxs(d):
    """Lender-by-state term for the named major lenders (their state rules differ)."""
    return np.where(d.LenderGroup.str.startswith("Other"), "none", d.LenderGroup + "|" + d.State)


class Design:
    def __init__(self, d, use_state=True):
        self.cols = (["State"] if use_state else []) + ["LenderGroup", "Era"] + (["LxS"] if use_state else [])
        d = d.assign(LxS=lxs(d))
        self.levels = {c: sorted(d[c].unique()) for c in self.cols}

    def X(self, d):
        d = d.assign(LxS=lxs(d))
        parts = []
        for c in self.cols:
            for lv in self.levels[c]:
                parts.append((d[c] == lv).astype(float).values)
        return np.column_stack(parts)

    def names(self):
        return [(c, lv) for c in self.cols for lv in self.levels[c]]


def fit(d, C, use_state=True):
    des = Design(d, use_state)
    m = LogisticRegression(C=C, max_iter=5000)
    m.fit(des.X(d), d.Bureau.values, sample_weight=d.Weight.values)
    return m, des


def proba(m, des, frame):
    p = m.predict_proba(des.X(frame))
    order = [list(m.classes_).index(b) for b in BUREAUS]
    return p[:, order]


def cv_score(d, C, use_state=True, folds=5):
    gkf = GroupKFold(n_splits=folds)
    ll, acc, w = 0.0, 0.0, 0.0
    for tr, te in gkf.split(d, groups=d.Cell):
        m, des = fit(d.iloc[tr], C, use_state)
        te_d = d.iloc[te]
        p = proba(m, des, te_d)
        idx = te_d.Bureau.map({b: i for i, b in enumerate(BUREAUS)}).values
        pt = np.clip(p[np.arange(len(idx)), idx], 1e-9, 1)
        ww = te_d.Weight.values
        ll += -(ww * np.log(pt)).sum()
        acc += (ww * (p.argmax(1) == idx)).sum()
        w += ww.sum()
    return ll / w, acc / w


def national_baseline(d, folds=5):
    gkf = GroupKFold(n_splits=folds)
    ll, acc, w = 0.0, 0.0, 0.0
    for tr, te in gkf.split(d, groups=d.Cell):
        tr_d, te_d = d.iloc[tr], d.iloc[te]
        sh = tr_d.groupby("Bureau").Weight.sum().reindex(BUREAUS).values
        sh = sh / sh.sum()
        idx = te_d.Bureau.map({b: i for i, b in enumerate(BUREAUS)}).values
        ww = te_d.Weight.values
        ll += -(ww * np.log(sh[idx])).sum()
        acc += (ww * (idx == sh.argmax())).sum()
        w += ww.sum()
    return ll / w, acc / w


def reference_mix(d):
    """National lender mix (by weight), scored in the current data era."""
    mix = d.groupby("LenderGroup").Weight.sum()
    return (mix / mix.sum()).rename("w").reset_index()


def state_predictions(m, des, states, mix):
    rows = []
    for s in states:
        f = mix.assign(State=s, Era=CURRENT_ERA)
        p = proba(m, des, f)
        rows.append((p * f.w.values[:, None]).sum(0))
    return pd.DataFrame(rows, index=states, columns=BUREAUS)


def main():
    rng = np.random.default_rng(SEED)
    d = load()
    states = sorted(d.State.unique())
    abbr = d.drop_duplicates("State").set_index("State").StateAbbr

    # choose the penalty by grouped cross-validation
    grid = [0.03, 0.1, 0.3, 1.0, 3.0]
    scores = {C: cv_score(d, C) for C in grid}
    C = min(scores, key=lambda c: scores[c][0])
    ll_full, acc_full = scores[C]
    ll_nostate, acc_nostate = cv_score(d, C, use_state=False)
    ll_nat, acc_nat = national_baseline(d)

    m, des = fit(d, C)
    mix = reference_mix(d)
    pred = state_predictions(m, des, states, mix)

    # bootstrap over reports (cells) for intervals and "how often is the leader the leader"
    cells = d.Cell.unique()
    boot = np.zeros((N_BOOT, len(states), 3))
    by_cell = {c: g for c, g in d.groupby("Cell")}
    for b in range(N_BOOT):
        pick = rng.choice(cells, size=len(cells), replace=True)
        bd = pd.concat([by_cell[c] for c in pick], ignore_index=True)
        mb, desb = fit(bd, C)
        # states missing from a resample fall back to the national pattern (no state term)
        mix_b = mix[mix.LenderGroup.isin(desb.levels["LenderGroup"])]
        mix_b = mix_b.assign(w=mix_b.w / mix_b.w.sum())
        boot[b] = state_predictions(mb, desb, states, mix_b).values

    # observed shares (capped weights) and raw counts
    obs_w = d.pivot_table(index="State", columns="Bureau", values="Weight", aggfunc="sum", fill_value=0).reindex(columns=BUREAUS, fill_value=0)
    obs_n = d.pivot_table(index="State", columns="Bureau", values="Datapoints", aggfunc="sum", fill_value=0).reindex(columns=BUREAUS, fill_value=0)
    obs_sh = obs_w.div(obs_w.sum(axis=1), axis=0)

    rows = []
    for i, s in enumerate(states):
        p = pred.loc[s].values
        order = np.argsort(-p)
        lead, second = BUREAUS[order[0]], BUREAUS[order[1]]
        sh = obs_sh.loc[s].values
        so = np.sort(sh)[::-1]
        obs_gap = so[0] - so[1]
        top_obs = [BUREAUS[j] for j in range(3) if abs(sh[j] - so[0]) < 1e-9]
        lo = np.percentile(boot[:, i, :], 5, axis=0)
        hi = np.percentile(boot[:, i, :], 95, axis=0)
        wins = (boot[:, i, :].argmax(1) == order[0]).mean()
        n = int(obs_n.loc[s].sum())
        gap = p[order[0]] - p[order[1]]
        if n < 10:
            conf = "Thin data (national pattern)"
        elif wins >= 0.9 and gap >= 0.10:
            conf = "Clear lean"
        elif wins >= 0.7:
            conf = "Moderate lean"
        else:
            conf = "Toss-up"
        rows.append({
            "State": s, "StateAbbr": abbr[s],
            "P_Experian": p[0], "P_Equifax": p[1], "P_TransUnion": p[2],
            "Experian_Low90": lo[0], "Experian_High90": hi[0],
            "Equifax_Low90": lo[1], "Equifax_High90": hi[1],
            "TransUnion_Low90": lo[2], "TransUnion_High90": hi[2],
            "Most Likely Bureau": lead, "Runner-up Bureau": second,
            "Lead Probability": p[order[0]], "Lead Margin (pts)": round(100 * gap, 1),
            "Leader Holds in Resamples": wins, "Model Confidence": conf,
            "Observed Experian Share": sh[0], "Observed Equifax Share": sh[1], "Observed TransUnion Share": sh[2],
            "Observed Leader": " / ".join(top_obs), "Observed Gap (pts)": round(100 * obs_gap, 1),
            "Close Call": "Yes" if obs_gap <= CLOSE_GAP else "No",
            "Datapoints": n,
            "Sample Note": "Thin (under 10)" if n < 10 else ("Moderate (10-29)" if n < 30 else "Solid (30+)"),
        })
    st = pd.DataFrame(rows)
    st.to_csv(OUT / "regression_state.csv", index=False)

    long = []
    for r in rows:
        for b in BUREAUS:
            long.append({
                "State": r["State"], "StateAbbr": r["StateAbbr"], "Bureau": b,
                "Predicted Likelihood": r[f"P_{b}"], "Low 90": r[f"{b}_Low90"], "High 90": r[f"{b}_High90"],
                "Observed Share": r[f"Observed {b} Share"], "Is Most Likely": "Yes" if b == r["Most Likely Bureau"] else "No",
                "Close Call": r["Close Call"], "Model Confidence": r["Model Confidence"], "Datapoints": r["Datapoints"],
            })
    pd.DataFrame(long).to_csv(OUT / "regression_state_long.csv", index=False)

    # lender x state predictions for the major issuers, current era
    lrows = []
    majors = [v for v in MAJOR.values() if v in des.levels["LenderGroup"]]
    seen = d.groupby(["State", "LenderGroup"]).Datapoints.sum()
    for s in states:
        f = pd.DataFrame({"State": s, "LenderGroup": majors, "Era": CURRENT_ERA})
        p = proba(m, des, f)
        for j, lg in enumerate(majors):
            lead = BUREAUS[int(p[j].argmax())]
            for k, b in enumerate(BUREAUS):
                lrows.append({
                    "State": s, "StateAbbr": abbr[s], "Lender": lg, "Bureau": b,
                    "Predicted Likelihood": p[j, k], "Most Likely Bureau": lead,
                    "Lender Datapoints in State": int(seen.get((s, lg), 0)),
                    "Close Call State": st.set_index("State").loc[s, "Close Call"],
                })
    pd.DataFrame(lrows).to_csv(OUT / "regression_lender_state.csv", index=False)

    # effects as odds ratios vs the average level, per bureau (relative to TransUnion as the base)
    coef = m.coef_ - m.coef_.mean(0, keepdims=True)  # identifiable contrasts
    cls = list(m.classes_)
    erows = []
    for j, (var, lv) in enumerate(des.names()):
        if lv == "none":
            continue
        for b in ["Experian", "Equifax"]:
            lo_ = coef[cls.index(b), j] - coef[cls.index("TransUnion"), j]
            erows.append({"Predictor": {"State": "State", "LenderGroup": "Lender", "Era": "Data era", "LxS": "Lender in state"}[var],
                          "Level": lv, "Comparison": f"{b} vs TransUnion", "Log Odds": lo_, "Odds Ratio": float(np.exp(lo_))})
    pd.DataFrame(erows).to_csv(OUT / "regression_effects.csv", index=False)

    fit_rows = [
        {"Model": "Full model (state + lender + era + lender in state)", "CV Log Loss": ll_full, "CV Accuracy": acc_full},
        {"Model": "Without state terms (lender + era)", "CV Log Loss": ll_nostate, "CV Accuracy": acc_nostate},
        {"Model": "National shares only", "CV Log Loss": ll_nat, "CV Accuracy": acc_nat},
    ]
    fit_df = pd.DataFrame(fit_rows)
    fit_df.to_csv(OUT / "regression_fit.csv", index=False)

    with pd.ExcelWriter(OUT / "Tableau_Regression_Data.xlsx") as xw:
        st.to_excel(xw, sheet_name="State_Likelihood", index=False)
        pd.DataFrame(long).to_excel(xw, sheet_name="State_Likelihood_Long", index=False)
        pd.DataFrame(lrows).to_excel(xw, sheet_name="Lender_State_Likelihood", index=False)
        pd.DataFrame(erows).to_excel(xw, sheet_name="Effects", index=False)
        fit_df.to_excel(xw, sheet_name="Model_Fit", index=False)

    summary = {
        "C": C, "cv_grid": {str(k): v for k, v in scores.items()}, "fit": fit_rows,
        "rows": int(len(d)), "reports": int(d.Cell.nunique()), "datapoints": int(d.Datapoints.sum()),
        "close_calls": st[st["Close Call"] == "Yes"][["State", "Most Likely Bureau", "Lead Probability", "Lead Margin (pts)", "Leader Holds in Resamples", "Model Confidence", "Observed Leader", "Observed Gap (pts)", "Datapoints"]].to_dict("records"),
    }
    (OUT / "regression_summary.json").write_text(json.dumps(summary, indent=1, default=float))
    print(json.dumps({k: summary[k] for k in ["C", "fit", "rows", "reports", "datapoints"]}, indent=1, default=float))
    print(st[st["Close Call"] == "Yes"][["State", "P_Experian", "P_Equifax", "P_TransUnion", "Most Likely Bureau", "Leader Holds in Resamples", "Model Confidence", "Observed Leader", "Observed Gap (pts)", "Datapoints"]].round(3).to_string())


if __name__ == "__main__":
    main()
