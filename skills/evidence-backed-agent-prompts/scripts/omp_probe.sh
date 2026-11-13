#!/usr/bin/env bash
# omp_probe.sh - read-only capability discovery for the omp CLI (install, version,
# entry points, model catalog). Prints facts; never launches a paid coding run.
set -euo pipefail
OMP=""
for cand in "${OMP_BIN:-}" "$HOME/.local/bin/omp" "$(command -v omp 2>/dev/null || true)"; do
  [ -n "$cand" ] && [ -x "$cand" ] && { OMP="$cand"; break; }
done
if [ -z "$OMP" ]; then
  echo "omp: NOT INSTALLED (checked \$OMP_BIN, ~/.local/bin/omp, PATH)"
  echo "install: curl -fsSL https://omp.sh/install | sh  (or brew/npm/bun/mise - see https://github.com/can1357/oh-my-pi)"
  exit 1
fi
echo "omp:      $OMP"
echo "version:  $("$OMP" --version 2>/dev/null | head -1)"
echo "agent:    ${HOME}/.omp/agent"
[ -f "$HOME/.omp/agent/config.yml" ] && echo "roles:    $(grep -E '^\s+\w+:' "$HOME/.omp/agent/config.yml" | tr -s ' ' | paste -sd'; ' -)"
printf 'entry points in this build:\n'
"$OMP" --help 2>/dev/null | grep -E -- '^\s+(-p, --print|--mode=|--cwd=|--model=|--no-session|--add-dir=|--config=|--thinking=|-r, --resume|--restore=|--no-tools|--tools=)' | sed 's/^/  /'
echo "docs:     https://github.com/can1357/oh-my-pi/blob/main/docs/cli-reference.md"
