# FM-124 comparison protocol, version 2

Use the identical [task prompt](fleetctl-output-prompt-v2.txt), historical base
`775b87ed75af7dc1977240f6a220183504cd055d`, work profile
`CODEX_HOME=~/.codex-work`, and `gpt-6-luna` with `max` reasoning. The prompt's
SHA-256 is `a0f7654c962887413f59c4567a5fcc9e16bf57c92833458196f202fd265d9fd6`.
The task reconstructs PR #4's CLI output refactor with three prescribed design
requirements. Do not prescribe discovery commands: retrieval is an outcome.

## Two checkpoints

The primary report is `checkpoints.json`, produced offline from provider usage:

1. **Initial request:** input tokens before tools run. This includes stock
   guidance, available skill descriptions, tool schemas, environment, and task.
   Compare controls and treatments to measure the combined startup difference.
2. **Before first edit:** input tokens for the request issuing the first edit,
   including a test edit. Also report growth since checkpoint 1 and the confirmed
   skills, agent guides, and documentation read by then. This captures how much
   context the agent gathered before implementing.

Check the raw transcript for the first edit, including shell-based edits.
Without review, the analyzer labels its first `apply_patch` mention only as an
**unreviewed candidate**. Review actual returned text before listing a read;
filenames, failed commands, or a discovery listing are not reads. Mark partial
or truncated reads as excerpts. The checkpoint excludes the first edit's output.

Review annotations are deliberately small:

```json
{
  "first_edit_request": 7,
  "guidance_reads": [
    {"source": ".agents/skills/nx-workspace/SKILL.md", "call_id": "call_..."},
    {"source": "docs/example.md", "call_id": "call_...", "scope": "excerpt"}
  ]
}
```

Use `first_edit_request: null` when review establishes that no edit occurred.
An empty read list means none confirmed; without review the list stays null.
The analyzer derives inclusion request numbers from the tool-result ledger and
excludes reads not consumed by the first-edit request. Keep call IDs as evidence.
Review files for the completed controls live in [reviews/](reviews).

Initial input is the whole request, not a separate count for each guidance
component. Growth includes source, assistant history, and tool results as well
as guidance. Keep aggregate tokens, elapsed time, and correctness as supporting
results. Cached input is part of input; reasoning is part of output. Accumulated
input repeatedly counts context and is not peak context size or a dollar cost.

There are no separate token-counting API calls, per-file token estimates, or
four-way startup captures in the current protocol. Previously captured startup
variants remain historical artifacts; they are not required for further runs.
Raw per-request telemetry remains available for investigating a result.

## Run and analyze

The [runner](harness/control_pair.py) prepares two original-guidance controls or
two lean-guidance treatments in
isolated repositories with independently copied dependencies and checked
relative workspace links. It captures initial input snapshots, guidance hashes,
full rollouts/events, elapsed time, final answers, and patches including new
files. It refuses to overwrite prepared bundles or completed runs and checks
normalized within-pair snapshot equality before capture.

```sh
python3 docs/agent-evals/fm-124/harness/control_pair.py prepare \
  --bundle "$bundle" --source "$repository_with_matching_dependencies" \
  --prompt docs/agent-evals/fm-124/fleetctl-output-prompt-v2.txt
python3 docs/agent-evals/fm-124/harness/control_pair.py capture --bundle "$bundle"
```

Add `--lean-agents AGENTS.md` to `prepare` for the treatment pair. Only the Nx
section is transplanted onto the historical root guide; the seven Nx skills,
their Claude/Cursor links, lockfile, and Nx-only Claude plugin settings are
removed. Nested guides and application source stay at the historical baseline.

For broader guidance revisions, use `--guidance-from "$repository"` instead.
This prepares `revised-1` and `revised-2`, overlays all tracked `AGENTS.md` files
(including additions/removals), and retains the Nx skill/plugin removal. It
records the source commit and exact guide hashes. Application code, project
metadata, build targets, and dependencies remain historical; generator changes
are not copied. Profile guidance/global skills are unchanged unless separately
recorded as an experimental factor. Preserve the earlier cohorts in results.

`capture` launches two model sessions and emits unreviewed checkpoint summaries
and mechanical `tool-statistics.json` activity counts.
Review their transcripts, then regenerate the primary summary with annotations:

```sh
python3 docs/agent-evals/fm-124/harness/context_usage.py "$rollout" \
  --run "$name" --review "$review_json" --output "$analysis_directory"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s docs/agent-evals/fm-124/harness -p 'test_*.py'
```

Log analysis uses only Python's standard library and makes no model/network calls.
It writes `checkpoints.json` plus supporting `context-usage.json` and CSV,
checking unique responses and reconciliation of per-request and final usage.

## Mechanical activity and failure counts

Keep the two context checkpoints as the primary measurement. As supporting
metrics, [tool_statistics.py](harness/tool_statistics.py) counts model tool calls,
actual shell executions, recognized skill reads, and nonzero command exits,
both overall and before the first recorded edit's enclosing tool call. It also
preserves tool-name/exit-code breakdowns and event IDs. No review annotations or
model classification feed these counts. An absent/ambiguous edit boundary stays
null; arbitrary shell writes are not detected. Skill reads are observable
retrievals, not proof of semantic use. Nonzero exits include iterative failures
and searches without matches, so they are not remaining-defect counts.

One compound shell script counts once; unlogged child processes and polling
are excluded. Skill reads require a successful nonempty command with a
logger-classified read path ending in `SKILL.md`; indirect/unclassified reads
can be missed. Read/search/list categories come from the logger, can overlap,
and retain `unknown`. The activity output also includes both token checkpoints
and usage totals, so a current run's metrics can be read together.

```sh
python3 docs/agent-evals/fm-124/harness/tool_statistics.py "$rollout" \
  --run "$name" --assessment "$assessment_directory" --output "$statistics_json"
node docs/agent-evals/fm-124/harness/login_stream_contract.mjs "$subject"
SUBJECT="$checkout_with_dependencies" node --test \
  docs/agent-evals/fm-124/harness/test_login_stream_contract.mjs
```

The optional assessment input mechanically parses explicit unittest/Vitest
totals and preserves job exits. Untested behavior has no measured pass/fail
result. A supplemental static login-stream contract check was added after the
four v2 runs; keep that result separate from frozen acceptance. See the
[current table](README.md) and consolidated [data/definitions](results.json).
The static check uses the installed TypeScript parser to compare the directly
declared AUTH_URL writer stream with the helper's readline input. It prints JSON
and exits 0 for passed, 1 for failed, or 2 for unsupported/ambiguous wiring.
It reads subject files without modifying them and does not exercise browser login.

## Correctness and current state

The frozen [acceptance rubric](acceptance-v2.md) covers the requested architecture,
subject tests/typecheck/lint/build, seven independent built-CLI cases, and four
real-Writable cases. Its older reporting footer is superseded by the two
checkpoints above; acceptance assertions are unchanged. Assessment stays outside
subject conversations. Preserve
failures; do not repair or coach completed subjects. Setup and assessment usage
are excluded from subject totals. Live authentication/backend coverage is absent.

The six completed v2 runs are consolidated in [results.json](results.json).
Keep one current data file and [short table](README.md); earlier writeups,
checkpoint snapshots, and detailed request timelines live under [archive/](archive/).
Controls completed October 23; lean and revised treatments completed October 26,
2026. Revised treatments use all current guides at `7b8aeb9`, including newer
nested guides. A change to the advertised subagent model list is recorded as
tool-description drift. Checkout paths and environment dates also differ between
cohorts. Two runs per cohort do not establish a reliable total-cost or speed effect.
