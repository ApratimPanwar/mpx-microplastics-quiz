# MPx — Drinking Water Microplastics Assessment

Part of the MPx MDes dissertation project (IISc): a portable device to detect and filter microplastics from drinking water.

## Live pages

- **Quiz** (for respondents): `index.html` — the stakeholder-research quiz. Share this URL with anyone you want to survey.
- **Dashboard** (for the research team only): `dashboard.html` — aggregate view + raw data export. Not linked from the quiz; keep this URL private.

## MPx Lab — interactive test benches (`lab/`)

`lab/index.html` is a separate section of this site with every virtual test bench, teardown viewer and design review from the project:

- **Spin** (`lab/spin/`) — centrifuge test bench (Fig 4), v1 and v1.1 teardown viewers, rig calibration, TRIZ, FMEA, BOM & sourcing, drawings, two design reviews.
- **Squeeze** (`lab/squeeze/`) — v1 and v2 test benches (Figs 2–3), v2 teardown, renders, drawing sets, FMEA, BOMs, design review.
- **Boil** (`lab/boil/`) — Boil-Loop Mini v0.5 cutaway bench (Fig 1), Boil-Loop v0.1 3D model, Boil-Trap v0.3 / Boil-Tube v0.4 / Boil-Loop v0.2 simulations, drawings, FMEA, BOMs.
- **Concept stage** (`lab/concepts/`) — function structure, technology map, morphological matrix, 12 concept sketches, evaluation, detection methods.

Everything is static and self-contained (three.js is bundled in `lab/assets/vendor/`). `.nojekyll` at the root is required so GitHub Pages serves the `_t/` thumbnail folders.
The pages are generated; the bench HTML files are standalone and can also be opened offline.

## Data collection

No response data is stored in this repository. Responses are collected into a private Google Sheet via a Google Apps Script Web App:

1. See `AppsScript-Code.gs` for the backend code and setup steps (also documented inline).
2. Once deployed, paste the Web App URL into `index.html`'s `SUBMIT_URL` constant near the top of the `<script>` block, and re-push.
3. Use `dashboard.html` to view aggregate results and export the raw merged data, either by loading downloaded files or by fetching a published Google Sheet CSV export live.

## Updating the site

This repo is served via GitHub Pages from the `main` branch root. Push changes to `main` and the live site updates automatically within a minute or two.
