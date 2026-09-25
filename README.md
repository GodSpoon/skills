# skills

Agent skills that are installable anywhere — Claude Code, Cursor, Codex, Oh My Pi (omp), Hermes, and any other agent that reads a `SKILL.md`.

Every skill here is self-contained and dependency-light: standard-library scripts, bundled references, and a fallback playbook for when the happy path doesn't apply. No paid services, no API keys required to use the skill itself.

## Install

Via the Skills CLI:

```bash
# List what's available without installing
npx skills add GodSpoon/skills -l

# Install one skill (verified against skills CLI v1.7.0)
npx skills add GodSpoon/skills -s api-spec-hunt -y

# Install every skill in the repo
npx skills add GodSpoon/skills -s '*' -y

# Add -g to install user-level instead of project-level
npx skills add GodSpoon/skills -s api-spec-hunt -g -y
```

Or copy a skill directory into your agent's skills folder:

```bash
cp -r skills/api-spec-hunt ~/.claude/skills/       # Claude Code
cp -r skills/api-spec-hunt ~/.omp/agent/skills/    # Oh My Pi (omp)
cp -r skills/api-spec-hunt ~/.hermes/skills/       # Hermes
```

## Catalog

| Skill | What it does | Category |
|-------|--------------|----------|
| [api-spec-hunt](./skills/api-spec-hunt) | Find, verify, and package a vendor's machine-readable API definition (OpenAPI > Postman > SDK > docs), sweep the behavioral facts specs omit, emit a cited hand-off file, and generate a working CLI from the spec | API / Integration |

## What a skill looks like

```
skills/<name>/
├── SKILL.md          # Required. `name` + `description` frontmatter, then the procedure.
├── README.md         # Required. Summary, file layout, install and usage.
├── references/       # Optional. Loaded on demand — playbooks, templates, deep tables.
└── scripts/          # Optional. Deterministic helpers (stdlib-only where possible).
```

`SKILL.md` frontmatter deliberately carries **only `name` and `description`**. Other agents' parsers reject or mis-handle extra fields, and the description is the *only* thing an agent sees when deciding whether to load the skill — so it must state the trigger, the behavior, and searchable keywords in one line.

## Adding a skill

1. `mkdir -p skills/<name>` with a `SKILL.md` (frontmatter + imperative procedure) and a `README.md`.
2. Put deep material in `references/`, runnable helpers in `scripts/`.
3. Add a row to the catalog table above.
4. `npx skills add GodSpoon/skills -l` should list it; verify before pushing.

## License

MIT. Individual skills retain their own license if one is declared inside the skill directory.
