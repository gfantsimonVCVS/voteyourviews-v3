# Candidate Self-Submission — Feature Spec
*VoteYourViews.org — let candidates supply their own photo, positions, and bio.*

> **Two designs in this doc:** (1) the original **separate form** (`/candidate?token=…`) — sections below; and (2) the newer **edit-in-place** vision — clean per-candidate URLs with an inline Edit button on the real profile page. See **"V2 — Clean URLs + edit-in-place"** at the bottom. V2 is the preferred long-term shape; the form is the simpler fallback. Both share the same backend, approval gate, and field-scoping rules.

> **Not to be confused with** the `statement_submissions` sheet tab, which is for **organizations** to suggest edits to the 3 belief statements per issue. This spec is **candidates** populating/correcting **their own profile**.

## Why this exists (the payoff)
Solves three problems at once for down-ballot/local candidates who aren't in any database (where Wikidata fails and Ballotpedia may not reach):
1. **Photo** — they upload it.
2. **Photo permission** — their consent grants republish rights (fixes the licensing gray area).
3. **The 9 belief positions** — they answer the questionnaire themselves, so matching works and is authentic ("what the candidate said about themselves").

## Core mechanic
The candidate **takes the same voter questionnaire** — their Agree / Disagree / No Opinion answers on the 9 statements map directly to their A/B/C/D position columns. Same framework voters use → matching "just works."

## Two doors into the SAME form
1. **Push — private link (high trust):** `/candidate?token=…` sent directly to candidates Gina knows. The token proves identity; no login needed.
2. **Pull — "Is this you?" (scales itself):** a subtle link on the **Candidate Profile card** — *"Is this you? Claim or update your profile →"* — so candidates find us. No outreach required.

Support **both**: links for known candidates, inbound discovery for everyone else.

## The form (shared by both doors)
- Pre-filled: name, office, party (from the skeleton) — candidate confirms.
- **Photo upload.**
- **9-statement questionnaire** → maps to position columns (A/B/C/D).
- Optional: campaign **website**, a short **"in their own words"** statement (raw material for hook2/evidence), contact.
- **Consent checkbox** — explicit permission to publish photo + responses (this is what grants photo rights). Capture timestamp.

## Identity verification (the hard part — only for the "Is this you?" door)
With a private link, the token = identity. With open self-claim, we must prevent impersonation (incl. a rival editing an opponent's card). Levels:
- **MVP — human approval gate:** every submission lands in a **pending** queue; **nothing goes live until Gina approves.** She verifies at review (knows many candidates; cross-checks campaign site / official filing). Cheapest, build this first.
- **Stronger (add later if needed) — email-to-official-contact:** candidate enters their campaign email; system emails the edit link there (better: to the official contact already on file from Ballotpedia/county). Only inbox-holder can submit — converts an open claim back into a secure link.
- **Launch with human approval; add email verification only if impersonation becomes a problem.**

## Backend (the app is static — needs one server piece)
- **Text answers → Google Sheet** via an Apps Script web app (same proven pattern as the mailing-list capture).
- **Photo → Google Drive** via Apps Script (receive file, save to Drive, write the Drive URL into the sheet). Keeps everything in Gina's ecosystem.
- Submissions write to a **pending tab** (e.g., `candidate_submissions`), NOT directly to the live `*County` tabs.

## Review / approval workflow
1. Submission → `candidate_submissions` (pending) tab.
2. Gina reviews: legit person? photo OK? answers reasonable?
3. On approve → data is mapped into the candidate's row in the live county tab: `photo`, the 9 positions, `website`, and `hook2`/evidence raw material (Gina polishes the hooks).
4. Nothing auto-publishes.

## Anti-spam (light)
- Rate-limit submissions; a "how did you hear about us" field; the approval gate catches the rest.

## What it deliberately does NOT need
- No user accounts, no passwords, no public candidate discovery directory, no payment. Token links + "Is this you?" + an approval gate keep it lightweight and safe.

## Bonus value
- **Correction channel:** "Is this you?" also lets candidates fix a wrong photo/position we have.
- **Inbound growth:** extend with an *"Are you a candidate? Add your race"* entry for races not yet in the guide.

## Tradeoff summary
- **Push (private links):** high trust, but Gina does the outreach.
- **Pull ("Is this you?"):** scales itself, but requires the approval gate to block impostors.
- **Do both.**

---

# V2 — Clean URLs + edit-in-place (the next evolution)
*The preferred long-term shape: every candidate has a shareable URL, and their team edits the real page directly behind a login — instead of filling out a separate form.*

## The idea
- Every candidate profile lives at a clean URL: **`voteyourviews.org/JamesTalarico`**.
- The page shows the normal public profile. For a logged-in candidate (or their team), an **"Edit this page"** button appears, unlocking **inline editing of safe fields right on the page**.
- Edits go to a pending queue → Gina approves → live. (Same gate as the form.)

## Why it's better than the separate form
- **Shareable + SEO:** candidates put `voteyourviews.org/TheirName` on their own site and socials; their name ranks in search. Free distribution.
- **No context switch:** they edit what they actually see, in place — higher completion than a separate form.
- **One canonical page** instead of form + profile drifting apart.

## Piece 1 — Clean per-candidate URLs (small, do anytime)
- The app is a single static `index.html`. Add a Netlify redirect so `/:slug` serves `index.html` (SPA-style), then the app reads the slug from `location.pathname`, finds the matching candidate, and renders their profile directly.
- Slug = candidate name slugified (`james-talarico` or `JamesTalarico`); store a `slug` column in the sheet to keep it stable and avoid collisions (two "John Smith"s → `john-smith-hd50`).
- This piece needs **no backend** and can ship independently of editing.

## Piece 2 — Auth (the part a static site can't do alone)
**Hard rule (today's lesson):** the Google Sheet write key must **never** reach the browser. Editing therefore needs a server piece.
- **Use Netlify Functions** (serverless) — upgrade path from the Apps Script approach, or keep Apps Script if preferred. The function holds the secret and does the writing.
- **Passwordless magic-link auth** (recommended): candidate enters their email → function emails a one-time signed link → clicking it grants a short-lived edit session. **No passwords for Gina to store, none for anyone to mishandle.**
- Only emails on an **approved allow-list for that specific candidate** can unlock editing (prevents a rival from claiming an opponent's page). The allow-list is seeded from the official contact on file (county filing / Ballotpedia) or added by Gina.

## Piece 3 — Inline edit UI + pending/approval
- Edit button reveals editable fields in place; Save posts to the Netlify Function.
- Function writes to the **pending tab** (`candidate_submissions`), never the live county tab.
- Gina reviews → approve maps it into the live row. Nothing auto-publishes. (Identical to the form workflow above.)

## Field scoping (credibility guardrail — important)
The guide's value is **independent research.** If candidates write their own belief positions, they'll soften them and the tool loses meaning. So:
- ✅ **Candidate may edit:** photo, bio / "in their own words" statement, campaign website, contact info, social links.
- 🔒 **Team-controlled (or clearly labeled):** the 9 belief positions. Either keep them research-only, **or** show candidate-submitted positions tagged **"candidate's claim"** distinct from the team's **"✓ verified"** research — never silently let a candidate overwrite the researched stance.
- This keeps the matching honest while still letting candidates fix photos/bios fast.

## Build order
1. **Clean URLs + slug routing** — no backend, ship first (immediate sharing/SEO win).
2. **Netlify Function + magic-link auth + pending/approval** — the real infrastructure.
3. **Inline edit UI**, scoped to safe fields, with the "candidate's claim" vs "verified" labeling.

## Still deliberately avoided
- No public account system, no passwords (magic link only), no candidate directory, no payment. Auth is per-candidate allow-list + one-time links; safety still rests on the **approval gate**.
