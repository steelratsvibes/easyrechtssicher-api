import contextlib
import importlib.util
import io
import json
from pathlib import Path
from subprocess import CalledProcessError
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    'probe_smoke', Path(__file__).resolve().parents[1] / 'scripts/probe-smoke.py'
)
probe_smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe_smoke)


def sample_result():
    return {'documents': {'data': []}, 'samples': [
        {'data': {'doc_type': doc_type, 'language': language,
                  'title': 'Muster – nicht verwenden', 'meta': {'sample': True}}}
        for doc_type in ('impressum', 'dse') for language in ('de', 'en')
    ]}


class ProbeSmokeTests(unittest.TestCase):
    def test_runs_all_five_examples_with_rate_limit_spacing(self):
        output = io.StringIO()
        result = SimpleNamespace(stdout=json.dumps(sample_result()))
        with patch.object(probe_smoke.subprocess, 'run', return_value=result) as run, \
             patch.object(probe_smoke.time, 'sleep') as sleep, contextlib.redirect_stdout(output):
            probe_smoke.main()
        self.assertEqual(run.call_count, 5)
        self.assertTrue(all(call.args[0][-1] == 'samples' for call in run.call_args_list))
        self.assertEqual([call.args for call in sleep.call_args_list], [(31,)] * 4)
        self.assertEqual(output.getvalue().count('HTTP 200'), 25)

    def test_example_failure_fails_run(self):
        with patch.object(probe_smoke.subprocess, 'run', side_effect=CalledProcessError(1, 'example')):
            with self.assertRaises(CalledProcessError):
                probe_smoke.main()

    def test_requires_all_four_type_language_pairs(self):
        result = sample_result()
        result['samples'].pop()
        with self.assertRaisesRegex(ValueError, 'coverage'):
            probe_smoke.sample_titles(result)

    def test_requires_both_marker_and_title(self):
        for field, value in [('meta', {'sample': False}), ('title', 'Real text')]:
            with self.subTest(field=field):
                result = sample_result()
                result['samples'][0]['data'][field] = value
                with self.assertRaisesRegex(ValueError, 'sample marker or title'):
                    probe_smoke.sample_titles(result)
