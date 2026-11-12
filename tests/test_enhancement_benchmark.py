from pathlib import Path
import json
import os
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import run_enhancement_benchmark as benchmark


class EnhancementBenchmarkTests(unittest.TestCase):
    def test_environment_allowlist_removes_secret_canary(self):
        source = {'PATH': '/bin', 'HOME': '/unchanged', 'LAZY_EVAL_SYNTHETIC_SECRET': 'secret'}
        actual = benchmark.benchmark_environment(source)
        self.assertEqual(actual, {'PATH': '/bin', 'HOME': '/unchanged'})
        self.assertNotIn('LAZY_EVAL_SYNTHETIC_SECRET', actual)

    def test_failure_hints_never_persist_raw_stderr(self):
        self.assertEqual(benchmark.classify_failure('HTTP 429 secret-token'), 'possible_rate_or_quota_limit')
        self.assertEqual(benchmark.classify_failure('unexpected secret-token'), 'unclassified')

    def test_router_workspace_uses_selected_agents_not_snippet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source, target = root / 'source', root / 'target'
            (source / '.agents/skills/example').mkdir(parents=True)
            (source / '.agents/skills/example/SKILL.md').write_text('skill')
            (source / 'AGENTS.md').write_text('selected baseline')
            (source / 'AGENTS.snippet.md').write_text('different snippet')
            (source / '.engram').mkdir()
            target.mkdir()
            benchmark.prepare_router_workspace(source, target)
            self.assertEqual((target / 'AGENTS.md').read_text(), 'selected baseline')
            self.assertFalse((target / '.engram').exists())

    def test_snapshot_applies_dirty_patch_in_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo, output = root / 'repo', root / 'snapshot'
            repo.mkdir(); output.mkdir()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), 'config', 'user.name', 'Test'], check=True)
            subprocess.run(['git', '-C', str(repo), 'config', 'user.email', 'test@example.invalid'], check=True)
            (repo / 'AGENTS.md').write_text('original\n')
            subprocess.run(['git', '-C', str(repo), 'add', 'AGENTS.md'], check=True)
            subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'base'], check=True)
            (repo / 'AGENTS.md').write_text('local change\n')
            patch = root / 'baseline.patch'
            patch.write_bytes(subprocess.run(['git', '-C', str(repo), 'diff', '--binary'], capture_output=True, check=True).stdout)
            with mock.patch.object(benchmark, 'ROOT', repo):
                meta = benchmark.snapshot('HEAD', patch, output)
            self.assertEqual((output / 'AGENTS.md').read_text(), 'local change\n')
            self.assertEqual((repo / 'AGENTS.md').read_text(), 'local change\n')
            self.assertEqual(len(meta['commit']), 40)
            self.assertEqual(len(meta['patch_sha256']), 64)

    def test_unavailable_codex_is_blocked_without_fabricated_result(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / '.agents/skills/example').mkdir(parents=True)
            (source / '.agents/skills/example/SKILL.md').write_text('skill')
            (source / 'AGENTS.md').write_text('rules')
            case = {'prompt': 'Inspect', 'primary': 'example', 'interaction': 'automatic'}
            result = benchmark.trial(source, case, '/missing/codex', 'model', 2, source / 'schema')
            self.assertEqual(result['outcome'], 'blocked')
            self.assertNotIn('routing', result)

    def test_trial_uses_restricted_profile_and_sanitized_environment(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)
            (source / '.agents/skills/example').mkdir(parents=True)
            (source / '.agents/skills/example/SKILL.md').write_text('skill')
            (source / 'AGENTS.md').write_text('rules')
            case = {'prompt': 'Inspect', 'primary': 'example', 'interaction': 'automatic'}
            def run(command, **kwargs):
                self.assertNotIn('--sandbox', command)
                self.assertIn(benchmark.FILESYSTEM_PROFILE, command)
                self.assertIn('hooks', command)
                self.assertIn('apps', command)
                self.assertNotIn('SYNTHETIC_TOKEN', kwargs['env'])
                output = Path(command[command.index('--output-last-message') + 1])
                output.write_text(json.dumps({'interaction': 'automatic', 'primary': 'example',
                                              'supporting': [], 'user_message': 'I will inspect it.'}))
                return SimpleNamespace(returncode=0, stderr='')
            with mock.patch.dict(os.environ, {'SYNTHETIC_TOKEN': 'synthetic-secret'}), \
                 mock.patch.object(benchmark.subprocess, 'run', side_effect=run):
                result = benchmark.trial(source, case, 'codex', 'model', 2, source / 'schema')
            self.assertEqual(result['outcome'], 'pass')

    def test_schema_enumerates_blocked_and_nullable_unknowns(self):
        schema = json.loads((benchmark.ROOT / 'docs/schemas/enhancement_run.schema.json').read_text())
        self.assertIn('blocked', schema['properties']['outcome']['enum'])
        self.assertIn('null', schema['properties']['metrics']['properties']['context_tokens']['type'])
        self.assertIn('repository_commit', schema['required'])

    def test_incomplete_run_can_resume_only_with_identical_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            corpus = root / 'cases.yaml'
            corpus.write_text('cases:\n- id: first\n  prompt: one\n- id: second\n  prompt: two\n')
            output = root / 'output'
            args = ['--baseline', 'HEAD', '--corpus', str(corpus), '--trials', '3',
                    '--model', 'same-model', '--output', str(output)]
            metadata = {'commit': 'a' * 40, 'patch_sha256': None}
            blocked = {'outcome': 'blocked', 'errors': ['unavailable'], 'wall_ms': 1}
            passed = {'outcome': 'pass', 'errors': [], 'wall_ms': 1}
            with mock.patch.object(benchmark, 'isolation_preflight', return_value=True), \
                 mock.patch.object(benchmark, 'snapshot', return_value=metadata), \
                 mock.patch.object(benchmark, 'trial', side_effect=lambda *a: dict(blocked)):
                self.assertEqual(benchmark.main(args), 2)
            first = json.loads((output / 'routing-ab.json').read_text())
            self.assertFalse(first['complete'])
            self.assertEqual(len(first['results']), 3)
            changed = args.copy()
            changed[changed.index('same-model')] = 'other-model'
            with mock.patch.object(benchmark, 'isolation_preflight', return_value=True), \
                 mock.patch.object(benchmark, 'snapshot', return_value=metadata):
                self.assertEqual(benchmark.main(changed + ['--resume']), 2)
            with mock.patch.object(benchmark, 'isolation_preflight', return_value=True), \
                 mock.patch.object(benchmark, 'snapshot', return_value=metadata), \
                 mock.patch.object(benchmark, 'trial', side_effect=lambda *a: dict(passed)) as run:
                self.assertEqual(benchmark.main(args + ['--resume']), 1)
                self.assertEqual(run.call_count, 3)
            result = json.loads((output / 'routing-ab.json').read_text())
            self.assertTrue(result['complete'])
            self.assertEqual(len(result['results']), 6)
            self.assertEqual([x['outcome'] for x in result['results'][:3]], ['blocked'] * 3)

    def test_failed_isolation_never_runs_a_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(benchmark, 'isolation_preflight', return_value=False), \
                 mock.patch.object(benchmark, 'trial') as run:
                code = benchmark.main(['--baseline', 'HEAD', '--model', 'example',
                                       '--output', str(Path(tmp) / 'out')])
                self.assertEqual(code, 2)
                run.assert_not_called()


if __name__ == '__main__':
    unittest.main()
