#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
command -v gitleaks >/dev/null || { echo 'gitleaks is required; push blocked.' >&2; exit 1; }
# --all traverses all refs; no shallow history is accepted.
if [[ "$(git rev-parse --is-shallow-repository)" == true ]]; then
  echo 'Full history required; push blocked.' >&2
  exit 1
fi
if git rev-parse --verify HEAD >/dev/null 2>&1; then
  gitleaks git --redact=100 --log-opts=--all .
else
  echo 'History scan: no commits (fresh repository); no history to scan.'
fi
# Includes untracked and ignored working-tree files; do not add allowlists for credentials.
gitleaks dir --redact=100 .
