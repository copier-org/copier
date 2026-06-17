# Contribution 1: Live Preview / Hot-Reloading for Copier Templates

**Contribution Number:** 1
**Student:** Karen Emily Muhwezi
**Issue:** https://github.com/copier-org/copier/issues/1451
**Status:** Phase II In Progress

---

## Why I Chose This Issue

As someone with a Python background who has worked with ML models, I'm drawn
to tooling problems that slow developers down in real, tangible ways. This
issue describes a genuinely frustrating workflow — having to commit, push, and
run updates just to preview a template change — and proposes a solution that
would make the development experience significantly better. That kind of
quality-of-life improvement is something I find meaningful to work on because
the impact is immediately visible.

This issue also aligns well with my learning goals. Copier is a Python
project, which plays to my existing strengths, but building a live preview
feature means I'll be working with file watching, CLI design, and real-time
rendering pipelines — areas I haven't worked in deeply before. I want to grow
my problem-solving skills by tackling something that has genuine complexity
underneath a simple-sounding description, and see that solution actually ship
in a tool that real developers use every day.

---

## Understanding the Issue

### Problem Description

Copier currently has no way to preview how a template renders during 
development. To see any changes, a developer must commit their changes, push 
to GitHub, switch to a downstream project, run `copier update`, and observe 
the output — then repeat the entire cycle for every fix. This makes template 
development extremely slow and tedious.

### Expected Behavior

A template developer should be able to run a single command like 
`copier preview` that renders their template locally into a temporary 
directory and automatically re-renders it every time they save a change, 
without any manual steps in between — similar to hot-reloading in React 
development.

### Current Behavior

There is no preview or watch command in Copier. The only way to test template 
changes is to go through the full commit, push, and `copier update` cycle on 
a downstream project, which requires switching between multiple repositories 
and running multiple commands every single time a change is made.

### Affected Components

- Copier's CLI layer — a new `preview` or `watch` command needs to be added
- Core template rendering pipeline in `copier/main.py` — the existing render 
  logic will be reused
- A new file watching component using the `watchfiles` library to detect 
  changes and trigger re-renders

---

## Reproduction Process

### Environment Setup

Cloned fork from https://github.com/karenemily/codepath-copier.git

Ran `python -m uv sync` and hit a network timeout trying to fetch `hatch_vcs`:
x Failed to build copier @ file:///C:/Users/Administrator/codepath-copier

|-> Failed to resolve requirements from build-system.requires

|-> No solution found when resolving: hatchling, hatch-vcs

|-> Request failed after 3 retries in 84.0s

|-> error sending request for url (https://files.pythonhosted.org/...)

`-> operation timed out
This appears to be a network connectivity issue on the current machine rather
than a project configuration problem. Will retry on a stable network
connection.

### Steps to Reproduce

1. Create a Copier template locally
2. Make a change to the template
3. Attempt to preview how the change renders without pushing to GitHub
4. Observed result: No preview mechanism exists — must commit, push, and run
   `copier update` on a downstream project to see any changes

### Reproduction Evidence

- **Commit showing reproduction:** [Link to commit in your fork]
- **Screenshots/logs:** Network timeout error documented above
- **My findings:** [What you discovered during reproduction]

---

## Solution Approach

### Analysis

[Your analysis of the root cause - what's causing the issue?]

### Proposed Solution

[High-level description of your fix approach]

### Implementation Plan

Using UMPIRE framework (adapted):

**Understand:** Template developers currently have no way to preview renders
locally without a full commit-push-update cycle. We need a live preview
command that watches for changes and re-renders automatically.

**Match:** The existing `copier copy` and `copier update` commands in
`copier/main.py` show how rendering is triggered. The new command will reuse
the same rendering logic but wrap it in a file watcher loop.

**Plan:**
1. Add `watchfiles` as a dependency in `pyproject.toml`
2. Create a new `preview` or `watch` function in `copier/main.py` that
   accepts a template path and output path
3. On first call, render the template into a temporary directory
4. Start a `watchfiles` watcher on the template directory
5. On every detected change, re-render and show a diff of what changed
6. Expose the new function as a CLI command via the existing CLI layer
7. Add tests for the new command

**Implement:** https://github.com/karenemily/codepath-copier/tree/fix-issue-live-preview

**Review:** [Self-review checklist - does it follow the project's contribution
guidelines?]

**Evaluate:** [What tests will confirm your fix works?]

---

## Testing Strategy

### Unit Tests

- [ ] Test case 1: [Description]
- [ ] Test case 2: [Description]
- [ ] Test case 3: [Description]

### Integration Tests

- [ ] Integration scenario 1
- [ ] Integration scenario 2

### Manual Testing

[What you tested manually and results]

---

## Implementation Notes

### Week 1 Progress

Environment setup attempted. Hit network timeout during `uv sync`. Branch
`fix-issue-live-preview` created and pushed. Codebase exploration in progress.

### Week [Y] Progress

[Continue documenting as you work]

### Code Changes

- **Files modified:** [List]
- **Key commits:** [Links to important commits]
- **Approach decisions:** [Why you chose certain approaches]

---

## Pull Request

**PR Link:** [GitHub PR URL when submitted]

**PR Description:** [Draft or final PR description]

**Maintainer Feedback:**
- [Date]: [Summary of feedback received]
- [Date]: [How you addressed it]

**Status:** [Awaiting review / Iterating / Approved / Merged]

---

## Learnings & Reflections

### Technical Skills Gained

[What you learned technically]

### Challenges Overcome

[What was hard and how you solved it]

### What I'd Do Differently Next Time

[Reflection on your process]

---

## Resources Used

- https://github.com/copier-org/copier — Main repository
- https://github.com/copier-org/copier/issues/1451 — Issue being addressed
- https://github.com/samuelcolvin/watchfiles — Suggested file watching library
- Copier documentation: https://copier.readthedocs.io