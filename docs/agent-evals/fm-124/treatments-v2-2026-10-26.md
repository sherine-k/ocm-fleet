# FM-124: lean Nx guidance comparison, October 26, 2026

The concise Nx guidance and removal of packaged skills are committed as
`53e497b` on `fm-124-agent-effectiveness`, in a separate checkout. Root
AGENTS.md keeps task execution through `npx nx`, resolved-project inspection,
installed CLI help, and pointers to Nx documentation. The seven Nx skills,
Claude/Cursor skill links, skill lockfile, and Nx-only Claude plugin settings
are removed. Nested guides and application code are unchanged by that commit.

Two treatment sessions completed with the exact frozen
[version-2 prompt](fleetctl-output-prompt-v2.txt). Compared with the
[October 23 controls](controls-v2-2026-10-23.md), their initial requests are
896 input tokens smaller (5.7%). Their context before the first edit is
slightly larger on average. This supports a smaller startup request, not a
claim that the change reduces exploration context or total work.

## Two primary checkpoints

| Run | Initial input tokens | Input before first edit | First-edit request | Skill bodies read |
| --- | ---: | ---: | ---: | --- |
| Control 1 | 15,827 | 75,951 | 7 | nx-workspace once |
| Control 2 | 15,827 | 77,534 | 11 | nx-workspace once |
| Treatment 1 | 14,931 | 79,712 | 15 | None |
| Treatment 2 | 14,931 | 76,631 | 11 | None |

The first-edit boundaries were checked against all preceding tool calls,
including possible shell edits. Both treatments first edited through
`apply_patch`. Counts are input to the request issuing that edit; the generated
patch is output and is excluded. The before-edit cohort means are 76,742.5
and 78,171.5 tokens, a treatment increase of 1,429 (1.9%). Initial-to-edit
growth includes source, assistant history, framing, and other tool results.
It is not isolated guidance cost.

Confirmed guidance/documentation reads consumed by the edit request:

- Control 1: Nx skill, CLI guide, UI guide, CLI README, feature-inventory excerpt.
- Control 2: Nx skill, CLI guide, CLI README, feature-inventory and Ink README excerpts.
- Treatment 1: CLI guide, CLI README, and two feature-inventory excerpt retrievals.
- Treatment 2: UI guide, CLI guide, and CLI README.

The UI guide is 10,249 bytes. Its retrieval varies within both cohorts; removing
Nx instructions did not eliminate that independent context load. Neither
treatment read a skill body during its full session. Complete reads and excerpts
are distinguished in the small [review files](reviews/); call IDs link them to
returned text. Filename listings and search-only matches are excluded.

## Supporting results

| Run | Total input + output tokens | Elapsed | Model requests | Final CLI tests |
| --- | ---: | ---: | ---: | ---: |
| Control 1 | 13,936,665 | 14m 31s | 111 | 36 passed |
| Control 2 | 9,462,876 | 14m 55s | 70 | 35 passed |
| Treatment 1 | 13,115,838 | 17m 47s | 110 | 36 passed |
| Treatment 2 | 9,282,933 | 14m 32s | 74 | 35 passed |

Treatment accumulated input/output is 4.3% lower across the pair; average
elapsed time is 9.8% higher. Input minus cached input is only 0.8% lower
(403,365 versus 400,177 across the pairs). These are not dollar costs: total
input repeatedly counts history, including cached input. Reasoning output is
already part of output. The larger differences between same-guidance replicates
limit interpretation of these small cohort differences. There were no observed
compactions. Setup, parent analysis, and assessment are excluded from run usage.

Both treatments passed their final CLI typecheck, lint, build, and tests. Both
also passed all seven frozen independent executable cases and all four real
Writable cases. Assessment adapters only re-export the actual writer. Source
patch hashes were unchanged by assessment and both patches pass
`git apply --check` against the historical baseline. Per-request usage sums
reconcile with final rollout totals and CLI completion usage.

Both preserve the prescribed typed leaf specs, generic `withSpec` registration,
and shared execution returning text or a React element without output I/O.
Treatment 1 uses `renderToString`; Treatment 2 uses Ink's render lifecycle.
Their layout and validation choices differ, as they did among the controls.

Additional findings are retained as outcomes:

- Treatment 2 moves `AUTH_URL` to stderr but leaves the browser-login helper
  reading `child.stdout`, reproducing the Control 1 integration regression.
  Treatment 1 updates the helper to stderr and its four support tests pass.
  These findings come from source review, not live browser authentication.
- Treatment 1 additionally ran the full E2E CLI suite: 164 tests passed and
  three HTTPS fixture tests failed with `listen EPERM` on `127.0.0.1` in its
  sandbox. The later targeted support suite passed. Those failures and the
  extra validation/review work remain in its elapsed time and token totals.

The 11 independent cases are targeted, not exhaustive. No live authentication,
gRPC reflection, or management backend was exercised. No subject was resumed,
repaired, coached, or shown assessment results.

## Comparison integrity and artifacts

Both cohorts use `gpt-6-luna`, `max` reasoning, Codex CLI `0.164.0`,
`CODEX_HOME=~/.codex-work`, and independent repositories exported from
`775b87ed75af7dc1977240f6a220183504cd055d`, before PR #4. Prompt SHA-256:
`a0f7654c962887413f59c4567a5fcc9e16bf57c92833458196f202fd265d9fd6`.
Dependencies were copied independently with package manifests, lockfile, and
relative workspace links checked. Profile guidance and global skill bodies
match the controls. Application source starts unchanged; only the agreed Nx
section and installations differ. Subjects do not have later repository refs.

The two new startup snapshots match each other after the existing path/envelope
normalization. They also match the frozen lean startup snapshot after changing
only the environment date from October 23 to October 26. Raw checkout paths and
dates differ between cohorts, so the 896-token figure is an observed whole-request
difference, not an exact isolated token count for the guidance files. Tool
schemas and remaining instructions match. The acceptance rubric and both
independent check files are byte-identical to the frozen control versions.
Concurrent execution and shared provider caching are further limitations.

The [machine-readable report](treatments-v2-2026-10-26.json) contains reconciled
usage, checkpoint/read evidence, session IDs, validation, source findings, and
cohort calculations. The [184-request timeline](context-growth-treatment-v2-2026-10-26.csv)
is supporting evidence. The [protocol](protocol-v2.md) documents preparation,
capture, and offline review; it has no separate token-count endpoint or
four-way startup preparation. Fourteen harness unit tests passed after adding
treatment preparation, including preserving nested guides/unrelated skills and
refusing to remove unrelated Claude settings.

Local raw bundle: `/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl`.
It retains the archive, frozen prompt/checks/harness, manifests and initial
snapshots, independent subject checkouts, full events/rollouts/stderr, final
answers, patches including new files, reviewed checkpoints, and directly
captured assessment logs. Selected results can be opened here:

| Result | Treatment 1 | Treatment 2 |
| --- | --- | --- |
| Full patch | [changes.patch](/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl/artifacts/treatment-1/changes.patch) | [changes.patch](/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl/artifacts/treatment-2/changes.patch) |
| Execution | [execution.ts](/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl/treatment-1/client/cli/src/execution.ts) | [execute.ts](/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl/treatment-2/client/cli/src/commands/execute.ts) |
| Writer | [app.tsx](/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl/treatment-1/client/cli/src/app.tsx) | [output.ts](/private/tmp/ocm-fleet-fm124-treatment-v2.0rz45_hl/treatment-2/client/cli/src/output.ts) |
