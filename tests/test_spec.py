import contextlib
import io
from pathlib import Path
import sys
import tempfile
from urllib.error import HTTPError
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import spec


class SpecTests(unittest.TestCase):
    def invoke(self, args, local, live=None, failure=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'openapi.json').write_bytes(local)
            output = io.StringIO()
            with patch.object(spec, 'ROOT', root), patch.object(sys, 'argv', ['spec.py'] + args), patch.object(spec, 'fetch', return_value=live, side_effect=failure) as fetch, contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                code = spec.main()
            return code, (root / 'openapi.json').read_bytes(), output.getvalue(), fetch.call_args_list

    def test_equal_bytes(self):
        self.assertEqual(self.invoke(['check'], b'{}\n', b'{}\n')[0], 0)

    def test_even_whitespace_is_drift(self):
        code, body, _, _ = self.invoke(['check'], b'{}\n', b'{}')
        self.assertEqual(code, 1)
        self.assertEqual(body, b'{}\n')

    def test_invalid_response_does_not_fall_back(self):
        code, body, output, calls = self.invoke(['check'], b'old', failure=ValueError('private'))
        self.assertEqual(code, 1)
        self.assertEqual(body, b'old')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].args, (False,))
        self.assertNotIn('private', output)

    def test_404_falls_back_with_warning(self):
        missing = HTTPError('/openapi.json', 404, 'Not found', {}, None)
        code, _, output, calls = self.invoke(['check'], b'{}', failure=[missing, b'{}'])
        self.assertEqual(code, 0)
        self.assertIn('::warning::', output)
        self.assertEqual([call.args for call in calls], [(False,), (True,)])

    def test_other_http_errors_do_not_fall_back(self):
        failure = HTTPError('/openapi.json', 503, 'Unavailable', {}, None)
        code, _, _, calls = self.invoke(['check'], b'{}', failure=failure)
        self.assertEqual(code, 1)
        self.assertEqual([call.args for call in calls], [(False,)])

    def test_sync_preserves_bytes(self):
        live = b'{ "openapi": "3.1.0" }\r\n'
        code, body, _, _ = self.invoke(['sync'], b'old', live)
        self.assertEqual(code, 0)
        self.assertEqual(body, live)

    def test_sync_ignores_symlink_at_old_temporary_path(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            unrelated = root / 'unrelated'
            unrelated.write_bytes(b'untouched')
            (root / 'openapi.json.tmp').symlink_to(unrelated)
            with patch.object(spec, 'ROOT', root), patch.object(sys, 'argv', ['spec.py', 'sync']), \
                 patch.object(spec, 'fetch', return_value=b'new'), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(spec.main(), 0)
            self.assertEqual(unrelated.read_bytes(), b'untouched')
            self.assertEqual((root / 'openapi.json').read_bytes(), b'new')
            self.assertTrue((root / 'openapi.json.tmp').is_symlink())

    def test_failed_sync_preserves_existing(self):
        code, body, _, _ = self.invoke(['sync'], b'old', failure=TimeoutError())
        self.assertEqual(code, 1)
        self.assertEqual(body, b'old')
