# VoteYourViews.org — Claude Code Context

## Project Overview
**VoteYourViews.org** is a Texas 2026 voter guide web app — a nonpartisan tool that lets voters answer belief questions, see which candidates match their values, and build a printable ballot.

- **Live site:** voteyourviews.org (deployed via Netlify)
- **GitHub:** gfantsimonVCVS/voteyourviews
- **Owner:** Gina Fant-Simon (gina@fantsimon.com)
- **Initiative:** State Over Party (stateoverparty.org)

## Tech Stack
Single HTML file — no build step, no npm, no framework setup needed.
- React 18 (UMD/CDN)
- Tailwind CSS (CDN)
- Babel Standalone (JSX in browser)
- PapaParse (CSV parsing)
- Google Sheets as CMS (published to web as CSV)
- Google Maps API (address autocomplete)
- Geocodio API (address → district lookup)
- ArcGIS REST API (Hays County commissioner/JP precinct lookup)

## File Structure
```
index.html          ← the entire app (3,244 lines)
icons/              ← candidate photos, section images, issue icons, logo files
  symbols/          ← issue symbol icons used in quiz screen
  candidate-undefined.png
  VoteYourViews_Logo_Color.png
  VoteYourViews_Logo_White.png
  Federal2.png, State2.png, County.png, Judicial.png
```

## Google Sheets
**Sheet ID:** `1V1oaEy6ToV3LZt0et9bIWEJQbPrYZg73tDxGelhiFn8`

Tabs:
- `Issues` — belief questions (id, topic, optionA/B/C/D, issueFact, …)
- `HaysCounty` — full Hays ballot; **master copy of the 18 statewide races (rows 2–37)**
- `TravisCounty` — full Travis ballot; statewide block is the array formula referencing Hays (see below)
- `Statements` — per-issue statements (issue, order, text, Party Perspective)

Candidate tab columns (HaysCounty / TravisCounty), A→AF:
`office, category, districtType, districtNumber, name, party, confirmed, description, summary, website, photo,` then the 9 position columns `reproductiveRights, immigration, gunPolicy, education, healthcare, climate, electionIntegrity, socialSecurity, affordability,` then `hook1, hook2, uncontested,` then the 9 matching `…Evidence` columns. (The old `source` provenance column was removed June 2026.)

### Multi-county data structure (READ BEFORE ADDING A COUNTY)
- One tab per county: `HaysCounty`, `TravisCounty`, … Each is a full ballot.
- **`HaysCounty` is the MASTER for the 18 statewide races (rows 2–37).** Edit a statewide candidate ONLY in HaysCounty; every other county inherits it.
- **Every other county's statewide block (rows 2–37) MUST be the array formula `={HaysCounty!A2:AF37}` in cell A2** — a single spilling formula, NOT pasted/static values. If a county's A2 holds a literal office name instead of a formula, it's been flattened to values and statewide edits will NOT propagate — reconvert it to the formula.
- County-specific district + local races go in **row 38 and below only**. Never write rows 2–37 of any county tab except the single master cells in HaysCounty.
- Service account for sheet writes: `voteyourviews-db39fac73eed.json` (see API Keys below).

Position values (candidate cells): full words — `Agree`, `Disagree`, `Unknown` (no moderate/middle option). Older A/B/C/D coding is retired.

## App Screens (state machine in `App` component)
1. **landing** — hero with 3x3 issue icon grid, CTAs
2. **quiz** — single-issue belief question with expandable views + rank gauge
3. **summary** — review chosen views, CTA to build ballot or view constellation
4. **constellation** — shareable political constellation card (SVG star map)
5. **address** — address lookup → district filtering (Geocodio + ArcGIS)
6. **results** — race-by-race belief match cards, auto-selects best match
7. **browse** — all candidates by section, collapsible, leads to RaceDetail
8. **ballot** — dark-themed printable ballot summary

## Key Components
- `Landing` — hero screen, issue grid, mobile/desktop responsive
- `Quiz` — expandable A/B/C cards + "No Opinion" + rank slider (1–10)
- `Summary` — views review + unanswered topics
- `ConstellationScreen` — SVG star map, shareable card
- `AddressScreen` — Google Places autocomplete + Geocodio district lookup
- `Results` / `RaceResultCard` — match scores per race
- `Browse` / `BrowseRaceCard` / `RaceDetail` — full candidate browser
- `RaceDetail` — 3-panel swipeable mobile layout (ME | CandA | CandB), 4-column desktop
- `CandidateProfile` — full-screen candidate issue breakdown sheet
- `Ballot` — printable dark-theme ballot grid

## Data Architecture
- `ISSUES` / `ISSUES_RAW` — 9 hardcoded belief issues (fallback + structure)
- `COUNTIES` — hardcoded candidate data for Hays County (fallback)
- `SHEETS` config — Sheet IDs; master sheet overrides hardcoded data on load
- `calcMatch()` — scores candidate vs. voter answers (A=full, B=half, C=0, D=excluded)
- `filterRacesByDistrict()` — filters races by user's looked-up districts

## Counties Status
- **Hays County** — fully built (federal + state + county + judicial races)
- **Travis, Bexar, Harris** — placeholder (`available: false`, empty race arrays)

## Current Candidate Status (as of June 2026)
- Many races still show TBD nominees (primary runoffs pending certification)
- James Talarico (D) vs Ken Paxton (R) — U.S. Senate confirmed
- Greg Abbott (R) — Governor confirmed, D nominee TBD
- Dan Patrick (R) — Lt. Governor confirmed, D runoff pending
- Most county/judicial races: both nominees TBD

## Deployment
- Netlify auto-deploys from GitHub `main` branch
- No build step — Netlify just serves `index.html` as static
- Icons folder must be committed to git (not gitignored)

## API Keys (NEVER LOSE THESE)
- **Democracy Works Elections API**
  - Key: `7ya5QclfLmVay7rTfmyD9BntG0ZSvEb4ZII3q3f5`
  - Header: `x-api-key` (lowercase, required)
  - Endpoint: `https://api.democracy.works/v2/elections`
  - Required params: `addressStreet`, `addressCity`, `addressStateCode`, `addressZip`, `startDate`, `includeBallotData=true`
  - Working curl: `curl "https://api.democracy.works/v2/elections?addressStreet=14360+Falcon+Head+Blvd&addressCity=Bee+Cave&addressStateCode=TX&addressZip=78738&startDate=2026-06-01&includeBallotData=true" --header "x-api-key: 7ya5QclfLmVay7rTfmyD9BntG0ZSvEb4ZII3q3f5"`
  - Returns: `data.elections[].contests[].candidates[]` with `fullName`, `partyAffiliation[]`, `contact.campaign.website`, `ballotpediaUrl`
- **Geocodio API**: `59cc9999fb36698b393c3f1c3861cab815fb35c`
- **Google Sheets Service Account**: `/Users/ginafant-simon/Downloads/State Over Party V3/voteyourviews-db39fac73eed.json`
- **Sheet ID**: `1V1oaEy6ToV3LZt0et9bIWEJQbPrYZg73tDxGelhiFn8`

## Engineering Standards (REQUIRED)
- **Renames must be complete — no band-aids, no aliases.** When you rename an issue name, `id`, icon, field, or column, change it across EVERY layer in the same edit: all code references (ids, `ISSUE_KEYS`/`GRID_ORDER`/`POS_*`/`ISSUE_VOICE`/`POSITION_PHRASE`, match logic), the Google Sheet column headers + data, AND the asset filename. Then load the app and confirm it renders.
  - **Never** override the old name at runtime (e.g. `iss.id === 'moneyInPolitics' ? {...iss, topic: 'Election Integrity'} : iss`).
  - **Never** add a compatibility alias for old names (e.g. `ID_ALIASES = { democracy: 'moneyInPolitics' }`) — delete the old name everywhere instead.
  - **Never** leave an icon `src`, column, or key pointing at a file/field that was renamed or deleted.
  - Before calling a rename done: `grep` the whole file for the old id/name and confirm zero stragglers.

## UI / Asset Conventions
- **Buttons:** use the canonical `BTN.std` class + a `BTN_STYLE` color variant (blue/red/green/amber/slate) for any standard button — rounded rectangle, 1px lighter border, 320px (home-page) width. Don't hand-roll `rounded-full` pills. (Legacy `BTN.primary/outline` remain only for the split "Candidates ▾" control.)
- **Shape grammar (two families):** rounded rectangles (`rounded-xl`) = action buttons that move you forward/commit (Agree, Disagree, Next Issue, Build My Ballot, home CTAs). Pills (`rounded-full`) = small inline chips/tags/badges (BETA chip, ✓ Match / ✗ Differs badges, "Get the Facts"). Keep these consistent *within* each family; don't square off the chips.
- **Asset filenames are case-sensitive on Netlify (Linux) but NOT on macOS.** A path that works locally can 404 in production. When referencing an asset, match the committed file's case EXACTLY (e.g. folder is `icons/Symbols/`, not `symbols/`). For NEW assets, prefer all-lowercase, hyphenated names. Do NOT mass-rename existing files — candidate photos are referenced by exact filename from the Google Sheet `photo` column, so renaming them breaks production images.

## Office-name separator
- In the sheet, office names use an em dash as the separator (e.g. `U.S. House — District 37`, `Travis County Court at Law — No. 1`). The **Compare race title auto-converts any em/en dash to a bullet `•`** at display (regex on `race.office`), so new races need no manual bullet — just type the em dash. (PreBallot/Ballot stack the parts on separate lines instead.)

## Important Notes
- **Token cost warning:** index.html is large (3,244 lines). Read in sections, not all at once.
- The app has NO backend — everything runs in the browser
- Sharing (constellation share button) shows an alert — not yet implemented
- The `returnToSummary` state variable exists but is set and never consumed (dead code)
