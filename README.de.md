# easyRechtssicher Rechtstexte-API

[![CI](https://github.com/steelratsvibes/easyrechtssicher-api/actions/workflows/checks.yml/badge.svg)](https://github.com/steelratsvibes/easyrechtssicher-api/actions/workflows/checks.yml)

Serverseitige Beispiele für **Impressum** und **Datenschutzerklärung** als JSON. Zuerst den Tool-Stack kostenlos und ohne Schlüssel prüfen. [English](README.md).

```bash
node examples/nextjs/smoke.mjs stack
```

Der Aufruf verwendet `GET https://easyrechtssicher.de/api/v1/agent/stack-check?tools=HighLevel` ohne Anmeldung. Er prüft die Katalogabdeckung, nicht die Rechtskonformität. [API-Einstieg](https://easyrechtssicher.de/agent-api).

## Fünf Beispiele ausführen

Voraussetzungen: Node.js 22+, PHP 8.2+ mit HTTPS-Streams/OpenSSL und `allow_url_fopen`, Python 3.10+, vertrauenswürdige System-CA-Zertifikate. Keine zusätzlichen npm-, Composer- oder pip-Abhängigkeiten. Frameworks stellt die bestehende Host-Anwendung bereit.

| Beispiel | Schlüsselfreier Live-Test | Host-Adapter |
|---|---|---|
| Next.js | `node examples/nextjs/smoke.mjs stack` | [route.mjs](examples/nextjs/route.mjs) |
| Astro | `node examples/astro/smoke.mjs stack` | [endpoint.mjs](examples/astro/endpoint.mjs) |
| Laravel | `php examples/laravel/smoke.php stack` | [routes.php](examples/laravel/routes.php), [config.php](examples/laravel/config.php) |
| PHP | `php examples/php/smoke.php stack` | [index.php](examples/php/index.php) |
| Python | `python3 examples/python/smoke.py stack` | `run` aus [client.py](examples/python/client.py) im Servercode importieren |

CLI und Host-Adapter verwenden denselben Clientcode. Erfolg liefert JSON; CLI-Fehler liefern eine feste Meldung und einen Fehler-Exitcode. Host-Adapter antworten bei Fehlern mit generischem JSON und Status 502, immer mit `private, no-store`. HTML aus `data.text` wird nicht gerendert.

## Dokumente mit einem Schlüssel abrufen

Im Modus `documents` vor dem Start des Beispiels den eigenen Registration-API-Schlüssel mit aktiver Lizenz als `EASYRECHTSSICHER_API_KEY` setzen. Fehlt der Schlüssel, bricht das Beispiel ab.

Alle fünf Beispiele mit dem öffentlichen Probe-Schlüssel prüfen:

```bash
python3 scripts/probe-smoke.py
```

Das Skript verwendet den Modus `samples`, der immer den öffentlichen Probe-Schlüssel nutzt. Jedes Beispiel ruft die Dokumentliste sowie Impressum und DSE auf Deutsch und Englisch ab. Zwischen den Blöcken mit je fünf Anfragen hält das Skript das Limit von zehn Anfragen pro Minute und IP ein.

Im aktuellen Vertrag fehlt das Antwortschema der Dokumentliste. Die Clients prüfen dort nur JSON-Objekt und `data`-Container; sie erraten keine Eintragsfelder, leiten keine Verfügbarkeit ab und folgen keinen Antwort-URLs. Dokumentantworten werden auf angeforderten Typ/Sprache, Format, Text, Titel und Metadaten geprüft. Zusätzliche Felder sind erlaubt. Das ist keine vollständige JSON-Schema-Prüfung.

## In eine bestehende Anwendung einbauen

Gemeinsame Clients außerhalb von Browser-Bundles und öffentlichen/static Verzeichnissen halten. Keine `NEXT_PUBLIC_`-, `PUBLIC_`- oder `VITE_`-Variable für den Schlüssel. Serverseitig `EASYRECHTSSICHER_MODE=documents` setzen, sobald der Dokumentabruf eingerichtet ist; Standard ist `stack`.

- **Next.js App Router:** `examples/shared/client.mjs` nach `lib/easyrechtssicher.mjs` kopieren, `examples/nextjs/route.mjs` nach `app/api/rechtstexte/route.js`. Import auf `../../../lib/easyrechtssicher.mjs` ändern. Node-Runtime und dynamische Route beibehalten. `/api/rechtstexte` abrufen.
- **Astro:** bestehende serverseitige Anwendung mit Node-Server-Adapter verwenden. Gemeinsamen Client nach `src/lib/easyrechtssicher.mjs`, `endpoint.mjs` nach `src/pages/api/rechtstexte.js` kopieren; Import auf `../../lib/easyrechtssicher.mjs` ändern. `prerender = false` beibehalten. Serverumgebung zur Laufzeit konfigurieren. `/api/rechtstexte` abrufen.
- **Laravel:** `examples/shared` und `examples/laravel` nach `<app>/examples/` kopieren. `examples/laravel/config.php` nach `<app>/config/easyrechtssicher.php` kopieren. In `routes/web.php` die Zeile `require base_path('examples/laravel/routes.php');` ergänzen. Serverumgebung vor dem Neuaufbau des Konfigurationscaches setzen. `/rechtstexte` abrufen; bei vertraulichen Dokumenten die Zugriffskontrollen der Host-Anwendung anwenden.
- **PHP:** `examples/` außerhalb des Webroots halten und `examples/php/index.php` aus einem öffentlichen Endpunkt einbinden. Lokale schlüsselfreie Demo: `php -S 127.0.0.1:8080 -t examples/php`, danach `/index.php` abrufen. Der eingebaute Server dient nur der lokalen Entwicklung.
- **Python:** serverseitig `run('stack')` oder `run('documents')` aufrufen und das Ergebnis als JSON serialisieren. Der CLI-Test verwendet dieselbe Funktion.

Dies sind Host-Adapter, keine neu angelegten Framework-Anwendungen. Framework-Builds und Deployment sind in der jeweiligen Host-Anwendung zu prüfen; CLI-Tests belegen kein vollständiges Framework-Deployment.

Fester HTTPS-Ursprung `https://easyrechtssicher.de`, TLS-Prüfung, keine Weiterleitungen, nur Status 200 akzeptiert. Auch 304 schlägt fehl, da kein Cache geführt wird. JS: 15 Sekunden Abbruchfrist; PHP/Python: 15 Sekunden Verbindungs-/Lese-Timeout plus Lesefrist. Maximal 2 MiB Antwort. Keine automatischen Wiederholungen, auch nicht bei 429. Fehler geben weder Antwortkörper noch Schlüssel aus. Erfolgreiches Dokument-JSON ist die beabsichtigte Ausgabe und gehört nicht in öffentliche CI-Protokolle.

## Prüfen und Vertrag aktualisieren

```bash
bash scripts/verify.sh --offline
bash scripts/verify.sh
python3 scripts/spec.py check
python3 scripts/spec.py sync
```

`verify.sh` prüft Syntax, native Tests, fünf schlüsselfreie Live-Aufrufe und den Vertrag bytegenau. `check` und `sync` verwenden `/openapi.json`. Nur bei HTTP 404 melden sie eine sichtbare Warnung und verwenden `/api/v1/agent/openapi.json`.

CI läuft bei jedem Push, PR und wöchentlich. Der Probe-Lauf schlägt fehl, wenn eine Anfrage fehlschlägt oder Mustertitel oder Mustermarker fehlen.

[gitleaks](https://github.com/gitleaks/gitleaks) 8.30.1 installieren und jeden Klon konfigurieren:

```bash
git config core.hooksPath .githooks
bash scripts/scan-secrets.sh
```

Der Pre-Push-Hook prüft die gesamte Historie aller Referenzen und den Arbeitsbaum einschließlich unversionierter Dateien mit vollständiger Schwärzung. Fehlender Scanner oder flache Historie blockieren den Push. In einer frischen Ablage wird ausdrücklich gemeldet, dass noch keine Historie existiert. Hook-Konfiguration ist lokal und muss pro Klon erfolgen. GitHub-Geheimnissuche und Push-Schutz sind vor der späteren freigegebenen Veröffentlichung einzuschalten.

## Umfang und Status


MIT gilt ausschließlich für Beispielcode, Skripte und Tests einschließlich Hook-/CI-Code. OpenAPI-Vertrag, Dokumentation, Skill-Text und Rechtstexte sind ausgenommen; siehe [LICENSE](LICENSE). Keine Aussage zur Herkunft der Rechtstexte.
