---
name: easyrechtssicher
description: Integrate easyRechtssicher document reads into a server application, starting with a keyless tool-stack check and using a server environment key for document JSON.
---

Use the [examples and setup instructions](../../README.md) and the [copied live contract](../../openapi.json). This skill covers document reads, not agency writes or an MCP server.

1. Run the appropriate example in `stack` mode first. It calls the fixed HTTPS Stack-Check without a key and checks catalog coverage only.
2. Run `documents` mode with `EASYRECHTSSICHER_API_KEY` unset to use the public probe for sample texts. Set your own licensed registration key in the server environment for real documents.
3. Document mode fetches the document list and German Impressum. Run `python3 scripts/probe-smoke.py` to verify the list and all four marked samples across the five examples. Sample content is for testing only.
4. Integrate the host adapter and shared client on the server. Keep keys outside browser bundles, URLs and logs. Preserve the fixed HTTPS origin, redirect rejection, bounded requests, response validation and generic errors. Return JSON; do not render upstream HTML as part of these examples. Keep host access controls where appropriate.
5. Run `bash scripts/verify.sh` and `python3 scripts/probe-smoke.py`. Report any warning from the legacy contract fallback. Update the exact live bytes with `python3 scripts/spec.py sync`.

Do not add claims about the origin of legal texts. MIT covers example code/scripts/tests only; this skill, the spec, docs and legal texts are excluded.
