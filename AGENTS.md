# Rules for Agents

This is the monorepo for OCM Fleet, an experimental Open Cluster Management variant using a resource manager architecture. It contains the resource manager server, CLI, proto definitions, React web UI, addons, and proof-of-concept experiments. Please follow these rules very closely. It is very important.

## Nx

- Run workspace tasks (build, test, lint, proto, image, infrastructure) through the repository's Nx CLI: `npx nx`. Deployment scripts provide platform-specific checks.
- When resolved project or target configuration is needed, use `npx nx show project <name> --json`.
- For unfamiliar commands or options, check the installed CLI's `--help`.
- For additional guidance, read the relevant version of the [Nx documentation](https://nx.dev/docs). Use the [topic index](https://nx.dev/llms.txt) to find the page needed for the task.

## Understanding the domain

The architecture documentation lives in docs/design/ and is the primary source of truth for domain concepts, system design, and open questions.

Use **OCM Fleet** for the project, **the OCM Fleet architecture** for its
particular design, **a resource manager architecture** for the locally defined
architectural approach, and **resource manager server** (or **resource manager**
once scoped) for the API, authorization, persistence, and orchestration
component. A platform instance includes enabled integrations and supporting
services; participation in a deployment does not establish addon membership in
the project. Use **fleetlet instances** for multiple deployments of the
canonical fleetlet and **management plane** for the APIs, services, and user
interfaces through which a platform instance represents, observes, configures,
and governs resources and coordinates their lifecycle. It includes the resource
manager server and addon-supplied management capabilities. See
docs/design/glossary.md for the architecture terminology guide.

- Start with docs/design/architecture.md -- it gives the system's core mental model, names the major subsystems, and contains a reading guide that routes to the detailed sub-documents in docs/design/architecture/:
 - core_model.md -- core vocabulary, strategy axes, fulfillment kernel primitive, target model, delivery contract, single-pod invariant
 - target_delivery_contract.md -- detailed target delivery protocol, reliability guarantees, generation ordering, journaling, observation reporting
 - orchestration.md -- fulfillment execution, re-evaluation, rollout
  - fleetlet_and_transport.md -- fleetlet instances, channels, proxying, routing, data paths
  - tenancy_and_permissions.md -- provider/tenant/workspace model, generic permission boundary
  - addon_integration.md -- capability registration, addon strategy contracts, managed-resource bridging, UI/API extensions
  - resource_identity_and_api.md -- two-layer API model, resource identity, platform resources, extension API packages, HTTP transcoding
  - resource_indexing.md -- fleet-wide indexing and search
  - platform_hierarchy.md -- recursive platforms, federation, provisioning, bootstrap, pivot
  - open_questions.md -- unresolved design areas
- For authentication and delivery authorization, see docs/design/authentication.md and poc/attestation/hybrid/README.md
- For managed resources, see docs/design/managed_resources.md

## Designing and defining APIs

- For gRPC / proto generation and linting, see docs/buf.md
- For API design conventions (AIP-aligned), see docs/api-design.md

## Cross-cutting concerns (very important)

- This is a prototype. Don't be afraid to break contracts if it would produce a more ideal design for the task at hand. We'd rather learn and experiment with a potentially better way. There's little value to backwards compatibility for compatibility's sake.
- _Please don't casually remove comments unless they are truly no longer relevant_ (e.g. a TODO that is now implemented or obsolete, or out of date explanations). Prefer updates to removal, unless behavior is obvious from the code or signature.
- Keep design documentation up to date, but focused on the design and vision. _Do not overfit design documentation to the code, specific API, or current implementation_. It is a guide for how we intend the implementation to evolve, more than it is a description of its current state. We should update them when, during the course of implementation and planning, we realize that the design and vision itself should change, or has become out of alignment with what we are building in non-temporary ways. References to code or API are far from forbidden, but just used judiciously, to tie the desired design to the prototype.
- Prefer modern stdlib abstractions and utilities where relevant (especially around crypto or low level encoding / decoding)
- Follow test-driven development. When at all possible, write failing tests **first**, then write the code to make the test pass.
- Please always run go fmt ./... after you're done with any Go code changes

## Resource manager server

Read the relevant docs below **before** writing or modifying code in this module. They contain design rules that are easy to violate without context.

For how to...

- decide what logic to put where (layering, service boundaries, method signatures), see server/docs/internal-architecture.md
- implement instrumentation (observability: tracing, logging, metrics), see server/docs/observer-pattern.md
- decide what package to use, see server/docs/package-structure.md
- write tests, see server/docs/testing.md
- write durable workflows and integrate with durable computing libraries, see server/docs/durable-workflows.md
- write or modify constructors, see server/docs/constructors.md
- write domain objects (aggregates, entities, values, where invariants belong, snapshot persistence), see server/docs/domain.md

When running tests, iterate with `go test ./...` (the default suite excludes Docker-heavy integration tests). Tests gated behind `//go:build integration` require `-tags integration` and a container runtime; run them explicitly when working on that code (e.g. `go test -tags integration ./internal/addon/kind/`) and/or to verify we haven't broken anything before completing.

## OCM Fleet console

This is the complete frontend web app for ocm-fleet. See docs/ui/AGENTS.md for agent instructions.
