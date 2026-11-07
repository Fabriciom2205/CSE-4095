# Agent Operating Guidelines & Workspace Index

Welcome! If you are an AI coding assistant (or human developer) working on this repository, **read this file before beginning work.**

This repository is shared across multiple contributors and agentic workflows. To ensure seamless collaboration and uninterrupted context between sessions, follow the conventions outlined below.

---

## Project Overview
> *Note: Project specifics, scope, and technical specifications are currently being finalized. Update this section once confirmed.*

* **Status:** Inception / Planning Phase
* **System Architecture:** See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) *(Template in place)*

---

## Agent Workflow & Handoff Protocol

Every agent working on this repository must adhere to the following 3-step lifecycle:

```
[Start Session] ──> Check AGENTS.md & Latest Notes
       │
[Execute Work]  ──> Keep changes scoped & tested
       │
[End Session]   ──> Create a Note in docs/notes/ & Update AGENTS.md
```

### 1. At the Start of Every Session
1. Read the **Active Tasks / Next Steps** section below.
2. Review the most recent note in [`docs/notes/`](docs/notes/) to understand recent changes, decisions, and known issues.
3. Verify git status and ensure you are working on the intended branch.

### 2. When Proposing Major Architectural Changes
* For significant architectural, framework, or tooling choices, document the proposal as an **Architecture Decision Record (ADR)** in [`docs/decisions/`](docs/decisions/) following the [ADR Template](docs/decisions/TEMPLATE.md).

### 3. At the End of Every Session (Mandatory Handoff)
Before closing your turn or concluding a task:
1. **Create a worklog note** in `docs/notes/YYYY-MM-DD-<short-topic>.md` using the [Worklog Template](docs/notes/TEMPLATE.md).
2. **Link the new note** in the [Worklogs & Session History](#worklogs--session-history) table below.
3. **Update the [Active Tasks & Backlog](#active-tasks--backlog)** section below so the next agent knows what to pick up immediately.

---

## Active Tasks & Backlog

Use this checklist for handoffs between agents. Keep it up to date.

* [ ] Finalize project scope and high-level architecture in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
* [ ] Define tech stack, dependencies, and environment setup
* [ ] Initialize repository structure and configuration

---

## Worklogs & Session History

Keep a reverse-chronological list of session notes here. Whenever you create a note in `docs/notes/`, add a row below:

| Date | Topic / Session | Note Link | Contributors / Agent |
| :--- | :--- | :--- | :--- |
| 2026-11-07 | Agent Notes & Collaboration Framework Setup | [docs/notes/2026-11-07-agent-framework-setup.md](docs/notes/2026-11-07-agent-framework-setup.md) | Antigravity |

---

## Repository Documentation Index

* **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**: System design, data flow, tech stack, and conventions.
* **[docs/notes/](docs/notes/)**: Session-by-session work logs and handoff notes.
* **[docs/decisions/](docs/decisions/)**: Architecture Decision Records (ADRs).
* **[README.md](README.md)**: Public facing overview.
