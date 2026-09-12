# Version tables, run tags, and review PRs

Use all three for different purposes:

- **README table:** acceptance, elapsed time, human attention and interventions by harness release/task/workflow/configuration.
- **Run tag:** the exact captured implementation plus an annotated, sanitized metrics record. Name: `eval/<release>/<run-id>`.
- **Results PR:** review the public run records and generated README/release pages before merging them into main.

A locked PR is not a frozen code snapshot. GitHub conversation locking restricts comments, not commits to the branch: [GitHub documentation](https://docs.github.com/en/communities/moderating-comments-and-conversations/locking-conversations). Preserve commit SHAs and tags instead; keep the PR available for discussing results.

## Archive a completed run

Only finished runs with successful final evidence capture and an independent assessment qualify. Accepted runs, assessed failures and timeouts can all be archived; do not retain only successes. Incomplete attention is retained and excluded from attention medians. An unfinished/ungraded run cannot acquire a completion tag.

Run these commands in a feature worktree for the results PR:

```bash
# Direct agent result, using the final captured workspace rather than live files:
scripts/bench archive-run RUN_ID --runs-dir /path/to/benchmark-checkout/.runs

# Daemon result: explicitly select its actual implementation worktree inside the capture.
scripts/bench archive-run RUN_ID --runs-dir /path/to/benchmark-checkout/.runs \
  --result-tree .worktrees/FEATURE_SLUG
```

The archive command verifies the final snapshot checksum, reads the recorded upstream fixture commit, and creates normalized baseline/result Git commits without changing your current branch or index. It tags the result and writes `results/runs/RUN_ID.json`. It does not launch an agent, push a ref, or alter the live trial workspace.

The code tree includes source additions, modifications, deletions, modes, and untracked files from the selected final snapshot. Runtime directories, harness process artifacts, provider state, instructions added for the trial, and common secret files such as `.env` and `master.key` are excluded from both sides of the code comparison. Raw terminal logs and provider histories remain local. Review the exported code and public JSON for unexpected sensitive content before publishing.

Tags and public records are write-once through the runner. Repeating `archive-run` refuses an existing tag/record rather than moving it. A correction requires a newly identified run; never overwrite an old result. The local pre-push hook also rejects updates/deletions to `eval/*` tags. Administrators can still bypass local hooks or change refs through other clients; GitHub tag rulesets restricting updates/deletions for `eval/**` are the server-side way to enforce this across clients. No server-side ruleset is configured by this setup.

## Publish and update main's README

After reviewing the snapshot and record:

```bash
scripts/bench publish-run RUN_ID
scripts/bench release-report --release vX.Y.Z
```

`publish-run` checks the tag target and annotation against the reviewed record, then pushes **only that tag** to `jstoup111/ai-conductor-benchmarks`. It never uses `--force`, pushes all tags, or targets Fizzy. The tag makes the otherwise separate code commits accessible on GitHub without merging benchmark feature implementations into the fixture.

`release-report` updates only the generated block in README and writes per-release pages under `reports/`. It includes all archived outcomes and keeps different image/model/prompt/resource configurations in separate rows. Human medians use only attention-complete runs and display measurement coverage. It does not invent results for empty releases.

Commit `results/`, `reports/`, and `README.md` in a results PR to **your fork**; merge that PR to make the table visible on main. Tag publication and results-PR merging are separate explicit operations. This setup does not publish run tags or create fake benchmark results.

## Compare versions or individual runs

```bash
scripts/bench compare-runs OLD_RUN_ID NEW_RUN_ID
```

This prints both metrics records and a GitHub **two-commit diff**, so you compare the actual outputs rather than each branch's changes since a merge base. Both runs must cover the same task; a changed baseline is flagged. The release pages also link each result back to its own baseline. See [GitHub's commit comparison documentation](https://docs.github.com/en/pull-requests/how-tos/commit-changes/comparing-commits).

Comparing code is useful even when a model or policy changed, but then the metric difference is not attributable solely to the harness release. Treat timing deltas as descriptive until task/model/resource/permission conditions are comparable. The three tasks remain a small benchmark, not proof of all Rails capabilities.
