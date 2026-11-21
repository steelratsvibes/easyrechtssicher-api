#!/usr/bin/env python3
"""Byte-preserving live spec sync and strict drift check."""
import argparse
import os
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch(legacy):
    path = '/api/v1/agent/openapi.json' if legacy else '/openapi.json'
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open('https://easyrechtssicher.de' + path, timeout=20) as response:
        if response.status != 200 or response.headers.get_content_type() != 'application/json':
            raise ValueError()
        deadline = time.monotonic() + 20
        chunks = []
        size = 0
        while True:
            if time.monotonic() >= deadline:
                raise TimeoutError()
            chunk = response.read1(8192)
            if not chunk:
                break
            size += len(chunk)
            if size > 4 * 1024 * 1024:
                raise ValueError()
            chunks.append(chunk)
        body = b''.join(chunks)
    value = json.loads(body)
    if not isinstance(value, dict) or value.get('openapi') != '3.1.0' or not isinstance(value.get('paths'), dict):
        raise ValueError()
    return body


def fetch_current():
    try:
        return fetch(False)
    except urllib.error.HTTPError as error:
        if error.code != 404:
            raise
        error.close()
    print('::warning::/openapi.json returned HTTP 404; comparing the legacy endpoint.', file=sys.stderr)
    return fetch(True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['check', 'sync'])
    args = parser.parse_args()
    try:
        live = fetch_current()
        target = ROOT / 'openapi.json'
        if args.action == 'sync':
            fd, temporary_name = tempfile.mkstemp(prefix='.openapi.', suffix='.tmp', dir=target.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(fd, 'wb') as stream:
                    stream.write(live)
                temporary.replace(target)
            finally:
                temporary.unlink(missing_ok=True)
        elif target.read_bytes() != live:
            print('FAIL: OpenAPI drift; review and run sync explicitly.', file=sys.stderr)
            return 1
        print(f'{args.action}: SHA-256 {hashlib.sha256(live).hexdigest()}')
        return 0
    except Exception:
        print('FAIL: live spec unavailable or invalid. Fallback is allowed only on HTTP 404 from the standard endpoint.', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
