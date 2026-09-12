# Execution and grading protocol

## Freeze before running

Freeze fixture hash, task prompt/criteria, image IDs, resource limits, model/effort settings, permission policy, execution cap, operator availability policy, prepared harness artifacts and the success endpoint. Use `schedule` for a seeded randomized order (three tasks × four configurations × two repeats = 24 runs). No run happens merely by producing a schedule.

Treat the labels small/medium/large as hypotheses to calibrate in a pilot. Once main collection starts, do not amend prompts or selectively rerun poor outcomes. New tasks/versions form a separate experiment. Report all attempted trials, including setup failures, task failures, timeouts, and incomplete attention data. Setup failures are not execution failures and have no execution duration.

Plans are a treatment-specific preparation input. Their human authoring cost is excluded by design; direct trials receive the same observable feature requirements, not the harness's solution plan. This experiment measures execution of prepared work, not an isolated causal effect of the engine given identical planning artifacts.

## Human attention

The runner starts the execution clock automatically. Attention begins off: explicitly start it before reading/thinking/answering. Looking at a dashboard and diagnosing a stall count even if you never type. Do not infer effort from keystroke count or wall-clock waiting. Switch off when you leave. Use the same policy for every arm; intervene on explicit requests or observed failures, not to coach a favorite tool toward your preferred implementation.

An intervention episode is a non-monitoring attention interval. It is not a message count. The shell wrapper captures rescue intervals automatically. Help-request/resolution events are manually timestamped unless an observer is integrated later; `help_wait_seconds` includes the period until you mark the request resolved, so it is not a precise notification-to-first-response measurement. Missing event coverage must not be described as automatic complete request capture.

Normal permission prompts remain enabled; their active handling time is approval attention. Authentication occurs in preparation. The timer cannot recover forgotten attention intervals, so only attest `attention_complete` when accurate. Do not use runs marked incomplete to claim a human-effort win.

Execution seconds include idle periods between sessions and waiting for the operator. Session seconds are durations of wrapped processes, not CPU time or active model time. Human seconds overlap both. The execution cap applies across resumed sessions; a host-owned timer stops the exact container during active execution. After a wrapper crash, use recover and mark the run appropriately. A hard host failure cannot guarantee the final event was written; incomplete runs stay visible.

## Quality

At a declared candidate, preserve the output with `mark candidate`. For the initial experiment, finish execution at final candidate submission and grade independently afterward. This gives time-to-submission plus acceptance, not time-to-acceptance. Do not include benchmark grading in the execution clock. If studying repair after review, define a separate bounded repair phase before collection; the current runner does not automatically exclude grading pauses in a multi-round repair protocol.

Give the reviewer the task brief, rubric, and implementation snapshot. Conceal provider/profile labels and generated process documents where practical. Source style may reveal an arm; call this partial blinding rather than promising anonymity. Prefer a reviewer other than the execution operator. Have the reviewer run independent checks, including negative paths, and inspect all application changes, including untracked files and the harness feature worktree.

Each task's assessment form contains criterion booleans, regression result, critical defect count, evidence references and a 1–5 maintainability score:

- 1: substantial redesign/repair needed to maintain the feature.
- 2: significant unnecessary complexity or poor fit with existing code.
- 3: understandable, acceptable fit; ordinary cleanup remains.
- 4: clear implementation following established patterns with focused tests.
- 5: particularly clear and economical implementation; no meaningful maintainability concerns found.

A run is accepted only if all criteria pass, regression checks pass, there are zero critical defects, execution completed within its cap, and final evidence capture completed. Maintainability is reported separately and cannot compensate for broken behavior. Criteria should be supported by external tests/manual checks, not the agent's own claim of success. Assessments are recorded once and require reviewer and evidence fields. No live external-service tests are required.

No hidden executable grading suite is included yet. The prepared prompts/criteria are enough to run and manually assess the pilot, but automated functional grading needs separately authored tests validated on a known-good reference implementation before results can be called automatically graded.

## Reporting

Report acceptance by task/configuration, then paired elapsed and human time differences for comparable outcomes. Show failures and timeouts next to timing; averaging only successful runs hides reliability costs. Use medians and individual points for a pilot. With only three distinct tasks, repeated runs estimate run variation on those tasks, not general performance across Rails projects. Do not collapse quality/time/attention into one unexplained score.

The ledger uses host monotonic timestamps for durations and UTC epoch timestamps for correlation. It is authoritative for benchmark lifecycle and human attention. Provider transcript data and unchanged conductor event ledgers are supplementary. Per-provider token/cost normalization and automatic native-hook request classification are deliberately not claimed by this setup.
