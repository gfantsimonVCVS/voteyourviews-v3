# Candidate Self-Submission — Feature Spec
*VoteYourViews.org — let candidates supply their own photo, positions, and bio.*

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
