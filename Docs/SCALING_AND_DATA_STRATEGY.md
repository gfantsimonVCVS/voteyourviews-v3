# VoteYourViews — Scaling & Data Strategy

*Working draft — June 2026. How to grow from 1 county (Hays) to 254 Texas counties: where the data comes from, how APIs fit a no-backend app, and a realistic plan for candidate photos.*

---

## 1. The core challenge

Hays County is **1 of 254** Texas counties. Doing each county by hand the way Hays was built does not scale. But not all data is equal — it splits into two very different buckets:

| Bucket | What it is | Can it be automated? |
|---|---|---|
| **The scaffolding** | Which races, candidates, offices, and districts are on the ballot at a given address | **Yes** — this is what election-data APIs do well |
| **The secret sauce** | Each candidate's positions on your 9 belief issues + hooks/summaries | **No** — this is your editorial value and stays human-curated |

**Key insight:** the API removes the *clerical* work (typing in who's running where), not the *judgment* work (where each candidate stands). Your differentiator — belief matching — is never something you buy from an API.

---

## 2. Current architecture (and why it constrains the API choice)

- Single static `index.html` — React via CDN, **no backend**, no build step.
- Data comes from **Google Sheets**, published to the web as CSV, read in the browser.
- Hosted on **Netlify** (static file serving).

This is cheap, simple, and non-engineer-friendly. The catch: **a keyed, partner-gated API cannot be called directly from the browser.**

- The API key would be visible to anyone viewing source (security hole).
- The API won't allow cross-origin browser requests (CORS) anyway.

So any API has to be reached from somewhere the key is hidden. Three ways to do that:

### Option A — API → Google Sheet (recommended)
A script (run on a schedule or on demand) calls the API, then writes races/candidates into your existing Sheet. **The live app doesn't change at all** — it keeps reading the Sheet.
- ✅ Keeps your hand-editing workflow (positions, hooks, photos, overrides)
- ✅ Zero change to the live app; lowest risk
- ✅ You can review/correct what the API produced before it goes live
- ⚠️ Data is as fresh as the last script run (fine — ballots change slowly)

### Option B — Build-time → static JSON
A script fetches the API at deploy time and commits JSON the app loads.
- ✅ Key stays server-side
- ⚠️ Loses easy hand-editing; every change needs a rebuild

### Option C — Netlify Function (serverless proxy)
A tiny serverless function holds the key and serves data live to the app.
- ✅ Most "real-time"
- ⚠️ Most setup; closest to running a backend

**Recommendation: Option A.** It preserves everything good about the current setup and adds the API as a *feeder* into the Sheet, not a replacement for it.

```
Democracy Works API ──(script, key hidden)──▶ Google Sheet ──(CSV)──▶ App
                                                   ▲
                                          you hand-edit positions,
                                          hooks, photos, overrides
```

---

## 3. Ballot data: Democracy Works (TurboVote) Elections API

- Provides **contests, candidates, ballot measures** tailored to a voter's address — exactly the per-county scaffolding.
- **Partner-gated** (request access/key from Democracy Works).
- **Does NOT include candidate photos** or issue positions.

**How it fits:** feed it into the Sheet (Option A). For each county it auto-populates the races and candidate names; you then layer on positions/hooks/photos. The clerical 90% is automated; you spend your time on the editorial 10% that matters.

> Note: validate exactly what fields it returns (district types, candidate party, incumbency) against what the app's `filterRacesByDistrict` and matching logic expect, so the importer maps cleanly.

---

## 4. Photos — the genuinely hard part

There is **no free, complete source of candidate photos** for local races across 254 counties. Even Ballotpedia (the most complete) misses many local candidates. So the goal is **not** 100% coverage — it's *graceful tiered coverage*.

### Cost reality (checked June 2026)
- **Ballotpedia API:** partner-only, **thousands of dollars/month** — not realistic for a nonpartisan civic project.
- **Ballotpedia one-time CSV dump:** ~**$600** for a requested report (a static snapshot, goes stale). Possible *one-shot* backfill, not a foundation.
- Contact `data@ballotpedia.org` for a rate card if ever needed.

### Recommended: free, tiered strategy

**Tier 1 — Marquee races (federal / statewide / legislative):**
Auto-fill from **Wikidata / Wikimedia Commons** — free, properly licensed, CORS-friendly (works in the app *and* the Save PDF). Coverage is strong for Congress, statewide officials, and most state legislators. The same importer that pulls candidates can try to resolve a Wikidata photo and drop the URL into the Sheet.

**Tier 2 — Local long tail (county / judicial / JP):**
Coverage is sparse everywhere. Accept the placeholder for unknowns; **manually add the local ones you personally know** (your Hays advantage) via the CDN.

**The unlock — make "no photo" a designed state.**
A missing photo should render as a clean, branded **initials avatar** (party-colored ring + initials), not a flat gray silhouette that reads as "broken." The mobile cards already do this. Once the placeholder looks intentional, **missing photos stop blocking a county launch.**

### Self-submission — scope it correctly
Only realistic for **local candidates you can personally reach** (mostly Hays). Treat it as a manual local tool, **not** a scaling mechanism.

---

## 5. Photo hosting — stop using Google Drive

Google Drive links (`lh3.googleusercontent.com/d/<id>`, `drive.google.com/...`) are the wrong tool:
- Google **throttles** hotlinking — it serves a tiny placeholder (this is why Talarico renders blank).
- They **break the Save PDF** (CORS taint).
- Even sized requests cap at ~200px.

### Two good hosts
1. **Cloudinary (recommended for scale).** Free tier (~25GB). The Sheet stores just the **filename** (your existing naming convention, e.g. `Hays_Dem_15thCourtPl2_Tom_Baker.png`); the app builds the URL from one base with transforms:
   ```
   https://res.cloudinary.com/<cloud>/image/upload/f_auto,q_auto,w_400,h_400,c_fill,g_face/candidates/<filename>
   ```
   - `c_fill,g_face` auto-crops centered on the face (fixes inconsistent framing across thousands of photos)
   - `f_auto,q_auto` auto-optimizes (~20KB versions — fast pages, small PDFs)
   - CORS-enabled → works in the vector PDF
   - **Your naming convention becomes the key** — no per-photo URL wrangling
2. **`filesafe.space` (zero new tooling).** Most current photos already load from this CDN reliably (full-res, CORS-OK). Consolidating everything here works, but you lose auto-crop/auto-optimize and still manage full URLs by hand.

### Naming convention (for reference)
- Simple: `First_Last.ext` — `Beth_Smith.png`, `Elaine_Cardenas.jpg`
- Hays local/judicial: `Hays_Dem_<OfficeCode>_<First>_<Last>.png` — e.g. `Hays_Dem_428DistJudge_Cassie_Benoist_Templeton.png`

> The convention is great for organizing files and (with Cloudinary) becomes the URL key. With raw Drive, the URL is a random file ID, so the convention can't become the URL — another reason to leave Drive.

---

## 6. Recommended phased rollout

1. **Now (Hays polish):** finalize the branded initials placeholder so gaps look intentional; move the few Hays photos you have off Drive onto a real CDN.
2. **Pick a photo host:** Cloudinary (filename-as-key + auto-crop) or consolidate on `filesafe.space`. Stop adding Drive links.
3. **Get Democracy Works API access** and build the **API → Sheet importer** (Option A). Start by importing one new county end-to-end to prove the pipeline.
4. **Add Wikidata photo resolution** to the importer for Tier-1 races (free coverage of the marquee candidates).
5. **Scale county by county:** importer fills scaffolding → you add positions/hooks → photos auto-fill where Wikidata has them, placeholder elsewhere, manual for locals you know.
6. **(Optional) one-time Ballotpedia $600 dump** only if a specific launch needs a photo boost.

---

## 7. Guiding principles

- **The matching engine is the product.** Photos and even auto-imported ballots are support; never let photo gaps gate a launch.
- **Keep the Sheet as the human source of truth.** APIs feed it; they don't replace your judgment.
- **Never put an API key in the browser.** Use the importer/serverless pattern.
- **Free + graceful beats expensive + incomplete.** A polished placeholder + Wikidata covers the 80% that matters at $0.
- **Cost discipline.** Wikidata/Cloudinary free tiers and the Sheet keep recurring costs near zero; reserve paid options (Ballotpedia) for one-shot needs.
