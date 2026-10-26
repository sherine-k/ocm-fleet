# FM-124 results

[results.json](results.json) is the current consolidated data for the four frozen v2 runs.
Controls retain the original guidance; treatments use lean Nx guidance without packaged Nx skills.
Model: `gpt-6-luna`, max reasoning; work profile: `~/.codex-work`.

| Metric | Control 1 | Control 2 | Treatment 1 | Treatment 2 |
| --- | ---: | ---: | ---: | ---: |
| Initial input tokens | 15,827 | 15,827 | 14,931 | 14,931 |
| Input tokens before first edit | 75,951 | 77,534 | 79,712 | 76,631 |
| Total input + output tokens | 13,936,665 | 9,462,876 | 13,115,838 | 9,282,933 |
| Elapsed seconds | 871.28 | 894.868 | 1066.67 | 872.006 |
| Tool calls | 110 / 6 | 69 / 10 | 109 / 14 | 73 / 10 |
| Shell commands | 78 / 24 | 72 / 22 | 65 / 14 | 110 / 57 |
| Recognized skill reads | 1 / 1 | 1 / 1 | 0 / 0 | 0 / 0 |
| Nonzero shell exits | 10 / 0 | 9 / 1 | 13 / 0 | 8 / 0 |
| Frozen checks failed | 0 / 11 | 0 / 11 | 0 / 11 | 0 / 11 |
| Supplemental login check failed | 1 / 1 | 0 / 1 | 0 / 1 | 1 / 1 |

Activity rows use **overall / before the first edit’s tool call**. Check rows use **failed / total**.
Both recognized skill reads were `nx-workspace`. Nonzero exits include iterative failures and searches.
The login check is a post-hoc static stream-wiring check; browser login was not exercised.
Input includes cached input; output includes reasoning. Accumulated tokens repeatedly count history.
The JSON retains detailed counts, token subsets, source hashes, and paths to logs and code patches.

[Prompt](fleetctl-output-prompt-v2.txt) · [Protocol and metric definitions](protocol-v2.md) ·
[Frozen acceptance](acceptance-v2.md) · [Earlier reports and timelines](archive/)
