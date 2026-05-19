# Branch Model

## 1. Purpose

This document defines how DBay state branches should work in the collaboration
workspace.

## 2. Why State Branches Exist

Exploratory engineering creates many local truths before any of them become
global truth.

Examples:

- a research session finds an idea promising
- one initiative branch proves a local gain on LoCoMo but not PersonaMem
- an agent drafts a new architecture relation before the team accepts it
- a failed spike should remain queryable without polluting the accepted roadmap

Git branches track code. State branches track collaborative knowledge and live
coordination state.

## 3. Branch Types

### 3.1 `project-main`

Authoritative project state.

Contains:

- accepted goals
- accepted architecture
- adopted initiatives
- authoritative metrics
- final decisions
- project-wide conventions

### 3.2 `track`

Long-lived strategic scope.

Contains:

- track-local goals
- track history
- active and archived initiatives under the track
- track-specific conclusions

### 3.3 `initiative`

One exploratory route.

Contains:

- hypotheses
- findings
- local metrics
- branch-specific relations
- linked Git branches
- current recommendation

### 3.4 `session`

One agent work session.

Contains:

- temporary notes
- in-progress status
- draft findings
- blockers
- handoff material

## 4. Hierarchy

```text
project-main
  -> track
    -> initiative
      -> session
```

## 5. Inheritance

Each branch sees:

1. its own local state
2. ancestor state
3. globally accepted project-main state

Read precedence:

```text
session local
  > initiative local
    > track local
      > project-main accepted
```

The system must preserve provenance. A caller should be able to ask:

- where did this fact come from
- whether it is local or accepted
- whether it has been promoted

## 6. Write Rules

### 6.1 `project-main`

Write only:

- accepted goals
- final decisions
- promoted conventions
- approved architecture facts

### 6.2 `track`

Write:

- track-specific conclusions
- track priorities
- promoted findings from initiatives

### 6.3 `initiative`

Write:

- route hypotheses
- local findings
- local metrics
- candidate architecture relations

### 6.4 `session`

Write:

- temporary working notes
- draft findings
- transient status
- handoff

## 7. Promotion

Promotion moves state upward with explicit intent.

### 7.1 Session -> Initiative

Typical promotion:

- draft finding becomes accepted finding inside an initiative
- handoff becomes official initiative progress

### 7.2 Initiative -> Track

Typical promotion:

- initiative conclusion
- benchmark-backed route result
- new convention relevant to the whole track

### 7.3 Track -> Project Main

Typical promotion:

- accepted architecture
- stable project-wide standard
- project roadmap change

## 8. Merge Semantics

There are several possible merge operations:

### 8.1 Promote

Copy selected state upward while preserving source provenance.

### 8.2 Supersede

Mark an older accepted item as replaced by a newer one.

### 8.3 Archive

Close a branch while preserving it for historical search.

### 8.4 Reject

Record that a branch-local claim should not be promoted.

### 8.5 Compare

Render two branches side by side:

- hypotheses
- artifacts
- metrics
- decisions

## 9. Relation to Git Branches

A state branch may link to:

- zero Git branches
- one Git branch
- many Git branches

Examples:

- an idea can have only a state branch at first
- one initiative can have competing Git prototypes
- an initiative branch can persist after one Git branch is merged and another
  begins

Recommended mapping:

```text
initiative state branch
  -> code branch A
  -> code branch B
  -> pull request(s)
```

## 10. Typical Examples

### 10.1 Research-only Idea

```text
project-main
  -> track-b
    -> initiative-topic-wm
      -> session-codex-20260518
```

No Git branch exists yet.

### 10.2 Implementation Spike

```text
initiative-topic-wm
  -> linked Git branch feat/topic-wm-spike
```

### 10.3 Failed Route

```text
initiative-profile-inject-v0
  -> metric LoCoMo -2.10pp
  -> decision reject
  -> archive branch
```

The history remains searchable.

## 11. Conflict Handling

### 11.1 Exploration Conflicts

Allow conflicting local findings in separate initiative branches.

### 11.2 Accepted State Conflicts

Do not silently overwrite project-main.

Require:

- explicit decision
- supersession link
- audit event

### 11.3 Concurrent Session Writes

Prefer append-only event writes, then derive latest views.

## 12. Branch Queries

The system should support:

- current visible state for a branch
- local-only state for a branch
- diff against parent
- unpromoted findings
- promoted findings
- rejected findings
- branch ancestry
- linked Git branches

## 13. Required APIs

```text
create_branch
read_branch_context
append_branch_event
list_branch_local_items
diff_branch
promote_item
supersede_item
archive_branch
compare_branches
```

## 14. Open Questions

1. Should branch ancestry be immutable?
2. Should promotion copy data or create references?
3. Should accepted state be materialized or resolved on read?
4. What is the best UX for conflicting accepted decisions?
5. Whether session branches should expire automatically.

