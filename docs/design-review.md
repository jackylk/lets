# Design Review

## Findings

### 1. `Track` branch may be premature and could blur planning vs state

The current model makes `track` both:

- a roadmap grouping concept
- a DBay state branch layer

This may be too much too early.

Why it matters:

- In many projects, tracks are simply planning buckets, not true divergence
  boundaries.
- If every track becomes a branch, inheritance and promotion logic become more
  complex before there is evidence that track-local state needs isolation.
- The model risks making agents ask, "is this a track conclusion or a project
  conclusion?" even when the answer does not materially matter.

Recommendation:

- Keep `Track` as a typed planning object.
- For MVP, support only:

```text
project-main -> initiative -> session
```

- Add `track` state branches later only if real usage shows track-level
  divergence is meaningful.

### 2. `Goal`, `Track`, `Initiative`, and `Milestone` currently overlap

The documents define:

- `Goal`
- `Track`
- `Initiative`
- `Milestone`

but the boundary between them is not yet strict enough.

Observed ambiguity:

- a track can contain goals
- an initiative can represent a path
- a milestone can look like an initiative checkpoint
- goals can also include metric targets

Why it matters:

- UI and agent APIs will become confusing if objects can be used
  interchangeably.
- Agents will create the wrong object type unless the ontology is very clear.

Recommendation:

- `Goal`: desired outcome
- `Track`: stable management lane
- `Initiative`: chosen exploratory path
- `Milestone`: scheduled checkpoint inside an initiative

Add explicit examples and creation rules to the schema docs before building.

### 3. `Signal` and `Idea` are useful, but the distinction may be over-modeled for MVP

The conceptual difference is valid:

- `Signal`: external input
- `Idea`: a researchable proposal

But many first-version workflows will be:

```text
paste URL + idea text -> one research item
```

Why it matters:

- A separate signal object adds one more entity and lifecycle without proving
  immediate user value.
- Humans likely think in terms of "new idea," not "new signal."

Recommendation:

- Preserve the model conceptually.
- In MVP UI and API, expose only `Idea`.
- Let `Idea` optionally carry:

```text
source_type
source_url
source_title
```

- Reintroduce standalone `Signal` later if one source commonly fans out into
  multiple ideas or if anomaly/event ingestion becomes important.

### 4. `Finding` is doing too many jobs

Currently `Finding` can be:

- a research conclusion
- an initiative observation
- a hypothesis support/refutation item
- perhaps an agent report

Why it matters:

- If `Finding` stays too generic, the architecture graph and evidence views will
  eventually need many ad hoc filters.
- A "finding" backed by a metric is semantically different from a draft note.

Recommendation:

- Keep `Finding`, but require:

```text
finding_type
status
support_level
```

- Consider the following initial types:

```text
observation
recommendation
claim
counterexample
```

- Link evidence separately instead of overloading `Finding` with too much proof
  semantics.

### 5. The branch model lacks a clear answer for "accepted but still scoped"

The current promotion ladder is:

```text
session -> initiative -> track -> project-main
```

If `track` branches are removed from MVP, one question remains:

- where does an accepted-but-not-global conclusion live?

Example:

- "For Track B, gpt-4o-mini is now the judge convention."

Why it matters:

- Not every accepted fact should become project-wide truth.
- Yet it should not remain trapped inside a single initiative.

Recommendation:

- Add `scope` independently of branch:

```text
project
track
initiative
session
```

- Branches model divergence.
- Scope models applicability.

This is a cleaner separation than using branch hierarchy for both jobs.

### 6. Promotion semantics are under-specified

The docs say "promote selected state upward," but do not define whether promotion:

- copies data
- references the original item
- changes acceptance status
- creates a new accepted object derived from the old one

Why it matters:

- This choice affects auditability, diffing, duplication, and query semantics.

Recommendation:

- Prefer promotion as:

```text
new accepted object + provenance link to source object
```

- Avoid moving the original item in place.
- Record:

```text
promoted_from_id
promoted_from_branch_id
decision_id
```

### 7. Event model may be too broad for the first implementation

The event list is conceptually sound but already quite large.

Why it matters:

- Full event sourcing for every entity from day one will slow implementation.
- Some events may never provide meaningful product value.

Recommendation:

- Split events into:

```text
must-event-source
nice-to-event-source
current-state-only
```

- MVP must-event-source:

```text
idea.claimed
finding.promoted
decision.created
initiative.status_changed
work_session.started
work_session.completed
metric_run.completed
state_branch.created
state_branch.archived
github.pull_request_merged
```

- Everything else can be added later unless required by a concrete UI or audit
  need.

### 8. `Human` and `Agent` are modeled, but `Organization` and `Device` are missing

Current `Human` has `org_id`; `Agent` has `device_id`; neither referenced object
is defined.

Why it matters:

- Multi-user, multi-device collaboration is one of the core product claims.
- Without typed `Organization` and `Device`, onboarding, permissions, and agent
  provenance will become ad hoc quickly.

Recommendation:

- Add:

```text
Organization
Device
```

- Even if permissions remain simple in MVP, identity should not be implicit.

### 9. `Task` may be overemphasized relative to the product thesis

The product differentiates around research coordination, not general-purpose
project management.

Why it matters:

- If the first product becomes task-heavy, it will drift toward Jira-like UX and
  away from its strongest differentiation.

Recommendation:

- Keep `Task`, but do not make it the center of first-screen UX.
- First-screen emphasis should stay on:

```text
ideas
initiatives
agents
evidence
human attention
```

### 10. Metrics need a richer validity model

Current metric fields include:

- baseline
- delta
- valid

This is not enough for the kind of benchmark-heavy work the system wants to
support.

Why it matters:

- Real experiments fail due to judge swap, partial runs, stale configs, or data
  contamination.
- Those are not binary valid/invalid cases.

Recommendation:

- Add:

```text
metric_status: provisional | accepted | invalidated
comparability_group
run_kind: smoke | partial | full
invalidated_by_decision_id nullable
```

This will matter a lot for projects like echomem.

## Recommended Simplified MVP Model

### Branches

```text
project-main -> initiative -> session
```

### Scopes

```text
project | track | initiative | session
```

### Hide or Defer

- standalone `Signal`
- track state branches
- broad event taxonomy

### Keep Core

- Goal
- Track
- Idea
- Initiative
- Hypothesis
- Finding
- Agent
- WorkSession
- StateBranch
- CodeBranch
- MetricRun
- MetricResult
- Feedback
- Decision

## Net Assessment

The design direction is strong.

The main risk is not that it is missing a core concept. The main risk is that it
currently uses some concepts to solve two jobs at once:

- branch as both divergence and applicability
- finding as both claim and evidence
- track as both roadmap lane and state container

Tightening those boundaries now will make the first implementation materially
cleaner.

