#!/usr/bin/env bash
# omp-delegate.sh - bounded Hermes -> oh-my-pi (omp) delegation with a run record.
#
# Why: Hermes owns requirements/research/review; omp is the downstream coding harness.
# This script launches exactly one omp run per invocation, keeps a reviewable run
# record, and refuses to guess model selectors or bypass approvals.
#
# Usage:
#   omp-delegate.sh [--model SELECTOR] [--cwd DIR] [--timeout SECONDS]
#                   [--mode text|json] [--probe-only] [--dry-run] PROMPT_FILE|-
#
# Examples:
#   ./omp-delegate.sh --probe-only
#   ./omp-delegate.sh --model argon --cwd ~/src/thing --timeout 1800 brief.md
#   cat brief.md | ./omp-delegate.sh --model google/gemini-4-argon --mode json -
#
# Exit codes: 0 run finished (see record), 2 blocked (omp missing / bad usage),
#             3 run reported an auth or quota error, 124 timeout.
set -euo pipefail

OMP_BIN="${OMP_BIN:-}"
MODEL=""
CWD=""
TIMEOUT=1800
MODE="text"
PROBE_ONLY=0
DRY_RUN=0
PROMPT_ARG=""

usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit "${1:-0}"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --model) MODEL="${2:?--model needs a value}"; shift 2 ;;
    --cwd) CWD="${2:?--cwd needs a value}"; shift 2 ;;
    --timeout) TIMEOUT="${2:?--timeout needs a value}"; shift 2 ;;
    --mode) MODE="${2:?--mode needs a value}"; shift 2 ;;
    --probe-only) PROBE_ONLY=1; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    -h|--help) usage 0 ;;
    -) PROMPT_ARG="-"; shift ;;
    -*) echo "unknown flag: $1" >&2; usage 2 ;;
    *) PROMPT_ARG="$1"; shift ;;
  esac
done

resolve_omp() {
  if [ -n "$OMP_BIN" ] && [ -x "$OMP_BIN" ]; then printf '%s\n' "$OMP_BIN"; return 0; fi
  if [ -x "$HOME/.local/bin/omp" ]; then printf '%s\n' "$HOME/.local/bin/omp"; return 0; fi
  if command -v omp >/dev/null 2>&1; then command -v omp; return 0; fi
  return 1
}

OMP="$(resolve_omp || true)"
if [ -z "$OMP" ]; then
  echo "BLOCKED: omp CLI not found (checked \$OMP_BIN, ~/.local/bin/omp, PATH)." >&2
  echo "Install (upstream): curl -fsSL https://omp.sh/install | sh   |   https://github.com/can1357/oh-my-pi" >&2
  exit 2
fi

OMP_VERSION="$("$OMP" --version 2>/dev/null | head -1 || echo 'unknown')"
HELP="$("$OMP" --help 2>/dev/null || true)"
has_flag() { printf '%s' "$HELP" | grep -q -- "$1"; }
FLAGS_OK="print=$(has_flag '\-p, --print' && echo yes || echo no) mode=$(has_flag '\-\-mode' && echo yes || echo no) cwd=$(has_flag '\-\-cwd' && echo yes || echo no) model=$(has_flag '\-\-model' && echo yes || echo no) no-session=$(has_flag '\-\-no-session' && echo yes || echo no)"

if [ "$PROBE_ONLY" = "1" ]; then
  echo "omp:         $OMP"
  echo "version:     $OMP_VERSION"
  echo "flags:       $FLAGS_OK"
  echo "agent dir:   ${HOME}/.omp/agent (config.yml: $([ -f "$HOME/.omp/agent/config.yml" ] && echo present || echo absent))"
  if [ -f "$HOME/.omp/agent/config.yml" ]; then
    echo "model roles: $(grep -E '^\s+[a-z]+:' "$HOME/.omp/agent/config.yml" | tr -s ' ' | paste -sd'; ' -)"
  fi
  printf 'catalog:     '
  if command -v python3 >/dev/null 2>&1 && [ -f "$HOME/.omp/agent/models.db" ]; then
    python3 - "$HOME/.omp/agent/models.db" <<'PY' || echo 'catalog unreadable'
import sqlite3, sys, re
db = sys.argv[1]
try:
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = c.execute("select provider_id, models from model_cache").fetchall()
except Exception as exc:
    print(f"catalog unreadable ({exc})"); raise SystemExit(0)
hits = {}
for pid, models in rows:
    if not isinstance(models, str):
        continue
    for mid in set(re.findall(r'"id"\s*:\s*"([^"]*argon[^"]*)"', models, re.I)):
        hits.setdefault(mid, []).append(pid.split(":")[0])
for mid, provs in sorted(hits.items()):
    print(f"{mid}  <- {', '.join(sorted(set(provs)))}")
if not hits:
    print("no 'argon' model ids in local catalog")
PY
  else
    echo "models.db not readable here"
  fi
  exit 0
fi

if [ -z "$PROMPT_ARG" ]; then echo "BLOCKED: no prompt file given (use a path or '-')." >&2; usage 2; fi
if [ "$PROMPT_ARG" = "-" ]; then
  PROMPT="$(cat)"
else
  [ -f "$PROMPT_ARG" ] || { echo "BLOCKED: prompt file not found: $PROMPT_ARG" >&2; exit 2; }
  PROMPT="$(cat "$PROMPT_ARG")"
fi
[ -n "${PROMPT//[[:space:]]/}" ] || { echo "BLOCKED: empty prompt." >&2; exit 2; }

WORKDIR="${CWD:-$PWD}"
[ -d "$WORKDIR" ] || { echo "BLOCKED: --cwd not a directory: $WORKDIR" >&2; exit 2; }
case "$MODE" in text|json) ;; *) echo "BLOCKED: --mode must be text or json (rpc needs the omp-rpc client)." >&2; exit 2 ;; esac

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
SLUG="$(printf '%s' "$PROMPT" | tr -cs 'A-Za-z0-9' '-' | cut -c1-40 | sed 's/^-//; s/-$//')"
[ -n "$SLUG" ] || SLUG="run"
RUNDIR="${OMP_RUN_DIR:-$HOME/.hermes/runs/omp}/$STAMP-$SLUG"
mkdir -p "$RUNDIR"
cp /dev/null "$RUNDIR/prompt.txt"; printf '%s\n' "$PROMPT" > "$RUNDIR/prompt.txt"

ARGV=(-p --no-session --mode "$MODE" --cwd "$WORKDIR")
[ -n "$MODEL" ] && ARGV+=(--model "$MODEL")
printf 'argv: omp %s <prompt %s chars>\n' "${ARGV[*]}" "${#PROMPT}" > "$RUNDIR/cmd.txt"

if [ "$DRY_RUN" = "1" ]; then
  echo "DRY-RUN: would execute: omp ${ARGV[*]}  (cwd=$WORKDIR, timeout=${TIMEOUT}s, prompt=$RUNDIR/prompt.txt)"
  exit 0
fi

set +e
timeout "$TIMEOUT" "$OMP" "${ARGV[@]}" "$PROMPT" > "$RUNDIR/output.txt" 2>&1
RC=$?
set -e

STATUS="finished"
case "$RC" in
  124) STATUS="timeout" ;;
  0)   STATUS="finished" ;;
  *)   STATUS="exit-$RC" ;;
esac
if grep -q -E 'exceeded_current_quota_error|"errorStatus":429|rate.?limit' "$RUNDIR/output.txt"; then
  STATUS="BLOCKED: model auth/quota error (see output.txt)"
fi
if grep -q -E 'errorStatus":401|invalid_api_key|unauthorized' "$RUNDIR/output.txt"; then
  STATUS="BLOCKED: model auth error (see output.txt)"
fi

{
  echo "# omp run record"
  echo
  echo "- task id:        $STAMP-$SLUG"
  echo "- run dir:        $RUNDIR"
  echo "- requested model: ${MODEL:-<omp default modelRoles.default>}"
  echo "- omp version:    $OMP_VERSION"
  echo "- entry point:    one-shot CLI: omp ${ARGV[*]}"
  echo "- flags verified: $FLAGS_OK"
  echo "- workdir:        $WORKDIR"
  echo "- timeout:        ${TIMEOUT}s"
  echo "- exit code:      $RC"
  echo "- status:         $STATUS"
  echo "- evidence:       $RUNDIR/output.txt, $RUNDIR/prompt.txt, $RUNDIR/cmd.txt"
  echo "- recorded:       $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo
  echo "Review this output before trusting a completion claim: omp is downstream of"
  echo "Hermes, so 'done' here is agent-reported until Hermes checks the diff/tests."
} > "$RUNDIR/RUN-RECORD.md"

echo "run dir: $RUNDIR"
echo "status:  $STATUS"
tail -c 2000 "$RUNDIR/output.txt" || true
case "$STATUS" in
  finished) exit 0 ;;
  timeout)  exit 124 ;;
  BLOCKED*) exit 3 ;;
  *)        exit 1 ;;
esac
