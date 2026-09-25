# api-spec-hunt

Find the machine-readable contract for a vendor's HTTP API, verify it, and package it so an agent can build an integration without re-doing discovery.

The premise: MSP/SaaS vendors park their marketing and training content on Zendesk/Confluence/Customer-style hubs, but the *renderable* API reference almost always lives on a **second host** — a docs engine, or the API server itself. Finding that second host is the job. Once a spec is confirmed, this skill emits a single hand-off markdown file (with a ready-to-paste agent prompt) and can generate a working CLI from the spec.

## What it does

1. **Locates** the best machine-consumable artifact — OpenAPI/Swagger spec > Postman collection > code-generated SDK > human docs.
2. **Probes** candidate hosts at ~58 conventional spec paths, reporting a verdict per path (`spec`, `spec-likely`, `gated`, `docs-ui`, `unknown`, `html`, `absent`, `unreachable`).
3. **Triangulates** existence through community artifacts — codegen tooling, MCP server repos, the APIs-guru directory.
4. **Sweeps behavior** the spec won't tell you: auth header shape, rate limit numbers, redirect/region sharding, pagination, error semantics, webhooks.
5. **Hands off** one `<vendor>-api-handoff.md` with every claim tagged confirmed / inferred / unknown.
6. **Generates** a self-contained stdlib-only Python CLI from the verified spec.

## File layout

```
api-spec-hunt/
├── SKILL.md                          # The skill: procedure, verdicts, pitfalls, verification bar
├── README.md                         # This file
├── references/
│   ├── handoff-template.md           # The 7-section output template + per-section guidance
│   └── undocumented-apis.md          # Fallback playbook when no public spec exists
└── scripts/
    ├── spec_hunt.py                  # Probe a host for specs, GraphQL introspection, gated endpoints
    ├── spec_to_cli.py                # OpenAPI/Swagger spec -> single-file Python CLI
    └── test_api_hunt.py              # 22 offline regression tests (no network)
```

All scripts are **stdlib-only** (PyYAML is optional and only used to fully parse YAML specs). No third-party packages, no network access required for the tests.

## Install

### Any agent, via the Skills CLI

```bash
npx skills add GodSpoon/skills -s api-spec-hunt -y
```

Add `-g` to install user-level instead of project-level. The CLI detects your agents and installs to `.agents/skills/` universally, symlinking the ones that expect their own directory (Claude Code, and Hermes among others).

### Manually, per agent

```bash
# Oh My Pi (omp) — native provider, highest discovery priority
cp -r api-spec-hunt ~/.omp/agent/skills/api-spec-hunt

# Claude Code
cp -r api-spec-hunt ~/.claude/skills/api-spec-hunt

# Hermes
cp -r api-spec-hunt ~/.hermes/skills/api-spec-hunt
```

The skill is picked up on the next session start.

## Usage

```bash
# Probe a vendor host
python3 scripts/spec_hunt.py https://api.vendor.com

# http-only internal API, with GraphQL introspection
python3 scripts/spec_hunt.py http://192.168.1.10:8080 --graphql-probe

# Confirm a fetched spec really is a spec
python3 scripts/spec_hunt.py --verify ./downloaded-spec.json

# List operations, then generate a CLI
python3 scripts/spec_to_cli.py --spec openapi.json --list
python3 scripts/spec_to_cli.py --spec openapi.json --out api_cli.py

# Run the offline tests
python3 scripts/test_api_hunt.py
```

Exit codes: `0` = spec found (or verified), `1` = nothing found / not a spec.

A bare host is treated as `https://<host>`; an explicit `http://` is honoured as given. A host that never answers is reported as `unreachable` — deliberately distinct from "reachable, no spec at conventional paths".

## Scope and ethics

Only probe hosts you own or are explicitly permitted to test. Active spec scanning against third parties is abuse, not research — for everyone else, read the vendor's docs.

## License

MIT
