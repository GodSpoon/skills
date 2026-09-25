---
name: api-spec-hunt
description: "Use when asked to find a vendor's API docs or OpenAPI/Swagger spec, check whether a platform's API is agent-consumable, or hand an agent enough to build an integration. Locates the machine-readable contract (OpenAPI > Postman collection > code-generated SDK > human docs) on the vendor's second host, probes conventional spec paths with a bundled stdlib prober, triangulates existence via SDKs/MCP servers/apis.guru, sweeps behavioral facts (auth, rate limits, pagination, webhooks), and emits one handoff markdown file — then optionally generates a single-file Python CLI from the spec. Keywords: API spec, OpenAPI, swagger, Postman collection, API documentation hunt, vendor API reference, integration."
---

# API Spec Hunt

Locate and verify the official machine-readable API definition for a vendor, then produce a single hand-off file an agent can integrate from directly — and optionally generate a CLI from it.

Core insight: MSP/SaaS vendors keep marketing/training docs on Zendesk/Confluence-style hubs, but the renderable API reference almost always lives on a **second host** (docs engine or the API server itself). Finding that second host — not reading the doc hub — is the job.

## When to Use

- "Find the API docs / OpenAPI spec for `<vendor>`"
- "Is there a swagger spec for `<vendor>`?"
- "Give an agent enough to integrate with `<vendor>`"
- Any request to evaluate or catalog a vendor's API surface

Don't use for a service that already has a maintained CLI or skill (use that), and only probe hosts the user owns or is permitted to test.

## Inputs to gather first

- Platform name (required).
- Optional: known API subdomain, tenant/region URL, product tier. Many MSP tools split APIs per product line (PSA vs RMM, monitoring vs billing) — enumerate them rather than asking, ask only if genuinely ambiguous.
- If the caller has tenant access, note their instance URL — API hosts and docs are commonly region-sharded (`{region}.api.vendor.com`).

## Quick Reference

All scripts are stdlib-only (PyYAML optional, used for YAML specs only) and safe to run in a sandboxed terminal.

```bash
# Probe a host at ~58 conventional spec paths (bare /spec included)
terminal(command="python3 <skill_dir>/scripts/spec_hunt.py https://api.vendor.com")

# http-only internal/self-hosted API, plus GraphQL introspection
terminal(command="python3 <skill_dir>/scripts/spec_hunt.py http://192.168.1.10:8080 --graphql-probe")

# Extra candidate paths (replaces the defaults), machine-readable output
terminal(command="python3 <skill_dir>/scripts/spec_hunt.py https://api.vendor.com --paths hints.txt --json")

# Confirm a fetched spec is really an OpenAPI/Swagger/AsyncAPI doc
terminal(command="python3 <skill_dir>/scripts/spec_hunt.py --verify ./downloaded-spec.json")

# List the operations a spec exposes, then generate a CLI from it
terminal(command="python3 <skill_dir>/scripts/spec_to_cli.py --spec openapi.json --list")
terminal(command="python3 <skill_dir>/scripts/spec_to_cli.py --spec openapi.json --out api_cli.py")
```

A bare host is treated as `https://<host>`; an explicit `http://` is honoured as given. Exit codes: `0` = spec found (or verified), `1` = nothing found / not a spec.

Searches that pay off repeatedly (run several in parallel with `web_search`):

```text
<vendor> API OpenAPI specification
<vendor> API documentation endpoints        → finds the official doc hub
<vendor> swagger json spec                  → catches renamed/legacy engines
site:github.com <vendor> openapi            → codegen SDKs prove a spec exists
<vendor> MCP server github                  → tool defs = de-facto endpoint catalog
site:apis.guru <vendor>                     → official-directory flag
"<host>/spec"  OR  site:<host> spec openapi → search indexes raw specs fetchers can't render
```

## Procedure

Run phases in order. **Stop the moment a spec verifies (Phase 4).** Don't crawl prose docs if a spec URL is confirmed.

### Phase 0 — Scope (1 min)
Identify product/tier and region/instance. Note multiple API products if the vendor has them.

### Phase 1 — Docs recon
Run the three vendor searches above in parallel. Output: doc hub URL, developer portal URL, named API products.

### Phase 2 — Find the second host
- Fetch the doc hub index with `web_extract`; look for tells: *"opens in a new window"*, *"developer portal"*, *"API reference"*.
- If the fetch comes back stripped/truncated (Zendesk/Kustomer SPAs do this), don't fight it — search for things that *quote* the real host instead:
  - `<vendor> api reference` + `dev.` / `developer.` / `api.` subdomain guesses
  - A plausible API path as a search query (`/v1/`, `/api/v2/`, product nouns like `/inventory/`, `/tickets/`, `/devices/`) — searching `auvikapi /v1/inventory/device/info` surfaced `auvikapi.us1.my.auvik.com/docs` directly in results.

### Phase 3 — Probe spec endpoints
Run `spec_hunt.py` against **every candidate host** (doc host AND api host). It reports a verdict per path:

| Verdict | Meaning |
|---|---|
| `spec` | A real OpenAPI/Swagger/AsyncAPI document. Full stop. |
| `spec-likely` | YAML or spec-shaped JSON that could not be fully parsed (install PyYAML to confirm). |
| `gated` | 401/403 — **the endpoint exists but needs auth**. A hit, not a miss. Record it. |
| `docs-ui` | An interactive docs page. Its note usually quotes the real spec URL (`spec-url=`, `url:`). |
| `unknown` / `html` | Present but not a spec. |
| `absent` | 404/405. |
| `unreachable` | The host never answered — **not** the same as absent. See Pitfalls. |

Doc-engine fingerprints and where the spec hides — a JS/SPA page means `web_extract` sees nothing, but the page must load its spec from a JSON URL:

| Page is... | Fingerprint in HTML | Where the spec usually hides |
|---|---|---|
| Swagger UI | `swagger-ui` bundle | `url:` param or `/swagger/v1/swagger.json` |
| Redoc | `<redoc spec-url="..">` | the `spec-url` attribute value |
| Scalar | `@scalar/api-reference` | `specUrl` / `configuration` in page JS |
| Stoplight Elements | `<elements-api` | `apiDescriptionUrl` |
| ReadMe.io | `readme.com` markup | add `?export=1` or find Download OpenAPI link |
| GitBook | gitbook assets | usually no spec; fall to human doc crawl |

If `spec_hunt.py` finds `docs-ui` but the note quotes no URL, fetch that page and read the config blob. If fetches fail entirely (bot-blocking), search-engine probe instead: `site:<host> spec openapi` or `"<host>/spec"` — indexes often carry the raw spec even when fetchers can't render it (that's how Auvik's `/v2/api/spec` surfaced).

### Phase 4 — Existence-proof via artifacts (parallel with Phase 3)
Artifacts that could only exist if a spec exists — they confirm existence AND often name the endpoint:
- Codegen tooling (`oapi-codegen`, NSwag, OpenAPI Generator configs, `generate.go`) — README/config usually names the spec URL.
- MCP server repos — someone normalized the API surface; tool definitions are a de-facto endpoint catalog even without a public spec.
- APIs-guru openapi-directory entry — an `Official: YES` flag is strong evidence.
- Vendored spec copies in repos — useful for cataloging but **flag as possibly stale**; verify against the live host.

**Triangulation rule:** one source found = a lead; three independent consumers agreeing on the same URL = the answer.

### Phase 5 — Fallback ladder (only when no public spec exists)
Best-first machine-consumable substitute. See [references/undocumented-apis.md](references/undocumented-apis.md) for the full playbook (finding unadvertised specs, HAR capture via proxy, hand-written OpenAPI stubs):
1. Official Postman collection (Postman API Network / vendor workspace)
2. Official SDK with typed clients/codegen hints (repo `docs/`, `/spec/`, codegen scripts)
3. Vendor-hosted docs with consistent machine-friendly structure (GitBook/ReadMe per-endpoint pages — crawlable into Markdown)
4. Community OpenAPI conversion — label **unverified**
5. Hand-built distilled reference — you crawl endpoint pages and emit paths/methods/params/auth yourself; flag **unofficial and incomplete**

### Phase 6 — Behavioral facts sweep (always)
Specs describe shapes; integration guides describe behavior — hand the agent both or it learns rate limits from a 429. Search `<vendor> API rate limit`, `<vendor> API authentication`, `<vendor> API changelog` and extract:
- Auth scheme + exact header shape + token lifetime
- Rate limit numbers + penalty behavior
- Region selection / redirect behavior (e.g. HTTP 308 to the right shard)
- Error semantics (200-with-empty? envelope? JSON:API?)
- Pagination style + default page size
- Write-vs-read endpoint split (agent must know the blast radius)
- Out-of-band systems: webhooks, event streams — anything not in the spec

### Phase 7 — Verification
Minimum bar before calling it done:
- Spec parses as OpenAPI 2/3, Swagger, or AsyncAPI (`spec_hunt.py --verify` checks the top-level `openapi`/`swagger`/`asyncapi` key, plus `paths`, `servers`/`host`).
- Endpoint count plausibly matches the doc-side endpoint list.
- Auth + at least one read endpoint shape consistent with the vendor's getting-started doc.
- State explicitly which checks were and were NOT run (e.g. no live authenticated call unless creds were provided).

## Generating a CLI from the spec

Once a spec verifies, `spec_to_cli.py` turns it into a self-contained, stdlib-only Python CLI — one subcommand per operation — so the agent has a working client instead of prose. This is the fastest way to prove the spec is real and usable.

```bash
python3 <skill_dir>/scripts/spec_to_cli.py --spec openapi.json --list          # see operations
python3 <skill_dir>/scripts/spec_to_cli.py --spec openapi.json --out api_cli.py
API_TOKEN=$TOKEN python3 api_cli.py --base-url https://api.vendor.com list-pets --limit 3
```

- The generated CLI reads its bearer token from the env var named by `--token-env` (default `API_TOKEN`). Never hardcode a token.
- Relative `servers[].url` values (e.g. `/api/v3`) are anchored to the spec's own origin; if you fetch the spec to disk, pass `--base-url`.
- Pin the spec next to the generated CLI (`<vendor>.openapi.json`) so the interface can be diffed later, and regenerate rather than hand-editing the generated file.

## Output

Emit **one** hand-off file (save as `<vendor>-api-handoff.md` in the workspace) plus a 3-paragraph chat summary. Never dump the full spec into chat. Use the template in [references/handoff-template.md](references/handoff-template.md).

Hard rules:
- Distinguish **confirmed** (fetched/verified) from **inferred** (community repo suggests) from **unknown** (state it; don't smooth over).
- Quote region/instance placeholders as `{region}` patterns — never silently bake in one tenant's values.
- If the spec URL requires auth or a tenant, say exactly how the agent gets it.
- Record the retrieval date — specs drift.

## Pitfalls

- **Doc hubs are decoys.** Zendesk/Kustomer articles describe endpoints in prose and are useless for agents. They're only useful for the tell that points at the second host.
- **Fighting SPA fetches.** If two `web_extract` attempts return stripped content, pivot to search-engine probing — don't keep retrying the same fetch.
- **Claiming on one source.** A vendored spec in a random repo may be two major versions stale. Verify against the live host or triangulate before writing "official".
- **Spec ≠ behavior.** A perfect OpenAPI doc won't mention rate limits, 308 redirects, or 200-with-empty semantics. The behavioral sweep is not optional.
- **Region sharding.** A spec found on `us1.` does not mean `eu1.` behaves identically — note the shard you verified.
- **401/403 is a hit, not a miss.** The endpoint exists; it needs auth. Record it — a cluster of `gated` paths around a prefix often proves a spec lives there.
- **Silence is not evidence of absence.** An `unreachable` verdict means the host never answered; it has NOT been ruled out. Never record it as "no spec found" — check the scheme (http vs https), DNS, TLS, and VPN/allowlist first.
- **Big specs are normal.** A ~50-path OpenAPI doc runs ~600 KB. Never truncate a spec before parsing it, and don't mistake a large document for a malformed one.
- **Don't probe hosts you don't own.** Active spec scanning against third parties is abuse, not research. Read vendor docs instead.

## Verification

```bash
terminal(command="python3 <skill_dir>/scripts/test_api_hunt.py")   # 22 offline tests, no network
```

End-to-end proof against the worked example (Auvik): unauthenticated OpenAPI 3.0.1 at `https://auvikapi.us1.my.auvik.com/spec`, ~50 paths, with the surrounding conventional paths returning 401 (`gated`) — behavioral facts from the integration guide, webhooks flagged out-of-band, one markdown artifact.

The run is complete when: the hand-off file exists with all seven template sections filled, every factual claim in it is tagged confirmed/inferred/unknown, the verification log names the checks not run, and the chat summary is ≤3 paragraphs.
