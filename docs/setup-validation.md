# Setup validation

Validated during repository setup on 2026-09-12:

- `make check`: 23 runner tests passed, Python compilation passed, shell syntax passed.
- Shared Docker image built, including Ruby/gems, both coding-agent CLIs, Chromium and GitHub CLI.
- Harness Docker image built from committed harness source `d809d31d2c3c557d7f8e2443dda48a5247bf23e4`; its installer completed inside the image.
- All 1,810 upstream Fizzy tracked files preserve their original content hashes and file modes under `fixtures/fizzy`.
- No benchmark trial directories were created, no agent execution was launched, and no GitHub publication was performed.

Built image IDs (local build evidence; use the IDs recorded in future run manifests):

```text
base:    sha256:15b33fb0932ead2dcdbe1c97e313c4cb9f90c3f5a941ee255d641193bb566696
harness: sha256:5e742e3d5163108c6bc2ef82754c30ffca6544a3736494952eeab1088cf98c62
```

Not exercised during setup: Rails database preparation/runtime startup, the existing Fizzy behavioral suite, real provider authentication, daemon dispatch with accepted plans, real GitHub SHIP, or any feature implementation/assessment. Runner process-boundary tests use mocks. Image-build success establishes dependency installation, not end-to-end trial readiness.

The first later pilot should verify those runtime boundaries before collecting comparison results. Hidden executable acceptance tests are not supplied; the three criterion-based assessment forms support manual independent grading.

Fork configuration: `jstoup111/ai-conductor-benchmarks` was created in the operator account. The basecamp remote was removed; origin and GitHub CLI default target the operator fork. Push-hook tests verify that both HTTPS and SSH Fizzy destinations are rejected. Creating the fork did not publish benchmark code or run any trial.
