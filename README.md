# easyRechtssicher Rechtstexte API

[![CI](https://github.com/steelratsvibes/easyrechtssicher-api/actions/workflows/checks.yml/badge.svg)](https://github.com/steelratsvibes/easyrechtssicher-api/actions/workflows/checks.yml)

Server-side examples for retrieving German legal notices (**Impressum**) and privacy policies (**Datenschutzerklärung**) as JSON. Start with the free, keyless tool-stack check. [Deutsch](README.de.md).

```bash
node examples/nextjs/smoke.mjs stack
```

This calls `GET https://easyrechtssicher.de/api/v1/agent/stack-check?tools=HighLevel` without authorization. It checks catalog coverage; it does not assess legal compliance. [API introduction](https://easyrechtssicher.de/agent-api).

## Run the five examples

Requirements: Node.js 22+, PHP 8.2+ with HTTPS streams/OpenSSL and `allow_url_fopen`, Python 3.10+, trusted system CA certificates. No npm, Composer or pip dependencies are added. Frameworks are supplied by your existing host application.

| Example | Keyless live smoke | Host adapter |
|---|---|---|
| Next.js | `node examples/nextjs/smoke.mjs stack` | [route.mjs](examples/nextjs/route.mjs) |
| Astro | `node examples/astro/smoke.mjs stack` | [endpoint.mjs](examples/astro/endpoint.mjs) |
| Laravel | `php examples/laravel/smoke.php stack` | [routes.php](examples/laravel/routes.php), [config.php](examples/laravel/config.php) |
| PHP | `php examples/php/smoke.php stack` | [index.php](examples/php/index.php) |
| Python | `python3 examples/python/smoke.py stack` | Import `run` from [client.py](examples/python/client.py) in server code |

Each CLI and its adapter call the same client implementation. CLI success prints JSON; failure prints a fixed error and exits nonzero. Adapters return JSON with `private, no-store`, including a generic 502 on upstream failures. No HTML is rendered, even when the upstream document's `text` contains HTML.

## Retrieve documents with one key

In `documents` mode, set `EASYRECHTSSICHER_API_KEY` to your own licensed registration key before starting an example. The example stops if the key is missing.

To verify all five examples against the public probe, run:

```bash
python3 scripts/probe-smoke.py
```

The runner uses `samples` mode, which always uses the public probe. Each example fetches the document list and Impressum and DSE in German and English. The runner spaces the five-request batches for the live limit of 10 requests per minute per IP.

The live contract currently has no document-list response schema. Clients validate the list's JSON object and `data` container only; they do not guess item fields, infer availability, or follow response URLs. Document responses validate the requested type/language, format, text, title and metadata. Unknown extra fields are permitted for forward compatibility. These are boundary checks, not a complete JSON Schema validator.

## Install in an existing host app

Keep the shared clients outside browser bundles and public/static folders. Never use `NEXT_PUBLIC_`, `PUBLIC_` or `VITE_` variables for the key. Set `EASYRECHTSSICHER_MODE=documents` on the server only when ready; the default is `stack`.

- **Next.js App Router:** copy `examples/shared/client.mjs` to `lib/easyrechtssicher.mjs`. Copy `examples/nextjs/route.mjs` to `app/api/rechtstexte/route.js`, changing its import to `../../../lib/easyrechtssicher.mjs`. Keep the Node runtime and dynamic route settings. Request `/api/rechtstexte`.
- **Astro:** use an existing server-rendered host with a Node server adapter. Copy the shared client to `src/lib/easyrechtssicher.mjs` and `endpoint.mjs` to `src/pages/api/rechtstexte.js`; change its import to `../../lib/easyrechtssicher.mjs`. Keep `prerender = false`. Configure runtime server environment variables. Request `/api/rechtstexte`.
- **Laravel:** copy `examples/shared` and `examples/laravel` to `<app>/examples/`. Copy `examples/laravel/config.php` to `<app>/config/easyrechtssicher.php`; add `require base_path('examples/laravel/routes.php');` in `routes/web.php`. Configure the server environment before rebuilding Laravel's configuration cache. Request `/rechtstexte`. Apply your host's access controls if documents should be restricted.
- **PHP:** keep `examples/` outside the web root; include `examples/php/index.php` from a public endpoint. For a local keyless demo: `php -S 127.0.0.1:8080 -t examples/php`, then request `/index.php`. The built-in server is for local development.
- **Python:** call `run('stack')` or `run('documents')` inside server code and serialize the result as JSON. CLI smoke uses exactly this function.

These are host adapters, not newly scaffolded framework applications. No framework packages are installed here. Host builds/deployments require verification in your application; CLI smoke does not prove a complete framework deployment.

All upstream requests use the fixed HTTPS origin `https://easyrechtssicher.de`, verify TLS, disable redirects, and reject non-200 responses (including 304 because these examples keep no cache). JS uses a 15-second abort deadline; PHP/Python use 15-second connection/read timeouts plus a response-read deadline. Response size is limited to 2 MiB. No automatic retries are made, including on 429. Errors never include upstream bodies or credentials. Successful document JSON is intended output; avoid routing it to public CI logs.

## Verify, check drift, sync

```bash
bash scripts/verify.sh --offline
bash scripts/verify.sh
python3 scripts/spec.py check
python3 scripts/spec.py sync
```

`verify.sh` checks syntax, native tests, five keyless live smokes and exact contract bytes. Both `check` and `sync` use `/openapi.json`. On HTTP 404 only, they emit a visible warning and use `/api/v1/agent/openapi.json`.

CI runs on every push, PR and weekly. The live probe check fails if a request fails or a sample lacks its title or sample marker.

Install [gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1 and configure each clone:

```bash
git config core.hooksPath .githooks
bash scripts/scan-secrets.sh
```

The pre-push hook scans all Git refs/history and working-tree files with 100% redaction, including untracked files, and fails closed when the scanner is missing or history is shallow. A fresh repository has no history to scan; that condition is reported explicitly. Hooks are local configuration, so repeat setup for every clone. GitHub secret scanning/push protection must be enabled before owner-approved public release.

## Scope and status


MIT applies only to example code, scripts and tests (including hook/CI code). The OpenAPI contract, documentation, skill text and legal texts are excluded; see [LICENSE](LICENSE). No claim is made about the origin of legal texts.
