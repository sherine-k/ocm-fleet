# Early context growth in the duplicate controls

The frozen rollout logs contain usage for every model response. We can recover
the input size of each individual request without rerunning the experiment.
These measurements are much more relevant to early context growth than the
accumulated input totals across the whole coding session.

## Semantic checkpoints

| Checkpoint | Control 1 input tokens | Control 2 input tokens |
| --- | ---: | ---: |
| Initial request, before tool results | 15,685 | 15,685 |
| First request including the Nx skill read | 17,876 | 17,961 |
| Request issuing the first file edit | 59,880 | 59,639 |

The first edit was issued by request 9 in Control 1 and request 8 in Control 2.
It includes test edits; it is not a claim that production implementation began
at that point. The initial inputs include automatically loaded AGENTS.md
guidance, skill descriptions, tool schemas, the task prompt, and other host
instructions. Skill bodies are retrieved later.

Control 2 also read the web UI guidance, `docs/ui/AGENTS.md`, before its CLI
instructions. That 10,249-byte file was first included in request 3, whose
input was 22,478 tokens. Control 1 did not read it. For this CLI task that
appears to be an unnecessary instruction retrieval, and is an example of the
behavioral cost to inspect alongside the fixed initial prompt size.

The input grew by 2,191 / 2,276 tokens between the initial request and the
request following the skill read. These deltas include prior assistant
history and tool-result framing as well as the skill text. They are not exact
token counts of the skill file alone. Subsequent startup reads were batched
with other file and metadata retrievals, limiting isolated attribution.

## Captured data

- [Per-request timeline](context-growth-2026-10-23.csv): all 98 / 67 requests,
  input size, growth and deltas, cache counts, generated output, elapsed time
  until usage reporting, and checkpoint annotations.
- [Checkpoint records](context-checkpoints-2026-10-23.json): machine-readable
  observations selected by the same semantic rules in each run.
- [Source component sizes](context-components-2026-10-23.json): source byte
  counts, distinct from provider-reported token usage.

Each CSV row comes from one `token_usage_record`, using its per-response
`usage`, rather than the cumulative usage. Response identifiers were unique,
and summing per-response input, cache, output, and reasoning counts reproduced
the previously recorded final totals. There were no context compactions.
Timestamps refer to response completion / usage reporting, not request start.
Cached input remains included in request input size.

The analyzer and raw rollouts remain in the local bundle recorded in the
[original report](controls-2026-10-23.md). No coding session was resumed or
given assessment feedback, and no new experimental model calls were made.

## Method for the treatment comparison

The [version-2 protocol](protocol-v2.md) specifies the startup factors,
retrieval ledger, counting calibration gate, and reusable offline analyzer.
It also records which harness changes are complete and which remain pending.

Use two complementary measurements:

1. **Fixed initial contribution.** Hold the rendered task prompt, model, tools,
   settings, and environment constant. Compare the initial prompt with only
   AGENTS.md changed, with only the skill catalogue changed, and with both
   changed. Count the complete requests; do not infer token counts from file
   lengths. The [input token counting API](https://developers.openai.com/api/docs/guides/token-counting)
   supports counting request structure and tool schemas without generating a
   model answer. Before using it for this Codex experiment, verify that the
   reconstructed request reproduces the observed 15,685-token baseline for
   the same model. Codex's debug snapshot is an internal representation and
   should not be assumed to be an API-ready request. These counterfactual
   token counts have not yet been performed.
2. **Retrieval and behavior.** Preserve the real run's per-request curve and
   annotate each instruction, skill, and documentation retrieval. Compare the
   first request, early request numbers, and the request issuing the first
   edit. This records context added through exploration and guidance-following
   behavior. When a treatment omits a retrieval, record its absence rather
   than forcing an equivalent read into the run.

Elapsed time is useful as a secondary axis, but different reasoning latency,
batching, approvals, and tool speed can place unrelated work at the same time.
Even semantic checkpoints do not isolate exact per-file costs once model
behavior diverges; the fixed initial comparison supplies that distinction.

The observed early growth is almost identical by the first edit despite the
large difference in eventual accumulated usage. Preserve both measurements
when interpreting the treatment, together with correctness and task progress.
