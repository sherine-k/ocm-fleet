Read the relevant docs below **before** writing or modifying code in this module. They contain design rules that are easy to violate without context. Paths are relative to this folder (server/).

For how to...

- decide what logic to put where (layering, service boundaries, method signatures), see docs/internal-architecture.md
- implement instrumentation (observability: tracing, logging, metrics), see docs/observer-pattern.md
- decide what package to use, see docs/package-structure.md
- write tests, see docs/testing.md
- write durable workflows and integrate with durable computing libraries, see docs/durable-workflows.md
- write or modify constructors, see docs/constructors.md
- write domain objects (aggregates, entities, values, where invariants belong, snapshot persistence), see docs/domain.md

When running tests, iterate with `go test ./...` (the default suite excludes Docker-heavy integration tests). Tests gated behind `//go:build integration` require `-tags integration` and a container runtime; run them explicitly when working on that code (e.g. `go test -tags integration ./internal/addon/kind/`) and/or to verify we haven't broken anything before completing.
