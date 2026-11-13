# Hermes -> omp delegation bridge

Two scripts, no daemon, no permission bypass:

| script | purpose | side effects |
|---|---|---|
| `omp_probe.sh` | read-only capability discovery (install path, version, entry points, model roles) | none |
| `omp-delegate.sh` | one bounded `omp` run per invocation, with a reviewable run record | launches a model run (billable/quota-consuming) |

## Verified interface (omp v18.16.0, Linux x64)

Entry points documented upstream: interactive TUI (`omp`), one-shot (`omp -p`), RPC
(`omp --mode rpc`, plus the `omp-rpc` Python client), Node SDK, ACP.

One-shot delegation, which is what the bridge uses:

```bash
omp -p --no-session --mode text|json --cwd <dir> [--model <selector>] "<prompt>"
```

Flags confirmed present in `omp --help` on v18.16.0: `-p, --print`, `--mode=text|json|rpc|rpc-ui`,
`--cwd=`, `--model=` (fuzzy match like `argon`, exact like `google/gemini-4-argon`),
`--no-session`, `--add-dir=`, `--config=`, `--thinking=`, `--tools=`, `--no-tools`,
`-r, --resume=`, `--restore=`, `--profile=`.

## Model selector: "argon 4"

The user-reported label **argon 4** resolves against the local OMP model catalog to
**`gemini-4-argon`** (display name "Gemini 4 Argon"), available through the `google`,
`google-vertex`, `github-copilot`, `venice`, `cloudflare-ai-gateway`, `commandcode`,
`nanogpt`, `kilo`, and `zenmux` providers. Use `--model argon` (fuzzy) or
`--model google/gemini-4-argon` (exact). Confirm the provider you are authenticated
against before a billable run.

## Known failures and how they surface

| symptom | meaning | handling |
|---|---|---|
| `429 exceeded_current_quota_error` in the JSON stream | provider subscription is out of quota (e.g. `kimi-code/kimi-for-coding` weekly window) | the bridge marks the run `BLOCKED` and exits 3; pick another `--model` or wait for reset |
| `errorStatus: 401`, `invalid_api_key` | no valid credential for the selected provider | run `omp` interactively once to authenticate; the bridge never handles secrets |
| exit 124 | `--timeout` reached | inspect `output.txt`; do not blind-retry on the same worktree |

## Run records

Each delegation writes `~/.hermes/runs/omp/<UTC-stamp>-<slug>/` containing `prompt.txt`,
`cmd.txt`, `output.txt`, and `RUN-RECORD.md` (mode, workdir, requested model, omp
version, entry point, exit code, status, evidence paths). Review the record before
believing a completion claim — an omp "done" is agent-reported until Hermes checks
the diff and tests.

## Boundary

The bridge does not disable approvals, does not read credentials, and does not push,
deploy, or flash. Local coding approval is not production access. One writer per
worktree: never launch a second run against a worktree an existing run owns.
