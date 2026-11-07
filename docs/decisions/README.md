# Architecture Decision Records (ADRs)

This directory stores records of significant architectural, technology, and design decisions made throughout the lifecycle of the project.

## When to write an ADR
Write an ADR whenever a decision is made that:
* Chooses a core language, framework, database, or major library.
* Changes how components communicate (e.g., REST vs. gRPC, pub/sub vs. direct RPC).
* Adopts a security, authentication, or deployment strategy.
* Overhauls or deprecates a core subsystem.

## Naming Convention
Files are numbered sequentially using four digits followed by a short hyphenated title:
```
0001-<short-title>.md
0002-<short-title>.md
```

## Instructions for Agents
1. Copy [TEMPLATE.md](TEMPLATE.md).
2. Number it sequentially after the latest existing ADR.
3. Fill out the context, alternatives considered, and anticipated consequences.
4. Reference the ADR in [docs/ARCHITECTURE.md](../ARCHITECTURE.md) and [../../AGENTS.md](../../AGENTS.md).
