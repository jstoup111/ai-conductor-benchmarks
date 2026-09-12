import argparse
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from test_runner import b, row

spec = importlib.util.spec_from_file_location('results', b.ROOT/'scripts/results.py')
r = importlib.util.module_from_spec(spec)
spec.loader.exec_module(r)


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.patch = patch.object(b, 'ROOT', self.root)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        (self.root/'app').mkdir()
        (self.root/'app/model.rb').write_text('original\n')
        (self.root/'app/deleted.rb').write_text('remove me\n')
        subprocess.run(['git','-C',str(self.root),'add','.'],check=True)
        subprocess.run(['git','-C',str(self.root),*r.IDENTITY,'commit','-qm','fixture'],check=True)
        fixture = r.git(self.root,'rev-parse','HEAD')
        self.head = fixture
        self.run = self.root/'.runs/r1'
        (self.run/'evidence/final').mkdir(parents=True)
        archive = self.run/'evidence/final/workspace.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for name, content in {'workspace/app/model.rb':'changed\n','workspace/app/new.rb':'added\n',
                                  'workspace/.env':'DO_NOT_EXPORT', 'workspace/.pipeline/log.txt':'private'}.items():
                data = content.encode()
                info = tarfile.TarInfo(name)
                info.size = len(data)
                tar.addfile(info,io.BytesIO(data))
        self.m = dict(run_id='r1',release='v1',task='small',profile='codex',model='fixed',effort='high',
                      profile_config={'harness':False},fixture={'commit':fixture},image='image',
                      prompt_sha256='prompt',cpus=4,memory='8g',seconds_limit=60,publish=False)
        b.write_json(self.run/'manifest.json',self.m)
        self.rows = [row('run_started',0), row('run_finished',10,outcome='completed',attention_complete=True),
                     row('snapshot_saved',11,evidence='evidence/final',archive_sha256=b.digest(archive)),
                     row('final_capture_completed',12),
                     row('assessment_recorded',13,accepted=True,passed=1,total=1,critical_defects=0,
                         maintainability=4,criteria={'S1':True})]
        self.save_events()
        self.args = argparse.Namespace(run='r1',runs_dir=str(self.root/'.runs'),result_tree=None)
        (self.root/'README.md').write_text('Introduction\n'+r.START+'\nold\n'+r.END+'\nKeep this prose\n')

    def save_events(self):
        (self.run/'events.jsonl').write_text(''.join(json.dumps(e)+'\n' for e in self.rows))

    def test_archive_preserves_diff_and_does_not_change_head_or_index(self):
        before = r.git(self.root,'write-tree')
        r.archive_run(b,self.args)
        record = json.loads((self.root/'results/runs/r1.json').read_text())
        diff = r.git(self.root,'diff','--name-status',record['baseline_commit'],record['result_commit'])
        self.assertIn('M\tapp/model.rb',diff)
        self.assertIn('A\tapp/new.rb',diff)
        self.assertIn('D\tapp/deleted.rb',diff)
        files = r.git(self.root,'ls-tree','-r','--name-only',record['result_commit'])
        self.assertNotIn('.env',files)
        self.assertNotIn('.pipeline',files)
        self.assertEqual(r.git(self.root,'rev-parse','HEAD'),self.head)
        self.assertEqual(r.git(self.root,'write-tree'),before)
        with self.assertRaisesRegex(ValueError,'write-once'):
            r.archive_run(b,self.args)

    def test_missing_assessment_refuses_tag(self):
        self.rows.pop()
        self.save_events()
        with self.assertRaisesRegex(ValueError,'assessed'):
            r.archive_run(b,self.args)
        self.assertEqual(r.git(self.root,'tag','--list'),'')

    def test_tampered_snapshot_refuses_tag(self):
        with (self.run/'evidence/final/workspace.tar.gz').open('ab') as f:
            f.write(b'tampered')
        with self.assertRaisesRegex(ValueError,'checksum'):
            r.archive_run(b,self.args)
        self.assertEqual(r.git(self.root,'tag','--list'),'')

    def test_daemon_requires_explicit_implementation_selection(self):
        self.m['profile_config']['harness']=True
        b.write_json(self.run/'manifest.json',self.m)
        with self.assertRaisesRegex(ValueError,'result-tree'):
            r.archive_run(b,self.args)

    def test_daemon_archives_selected_worktree_not_root_checkout(self):
        self.m['profile_config']['harness']=True
        b.write_json(self.run/'manifest.json',self.m)
        archive=self.run/'evidence/final/workspace.tar.gz'
        with tarfile.open(archive,'w:gz') as tar:
            for name, content in {'workspace/app/model.rb':'wrong root',
                                  'workspace/.worktrees/feature/app/model.rb':'actual implementation'}.items():
                data=content.encode()
                info=tarfile.TarInfo(name)
                info.size=len(data)
                tar.addfile(info,io.BytesIO(data))
        self.rows[2]['archive_sha256']=b.digest(archive)
        self.save_events()
        self.args.result_tree='.worktrees/feature'
        r.archive_run(b,self.args)
        record=json.loads((self.root/'results/runs/r1.json').read_text())
        self.assertEqual(r.git(self.root,'show',record['result_commit']+':app/model.rb'),'actual implementation')

    def test_bad_readme_markers_do_not_write_partial_reports(self):
        (self.root/'README.md').write_text('no markers')
        with self.assertRaisesRegex(ValueError,'marker'):
            r.render_reports(b,argparse.Namespace(release='v1'))
        self.assertFalse((self.root/'results/releases/v1.json').exists())

    def test_publishing_is_exact_ref_to_fork_and_rejects_record_edit(self):
        r.archive_run(b,self.args)
        with patch.object(b,'call') as call:
            r.publish_run(b,self.args)
            self.assertEqual(call.call_args.args[0],['git','-C',self.root,'push',b.FORK_URL,'refs/tags/eval/v1/r1'])
        path = self.root/'results/runs/r1.json'
        record=json.loads(path.read_text())
        record['summary']['human_seconds']=999
        b.write_json(path,record)
        with patch.object(b,'call') as call:
            with self.assertRaisesRegex(ValueError,'annotation'):
                r.publish_run(b,self.args)
            call.assert_not_called()

    def test_reports_preserve_readme_and_show_missing_release_without_fake_metrics(self):
        r.archive_run(b,self.args)
        r.render_reports(b,argparse.Namespace(release='v1'))
        readme=(self.root/'README.md').read_text()
        self.assertIn('Introduction',readme)
        self.assertIn('Keep this prose',readme)
        self.assertIn('1/1',readme)
        r.render_reports(b,argparse.Namespace(release='v2'))
        self.assertIn('No archived results',(self.root/'README.md').read_text())
        self.assertIn('No archived runs',(self.root/'reports/v2.md').read_text())

    def test_failed_run_with_incomplete_attention_is_retained(self):
        self.rows[1].update(outcome='timeout',attention_complete=False)
        self.rows[-1].update(accepted=False,passed=0,criteria={'S1':False})
        self.save_events()
        r.archive_run(b,self.args)
        r.render_reports(b,argparse.Namespace(release='v1'))
        self.assertIn('0/1',(self.root/'README.md').read_text())
        self.assertIn('— (0/1)',(self.root/'README.md').read_text())
        self.assertIn('timeout',(self.root/'reports/v1.md').read_text())
        self.assertIn('S1',(self.root/'reports/v1.md').read_text())


class RefGuardTests(unittest.TestCase):
    def test_tag_replacement_and_deletion_refused_without_network(self):
        hook=b.ROOT/'scripts/hooks/pre-push'
        for local,remote,success in [('a'*40,'0'*40,True),('a'*40,'b'*40,False),('0'*40,'b'*40,False)]:
            line=f'refs/tags/eval/v1/r {local} refs/tags/eval/v1/r {remote}\n'
            result=subprocess.run([str(hook),'origin',b.FORK_URL],input=line,text=True,capture_output=True)
            self.assertEqual(result.returncode==0,success)
