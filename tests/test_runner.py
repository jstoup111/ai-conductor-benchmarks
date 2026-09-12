import argparse
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

loader = importlib.machinery.SourceFileLoader('bench', str(Path(__file__).resolve().parents[1] / 'scripts/bench'))
spec = importlib.util.spec_from_loader(loader.name, loader)
b = importlib.util.module_from_spec(spec)
loader.exec_module(b)


def row(kind, seconds, **extra):
    return dict(type=kind, mono=seconds, ts=seconds, **extra)


class MetricsTests(unittest.TestCase):
    def setUp(self):
        self.m = dict(run_id='test', task='small', profile='codex', model='fixed', effort='high')

    def test_attention_and_wait_overlap_elapsed_not_added(self):
        rows = [row('run_started', 0), row('session_started', 0),
                row('attention_started', 2, category='monitoring'), row('attention_stopped', 5),
                row('help_requested', 10), row('attention_started', 12, category='rescue'),
                row('help_resolved', 18), row('attention_stopped', 20),
                row('session_exited', 30), row('run_finished', 40, outcome='completed', attention_complete=True)]
        result = b.summarize(self.m, rows)
        self.assertEqual(result['execution_seconds'], 40)
        self.assertEqual(result['session_seconds'], 30)
        self.assertEqual(result['human_seconds'], 11)
        self.assertEqual(result['help_wait_seconds'], 8)
        self.assertEqual(result['intervention_episodes'], 1)
        self.assertIsNone(result['accepted'])

    def test_resumed_sessions_keep_between_session_wait(self):
        rows = [row('run_started', 0), row('session_started', 0), row('session_exited', 5),
                row('session_started', 20), row('session_exited', 25),
                row('run_finished', 30, outcome='failed')]
        result = b.summarize(self.m, rows)
        self.assertEqual(result['session_seconds'], 10)
        self.assertEqual(result['execution_seconds'], 30)
        self.assertEqual(result['status'], 'failed')

    def test_unfinished_is_not_success_and_open_attention_is_visible(self):
        with patch.object(b.time, 'monotonic', return_value=25):
            result = b.summarize(self.m, [row('run_started', 10),
                                  row('attention_started', 15, category='approval')])
        self.assertEqual(result['human_seconds'], 10)
        self.assertEqual(result['status'], 'running')
        self.assertIsNone(result['accepted'])
        self.assertIsNone(result['attention_complete'])

    def test_setup_failure_has_no_execution_time(self):
        result = b.summarize(self.m, [row('preparation_failed', 0)])
        self.assertIsNone(result['execution_seconds'])
        self.assertIsNone(result['accepted'])


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'run'
        self.path.mkdir()
        (self.path / 'events.jsonl').touch()
        self.m = dict(run_id='run', task='small', profile='codex', model='fixed', effort='high',
                      container='acb-exact-test', seconds_limit=100)
        b.write_json(self.path / 'manifest.json', self.m)
        b.write_json(self.path / 'task.json', dict(criteria={'S1': 'works', 'S2': 'authorized'}))
        self.patch = patch.object(b, 'RUNS', Path(self.temp.name))
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def emit(self, kind, **extra):
        b.emit(self.path, kind, **extra)

    def test_double_attention_and_after_finish_rejected(self):
        self.emit('run_started')
        args = argparse.Namespace(run='run', action='on', category='monitoring')
        b.mark(args)
        with self.assertRaisesRegex(ValueError, 'already on'):
            b.mark(args)
        self.emit('run_finished', outcome='failed')
        with self.assertRaisesRegex(ValueError, 'already finished'):
            b.mark(argparse.Namespace(run='run', action='off'))

    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError):
            b.run_dir('../other')

    def test_corrupt_ledger_does_not_silently_drop_evidence(self):
        (self.path/'events.jsonl').write_text('{bad json\n')
        with self.assertRaises(json.JSONDecodeError):
            b.events(self.path)

    def test_missing_publication_remote_fails_before_execution_clock(self):
        (self.path/'workspace').mkdir()
        self.m.update(publish=True, input_inventory={})
        b.write_json(self.path/'manifest.json', self.m)
        self.emit('preparation_completed')
        with patch.object(b, 'capture', return_value=''), patch.object(b, 'call') as call:
            with self.assertRaisesRegex(ValueError, 'dedicated origin'):
                b.start(argparse.Namespace(run='run'))
            call.assert_not_called()
        self.assertIsNone(b.latest(b.events(self.path), 'run_started'))

    def test_wrong_remote_baseline_fails_before_launch(self):
        (self.path/'workspace').mkdir()
        self.m.update(publish=True, input_inventory={}, baseline_commit='expected')
        b.write_json(self.path/'manifest.json', self.m)
        self.emit('preparation_completed')
        with patch.object(b, 'capture', side_effect=['origin', b.FORK_URL, b.FORK_URL, 'wrong refs/heads/main']), patch.object(b, 'call') as call:
            with self.assertRaisesRegex(ValueError, 'frozen trial base branch'):
                b.start(argparse.Namespace(run='run'))
            self.assertEqual(call.call_args.args[0], ['docker','exec','acb-exact-test','gh','auth','status'])
        self.assertIsNone(b.latest(b.events(self.path), 'run_started'))

    def test_finish_refuses_active_session_before_process_boundary(self):
        self.emit('run_started')
        self.emit('session_started')
        with patch.object(b, 'call') as call, patch.object(b, 'snapshot') as snapshot:
            with self.assertRaisesRegex(ValueError, 'Exit the trial session'):
                b.finish(argparse.Namespace(run='run', outcome='completed', attention_complete=True))
            call.assert_not_called()
            snapshot.assert_not_called()

    def test_finish_timeout_uses_only_manifest_container_and_closes_attention(self):
        self.emit('run_started')
        self.emit('attention_started', category='rescue')
        self.m['seconds_limit'] = 0
        b.write_json(self.path / 'manifest.json', self.m)
        with patch.object(b, 'call') as call, patch.object(b, 'snapshot'):
            b.finish(argparse.Namespace(run='run', outcome='completed', attention_complete=True))
            self.assertEqual(call.call_args.args[0], ['docker','stop','--time','5','acb-exact-test'])
        self.assertEqual(b.latest(b.events(self.path), 'run_finished')['outcome'], 'timeout')
        self.assertIsNone(b.attention_open(b.events(self.path)))

    def assessment(self, **extra):
        result = dict(criteria={'S1':True, 'S2':True}, reviewer='independent reviewer',
                      evidence='review/behavior.log', critical_defects=0,
                      regressions_pass=True, maintainability=4)
        result.update(extra)
        path = Path(self.temp.name)/'assessment.json'
        b.write_json(path, result)
        return argparse.Namespace(run='run', file=str(path))

    def test_exit_does_not_pass_and_critical_defect_blocks_acceptance(self):
        self.emit('run_started')
        self.emit('session_exited', exit_code=0)
        with self.assertRaisesRegex(ValueError, 'Finish execution'):
            b.assess(self.assessment())
        self.emit('run_finished', outcome='completed')
        b.assess(self.assessment(critical_defects=1))
        self.assertFalse(b.latest(b.events(self.path), 'assessment_recorded')['accepted'])

    def test_missing_criterion_cannot_be_accepted(self):
        self.emit('run_finished', outcome='completed')
        with self.assertRaisesRegex(ValueError, 'exactly'):
            b.assess(self.assessment(criteria={'S1':True}))

    def test_complete_quality_and_evidence_are_required_for_acceptance(self):
        self.emit('run_finished', outcome='completed')
        self.emit('final_capture_completed')
        b.assess(self.assessment())
        self.assertTrue(b.latest(b.events(self.path), 'assessment_recorded')['accepted'])
        with self.assertRaisesRegex(ValueError, 'Already assessed'):
            b.assess(self.assessment())

    def test_missing_final_evidence_blocks_acceptance(self):
        self.emit('run_finished', outcome='completed')
        b.assess(self.assessment())
        self.assertFalse(b.latest(b.events(self.path), 'assessment_recorded')['accepted'])

    def test_timeout_cannot_be_accepted_even_with_all_criteria_passed(self):
        self.emit('run_finished', outcome='timeout')
        b.assess(self.assessment())
        self.assertFalse(b.latest(b.events(self.path), 'assessment_recorded')['accepted'])


class IsolationTests(unittest.TestCase):
    def test_copy_excludes_nested_provider_config_and_preserves_project_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source, target = root/'source', root/'target'
            (source/'.claude/skills').mkdir(parents=True)
            (source/'app/.agents').mkdir(parents=True)
            (source/'AGENTS.md').write_text('ordinary project guidance')
            (source/'CLAUDE.md').write_text('stale provider-specific content')
            (source/'.claude/skills/private').write_text('do not copy')
            (source/'app/model.rb').write_text('class Model; end')
            b.copy_fixture(source, target)
            self.assertFalse((target/'.claude').exists())
            self.assertFalse((target/'app/.agents').exists())
            self.assertEqual((target/'CLAUDE.md').read_text(), (target/'AGENTS.md').read_text())
            self.assertTrue((target/'app/model.rb').exists())

    def test_external_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'source').mkdir()
            (root/'source/escape').symlink_to('/etc/passwd')
            with self.assertRaisesRegex(ValueError, 'escapes'):
                b.copy_fixture(root/'source', root/'target')

    def test_all_briefs_have_exact_assessment_criteria(self):
        for size in ('small','medium','large'):
            path = b.ROOT/'benchmarks'/size
            task = json.loads((path/'task.json').read_text())
            form = json.loads((path/'assessment.example.json').read_text())
            self.assertEqual(set(task['criteria']), set(form['criteria']))
            self.assertGreater(task['minutes_limit'], 0)
            self.assertIn('Execution contract:', (path/'prompt.md').read_text())

if __name__ == '__main__':
    unittest.main()

class EvidenceTests(unittest.TestCase):
    def test_runtime_exclusion_never_drops_production_storage_code(self):
        self.assertTrue(b.runtime_path('storage/development.sqlite3'))
        self.assertTrue(b.runtime_path('.worktrees/feature/storage/test.sqlite3'))
        self.assertFalse(b.runtime_path('app/models/storage/tracked.rb'))
        self.assertFalse(b.runtime_path('.worktrees/feature/app/models/storage/tracked.rb'))

    def test_candidate_archives_are_immutable_and_include_untracked_source(self):
        import tarfile
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path/'workspace/app').mkdir(parents=True)
            (path/'workspace/app/new.rb').write_text('version one')
            (path/'events.jsonl').touch()
            b.write_json(path/'manifest.json',dict(container='exact-fixture',baseline_commit='abc'))
            with patch.object(b, 'capture', return_value=''), patch.object(b, 'call'), patch.object(b.subprocess, 'run'):
                b.snapshot(path)
                (path/'workspace/app/new.rb').write_text('version two')
                b.snapshot(path)
            archives = sorted((path/'evidence').glob('*/workspace.tar.gz'))
            self.assertEqual(len(archives), 2)
            with tarfile.open(archives[0]) as archive:
                self.assertEqual(archive.extractfile('workspace/app/new.rb').read(), b'version one')
            with tarfile.open(archives[1]) as archive:
                self.assertEqual(archive.extractfile('workspace/app/new.rb').read(), b'version two')

class PublicationAndReleaseTests(unittest.TestCase):
    def test_hook_accepts_only_operator_fork(self):
        import subprocess
        hook = b.ROOT/'scripts/hooks/pre-push'
        cases = {
            b.FORK_URL: True,
            'git@github.com:jstoup111/ai-conductor-benchmarks.git': True,
            'https://github.com/basecamp/fizzy.git': False,
            'git@github.com:basecamp/fizzy.git': False,
            'https://github.com/jstoup111/fizzy.git': False,
            'https://github.com.evil.invalid/jstoup111/ai-conductor-benchmarks.git': False,
        }
        for url, allowed in cases.items():
            # Invoke the pure hook directly: never contact any git remote.
            result = subprocess.run([str(hook), 'origin', url], input=b'', capture_output=True)
            self.assertEqual(result.returncode == 0, allowed, url)

    def test_release_and_criterion_results_survive_report(self):
        m = dict(run_id='r', task='small', profile='harness-claude', model='fixed', effort='high',
                 release='v1.2.3', harness_commit='abc')
        rows = [row('run_started', 0), row('run_finished', 20, outcome='completed'),
                row('assessment_recorded', 30, accepted=False, passed=1, total=2,
                    critical_defects=0, maintainability=3, criteria={'S1':True,'S2':False})]
        report = b.summarize(m, rows)
        self.assertEqual(report['release'], 'v1.2.3')
        self.assertEqual(report['harness_commit'], 'abc')
        self.assertEqual(report['criteria'], {'S1':True,'S2':False})
