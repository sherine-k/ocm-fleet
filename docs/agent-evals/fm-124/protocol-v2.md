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
Review files for the completed controls live in [reviews/](reviews/).

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

`capture` launches two model sessions and emits unreviewed checkpoint summaries.
Review their transcripts, then regenerate the primary summary with annotations:

```sh
python3 docs/agent-evals/fm-124/harness/context_usage.py "$rollout" \
  --run "$name" --review "$review_json" --output "$analysis_directory"
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover \
  -s docs/agent-evals/fm-124/harness -p 'test_*.py'
```

Analysis uses only Python's standard library and makes no model/network calls.
It writes `checkpoints.json` plus supporting `context-usage.json` and CSV,
checking unique responses and reconciliation of per-request and final usage.

## Correctness and current state

The frozen [acceptance rubric](acceptance-v2.md) covers the requested architecture,
subject tests/typecheck/lint/build, seven independent built-CLI cases, and four
real-Writable cases. Its older reporting footer is superseded by the two
checkpoints above; acceptance assertions are unchanged. Assessment stays outside
subject conversations. Preserve
failures; do not repair or coach completed subjects. Setup and assessment usage
are excluded from subject totals. Live authentication/backend coverage is absent.

The [fresh controls](controls-v2-2026-10-23.md) completed on October 23, 2026.
Their [two-checkpoint summaries](checkpoints-v2-2026-10-23.json) are derived from
those frozen rollouts; no coding sessions were rerun. Both pass the 11 targeted
independent checks, with an additional login-helper regression found in Control 1
by source review. These are A/A controls, not evidence of a guidance improvement.
The [treatment pair](treatments-v2-2026-10-26.md) completed on October 26 using
the combined lean AGENTS.md and Nx-skill removal, the same task, and the same
acceptance checks. Both passed all 11 independent cases; source review found the
login-helper regression in Treatment 2. Initial snapshots match the frozen lean
startup snapshot after path/envelope and environment-date normalization. Record
such drift rather than attributing it to the treatment.
