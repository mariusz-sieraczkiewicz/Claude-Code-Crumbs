# Human-readable skill language

## 1\. Purpose and architecture

### Purpose and pipeline

This document is the stable target design for describing a skill in readable Markdown and turning it into a precise, executable workflow. It owns the language's concepts, author-facing forms, formal meaning, and universal execution guarantees. Linked pattern and runtime references own lower-level APIs and validation mechanics.

A construct is executable only when the selected versioned validation profile—the exact set of syntax and patterns supported by an implementation—includes its rules. Unsupported constructs are rejected before generated code is loaded; this design does not imply that every conforming profile implements every optional pattern at the same time.

The generated intermediate representation (IR) is restricted Python: ordinary Python expresses the algorithm, while controlled interfaces provide model calls and interactions with external systems.

A universal Harness is the runtime interface that executes accepted IR independently of a particular agent product. It sends work requiring interpretation or judgment to a selected agent backend and sends fully specified operations, such as reading one known file, to a deterministic effect backend without an LLM call.

```
human-readable skill + optional author references
  + autonomously discovered, pinned project evidence
  -- conditional normalization --> canonical human-readable skill
  -- independent intent check --> accepted canonical human-readable skill
  -- formalization --> validated data contracts + typed executable Python IR
  -- execution -----> universal Harness + selected agent/effect backends
```

The human-readable skill is the only form written directly by a person. It owns task-specific intent and workflow decisions while remaining readable at the appropriate level of abstraction.

The translation process, called canonicalization, first decides whether the source `SKILL.md` already follows this language's human-readable conventions. If it does, the file is preserved exactly. If it does not, canonicalization rewrites it into a concise declarative form before generating code. An independent semantic check must accept that rewrite against the original source and any references deliberately supplied by the author. The human skill remains the semantic source of truth. Before formalization, canonicalization autonomously inspects the existing skill package and relevant project context—such as files named by the skill, prior implementations, artifact schemas and examples, workflow state, and repository conventions—and pins the files actually used as evidence. That evidence recovers compatible existing data and integration contracts; it cannot override explicit human-skill meaning or silently introduce new business policy. Canonicalization is not required to be a standalone component; its internals may use deterministic code or model assistance without changing these guarantees.

This repository's reference implementation deliberately exercises the same language: a thin `human-skill build` host runs the accepted `canonicalize-human-skill` human skill through the Harness. The host owns trusted mechanics such as source snapshots, deterministic validation, and atomic publication; the builder skill owns interpretation, generation, bounded repair, and semantic review. Other implementations may organize canonicalization differently while preserving the same input, traceability, validation, and publication guarantees.

Every semantic workflow rule must be traceable to the human skill or an author-supplied reference. Generated structural fields and integration boundaries may additionally be traced to pinned project evidence or a convention defined in this document. Canonicalization owns technical choices such as Pydantic structure, operation boundaries, deterministic effects, interactions, typed application ports, and their names. It asks the author only after available evidence has been examined and at least two materially different business or policy meanings remain with different consequences. Missing technical detail by itself is not an ambiguity for the author.

The document follows the same path as a skill:

1. This section introduces the overall architecture, responsibilities, ownership boundaries, and package contents.
2. Section 2 describes what a person writes, including optional author-facing forms such as file inputs and managed workspaces.
3. Section 3 explains how that meaning becomes typed executable IR; its core rules apply to every skill, while its named pattern sections apply only when activated.
4. Section 4 defines universal validation and runtime behavior, then describes Claude Agent SDK as one concrete agent-backend profile.

### Responsibility boundaries

The pipeline separates what a person decides, what canonicalization makes explicit, and what the runtime executes.

**Human-readable skill — what a person writes**

*   Declares typed workflow inputs and the official domain output produced by a
    successful run.
*   Describes roles, task-specific instructions, ordering, parallelism, decisions, limits, required interactions with external state, and workflow-ending outcomes.
*   Opts into optional runtime patterns when the workflow requires them.
*   States recovery behavior only when a failed effect may be retried or repaired; otherwise the effect fails exactly as requested.

**Canonical human-readable skill — what canonicalization accepts or normalizes**

*   Preserves the authored file byte for byte when it already follows the language manifest.
*   Otherwise removes verbosity and general knowledge familiar to capable models while retaining every domain rule, constraint, decision, branch, responsibility, and other behavior-changing instruction.
*   Remains natural-language Markdown and becomes the published `SKILL.md`; it is not generated implementation code.

**Canonicalization — what the compiler decides and investigates**

*   Inspects the complete existing skill package and relevant project files before asking for clarification, then pins every cited evidence file for the remainder of the build. Listings and search results guide discovery, but a formal evidence entry names a readable regular file whose bytes and hash can be frozen; a directory is not treated as an evidence file.
*   Uses repository material as evidence of existing contracts and behavior, not as a second semantic specification beside the human skill.
*   Chooses the formal Pydantic structure and the boundaries and names of model operations, deterministic effects, participant interactions, and typed application ports.
*   Requests participant input only for unresolved business or policy meaning, never merely because the human skill omits compiler-owned mechanics. Operation ordering, effect timing, failure representation, generated schema shape, and host mechanics remain canonicalization decisions unless the human skill explicitly makes one of them part of business policy.

**Intermediate representation — what the system generates**

*   Makes control flow and data dependencies explicit.
*   Contains resolved types and explicit connections that can be validated before execution.
*   Expands implied conventions into formal operations and policies.
*   Is executable Python, but only within an explicitly accepted subset.
*   May be inspected by people but is not a human authoring surface.

**Execution runtime — what runs the generated workflow**

Python executes the deterministic workflow body. The Harness coordinates its typed operations without interpreting another workflow representation. An agent backend connects model-facing operations to a concrete agent system, while an independent effect backend performs validated deterministic effects. Changing either backend does not change the workflow algorithm.

### Where workflow concepts belong

The boundaries above describe the stages of a skill's lifecycle. This section changes perspective and asks where each construct used by the generated workflow should be defined. A construct belongs to the narrowest scope that can own it without importing assumptions from a particular skill.

**Universal IR core — available to every skill**

The core is the smallest vocabulary available to every IR workflow. Python provides explicit data and control flow. The Harness defines typed workflow and operation boundaries, whether model work reuses the current context or receives a fresh isolated one, separate agent capabilities and deterministic effect permissions, backend state isolated to one run, parallel execution, operational reporting, and rules for creating a safe redacted report. Core constructs include `harness.workflow`, `harness.step`, `harness.subagent`, and `harness.parallel`; conditions, loops, calls, and returns retain their Python semantics. The core distinguishes a model-facing operation—work sent to a model—from a typed effect request. Therefore permission for the host—the application or process invoking the Harness—to read one known file does not grant the model a `Read` tool.

**Reusable patterns — optional capabilities shared by skills**

A pattern is a reusable, optional behavior package, such as controlled file effects, file input loading, managed workspaces, source coverage, domain evidence, approvals, recovery, or versioning. A skill activates only the patterns it uses. A primitive is one Harness-recognized building block, such as `FileInput(...)`; a policy is a declarative rule attached to an operation or effect, such as required coverage of every selected source or one explicitly limited retry for a missing path. Pattern contracts may define their own primitives and policies, but may not introduce vocabulary from one skill domain into the core or another pattern.

**Skill domain — concepts belonging to one skill**

Pydantic contracts, prompts, decisions, evidence vocabularies, artifact names, and deterministic helpers specific to one workflow remain in that skill package. Domain-specific ownership rules, identifiers, naming conventions, and status vocabularies do not belong to the workspace pattern or IR core.

### Skill package

The ownership boundaries above are reflected in packaging. Skill-specific source and generated artifacts live in the skill directory, while universal constructs and reusable patterns are supplied by the runtime.

```
<skill-name>/
├── SKILL.md
├── references/         # optional author-supplied domain material
└── scripts/
    ├── contracts.py
    ├── ports.py          # optional typed application dependencies
    ├── adapters.py       # optional file-input conversion
    └── workflow.ir.py
```

*   `SKILL.md` is the human-readable skill and the only workflow authoring surface. A source package contains the author's version; an accepted built package contains the unchanged or normalized canonical version.
*   `references/` contains optional authoritative domain material explicitly selected by the skill author; it does not contain executable workflow logic. Clean Skill does not require this directory, and canonicalization must not create a reference merely to store its own technical choices or answers to its own questions.
*   `scripts/contracts.py` is generated during canonicalization and owns the Pydantic contracts referenced by the skill. The name avoids collision with Python's standard `types` module.
*   `scripts/ports.py` is generated only when the workflow needs application-specific deterministic capabilities. It contains typed abstract protocols and the immutable dependency aggregate, never concrete adapter implementations.
*   `scripts/workflow.ir.py` is generated during canonicalization and contains restricted, executable Python IR. Its `.py` suffix is literal: after validation, the same module runs against any conforming backend.
*   Core constructs such as `Harness`, `Capability`, `harness.step`, `harness.workflow`, `harness.subagent`, and `harness.parallel` are supplied by `human_skill_runtime`. Optional patterns may add typed runtime values such as `InvocationContext`.
*   Optional pattern APIs for controlled effects, recovery, input binding, source coverage, domain evidence, and managed workspaces are supplied by their Harness runtime modules. Their semantic definitions are not owned by individual skills.
*   Canonicalization generates real imports for editor navigation, type hints, and autocomplete.
*   Tooling discovers `workflow.ir.py` by package convention. The `metadata.types` entry in `SKILL.md`'s opening YAML metadata block, called frontmatter, resolves relative to that file and points to the module containing the Pydantic contracts.
*   Each executable profile owns a closed script surface and validates every module before import. It allows `contracts.py`, optional `ports.py`, optional `adapters.py`, and `workflow.ir.py`; pure contract helpers stay in `contracts.py`, abstract application boundaries stay in `ports.py`, and deterministic file-input conversion stays in `adapters.py`. Every accepted module and function body is checked even when the workflow does not call it.

## 2\. Writing the human-readable skill

Section 1 established the complete lifecycle and ownership boundaries. This section starts at the author-facing end: the Markdown a person writes before any formal IR exists.

### Authoring principles

A human-readable skill has two parts: machine-readable frontmatter and a natural-language Markdown body. The file begins with frontmatter; the workflow body follows it. Formal annotations in the body should remain small and secondary to the instructions.

Describe the meaning and authority that matter without trying to predict every
state the outside world may later present. Keep genuinely closed choices
closed—for example, the only permitted actions may be `keep`, `refresh`, or
`escalate`—while leaving open evidence in ordinary domain language. A status
label, note, or combination of facts is not turned into an exhaustive catalog
merely because generated Python must handle it.

For example:

```markdown
Interpret the observed record under the review policy. Treat its status and
evidence as meaningful facts rather than a fixed list of states.

- When one permitted action is clearly appropriate, propose it.
- When the choice requires participant judgment, report the decision needed.
- When no permitted action can continue safely, report why.

Do not modify the record while interpreting it.
```

This states an open semantic responsibility inside closed authority without
listing hypothetical anomalies or exposing runtime tokens and adapter
mechanics.

### Conditional normalization

Authors do not have to perform a separate manual conversion before building a skill. Canonicalization compares the source with the language manifest and returns one of two explicit dispositions:

*   `unchanged` means the published `SKILL.md` is byte-for-byte identical to the source;
*   `normalized` means the human-readable layer was rewritten because its presentation did not yet follow the manifest.

Normalization may shorten explanations, replace implementation-heavy wording with the standard human notation, and remove general advice already known to capable models. It must not remove or invent domain rules, constraints, decisions, branches, responsibility boundaries, limits, required evidence, or side effects. For example:

```text
Source: Explain at length how software teams normally review work. Then have two
reviewers inspect the result independently and stop after at most 3 attempts.

Canonical: Review the result independently with two reviewers. Stop after at
most 3 attempts.
```

The first sentence is general background; reviewer independence and the attempt limit change execution and therefore remain. A separate model-facing reviewer compares the complete source package with the proposed canonical `SKILL.md`. Types and IR are generated only after that review accepts the preservation of intent. A bounded repair may replace a rejected normalization, but the same structural validation and independent review run again.

The immutable source snapshot, including the original `SKILL.md`, remains build input and audit evidence. It is not copied into the accepted package as if it were canonical. Any reference files deliberately supplied by the author remain unchanged and accompany the canonical `SKILL.md`. Project context is separate: canonicalization first uses read-only listing and search to discover relevant material, then cites the readable regular files that actually support its decisions. The host captures those files and their hashes as a bounded evidence snapshot. A statement that a bounded directory listing found nothing further may remain in the source-reading explanation, but it has no file bytes to pin and is not passed to later stages as a project evidence file. Generation, repair, semantic review, and the candidate fingerprint use the pinned snapshot rather than mutable live project files.

### Frontmatter metadata

Frontmatter is the YAML block between `---` markers at the beginning of `SKILL.md`. It identifies the skill and connects its human-readable instructions to typed inputs and outputs. Its shape is:

```
---
name: example-skill
description: Produces a typed result through a multi-stage workflow. Use when the example workflow applies.
metadata:
  inputs: Request
  output: Result
  types: "./scripts/contracts.py"
  workspace: default
---
```

For canonicalized skills, `metadata` is a string-to-string map in which `inputs`, `output`, and `types` are required and `workspace` is optional.

`types` points to the Pydantic module that owns every named type used by the skill. Relative paths are resolved from the human-readable skill file.

### Output declaration and default serialization

The `output` entry names the Pydantic model that represents the skill's
official domain result. It does not name a runtime status wrapper, a UI
response, or a list of side effects. The workflow must return an instance of
that model whenever it successfully produces its result.

After validating the returned model, the Harness serializes its declared
fields and aliases to YAML by default. That YAML is a materialization of the
same typed result, not a second contract with an independently maintained
schema. When a skill requires the YAML to be persisted under a domain-specific
name or location, the output materialization binds the same validated value to
that declared target through a controlled effect. Serialization alone grants
no filesystem authority.

For example, `output: ExpressIntentResult` means that a successful
`express-intent` run returns an `ExpressIntentResult`; its YAML representation
is the complete contents of `business-intent.yaml`. Workspace creation, branch
changes, auxiliary files, and workflow-state updates remain effects of the run
and do not add technical fields to `ExpressIntentResult`.

Intermediate typed results remain values in the workflow data flow and in the
operational report. They do not implicitly become separate files. Persisting an
intermediate result is a behavior-changing artifact requirement and must be
stated by the human skill; otherwise canonicalization uses the typed result and
the Harness-owned reporting and audit facilities without asking the participant
to choose a storage mechanism.

When that YAML is an official file rather than only a returned representation,
the target is written next to the type:

```
output: ExpressIntentResult(`business-intent.yaml`)
```

The path is relative to the skill's declared workspace and activates the
controlled `WorkspaceWrite` effect. A persisted output therefore requires a
`workspace` declaration. The generated Harness writes exactly the YAML it
returns to the caller, with `overwrite=False`; a workflow that revises an
existing artifact needs an explicit versioning or replacement policy rather
than receiving ambient overwrite authority. Missing parent directories are
not created implicitly.

If version, update time, or changelog entries are part of the domain artifact,
they remain declared fields of its Pydantic output model. The model may decide
the semantic description of a change, but it does not invent operational
facts. A deterministic host supplies the observed UTC time, current version,
archive receipt, and configured versioning policy before the workflow builds
the final output. For example, an `ExpressIntentResult` revision reuses those
host values and the Harness serializes the resulting model; it does not edit a
second YAML representation after success.

A run that intentionally stops before producing the official result has no
output model or YAML artifact. The Harness represents that state separately in
its typed execution response for callers and user interfaces.

### Input declaration notation

The `inputs` metadata entry tells the runtime what values must exist when one request starts the skill. A bare type such as `Request` is supplied directly with that request. The optional file-input form ``Config(`path`)`` tells the runtime to load and validate a known YAML or JSON file before the workflow begins. Other origins, including environment variables and application programming interfaces (APIs), require their own typed source contracts.

`metadata.inputs` is a comma-separated list of these typed declarations:

```
inputs: "Request, Config(`.tool/config.yaml`)"
```

By convention, the workflow parameter name is the type name converted from `PascalCase` to `snake_case`. A word boundary occurs before an uppercase letter when it follows a lowercase letter or digit, and before the last uppercase letter of a run when that letter is followed by a lowercase letter; boundaries are then joined with `_` and letters are lowercased. Thus `Request` becomes `request`, `ProjectConfig` becomes `project_config`, `HTTPConfig` becomes `http_config`, and `OAuth2Config` becomes `o_auth2_config`. When the derived name is undesirable or default names would collide, the human-readable form uses `name: Type` or ``name: Type(`path`)``. Because an alias contains `:` , the complete `metadata.inputs` value is quoted as a YAML string when this form is used. Aliases are otherwise unnecessary.

```
inputs: "request: Request, project_config: Config(`.tool/config.yaml`)"
```

The file shorthand has one canonical profile: infer `yaml` from `.yaml` or `.yml` and `json` from `.json`, resolve the path from `project_root` (the root directory of the project for this invocation), require the file, and forbid invocation overrides. An unknown extension or any intended departure from this profile requires another typed source form owned by the input-binding pattern; canonicalization does not guess.

### Workspace notation

The optional `workspace` metadata entry asks the runtime to prepare a controlled working directory when its declared identity becomes available. A skill that does not need one omits this entry.

Declaring a workspace does not by itself copy every input, intermediate result,
or report into that directory. The workspace provides controlled working state;
official output materialization and any additional persisted artifacts remain
separate explicit requirements.

Workspace patterns may refer to values supplied by the Harness, typed skill inputs, and named earlier results. `$runtime.run_id` is a unique path-safe identifier for one invocation; `$runtime.utc_timestamp` is path-safe but does not guarantee uniqueness. `$inputs.<name>` refers to a declared input and `$results.<name>` to the named result produced by an earlier responsibility. A reference may continue through declared Pydantic fields, for example `$inputs.config.paths.work_root`.

```
workspace?: default | <workspace-pattern>
```

Illustrative custom patterns:

```
workspace: ".work/$runtime.utc_timestamp/"
workspace: ".work/$runtime.run_id/"
workspace: ".work/"
workspace: "$inputs.config.paths.work_root/$results.record_identity.name/"
```

Workspace patterns consist of safe literal segments plus recognized typed references. Every resolved workspace remains beneath the invocation's project root; an absolute typed root is valid only when it resolves inside that boundary. Canonicalization preserves the human-facing requirement but lowers it according to data availability: a run-start pattern becomes a static `WorkspaceSpec`, while an input- or result-dependent pattern becomes an explicit `resolve_workspace(...)` call immediately after every referenced value exists. Validation rejects forward references, missing fields, cycles, unsafe segments, and any operation that could use the workspace before resolution. Additional source roots authorize read-only source inspection only and never broaden workspace authority.

The detailed path resolution, access, lease, lifecycle, and audit rules are defined by the [managed workspace pattern](reference/managed-workspace-pattern.md).

After the metadata, the Markdown body describes responsibilities, data flow, decisions, and workflow-ending outcomes in natural language.

### Standard human-readable notation

The skill body remains natural-language Markdown rather than a token-based grammar. The forms below are standard authoring conventions. Equivalent wording is accepted when it preserves the meaning established by the human skill and any author-supplied domain material. If autonomous inspection still leaves at least two business or policy meanings with different consequences, canonicalization asks for that decision. Presentation alone does not create execution semantics. All roles, domain names, types, and numeric limits in the examples are illustrative.

Use natural language and the conventions people normally apply in the task's domain. State only departures or ambiguities that would materially change execution.

For visual structure:

*   Level-two headings may separate the workflow's main responsibilities.
*   The recommended subagent form begins with `Subagent: <role> (→ <result>)`, followed by its instructions as ordinary paragraphs.
*   Parallel execution is stated by the surrounding workflow instruction rather than encoded through Markdown nesting.
*   Lists are reserved for content that is naturally a set of alternatives or items, such as decision outcomes.
*   Avoid using deeper headings for individual subagents.
*   Headings and lists remain presentation choices; step boundaries are inferred from workflow semantics.

Main responsibilities may be separated with headings, with or without numbering. Their order comes from the described workflow, not from a requirement that every step be a numbered list. A compact arrow introduces a typed stage result:

```
## Prepare context

Collect the material needed to address the request. (→ `PreparedContext`)

## Produce proposal

Then produce a proposal from the prepared context. (→ `Proposal`)
```

Use `(→ Type)` to derive the result name from the type with the same `PascalCase`-to-`snake_case` rule used for input names. Use `(→ name: Type)` to override that name or avoid a collision.

A delegated responsibility uses a `Subagent:` block followed by ordinary paragraphs, without turning the instructions into a nested list:

```
Subagent: Research Analyst (→ `ResearchAssessment`)

Find relevant evidence and identify important uncertainties.
```

Parallel work is stated naturally around the participating blocks:

```
Review the proposal using two subagents in parallel:

Subagent: Evidence Reviewer (→ `EvidenceReview`)

Check whether the proposal is supported by the available evidence.

Subagent: Risk Reviewer (→ `RiskReview`)

Identify material risks, conflicts, and missing safeguards.
```

A loop with an explicit maximum states that human limit and when to continue or finish:

```
Run at most 5 work–verification iterations.

After each verification, decide:

- If every instruction is complete and the outcome passes, report success and finish.
- If iteration 5 has been completed, report every remaining issue and finish.
- Otherwise, fix the unresolved issues and verify again in the next iteration.
```

Ordinary human counting applies unless the task's domain intentionally defines another convention. Internal zero-based counters may exist in generated code, but they do not change or leak into this notation.

Expected branches that stop before producing the official result are described
in ordinary human language rather than fabricated as variants of the output:

```
If any required source is unavailable, report the unavailable sources and stop without producing a result.

If the requester decides that no further work is needed, report that decision and finish without producing a result.
```

An unsuccessful domain assessment may still be part of the declared output
when the official artifact is supposed to record it. The distinction is
whether the branch produces the domain result, not whether its conclusion is
positive.

When the workflow cannot continue without a participant's information or
decision, say what must be presented and what decision is needed in ordinary
domain language. Do not hide the interaction inside a model-facing step:

```
If material overlap exists, present the matching requirements and uncovered
value to the PO. Ask whether to merge, extend, create a distinct item, or finish
because no further work is needed. Continue the same workflow from that answer.
```

The human-readable skill does not describe transport, polling, continuation
tokens, or checkpoint files. Those mechanics belong to the Harness and host.
If answers may expose another material question, the skill may say to repeat
until the ambiguity is resolved; each round still waits for the participant
and may be cancelled or allowed to expire.

When an open situation must be interpreted before one of a closed set of
authoritative actions can be applied, describe the same responsibility in
domain terms:

```markdown
Interpret the record from its current authoritative state. The available
actions are to keep it unchanged, request a refresh, or escalate it for review.
The policy may make a non-empty subset of that catalog available for a
deployment; an omitted action is unavailable.

Continue automatically only when exactly one safe action remains overall and
it is already authorized. A safe action that is not already authorized still
requires participant confirmation, even when it is the only safe action. If
judgment remains, ask the participant to choose among the safe alternatives or
clarify the intended outcome, then reassess from current state. Do not change
the record while the decision is pending, and do not reuse an earlier choice
after the state changes. Keep only the most recent clarification, and discard
it as well if the state changes again before application.
```

The author states the closed actions, the authority policy, and whether
participant clarification is meaningful. The author does not describe state
tokens, option tokens, locks, checkpoint records, response transport, or
adapter classes. Canonicalization derives those mechanics. Participant
guidance can refine interpretation but cannot add an action, permission,
resource scope, or authority.

When a responsibility consumes a source collection, state its selection, coverage, and unavailable-source behavior at the workflow's level of abstraction:

```
Each analyst considers every enabled source of its kind and accounts for each selected source in its result.

All required sources must be available. Otherwise, report the unavailable sources and stop without producing a result.

Unavailable optional sources do not block the assessment. Record the missing coverage and reflect it in the assessment confidence.
```

### Deterministic actions and optional error recovery

The human-readable skill describes what must happen, not which runtime class performs it. No special syntax is required to distinguish a controlled deterministic effect from an LLM tool call. Canonicalization uses the responsibility described by the instruction:

*   If the operation, target, and mechanical result are fully specified before execution, translate it into a deterministic Harness effect.
*   If execution requires interpreting content, choosing what to inspect, generating material, judging alternatives, or adapting the next action semantically, translate it into a model-facing step or subagent.
*   If both readings are technical lowering choices, canonicalization chooses one from the language conventions and available evidence. It asks the author only when both readings represent materially different business or policy meanings with different consequences.

For example, “Read `config.yaml`” identifies a deterministic read. “Inspect the repository and determine which configuration governs this request” requires an agent because file selection and relevance depend on interpretation. “Write the validated `Result` to `result.json`” is deterministic; “edit the project until the tests pass” is an adaptive agent responsibility.

A deterministic effect is exact and fails hard by default:

```
1. Read `config.yaml`.
```

The absence of a recovery clause means that the exact missing or invalid target is not silently replaced, broadened, or delegated to an agent.

Deterministic recovery is expressed as an ordinary failure branch immediately associated with the action:

```
1. Read `config.yaml`.
   If it is missing and exactly one `config.yml` exists in the same directory,
   use that file instead. Otherwise stop and report the error.
```

Recovery that genuinely requires judgment names an isolated recovery subagent and bounds its choice:

```
1. Read `config.yaml`.
   If the exact read fails, have an isolated recovery subagent choose a
   replacement only among `.yaml` and `.yml` files in the same directory.
   Retry once. If there is no single defensible choice, stop and report the
   original error.
```

The human-readable clause states only behavior-changing decisions that cannot be inferred safely:

*   which failure may start recovery;
*   what may change and which candidates are in scope;
*   whether recovery is deterministic or requires an isolated subagent;
*   the retry limit;
*   what happens when recovery is impossible or ambiguous.

It does not mention `EffectBackend`, `with_recovery`, SDK sessions, path-containment checks, or audit events. Canonicalization and the Harness supply those mechanics. The recovery subagent proposes a typed choice from candidates prepared by the Harness; it does not receive broader access or execute the repaired system operation itself. The exact effect and recovery mechanics are defined in the [deterministic effects API contract](deterministic-effects-api-contract.md).

## 3\. From human-readable skill to executable IR

Section 2 defined what a person writes. This section explains how that meaning is made explicit as connected data contracts, Python control flow, model-facing operations, and deterministic effects.

### Type system

Pydantic is the canonical type system: generated Python models define the exact shape and local validation rules of inputs and results.

*   Inputs, intermediate results, and outputs reference named Pydantic models.
*   Pydantic owns structural validation and constraints local to one typed value.
*   The accepted canonical human-readable skill and any domain material explicitly supplied by the author own business meaning. Pinned project evidence may recover the structural shape and existing integration contract for that meaning. Generated `contracts.py` formalizes those inputs and the canonicalizer's recorded technical decisions but does not create new domain requirements. The original source wording remains traceability evidence, not an alternative input to formal generation.
*   A value that requires confidentiality uses a Pydantic secret type or an explicit serialization/audit exclusion. A field name such as `token` does not implicitly make an ordinary `str` secret; secrecy must remain part of the typed contract when the value is passed onward.
*   The human-readable skill refers to model names without repeating their fields.
*   Canonicalization generates explicit imports from the module declared by `metadata.types`, allowing editor navigation and type assistance in the IR.
*   Static validation verifies that every imported name exists in that module, while the Harness validates concrete values before they are consumed by subsequent operations.
*   Relations between inputs, outputs, and side effects become explicit IR conditions and pattern contracts enforced by Python, the Harness, and its backend boundary.
*   When a later step adds required information to an earlier result, use distinct stage types rather than weakening one model with optional fields. For example: `DraftRecord` → `ValidatedRecord`.
*   For a closed set of mutually exclusive alternatives that all belong to one
    official domain result, place a discriminated union inside the output
    model. For example, `VerificationResult(outcome=Passed() |
    Failed(issues=...))` records either conclusion in the same official
    artifact. A branch that produces no official result is an execution state,
    not an output variant. Keep independent dimensions as separate typed fields
    or nested unions instead of creating a separate variant for every possible
    combination. Conditional validators remain appropriate for invariants that
    cannot be expressed structurally.
*   Do not use a domain enum as a substitute for open semantic interpretation.
    Observed labels and facts may remain bounded strings or typed evidence while
    the actions available to the workflow remain a closed union.
*   A Pydantic contract requested directly as model structured output has an object at its JSON Schema root. When alternatives carry different fields or invariants, place their discriminated union inside that object—for example `VerificationReport(verdict=Passed() | Failed(issues=...))`. This preserves both SDK compatibility and structural validation; it is a general transport rule, not a domain-specific wrapper convention.

Other type systems such as Zod are outside this language contract and require an explicit conversion layer.

### Intermediate representation

The intermediate representation is executable Python restricted by ordinary Python tooling and an IR-specific static validator. Its executable status is intentional: Python directly owns typed values, conditions, loops with explicit limits, participant-gated loops, assignments, and returns. A participant-gated loop must begin every iteration with one typed interaction, so it cannot run freely while waiting for a human decision. The accepted subset excludes uncontrolled direct I/O, processes, networking, reflection, dynamic imports, and undeclared effects. It may invoke only the closed set of typed deterministic effects exposed by active Harness patterns.

The IR instantiates a backend-neutral `Harness`. Decorators register formal model-facing operation definitions and replace declarative operation placeholders with typed asynchronous wrappers. Typed deterministic effect requests are executed through the Harness without becoming decorated model operations. `Harness.run(...)` binds independently selected agent and effect backends only for that run and executes the Python workflow directly.

Generated Python is a thin control skeleton. It owns typed data flow,
predictable ordering, bounded loops, conditions, checkpoint boundaries,
scheduling, permissions, and deterministic dispatch. Model-facing operations
retain interpretation, semantic classification of open evidence, planning,
proposal generation, and adaptation. Python may branch on genuinely closed
domain decisions and universal control outcomes; it must not manufacture an
exhaustive state machine for situations the human skill deliberately leaves
open.

An adaptive model operation returns one object-root Pydantic model whose
`outcome` field is a discriminated union of:

*   `Proceed[Proposal]`: a proposal may continue to deterministic validation;
*   `NeedsParticipantDecision[Decision]`: safe continuation requires a
    participant choice or bounded guidance; or
*   `NoSafeContinuation[Details]`: nothing can be proposed inside the declared
    evidence and authority.

```python
@harness.subagent
async def interpret(
    request: Request,
    observation: Observation,
) -> AdaptiveControlOutcome[Proposal, Decision, StopDetails]:
    """Interpret $observation under $request without applying a change."""
    raise NotImplementedError
```

This is a model-operation result, not a Runtime execution response and not an
effect authorization. `NeedsParticipantDecision` does not itself create
`NeedsInput`; the workflow maps it through the declared participant pattern.
Likewise, `Proceed.proposal` cannot be sent directly to an authoritative
effect. Deterministic application policy must validate it first.

Application-specific deterministic capabilities use responsibility-specific
abstract ports in generated `scripts/ports.py`. A runtime-prepared immutable
dependency aggregate is separate from human inputs. A port may group one or
more cohesive methods under the same application responsibility. Each method
accepts one keyword-only Pydantic request, returns one typed result, and
declares its own name-independent safety role and invocation policy:

```python
from typing import Protocol, runtime_checkable

from human_skill_runtime import dependency_role


@runtime_checkable
class Observer(Protocol):
    @dependency_role(
        "observation",
        timeout_seconds=10.0,
        retry_safe=True,
        max_attempts=3,
    )
    async def fetch_current(
        self,
        *,
        request: ObserveRequest,
    ) -> Observation: ...

    @dependency_role("observation")
    async def fetch_history(
        self,
        *,
        request: HistoryRequest,
    ) -> History: ...


@runtime_checkable
class Policy(Protocol):
    @dependency_role("proposal_validation")
    async def check_candidate(
        self,
        *,
        request: ValidationRequest,
    ) -> Validation: ...


@runtime_checkable
class Writer(Protocol):
    @dependency_role("atomic_authorized_apply")
    async def commit_authorized_action(
        self,
        *,
        request: AuthorizedApplyRequest,
    ) -> ApplyResult: ...


observation = await dependencies.observer.fetch_current(request=observe_request)
validation = await dependencies.policy.check_candidate(
    request=validation_request,
)
applied = await dependencies.writer.commit_authorized_action(
    request=authorized_request,
)
```

The decorator role, not a domain method name, carries the safety meaning.
`observation` reads authoritative facts and state without mutation;
`proposal_validation` may consume an untrusted adaptive proposal and returns
trusted policy validation; `atomic_authorized_apply` consumes that validation
plus a participant-selected or pre-authorized option, revalidates current
state, and applies at most once atomically. `operation` marks a typed
deterministic dependency with none of those special adaptive privileges. The
validator therefore recognizes renamed methods such as `check_candidate` and
`commit_authorized_action` without weakening the authorization proof.

Every dependency method has a positive timeout; the Runtime default is 30
seconds when the declaration does not override it. There is no implicit
retry. A method is retryable only when its declaration explicitly sets both
`retry_safe=True` and `max_attempts` above 1; the Runtime rejects more than five
attempts. Only invocation failures and Runtime-owned timeouts are retried.
Request or result validation failure and cancellation are never retried. An
`atomic_authorized_apply` is always single-attempt; recovery uses its durable
result and state revalidation rather than automatic reinvocation. Cancellation reaches the adapter and
then propagates. A completed dependency boundary is checkpointed and replayed
on continuation instead of invoking the adapter again.

Each concrete adapter supplies a stable, non-empty
`dependency_scope_fingerprint`. The composition root derives it from every
authority, configuration, and policy choice that can change the method's
meaning or result; it must not contain a per-process loader nonce. The Runtime
hashes these values with the declared aggregate and invocation policies. A
continuation fails closed before replay when that aggregate scope has changed.

Pre-authorization uses the same explicit-role principle for contract fields.
The result of `proposal_validation` marks its policy-selected value with
`Annotated[..., AuthorizationRole("preauthorized_source")]`; the request of
`atomic_authorized_apply` marks exactly one receiving field with
`Annotated[..., AuthorizationRole("authorized_selection")]`. The validator
proves a typed value flow between those roles. Field names, variable names,
discriminator labels, and control-branch strings carry no authority.

Generated IR cannot construct concrete adapters, look up a dependency by
string, pass arbitrary callables, or treat `Proceed.proposal` as
`authorized_request`. Concrete implementations are selected only by the
composition root.

A participant interaction is another typed boundary, not a model operation.
IR declares an `Interaction` with Pydantic request and response contracts. The
request contains a `kind`, a human prompt, and safe structured context; the
response describes exactly what the workflow can accept. For example:

```python
decision = await harness.request_input(
    interaction=Interaction(
        id="review.overlap_decision",
        request=OverlapDecisionRequest,
        response=OverlapDecision,
    ),
    request=OverlapDecisionRequest(
        kind="decision",
        prompt="Choose how to proceed with the overlap.",
        context=OverlapDecisionContext(overlap=overlap),
    ),
)
```

The Harness validates and checkpoints this boundary, then returns
`NeedsInput` to a non-interactive host. The host alone transports the request
to a UI, CLI, API, or other participant channel and later supplies the typed
answer with the opaque resume token. This remains backend-neutral: Claude
Agent SDK neither asks the participant nor owns continuation state.

#### Participant-guided adaptive continuation

An adaptive authoritative workflow keeps three outcome layers distinct:

1. The model control outcome is `Proceed`, `NeedsParticipantDecision`, or
   `NoSafeContinuation` inside `AdaptiveControlOutcome`.
2. The Runtime execution response is `Succeeded`, `NeedsInput`, `Blocked`,
   `CompletedWithoutResult`, `Cancelled`, or `Failed`.
3. The atomic application outcome is `Applied`, `StateChanged`, or
   `NoLongerSafe` inside `AtomicApplyResult`.

`NoSafeContinuation` is a model judgment within declared evidence and
authority, not a technical exception. Generated workflow control maps it to
the controlled stop required by the human skill. Participant cancellation is
`Cancelled`; invalid configuration, programming defects, and unexpected
infrastructure failures remain `Failed` and are never converted into a
question for the participant.

The formal flow is:

```text
typed observation with an opaque state token
  -> model interpretation and proposal inside closed action capability
  -> deterministic proposal validation
  -> pre-authorized option
     or typed participant choice / bounded guidance
     or controlled stop
  -> atomic state-and-option revalidation and apply
  -> Applied, StateChanged, or NoLongerSafe
```

Observation returns authoritative facts and an opaque `StateToken`, but the
model receives only the safe facts needed for interpretation. Deterministic
policy checks proposal types, action capability, permissions, scope,
invariants, current facts, and configured authority. Every feasible action is
represented by a `ValidatedOption` whose opaque token is bound to the observed
state, action, resource scope, policy version, workflow package, and expiry.
A raw model proposal is never an authorized apply request.

Automatic continuation is allowed only when deterministic validation finds
exactly one meaning-preserving action in the safe set overall and that action
is already authorized. For a closed action catalog, validation assesses every
declared action against current state and policy. Model proposals may guide the
assessment but cannot define its completeness: one proposal is not evidence
that only one safe action exists overall. Otherwise a
typed interaction exposes safe option identifiers and descriptions. It does
not expose the state token or validated-option token to the model, participant,
UI, report, or audit. The completed interaction selects one option already
held in the trusted checkpoint; free-text guidance selects none.

Guidance is length-bounded by a Runtime-owned contract and returns to a
model-facing operation. The workflow reobserves authoritative state and
validates every revised proposal again. The reassessment loop has an explicit
Runtime-owned maximum and a deterministic controlled stop when exhausted.
Guidance cannot expand the action catalog, tools, resource scope, permissions,
or authority.

Canonical IR activates that bound with
`Harness(adaptive_resolution=AdaptiveResolutionLimits(...))` and iterates with
`harness.adaptive_resolution_attempts()`. The helper takes no dynamic bound:
the Runtime default and absolute maximum are three resolution attempts, with
the initial resolution counted as attempt 1. Generated code may configure a
smaller positive limit. The Runtime rejects a larger value, and repeated uses
of the helper in one run share the same attempt counter rather than creating a
new allowance.

Applying an option is one application-port call. The IR passes the complete
trusted validation result, the current state token, and only the selected safe
option identifier. It does not extract an authority token or reconstruct the
action. Under the relevant lock, the adapter resolves that identifier within
the supplied validation result, verifies the matching state and option tokens,
and only then performs its first mutation. `Applied` contains the typed receipt,
including the action actually applied. `StateChanged` and `NoLongerSafe`
perform no mutation. `StateChanged` starts a bounded fresh observation and
interpretation cycle; the previous participant answer and option authority are
discarded rather than reused. While participant judgment is pending, the
disputed resource remains unchanged, although completed independent boundaries
remain checkpointed and replayable.

An apply port that changes several authoritative resources is one logical
operation but not automatically one atomic operation. Before its first
mutation it records a host-owned transaction containing the validated request
fingerprint, preconditions, desired state, and stable timestamp. Each resource
is applied with compare-and-apply semantics; a retry resumes the same plan,
returns the persisted typed receipt after commit, and fails closed if external
state no longer matches either the recorded precondition or desired state.
This transaction mechanism belongs to the application adapter, not the human
skill or model.

The following example illustrates the canonical IR constructs; its domain types and function names are not part of the language:

```python
from contracts import (
    Accepted,
    Analysis,
    Context,
    Rejected,
    Request,
    Result,
    Review,
    collect_issues,
)
from human_skill_runtime import FileRead, Harness

harness = Harness()


@harness.step(capabilities=(FileRead,))
async def prepare_context(request: Request) -> Context:
    """
    Prepare the context needed to evaluate $request.
    """
    raise NotImplementedError


@harness.subagent(capabilities=(FileRead,))
async def analyze(request: Request, context: Context) -> Analysis:
    """
    Analyze $request using $context.
    """
    raise NotImplementedError


@harness.subagent(capabilities=(FileRead,))
async def review(request: Request, context: Context) -> Review:
    """
    Independently review $request using $context.
    """
    raise NotImplementedError


@harness.workflow
async def example(request: Request) -> Result:
    context = await prepare_context(request=request)
    first, second = await harness.parallel(
        analyze(request=request, context=context),
        review(request=request, context=context),
    )

    if first.accepted and second.accepted:
        return Result(outcome=Accepted(first=first, second=second))

    return Result(
        outcome=Rejected(issues=collect_issues(first=first, second=second)),
    )
```

Semantics:

*   `@harness.workflow` marks the asynchronous restricted-Python workflow. `@harness.step` declares a model operation in its current backend context; `@harness.subagent` declares one in a fresh isolated context.
*   A controlled deterministic effect is a typed Harness request, not a decorated model operation. An ordinary deterministic helper remains a plain typed Python function.
*   An operation signature declares typed inputs and output; its docstring is the instruction. `$parameter` and `$parameter.field` are formal references to model-facing arguments, which are supplied as named structured context rather than interpolated into instruction text.
*   Every declared value has an explicit consumer in prompt references, Python data flow, a constructor, binding, policy, effect, or return. Runtime-only values are consumed by their declared bindings and cannot be referenced by a prompt when their type forbids model exposure.
*   Awaiting a step or subagent executes that operation and returns its Pydantic-validated result. `harness.parallel(...)` executes an accepted, explicitly limited group of isolated operations concurrently, preserves declared result order, and fails without leaving unfinished sibling work. The selected executable profile determines how many parallel operations are permitted.
*   Assignments, calls, field access, conditions, explicitly limited loops, participant-gated loops, and returns retain their accepted Python semantics; the Harness does not reinterpret them.
*   IR imports Pydantic contracts, the universal Harness, and abstract capabilities explicitly. Concrete SDK tools and options remain backend bindings.
*   Agent capabilities and deterministic effect permissions use separate types and are checked independently before execution. Permission for a host-side workspace read, for example, does not expose a model `Read` tool.
*   Runtime-prepared values enter through explicit Harness contracts rather than ambient process state. Universal operational reporting belongs to the Harness core; skill-specific evidence and artifact policy remains optional.
*   Every Pydantic constructor field is supplied explicitly, including fields with defaults. The validator neither relies on those defaults nor fills fields from similarly named values in scope.

Every value consumed by an operation must be available from the workflow input, a preceding result, or an activated Harness pattern. Python type checking and the IR validator must reject unresolved names, incompatible connections, unsupported constructs, normal completion paths that do not return the declared workflow output, and no-output branches that do not use a typed controlled stop. The Harness rejects unavailable agent capabilities or deterministic effect permissions before the first relevant action.

### How responsibilities become IR operations

A step represents one workflow-visible responsibility, not every action verb or internal operation in its instructions. Canonicalization creates a separate operation when responsibility changes, model context must be isolated, a result needs separate validation, or an external interaction needs its own permissions and error handling.

One responsibility may contain several related actions when the workflow consumes only their combined result. A non-subagent model responsibility becomes `@harness.step` and retains the current backend context; an explicit delegation becomes an isolated `@harness.subagent`. Loops, branches, and parallel groups remain Python control flow around those operations. A fully specified external action becomes a typed effect rather than a model operation.

Headings, numbering, and lists do not create steps by themselves. Canonicalization chooses technical operation boundaries from the described responsibilities, language conventions, and available evidence. It asks the author only if the boundary exposes a genuinely unresolved business or policy decision with materially different consequences.

### Official output, controlled stops, and execution failures

The explicit typed `return` is the source of truth for the official domain
result. The Harness validates the returned Pydantic model, serializes the same
value to YAML, and records its production in the audit stream. Side-effect
receipts may be presented alongside the result but do not become fields of the
domain output merely because the runtime created them.

An expected branch that finishes without the declared output uses a typed
Harness termination state. Examples include required sources being unavailable
or a requester deciding that no further work is needed. Generated IR must not
invent a partial output model or use a generic exception for such a branch.
The termination carries a stable reason code and typed safe details for the
execution response and audit.

A generated branch uses one of two universal terminal records. `CompletedStop`
means the workflow deliberately concluded without a domain result;
`BlockedStop` means a named precondition prevented the result and also states
whether retry may help. For example:

```python
if not sources.all_available:
    harness.stop(
        BlockedStop(
            kind="blocked",
            reason="requirements_sources_unavailable",
            details=UnavailableSources(
                sources=sources.issue_identifiers,
            ),
            retryable=True,
        )
    )
```

The details are an inline Pydantic model. The reason is a stable code rather
than UI prose; the caller response and renderer derive safe wording from it.

Unexpected failures such as invalid invocation configuration, failed
validation, an unavailable runtime capability, or failure of a declared policy
mechanism are typed Harness execution errors. A controlled stop is not
converted into an execution error merely because no output was produced.

An exact deterministic effect failure becomes a typed execution error unless
the human-readable skill explicitly associates a recovery clause with it.
Exhausted or invalid recovery preserves the original failure unless the skill
explicitly maps that condition to a controlled stop or still produces a valid
official domain result.

The core IR, step, and final-result rules above apply to every workflow. The next three sections define optional reusable patterns for file-backed inputs, source coverage, and managed workspaces; they apply only when the human-readable skill activates the corresponding behavior.

### Optional pattern: how file inputs become IR

Canonicalization expands a file shorthand into an explicit typed input binding. The Harness resolves the declared path beneath the host-selected project root, decodes the file, applies a small deterministic conversion function (an adapter) only when the file's location affects interpretation, and validates the resulting Pydantic value before workflow execution. Steps and subagents receive the converted value rather than the raw file.

The shorthand is exact: the required file cannot be replaced by an invocation value, another extension, or a neighboring file. Any fallback uses the same explicitly limited recovery rules as other deterministic effects and cannot broaden the project root or bypass adaptation and validation.

APIs, environment values, secrets, databases, optional files, and overridable values require their own typed source rules rather than inheriting file semantics. The complete generated IR form, adapter restrictions, validation checks, failures, and audit requirements are defined in the [file-backed input pattern](reference/file-input-binding-pattern.md).

### Optional pattern: source coverage and isolated source use

A typed source collection is a catalog, not an implicit usage policy. The skill identifies the responsibility that consumes it and states selection, required coverage, permitted non-success behavior, and who owns the resulting coverage record. Canonicalization attaches those semantics to the corresponding typed operation parameter; it does not infer them from field names.

Every source has a stable typed identity. Every field that can affect selection, access, scope, or source-specific instructions is declared in Pydantic. Before model-facing work, the runtime exposes only selected sources and declared fields. Coverage is then checked deterministically by comparing selected identities with typed recorded outcomes, called dispositions in the generated API, and their evidence.

A source descriptor says what to inspect; it does not grant access. The host
owns source authority in `InvocationContext`: the project root is available by
default, while any additional filesystem roots are explicitly authorized as
read-only. Configuration can select a neighboring repository only when the
host independently authorizes it. A missing non-filesystem connector is
recorded as unavailable rather than treated as model-readable merely because
its descriptor is well formed.

The active policy owns its selector and permitted outcome vocabulary. The language core does not assume that every catalog has an `enabled` flag or one universal set of outcomes.

#### Source-specific instructions

Source-specific instructions are activated explicitly; a similarly named field has no implicit behavior. Their content is model-facing only inside a fresh context limited to one source, its explicitly limited source task, and the operation's explicitly referenced non-source inputs. It never becomes a global prompt or a sibling source's context.

These instructions remain subordinate to the skill, request, safety policy, selection, coverage, permitted outcomes, and permissions. They cannot expand access. Load failures become typed source availability evidence or an execution failure according to the declared policy, and audit records never contain the instruction content.

#### Checking source availability before use

When availability is a workflow precondition, canonicalization emits an explicit deterministic check before dependent model work. It returns `SourcePreparation[T]`: a complete, non-overlapping, ordered partition of available, unavailable, and invalid selected sources plus typed evidence. Expected unavailability is data that may drive a declared workflow-ending branch; failure of the checking mechanism is an execution failure. Human-facing branches use safe properties such as `all_available`, `issue_count`, and ordered `issue_identifiers`; opaque prepared-source contents are not ordinary workflow data.

The source-scoped operation receives the complete `SourcePreparation[T]`, not only its `.available` collection. `@harness.source_policy` verifies that its identity, instruction, and probe declarations match preparation, then runs one fresh model context for every available source and deterministically carries unavailable and invalid entries into `SourceCoverage[O]`. The workflow gives that complete coverage to an ordinary domain step or subagent that synthesizes the requested assessment. A descriptor-only probe grants no filesystem authority; a path probe grants only the pinned source scope. No dependent operation may silently reselect, recheck, or reload a source.

When the official result reports source coverage, a trusted validation dependency
compares it with the runtime-observed projection of `SourceCoverage` and with
typed connector receipts. A model may summarize what it found and explain the
effect of missing coverage, but it cannot change whether a configured source
was actually searched, unavailable, or invalid.

The exact policy constructors, source isolation, preparation, evidence, validation, and IR example are defined in the [source coverage pattern](reference/source-coverage-pattern.md).

### Optional pattern: how workspace requirements become IR

Canonicalization turns the author-facing workspace requirement into a managed workspace specification at the point where its identity and lifecycle are known. `default` creates a unique run-scoped workspace. A static custom pattern is complete and receives no implicit suffix. Input- or result-dependent patterns remain concise in frontmatter but lower to explicit typed `resolve_workspace(...)` data flow in IR.

All workspaces resolve beneath the trusted project root. The Harness validates path safety, performs `create`, `open`, or `ensure` according to the declared lifecycle, acquires exclusive run ownership, and injects the runtime-owned workspace handle. A path or lookalike object supplied by a caller or model grants no permission to perform effects.

The Harness preserves the workspace and records both the requested operation (`create`, `open`, or `ensure`) and the observed outcome (`created` or `opened`), together with its final state and declared artifacts after success, failure, or cancellation. It then releases the lease during cleanup. A separately declared lifecycle policy is required to delete the workspace. Exact resolution fails hard unless the skill declares explicitly limited recovery. The detailed rules for static and data-dependent workspaces, access rights, lifecycle, effects, and audit are defined in the [managed workspace pattern](reference/managed-workspace-pattern.md).

## 4\. Validating and running the IR

Sections 2 and 3 defined the authored skill and its executable form. This section defines the checks required before execution and the responsibilities of the runtime and concrete backends during a run.

### Validation and execution pipeline

The execution pipeline separates validation, deterministic Python execution, universal operation semantics, and concrete backends:

```
canonical SKILL.md + optional author references + pinned project evidence
  + generated contracts + generated IR
  → py_compile + type checker + IRValidator
  → executable Python workflow
  → universal Harness
  ├→ selected EffectBackend for declared deterministic effects
  ├→ selected AgentBackend for model-facing operations
  └→ runtime-injected typed application dependencies
```

The build validator checks the canonical `SKILL.md` together with the complete formal candidate and includes it in the candidate fingerprint. The publisher writes that same validated `SKILL.md`; it never substitutes the original source copy. Publication stages and flushes the complete package, then atomically exchanges it with an existing package under a host-owned lock. A reader holds the matching shared lock while validating and importing, so it observes one complete accepted version rather than a missing or mixed directory. No generated executable code is loaded and no model or external-system operation may begin until the complete selected validation profile passes.

Every generated or repaired formal candidate passes the same technical validation before publication. A bounded technical repair may address concrete validator diagnostics, after which validation runs again. Semantic review runs only on a technically accepted candidate. If semantic review requires a replacement, that replacement re-enters the technical validation and bounded technical-repair gate before semantic review is repeated; semantic correctness never exempts generated code from syntax, imports, formatting, type, or IR-policy checks.

The atomic rename or exchange is the publication commit point. A failure before
that point returns `Failed` and leaves the previous package visible. After that
point the publisher must not report `Failed`, because the accepted package may
already have been observed by readers; a best-effort parent-directory flush
may strengthen crash durability but cannot roll publication back.

### Validation before execution

Validation combines valid Python syntax, static type consistency, the restricted core IR profile, and every activated pattern's rules. Together they verify that inputs and results connect, constructors and operation calls are complete, control flow is supported, capabilities and permissions are declared independently, model-facing references use only fields declared by their types and not explicitly excluded from model use, and generated code contains no undeclared execution path or effect.

These checks cover the complete script surface selected by the profile, including generated contracts, approved deterministic helpers, adapters, executable IR, and every construct that can run while modules are imported. An unexpected Python module is rejected rather than merely ignored. Passing validation establishes compliance with the structural and policy rules of the selected language profile. It does not prove prompt quality, domain correctness, model reliability, or correctness of external systems.

The exact allowed Python elements, command, and pattern-specific checks are maintained in the [executable IR validation and runtime rules](reference/executable-ir-acceptance-and-runtime.md).

### Universal Harness guarantees

After validation, the Harness loads and executes the restricted Python workflow. It validates values at workflow, operation, effect, dependency, and final-result boundaries; binds the selected agent backend, effect backend, and typed dependencies to one run; and checks agent capabilities, deterministic effect permissions, and dependency authority independently before execution. Missing or denied support stops execution, and no backend or dependency can substitute for another.

Typed application dependencies are supplied only by the composition root
through `Harness.execute(..., dependencies=...)`. The generated workflow
receives its declared immutable dependency aggregate as a Runtime-prepared
final parameter; it is not a human-skill input and a caller cannot replace it
through the input payload. Runtime middleware wraps each direct keyword-only
port invocation to validate its request and result, enforce timeout and
cancellation, record a dependency lifecycle, and checkpoint a completed
boundary for replay. Generated IR sees the declared protocols, never the
concrete adapter or middleware implementation.

This is the required complete standard architecture. Runtime preflight checks
the exact aggregate and all declared methods before model work. The middleware
then provides request/result validation, per-method timeout, explicit bounded
retry for retry-safe invocations, lifecycle reporting, cancellation
propagation, and checkpoint replay.

The validated loader also returns the immutable package fingerprint as a
public composition value. A composition root can therefore bind application
authority tokens to the exact accepted skill package without reading private
Harness state or inventing a second workflow identity.

Python retains ownership of assignments, conditions, explicitly limited loops, scheduling positions, value construction, and returns. The Harness invokes typed operations, runs declared independent work in parallel, cancels unfinished siblings when one fails, prepares runtime values, controls effects, and performs lifecycle cleanup. A backend executes one declared operation or effect; it never interprets the workflow algorithm.

On success, the Harness returns the validated output model together with its
canonical YAML serialization. On a controlled stop, failure, or cancellation,
it returns no domain output. These states are exposed through the universal
execution response described below.

Canonical YAML preserves the declared order of Pydantic model fields and sorts
keys inside ordinary mapping values recursively. Equivalent mapping insertion
orders therefore produce identical bytes and hashes. When a resumed run finds
the declared output path already containing those exact bytes, materialization
is an idempotent success; different existing bytes remain a conflict and are
never overwritten.

### Execution responses for callers and user interfaces

The official domain output and the runtime response are separate contracts.
The Harness exposes a generic `ExecutionResponse[T]` with six states:

*   `Succeeded` contains the validated `T`, its YAML materialization, the run
    identifier, and a safe audit reference.
*   `CompletedWithoutResult` records an expected successful conclusion that
    intentionally produced no `T`.
*   `Blocked` records a stable reason, typed safe details, and whether a later
    retry may succeed.
*   `NeedsInput` contains the safe typed participant request, its response
    schema, an expiry time, and an opaque resume token. It contains no domain
    output and does not mean that the workflow failed.
*   `Failed` records a safe error code, a user-facing message, and retryability
    without exposing internal exceptions, paths, prompts, or secrets.
*   `Cancelled` records that execution was intentionally interrupted.

The latter five states do not contain `T` or a YAML output artifact. UI
renderers derive deterministic messages from the state, reason code, and safe
details. They may also present safe projections of effect receipts—for example
that a workspace or branch was created—without adding those operational facts
to the domain output. An optional model-written explanation is presentation
only: it cannot change status, result, retryability, or error identity.

The continuation checkpoint is stored by the host and bound to the validated
workflow package, original inputs, project scope, completed typed boundaries,
pending interaction, and expiry. Resuming atomically claims it, validates the
answer, and replays completed boundaries instead of repeating them. An invalid
answer returns `NeedsInput` again with safe validation diagnostics and the same
token. Concurrent resume attempts fail closed. Participant cancellation returns
`Cancelled`; expiry, a mismatched workflow/input/scope, or an invalid token
returns a safe `Failed` response. A failure after a valid answer releases the
same checkpoint for a controlled retry without discarding completed work.

For participant-guided adaptive continuation, the trusted checkpoint also
retains the exact validated options needed to map a safe participant-facing
option identifier back to its opaque authority token. These values are
checkpointable capabilities, not participant payloads. They are excluded from
model arguments, safe execution responses, reports, and audit projection. A
resume may use only the option set bound to its own observation and interaction;
stale, expired, forged, out-of-scope, or concurrently consumed authority fails
closed before mutation.

The checkpoint cannot make an arbitrary external mutation exactly once across
a process crash. Mutating application ports therefore keep their own idempotency or
transaction receipt, and deterministic effects use their declared audit and
reconciliation contract. The Harness never treats an unrecorded external
outcome as completed merely because execution had started it.

A resumed run holds an exclusive host lease for its opaque continuation token.
The persisted `running` state is therefore evidence of a live owner only while
that lease is held; after a process crash a later host may reclaim it and replay
the recorded boundaries. The checkpoint is deleted only after the terminal
report has been published. If publication fails, the checkpoint returns to a
retryable waiting state and already recorded effects or dependency calls are replayed
rather than executed again.

A newly created continuation token is not considered delivered until its first
`NeedsInput` report is published. If that publication fails, the host deletes
the fresh checkpoint because no caller can know its token. For a token already
delivered by an earlier `NeedsInput`, a later publication failure preserves the
checkpoint in the retryable waiting state.

### Deterministic audit events

Operational auditing is a universal Harness facility. The Harness formulates
events mechanically; a skill, agent backend, model, effect implementation, or
UI cannot supply free-form text as the authoritative audit record. The event
catalog is a closed schema distinguished by event kind and lifecycle status,
covering run, operation, parallel, effect, dependency, interaction, source, workspace, output,
controlled-stop, failure, and cancellation transitions. Validation rejects
unknown fields, statuses that do not belong to a kind, and incomplete
kind-specific identities or receipts.

Every event contains a schema version, run identifier, stable logical position,
attempt number, event kind, status, and typed payload. A host-owned clock adds a
UTC timestamp, while a monotonic clock measures durations. A run-local recorder
adds an observed sequence number. The sequence records the order in which
events reached the recorder; the logical position records their stable place in
the workflow. Parallel completion order is therefore preserved as an observed
fact without making the canonical workflow structure unstable.

Input values, operation results, and effect receipts enter an event only
through a deterministic audit projection. The projection follows declared
Pydantic fields, removes audit-excluded values, redacts typed secrets,
normalizes paths and unordered collections, applies size limits, and rejects
unsupported or cyclic data. It never uses `repr()`, object addresses, or model
authored summaries as structured evidence.

State and validated-option tokens are always audit-excluded. Participant
guidance may also be audit-excluded when its contract can carry sensitive
free text. The run-local recorder remembers string values removed by typed
audit exclusions and redacts their later echoes from model outputs, tool
events, and other event payloads. Exclusion therefore protects a value after
it has crossed a model boundary, not only at its original field. The audit
still records the typed observation, interpretation, validation, interaction,
revalidation, apply, and terminal lifecycles in order; redaction removes
authority-bearing or sensitive values without removing the event identity or
outcome.

The recorder validates each event and serializes it canonically as one UTF-8
JSON object per line through a single run-local writer. Field names, encoding,
normalization, and newline behavior are fixed. The raw journal retains observed
sequence; a final report may additionally sort a safe projection by logical
position. Production timestamps and external outcomes differ between runs, but
event formulation, projection, and serialization remain deterministic. Tests
use a fixed clock when byte-identical evidence is required.

Before an effect, the recorder persists a typed `started` event with a stable
operation identifier. It then records exactly one typed terminal observation
when the effect succeeds, fails, or is cancelled. If execution stops between
the external effect and its terminal event, recovery treats the unmatched
`started` event as incomplete and reconciles it with actual external state; it
does not assume that the effect did or did not happen.

The audit journal is evidence about execution, not the source of truth for an
external resource. A Git branch, workspace, or state file remains authoritative
in its owning system; the corresponding audit event carries a typed receipt
that identifies what the Harness requested and observed.

The full audit journal is not safe for arbitrary persistence or display.
Its canonical raw JSONL may be stored only in the trusted run audit sink.
Execution responses, UI renderers, and less-trusted external sinks receive only
an explicitly limited and redacted projection that honors typed secrets,
exclusions, path redaction, deterministic ordering, and size limits.
The trusted sink is host-owned and remains outside the governed project
worktree so journal creation cannot violate the workflow's own clean-tree
precondition or become model-readable source content.

The exact division of responsibilities inside the runtime, reporting mechanics, and backend requirements are maintained in the [executable IR validation and runtime rules](reference/executable-ir-acceptance-and-runtime.md). Controlled filesystem effects and recovery are specified by the [deterministic effects API contract](deterministic-effects-api-contract.md).

### Claude Agent SDK as a concrete backend

Claude Agent SDK is one conforming implementation of the agent-backend contract. It receives a declared model-facing operation and validated named values, maps backend-neutral capabilities to explicitly visible Claude tools, requests the declared structured result, and returns only a value that passes the operation's Pydantic contract. Current-context operations may resume their run-local SDK session; isolated subagents start a fresh one. Scheduling remains in Python and the Harness.

A backend adapter preserves an explicit terminal error even when the transport
subsequently exits with another exception. It must not replace a specific
upstream failure with a generic stream error merely because process shutdown
follows the terminal. For example, a model connection closed before completion
is reported as the retryable `upstream_connection_closed`; it never becomes a
domain result or a successful partial structured value.

Operation boundaries must also account for bounded execution time, not only
schema validity or byte limits. A single responsibility may have individually
acceptable input and output sizes yet exceed an upstream request lifetime when
both require substantial model work. When a formal result consists of several
independently valid artifacts, canonicalization may emit separate typed model
operations and assemble their validated outputs deterministically. This is a
general reliability boundary, not a reason to expose token, transport, or SDK
mechanics in the human-readable skill.

Model-visible input is built only from declared Pydantic fields that are not explicitly excluded from model use; retained extras, secrets marked as non-model data, and runtime-only values do not become prompt context. Authentication, model selection, sandboxing, hooks, tool approvals, and shell policy are explicit deployment settings. They cannot expand the access allowed by IR or implicitly activate ambient plugins, skills, MCP servers, credentials, or permissions.

Timeout and model-budget ceilings can be set both for one operation and for the
whole run. A whole-run deadline limits every later operation even when its own
timeout is longer. A whole-run budget is shared: concurrent operations reserve
disjoint portions before invoking the SDK and return only observed unused
budget, so parallel execution cannot silently multiply the configured ceiling.
A run budget therefore requires a finite per-operation budget. Without that
reservation ceiling, configuration is rejected before execution rather than
letting the first concurrent call reserve the entire run allowance.

Claude-specific transport and deployment mechanics are maintained in the [executable IR validation and runtime rules](reference/executable-ir-acceptance-and-runtime.md). Another conforming backend executes the same validated workflow without changing its algorithm.
