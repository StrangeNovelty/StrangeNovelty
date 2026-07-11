# Strange Novelty Architecture Decision Records

## Purpose

Architecture decision records (ADRs) preserve significant, durable decisions that shape Strange Novelty. They explain what was decided, why it was chosen, which alternatives were considered, what tradeoffs follow, and what work remains.

ADRs complement the product and architecture documents. Product documents define intent and scope. Architecture documents define current system-wide requirements and boundaries. ADRs record particular choices made within those constraints. Implementation may demonstrate a decision, but it must not become the only place where a durable decision is discoverable.

ADRs are not brainstorming notes, meeting transcripts, implementation diaries, or a substitute for updating normative documentation. A proposal becomes an ADR when it is concrete enough to review as a durable choice.

This directory currently defines the process only. No numbered ADRs are created by this document.

## What Requires an ADR

Create an ADR when a decision is durable, materially constrains later work, has meaningful alternatives or tradeoffs, crosses an important trust or data boundary, or would be costly or risky to reverse.

Examples include:

- selecting the application architecture, language, framework, deployment shape, or major runtime boundary;
- selecting hosting, database, object storage, job execution, search, or deployment approaches;
- selecting authentication, session, authorization, account-recovery, secret-management, encryption, logging, or administrative-access mechanisms;
- defining a physical data representation, stable-identifier strategy, revision model, concurrency model, deletion model, or migration policy;
- choosing export, backup, integrity-verification, retention, restoration, or disaster-recovery approaches;
- selecting the Version 1 AI provider, model-access pattern, context implementation, retention behavior, or hard request limits;
- approving a future integration provider, authorization scope, data direction, synchronization model, or source-of-truth rule;
- accepting a significant security, privacy, reliability, portability, operational, cost, or vendor-dependency tradeoff;
- changing an established architectural invariant or replacing a prior decision;
- adopting a dependency or external service that becomes critical to security, durability, or core operation; and
- making a choice explicitly identified by the roadmap or architecture documents as requiring a decision record.

Several related choices may share one ADR only when they form one coherent decision and can be evaluated together. Independent choices should remain separate so they can be superseded independently.

## What Does Not Require an ADR

An ADR is normally unnecessary for:

- exploratory notes, questions, prototypes, spikes, or brainstorming without a decision;
- routine implementation details that follow directly from an accepted decision and are inexpensive to change;
- local refactors that preserve documented behavior and boundaries;
- bug fixes that restore already documented behavior;
- formatting, naming, comments, or documentation corrections without durable implications;
- temporary diagnostic commands or development-only tooling that introduces no durable dependency;
- ordinary dependency patch updates that do not change behavior, risk, support policy, or architecture;
- decisions already fully constrained by an accepted ADR, unless the new work changes its assumptions or consequences; and
- product ideas that have not entered scope.

When uncertainty exists, consider reversibility, blast radius, lifespan, security and privacy impact, data migration, operational burden, and whether a future contributor would reasonably ask why the choice was made. A short ADR is preferable to an undocumented consequential decision, but records should not be created merely to catalog every code choice.

## Decision Timing

Record a decision before implementation materially depends on it.

The normal sequence is:

1. Identify the decision and the constraints that make it necessary.
2. Gather proportionate evidence and viable alternatives.
3. Draft the ADR with status **Proposed**.
4. Review it against product, architecture, security, data, AI, integration, portability, and recovery requirements as applicable.
5. Resolve material questions and set the ADR to **Accepted** or another terminal proposal status.
6. Update affected normative documentation.
7. Implement the accepted decision and add implementation references when they exist.

Exploration may precede an ADR, and a bounded prototype may provide evidence when clearly isolated and disposable. A prototype does not establish architecture by default. Production code, irreversible migrations, provider commitments, secret provisioning, or durable schemas must not silently precede the decision that authorizes them.

Urgent security remediation may temporarily lead documentation when delay would increase harm. In that case, record the decision and reconcile affected documentation as part of the remediation, not as indefinite follow-up.

## Decision Ownership

The repository owner is the final decision authority for Strange Novelty. Authors of an ADR are responsible for presenting the decision accurately, identifying affected documents and stakeholders, and incorporating review evidence. An ADR author does not gain authority merely by writing the proposal.

Each ADR names:

- the decision owner;
- the author or authors;
- relevant reviewers or review roles;
- the date proposed and, when decided, the decision date; and
- the people or roles responsible for follow-up work where known.

External providers, AI systems, imported material, prototypes, and existing implementations may inform a decision but cannot approve it. The old Story Engine is reference-only and does not define current architecture.

## Status Lifecycle

Use one of these statuses:

- **Proposed** — ready for review; not yet authorized for dependent implementation.
- **Accepted** — approved as the current decision; implementation may depend on it.
- **Rejected** — considered and deliberately not chosen.
- **Deferred** — decision is valid to consider but intentionally postponed until named prerequisites or evidence exist.
- **Superseded** — replaced in whole by a later accepted ADR.
- **Withdrawn** — proposal removed by its owner before acceptance because it is no longer relevant, adequately formed, or needed.

An accepted ADR remains **Accepted** even if implementation is incomplete. Implementation state belongs in follow-up work or project tracking, not the decision status.

A typical lifecycle is:

```text
Proposed -> Accepted -> Superseded
         -> Rejected
         -> Deferred -> Proposed
         -> Withdrawn
```

Status changes are edits to the existing record except when an accepted decision is replaced; replacement requires a new ADR and superseding links. The status history and relevant dates should remain understandable from the record or repository history.

## File Naming and Numbering

Number ADRs sequentially using four digits and a short lowercase kebab-case title:

```text
docs/decisions/0001-example-decision-title.md
docs/decisions/0002-another-decision.md
```

Rules:

- Reserve the next number when a concrete ADR file is created, not during brainstorming.
- Never reuse a number, including after rejection, withdrawal, or supersession.
- Keep the filename stable after review begins. Clarify the document title rather than renaming casually.
- Use one top-level heading in the form `ADR-NNNN: Decision Title`.
- Number by repository order, not by product phase or architecture area.
- Do not encode status in the filename.
- Do not create placeholder ADR files solely to reserve future numbers.

This README is unnumbered and is not itself an ADR.

## Required ADR Sections

Every ADR must include these sections:

1. **Status** — current lifecycle status and relevant dates.
2. **Decision Owners** — owner, authors, and reviewers.
3. **Context** — the problem, constraints, assumptions, and reason a decision is needed now.
4. **Decision** — the concrete choice and its boundaries.
5. **Rationale** — why the decision best satisfies the documented requirements.
6. **Alternatives Considered** — viable alternatives and why they were not chosen.
7. **Consequences** — positive, negative, neutral, operational, and migration effects.
8. **Risks and Mitigations** — material failure, security, privacy, durability, cost, and lock-in risks.
9. **Product and Architecture Alignment** — affected scope, principles, architecture documents, and invariants.
10. **Follow-Up Work** — required documentation, implementation, testing, migration, operational, and review tasks.
11. **Implementation References** — links to later code, schema, configuration, tests, runbooks, or pull requests when available.
12. **Supersession and Amendment History** — related ADRs and material clarifications.

Sections may be concise when the decision is small, but they should not be omitted. Use “None” or “Not yet available” with a short explanation when appropriate.

An ADR must explain context, decision, rationale, alternatives, consequences, risks, and follow-up work clearly enough that a future reader can understand the choice without reconstructing a private conversation.

## Evidence and Alternatives

Evidence should be proportionate to the decision’s cost and risk. Useful evidence may include:

- requirements traced to product and architecture documents;
- small, non-production prototypes using synthetic data;
- performance, reliability, recovery, or compatibility measurements;
- official specifications and provider documentation;
- security and privacy assessments;
- operational complexity and maintenance estimates;
- migration and exit-path exercises;
- cost models with stated assumptions; and
- prior incidents or known failure modes described without sensitive data.

Distinguish verified facts, measurements, estimates, assumptions, and preferences. Date evidence that may change, especially provider terms, prices, support lifecycles, security features, and service limits.

Rejected alternatives must be summarized fairly. State the strongest relevant benefits and the actual reason each was not selected. Do not invent weak alternatives to make the chosen option appear inevitable. When no credible alternative exists, explain why.

An ADR should identify what new evidence would justify reconsideration.

## Security and Privacy Review

Every ADR must state whether it has security or privacy implications. A decision is security-sensitive when it affects identity, authorization, sessions, secrets, transport, storage, private objects, uploads, imports, AI exposure, integrations, logging, telemetry, exports, backups, restoration, administrative access, dependencies, or incident response.

A security-sensitive ADR must:

- reference `docs/architecture/security.md` and the applicable invariants;
- describe protected assets and affected trust boundaries;
- document private data entering, leaving, or being duplicated by the decision;
- identify permissions, credentials, secrets, logs, retention, deletion, and operator access involved;
- explain threat assumptions, abuse cases, failure behavior, and mitigations;
- document privacy implications and data minimization;
- identify security testing and incident-response follow-up; and
- state any accepted residual risk explicitly.

AI decisions must also reference `docs/architecture/ai-context.md`. Integration decisions must also reference `docs/architecture/integrations.md`.

ADRs must never contain credentials, API keys, tokens, certificates, private manuscripts, unpublished story content, sensitive prompts, provider request or response bodies, private exports, backups, databases, artwork, or other secrets. Use synthetic examples, redacted identifiers, bounded summaries, and protected references instead.

## Product and Scope Alignment

Each ADR must identify the product goals, principles, scope boundaries, roadmap phase, and architecture requirements it supports.

An ADR cannot silently change product scope. If a decision adds, removes, or materially changes a feature, user journey, acceptance criterion, roadmap phase, external integration, public exposure, or author-control behavior, update the relevant product documents in addition to the ADR before implementation proceeds.

An ADR also cannot silently weaken established invariants. If a proposal conflicts with an architecture document, the proposal must identify the conflict and include the required architecture-document amendment. Acceptance requires those sources of truth to be made consistent.

Specific alignment expectations include:

- data-model decisions preserve stable identity, Workspace ownership, provenance, content states, contextual Canon, revisions, concurrency, export, backup, migration, and restoration requirements;
- security decisions preserve private-by-default access, server-side enforcement, secret isolation, privacy-conscious logging, and protected recovery;
- AI decisions preserve explicit invocation, bounded understandable context, author control, AI-suggestion state, provider isolation, and unchanged authoritative content on failure; and
- integration decisions do not silently add an integration to Version 1, make a provider authoritative, broaden permissions, or weaken disconnection and local-usability guarantees.

## Consequences and Tradeoffs

Consequences describe what becomes easier, harder, possible, constrained, costly, or risky because of the decision.

At minimum, consider:

- product behavior and author experience;
- implementation and maintenance complexity;
- security and privacy;
- data integrity, identity, provenance, and content-state meaning;
- reliability, failure isolation, and operability;
- export, backup, restoration, migration, and provider exit;
- performance, capacity, and cost;
- testing and observability;
- vendor, format, protocol, and skill lock-in; and
- future options foreclosed or deliberately preserved.

Do not describe only benefits. Accepted decisions can have known disadvantages. Recording them helps future readers distinguish an intentional tradeoff from an overlooked flaw.

## Superseding Decisions

When an accepted ADR is replaced materially, create a new ADR. Do not rewrite the old decision to make it appear that the new choice was always intended.

The new ADR must:

- identify every ADR it supersedes;
- explain why the previous context or conclusion changed;
- describe migration, compatibility, rollback, and recovery effects;
- carry forward unresolved consequences and follow-up work where relevant; and
- link to required product and architecture updates.

The old ADR remains in the repository with status **Superseded** and a prominent link to its replacement. The new ADR links back to the old one. Supersession does not delete decision history or erase implementation references.

If only part of an ADR is replaced and the remaining decision is still coherent, the new record must state the exact superseded scope. Prefer full supersession when partial status would make the effective decision difficult to understand.

## Amending Decisions

Edit an existing ADR after acceptance only for non-material changes such as:

- correcting spelling, grammar, broken links, or formatting;
- adding implementation references or completed follow-up links;
- clarifying wording without changing the decision or its tradeoffs;
- updating review dates or factual implementation status; or
- recording its later supersession.

Record meaningful clarifications in the amendment-history section with a date and explanation. If an edit changes the chosen approach, scope, assumptions, security posture, data meaning, consequences, or rejected alternatives, create a new ADR that supersedes the old one.

Repository history is useful but does not replace an understandable amendment note.

## Rejected and Deferred Decisions

A rejected ADR remains in the repository. It records that a concrete option was evaluated and not selected, preventing the same discussion from being repeated without new evidence. Rejection must state the deciding reasons and must not portray alternatives unfairly.

A deferred ADR remains a proposal whose decision point has been postponed. It must identify:

- why deciding now would be premature;
- which prerequisite, evidence, scope change, or date should trigger reconsideration;
- what work must not depend on the unresolved choice; and
- any safe temporary constraint.

Deferred does not mean accepted, and roadmap placement does not authorize implementation. If a deferred proposal changes materially before reconsideration, revise it transparently or withdraw it and create a new proposal.

## Implementation References

ADRs should link to implementation only after those artifacts exist. References may include:

- repository files and modules;
- database schemas and migrations;
- configuration definitions without secret values;
- automated tests and security checks;
- export, backup, restoration, and migration tooling;
- operational runbooks and incident procedures;
- pull requests, issues, milestones, and release notes; and
- provider documentation or specifications used by the implemented decision.

Use stable repository-relative links where practical. Never paste credentials, private-data paths containing sensitive filenames, private artifact URLs, logs with story content, or secret-bearing configuration into an ADR.

Implementation references verify where a decision is realized; they do not replace the Decision or Rationale sections. If implementation diverges materially, update the normative documentation and create or amend the appropriate ADR before treating the divergence as accepted.

## Review Expectations

Review depth should match risk and reversibility. Every proposed ADR should be reviewed for:

- a concrete, bounded decision;
- accurate context and assumptions;
- fair alternatives and sufficient evidence;
- consistency with product vision, principles, scope, and roadmap;
- consistency with architecture and existing ADRs;
- security, privacy, data, AI, and integration effects where applicable;
- consequences, residual risks, migration, recovery, and exit paths;
- actionable follow-up work and acceptance evidence; and
- absence of private or secret material.

High-impact decisions should receive focused review from the relevant perspectives before acceptance. Examples include security boundaries, identity, data storage, migrations, AI-provider exposure, integrations, destructive operations, backup, and restoration.

Review comments may live in the normal collaboration mechanism, but the final ADR must incorporate the reasoning needed to stand alone. Unresolved material objections should be documented rather than silently ignored.

Before changing status to **Accepted**, confirm that required product and architecture updates are ready and that implementation is not relying on undocumented assumptions. After implementation, verify the decision against its stated acceptance evidence and update references.

## ADR Index Format

Maintain an index in this README once numbered ADRs exist. Use a compact table ordered by ADR number:

| ADR | Title | Status | Decision date | Supersedes |
| --- | --- | --- | --- | --- |
| [`0001`](0001-deployment-and-trust-boundary-model.md) | Deployment and Trust-Boundary Model | Accepted | 2026-07-11 | — |
| [`0002`](0002-application-runtime-and-framework.md) | Application Runtime and Framework | Accepted | 2026-07-11 | — |
| [`0003`](0003-primary-database-and-physical-persistence.md) | Primary Database and Physical Persistence | Accepted | 2026-07-11 | — |
| [`0004`](0004-stable-identifiers-revisions-and-optimistic-concurrency.md) | Stable Identifiers, Revisions, and Optimistic Concurrency | Accepted | 2026-07-11 | — |
| [`0005`](0005-authentication-sessions-authorization-mfa-and-account-recovery.md) | Authentication, Sessions, Authorization, MFA, and Account Recovery | Accepted | 2026-07-11 | — |
| [`0006`](0006-scene-content-representation-and-editor-persistence-boundary.md) | Scene Content Representation and Editor Persistence Boundary | Accepted | 2026-07-11 | — |
| [`0007`](0007-core-domain-schema-and-workspace-scoped-record-model.md) | Core Domain Schema and Workspace-Scoped Record Model | Accepted | 2026-07-11 | — |
| [`0008`](0008-physical-schema-constraints-and-initial-migration-boundary.md) | Physical Schema, Constraints, and Initial Migration Boundary | Accepted | 2026-07-11 | — |
| [`0009`](0009-backup-structured-archive-export-and-restoration-verification.md) | Backup, Structured Archive Export, and Restoration Verification | Accepted | 2026-07-11 | — |

Index rules:

- Link the ADR number or title to the record.
- Use the status written in the ADR.
- Use the acceptance, rejection, deferral, withdrawal, or supersession date as the decision date; use an em dash while Proposed.
- List replaced ADR numbers in **Supersedes** and link them where useful.
- Keep rejected, deferred, withdrawn, and superseded ADRs in the index.
- Do not use the index as a substitute for the ADR’s status or supersession links.
- Remove the example row when the first actual ADR is added.

No ADR index entries are created yet.

## Initial ADR Candidates

The following are candidates for future ADRs, not decisions, approvals, reserved numbers, or implementation authorization:

1. Deployment and trust-boundary model.
2. Application language, framework, and cohesive deployment architecture.
3. Primary database and hosting approach.
4. Stable-identifier and physical data-representation strategy.
5. Scene content, revision, concurrency, and recovery model.
6. Authentication, session, authorization, and account-recovery mechanism.
7. Secret, encryption-key, and environment-configuration management.
8. Private object-storage need and access model.
9. Search and indexing implementation.
10. Background-job and retry execution model.
11. Version 1 scene-focused AI provider and model-access boundary.
12. AI request, response, provenance, usage, and retention limits.
13. Export format and compatibility policy.
14. Backup format, destination, protection, schedule, verification, and retention.
15. Restoration isolation, activation, migration, and representative acceptance test.
16. Operational logging, security-event, monitoring, alerting, and retention approach.
17. Dependency, build, deployment, and supply-chain controls.
18. The first future integration, only after its roadmap entry criteria and scope change are approved.

Candidates may be split, combined, reordered, deferred, or removed when their actual decision boundaries become clear. This list must not be treated as a technology selection or permission to create application code.

## ADR Template

Copy the template below into the next numbered file only when a concrete durable decision is ready for review.

```markdown
# ADR-NNNN: Decision Title

## Status

Proposed

- Proposed: YYYY-MM-DD
- Decided: —
- Last amended: —

## Decision Owners

- Decision owner: [name or role]
- Authors: [names or roles]
- Reviewers: [names or review perspectives]

## Context

Describe the problem, why it requires a durable decision now, applicable constraints, assumptions, and the consequences of not deciding. Link to relevant product, architecture, and earlier decision documents.

## Decision

State the chosen approach precisely. Define what is included, excluded, and intentionally left open.

## Rationale

Explain why this choice best satisfies the documented requirements and evidence.

## Alternatives Considered

### Alternative: [name]

Summarize the alternative fairly, including its strengths, weaknesses, and why it was not selected.

### Alternative: [name]

Summarize the alternative fairly, including its strengths, weaknesses, and why it was not selected.

## Evidence

List relevant measurements, prototypes, official documentation, threat analysis, cost assumptions, recovery exercises, or other evidence. Distinguish facts, estimates, and assumptions.

## Consequences

### Positive

- [benefit]

### Negative

- [cost or limitation]

### Neutral or Operational

- [ongoing implication]

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| [risk] | [impact] | [mitigation] | [remaining risk] |

## Security and Privacy Review

- Security-sensitive: Yes / No
- Affected assets and trust boundaries: [summary]
- Data exposure and retention: [summary]
- Credentials, permissions, and operator access: [summary]
- Required security testing and incident follow-up: [summary]
- Applicable security invariants: [links]

Do not include credentials, secrets, private story content, sensitive prompts, private exports, backups, or databases.

## Product and Architecture Alignment

- Product vision and principles: [links and explanation]
- Scope and roadmap: [links and explanation]
- Architecture: [links and explanation]
- Required normative-document updates: [list or None]
- Invariants preserved or changed: [summary]

## Migration, Portability, and Recovery

Describe migration needs, compatibility, rollback, export, backup, restoration, provider-exit, and data-recovery effects.

## Follow-Up Work

- [ ] Documentation update
- [ ] Implementation task
- [ ] Test or verification
- [ ] Operational or recovery work

## Implementation References

- Not yet available.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
```
