# Adding a County — Build Playbook
*VoteYourViews.org — how to add a new county (Travis first), built to scale to all 254.*

This is the repeatable process. Travis is the first run; everything here is written so county #3–#254 is the same checklist. "Statewide block" = the 18 races identical on every Texas ballot (see `Docs`/memory `reference-ballot-structure`).

---

## 0. The model (read once)
- **One tab per county** in the master Google Sheet: `HaysCounty`, `TravisCounty`, … Each tab is that county's *full* ballot.
- **`HaysCounty` is the master** for the 18 statewide races (rows 2–37, color-coded light yellow).
- Every other county tab pulls those 18 races with **one formula** — `={HaysCounty!A2:AF37}` at the top — so statewide stays in sync forever. Below that go the county's **district-based** and **local** races.
- **The API (Democracy Works) gives the skeleton** (which races/districts/candidates exist). **We build the meat** (photos, hooks, office descriptions, and the 9 belief positions + evidence). The meat is the real work and the reason scale = a content effort, not a tech one.
- Sheet column layout (A–AF, 32 cols): `office, category, districtType, districtNumber, name, party, confirmed, description, summary, website, photo, [9 position cols A/B/C/D], hook1, hook2, uncontested, [9 evidence cols]`.

---

## 1. Set up the county tab (10 min)
1. Duplicate the column **header row** structure (copy row 1 from `HaysCounty`).
2. Create a new tab named exactly `<County>County` (e.g., `TravisCounty`).
3. In the new tab, **row 2, column A**, paste the statewide formula:
   ```
   ={HaysCounty!A2:AF37}
   ```
   → the 18 statewide races auto-populate (read-only mirror). Local races start **below** the spilled block.

## 2. Get the skeleton (which races/candidates) 
- **Preferred (when Democracy Works key is live):** query the API for the county to get its contests, districts, and candidate names/party/website. Confirm which **districts** apply (US House, State Senate, State House, SBOE differ by county).
- **Fallback (no API):** pull the official candidate list from the **county elections office** + Texas Secretary of State + Ballotpedia for that county's offices.
- Identify the three buckets for this county:
  - **District-based:** US House, State Senate, State House, State Board of Education (by the county's district numbers).
  - **Regional:** the county's Court of Appeals district (e.g., 3rd Court = Central TX).
  - **County-local:** County Judge, Commissioners (by precinct), DA/Criminal DA, District/County Clerk, Treasurer, JPs (by precinct), County Courts at Law, local District Judges, Sheriff, etc.

## 3. Enter the races (skeleton → sheet)
For each non-statewide race, add rows (one per candidate) below the statewide block with: `office, category, districtType, districtNumber, name, party, confirmed, website`. Leave the "meat" columns blank for now. Match the office-naming style already used in `HaysCounty`.

## 4. Write the office descriptions
- Plain, casual, "what it does + why it matters," **no candidate names**, low-propensity-voter friendly (same voice as the Hays descriptions).
- Statewide descriptions are inherited via the formula — only write the **county-specific** ones.

## 5. Candidate photos (tiered pipeline)
Always **download + self-host** (`images/candidates/<county>/first-last.jpg`); never hot-link. Statewide photos are shared (`images/candidates/statewide/`).
- **Tier 1 (auto): Wikidata/Wikimedia Commons** — statewide/federal/prominent/incumbents; clean license; script by name.
- **Tier 2 (semi-auto): official .gov** — `house.texas.gov`, `senate.texas.gov`, `txcourts.gov` for incumbents.
- **Tier 3 (manual): local/challengers** — candidate self-submission form (uploads photo + grants permission) or manual download.
- Every auto-match gets a quick human "is this the right person?" check (name collisions).

## 6. Write the candidate "meat"
For every candidate in the county's non-statewide races:
- **Hook 1** — short, bold one-liner.
- **Hook 2** — longer backstory; **verify facts** (some old bios were stale — accuracy-check before Beta).
- **The 9 belief positions** (A/B/C/D) + the matching **evidence** cell for each — researched from voting records, public statements, campaign sites. This is the core matching data and the most time-consuming step.

## 7. Wire the code (one-time per new county)
- The app currently fetches only the `HaysCounty` tab. Add a **county → tab mapping** so the app loads the right tab based on the user's looked-up county, and flip the county from placeholder (`available: false`) to live.
- District filtering must use the county's actual districts.
- (Hays uses ArcGIS for commissioner/JP precincts; replicate equivalent precinct lookup for the new county if it has precinct-based local races.)

## 8. QA before going live
- Address test: enter several addresses across the county → correct districts + correct races show.
- Out-of-county address → the waitlist modal still fires correctly.
- Every candidate has: photo, hook1, hook2, 9 positions, evidence, description.
- Spot-check matching math on a known profile.
- Confirm the statewide block matches Hays (formula working).

## 9. Polling (optional, low priority)
Per analytics, users want candidates >> polling. Baseline: link to the county's official elections page + "vote at any vote center in your county" where it applies. Don't over-build. (See memory `project-democracyworks`.)

---

## Scale notes (why this stays manageable)
- **Statewide = once.** Maintained only in `HaysCounty`, mirrored by formula. A statewide change updates everywhere automatically.
- **Per county, the only NEW work** is: district-based + local races' content (descriptions, photos, hooks, 9 positions). That's inherent — it's the product's value.
- **Photos** scale via Tier 1/2 automation + self-submission for the tail.
- **The bottleneck is research** (the 9 positions per candidate), so plan county rollout around research capacity, not code.

## The recurring cost
- Each **election cycle**, re-verify the statewide "paste block" (which seats are up rotates) and refresh candidates. Districts can change with redistricting.

---

# Appendix A — Photo automation (concrete solution)

Goal: auto-resolve as many candidate photos as reasonable, self-host them, leave a clean list for manual. Runs as a script (Python, using the service-account sheet access already set up).

### Pipeline
**Input:** candidate `name` (+ `office`/state for disambiguation), from the county tab.

**Step 1 — Wikidata lookup (Tier 1, the workhorse).**
1. `wbsearchentities` (Wikidata API) for the name → candidate entities.
2. Keep entities that are **humans** (`P31 = Q5`) and, when possible, match context (occupation = politician/judge, or a "position held" / "elections" tie to Texas) to cut name collisions.
3. Read the **image property `P18`** → Commons filename.
4. Build the image URL via Commons (`Special:FilePath/<file>` or the `imageinfo` API for a sized thumbnail).
5. Commons images are reuse-licensed → safe to host.

**Step 2 — Official .gov fallback (Tier 2).** For incumbents with no Wikidata photo: pull the headshot from the office's official site (`house.texas.gov`, `senate.texas.gov`, `txcourts.gov`). These are per-source scrapers (one small adapter each), used only for sitting officeholders.

**Step 3 — Download + self-host.** Save each found image to `images/candidates/<county>/first-last.jpg` (statewide → `images/candidates/statewide/`). Normalize size/crop.

**Step 4 — Report, don't auto-publish.** Output three lists:
- ✅ **Matched** — with a thumbnail link for a quick human "right person?" check.
- ❓ **Ambiguous** — multiple plausible entities; needs a human pick.
- ❌ **Not found** — goes to the manual / self-submission queue (Tier 3).

**Step 5 — Human approve → write sheet.** After the human glance, write the **self-hosted path** into the sheet's `photo` column (replacing fragile hot-links / filling blanks).

### Guardrails
- Only auto-pull from **clean-license** sources (Wikimedia Commons, public .gov). Never auto-scrape/republish copyrighted campaign or news photos.
- Always **self-host** — never leave a hot-link in the sheet (that's why current R photos are fragile).
- Every auto-match is **human-verified** before it goes live (name collisions are common down-ballot).

### Realistic coverage expectation — TESTED on Hays (June 2026)
Pilot ran Wikidata against the 12 Hays candidates with blank/fragile photos (all local/down-ballot): **0 useful matches** (the 1 "hit" was a wrong-person name collision — a JP candidate matched to a dead reality-TV star). Conclusion:
- Wikidata/Commons covers **prominent people only** (statewide execs, federal, known incumbents) — i.e., your **shared statewide block, which you build once**.
- It has **~0 coverage of local/down-ballot candidates** — which are exactly the **per-county NEW work**.
- **Therefore Tier 1 automation does NOT reduce the per-county photo burden.** It only mops up occasional prominent names. Do not over-invest in it.
- **The real scale solution is Tier 3 (candidate self-submission)** + manual sourcing. Treat Tier 1/2 as optional helpers for the prominent/incumbent few.
- Human verification is mandatory — the pilot's one match was wrong.

### Tier 3 — candidate self-submission (the scalable tail)
A `/candidate?id=slug` page where candidates upload their own photo and (optionally) take the questionnaire. Solves both the photo gap *and* photo-usage permission for down-ballot races where no clean public photo exists. (Already on the project to-do list.)
