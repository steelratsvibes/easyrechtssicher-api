#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mode="${1:---standard}"
case "$mode" in --standard|--offline) ;; *) echo 'Use --standard or --offline' >&2; exit 2;; esac
while IFS= read -r file; do node --check "$file"; done < <(find examples tests -name '*.mjs' -type f | sort)
while IFS= read -r file; do php -l "$file" >/dev/null; done < <(find examples tests -name '*.php' -type f | sort)
bash -n scripts/verify.sh scripts/scan-secrets.sh .githooks/pre-push
python3 - <<'PY'
import ast
import json
from pathlib import Path
spec = json.loads(Path('openapi.json').read_bytes())
assert spec['openapi'] == '3.1.0' and isinstance(spec['paths'], dict)
for directory in ('examples', 'scripts', 'tests'):
    for path in Path(directory).rglob('*.py'):
        ast.parse(path.read_text(), filename=str(path))
PY
node --test tests/client.test.mjs
python3 -m unittest discover -s tests -p 'test_*.py' -v
php -d zend.assertions=1 -d assert.exception=1 tests/client.test.php
if [[ "$mode" == --offline ]]; then exit 0; fi
# Explicit stack mode never reads or sends EASYRECHTSSICHER_API_KEY.
node examples/nextjs/smoke.mjs stack >/dev/null
echo 'Next.js keyless live smoke: PASS'
node examples/astro/smoke.mjs stack >/dev/null
echo 'Astro keyless live smoke: PASS'
php examples/laravel/smoke.php stack >/dev/null
echo 'Laravel keyless live smoke: PASS'
php examples/php/smoke.php stack >/dev/null
echo 'PHP keyless live smoke: PASS'
python3 examples/python/smoke.py stack >/dev/null
echo 'Python keyless live smoke: PASS'
python3 scripts/spec.py check
