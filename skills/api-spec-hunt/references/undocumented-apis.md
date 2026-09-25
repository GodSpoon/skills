# APIs with no published spec

`spec_hunt.py` exits 1 when a host serves nothing machine-readable. That is the common case for
homelab appliances, older enterprise gear, and internal services. Do not fall back to HTML
scraping if you can avoid it — recovery order below is cheapest-and-most-durable first.

## 1. Find the spec that exists but is not advertised

- Vendor docs sites: look for `openapi.json`, `swagger.json`, a "Developer / API" page, or a
  Postman public workspace. Search: `web_search(query="<product> openapi spec site:github.com")`.
- The web UI's own XHRs: open the app, watch Network for `/api/...` calls. The front-end bundle
  or a Swagger UI config blob usually contains the real spec URL.
- Spring Boot / FastAPI / .NET services expose `/v3/api-docs`, `/openapi.json`, `/swagger/v1/swagger.json`.
- Metabase, Grafana, Home Assistant, Jellyfin, Proxmox and most self-hosted tools ship a
  spec-adjacent document (JSON schema, `/api-docs`, `/api/schema/`) even when it is not OpenAPI.
- Re-run the hunter with a candidate list once you have hints:
  `terminal(command="python3 <skill_dir>/scripts/spec_hunt.py <host> --paths hints.txt")`

## 2. Capture traffic when no spec exists

1. Record one known-good interaction (a real browser session, or a proxy).
2. For a proxy: point the client at mitmproxy / Charles and export a HAR.
3. Reduce the HAR to the endpoints that matter, then promote it to a spec (step 3) so the
   generated CLI and its `--help` become the documentation.
4. Prefer a proxy over reading the app's JS: bundlers minify and re-chunk constantly.

## 3. Hand-write a minimal OpenAPI stub, then generate

You do not need a complete spec to get value from `spec_to_cli.py` — a few operations is enough:

```yaml
openapi: 3.0.0
info: {title: Widget API, version: "1"}
servers: [{url: http://192.168.1.10:8080}]     # include the scheme and host here
paths:
  /api/widgets:
    get:
      operationId: listWidgets
      parameters:
        - {name: page, in: query, schema: {type: integer}}
  /api/widgets/{id}:
    get:
      operationId: getWidget
      parameters:
        - {name: id, in: path, schema: {type: string}, required: true}
```

Then `spec_to_cli.py --spec widget.openapi.yaml --out widget_cli.py`. The stub doubles as
durable documentation for the next session, and diffing it against a future spec shows drift.

## 4. Auth patterns and where the credential lives

| Scheme | How it appears | Generated CLI handling |
|---|---|---|
| Bearer / JWT | `Authorization: Bearer <t>` | `API_TOKEN` env var (default) |
| API key in header | `X-API-Key: <k>` | `-H 'X-API-Key:<k>'` |
| API key in query | `?api_key=<k>` | pass as a normal query flag |
| Basic | `Authorization: Basic ...` | `-H` with the encoded value from Bitwarden |
| Session cookie | `Cookie: session=...` | `-H 'Cookie:session=<v>'` |

Store credentials in Bitwarden (`bw` CLI, `secrets-handling` skill) and export them into the
environment for the call. Never write a token into a generated file, a skill, or a note.

Long-lived tokens: check expiry before blaming the API (`ha_get_state`-style checks do not apply
here — read the error body, which usually says `token expired` vs `invalid scope`).

## 5. Behaviour the spec rarely documents

- **Pagination**: `?page=&per_page=`, `?limit=&offset=`, cursor `?after=`, or a `Link` header.
  Always cap the page size on the first call; unbounded endpoints can return the whole table.
- **Rate limits**: read `X-RateLimit-*` / `Retry-After` headers, back off on 429.
- **Idempotency**: writes may need `Idempotency-Key`; retrying blindly can duplicate records.
- **Defaults that differ from the UI**: the UI often sends hidden fields (filters, `tenant`,
  CSRF tokens). A call that works in the browser and 400s from the CLI is usually missing one.
- **Trailing-slash sensitivity**: some frameworks 301 without a slash, which breaks POSTs.

## 6. When to abandon generated tooling

If the service already ships a maintained CLI, an SDK, or a Hermes skill, use it — do not
re-implement it from a spec. Generated CLIs are for services that have no first-class client,
and they must be regenerated when the pinned spec changes.