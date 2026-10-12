# Client Personal and Business Funding Sequence Dashboard

**Live dashboard:** https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/

| View | Link |
| --- | --- |
| Dashboard site (this repository, GitHub Pages) | [shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/) |
| Interactive maps and Story (Tableau Public) | [Which Bureau Will They Pull](https://public.tableau.com/app/profile/shamar.robinson/viz/ClientPersonalandBusinessFundingSequenceDashboard/WhichBureauWillTheyPull) |
| Slideshow | [Project presentation](https://claude.ai/artifact/95vnkBxejyTxzMTD5QAxnw) |
| Full workbook | [data/Inquiry_Database_Expanded.xlsx](data/Inquiry_Database_Expanded.xlsx) |

A dashboard and database of which credit bureau each lender pulls by state, with funding type, average score needed, documentation level, and a funding sequence for every credit score tier.

## Dashboard pages

| Page | What it shows |
| --- | --- |
| [Dashboard](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/index.html) | Headline metrics and charts |
| [Lender Database](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/lenders.html) | 204 lenders in 19 industry sections |
| [All States & Banks](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/states.html) | The original 355 inquiry rows, cross-checked |
| [Bureau by State](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/matrix.html) | 670 outside state-level datapoints |
| [Funding Sequence](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/sequence.html) | Application order for each score tier |
| [Bureau Likelihood](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/likelihood.html) | Regression: most likely bureau in close-call states, and by lender |
| [Sources & Notes](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/sources.html) | Sources, column guide and data limits |

## Tableau Public

The [Tableau workbook](https://public.tableau.com/app/profile/shamar.robinson/viz/ClientPersonalandBusinessFundingSequenceDashboard/WhichBureauWillTheyPull) has four choropleth maps (top bureau by state for a chosen lender, and the Experian, Equifax and TransUnion share of pulls by state) and a Story, "Which Bureau Will They Pull". The Story is being rebuilt into nine cards, with information cards before, between and after the maps. The diagram, decision tree, what-if and scorecard sheets are already published:

| Card | Type | What it shows |
| --- | --- | --- |
| 1. Start here | Info | Who the tool is for (stakeholder grid) and what is in and out of scope |
| 2. Data and method | Info | Enrichment flow (355 original rows, 670 outside datapoints, 0 contradicted) and the ETL chart |
| 3. Top bureau by lender | Map | Pick a lender; each state is filled by the bureau it pulls most |
| 4. Reading the share maps | Info | The share equation, worked for Utah, Florida and Georgia |
| 5. Experian and Equifax | Map | Both share maps on one card, every state labeled with its percentage |
| 6. TransUnion | Map | TransUnion share by state |
| 7. Close calls | Info + chart | Regression flow chart and predicted likelihood bars for the 24 close-call states |
| 8. Funding ladder | Info | Seven score tiers from 500-549 to 800+, with the sequencing rules |
| 9. Scorecard | Scorecard | Six headline numbers and the bureau profile of the eight busiest issuers |

Every diagram is a Tableau sheet drawn from [data/tableau/story_diagrams.csv](data/tableau/story_diagrams.csv), [scorecard_bars.csv](data/tableau/scorecard_bars.csv) and [regression_bars.csv](data/tableau/regression_bars.csv), which [analysis/story_infographics.py](analysis/story_infographics.py) generates. The scorecard adds a new finding: issuers have clear bureau profiles. American Express lands on Experian in 87% of recorded pulls, Synchrony on TransUnion in 62% and U.S. Bank on TransUnion in 47%, while Capital One splits close to evenly (37% Experian, 35% Equifax, 28% TransUnion).

## Regression: close-call states

[analysis/bureau_regression.py](analysis/bureau_regression.py) fits a multinomial logistic regression (multiple regression for a three-way outcome) on 2,901 bureau-pull datapoints. Predictors: state, lender, data era, and lender-in-state for the 14 major issuers. A close call is a state where the top two bureaus are within 20 points in the recorded pulls (24 states).

| Model (5-fold cross-validation, whole reports held out) | Log loss | Accuracy |
| --- | --- | --- |
| State + lender + era + lender in state | 0.903 | 55% |
| Lender + era only | 0.905 | 55% |
| National shares only | 1.041 | 50% |

The lender explains most of which bureau is pulled; the state adds a little, mainly through lenders whose bureau changes by state. For a typical application, Experian is the most likely bureau in all 24 close-call states: 15 with a clear or moderate lean, 4 still toss-ups (Hawaii, Kansas, South Carolina, Virginia) and 5 with too little data to call. Outputs are in [data/tableau](data/tableau) (`regression_*.csv`, `Tableau_Regression_Data.xlsx`) and on the [Bureau Likelihood page](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/likelihood.html).

## Files

- `index.html`, `lenders.html`, `states.html`, `matrix.html`, `sequence.html`, `likelihood.html`, `sources.html`: site pages
- `analysis/`: regression model and Tableau extract scripts
- `data/regression.json`: regression results the Likelihood page reads
- `assets/`: shared styles and script
- `data/db.json`: data the site reads
- `data/Inquiry_Database_Expanded.xlsx`: full workbook
- `data/tableau/`: Tableau-ready CSV and Excel files

Bureau data is consumer-reported. Scores are published minimums or community estimates. Reference information only, not financial advice.
