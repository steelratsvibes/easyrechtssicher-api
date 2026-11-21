import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { run, request, respond } from '../examples/shared/client.mjs';
const cases = JSON.parse(readFileSync(new URL('./responses.json', import.meta.url)));
const response = (body, status = 200, type = 'application/json') => new Response(body, {status, headers: {'Content-Type': type}});
for (const c of cases) test(c.name, async () => {
  const call = () => request('/fixture', c.kind, undefined, async () => response(JSON.stringify(c.body)));
  if (c.ok) assert.deepEqual(await call(), c.body);
  else await assert.rejects(call, /^Error: API request or response failed$/);
});
for (const status of [301, 401, 403, 404, 422, 429, 500]) test(`HTTP ${status} is sanitized`, async () => {
  await assert.rejects(() => request('/fixture', 'stack', undefined, async () => response('private body', status)), /^Error: API request or response failed$/);
});
test('304 fails without a cached body', async () => {
  await assert.rejects(() => request('/fixture', 'stack', undefined, async () => new Response(null, {status: 304})));
});
test('malformed JSON', async () => {
  await assert.rejects(() => request('/fixture', 'stack', undefined, async () => response('{private')));
});
test('wrong media type', async () => {
  await assert.rejects(() => request('/fixture', 'stack', undefined, async () => response('{}', 200, 'text/html')));
});
test('oversized response', async () => {
  await assert.rejects(() => request('/fixture', 'stack', undefined, async () => response('x'.repeat(2 * 1024 * 1024 + 1))));
});
test('network and timeout errors are sanitized', async () => {
  for (const name of ['Error', 'TimeoutError', 'AbortError']) {
    await assert.rejects(() => request('/fixture', 'stack', undefined, async () => { throw new DOMException('private', name); }), /^Error: API request or response failed$/);
  }
});
test('keyless ignores env and sets bounded no-redirect transport options', async () => {
  const env = new Proxy({}, {get() { throw new Error('env must not be read'); }});
  await run('stack', async (url, options) => {
    assert.equal(url, 'https://easyrechtssicher.de/api/v1/agent/stack-check?tools=HighLevel');
    assert.equal(options.headers.Authorization, undefined);
    assert.equal(options.redirect, 'error');
    assert.equal(options.cache, 'no-store');
    assert.ok(options.signal instanceof AbortSignal);
    return response(JSON.stringify(cases[0].body));
  }, env);
});
test('documents use one env key, list first, fixed document second', async () => {
  const calls = [];
  const result = await run('documents', async (url, options) => {
    calls.push(url);
    assert.equal(options.headers.Authorization, 'Bearer fixture-only');
    return response(JSON.stringify(cases[calls.length === 1 ? 1 : 2].body));
  }, {EASYRECHTSSICHER_API_KEY: 'fixture-only'});
  assert.deepEqual(calls, ['https://easyrechtssicher.de/api/v1/agent/documents', 'https://easyrechtssicher.de/api/v1/agent/documents/impressum?lang=de']);
  assert.deepEqual(result.document, cases[2].body);
});
test('samples always use the public probe', async () => {
  let calls = 0;
  const env = new Proxy({EASYRECHTSSICHER_API_KEY: 'fixture-only'}, {
    get() { assert.fail('env read in samples mode'); },
  });
  await run('samples', async (url, options) => {
    assert.equal(options.headers.Authorization, 'Bearer ers_test_public_sample_do_not_use');
    calls++;
    const parsed = new URL(url);
    const body = calls === 1 ? cases[1].body : {data: {
      ...cases[2].body.data, doc_type: parsed.pathname.split('/').at(-1), language: parsed.searchParams.get('lang'),
    }};
    return response(JSON.stringify(body));
  }, env);
  assert.equal(calls, 5);
});

test('documents require a key before transport', async () => {
  for (const env of [{}, ...[null, false, ''].map(key => ({EASYRECHTSSICHER_API_KEY: key}))]) {
    await assert.rejects(() => run('documents', () => assert.fail('transport invoked'), env), {
      message: 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.',
    });
  }
});

test('bad explicit key rejected before transport', async () => {
  for (const key of ['', 'bad\r\nheader', 'x'.repeat(513)]) {
    await assert.rejects(() => run('documents', () => assert.fail('transport invoked'), {EASYRECHTSSICHER_API_KEY: key}), /No API key set/);
  }
});
test('list failure prevents document request', async () => {
  let count = 0;
  await assert.rejects(() => run('documents', async () => { count++; return response('{}', 401); }, {EASYRECHTSSICHER_API_KEY: 'fixture-only'}));
  assert.equal(count, 1);
});
test('invalid mode never calls transport', async () => {
  await assert.rejects(() => run('other', () => assert.fail('transport invoked')), /Use stack or documents/);
});
test('adapter errors are JSON and private without upstream details', async () => {
  const res = await respond('stack', async () => { throw Error('private'); });
  assert.equal(res.status, 502);
  assert.equal(res.headers.get('Cache-Control'), 'private, no-store');
  assert.deepEqual(await res.json(), {error: 'API request or response failed'});
});
test('both framework adapters return JSON using their shared client', async () => {
  const savedFetch = globalThis.fetch;
  const savedMode = process.env.EASYRECHTSSICHER_MODE;
  try {
    process.env.EASYRECHTSSICHER_MODE = 'stack';
    globalThis.fetch = async () => response(JSON.stringify(cases[0].body));
    for (const path of ['../examples/nextjs/route.mjs', '../examples/astro/endpoint.mjs']) {
      const {GET} = await import(path);
      const res = await GET();
      assert.equal(res.status, 200);
      assert.deepEqual(await res.json(), cases[0].body);
    }
  } finally {
    globalThis.fetch = savedFetch;
    if (savedMode === undefined) delete process.env.EASYRECHTSSICHER_MODE;
    else process.env.EASYRECHTSSICHER_MODE = savedMode;
  }
});
