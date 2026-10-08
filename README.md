# Client Personal Funding Dashboard

A shareable dashboard and database of which credit bureau each lender pulls by state, with funding type, average score needed, documentation level, and a funding sequence for every credit score tier.

## Pages

- `index.html`: dashboard metrics
- `lenders.html`: lender database, 204 lenders in 19 industry sections
- `states.html`: the original 355 inquiry rows, cross-checked
- `matrix.html`: 670 outside state-level datapoints
- `sequence.html`: funding sequence by score tier
- `sources.html`: sources, column guide and data limits

The full workbook is in `data/Inquiry_Database_Expanded.xlsx`. The site reads `data/db.json`.

Bureau data is consumer-reported. Scores are published minimums or community estimates. Reference information only, not financial advice.
