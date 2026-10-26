# Independent acceptance for the version-2 prompt

Freeze this rubric before launching subjects. Keep checks and assessment
feedback outside the subject checkouts and conversations. Do not repair or
resume subjects after assessment; retain failures as outcomes.

1. Leaf commands export plain typed `CommandSpec<Data>` definitions. Group
   indexes register them. Registration exposes the full specification through
   `withSpec<Result>(visit: <Data>(spec: CommandSpec<Data>) => Result): Result`.
   Runner/presenter mismatches fail typechecking, including heterogeneous
   registry dispatch.
2. Shared execution returns `Promise<string | ReactElement>` without output
   I/O. JSON bypasses presenters and Ink; a missing human presenter falls back
   to JSON. Execution errors propagate. Hooks remain in React components.
3. Commands preserve human tables, schemas, and useful messages; implemented
   commands support JSON, including resource types/describe and success
   messages. Review these paths and their coverage, not just test counts.
4. Run [independent executable checks](harness/acceptance_cli.py) against the
   built binary with a real local HTTP fixture and temporary configuration.
   Under CI=true and CI=false, assert complete deployment-list JSON bytes,
   complete success-message JSON bytes, and human table content. Also check
   that debug diagnostics stay on stderr. A success-message data shape is not
   prescribed; its actual data must serialize canonically with one newline.
5. Test the actual writer using real Node Writable streams: pending write
   completion must keep the returned promise pending; write-callback errors
   must reject without causing an unhandled stream error, and independently
   emitted errors must reject. Do not attach a test-side error-suppression
   listener. Any per-subject adapter may only map exported functions to these
   calls, not modify their behavior. Keep identical cases across subjects.
6. Inspect subject compile-time coverage and executable regression tests.
   Applicable CLI tests, typecheck, lint, and build must pass; capture actual
   command exit status and distinguish subject failures from environment
   restrictions. Integrating typecheck into the build graph is not required.
7. Relevant documentation is updated, command organization preserved, and
   unrelated changes avoided. Note scope, remaining limitations, and meaningful
   differences from the intended architecture independently of token totals.

Report provider-measured first-request and per-request usage, aggregate
input/cache/output/reasoning usage, observed compactions, elapsed time, skill
reads, documentation retrievals, failures, interventions, patches including
untracked files, and validation outcomes. Exact initial component token counts
remain unavailable until the separate counting endpoint is authorized and its
request reconstruction calibrated. Preserve byte/hash evidence in the meantime.
