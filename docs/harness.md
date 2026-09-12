# Preparing daemon trials

Plans are built and approved before measured execution. The runner does not author plans, forge approvals, or bypass harness gates.

For each task/provider/repetition, prepare a package with exactly one accepted plan and its required companion artifacts:

```text
prepared/small-claude/
  .docs/plans/<unique-trial-slug>.md
  .docs/...                 Required accepted stories, decisions, ownership/seal records
  .ai-conductor/config.yml  Provider/model routing, Rails verification, finish behavior
  HARNESS.md                If required by this harness installation
  ARCHITECTURE.md           If required by this harness installation
  AGENTS.md                 Shared Fizzy + harness execution guidance
  CLAUDE.md                 Equivalent guidance for Claude
```

Use a distinct accepted feature slug per trial so the daemon's generated feature branch and retained PR cannot collide with an earlier run. Keep application behavior and acceptance criteria identical across matched plans. Do not simply rename sealed artifacts without updating their references and approvals.

Allowed package roots: `.docs`, `.pipeline`, `.ai-conductor`, `.benchmark`, `HARNESS.md`, `ARCHITECTURE.md`, `AGENTS.md`, `CLAUDE.md`. No application code or symlinks. Exclude old HALTs, completed task state and prior shipped records. Instruction files must preserve Fizzy's ordinary guidance. The runner hashes the package before execution; the daemon remains the authority on semantic gate validity.

## One fork, isolated branches

The only publication repository is **jstoup111/ai-conductor-benchmarks**. The runner sets:

- `origin` to `https://github.com/jstoup111/ai-conductor-benchmarks.git`;
- an isolated local/remote base branch `benchmarks/<release>/<run>/base`;
- local `origin/HEAD` to that trial base branch, which the inspected daemon uses to discover its base;
- `GH_REPO=jstoup111/ai-conductor-benchmarks`, preventing GitHub CLI's fork-parent inference from choosing Fizzy;
- a read-only mounted Git pre-push hook that permits only that fork.

No trial overwrites main or requires a separate GitHub repository. No `upstream` remote is installed. Prepared plans are committed on the isolated trial base; the daemon creates its usual feature worktrees. Direct agents receive an isolated `benchmarks/<release>/<run>/implementation` branch.

Normal daemon SHIP includes publication, so prepare daemon runs with `--publish`. Use the same flag for matched direct runs; it adds identical authorization to their prompts. Before execution, use `scripts/bench configure RUN_ID` to authenticate with `gh auth login` and execute the printed `git push -u origin <trial-base-branch>` command. This future preparation push publishes only to your fork. The runner checks fetch/push destinations, authentication, and the remote base commit before starting the execution clock. It never force-pushes or silently repairs a mismatched baseline.

## Daemon and release configuration

The configured command is:

```text
ai-conductor daemon --concurrency 1 --max-items 1
```

This is the real daemon running in the foreground, allowing the host recorder and timeout to own its lifetime. It is not the inline pipeline. `daemon start` is a tmux management command whose return/detachment does not represent execution completion.

Prepare plans against the exact harness release image. `scripts/build-harness /path/to/harness-release-checkout` archives committed HEAD, excluding host configuration and uncommitted changes. Its image label preserves the harness commit; manifests and reports record it alongside `--release`.

The daemon's prepared configuration controls actual provider/model routing. The runner's `--model` and `--effort` arguments label the intended setup; they override direct profiles but do not override the daemon. Verify actual routing through the saved configuration and native conductor events. Match routing for an engine-overhead comparison, or preserve normal routing and label the experiment as a complete workflow comparison.

No real daemon trial, GitHub trial push, or model execution has been performed during repository setup. Plan approval compatibility, dispatch, and SHIP remain to be validated in a later pilot.
