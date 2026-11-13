# evidence-backed-agent-prompts

Research and create implementation-ready coding-agent briefs; ask consequential questions, then optionally orchestrate an approved OMP coding run. Hermes-first orchestration, OMP execution, source-backed requirements, acceptance tests, and evidence review.

Status: Hermes-first v2, prepare-only by default. Replaces the earlier Cursor-centered edition.

## Layout

| path | purpose |
|---|---|
| `SKILL.md` | the skill body: 8 stages + final quality gate |
| `references/sources.md` | workflow source ledger and the ESP32/Auvik reference locators |
| `references/hermes-omp.md` | verified OMP v18.16.0 CLI surface, argon resolution, quota failure mode |
| `templates/HANDOFF.md` | portable brief skeleton |

## Install

```bash
# via the Skills CLI
npx skills add GodSpoon/skills -s evidence-backed-agent-prompts -y

# or copy the directory into your agent's skills folder
cp -r skills/evidence-backed-agent-prompts ~/.hermes/skills/     # Hermes
cp -r skills/evidence-backed-agent-prompts ~/.claude/skills/    # Claude Code
cp -r skills/evidence-backed-agent-prompts ~/.omp/agent/skills/ # Oh My Pi (omp)
```

Keep `references/` and `templates/` together with `SKILL.md`. Verify discovery with `skill_view` in your session.

For OMP-local use, the project `.agents/skills/evidence-backed-agent-prompts` layout is supported when its Agents provider is enabled; keep the skill one level below `skills/`.

## Invoke in Hermes

"Use evidence-backed-agent-prompts. Prepare a source-backed OMP implementation brief for this project. You own requirements, clarification, research, handoff, and evidence review. My preferred execution model label is argon 4; verify the real selector before any launch. Ask consequential questions first. Do not start OMP yet."

To request execution later:

"Review the prepared brief and current run state. Once repository, model selector, permission scope, and budget boundaries are resolved, launch the approved OMP work and review the evidence. Ask me about unresolved gates first."

## Boundaries

No automatic installer, launcher, permission-bypass configuration, or credentials are included. Documentation/packaging verification is not an end-to-end test in Hermes or OMP. The model label `argon 4` is user-reported; vendor and exact model ID are unverified.

Canonical source: https://github.com/GodSpoon/skills (`skills/evidence-backed-agent-prompts`). Edit the repo copy first, then reinstall into the profile.
