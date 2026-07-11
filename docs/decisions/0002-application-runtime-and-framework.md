# ADR-0002: Application Runtime and Framework

## Status

Accepted

- Proposed: 2026-07-11
- Decided: 2026-07-11
- Last amended: —

This ADR establishes Python on a supported CPython runtime and Django as the runtime and framework choice, while exact versions, packages, providers, hosting, database, authentication, jobs, storage, AI, and frontend packages remain undecided.

## Decision Owners

- Decision owner: Strange Novelty repository owner
- Authors: Codex draft prepared for owner review
- Reviewers: repository owner; application architecture, security, privacy, data, frontend, operations, AI-context, and recovery perspectives

## Context

ADR-0001 establishes Strange Novelty as a private authenticated web application with a server-enforced trust boundary. The browser is an untrusted presentation client. Authentication, authorization, Workspace scoping, validation, content-state transitions, contextual Canon, provenance, concurrency, and durable writes remain server-side. The browser cannot connect directly to the primary database or AI provider. Background jobs, AI, export, backup, migration, and restoration retain separate bounded authority.

The next durable decision is which language/runtime and cohesive web framework should implement that model for Version 1. The choice must support a small modular monolith that one owner can understand and maintain, while remaining capable of a polished desktop-class writing interface.

The framework is not the architecture. Regardless of selection:

- application services and domain rules remain explicit;
- framework route or model convenience must not bypass Workspace authorization;
- browser code remains outside the trusted boundary;
- rich interaction must not duplicate authoritative rules in the client;
- persistence, authentication mechanism, durable job execution, providers, and deployment remain later decisions; and
- export, backup, migration, and restoration remain product capabilities rather than framework defaults.

The old Story Engine reinforces the need for this separation. It concentrated persistence and provider calls in browser/webview TypeScript and placed broad database authority in the presentation layer. Strange Novelty should preserve useful interface lessons without repeating that trust model.

This decision favors boring, well-supported, testable technology over novelty. It evaluates framework capabilities separately from optional ecosystem packages and does not make experimental features architectural requirements.

## Decision

If accepted, Strange Novelty Version 1 will use:

- **Language and runtime:** Python on a supported CPython runtime.
- **Cohesive web framework:** Django on a supported release line.

Django will host the server-rendered web application, server-side request handling, application services, authorization checks, forms and validation, session integration, persistence boundary, migrations, and core test harness. The application will be organized as a modular monolith with explicit internal boundaries.

HTML rendered by Django will be the default delivery mechanism. Progressive enhancement will add browser interaction where it materially improves the writing experience. A bounded client-side editor or interactive component may be selected later, but it will submit through authenticated Django endpoints and will not contain authoritative domain rules, credentials, direct database access, or provider access.

This ADR does not select:

- an exact Python or Django version;
- a database or physical schema;
- a particular ORM mapping beyond using Django’s persistence boundary as the default application integration point;
- a final authentication provider or credential mechanism;
- a job queue, object store, AI provider, integration provider, monitoring platform, or hosting product;
- a JavaScript framework, rich-text editor, CSS system, or frontend build tool;
- a deployment topology beyond ADR-0001’s cohesive initial application; or
- package versions or optional ecosystem packages.

## Selected Language and Runtime

Python on a supported CPython release is recommended because it is readable, mature, broadly understood, portable across common self-hosted environments, and well suited to data transformation, document handling, AI gateways, export, migration, backup verification, and recovery tooling.

The runtime boundary will follow these rules:

- use a currently supported stable release when implementation begins;
- pin and reproduce application dependencies through the chosen packaging process;
- avoid implementation dependence on experimental interpreter features;
- keep domain code framework-aware only where the framework materially supplies correctness or lifecycle behavior;
- isolate provider-specific clients behind internal gateways or adapters;
- treat scripts, management commands, migrations, and jobs as bounded application entry points rather than unrestricted utilities; and
- keep browser JavaScript separate from trusted Python execution.

Python’s ecosystem breadth is useful but not itself a reason to add dependencies. Standard library and Django capabilities should be preferred when they satisfy the requirement clearly and safely.

## Selected Web Framework

Django is recommended as the cohesive Version 1 framework because its core distribution supplies a mature server-side baseline for:

- request routing and middleware;
- authentication primitives and authorization hooks;
- server-side sessions;
- CSRF protection;
- forms, validation, and model-form integration;
- file-upload parsing and limits that can be wrapped by the security architecture;
- HTML templates and server rendering;
- an ORM, schema migrations, and transaction control;
- database-backed test isolation, request clients, and live-server testing;
- environment-aware settings and deployment checks; and
- management-command entry points for bounded operational workflows.

These are framework capabilities, not proof that an application is secure by default. Strange Novelty must still define authentication and account recovery, authorize every private record, protect uploads, configure sessions and HTTPS, constrain settings, exclude sensitive logs, and test all invariants.

Django’s optional administrative interface is not selected as the authoring interface or as an unrestricted operator path. If used at all later, it requires a separate bounded purpose and security review.

Durable background execution is not treated as a built-in Django capability. Django can define task entry points and application services, but the queue and worker mechanism remain a later ADR.

## Application Structure

The application will be one deployable Django project organized into cohesive internal modules. Exact names remain implementation details, but responsibilities should follow boundaries such as:

- **identity and access** — owner identity, sessions, authorization policy, and security events;
- **workspace** — Workspace ownership and root policy;
- **narrative** — Worlds, Series, Books, Chapters, Scenes, revisions, and hierarchy;
- **entities** — Characters and Locations;
- **relationships** — authoritative Links and derived backlinks;
- **authority and provenance** — content states, Creative Context, provenance, and authority-changing audit records;
- **search** — authorized queries and rebuildable indexes;
- **AI** — context manifests, gateway, suggestions, usage, and provider-independent provenance;
- **imports** — staged untrusted input and review;
- **exports** — documented author-facing representations;
- **recovery** — backup metadata, verification, migration, and restoration orchestration; and
- **operations** — bounded jobs, security events, health checks, and privacy-conscious diagnostics.

These are logical modules, not microservices. Modules communicate through explicit application-service interfaces and typed values where practical. They may share one process and database while preserving authority boundaries.

The project should avoid:

- one global models or services file;
- business rules embedded only in templates, browser components, signals, or model hooks;
- hidden cross-module writes;
- provider SDK types in core domain records;
- generic repositories that erase typed domain meaning; and
- premature internal frameworks that duplicate Django.

## Server and Browser Responsibilities

### Server responsibilities

Django server-side code will:

- authenticate requests using the later selected mechanism;
- resolve the current owner and Workspace from trusted server-side state;
- authorize every private read and write;
- validate forms, uploads, API-like requests, and operation intent;
- load current state and enforce concurrency;
- enforce hierarchy, Links, provenance, content states, contextual Canon, lifecycle, and revision rules;
- perform durable writes inside explicit transaction boundaries;
- issue bounded jobs and revalidate their results;
- build AI manifests and call the AI gateway;
- mediate private objects;
- coordinate export, backup, migration, and restoration; and
- emit bounded audit and operational events.

### Browser responsibilities

The browser will:

- render server-authorized HTML and data;
- provide navigation, editing controls, previews, and responsive interaction;
- hold transient interface state and unsaved text only as explicitly designed;
- submit author intent, form data, stable identifiers, and base versions;
- display validation errors, conflicts, job status, and AI suggestions; and
- use progressive enhancement without becoming the sole route to a core workflow where practical.

The browser will not:

- connect to the database or AI provider;
- receive database, provider, backup, object-storage, or administrative credentials;
- establish Workspace ownership;
- authorize itself based on hidden controls or routes;
- create trusted provenance or Canon approval events;
- bypass CSRF, validation, concurrency, or server-side state transitions; or
- activate imports or restored data directly.

Client-side validation may improve usability but never substitutes for server validation.

## Rendering and Interaction Model

Django templates and ordinary HTTP forms are the baseline. This gives important flows a straightforward request/response model, server-side validation, CSRF integration, and progressive enhancement.

The interaction strategy is:

1. Render authenticated pages and initial data on the server.
2. Use semantic HTML and conventional forms for navigation and bounded mutations.
3. Add small browser-side enhancements for filtering, previews, autosave indicators, conflict dialogs, job progress, and keyboard-centric editing.
4. Introduce a richer client-side editing component only where the writing experience requires it.
5. Keep durable save, revision creation, concurrency resolution, state transitions, AI submission, and destructive actions in server endpoints.

The rich Scene editor may need substantial browser code. That does not require a separate SPA architecture. Its protocol with the server must be explicit, versioned where necessary, authenticated, CSRF-protected as applicable, and tested for stale writes and recovery.

The browser-local draft strategy remains undecided. Local data must not become the only copy of acknowledged content, and sensitive caching must follow the security architecture.

## Domain and Persistence Boundaries

Django models may represent persistence concepts, but database models are not automatically the complete domain boundary. Important workflows should use explicit application services that coordinate:

- authorization and Workspace scoping;
- validation and normalized input;
- current-version loading;
- domain invariants;
- transactions and locking where required;
- revision and provenance creation;
- content-state and Creative Context transitions;
- audit records;
- derived-state invalidation; and
- post-commit job creation.

Views, forms, commands, and jobs call the same application services rather than duplicate domain rules.

Database constraints should reinforce stable identity, ownership, references, and uniqueness where the later data ADR determines they are appropriate. The physical schema, database engine, identifier format, locking strategy, and ORM details remain undecided.

Django transactions provide a clear mechanism for multi-record writes, but transaction scope must be deliberate. External AI, storage, export, or integration calls do not occur while holding an avoidably long database transaction. Jobs are issued after the authoritative commit under a safe handoff design selected later.

## Background-Job Boundary

Django will define provider-independent job intents and the application services jobs may invoke. The durable job runner and queue remain a later decision.

Every job must carry:

- a stable operation identifier;
- one Workspace;
- one supported task type;
- bounded record or artifact references;
- base versions or other consistency markers;
- the minimum service authority; and
- retry, expiration, and idempotency metadata.

Workers execute server-side Python, not browser code. They must reauthorize their service operation and revalidate affected records before committing results. A job cannot reuse the owner’s browser session, promote Canon, accept imported content, activate restoration, publish, purge, or expand its scope.

The framework’s management-command mechanism may support manual bounded operations and recovery tooling, but it is not a durable queue and must not become an unaudited administrative bypass.

## AI-Gateway Boundary

The AI gateway will be a server-side Django module or adjacent bounded process using application-service interfaces. It will:

- accept only supported, explicitly invoked task packages;
- load or receive the exact approved context manifest;
- obtain credentials through server-side secret handling;
- construct provider requests;
- enforce request and response limits;
- normalize untrusted responses;
- attach provider-independent provenance and usage; and
- return results as AI suggestions.

No provider SDK will be imported into browser code or core domain models. Provider-specific code remains behind the gateway. The provider, model, request library, retry policy, and retention contract remain later decisions.

Django does not make AI requests safe automatically. Prompt-injection handling, context preview, provider isolation, failure behavior, and retention continue to be governed by `docs/architecture/ai-context.md`.

## Testing Model

The recommended stack supports a layered test model:

- **domain tests** — pure or database-backed tests for hierarchy, Links, states, contextual Canon, provenance, revisions, deletion, and migration invariants;
- **application-service tests** — authorization, Workspace scoping, transactions, concurrency, audit events, and job creation;
- **form and validation tests** — server-side parsing, field errors, CSRF-dependent flows, uploads, and malicious input;
- **request tests** — authenticated and unauthenticated routes, altered identifiers, response minimization, and safe failure;
- **database tests** — constraints, migrations, rollback or recovery behavior, and representative data transformations;
- **job tests** — bounded authority, stale data, idempotency, retry, and partial failure;
- **AI gateway tests** — manifest fidelity, credential isolation, hostile output, provider failure, and unchanged source content;
- **export and recovery tests** — format completeness, integrity, secret exclusion, backup verification, isolated restoration, and migration;
- **browser tests** — the core user journeys, rich editor behavior, conflicts, progressive enhancement, and supported browsers; and
- **security tests** — authentication, authorization, CSRF, XSS, injection, uploads, logging boundaries, secrets, and administrative access.

Django includes a test runner, request client, transaction-aware test cases, and live-server facilities. Browser automation and specialized security tooling are separate package/tool choices and are not selected here.

Tests use synthetic content. Production manuscripts, databases, exports, backups, prompts, and artwork do not enter routine development or CI.

## Development Model

Development should use one repository and one primary application project. The normal workflow should make server/client boundaries visible:

- server modules own domain and persistence behavior;
- templates own server-rendered presentation;
- static browser assets own bounded interaction;
- tests accompany each authority boundary;
- migrations are reviewed as durable transformations;
- environment-specific settings do not contain committed secrets;
- development data is synthetic; and
- commands that mutate data are explicit and safe by default.

The development server is not a production deployment. Production-equivalent security settings, static/private media handling, HTTPS assumptions, and administrative controls require separate verification.

Formatting, linting, type checking, dependency auditing, browser testing, and packaging tools remain later implementation choices. Python type annotations should be used where they improve boundary clarity, but static typing is not treated as enforcement of runtime authorization or validation.

## Dependency Policy

The project will prefer Django core and the Python standard library when they meet requirements without compromising clarity or security.

Add a third-party dependency only when:

- a documented requirement cannot reasonably be met by the framework or small local code;
- the package has a clear bounded responsibility;
- maintenance, release cadence, security history, license, transitive dependencies, and exit path are reviewed;
- it does not move authority into the browser or provider;
- it does not require provider-specific core data; and
- representative tests protect the boundary it supplies.

Authentication, MFA, rich editing, background jobs, document parsing, AI access, object storage, observability, and browser testing may need third-party packages. This ADR explicitly does not select them.

Avoid framework-within-framework abstractions, large convenience suites added speculatively, and client packages that duplicate server domain logic. Lock dependencies reproducibly and maintain a reviewable inventory.

## Upgrade and Support Policy

- Begin implementation on a stable, supported CPython release and a stable, supported Django release line.
- Prefer a Django release with a support horizon appropriate to Version 1 delivery and maintenance; select the exact release in implementation planning without changing this architectural decision.
- Do not depend on experimental framework features.
- Track Python and Django support windows and security advisories.
- Apply security updates promptly under the vulnerability-response process.
- Test framework upgrades against authentication, authorization, sessions, CSRF, forms, uploads, migrations, transactions, templates, jobs, AI, export, and restoration.
- Review deprecations before they become forced migrations.
- Keep provider and optional-package upgrades separate from framework upgrades where practical.
- Record a new ADR if an upgrade materially changes the authority model, rendering strategy, persistence boundary, deployment model, or major tradeoffs.

The project should favor documented stable APIs and avoid deep reliance on undocumented internals.

## Deployment Portability

Django and CPython will be deployed through provider-neutral application interfaces. The exact process manager, reverse proxy, operating environment, container choice, hosting provider, and network topology remain undecided.

Portability requirements are:

- no dependency on vendor-specific request, identity, storage, job, or observability APIs in core domain modules;
- configuration supplied outside source control;
- provider adapters behind internal interfaces;
- documented environment requirements and startup checks;
- repeatable static-asset and application builds;
- migrations runnable through a protected operational workflow;
- health checks that do not expose private content;
- exports and backups restorable without the original hosting provider; and
- no assumption that a serverless or edge-only runtime is required.

The application may use managed services later, but the cohesive server-side authority model must remain portable to another compatible environment.

## Rationale

Django best matches Strange Novelty’s risk profile and maintenance needs because it starts with a cohesive, server-centered web model rather than requiring the project to assemble core web security and data workflows from unrelated packages.

The strongest reasons are:

1. **Server-enforced boundaries are natural.** Middleware, request handlers, sessions, forms, ORM access, and templates reside on the trusted server side, while static browser code is visibly separate.
2. **Core web capabilities are integrated.** Authentication primitives, session support, CSRF, validation, forms, uploads, transactions, migrations, and testing are framework capabilities rather than mandatory third-party architectural foundations.
3. **A modular monolith is the default shape.** Django applications can separate domain areas while remaining one cohesive deployment and one operational system.
4. **Data-rich workflows fit the framework.** Typed records, relationships, transactional changes, revision history, provenance, content states, imports, exports, and migrations align with Django’s server-side data model and test tools.
5. **Maintenance is explicit and conservative.** Django has mature documentation, stable conventions, long-lived deployment patterns, and a support model suitable for choosing a boring supported release line.

Python also supports future document transformation, AI gateway, export, verification, and migration needs without requiring those concerns to dictate the browser architecture.

The recommendation is not based on benchmark leadership, popularity, automatic security, or an assumption that Python is the only capable language. Rails offers a comparably cohesive model. Next.js and SvelteKit can enforce server boundaries but require more deliberate assembly around authentication, validation, CSRF/session choices, persistence, and jobs. A separate SPA/API split adds a second application boundary and domain duplication before the project needs it.

## Decision Criteria

The alternatives were evaluated using these criteria:

1. Fit with ADR-0001’s server-enforced trust boundary.
2. Suitability for a cohesive modular monolith.
3. Maintainability for one owner and a small project.
4. Readability and future maintainability.
5. Secure defaults and clarity of server/client separation.
6. Server-side authentication and authorization support.
7. Forms, validation, sessions, CSRF, and file-upload handling.
8. Domain modeling and transactional writes.
9. Revision, concurrency, provenance, and content-state enforcement.
10. Rich desktop-class writing UI support.
11. Server rendering and progressive enhancement.
12. Domain, request, authorization, and browser testing.
13. Background jobs without browser authority.
14. AI gateway and external-service isolation.
15. Export, backup, migration, and restoration support.
16. Privacy-conscious logging and error handling.
17. Self-hosting and deployment portability.
18. Dependency and upgrade burden.
19. Ecosystem maturity and long-term support.
20. Operational complexity.
21. Avoiding duplicate domain rules across frontend and backend.
22. Provider independence.
23. Migration away from the framework.

Security features were evaluated as tools that require correct application, not guarantees. Rich-interface capability was evaluated separately from whether a framework encourages excessive browser authority.

## Alternatives Considered

### Alternative: TypeScript on Node.js with Next.js App Router

Next.js offers TypeScript across server and browser code, React’s mature UI ecosystem, server and client components, route handlers, server-side rendering, form actions, progressive enhancement patterns, and documented self-hosting. It is strong for a rich interactive writing interface and can be deployed cohesively.

It was not selected because the required server baseline is less integrated for this application’s priorities. Official guidance commonly relies on ecosystem choices for authentication and server-side schema validation. Sessions, CSRF strategy, persistence, migrations, jobs, and authorization architecture require more project assembly. The server/client component and caching model is powerful but increases the number of boundaries a small team must understand and test carefully for private, mutable content. React and framework release coupling also adds upgrade surface.

Next.js remains viable if owner expertise strongly favors TypeScript/React and the additional security/data assembly burden is explicitly accepted.

### Alternative: Python with Django

Django supplies an integrated server-side foundation for routing, middleware, authentication primitives, sessions, CSRF, forms, uploads, templates, ORM transactions, migrations, and testing. It naturally supports a modular monolith and conventional request/response flows.

It is the recommendation. Its weaker point is the rich browser experience: advanced editor behavior will require deliberately selected JavaScript and possibly a client component library. Durable job execution also requires a later choice. Django’s active-record-like models and implicit framework conventions can accumulate hidden coupling unless application services and module boundaries are enforced.

### Alternative: Ruby with Ruby on Rails

Rails is a strong cohesive alternative. It provides server rendering, form helpers with CSRF integration, sessions, Active Record transactions and migrations, conventions, testing, progressive enhancement through its default frontend approach, and a built-in job abstraction. It is highly productive for data-rich CRUD and workflow applications.

It was not selected because Django offers a similarly cohesive security and data baseline while Python provides a broader direct fit for the anticipated document, AI, data transformation, export, and recovery tooling. The recommendation also judges Python syntax and Django’s explicit forms and settings model to be slightly easier for long-term maintenance in this project. These are comparative preferences, not deficiencies in Rails.

Rails would be a defensible second choice, especially if owner Ruby experience is materially stronger than Python experience.

### Alternative: TypeScript on Node.js with SvelteKit

SvelteKit provides server rendering, server load functions, route handlers, form actions, hooks, progressive enhancement, and a concise component model. It can produce a cohesive full-stack application with less client boilerplate than a conventional React application and is capable of a rich writing interface.

It was not selected because more of the required security and data baseline must be composed: authentication, session policy, persistence, migrations, transactional domain services, job execution, and much validation depend on application design or third-party packages. Its ecosystem and long-term operational conventions are less established than Django’s for this conservative, data-rich application. The framework’s frontend strengths do not outweigh the extra server-side assembly for Version 1.

### Alternative: separately developed single-page frontend and standalone API backend

A separate SPA and API can create a strong network boundary, allow specialized frontend and backend stacks, and support independent scaling or additional clients.

It was not selected because it introduces two applications, a formal API surface, duplicated types and validation, cross-origin and token concerns, separate builds, and pressure to duplicate domain rules. It increases operational and test complexity before Version 1 has multiple clients or scaling requirements. A rich editor does not by itself require an independently deployed SPA.

If future native or external clients create a demonstrated need, a bounded API can be extracted from the same server-side application services without changing the authority model.

## Comparative Assessment

Ratings are relative to Strange Novelty Version 1, not general framework quality. “Strong” means the framework supplies or naturally supports the criterion with limited architectural assembly. “Moderate” means it is viable but requires more deliberate application or ecosystem choices.

| Criterion | Django | Next.js App Router | Rails | SvelteKit | Separate SPA + API |
| --- | --- | --- | --- | --- | --- |
| ADR-0001 server boundary | Strong | Strong with discipline | Strong | Strong with discipline | Strong but more boundaries |
| Cohesive modular monolith | Strong | Strong | Strong | Strong | Weak by design |
| Built-in auth/session/CSRF baseline | Strong | Moderate | Strong | Moderate | Depends on backend |
| Forms and server validation | Strong | Moderate | Strong | Moderate | Duplicated coordination |
| Transactional domain workflows | Strong | Moderate; persistence-dependent | Strong | Moderate; persistence-dependent | Strong backend, more integration |
| Rich writing interface | Moderate to strong with bounded JS | Strong | Moderate to strong | Strong | Strong |
| Server rendering/progressive enhancement | Strong | Strong | Strong | Strong | Usually weaker baseline |
| Integrated request/database testing | Strong | Moderate | Strong | Moderate | More suites and contracts |
| Background-job abstraction | Requires later package/design | Requires later package/design | Strong built-in abstraction | Requires later package/design | Backend-dependent |
| AI/provider isolation | Strong server module boundary | Strong with server-only discipline | Strong server module boundary | Strong with server-only discipline | Strong backend, more API surface |
| Migration/export/recovery tooling | Strong | Moderate; package-dependent | Strong | Moderate; package-dependent | Backend-dependent |
| Dependency burden for required baseline | Lower | Higher | Lower | Higher | Highest overall |
| Operational simplicity | Strong | Strong to moderate | Strong | Strong to moderate | Weakest |
| Provider independence | Strong | Strong if self-hosted assumptions remain explicit | Strong | Strong | Strong but complex |
| Framework exit path | Moderate | Moderate | Moderate | Moderate | Frontend/backend independently replaceable at higher cost |

No option eliminates the need for application-specific authorization, concurrency, provenance, content-state, backup, or restoration design.

## Evidence

### Repository evidence

- ADR-0001 requires a cohesive private web application with server-enforced boundaries.
- The architecture overview assigns policy enforcement and external coordination to the application server.
- The security architecture requires server-side authorization, sessions, CSRF, upload safety, secret isolation, protected storage, bounded jobs, and isolated restoration.
- The data model requires transactional multi-record workflows, stable identity, provenance, revisions, concurrency, states, migrations, and recovery.
- The AI context architecture requires a server-side gateway and manifest validation.
- The integration architecture requires future adapters behind the application server.
- The old Story Engine audit identifies direct client database/provider authority and concentrated frontend persistence logic as patterns not to repeat.

### Framework documentation reviewed

The comparison used current official documentation conceptually and does not bind the ADR to the exact documented versions:

- [Django authentication](https://docs.djangoproject.com/en/stable/topics/auth/)
- [Django sessions](https://docs.djangoproject.com/en/stable/topics/http/sessions/)
- [Django forms](https://docs.djangoproject.com/en/stable/topics/forms/)
- [Django file uploads](https://docs.djangoproject.com/en/stable/topics/http/file-uploads/)
- [Django transactions](https://docs.djangoproject.com/en/stable/topics/db/transactions/)
- [Django testing](https://docs.djangoproject.com/en/stable/topics/testing/)
- [Django deployment checklist](https://docs.djangoproject.com/en/stable/howto/deployment/checklist/)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Next.js forms guide](https://nextjs.org/docs/app/guides/forms)
- [Next.js authentication guide](https://nextjs.org/docs/app/guides/authentication)
- [Next.js self-hosting guide](https://nextjs.org/docs/app/guides/self-hosting)
- [Rails security guide](https://guides.rubyonrails.org/security.html)
- [Rails form helpers](https://guides.rubyonrails.org/form_helpers.html)
- [Rails Active Record transactions](https://api.rubyonrails.org/classes/ActiveRecord/Transactions/ClassMethods.html)
- [Rails Active Job](https://guides.rubyonrails.org/active_job_basics.html)
- [Rails testing guide](https://guides.rubyonrails.org/testing.html)
- [SvelteKit form actions](https://svelte.dev/docs/kit/form-actions)
- [SvelteKit authentication guidance](https://svelte.dev/docs/kit/auth)
- [SvelteKit server hooks](https://svelte.dev/docs/kit/hooks)
- [SvelteKit Node deployment adapter](https://svelte.dev/docs/kit/adapter-node)

### Limits of the evidence

No prototype, benchmark, owner-maintenance exercise, rich-editor spike, deployment trial, restoration exercise, or dependency audit was performed. The recommendation relies on documented capabilities and architectural fit. Before acceptance, owner experience and willingness to maintain Python/Django should be weighed explicitly.

## Consequences

### Positive

- The trusted server boundary maps naturally to the framework’s request lifecycle.
- Core security and web capabilities require fewer foundational third-party packages.
- One language covers domain services, migrations, AI gateway, export, backup verification, and recovery tools.
- Server rendering and forms provide a dependable baseline before rich enhancement.
- ORM transactions and migrations support explicit multi-record workflows.
- The built-in test framework supports domain, request, authorization, and database tests.
- A modular monolith remains straightforward to deploy and understand.
- Provider-specific code can stay behind server-side adapters.
- Self-hosting remains possible without selecting a hosting vendor.

### Negative

- The browser experience will use a different language from trusted server code.
- A sophisticated editor may require a separate JavaScript package and build process.
- Django does not provide the final durable background-job mechanism.
- Built-in authentication primitives do not decide MFA, recovery, enrollment, or the final security policy.
- ORM convenience can encourage domain logic in models or signals unless boundaries are enforced.
- Python’s dynamic typing provides less compile-time boundary checking than end-to-end TypeScript.
- Server rendering may require deliberate partial-update design to feel fluid during long writing sessions.

### Neutral or Operational

- Django templates are the baseline, not a prohibition on client components.
- The Django admin is not the product interface.
- The selected database remains open within Django-supported and application-required constraints.
- Async request support is not an architectural requirement.
- Jobs may run in a separate process while remaining part of one cohesive application deployment.
- Exact Python and Django releases are selected at implementation time from supported stable lines.

## Risks and Mitigations

| Risk | Impact | Mitigation | Residual risk |
| --- | --- | --- | --- |
| Rich editor outgrows template-first UI | Pressure to create a second frontend architecture | Define editor protocol as a bounded component; keep saves and rules server-side; prototype with synthetic content before selection | Significant browser code may still need its own testing and upgrade cycle |
| Domain logic accumulates in models, views, signals, or forms | Hidden coupling and inconsistent authorization | Explicit application services, module boundaries, architecture tests, limited signal use, code review | Django conventions can still encourage shortcuts |
| Dynamic typing hides boundary mistakes | Runtime defects in complex workflows | Type annotations, focused value objects, validation, static analysis choice later, comprehensive tests | Python remains dynamically typed at runtime |
| Background jobs require third-party infrastructure | Added dependency and operational burden | Keep provider-independent job intents; select queue in a later ADR; begin with only demonstrated asynchronous work | A reliable worker still adds another process or service |
| Authentication capabilities are mistaken for complete security | Account or authorization vulnerabilities | Separate auth ADR, server-side Workspace checks, security tests, deployment checklist, threat review | Misconfiguration remains possible |
| File-upload support is treated as safe parsing | Malicious uploads or parser compromise | Apply security architecture limits, quarantine, isolated parsing, allowlists, and no public media execution | Complex document parsers remain high risk |
| ORM obscures expensive or unsafe queries | Performance problems or authorization leakage | Workspace-scoped query services, query tests, indexes decided with schema, explain/measure representative workloads | Data growth may expose later bottlenecks |
| Framework upgrade affects behavior | Security or compatibility regressions | Supported release policy, deprecation tracking, upgrade tests, pinned dependencies, staged upgrades | Major upgrades still require maintenance work |
| Python/Django owner familiarity is insufficient | Slower development and harder maintenance | Owner review before acceptance, small synthetic vertical-slice validation after acceptance, strong documentation | Learning cost may remain larger than an alternative |
| Framework-specific models impede exit | Migration cost | Keep exports documented, stable domain identities, provider-independent records, application services, tested restoration | Rewriting persistence and views would still be substantial |
| Privacy leakage through framework errors or logging | Manuscript content exposed operationally | Structured error handling, production-safe settings, explicit log allowlists, synthetic tests | Third-party packages may add unsafe logging defaults |

## Security and Privacy Review

- Security-sensitive: Yes
- Primary references: `docs/architecture/security.md` and ADR-0001
- Additional references: `docs/architecture/ai-context.md`, `docs/architecture/integrations.md`, and `docs/architecture/data-model.md`

### Security implications

The recommendation puts routing, session integration, forms, CSRF, validation, persistence access, and authorization enforcement in one server framework. This reduces boundary assembly but creates a high-value Django process that must be configured, patched, monitored, and least-privileged.

Django features are defense mechanisms, not authorization policy. Every query and mutation still requires explicit current-owner and Workspace scoping. Model identifiers, forms, URL patterns, and admin permissions do not establish ownership automatically.

### Privacy implications

The server processes manuscript content and sensitive metadata. Templates, forms, errors, debug tooling, query logging, uploaded files, and test fixtures can expose that content if configured carelessly. Production debug output must be disabled; logging must use bounded event fields; development and CI use synthetic content.

No browser bundle may contain Django secret material, database credentials, provider credentials, backup credentials, or unrestricted object-storage authority. Environment settings and server secrets remain outside Git.

### Authentication and session implications

Django supplies authentication primitives and session middleware, but this ADR does not choose enrollment, passwords, delegated identity, MFA, account recovery, session backend, expiration, or reauthentication policy. Those require a later ADR consistent with the security architecture.

CSRF protections must remain enabled for cookie-authenticated state-changing requests. API-like editor requests do not bypass protection merely because they use JSON or browser JavaScript.

### Upload implications

Django can receive uploaded files, but all imports and uploads remain untrusted. Size limits, type verification, storage isolation, parsing sandbox, archive controls, active-content handling, and retention require separate design.

### Required security testing

- authentication and session behavior selected later;
- unauthenticated and cross-Workspace denial on every private route and service;
- CSRF on forms and enhanced editor mutations;
- server-side validation despite altered client requests;
- XSS-safe rendering of story, imported, and AI text;
- query scoping and injection resistance;
- file-upload limits and malicious-content handling;
- absence of secrets from browser assets, logs, errors, exports, and backups;
- debug and deployment settings;
- job and management-command authority;
- AI gateway isolation;
- private object access; and
- export, migration, backup, and restoration boundaries.

### Residual risk

The framework cannot prevent application-specific authorization mistakes, unsafe rich-editor rendering, harmful dependencies, incorrect deployment, or privileged server compromise. These risks require explicit architecture, tests, operations, and later ADRs.

## Product and Architecture Alignment

### Product alignment

The recommendation supports a private, dependable, low-maintenance writing workspace. Server rendering and conventional forms provide a trustworthy baseline, while bounded enhancement allows the desktop-class editor to improve without shifting authority into the browser.

It preserves authorial control, visible states, deliberate AI, imports as evidence, navigable Links, useful export, complete backup, and tested restoration.

### Scope alignment

The framework can implement Version 1 without adding teams, public sharing, integrations, general AI, native mobile applications, or a plugin platform. No future-phase feature is moved into scope.

### Architecture alignment

The decision preserves ADR-0001:

- private authenticated web application;
- untrusted browser client;
- server-side authentication, authorization, Workspace scoping, validation, domain rules, concurrency, provenance, and writes;
- no direct browser database or provider access;
- one cohesive initial deployment;
- explicit logical boundaries without microservices; and
- bounded jobs, AI, export, backup, migration, and restoration.

It also preserves the data model’s stable identity and authority requirements, the security architecture’s secret and logging boundaries, the AI context manifest, and the future integration-adapter boundary.

### Normative-document impact

No product or architecture document requires amendment for this Proposed ADR. If accepted, the ADR index should be updated. Later physical and operational decisions must remain consistent with it or supersede it explicitly.

## Migration, Portability, and Recovery

### Migration from the old Story Engine

Django management commands or application services may later host a bounded importer, but this ADR does not authorize one. A future importer must use synthetic tests first, read an approved copy or export, exclude settings and credentials, stage records as Imported content, preserve external provenance, map stable identities, and never infer Canon.

### Framework portability

To reduce Django lock-in:

- keep stable identifiers and export formats independent of framework internals;
- avoid serializing ORM objects as the author-facing export contract;
- keep provider-specific types outside core records;
- document domain rules separately from models and templates;
- use explicit application services for important workflows;
- maintain versioned data exports and migrations;
- keep private objects portable; and
- test restoration from documented artifacts rather than from framework assumptions alone.

### Backup and restoration

Django migrations are part of representation evolution but are not the complete backup or restoration design. Later ADRs must define consistent database and private-object capture, manifests, integrity, secret exclusion, version compatibility, isolated restoration, inactive external credentials, representative checks, and explicit activation.

The selected framework must be reconstructible from source, locked dependencies, documented configuration, and protected secrets. A backup is not complete merely because Django can recreate database tables.

## Follow-Up Work

- [ ] Review and either accept, revise, defer, reject, or withdraw this ADR.
- [ ] Confirm owner willingness and ability to maintain Python and Django.
- [ ] Validate that the selected rendering model can support the core desktop writing journey with a small synthetic prototype only after authorization.
- [ ] Choose exact supported Python and Django release lines during implementation planning.
- [ ] Define repository module boundaries and dependency rules.
- [ ] Propose the primary database and physical persistence ADR.
- [ ] Propose stable identifier, revision, concurrency, and migration details where not already decided.
- [ ] Propose authentication, session, authorization, MFA, and account-recovery ADRs.
- [ ] Decide whether Version 1 needs a rich editor package and document its security and portability boundary.
- [ ] Select a durable background-job approach in a later ADR.
- [ ] Define secret management and environment configuration.
- [ ] Define private object-storage need and access pattern.
- [ ] Select AI provider access and request implementation behind the gateway.
- [ ] Define logging, security events, error handling, and observability.
- [ ] Define export format, backup, verification, migration, and isolated restoration.
- [ ] Define dependency scanning, support-window monitoring, and upgrade verification.
- [ ] Update `docs/decisions/README.md` only after this ADR is accepted.

No follow-up item authorizes application initialization, package installation, provider selection, database selection, deployment, or migration while this ADR remains Proposed.

## Implementation References

- Not yet available.
- No application project, configuration, package selection, or prototype is created by this ADR.

## Supersession and Amendment History

- Supersedes: None
- Superseded by: None
- Amendments: None
