# Hand-off File Template

Copy this structure for `<vendor>-api-handoff.md`. Every factual claim must be tagged **confirmed** (fetched/verified firsthand), **inferred** (community artifact suggests), or **unknown** (stated plainly, not smoothed over).

```markdown
# <Vendor> API — Agent Hand-off Reference

## 1. Machine-readable sources
(verified URLs, formats, auth-required-or-not, retrieval date)

## 2. Authentication
(exact headers, example, token/region notes, sanity endpoint if one exists)

## 3. Rate limits & error semantics
(numbers with source, empty-result behavior, redirect behavior)

## 4. API groups / endpoint catalog
(table of areas → endpoint counts/paths, write endpoints flagged)

## 5. Out-of-band systems
(webhooks, event streams, worker queues — anything not in the spec)

## 6. Ready-to-paste agent prompt
(a literal paragraph the user can give any coding agent)

## 7. Verification log & unknowns
(what was verified, via what; what couldn't be checked; staleness risks)
```

## Section guidance

1. **Machine-readable sources** — list every candidate found, best first, each with format (OpenAPI 3.x / Swagger 2.0 / Postman / SDK), whether auth is needed to retrieve it, the region shard it was verified on (`{region}` placeholders for anything not), and the retrieval date.
2. **Authentication** — exact header shape as a copy-pasteable example, token lifetime, how to obtain credentials, and a cheap read-only sanity endpoint if one exists.
3. **Rate limits & error semantics** — numbers plus where they came from, what happens on violation (429? penalty window?), empty-result behavior (200-with-empty vs 404), envelope/JSON:API conventions.
4. **Endpoint catalog** — group by area with counts; flag every write method (POST/PUT/PATCH/DELETE) so the integrating agent knows the blast radius.
5. **Out-of-band systems** — webhooks/event streams the spec doesn't cover, with registration pointers.
6. **Ready-to-paste agent prompt** — one literal paragraph containing: base URL, auth header shape, rate limit, pagination style, where the spec lives, and what is still unknown. Written to be pasted into any coding agent cold.
7. **Verification log** — checks run vs. checks not run (e.g. "no live authenticated call made — no creds provided"), and staleness risks (vendored community spec may lag).
