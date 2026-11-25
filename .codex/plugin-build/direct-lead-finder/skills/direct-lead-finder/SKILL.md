---
name: direct-lead-finder
description: Find individual people likely to hire Muhammad Azeem as an all-in-one freelance developer and add qualified leads with outreach drafts to the Direct Leads tab of the International Leads Google Sheet. Use when the user says "find direct leads" or asks for direct freelance lead research.
---

# Direct Lead Finder

Find qualified individual prospects using public web sources, verify every signal, avoid duplicates, and add the best leads to the user's Google Sheet. Never contact anyone; only research and draft outreach.

## Tool and access requirements

- Use public web search and open every source used as a signal.
- Use an available connected Google Sheets or Google Drive tool to read and update the spreadsheet named `International Leads`.
- If spreadsheet access is unavailable, do not invent existing rows or claim that leads were added. Explain that the user needs to connect a Google Sheets/Drive-capable app, and offer to return a reviewable table instead.
- Never bypass platform access controls or use scraping that violates a site's terms.

## Offer

Muhammad Azeem is an all-in-one full-stack developer with 5+ years of experience. He handles frontend, backend, database, deployment, and AI features as one developer rather than a small team. His stack includes React, Next.js, TypeScript, Node.js/NestJS, PostgreSQL, Odoo, and LLM/AI integrations. He works remotely from Pakistan, 4–5 hours ahead of the UK/EU and 2 hours ahead of Saudi Arabia, and is available for freelance, contract, or part-time retainers.

## Proof links

Choose only the most relevant proof link. Never claim that a project does something it does not.

- OdooPilot: https://www.odoopilot.ai/ — an AI-powered Odoo platform for scoping, configuring, and customizing Odoo. Use for Odoo, ERP, or AI needs.
- AI Shop Solutions: https://www.aishopsolutions.com/ — an all-in-one business-management platform covering inventory, customers, accounting, scheduling, and POS. Use for SMEs, dashboards, and internal tools.
- Portfolio: https://azeem-portfolio-six.vercel.app/ — use for MVPs, web apps, and other relevant work.

## Markets

Search the UK/EU and Saudi Arabia/UAE by default. Search the US only when the user asks.

## Lead priorities

Search in this order:

1. **Active request:** a person who publicly posted within the last 14 days that they need a developer, technical co-founder, MVP, site rebuild, or AI feature.
2. **Non-tech founder:** a founder of an early-stage startup, pre-seed through seed, whose team page or announcements show no CTO or engineering lead.
3. **Solo founder:** a founder with a Product Hunt launch, pre-seed announcement, or "we're live" post within the last 60 days.
4. **Agency owner:** the founder or managing director of a small digital, design, or marketing agency with roughly 5–50 people that builds websites or apps for clients.
5. **Odoo partner:** the owner or technical lead of a small Odoo implementation partner.

Aim for at least 3 Active requests in every batch of 10, but never lower quality or pad the batch to reach a quota.

## Public sources

- Public posts discoverable in web search: LinkedIn and X results, Indie Hackers, Reddit hiring threads such as r/forhire `[Hiring]` posts, and startup-community job boards.
- Launch and funding coverage: Product Hunt, EU-Startups, Sifted, Wamda, MAGNiTT, and Arab News startup coverage.
- Agencies: company websites and directory pages such as Clutch.
- Odoo partners: the public Odoo partner directory at https://www.odoo.com/partners.

Rotate markets and query wording between runs. Useful query patterns include:

- `"looking for a developer to build MVP"`
- `"need a Next.js developer" freelance`
- `"looking for technical cofounder" Riyadh`
- `"hiring freelance full stack developer" UK`
- `"need Odoo developer"`

## Exclusions

Skip:

- Active requests older than 14 days, and launches or funding signals older than 60 days.
- Requests marked filled, closed, or indicating that someone was found.
- Free, equity-only, or unpaid-trial requests, spam, and likely scams.
- Jobs requiring local residency or country-specific work authorization without a contractor option.
- Large companies with established engineering teams.
- Anyone already present in the `Direct Leads` or `People` tabs, matching on name plus company or on profile URL.
- Patterns previously disqualified in the sheet's Notes.

## Spreadsheet workflow

When the user asks to find direct leads:

1. Open the `International Leads` spreadsheet. Read the `Direct Leads` and `People` tabs before searching. Collect existing names, companies, and profile URLs. Read Notes for rows whose status is `disqualified`, and avoid the same problems.
2. Determine the next Lead ID by finding the highest existing `D-0001`-style ID and incrementing it without gaps caused by the current batch.
3. Search in priority order, rotating markets and query wording from prior runs when history is available.
4. Open every post, page, or article before accepting it. Confirm that the person, role, company, date, need, and open status are supported by the source.
5. Rank candidates by fit, recency, evidence quality, and practical contact channel.
6. Append up to 10 new rows, best first. Add fewer when fewer qualify.
7. Write outreach drafts for High- and Medium-confidence leads. Leave draft fields blank for Low-confidence leads unless the user explicitly asks otherwise.
8. Re-read the appended range to verify the values, IDs, column alignment, and draft lengths.
9. Summarize the leads added with name, company, lead type, need, and channel, plus notable skips and reasons.

## Direct Leads columns

Write columns in exactly this order:

`Lead ID | Name | Title | Company | Website | Country | Lead type | Their need | Signal URL | Signal date | Confidence | Profile URL | Channel | First message | Follow-up | Contact status | Date added | Notes`

Field rules:

- **Lead ID:** continue from the highest existing `D-0001`-style ID.
- **Lead type:** exactly one of `Active request`, `Non-tech founder`, `Solo founder`, `Agency owner`, or `Odoo partner`.
- **Their need:** one factual line, such as `Posted: needs an MVP for a logistics booking app`.
- **Signal URL:** the exact public post, launch, article, directory, or company page actually opened and verified.
- **Signal date:** use the source's published date. Do not infer an exact date from a vague timestamp unless the interface reliably resolves it.
- **Confidence:** `High` when name, role, and company are confirmed by two or more sources or the person's own company site; `Medium` for one reliable source; `Low` when any important fit judgment is inferred.
- **Profile URL:** a LinkedIn or other public professional profile only when it appeared in search results or another opened public source.
- **Channel:** exactly one of `Reply to post`, `LinkedIn connect`, `LinkedIn DM`, `X DM`, or `Email listed in post`. Use email only when the person published it in the post.
- **Contact status:** always `to-contact`.
- **Date added:** today's date in the user's local timezone.
- **Notes:** include `verify on LinkedIn` for Medium- and Low-confidence leads. Add concise factual caveats where useful.

## Drafts

### First message

For an Active request, write a direct reply of at most 500 characters. Address the exact need, give a one-line approach, include one relevant proof link, and end with one question. Do not use a generic introduction.

For every other lead type, write a LinkedIn connection note of at most 200 characters, or at most 300 only when the user says they have Premium. Include one specific factual observation about the person or company. Do not pitch and do not include links.

### Follow-up

Write 3–4 sentences for after the person accepts or replies. Make one concrete offer tied to the situation, include one relevant proof link, and end with a low-pressure question.

- Non-tech or Solo founder: offer one developer who can build and run the whole product across frontend, backend, and AI.
- Agency owner: offer reliable white-label capacity for client projects.
- Odoo partner: offer extra Odoo development and AI-feature capacity, linking OdooPilot.

Example Active-request reply:

> Hi Daniel, I can build this. For a booking MVP like yours I'd use Next.js + NestJS + PostgreSQL and get a working first version live in a few weeks. Here's a recent platform I built end-to-end: https://www.aishopsolutions.com/. Do you already have designs, or should I start from a simple wireframe?

Never write `I hope this finds you well`, `I came across your profile`, `cheap`, or `low-cost`. Avoid flattery, prices, unverifiable delivery promises, and claims outside the documented offer.

## Data and safety rules

- Never guess names, titles, profile URLs, dates, or email addresses.
- Every row requires a Signal URL that was actually opened.
- Record professional business information only: name, title, company, and the publicly stated or evidenced business need.
- Do not collect personal details.
- Never send messages, replies, emails, or connection requests. Only save drafts in the sheet.
- If a source is inaccessible, ambiguous, stale, or contradictory, skip the lead rather than filling gaps with assumptions.
