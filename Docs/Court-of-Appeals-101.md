# Court of Appeals 101
*VoteYourViews.org — how Texas Courts of Appeals work, and what that means for the guide.*

## What they do
When someone loses a trial and says "the court got it wrong," the case doesn't jump straight to the Texas Supreme Court — it goes to a **Court of Appeals** first. These are the middle layer of the court system: panels of justices who review whether the trial was done right. No new witnesses, no juries — they read the trial record and hear lawyers argue. The vast majority of appeals **end here**; the Texas Supreme Court (civil) and Court of Criminal Appeals (criminal) take only a small fraction of cases further.

Trial court → **Court of Appeals** → Supreme Court (civil) / Court of Criminal Appeals (criminal)

## How the map works
Texas is carved into **14 numbered regions**, each with its own Court of Appeals, each covering a set of counties (listed in Government Code ch. 22):
- The **3rd** sits in Austin — 24 Central Texas counties including **Hays and Travis**.
- The **5th** is Dallas; the **8th** is El Paso; the **13th** is Corpus Christi/Edinburg; etc.

**Your county determines your court**, the way your address determines your congressional district. So for the guide these are *district races keyed by county* — researched once, served to every county in the region.

## The Houston oddity
Harris County is the exception: the **1st and 14th** Courts of Appeals cover the **same ten Houston-area counties**, sitting in the same building. Appeals get randomly assigned to one or the other — a historical artifact of Houston outgrowing one court. Consequence: **a Harris-area voter votes for justices on BOTH courts**, which is part of why Houston judicial ballots are so long.

## The 15th is different
Created in 2024, the **15th Court of Appeals is statewide** — it handles appeals in cases involving the State of Texas itself (suits against agencies, constitutional challenges). Every Texan votes on it, so in the guide it lives with the Supreme Court in the **Statewide** data, not the regional layer.

## How the elections work
- Justices are **elected in partisan races** (Texas is one of the few states that elects appellate judges) to **6-year staggered terms**.
- Each court has a **Chief Justice** plus numbered **Places**; only seats whose terms expire appear on a given ballot. (That's why a court may have one race on the 2026 ballot and another may have three — not missing data, just whose term is up.)
- Some seats draw only one candidate → shown as uncontested.

## What this means for the guide (2026 status)
- **All 21 regional COA races on the 2026 ballot are harvested** (Democracy Works, Jul 10 2026) into the `Districts` tab with `districtType: coa`, `districtNumber: 1–14`. The 3rd's rows carry the original researched content (Byrne/Liu); the rest are honest-Unknown skeletons pending research.
- The app filters `coa` races by `userDistricts.coa` (an array — Houston voters have two). **Shown only when the voter's region is known; hidden when unknown** (never over-shown). Hays/Travis are hard-wired to `['3']` in both address flows.
- **Missing piece: the county → region lookup table** (254 counties → 14 regions, from Gov't Code ch. 22). Once added, every Texan's ballot is complete above the county level. Note: the statutes website is a scrape-resistant JS app — source the table from txcourts.gov court pages, the print statute, or another authoritative copy, and spot-check against Democracy Works responses (each county's DW ballot names its COA races).
- The **15th COA lives in the `Statewide` tab** — don't move it to the regional layer.
