#!/usr/bin/env python3
"""Probe a host for machine-readable API specs and GraphQL introspection.

Stdlib only (PyYAML optional, for YAML specs). Emits a JSON or table report of
every spec-like document found, including 401/403 responses, which prove an
endpoint exists but is gated.

Usage:
  spec_hunt.py https://api.example.com
  spec_hunt.py http://192.168.1.10:8080 --graphql-probe
  spec_hunt.py https://api.example.com --paths extra-paths.txt --json
  spec_hunt.py --verify ./downloaded-spec.json
  spec_hunt.py --verify https://api.example.com/spec

A host that never answers is reported as UNREACHABLE, which is a different
finding from "reachable, no spec at conventional paths" — never record the
first as the second.

Exit codes: 0 = a spec was found (or verified), 1 = nothing found / not a spec.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request

# Stdlib-only fallback for YAML specs when PyYAML is not installed: a top-level
# `openapi:`/`swagger:`/`asyncapi:` key is strong enough to confirm a spec.
_YAML_TOP_KEY = re.compile(r"^(openapi|swagger|asyncapi)\s*:\s*[\"']?(\d[\w.\-]*)", re.M)
_YAML_TITLE = re.compile(r"^\s{0,4}title\s*:\s*[\"']?(.+?)[\"']?\s*$", re.M)

DEFAULT_PATHS = [
    # Bare /spec is a very common convention (and where the Auvik worked example
    # lives) — without it the prober misses specs it can otherwise prove exist.
    "spec", "spec/",
    "openapi.json", "openapi.yaml", "openapi.yml", "swagger.json", "swagger.yaml",
    "api/openapi.json", "api/swagger.json", "api/openapi.yaml", "api-docs",
    "v2/api-docs", "v3/api-docs", "v1/api-docs", "swagger/v1/swagger.json",
    "docs/openapi.json", "docs/swagger.json", "spec/openapi.json", "spec/swagger.json",
    ".well-known/openapi.json", ".well-known/openapi.yaml", ".well-known/schema-discovery",
    "redoc", "swagger-ui.html", "swagger-ui/", "api-docs/",
    "api/v1/openapi.json", "api/v2/openapi.json", "api/v3/openapi.json",
    "api/v1/openapi.yaml", "api/v2/openapi.yaml", "api/v3/openapi.yaml",
    "api/v1/swagger.json", "api/v2/swagger.json", "api/v3/swagger.json",
    "v1/openapi.json", "v2/openapi.json", "v3/openapi.json",
    "api/openapi/v3.json", "api/openapi/v2.json", "api/schema/", "api/schema",
    "schema/openapi.json", "openapi/v3/openapi.json",
    "graphql", "api/graphql", "v1/graphql", "graphiql", "postman.json",
    "collection.json", "asyncapi.yaml", "asyncapi.json", "openapi/3.0/openapi.json",
    "api/docs", "docs", "api/", "wp-json", "index.php?rest_route=/",
]

SPEC_KEYS = ("openapi", "swagger", "asyncapi", "raml", "paths", "components")


def fetch(url: str, timeout: float, method: str = "GET", body: bytes | None = None,
          headers: dict | None = None):
    try:
        req = urllib.request.Request(url, data=body, method=method, headers=headers or {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), r.read(2_000_000)
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read(200_000)
    except Exception as e:  # DNS failure, TLS error, timeout, malformed URL
        return None, {}, str(e).encode()


def normalize_base(base: str) -> str:
    """Give a scheme-less host an https:// scheme; honour an explicit scheme."""
    base = base.strip().rstrip("/")
    if base and not base.startswith(("http://", "https://")):
        base = "https://" + base
    return base


def classify(path: str, status: int | None, ctype: str, body: bytes) -> tuple[str, str]:
    """Return (verdict, note)."""
    if status is None:
        return "unreachable", body[:120].decode("utf-8", "replace")
    if status in (401, 403):
        return "gated", f"exists but requires auth (HTTP {status})"
    if status == 404:
        return "absent", "404"
    if status >= 500:
        return "error", f"HTTP {status}"
    # Parse the WHOLE body. `fetch` already caps at 2 MB, and real specs are
    # routinely large (a 50-path OpenAPI doc runs ~600 KB), so a truncating
    # slice here silently misclassifies big specs as "body is not valid JSON".
    text = body.decode("utf-8", "replace")
    if "json" in ctype or text.lstrip()[:1] in ("{", "["):
        try:
            doc = json.loads(text)
        except ValueError:
            return "unknown", "body is not valid JSON"
        if isinstance(doc, dict):
            for key in SPEC_KEYS:
                if key in doc:
                    version = doc.get("openapi") or doc.get("swagger") or doc.get("asyncapi") or ""
                    return "spec", f"{key}={version or 'present'}"
            if "data" in doc and "__schema" in doc.get("data", {}):
                return "graphql-introspection", "introspection enabled"
        if path.endswith(".json") and isinstance(doc, dict) and ("info" in doc or "host" in doc):
            return "spec-likely", "json with spec-like top-level keys"
        return "unknown", "json, unrecognized shape"
    # Heuristics below only need a bounded prefix, so cap the scan.
    head = text[:400_000]
    if "yaml" in ctype or head.lstrip().startswith(("openapi:", "swagger:", "asyncapi:", "---")):
        try:
            import yaml  # type: ignore
            doc = yaml.safe_load(head) or {}
        except Exception:
            return "spec-likely", "YAML body (content-type says yaml); install pyyaml to confirm"
        if isinstance(doc, dict):
            for key in SPEC_KEYS:
                if key in doc:
                    version = doc.get("openapi") or doc.get("swagger") or doc.get("asyncapi") or ""
                    return "spec", f"yaml {key}={version or 'present'}"
        return "unknown", "yaml, unrecognized shape"
    if "<html" in head.lower():
        low = head.lower()
        hinted = ""
        for marker in ("url: ", "spec-url=", "spec_url=", "openapi"):
            idx = low.find(marker)
            if idx != -1:
                hinted = head[idx:idx + 120].split("\n")[0].strip()
                break
        if "swagger" in low or "redoc" in low or "graphiql" in low:
            return "docs-ui", f"interactive docs page ({hinted or 'no spec URL found in HTML'})"
        return "html", "an HTML page, not a spec"
    return "unknown", f"content-type {ctype or '?'}"


def verify(target: str) -> bool:
    """Confirm that a file or URL really is an OpenAPI/Swagger/AsyncAPI doc."""
    if target.startswith(("http://", "https://")):
        status, _headers, body = fetch(target, 15.0)
        if status is None:
            reason = body[:200].decode("utf-8", "replace")
            print(f"FAIL: transport error fetching {target}: {reason}")
            return False
        if status != 200:
            print(f"FAIL: HTTP {status} fetching {target}")
            return False
    else:
        with open(target, encoding="utf-8", errors="replace") as fh:
            body = fh.read().encode("utf-8")

    # Parse the whole body — `fetch` caps at 2 MB, and truncating a real spec
    # (Auvik's is ~640 KB) makes json.loads fail on a perfectly good document.
    text = body.decode("utf-8", "replace")
    try:
        doc = json.loads(text)
    except ValueError:
        try:
            import yaml  # type: ignore
            doc = yaml.safe_load(text)
        except Exception:
            doc = None

    if isinstance(doc, dict):
        version = doc.get("openapi") or doc.get("swagger") or doc.get("asyncapi")
        if not version:
            print(f"FAIL: {target} has no top-level openapi/swagger/asyncapi key")
            return False

        info = doc.get("info") if isinstance(doc.get("info"), dict) else {}
        title = info.get("title", "?")
        npaths = len(doc.get("paths") or {})
        print(f"OK: '{title}' (version key: {version}, ~{npaths} paths)")

        servers = doc.get("servers") or []
        urls = [str(s.get("url", "?")) for s in servers if isinstance(s, dict)]
        if urls:
            print(f"    servers: {', '.join(urls[:3])}")
        elif doc.get("host"):
            print(f"    host: {doc['host']}{doc.get('basePath', '')}")
        return True

    # Not JSON, and PyYAML is missing or the parse failed. Fall back to a
    # stdlib top-level-key check so a real YAML spec is not reported as absent.
    m = _YAML_TOP_KEY.search(text)
    if m:
        title_m = _YAML_TITLE.search(text)
        title = title_m.group(1).strip() if title_m else "?"
        print(f"OK: '{title}' (version key: {m.group(1)} {m.group(2)} — matched by "
              f"top-level YAML key; install PyYAML for a full parse)")
        return True

    print(f"FAIL: {target} did not parse as a JSON/YAML object and has no top-level "
          f"openapi/swagger/asyncapi key")
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description="Hunt for API specs on a host.")
    ap.add_argument("base_url", nargs="?",
                    help="e.g. https://api.example.com or http://192.168.1.10:8080")
    ap.add_argument("--verify", metavar="FILE|URL",
                    help="verify that a file or URL is a real spec, then exit")
    ap.add_argument("--paths", help="file with one candidate path per line (replaces defaults)")
    ap.add_argument("--timeout", type=float, default=8.0, help="per-request timeout seconds")
    ap.add_argument("--graphql-probe", action="store_true",
                    help="POST a GraphQL introspection query to /graphql and /api/graphql")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    args = ap.parse_args()

    if args.verify:
        return 0 if verify(args.verify) else 1
    if not args.base_url:
        ap.error("base_url is required (or use --verify FILE|URL)")

    base = normalize_base(args.base_url)
    paths = DEFAULT_PATHS
    if args.paths:
        with open(args.paths, encoding="utf-8") as fh:
            paths = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]

    hits = []
    unreachable = []
    for path in paths:
        url = f"{base}/{path.lstrip('/')}"
        status, headers, body = fetch(url, args.timeout)
        ctype = (headers.get("Content-Type") or "").lower()
        verdict, note = classify(path, status, ctype, body)
        if verdict == "unreachable":
            # Keep this separate from "absent": a host that never answered has
            # not been ruled out, and reporting it as "no spec" is a false negative.
            unreachable.append({"url": url, "note": note})
            continue
        if verdict != "absent":
            hits.append({"url": url, "status": status, "verdict": verdict, "note": note})

    if args.graphql_probe:
        query = json.dumps({"query": "{__schema{queryType{name} types{name}}}"}).encode()
        for path in ("graphql", "api/graphql", "v1/graphql"):
            url = f"{base}/{path}"
            status, _h, body = fetch(url, args.timeout, method="POST", body=query,
                                     headers={"Content-Type": "application/json"})
            if status == 200 and b"__schema" in body:
                hits.append({"url": url, "status": status,
                             "verdict": "graphql-introspection",
                             "note": "introspection query returned a schema"})
            elif status is not None and status != 404:
                hits.append({"url": url, "status": status, "verdict": "graphql-endpoint",
                             "note": body[:160].decode("utf-8", "replace")})

    specs = [h for h in hits if h["verdict"] in ("spec", "graphql-introspection")]
    all_unreachable = bool(paths) and len(unreachable) == len(paths)

    if args.json:
        print(json.dumps({"base_url": base, "specs": specs, "all_hits": hits,
                          "unreachable": unreachable if all_unreachable else [],
                          "unreachable_paths": len(unreachable), "paths_probed": len(paths)},
                         indent=2))
        return 0 if specs else 1

    print(f"base: {base}")
    print(f"{'STATUS':<7} {'VERDICT':<22} URL")
    for h in hits:
        print(f"{str(h['status']):<7} {h['verdict']:<22} {h['url']}")
        if h["note"]:
            print(f"{'':<7} {'':<22}   -> {h['note']}")
    print(f"\n{len(specs)} machine-readable spec(s) found.")

    if all_unreachable:
        reason = unreachable[0]["note"] if unreachable else "unknown"
        print(f"\nUNREACHABLE — the host never answered on any of the {len(paths)} "
              f"conventional paths, so no spec could be ruled in or out.")
        print(f"  reason: {reason}")
        print("  This is not the same finding as \"reachable, no spec\". Check the scheme "
              "(http vs https), DNS, TLS, and any VPN/allowlist before concluding.")
    elif unreachable:
        print(f"note: {len(unreachable)}/{len(paths)} paths were unreachable and were "
              f"not ruled out.")
    return 0 if specs else 1


if __name__ == "__main__":
    sys.exit(main())
