"""Reviewed public result records and code snapshots; never launches a trial."""
from collections import defaultdict
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import statistics
import subprocess
import tarfile
import tempfile
from urllib.parse import quote

START = '<!-- benchmark-results:start -->'
END = '<!-- benchmark-results:end -->'
OMIT = {'.git', '.claude', '.codex', '.agents', '.docs', '.pipeline', '.worktrees',
        '.ai-conductor', '.benchmark', '.githooks', 'AGENTS.md', 'CLAUDE.md',
        'BENCHMARK_TASK.md', 'HARNESS.md', 'ARCHITECTURE.md'}
IDENTITY = ['-c', 'user.name=Benchmark Archive', '-c', 'user.email=benchmark@invalid']


def git(root, *args, env=None, text=None):
    result = subprocess.run(['git', '-C', str(root), *args], input=text, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, env=env)
    return result.stdout.strip()


def label(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,90}', value):
        raise ValueError('Invalid release or run label')
    return value


def copy_source(archive, prefix, target, bench):
    """Extract source only, excluding process evidence, runtime state and common secret files."""
    prefix = PurePosixPath(prefix)
    target.mkdir()
    count = 0
    with tarfile.open(archive) as stream:
        for member in stream:
            full = PurePosixPath(member.name)
            if full.is_absolute() or '..' in full.parts:
                raise ValueError('Unsafe snapshot path')
            try:
                relative = full.relative_to(prefix)
            except ValueError:
                continue
            if not relative.parts:
                continue
            if relative.parts[0] in OMIT or bench.runtime_path(str(relative)):
                continue
            if any(part == '.env' or part.startswith('.env.') or part == 'master.key'
                   for part in relative.parts):
                continue
            destination = target / str(relative)
            if not destination.resolve().is_relative_to(target.resolve()):
                raise ValueError('Snapshot path escapes source tree')
            destination.parent.mkdir(parents=True, exist_ok=True)
            if member.isdir():
                destination.mkdir(exist_ok=True)
            elif member.issym():
                if Path(member.linkname).is_absolute() or not (destination.parent/member.linkname).resolve().is_relative_to(target.resolve()):
                    raise ValueError('Snapshot symlink escapes source tree')
                destination.symlink_to(member.linkname)
            elif member.isfile():
                with stream.extractfile(member) as source, destination.open('wb') as output:
                    shutil.copyfileobj(source, output)
                destination.chmod(0o755 if member.mode & 0o111 else 0o644)
                count += 1
            else:
                raise ValueError('Unsupported snapshot member: ' + member.name)
    if count == 0:
        raise ValueError('Selected result tree contains no source files')


def commit_source(root, source, index, message, parent=None, deterministic=False):
    env = os.environ.copy()
    env['GIT_INDEX_FILE'] = str(index)
    if deterministic:
        env.update(GIT_AUTHOR_DATE='2000-01-01T00:00:00+00:00', GIT_COMMITTER_DATE='2000-01-01T00:00:00+00:00')
    git(root, 'read-tree', '--empty', env=env)
    git(root, '--work-tree=' + str(source), 'add', '--all', '--force', env=env)
    tree = git(root, 'write-tree', env=env)
    args = [*IDENTITY, 'commit-tree', tree]
    if parent:
        args += ['-p', parent]
    return git(root, *args, env=env, text=message + '\n')


def archive_run(bench, args):
    run_id = label(args.run)
    path = Path(args.runs_dir).resolve()/run_id if args.runs_dir else bench.run_dir(run_id)
    m, rows = bench.manifest(path), bench.events(path)
    if m['run_id'] != run_id:
        raise ValueError('Run ID mismatch')
    if not all(bench.latest(rows, kind) for kind in ('run_finished', 'final_capture_completed', 'assessment_recorded')):
        raise ValueError('Only finished, captured, independently assessed runs can be archived')
    release = label(m['release'])
    tag = f'eval/{release}/{run_id}'
    record_path = bench.ROOT/'results/runs'/f'{run_id}.json'
    if record_path.exists() or git(bench.ROOT, 'tag', '--list', tag):
        raise ValueError('Run already archived; tags and result records are write-once')
    capture = bench.latest(rows, 'snapshot_saved')
    archive = (path/capture['evidence']/'workspace.tar.gz').resolve()
    if not archive.is_relative_to(path.resolve()):
        raise ValueError('Evidence path escapes run')
    if not capture.get('archive_sha256') or bench.digest(archive) != capture['archive_sha256']:
        raise ValueError('Final snapshot checksum missing or mismatched')
    if m['profile_config']['harness'] and not args.result_tree:
        raise ValueError('Daemon runs require --result-tree .worktrees/SLUG to select the actual implementation')
    selected = PurePosixPath(args.result_tree or '.')
    if selected.is_absolute() or '..' in selected.parts:
        raise ValueError('Invalid result tree')
    fixture_commit = m['fixture']['commit']
    if not re.fullmatch(r'[0-9a-f]{40,64}', fixture_commit):
        raise ValueError('Invalid fixture commit')
    with tempfile.TemporaryDirectory(prefix='benchmark-archive-') as directory:
        temp = Path(directory)
        git(bench.ROOT, 'archive', '--format=tar', '--output=' + str(temp/'baseline.tar'), fixture_commit)
        copy_source(temp/'baseline.tar', '.', temp/'baseline', bench)
        copy_source(archive, str(PurePosixPath('workspace')/selected), temp/'result', bench)
        base = commit_source(bench.ROOT, temp/'baseline', temp/'base.index',
                             'Normalized Fizzy baseline ' + fixture_commit, deterministic=True)
        commit = commit_source(bench.ROOT, temp/'result', temp/'result.index',
                               'Benchmark result ' + run_id, parent=base)
    record = dict(schema=1, run_id=run_id, release=release, tag=tag, baseline_commit=base,
                  result_commit=commit, snapshot_sha256=capture['archive_sha256'],
                  result_tree=str(selected), summary=bench.summarize(m, rows),
                  configuration={k:m.get(k) for k in ('harness_commit','model','effort','image',
                                 'prompt_sha256','fixture','cpus','memory','seconds_limit','publish')})
    content = json.dumps(record, indent=2, sort_keys=True) + '\n'
    record_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as message:
        message.write(content)
        message.flush()
        git(bench.ROOT, *IDENTITY, 'tag', '-a', tag, commit, '-F', message.name)
    with record_path.open('x') as file:
        file.write(content)
    print(f'Archived locally: {tag}\nCode commit: {commit}\nRecord: {record_path}')
    print('Review the code snapshot and public record before publish-run. No network operation was performed.')


def publish_run(bench, args):
    record = json.loads((bench.ROOT/'results/runs'/f'{label(args.run)}.json').read_text())
    ref = 'refs/tags/' + record['tag']
    if git(bench.ROOT, 'rev-parse', ref + '^{}') != record['result_commit']:
        raise ValueError('Tag target changed; refusing publication')
    tag_object = git(bench.ROOT, 'cat-file', '-p', ref)
    if json.loads(tag_object.split('\n\n', 1)[1]) != record:
        raise ValueError('Tag annotation differs from reviewed public result record')
    # Explicit destination and exact tag ref only. Never --tags or --force.
    bench.call(['git', '-C', bench.ROOT, 'push', bench.FORK_URL, ref])


def escaped(value):
    return str(value).replace('|', '\\|').replace('\n', ' ').replace('<', '&lt;').replace('>', '&gt;')


def median(values):
    values = [v for v in values if v is not None]
    return f'{statistics.median(values)/60:.1f}' if values else '—'


def render_reports(bench, args):
    release = label(args.release)
    readme = bench.ROOT/'README.md'
    text = readme.read_text()
    if text.count(START) != 1 or text.count(END) != 1 or text.index(START) > text.index(END):
        raise ValueError('README must contain exactly one ordered result marker pair')
    directory = bench.ROOT/'results/releases'
    directory.mkdir(parents=True, exist_ok=True)
    release_path = directory/f'{release}.json'
    if not release_path.exists():
        bench.write_json(release_path, dict(release=release))
    records = [json.loads(p.read_text()) for p in sorted((bench.ROOT/'results/runs').glob('*.json'))]
    releases = sorted({p.stem for p in directory.glob('*.json')} | {r['release'] for r in records})
    table = ['| Release | Task | Workflow / model | Runs | Accepted | Elapsed min¹ | Human min² | Interventions² |',
             '| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for version in releases:
        selected = [r for r in records if r['release'] == version]
        groups = defaultdict(list)
        for record in selected:
            # Do not combine configurations that differ in image, model, prompt or resource limits.
            key = (record['summary']['task'], record['summary']['profile'],
                   json.dumps(record['configuration'], sort_keys=True))
            groups[key].append(record)
        if not groups:
            table.append(f'| [{escaped(version)}](reports/{version}.md) | — | No archived results | 0 | — | — | — | — |')
        for (task, profile, config), group in sorted(groups.items()):
            summaries = [r['summary'] for r in group]
            complete = [s for s in summaries if s['attention_complete']]
            config_id = hashlib.sha256(config.encode()).hexdigest()[:8]
            model = escaped(summaries[0]['model'])
            attention = median([s['human_seconds'] for s in complete]) + f' ({len(complete)}/{len(group)})'
            interventions = str(statistics.median([s['intervention_episodes'] for s in complete])) if complete else '—'
            table.append(f'| [{escaped(version)}](reports/{version}.md) | {task} | {profile} / {model} `{config_id}` | {len(group)} | '
                         f'{sum(s["accepted"] is True for s in summaries)}/{len(group)} | '
                         f'{median([s["execution_seconds"] for s in summaries])} | {attention} | {interventions} |')
        detail = [f'# Harness {version}: archived benchmark results', '',
                  'These are archived, independently assessed runs, including failures and timeouts. Missing results are not evidence of support or failure.', '',
                  '| Run | Task / workflow | Outcome | Criteria | Missing criteria | Result code | Change from baseline |',
                  '| --- | --- | --- | --- | --- | --- | --- |']
        for record in selected:
            s = record['summary']
            missing = ', '.join(k for k,v in (s.get('criteria') or {}).items() if not v) or 'none'
            base = 'https://github.com/' + bench.FORK
            detail.append(f'| [{record["run_id"]}](../results/runs/{record["run_id"]}.json) | {s["task"]} / {s["profile"]} | '
                          f'{s["status"]}; accepted={s["accepted"]} | {s["criteria_passed"]}/{s["criteria_total"]} | {missing} | '
                          f'[snapshot]({base}/tree/{record["result_commit"]}) | '
                          f'[diff]({base}/compare/{record["baseline_commit"]}..{record["result_commit"]}) |')
        if not selected:
            detail += ['', 'No archived runs for this release.']
        detail += ['', 'Commit links become available after publishing the run tags. Configuration and full metrics are in each run record.',
                   'For two runs, use `scripts/bench compare-runs OLD_RUN NEW_RUN`; it prints an exact two-commit code comparison link.']
        (bench.ROOT/'reports').mkdir(exist_ok=True)
        (bench.ROOT/'reports'/f'{version}.md').write_text('\n'.join(detail)+'\n')
    if not releases:
        table += ['| — | — | No archived results | 0 | — | — | — | — |']
    body = '\n'.join(table) + '\n\n¹ Median across all archived outcomes, including failures/timeouts.\n² Only attention-complete runs; human column shows complete/total coverage. No aggregate claim is made across different configuration IDs.\n'
    before, rest = text.split(START, 1)
    _, after = rest.split(END, 1)
    readme.write_text(before + START + '\n' + body + END + after)
    print('Updated README metrics and release reports. Review and commit these files through a PR to your fork.')


def compare_runs(bench, args):
    records = [json.loads((bench.ROOT/'results/runs'/f'{label(name)}.json').read_text())
               for name in (args.old, args.new)]
    a,b = records
    if a['summary']['task'] != b['summary']['task']:
        raise ValueError('Different tasks: this is not a like-for-like comparison')
    if a['baseline_commit'] != b['baseline_commit']:
        print('CAUTION: baseline code differs; the diff includes that change.')
    print('https://github.com/' + bench.FORK + '/compare/' + a['result_commit'] + '..' + b['result_commit'])
    print(json.dumps({r['run_id']:r['summary'] for r in records}, indent=2))
