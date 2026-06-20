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
- `issues` — 9 belief questions (id, topic, question, optionA/B/C, shortA/B/C, fact, hoverDesc)
- `statewide` — statewide + federal candidates (office, name, party, confirmed, photo, website, summary, + 9 position columns)
- `candidates` — Hays County local races (same schema as statewide)

Position columns: `reproductiveRights`, `immigration`, `gunPolicy`, `education`, `healthcare`, `climate`, `moneyInPolitics`, `socialSecurity`, `affordability`

Values: `A` (liberal), `B` (moderate), `C` (conservative), `D` (no position/n/a)

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

## Important Notes
- **Token cost warning:** index.html is large (3,244 lines). Read in sections, not all at once.
- The app has NO backend — everything runs in the browser
- Sharing (constellation share button) shows an alert — not yet implemented
- The `returnToSummary` state variable exists but is set and never consumed (dead code)
