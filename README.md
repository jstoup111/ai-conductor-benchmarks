# AI Conductor Benchmarks

Compare **execution** using AI Conductor's daemon with direct Claude Code or Codex on the same Rails application. Measure final output quality, elapsed execution time, and active human attention. Specification/plan preparation, image building, initial authentication, and independent grading happen outside the execution clock.

**This repository is setup, not completed evaluation results. No agent trials have been run.** See [setup validation](docs/setup-validation.md) for what was checked and what remains unexercised.

## Repository layout

```text
fixtures/fizzy/       Pinned Fizzy application, original guidance and license
fixtures/UPSTREAM.json  Source commit and provenance
benchmarks/{small,medium,large}/
  prompt.md          Implementation-ready feature request (same for all arms)
  task.json          Acceptance criteria and initial time cap
  assessment.example.json
scripts/bench        Host-side runner, attention controls, assessments, reports
scripts/build-harness  Build a separate image from a committed harness checkout
docker/              Development images and application preparation
profiles.json        Four execution configurations
.runs/               Local-only manifests, event ledgers, output, and workspaces
```

The baseline is Fizzy commit `19a22eae3cf6562d0f6fc810ceedf7934e45d61f`. Its source remains unmodified under `fixtures/fizzy`. Root tools are benchmark tooling; they are never mounted into a trial.

## Setup now

Requires Linux, Python 3.12+, Git, Docker Engine, and util-linux `script`. The current container user is UID/GID 1000; `doctor` verifies the host matches. Docker Desktop/macOS support is not yet validated.

```bash
scripts/bench doctor
python3 -m unittest discover -s tests
scripts/bench list
scripts/bench schedule --repeats 2 --seed 42 > schedule.json
scripts/bench build
scripts/build-harness ~/code/ai-conductor
```

Image builds install dependencies and the pinned coding-agent CLIs; they do **not** launch agents or execute benchmark tasks. Keep the resulting image IDs fixed throughout an experiment. Fizzy's production image is unsuitable for development; the benchmark image installs test gems and Chromium. It deliberately avoids Fizzy's host-package-manager `bin/setup`.

Prepare approved harness plans separately using [the harness preparation contract](docs/harness.md). No feature implementation is included in this repository.

## Feature distribution

| Size | Feature | Intended scope | Initial execution cap |
| --- | --- | --- | --- |
| Small | [Card effort estimates](benchmarks/small/prompt.md) | Validation, persistence, small UI change | 60 min |
| Medium | [Due dates and overdue filtering](benchmarks/medium/prompt.md) | Date semantics, UI, combined filters, authorization | 150 min |
| Large | [Card dependencies](benchmarks/large/prompt.md) | Graph rules, multiple write paths, permissions, concurrency | 300 min |

These are **provisional complexity labels and safety caps**, not measured runtimes. Freeze them before trials; calibrate them in a separate pilot. Each task starts from the same baseline: medium and large do not inherit the small feature. Three tasks test three cases, not the distribution of all Rails work. Use repetitions and report each size separately.

## Execute later

The commands below intentionally launch real trials. Do not run them during repository setup.

Choose explicit model IDs. Profiles use normal interactive permission behavior; they do not force permission bypass. The harness package owns its provider/model routing; record and match that configuration if studying harness overhead alone. The `--model` and `--effort` arguments label the intended configuration; direct profiles apply them, while daemon profiles use their prepared config.

```bash
# Creates a fresh workspace/container and prepares Rails; no agent starts yet.
scripts/bench prepare small claude --model YOUR_CLAUDE_MODEL --effort high
scripts/bench prepare small codex --model YOUR_CODEX_MODEL --effort high

# Alternative: exactly one pre-approved feature package, prepared before execution.
scripts/bench prepare small harness-claude --model YOUR_CLAUDE_MODEL --publish \
  --prepared /path/to/prepared/small-claude
```

Normal daemon SHIP requires `--publish`. For matched comparisons, pass `--publish` to direct trials too; it adds identical publication authorization to their prompts. Configure a dedicated remote and GitHub login in preparation; `start` refuses publication trials until their frozen baseline is present on that remote. It never pushes during preparation automatically.

Only one container can bind the default port 3006. Prepare/run sequentially, or select a distinct `--port`. Use the printed run ID in the commands below. Only explicitly named API-key variables are passed into a container; host home/config/skills are never mounted. Alternatively, authenticate inside its fresh home:

```bash
scripts/bench login RUN_ID
# For daemon SHIP: configure dedicated GitHub remote/auth before start; see docs/harness.md.
scripts/bench configure RUN_ID
scripts/bench start RUN_ID
```

`start` launches the interactive coding agent, or the real **foreground daemon process** with one worker and a one-feature cap. It is the daemon execution loop, not an inline pipeline or a skill-only substitute. Launch/exit hooks, a flushed terminal recording, and a host-owned timeout wrap both configurations. Closing the terminal does not mean the feature passed.

In a second terminal, use the attention console:

```bash
scripts/bench attention RUN_ID
```

Press a category key and Enter when you begin attending, and `o` then Enter when you leave. The console supports monitoring, clarification, approvals, steering, and rescue. It can also mark help requested/resolved. These events measure **your actual attention**, not agent guesses. Use `scripts/bench shell RUN_ID` for troubleshooting inside the trial; that wrapper automatically times rescue attention and captures shell output.

If a session exits before completion, `start RUN_ID` can launch another session against its existing workspace; all elapsed time remains in the same run. Direct agents start a new conversation by default, so explain the remaining work and count that attention. A dead wrapper can be stopped and recorded with `recover RUN_ID`; do not silently discard the failed run.

```bash
scripts/bench mark RUN_ID candidate
scripts/bench finish RUN_ID --outcome completed --attention-complete
# Other outcomes: failed, timeout, abandoned
```

`--attention-complete` is your explicit attestation that you recorded all attention intervals. Omit it if measurement is incomplete; reports retain the flag rather than treating missing attention as zero verified effort. `finish` stops the exact trial container and retains its filesystem. It does not delete containers or workspaces.

## Quality and results

Execution completion is **not** acceptance. Grade the resulting code against the frozen task rubric, using independent behavior checks and review. Existing/agent-written tests alone are insufficient. No hidden acceptance-test implementation is supplied yet: these first three tasks include concrete criteria and assessment forms, so grading remains an explicit human step. See [the protocol](docs/protocol.md).

```bash
# Fill a COPY of the task's assessment.example.json using observed evidence.
scripts/bench assess RUN_ID /path/to/completed-assessment.json
scripts/bench report
scripts/bench report --csv > results.csv
```

Reports include failures/ungraded runs, execution seconds, session seconds, human seconds by category, intervention episodes, reported help wait, criterion pass counts, critical defects, maintainability, acceptance, and final evidence completeness. Missing final evidence blocks acceptance. Active human time overlaps execution time: do not add the two. No cost/token estimate is fabricated; raw provider histories and available conductor JSONL evidence are retained for later normalization.

## Isolation and evidence

- Only `.runs/RUN_ID/workspace` is writable through a host bind mount. No Docker socket, benchmark grader, root README, host home, or results ledger is exposed.
- Every container has its own provider home. Fresh baselines exclude provider skill/config directories and host hook directories; the same ordinary Fizzy guidance is given to both providers.
- Harness images install the harness from a committed source snapshot. Prepared plans/configuration are hashed into the run manifest before execution.
- Host lifecycle events are serialized and flushed to `.runs/RUN_ID/events.jsonl`; agent exit cannot mint a passing assessment. Conductor's own `.pipeline` ledgers are copied unchanged as supplementary evidence, not rewritten into invented engine events.
- Output inventories, tracked diffs, the full retained workspace (including untracked files and harness worktrees), and terminal logs support later inspection. Provider-native histories are best-effort supplementary evidence, not a required timing source.
- `.runs` is gitignored. Logs can contain task content and operator-entered secrets; keep raw artifacts local. Authentication should happen before recording begins.

Fizzy is licensed under [O'Saasy](fixtures/fizzy/LICENSE.md); additional notices remain in its source tree. This repository retains upstream history and the `upstream` remote for provenance. Publishing a separate GitHub repository is a separate action.
