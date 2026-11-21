import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples/python'))
import client

CASES = json.loads(Path(__file__).with_name('responses.json').read_text())


class ClientTests(unittest.TestCase):
    def test_http_errors(self):
        for status in [301, 304, 401, 403, 404, 422, 429, 500]:
            with self.subTest(status=status), self.assertRaisesRegex(ValueError, '^API request or response failed$'):
                client.request('/fixture', 'stack', send=lambda *_: (status, 'application/json', b'private'))

    def test_invalid_encoding_media_and_size(self):
        for content_type, body in [('application/json', b'{private'), ('text/html', b'{}'), ('application/json', b'x' * (client.LIMIT + 1))]:
            with self.subTest(type=content_type, size=len(body)), self.assertRaises(ValueError):
                client.request('/fixture', 'stack', send=lambda *_: (200, content_type, body))

    def test_network_timeout_sanitized(self):
        def send(*_):
            raise TimeoutError('private')
        with self.assertRaisesRegex(ValueError, '^API request or response failed$'):
            client.run(send=send)

    def test_keyless_does_not_read_env(self):
        class Env(dict):
            def get(self, *_):
                self.fail('env read')
        def send(url, headers):
            self.assertEqual(url, client.ORIGIN + '/stack-check?tools=HighLevel')
            self.assertNotIn('Authorization', headers)
            return 200, 'application/json', json.dumps(CASES[0]['body']).encode()
        client.run(send=send, env=Env())

    def test_document_sequence(self):
        calls = []
        def send(url, headers):
            calls.append(url)
            self.assertEqual(headers['Authorization'], 'Bearer fixture-only')
            return 200, 'application/json', json.dumps(CASES[1 if len(calls) == 1 else 2]['body']).encode()
        result = client.run('documents', send, {'EASYRECHTSSICHER_API_KEY': 'fixture-only'})
        self.assertEqual(calls, [client.ORIGIN + '/documents', client.ORIGIN + '/documents/impressum?lang=de'])
        self.assertEqual(result['document'], CASES[2]['body'])

    def test_samples_always_use_public_probe(self):
        class Env(dict):
            def get(self, *_):
                raise AssertionError('env read in samples mode')

        calls = []
        def send(url, headers):
            calls.append(url)
            self.assertEqual(headers['Authorization'], 'Bearer ers_test_public_sample_do_not_use')
            if len(calls) == 1:
                body = CASES[1]['body']
            else:
                path, language = url.split('?lang=')
                body = {'data': dict(CASES[2]['body']['data'], doc_type=path.split('/')[-1], language=language)}
            return 200, 'application/json', json.dumps(body).encode()
        client.run('samples', send, Env(EASYRECHTSSICHER_API_KEY='fixture-only'))
        self.assertEqual(len(calls), 5)

    def test_documents_require_key_before_transport(self):
        def send(*_):
            self.fail('transport invoked')
        for env in ({}, *({'EASYRECHTSSICHER_API_KEY': key} for key in (None, False, ''))):
            with self.subTest(env=env):
                with self.assertRaises(ValueError) as error:
                    client.run('documents', send, env)
                self.assertEqual(str(error.exception), 'Kein API-Schlüssel gesetzt (EASYRECHTSSICHER_API_KEY). Für Muster ohne Konto: Modus `samples`. / No API key set (EASYRECHTSSICHER_API_KEY). For samples without an account, use `samples` mode.')

    def test_invalid_key_and_mode(self):
        def send(*_):
            self.fail('transport invoked')
        for key in ['', 'bad\r\nheader', 'x' * 513]:
            with self.subTest(key_length=len(key or '')), self.assertRaises(ValueError):
                client.run('documents', send, {'EASYRECHTSSICHER_API_KEY': key})
        with self.assertRaises(ValueError):
            client.run('other', send)

    def test_list_failure_stops(self):
        calls = []
        def send(*args):
            calls.append(args)
            return 401, 'application/json', b'private'
        with self.assertRaises(ValueError):
            client.run('documents', send, {'EASYRECHTSSICHER_API_KEY': 'fixture-only'})
        self.assertEqual(len(calls), 1)

    def test_redirect_handler(self):
        self.assertIsNone(client.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.invalid'))


def make_case(case):
    def test(self):
        send = lambda *_: (200, 'application/json', json.dumps(case['body']).encode())
        if case['ok']:
            self.assertEqual(client.request('/fixture', case['kind'], send=send), case['body'])
        else:
            with self.assertRaisesRegex(ValueError, '^API request or response failed$'):
                client.request('/fixture', case['kind'], send=send)
    return test


for i, case in enumerate(CASES):
    setattr(ClientTests, f'test_response_{i:02d}_{case["name"].replace(" ", "_")}', make_case(case))
