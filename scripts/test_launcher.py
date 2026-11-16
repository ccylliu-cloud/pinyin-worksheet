#!/usr/bin/env python3
"""Dependency-bootstrap behavior tests; never installs packages or accesses the network."""
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import run_worksheet as run

OK = {'ok': True, 'versions': {'reportlab': '4.4.9', 'pypdf': '6.21.4'}}
MISSING = {'ok': False, 'reason': 'missing'}


class LauncherTests(unittest.TestCase):
    def test_current_runtime_never_installs(self):
        with patch.object(run, 'check_runtime', return_value=OK), patch.object(run.subprocess, 'run') as child, patch.object(run.venv, 'EnvBuilder') as env:
            _, mode, _ = run.choose_runtime()
            self.assertEqual(mode, 'current')
            child.assert_not_called()
            env.assert_not_called()

    def test_cached_runtime_never_installs(self):
        with patch.object(run, 'check_runtime', side_effect=[MISSING, OK]), patch.object(run.subprocess, 'run') as child:
            _, mode, _ = run.choose_runtime('/tmp/test-cache')
            self.assertEqual(mode, 'cached')
            child.assert_not_called()

    def test_check_only_never_installs_when_missing(self):
        with patch.object(run, 'check_runtime', return_value=MISSING), patch.object(run.subprocess, 'run') as child, patch.object(run.venv, 'EnvBuilder') as env:
            with self.assertRaises(RuntimeError):
                run.choose_runtime('/tmp/test-cache', install=False)
            child.assert_not_called()
            env.assert_not_called()

    def test_first_install_is_isolated(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, 'check_runtime', side_effect=[MISSING, MISSING, OK]), patch.object(run.subprocess, 'run') as child, patch.object(run.venv, 'EnvBuilder') as env:
            with redirect_stderr(io.StringIO()):
                python, mode, _ = run.choose_runtime(tmp)
            self.assertEqual(mode, 'installed')
            self.assertTrue(python.is_relative_to(Path(tmp)))
            env.return_value.create.assert_called_once()
            command = child.call_args.args[0]
            self.assertEqual(command[0], str(python))
            self.assertIn('-r', command)
            self.assertNotIn('--break-system-packages', command)

    def test_failed_install_has_no_retry_loop(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, 'check_runtime', return_value=MISSING), patch.object(run.subprocess, 'run') as child, patch.object(run.venv, 'EnvBuilder'):
            with self.assertRaises(RuntimeError), redirect_stderr(io.StringIO()):
                run.choose_runtime(tmp)
            self.assertEqual(child.call_count, 1)

    def test_help_no_runtime_or_install(self):
        with patch.object(run, 'choose_runtime') as choose, redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(['--help']), 0)
            choose.assert_not_called()

    def test_missing_input_no_runtime_or_install(self):
        with patch.object(run, 'choose_runtime') as choose, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(run.main([]), 2)
            self.assertEqual(run.main(['-o', 'out.pdf']), 2)
            self.assertEqual(run.main(['-i']), 2)
            self.assertEqual(run.main(['-i', '/nonexistent/words.txt']), 2)
            choose.assert_not_called()

    def test_check_reports_available_without_generation(self):
        with patch.object(run, 'choose_runtime', return_value=(Path('/example/python'), 'cached', OK)) as choose, patch.object(run.subprocess, 'run') as child, redirect_stdout(io.StringIO()):
            self.assertEqual(run.main(['--check']), 0)
            self.assertFalse(choose.call_args.kwargs['install'])
            child.assert_not_called()

    def test_requirements_or_cache_root_changes_environment_path(self):
        a = run.cache_environment('/tmp/a')
        b = run.cache_environment('/tmp/b')
        self.assertNotEqual(a, b)
        with tempfile.TemporaryDirectory() as tmp, patch.object(run, 'ROOT', Path(tmp)):
            req = Path(tmp)/'requirements.txt'
            req.write_text('reportlab>=4.2,<5\n')
            first = run.cache_environment('/tmp/a')
            req.write_text('reportlab>=4.3,<5\n')
            self.assertNotEqual(first, run.cache_environment('/tmp/a'))

    def test_real_interpreter_probe(self):
        result = run.check_runtime(run.sys.executable)
        self.assertTrue(result['ok'], result)

if __name__ == '__main__':
    unittest.main(verbosity=2)
