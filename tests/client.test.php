<?php
declare(strict_types=1);
require_once __DIR__ . '/../examples/shared/client.php';
use function EasyRechtssicherExample\run;
use function EasyRechtssicherExample\request;
if ((int)ini_get('zend.assertions') !== 1) { fwrite(STDERR, "Enable zend.assertions=1\n"); exit(1); }
$cases = json_decode(file_get_contents(__DIR__ . '/responses.json'), true, 512, JSON_THROW_ON_ERROR);
$count = 0;
function check(string $name, callable $test): void {
    global $count;
    try { $test(); $count++; }
    catch (Throwable) { fwrite(STDERR, "FAIL: $name\n"); exit(1); }
}
function rejects(callable $call): void {
    try { $call(); } catch (RuntimeException $e) {
        assert($e->getMessage() === 'API request or response failed'); return;
    }
    throw new LogicException('Expected failure');
}
foreach ($cases as $c) check($c['name'], function () use ($c) {
    $call = fn() => request('/fixture', $c['kind'], null, fn() => [200, 'application/json', json_encode($c['body'])]);
    if ($c['ok']) assert(json_encode($call()) === json_encode(json_decode(json_encode($c['body']))));
    else rejects($call);
});
foreach ([301, 304, 401, 403, 404, 422, 429, 500] as $status) check("HTTP $status", fn() => rejects(fn() => request('/fixture', 'stack', null, fn() => [$status, 'application/json', 'private'])));
foreach ([['application/json', '{private'], ['text/html', '{}'], ['application/json', str_repeat('x', 2 * 1024 * 1024 + 1)]] as [$type, $body]) check('invalid body/media/size', fn() => rejects(fn() => request('/fixture', 'stack', null, fn() => [200, $type, $body])));
check('network/timeout sanitized', fn() => rejects(fn() => run('stack', function () { throw new RuntimeException('private'); })));
check('keyless omits auth', function () use ($cases) {
    run('stack', function ($url, $headers) use ($cases) {
        assert($url === 'https://easyrechtssicher.de/api/v1/agent/stack-check?tools=HighLevel');
        assert(!isset($headers['Authorization']));
        return [200, 'application/json', json_encode($cases[0]['body'])];
    }, ['EASYRECHTSSICHER_API_KEY' => 'ignored']);
});
check('documents sequence and one key', function () use ($cases) {
    $calls = [];
    $result = run('documents', function ($url, $headers) use (&$calls, $cases) {
        $calls[] = $url;
        assert($headers['Authorization'] === 'Bearer fixture-only');
        return [200, 'application/json', json_encode($cases[count($calls) === 1 ? 1 : 2]['body'])];
    }, ['EASYRECHTSSICHER_API_KEY' => 'fixture-only']);
    assert($calls === ['https://easyrechtssicher.de/api/v1/agent/documents', 'https://easyrechtssicher.de/api/v1/agent/documents/impressum?lang=de']);
    assert($result['document']->data->doc_type === 'impressum');
});
check('samples always use the public probe', function () use ($cases) {
    $calls = 0;
    run('samples', function ($url, $headers) use (&$calls, $cases) {
        assert($headers['Authorization'] === 'Bearer ers_test_public_sample_do_not_use');
        $body = $cases[++$calls === 1 ? 1 : 2]['body'];
        if ($calls > 1) {
            [$path, $language] = explode('?lang=', $url);
            $body['data']['doc_type'] = basename($path);
            $body['data']['language'] = $language;
        }
        return [200, 'application/json', json_encode($body)];
    }, ['EASYRECHTSSICHER_API_KEY' => 'fixture-only']);
    assert($calls === 5);
});
check('documents require a key before transport', function () {
    $send = function () { throw new LogicException('transport invoked'); };
    foreach ([[], ['EASYRECHTSSICHER_API_KEY' => null], ['EASYRECHTSSICHER_API_KEY' => false], ['EASYRECHTSSICHER_API_KEY' => '']] as $env) {
        try { run('documents', $send, $env); throw new LogicException('expected failure'); }
        catch (RuntimeException $e) { assert($e->getMessage() === 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.'); }
    }
});
check('invalid key and mode before transport', function () {
    $send = function () { throw new LogicException('transport invoked'); };
    foreach (['', "bad\r\nheader", str_repeat('x', 513)] as $key) {
        try { run('documents', $send, ['EASYRECHTSSICHER_API_KEY' => $key]); throw new LogicException('expected failure'); }
        catch (RuntimeException $e) { assert($e->getMessage() === 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.'); }
    }
    try { run('other', $send); throw new LogicException('expected failure'); }
    catch (RuntimeException $e) { assert($e->getMessage() === 'Use stack or documents or samples'); }
});
check('list failure prevents second request', function () {
    $count = 0;
    rejects(function () use (&$count) {
        run('documents', function () use (&$count) { $count++; return [401, 'application/json', 'private']; }, ['EASYRECHTSSICHER_API_KEY' => 'fixture-only']);
    });
    assert($count === 1);
});
echo "PHP native assertions: $count tests passed\n";
