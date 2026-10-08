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
| [Sources & Notes](https://shamarrobinson.github.io/Client-Personal-and-Business-Funding-Sequence-Dashboard/sources.html) | Sources, column guide and data limits |

## Tableau Public

The [Tableau workbook](https://public.tableau.com/app/profile/shamar.robinson/viz/ClientPersonalandBusinessFundingSequenceDashboard/WhichBureauWillTheyPull) has four choropleth maps (top bureau by state for a chosen lender, and the Experian, Equifax and TransUnion share of pulls by state) plus a Story that steps through them. The data behind it is in [data/tableau](data/tableau).

## Files

- `index.html`, `lenders.html`, `states.html`, `matrix.html`, `sequence.html`, `sources.html`: site pages
- `assets/`: shared styles and script
- `data/db.json`: data the site reads
- `data/Inquiry_Database_Expanded.xlsx`: full workbook
- `data/tableau/`: Tableau-ready CSV and Excel files

Bureau data is consumer-reported. Scores are published minimums or community estimates. Reference information only, not financial advice.
