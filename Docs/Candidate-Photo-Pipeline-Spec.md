# Candidate Photo Pipeline — Spec
*VoteYourViews.org — an automated "photo machine" that sources, normalizes, and self-hosts candidate headshots, county by county, built to scale to all 254 Texas counties.*

> **Companion docs:** `Adding-a-County-Playbook.md` (Appendix A is the older photo-automation notes — this spec supersedes and expands it), `Candidate-Self-Submission-Spec.md` (the human-supplied tail), memory `project-democracyworks`.

---

## The problem we're solving
1. **Sourcing.** Ballotpedia has **no photo API**. Wikidata/Commons was tested on Hays down-ballot candidates → **0 useful matches** (Appendix A). So there is no single clean feed for *local* candidate photos — they live scattered across campaign sites, county .gov pages, and social profiles.
2. **Consistency / look.** Today's photos are a mess:
   - **Democrats** use a Google Drive folder Gina built for the primary guide — **backgrounds already removed**, uniform, good-looking.
   - **Republicans** use **external hot-links** — fragile (break when the source moves), inconsistent crop/background, partisan visual mismatch (R photos look worse than D, which is itself a nonpartisan-brand problem).
3. **Scale.** Travis is county #2 of 254. Anything manual dies at county #5. The pipeline **must be automated**, with a human only doing fast yes/no verification, never sourcing or editing by hand.

**Design goal:** every candidate ends up as a **self-hosted, background-removed, face-centered, uniformly-sized PNG** — so a Republican and a Democrat on the same card look like they belong to the same product. The "D photos look better" gap disappears because *every* photo runs the same processor, including re-processing the existing R hot-links.

---

## Architecture — 5 stages
A batch script (Python, reuses the service-account sheet access already set up). Runs **per county**. Reads that county's tab, processes every candidate with a blank/hot-linked photo, writes back a self-hosted path.

```
[1 ACQUIRE] → [2 PROCESS] → [3 VERIFY] → [4 PUBLISH] → [5 TAIL: self-submission]
 find a photo   normalize    is it the    write path     fill the gaps
                + bg-removal  right person  to sheet       automation can't
```

### Stage 1 — Acquire (multi-source resolver, in trust order)
For each candidate, try sources **highest-trust first** and stop at the first hit. Record `source` + `sourceUrl` + a `trust` level on every result (drives Stage 3).

| # | Source | Covers | Trust | How |
|---|--------|--------|-------|-----|
| 1 | **Self-submission upload** | the tail (any candidate) | **highest** — they sent it + consented | Already-uploaded file from `Candidate-Self-Submission-Spec`. No verification needed. |
| 2 | **Official .gov** | sitting incumbents | high | Per-source adapters: `house.texas.gov`, `senate.texas.gov`, `txcourts.gov`, county elected-official pages. |
| 3 | **Existing sheet photo (re-ingest)** | current R hot-links + D Drive photos | medium-high (already vetted by a human once) | Pull whatever URL is in the `photo` column today, run it through Stage 2 so it gets self-hosted + bg-removed. **This is how the R/D look gap closes.** |
| 4 | **Campaign website** | challengers with a site | medium | Fetch the candidate's `website` (already in the sheet). Take the page's `og:image`, or the largest face-containing image near the top. |
| 5 | **Ballotpedia page image** | **most candidates, incl. down-ballot — the broadest coverage we have** | medium — **per-image license check required, see Risks; do NOT pay for the API** | Photos are **not** in the paid API (confirmed June 2026 — the ~$6k API buys nothing for photos), but they ARE on the public candidate pages. Resolve the candidate's Ballotpedia URL (collected per playbook §2). **Read the image's copyright tag**: if freely reusable (GFDL/CC/PD), use it + attribution `"This image comes from the website Ballotpedia.org"`. If tagged non-free / "non-commercial use only", **do not copy it** — instead read the page for the photo's *original source* (campaign/social/.gov) and route to that source (#4/#2) or self-submission. |
| 6 | **Wikidata/Commons** | prominent/statewide only | medium (verify) | `P18` image. Per Appendix A, near-zero local coverage — keep as a cheap last automated pass for the statewide block, not a local solution. |

Output of Stage 1: `{candidate, imageUrl|file, source, sourceUrl, trust}` or **not-found** (→ Stage 5).

### Stage 2 — Process (the great equalizer)
Every acquired image runs the identical pipeline so output is uniform regardless of source:
1. **Face detect** (e.g. MediaPipe / OpenCV / `face_recognition`). Reject images with 0 or >1 faces → flag for review (avoids logos, group photos).
2. **Crop** to a consistent headshot ratio centered on the face (square, head-and-shoulders, fixed padding).
3. **Background removal** → transparent PNG. **Default tool: `rembg`** (open-source U²-Net, runs locally, **free** — matters at 254-county scale and Gina is cost-conscious). Optional quality upgrade: remove.bg API (paid, per-image) for hero/statewide photos only.
4. **Normalize** size (e.g. 512×512), color, and output **transparent PNG** — matching the look Gina already created for the D photos. The app card supplies the background, so every candidate sits on the same backdrop.
5. Save to `images/candidates/<county>/first-last.png` (statewide → `images/candidates/statewide/`). **Always self-host — never leave a hot-link** (that's the root cause of the fragile R photos).

### Stage 3 — Verify (minimize the human, don't eliminate)
Name collisions are the real failure mode (Appendix A's one Wikidata "match" was a dead reality-TV star). Rules:
- **Trust = highest/high (self-submission, .gov, re-ingested existing):** auto-approve, no human.
- **Trust = medium (campaign site, Ballotpedia, Wikidata):** require a human glance. Generate a **review sheet** — thumbnail + name + office + source link + Approve/Reject — so the human does **one-click yes/no**, never sourcing or editing.
- **0 or >1 faces, or download failed:** route to the not-found / self-submission queue.

### Stage 4 — Publish
After approval, write the **self-hosted path** into the sheet `photo` column via the service account, and set `source` accordingly (`api`/`manual`/`api+manual` per playbook). Re-runs are idempotent: skip candidates already self-hosted unless `--force`.

### Stage 5 — The tail (what automation can't reach)
Whatever is still not-found goes to **candidate self-submission** (`Candidate-Self-Submission-Spec.md`): the "Is this you? Claim your profile" link on the card. Their upload re-enters at Stage 1 source #1 with consent attached. **This is the only true scale solution for the long tail** — automation mops up the findable; self-submission covers the rest and fixes photo *permission* at the same time.

---

## Per-county run = one command
```
photo-machine --county travis            # process Travis tab end to end
photo-machine --county travis --review   # open the review sheet for medium-trust hits
photo-machine --county travis --force    # re-process even already self-hosted
```
Adds **zero per-county code** — it reads the county tab and that county's candidates. (Endpoint discovery like the GIS precinct lookups is *not* needed here; photos are sourced per-candidate, not per-county-service.)

## Reusability — one script, all counties (build once)
**This is the core scale property: the script is county-agnostic. The county is just an argument.** Build it for Travis; run it on county #3–#254 by changing one flag. Nothing inside changes between counties.

- **Why it carries over cleanly (and the precinct lookup did NOT):** the GIS precinct work needed per-county wiring because every county runs *its own GIS service* with different endpoints and field names — genuinely new code each time. Photos are the opposite: the source is **per-candidate** (each candidate's own Ballotpedia/campaign/.gov page), not per-county. There's no "Travis photo server" vs "Harris photo server" — it's the same handful of statewide sources for every candidate in Texas. So the script has nothing county-specific to learn.
- **What's driven by row data, not code:** county name → which tab to read and the `images/candidates/<county>/` output folder; each candidate's Ballotpedia URL / `website` → where to fetch; party/name → filename. All of it lives in the sheet, so the same code path handles every county.
- **The one optional per-county add:** the `.gov` incumbent-photo adapters (Stage 1 source #2: `house.texas.gov`, `txcourts.gov`, etc.) are **statewide and reused as-is**. If some future county leans on a county-specific official site for incumbent headshots, you add **one small adapter** — an enrichment, not a rebuild. The Ballotpedia + campaign-site + self-submission path already covers every county with no changes.
- **Net:** build + harden once on Travis (+ the Hays back-fix below as a second real test), then county rollout is `photo-machine --county <name>` + the human one-click review pass. No code rewrite per county.

## First run target: Travis + back-fix Hays
1. **Travis** — full pipeline run (most candidates have no photo yet).
2. **Hays back-fix** — re-ingest the existing R hot-links and D Drive photos through Stage 2 so **both parties become uniform self-hosted bg-removed PNGs**, killing the "Democrats look better" gap and the fragile external links in one pass.

---

## Risks / open decisions (flag before building)
- **Ballotpedia — usable, but NOT via the API, and per-image.** Two separate facts:
  - **Don't buy the API for photos.** Confirmed June 2026: photos are NOT in Ballotpedia's paid (~$6k) API. It buys nothing for this pipeline.
  - **The public pages DO have most candidates' photos, and reuse IS permitted for non-commercial use with attribution** (`"This image comes from the website Ballotpedia.org"`, GFDL) — **but per-image**: many candidate headshots are tagged "non-commercial use only" and confer **no** reuse rights elsewhere. So Stage 1 source #5 is **on, conditionally**: take only freely-tagged images; for non-free ones, use the page to find the original source instead (see Stage 1 table).
  - **Two confirmations to lock down** (one email to `editor@ballotpedia.org`): (1) that VoteYourViews qualifies as **non-commercial** reuse (we're free, nonpartisan, no ads — strong case, but confirm as an org), and (2) acceptable **bulk/automated** access (their ToS view on scraping at volume; ask if they'll bless it or offer a freely-licensed image feed). Until (1) is confirmed, treat Ballotpedia as discovery-only (find original source) rather than copying their hosted image.
- **Copyright on campaign-site photos.** A campaign photo's copyright belongs to the photographer, not the candidate. Safest path for republish rights is **self-submission consent** (Stage 5). Campaign-site scraping (source #4) is a gray area — acceptable for a nonpartisan voter guide under fair-use arguments, but self-submission is the clean fix and should be pushed for contested cases.
- **rembg vs remove.bg.** Default `rembg` (free, local, scales to 254 counties). Reserve paid remove.bg for the handful of statewide/hero shots if quality demands it. Decision is reversible — same interface.
- **Face-match strength.** v1 verification is a human glance on medium-trust hits. A later upgrade could add automated face-vs-reference matching, but only where a trusted reference photo already exists — not worth building for v1.

## What stays out of scope (v1)
- No automated identity proofing of self-submitters (handled in the self-submission spec).
- No video/animated avatars.
- No real-time/on-demand fetch — this is a **batch** that runs when a county is built or refreshed.
