# Preparing daemon trials

Plans are built and approved before the measured run. The runner does not author plans, forge approval evidence, bypass harness gates, or treat a bare feature prompt as a daemon-ready package.

For each task/provider, create a package with exactly one accepted plan and its required companion artifacts:

```text
prepared/small-claude/
  .docs/plans/<slug>.md
  .docs/...                 Required accepted stories, decisions, seals/owner records, etc.
  .ai-conductor/config.yml  Provider/model routing, Rails verification, finish behavior
  HARNESS.md                If required by this harness installation
  ARCHITECTURE.md           If required by this harness installation
  AGENTS.md                 Shared project + harness execution guidance
  CLAUDE.md                 Equivalent guidance for Claude
```

Only `.docs`, `.pipeline`, `.ai-conductor`, `.benchmark`, `HARNESS.md`, `ARCHITECTURE.md`, `AGENTS.md`, and `CLAUDE.md` are allowed at the package root; no application code or symlinks. Keep the package free of stale HALTs, completed task state, old shipped records, and results from prior runs. Both instruction files must preserve Fizzy's ordinary project guidance. All package content and the image ID enter the frozen manifest.

The runner commits the package with the baseline on the trial repository's `main`. The daemon discovers committed default-branch plans; it does not build an arbitrary uncommitted prompt. Direct trials use a separate `trial` branch. The harness creates its own feature worktrees.

The installed source was inspected for the invocation:

```text
ai-conductor daemon --concurrency 1 --max-items 1
```

This runs the real daemon in the foreground, which lets the host recorder and timeout own its lifetime. `daemon start` supervises through tmux and is deliberately not used as the measured process because returning/detaching does not represent completion. The daemon can still launch its normal child processes inside the isolated container.

Prepare the package against the exact harness image/version. Ensure the selected provider, model routing, test commands, approval artifacts and finish policy are correct before execution. The runner's structural preflight checks the package shape, not the semantic validity of harness gates; the daemon remains the authority. A gate rejection is recorded and never turned into a false pass.

Normal daemon SHIP uses GitHub publication. Before execution, configure a dedicated trial remote, authenticate GitHub inside the trial container, and publish its frozen main baseline so the daemon can open its normal feature PR. The shared image includes gh for both arms. Use the preparation shell (`scripts/bench configure RUN_ID`) for these operations, which are outside the clock. The repository does not create GitHub remotes or upload credentials during setup. Do not point trial publication at Fizzy upstream or disable correctness gates to manufacture success. Use `prepare --publish` for daemon trials and for their matched direct trials. The runner adds the same publication authorization to their task briefs and refuses to start until GitHub authentication and the frozen remote main baseline are present. Until remote/auth setup is supplied, daemon end-to-end execution is not validated.

`--model` on a harness trial is an experiment label, not a daemon override. The prepared config controls actual routing. Inspect the saved config plus native conductor events to verify what ran. For a same-model experiment, make all relevant provider/step mappings agree; for a normal-workflow experiment, retain normal routing and label it accordingly.

Build the harness image with `scripts/build-harness ~/code/ai-conductor`. It archives committed `HEAD`; it never copies host credentials, installed global skills, or uncommitted changes. Installation happens inside the image's home. Images and prepared artifacts are kept separate from the baseline image and baseline application source.

In the preparation shell, authenticate with `gh auth login`, add your **dedicated empty trial repository** as `origin`, and push the frozen `main` branch with `git push -u origin main`. These commands perform external publication only when you execute them later. Use a distinct trial repository for each run so histories and PR state do not leak across runs. The runner never creates or deletes GitHub repositories automatically.
