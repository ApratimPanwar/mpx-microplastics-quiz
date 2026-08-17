# MPx — Drinking Water Microplastics Assessment

Part of the MPx MDes dissertation project (IISc): a portable device to detect and filter microplastics from drinking water.

## Live pages

- **Quiz** (for respondents): `index.html` — the stakeholder-research quiz. Share this URL with anyone you want to survey.
- **Dashboard** (for the research team only): `dashboard.html` — aggregate view + raw data export. Not linked from the quiz; keep this URL private.

## Data collection

No response data is stored in this repository. Responses are collected into a private Google Sheet via a Google Apps Script Web App:

1. See `AppsScript-Code.gs` for the backend code and setup steps (also documented inline).
2. Once deployed, paste the Web App URL into `index.html`'s `SUBMIT_URL` constant near the top of the `<script>` block, and re-push.
3. Use `dashboard.html` to view aggregate results and export the raw merged data, either by loading downloaded files or by fetching a published Google Sheet CSV export live.

## Updating the site

This repo is served via GitHub Pages from the `main` branch root. Push changes to `main` and the live site updates automatically within a minute or two.
