# Hermes / OMP adapter reference

Official sources reviewed for this revision:
- https://hermes-agent.nousresearch.com/docs/developer-guide/creating-skills
- https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/skills-catalog.md
- https://github.com/can1357/oh-my-pi/blob/main/docs/skills.md
- https://github.com/can1357/oh-my-pi

Version caveat: these are evolving documentation pages, not evidence of the user's installed versions. Recheck runtime help and availability before use.

## Hermes packaging
The official skill guide uses SKILL.md plus optional scripts/references. Installed Hermes skills are documented under ~/.hermes/skills/. Keep this folder intact in the active profile's skills location; verify discovery rather than assuming a nondefault profile uses the default home.

This skill deliberately has no mandatory toolset gating: preparing a brief still works without a terminal. Terminal/process access and model authentication are prerequisites only for launching OMP. Do not request API secrets in chat. No inline shell snippets or auto-running setup scripts are bundled.

## OMP skill consumption
OMP's skill docs describe one-level provider layouts: <skills-root>/<name>/SKILL.md, not arbitrary recursively nested taxonomy. A project .agents/skills/<name>/SKILL.md layout is supported by its Agents provider, subject to configuration. Keep explicit name/description frontmatter. The /skill:<name> form is available when skill commands are enabled. Local skill references can use skill://<name>/... inside OMP, but these URIs are not portable Hermes filesystem paths.

## OMP launch options (verified against omp v18.16.0, Linux x64)

Entry points documented upstream: interactive TUI (`omp`), one-shot (`omp -p`), RPC
(`omp --mode rpc`, with a Python `omp-rpc` client), Node SDK, ACP.

Flags confirmed in `omp --help` on the installed build: `-p, --print` (non-interactive),
`--mode=text|json|rpc|rpc-ui`, `--cwd=`, `--model=` (fuzzy match such as `argon`, exact with
a provider such as `google/gemini-4-argon`), `--provider=` (legacy), `--no-session`,
`--add-dir=`, `--config=`, `--thinking=off|minimal|low|medium|high|xhigh|max|auto`,
`--tools=`, `--no-tools`, `--no-lsp`, `--no-pty`, `-c/--continue`, `-r/--resume=`,
`--restore=`, `--profile=`, `--session-dir=`.

One-shot delegation therefore is:
`omp -p --no-session --mode text|json --cwd <dir> [--model <selector>] "<prompt>"`

Binary location caveat: the installer places `omp` in `~/.local/bin`, which is absent from
the PATH of non-interactive shells. Resolve `$OMP_BIN`, then `~/.local/bin/omp`, then PATH.
Prefer passing the prompt as a single argument read from a file; never interpolate prose
into shell syntax. Use `--mode=json` when the caller needs to parse the event stream.

The model label **argon 4** resolves in the local catalog to `gemini-4-argon` ("Gemini 4
Argon"), available through the `google`, `google-vertex`, `github-copilot`, `venice`,
`cloudflare-ai-gateway`, `commandcode`, `nanogpt`, `kilo` and `zenmux` providers. Fuzzy
`--model argon` works; confirm the authenticated provider before a billable run.

Observed failure modes: the configured role `kimi-code/kimi-for-coding` returns
`429 exceeded_current_quota_error` when its weekly window is exhausted — the event stream
carries `"errorStatus":429` inside a normal-looking `-p` run, so a launcher must scan output
for quota/auth errors and report BLOCKED rather than treating exit 0 as success.

Discovery is not authorization: learning the supported flags does not authorize a paid run.

## Minimum run record
mode; task ID; working directory; branch/worktree; artifact paths accessible to child; parent session if available; requested model label; verified provider/model selector; OMP version; launch entry point; allowed actions; timeout/budget boundary; process/session ID; status; last reviewed evidence; next action.