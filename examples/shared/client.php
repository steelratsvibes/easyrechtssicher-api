<?php
declare(strict_types=1);
namespace EasyRechtssicherExample;

const KEY_ERROR = 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.';
const PROBE_KEY = 'ers_test_public_sample_do_not_use';

function transport(string $url, array $headers): array {
    $lines = [];
    foreach ($headers as $name => $value) $lines[] = "$name: $value";
    $context = stream_context_create(['http' => [
        'method' => 'GET', 'header' => implode("\r\n", $lines), 'timeout' => 15,
        'follow_location' => 0, 'max_redirects' => 0, 'ignore_errors' => true,
    ], 'ssl' => ['verify_peer' => true, 'verify_peer_name' => true]]);
    $stream = @fopen($url, 'rb', false, $context);
    if ($stream === false) throw new \RuntimeException('API request failed');
    try {
        $deadline = microtime(true) + 15;
        $body = '';
        while (!feof($stream)) {
            $remaining = $deadline - microtime(true);
            if ($remaining <= 0) throw new \RuntimeException('API request failed');
            stream_set_timeout($stream, (int)$remaining, (int)(($remaining - (int)$remaining) * 1000000));
            $chunk = @fread($stream, 8192);
            if ($chunk === false || stream_get_meta_data($stream)['timed_out']) throw new \RuntimeException('API request failed');
            $body .= $chunk;
            if (strlen($body) > 2 * 1024 * 1024) throw new \RuntimeException('API request failed');
        }
        $metadata = stream_get_meta_data($stream);
        if ($body === false || $metadata['timed_out']) throw new \RuntimeException('API request failed');
        $status = 0;
        $type = '';
        foreach ($metadata['wrapper_data'] ?? [] as $line) {
            if (preg_match('~^HTTP/\S+ (\d{3})~', $line, $m)) $status = (int)$m[1];
            if (stripos($line, 'Content-Type:') === 0) $type = trim(substr($line, 13));
        }
        return [$status, $type, $body];
    } finally { fclose($stream); }
}
function validString(mixed $v): bool { return is_string($v) && $v !== ''; }
function validate(mixed $v, string $kind, string $docType = 'impressum', string $language = 'de'): object {
    $ok = is_object($v) && !property_exists($v, 'error');
    if ($ok && $kind === 'stack') {
        $rows = $v->results ?? null;
        $ok = is_array($rows) && count($rows) === 1;
        if ($ok) {
            $r = $rows[0];
            $ok = is_object($r) && ($r->input ?? null) === 'HighLevel'
                && in_array($r->status ?? null, ['covered', 'not_covered', 'ambiguous'], true)
                && is_array($r->candidates ?? null)
                && ($r->status !== 'covered' || (is_object($r->match ?? null) && validString($r->match->slug ?? null)));
        }
    } elseif ($ok && $kind === 'list') {
        // No list schema in live contract: envelope only, no inferred fields.
        $ok = is_object($v->data ?? null) || is_array($v->data ?? null);
    } elseif ($ok) {
        $d = $v->data ?? null;
        $m = is_object($d) ? ($d->meta ?? null) : null;
        $ok = is_object($d) && ($d->doc_type ?? null) === $docType
            && ($d->language ?? null) === $language && ($d->format ?? null) === 'html'
            && validString($d->title ?? null) && validString($d->text ?? null)
            && is_object($m) && validString($m->content_hash ?? null)
            && validString($m->source ?? null) && validString($m->jurisdiction ?? null)
            && property_exists($m, 'stand') && ($m->stand === null || validString($m->stand));
    }
    if (!$ok) throw new \RuntimeException('Invalid API response');
    return $v;
}
function request(string $path, string $kind, ?string $key, callable $send, string $docType = 'impressum', string $language = 'de'): object {
    try {
        $headers = ['Accept' => 'application/json'];
        if ($key !== null) $headers['Authorization'] = 'Bearer ' . $key;
        [$status, $type, $body] = $send('https://easyrechtssicher.de/api/v1/agent' . $path, $headers);
        if ($status !== 200 || !preg_match('~^application/json(?:;|$)~i', $type) || strlen($body) > 2 * 1024 * 1024) throw new \RuntimeException();
        return validate(json_decode($body, false, 512, JSON_THROW_ON_ERROR), $kind, $docType, $language);
    } catch (\Throwable) { throw new \RuntimeException('API request or response failed'); }
}
function run(string $mode = 'stack', ?callable $send = null, ?array $env = null): array|object {
    $send ??= __NAMESPACE__ . '\\transport';
    if (!in_array($mode, ['stack', 'documents', 'samples'], true)) throw new \RuntimeException('Use stack or documents or samples');
    if ($mode === 'stack') return request('/stack-check?tools=HighLevel', 'stack', null, $send);
    $key = $mode === 'samples' ? PROBE_KEY
        : ($env === null ? getenv('EASYRECHTSSICHER_API_KEY') : ($env['EASYRECHTSSICHER_API_KEY'] ?? null));
    if (!is_string($key) || !preg_match('/^[\x21-\x7e]{1,512}$/D', $key)) throw new \RuntimeException(KEY_ERROR);
    $documents = request('/documents', 'list', $key, $send);
    if ($mode === 'samples') {
        $samples = [];
        foreach (['impressum', 'dse'] as $docType) {
            foreach (['de', 'en'] as $language) {
                $samples[] = request("/documents/$docType?lang=$language", 'document', $key, $send, $docType, $language);
            }
        }
        return compact('documents', 'samples');
    }
    $document = request('/documents/impressum?lang=de', 'document', $key, $send);
    return compact('documents', 'document');
}
function cli(array $args): void {
    try { echo json_encode(run($args[1] ?? 'stack'), JSON_THROW_ON_ERROR) . PHP_EOL; }
    catch (\Throwable $error) {
        fwrite(STDERR, ($error->getMessage() === KEY_ERROR ? KEY_ERROR : 'Example failed') . PHP_EOL);
        exit(1);
    }
}
