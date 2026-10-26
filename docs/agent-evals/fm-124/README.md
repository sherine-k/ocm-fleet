# FM-124 results

[results.json](results.json) is the current consolidated data for six frozen v2 runs.
Controls: original guidance. Treatments: lean Nx guidance. Revised: complete current agent guides at `7b8aeb9`.
Model: `gpt-6-luna`, max reasoning; work profile: `~/.codex-work`.

| Metric | Control 1 | Control 2 | Treatment 1 | Treatment 2 | Revised 1 | Revised 2 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Initial input tokens | 15,827 | 15,827 | 14,931 | 14,931 | 14,836 | 14,836 |
| Input tokens before first edit | 75,951 | 77,534 | 79,712 | 76,631 | 71,877 | 79,787 |
| Total input + output tokens | 13,936,665 | 9,462,876 | 13,115,838 | 9,282,933 | 15,875,139 | 12,264,679 |
| Elapsed seconds | 871.28 | 894.868 | 1066.67 | 872.006 | 992.577 | 860.515 |
| Tool calls | 110 / 6 | 69 / 10 | 109 / 14 | 73 / 10 | 135 / 9 | 95 / 16 |
| Shell commands | 78 / 24 | 72 / 22 | 65 / 14 | 110 / 57 | 80 / 18 | 92 / 24 |
| Recognized skill reads | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 | 0 / 0 | 0 / 0 |
| Nonzero shell exits | 10 / 0 | 9 / 1 | 13 / 0 | 8 / 0 | 11 / 0 | 11 / 2 |
| Frozen checks failed | 0 / 11 | 0 / 11 | 0 / 11 | 0 / 11 | 0 / 11 | 0 / 11 |
| Supplemental login check | failed | passed | passed | failed | passed | unresolved |

Activity rows use **overall / before the first edit’s tool call**. Frozen checks use **failed / total**.
Nonzero exits include iterative failures/searches. Login is a supplemental static check; browser login was not exercised.
`unresolved` means the static check cannot follow an indirect writer. Additional E2E commands and reported test counts are retained in JSON.
Input includes cached input; output includes reasoning. Accumulated tokens repeatedly count history.
Revised runs include newer nested guides; generator/build metadata stays historical. The advertised subagent model list also changed; the exact diff is recorded in JSON.
The JSON retains detailed counts, token subsets, source hashes, and log/patch paths. Two runs per cohort are exploratory.

[Prompt](fleetctl-output-prompt-v2.txt) · [Protocol](protocol-v2.md) · [Frozen acceptance](acceptance-v2.md) · [Archive](archive/)
