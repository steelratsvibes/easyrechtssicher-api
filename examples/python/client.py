"""Server-side stdlib client; never forwards redirects or logs upstream errors."""
import json
import os
import re
import time
import urllib.request

ORIGIN = 'https://easyrechtssicher.de/api/v1/agent'
KEY_ERROR = 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.'
PROBE_KEY = 'ers_test_public_sample_do_not_use'
LIMIT = 2 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def transport(url, headers):
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(urllib.request.Request(url, headers=headers), timeout=15) as response:
        deadline = time.monotonic() + 15
        chunks = []
        size = 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError()
            chunk = response.read1(min(8192, LIMIT + 1 - size))
            if not chunk:
                break
            chunks.append(chunk)
            size += len(chunk)
            if size > LIMIT:
                raise ValueError()
        return response.status, response.headers.get('Content-Type', ''), b''.join(chunks)


def validate(value, kind, doc_type='impressum', language='de'):
    def string(x):
        return isinstance(x, str) and bool(x)
    valid = isinstance(value, dict) and 'error' not in value
    if valid and kind == 'stack':
        rows = value.get('results')
        valid = isinstance(rows, list) and len(rows) == 1
        if valid:
            r = rows[0]
            valid = (isinstance(r, dict) and r.get('input') == 'HighLevel'
                     and r.get('status') in ('covered', 'not_covered', 'ambiguous')
                     and isinstance(r.get('candidates'), list)
                     and (r['status'] != 'covered' or
                          isinstance(r.get('match'), dict) and string(r['match'].get('slug'))))
    elif valid and kind == 'list':
        # No list schema in live contract: envelope only, no inferred fields.
        valid = isinstance(value.get('data'), (dict, list))
    elif valid:
        d = value.get('data')
        valid = isinstance(d, dict)
        if valid:
            m = d.get('meta')
            valid = (d.get('doc_type') == doc_type and d.get('language') == language
                     and d.get('format') == 'html' and string(d.get('title'))
                     and string(d.get('text')) and isinstance(m, dict)
                     and all(string(m.get(k)) for k in ('content_hash', 'source', 'jurisdiction'))
                     and 'stand' in m and (m['stand'] is None or string(m['stand'])))
    if not valid:
        raise ValueError('Invalid API response')
    return value


def request(path, kind, key=None, send=transport, doc_type='impressum', language='de'):
    try:
        headers = {'Accept': 'application/json'}
        if key:
            headers['Authorization'] = 'Bearer ' + key
        status, content_type, body = send(ORIGIN + path, headers)
        if status != 200 or not re.match(r'^application/json(?:;|$)', content_type, re.I) or len(body) > LIMIT:
            raise ValueError()
        return validate(json.loads(body), kind, doc_type, language)
    except Exception:
        raise ValueError('API request or response failed') from None


def run(mode='stack', send=transport, env=None):
    if mode not in ('stack', 'documents', 'samples'):
        raise ValueError('Use stack or documents or samples')
    if mode == 'stack':
        return request('/stack-check?tools=HighLevel', 'stack', send=send)
    environment = os.environ if env is None else env
    key = PROBE_KEY if mode == 'samples' else environment.get('EASYRECHTSSICHER_API_KEY')
    if not isinstance(key, str) or not re.fullmatch(r'[\x21-\x7e]{1,512}', key):
        raise ValueError(KEY_ERROR)
    documents = request('/documents', 'list', key, send)
    if mode == 'samples':
        samples = [
            request(f'/documents/{doc_type}?lang={language}', 'document', key, send, doc_type, language)
            for doc_type in ('impressum', 'dse')
            for language in ('de', 'en')
        ]
        return {'documents': documents, 'samples': samples}
    document = request('/documents/impressum?lang=de', 'document', key, send)
    return {'documents': documents, 'document': document}
