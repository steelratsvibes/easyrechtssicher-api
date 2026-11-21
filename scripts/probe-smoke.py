#!/usr/bin/env python3
"""Check the five example clients against the public document probe."""
from itertools import product
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = (
    ('Python', 'python3', 'python/smoke.py'),
    ('Next.js', 'node', 'nextjs/smoke.mjs'),
    ('Astro', 'node', 'astro/smoke.mjs'),
    ('Laravel', 'php', 'laravel/smoke.php'),
    ('PHP', 'php', 'php/smoke.php'),
)


def sample_titles(result):
    samples = [response['data'] for response in result['samples']]
    expected = list(product(('impressum', 'dse'), ('de', 'en')))
    if [(row['doc_type'], row['language']) for row in samples] != expected:
        raise ValueError('Unexpected sample coverage')
    for row in samples:
        if row['meta'].get('sample') is not True or 'Muster – nicht verwenden' not in row['title']:
            raise ValueError('Probe response is missing its sample marker or title')
    return [f"{row['doc_type']}/{row['language']} HTTP 200 {row['title']}" for row in samples]


def main():
    for index, (label, runtime, example) in enumerate(EXAMPLES):
        if index:
            # Each client makes five requests. Wait after completion so any
            # rolling minute contains at most two batches from this run.
            time.sleep(31)
        completed = subprocess.run(
            [runtime, 'examples/' + example, 'samples'], cwd=ROOT, check=True, stdout=subprocess.PIPE
        )
        titles = sample_titles(json.loads(completed.stdout))
        print(f'{label} /documents HTTP 200', flush=True)
        for title in titles:
            print(f'{label} {title}', flush=True)


if __name__ == '__main__':
    main()
