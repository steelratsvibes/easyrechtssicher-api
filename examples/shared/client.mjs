// Server-only. Do not import into browser bundles.

const ORIGIN = 'https://easyrechtssicher.de/api/v1/agent';
export const KEY_ERROR = 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.';
const PROBE_KEY = 'ers_test_public_sample_do_not_use';
const LIMIT = 2 * 1024 * 1024;
const object = x => x !== null && typeof x === 'object' && !Array.isArray(x);
const string = x => typeof x === 'string' && x.length > 0;
export function validate(value, kind, docType = 'impressum', language = 'de') {
  if (!object(value) || 'error' in value) throw new Error('Invalid API response');
  if (kind === 'stack') {
    if (!Array.isArray(value.results) || value.results.length !== 1) throw new Error('Invalid API response');
    const r = value.results[0];
    if (!object(r) || r.input !== 'HighLevel' || !['covered', 'not_covered', 'ambiguous'].includes(r.status) ||
        !Array.isArray(r.candidates) || (r.status === 'covered' && (!object(r.match) || !string(r.match.slug)))) throw new Error('Invalid API response');
  } else if (kind === 'list') {
    // The live contract has no list schema. Validate the envelope only;
    // do not infer availability or follow URLs supplied by the response.
    if (!('data' in value) || !(object(value.data) || Array.isArray(value.data))) throw new Error('Invalid API response');
  } else {
    const d = value.data;
    if (!object(d) || d.doc_type !== docType || d.language !== language || d.format !== 'html' ||
        !string(d.title) || !string(d.text) || !object(d.meta) || !string(d.meta.content_hash) ||
        !string(d.meta.source) || !string(d.meta.jurisdiction) ||
        !(d.meta.stand === null || string(d.meta.stand))) throw new Error('Invalid API response');
  }
  return value;
}
export async function request(path, kind, key, transport = fetch, docType, language) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 15000);
  try {
    const headers = { Accept: 'application/json' };
    if (key) headers.Authorization = `Bearer ${key}`;
    const response = await transport(ORIGIN + path, { headers, signal: controller.signal, redirect: 'error', cache: 'no-store' });
    if (response.status !== 200) throw new Error('API request failed');
    if (!/^application\/json(?:;|$)/i.test(response.headers.get('content-type') || '')) throw new Error('Invalid API response');
    const reader = response.body.getReader();
    let size = 0;
    const chunks = [];
    try {
      while (true) {
        const {done, value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > LIMIT) throw new Error('Invalid API response');
        chunks.push(value);
      }
    } finally { await reader.cancel(); }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.length; }
    return validate(JSON.parse(new TextDecoder('utf-8', {fatal: true}).decode(bytes)), kind, docType, language);
  } catch { throw new Error('API request or response failed'); }
  finally { clearTimeout(timer); }
}
export async function run(mode = 'stack', transport = fetch, env = process.env) {
  if (typeof window !== 'undefined') throw new Error('Server only');
  if (!['stack', 'documents', 'samples'].includes(mode)) throw new Error('Use stack or documents or samples');
  if (mode === 'stack') return request('/stack-check?tools=HighLevel', 'stack', undefined, transport);
  const key = mode === 'samples' ? PROBE_KEY : env.EASYRECHTSSICHER_API_KEY;
  if (typeof key !== 'string' || !/^[\x21-\x7e]{1,512}$/.test(key)) throw new Error(KEY_ERROR);
  const documents = await request('/documents', 'list', key, transport);
  if (mode === 'samples') {
    const samples = [];
    for (const docType of ['impressum', 'dse']) {
      for (const language of ['de', 'en']) {
        samples.push(await request(`/documents/${docType}?lang=${language}`, 'document', key, transport, docType, language));
      }
    }
    return {documents, samples};
  }
  const document = await request('/documents/impressum?lang=de', 'document', key, transport);
  return {documents, document};
}
export async function respond(mode, transport = fetch, env = process.env) {
  try { return Response.json(await run(mode, transport, env), {headers: {'Cache-Control': 'private, no-store'}}); }
  catch (error) {
    const message = error?.message === KEY_ERROR ? KEY_ERROR : 'API request or response failed';
    return Response.json({error: message}, {status: 502, headers: {'Cache-Control': 'private, no-store'}});
  }
}
