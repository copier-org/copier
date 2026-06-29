# Contribution 1: Live Preview / Hot-Reloading for Copier Templates

**Contribution Number:** 1
**Student:** Karen Emily Muhwezi
**Issue:** https://github.com/copier-org/copier/issues/1451
**Status:** Phase IV Complete

---

## Why I Chose This Issue

As someone with a Python background who has worked with ML models, I'm drawn
to tooling problems that slow developers down in real, tangible ways. This
issue describes a genuinely frustrating workflow, having to commit, push, and
run updates just to preview a template change, and proposes a solution that
would make the development experience significantly better. That kind of
quality-of-life improvement is something I find meaningful to work on because
the impact is immediately visible.

This issue also aligns well with my learning goals. Copier is a Python
project, which plays to my existing strengths, but building a live preview
feature means I'll be working with file watching, CLI design, and real-time
rendering pipelines, areas I haven't worked in deeply before. I want to grow
my problem-solving skills by tackling something that has genuine complexity
underneath a simple-sounding description, and see that solution actually ship
in a tool that real developers use every day.

---

## Understanding the Issue

### Problem Description

Copier currently has no way to preview how a template renders during 
development. To see any changes, a developer must commit their changes, push 
to GitHub, switch to a downstream project, run `copier update`, and observe 
the output, then repeat the entire cycle for every fix. This makes template 
development extremely slow and tedious.

### Expected Behavior

A template developer should be able to run a single command like 
`copier preview` that renders their template locally into a temporary 
directory and automatically re-renders it every time they save a change, 
without any manual steps in between, similar to hot-reloading in React 
development.

### Current Behavior

There is no preview or watch command in Copier. The only way to test template 
changes is to go through the full commit, push, and `copier update` cycle on 
a downstream project, which requires switching between multiple repositories 
and running multiple commands every single time a change is made.

### Affected Components

- Copier's CLI layer — a new `preview` or `watch` command needs to be added
- Core template rendering pipeline in `copier/_main.py` — the existing render 
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

Resolved by retrying on a stable network connection. Confirmed working
environment by running `python -m uv run copier --version` which returned
`copier 0.1.dev2247+g735b2ed0e`.

Note: `uv` is not on the system PATH on Windows, so all commands must be
run as `python -m uv` instead of `uv` directly.

### Steps to Reproduce

1. Create a Copier template locally
2. Make a change to the template
3. Attempt to preview how the change renders without pushing to GitHub
4. Observed result: No preview mechanism exists — must commit, push, and run
   `copier update` on a downstream project to see any changes

### Reproduction Evidence

- **Commit showing reproduction:** https://github.com/karenemily/codepath-copier/commit/65b7fcaad88c0ac22ffe5a245e03d74a056789f8
- **Screenshots/logs:** Network timeout error documented above
- **My findings:** The issue is a missing feature — there is no existing 
  preview or watch command in Copier's CLI. Confirmed by searching the 
  codebase for any `preview` or `watch` functionality and finding none. 
  Identified `_main.py` as the correct file to add the feature by studying 
  how `run_copy` and `run_update` are structured. Confirmed the feature 
  was fully missing by successfully running `copier --help` and seeing no 
  preview command listed.

---

## Solution Approach

### Analysis

This is a missing feature rather than a bug. Copier currently only supports
rendering templates on demand via `copier copy` or `copier update`. There is
no mechanism to watch a template directory for changes and re-render
automatically. The root cause is that the CLI and rendering pipeline were
built for one-shot use, not continuous development workflows.

### Proposed Solution

Added a new `run_preview` function that renders the template into a
destination directory and then watches the template directory for file
changes using the `watchfiles` library, re-rendering automatically on every
change detected.

### Implementation Plan

Using UMPIRE framework (adapted):

**Understand:** Template developers currently have no way to preview renders
locally without a full commit-push-update cycle. We need a live preview
command that watches for changes and re-renders automatically.

**Match:** The existing `run_copy` and `run_update` methods in `copier/_main.py` 
show how rendering is triggered inside the `Worker` class. The new 
`run_preview` method follows the exact same pattern, reusing `_render_template()` 
and wrapping it in a `watchfiles` loop. The standalone function pattern was 
modelled on `run_recopy`.

**Plan:**
1. ✅ Add `watchfiles` as a dependency in `pyproject.toml`
2. ✅ Add `from watchfiles import watch` to module-level imports in `_main.py`
3. ✅ Add `run_preview` method to the `Worker` class decorated with 
   `@as_operation("copy")`
4. ✅ Add standalone `run_preview` function following the same pattern as 
   `run_recopy`
5. ✅ Write and pass test for the new command
6. ✅ Expose the new function as a CLI command via the existing CLI layer
7. ⬜ Add additional edge case tests

**Implement:** https://github.com/karenemily/codepath-copier/tree/fix-issue-live-preview

**Review:**
- [x] Follows Copier's code style
- [x] New command is documented in PR description
- [x] Existing tests still pass
- [x] New tests added and passing
- [ ] CHANGELOG updated if required by maintainer

**Evaluate:** Test `test_preview_renders_template` confirms the initial render
works correctly. Manual end-to-end testing confirmed hot-reload re-renders
correctly when template files are saved.

---

## Testing Strategy

### Unit Tests

- [x] Test case 1: `test_preview_renders_template` — confirms that 
      `run_preview` correctly renders template files into the destination 
      directory on initial run. Test passes.
- [ ] Test case 2: Re-render triggered correctly after a file change is 
      detected by the watcher
- [ ] Test case 3: Preview handles template errors gracefully without 
      crashing the watcher

### Integration Tests

- [ ] Integration scenario 1: Full preview workflow from template edit to 
      re-render
- [ ] Integration scenario 2: Preview works correctly with Jinja templating 
      and variable substitution

### Manual Testing

Manually tested by running `copier preview` on a local test template. Created
a template with a `hello.txt` file, ran the preview command, edited the file,
and confirmed the output directory updated automatically without any manual
steps. Hot-reload confirmed working end to end.

---

## Implementation Notes

### Week 1 Progress

- Reviewed `CONTRIBUTING.md` and understood code style, testing, and commit 
  message requirements (Conventional Commits format)
- Explored codebase — identified `_main.py` as the correct file, studied 
  `run_copy` and `run_update` patterns
- Added `watchfiles>=0.20` to `pyproject.toml` dependencies
- Added `from watchfiles import watch` to module-level imports in `_main.py`
- Added `run_preview` method to the `Worker` class using `@as_operation("copy")` 
  decorator to satisfy operation context requirements
- Added standalone `run_preview` function with `src_path`, `dst_path`, `data`, 
  `defaults`, `overwrite`, and `quiet` parameters
- Wrote and passed test `test_preview_renders_template` in `tests/test_copy.py`
- Debugged multiple errors including SyntaxError from misplaced import, 
  LookupError from missing operation context, and mock patching issues

### Week 2 Progress

- Added `CopierPreviewSubApp` class to `copier/_cli.py` to expose `run_preview`
  as a `copier preview` CLI subcommand
- Imported `run_preview` into the CLI module alongside existing commands
- Rebased branch on `upstream/master` to stay up to date
- Ran full test suite — 246 passed, 2 pre-existing Windows-only failures 
  unrelated to our changes
- Performed manual end-to-end testing — confirmed hot-reload works correctly
- Submitted PR #2747 to the upstream Copier repository
- Tagged maintainer @sisp for review

### Code Changes

- **Files modified:** `copier/_main.py`, `copier/_cli.py`, `pyproject.toml`, 
  `tests/test_copy.py`
- **Key commits:** https://github.com/karenemily/codepath-copier/tree/fix-issue-live-preview
- **Approach decisions:** Used `@as_operation("copy")` decorator on the 
  `run_preview` method to satisfy the internal operation context requirement. 
  Mocked `watchfiles.watch` in tests to avoid actual file watching during 
  test runs. Moved `watchfiles` import to module level to allow proper mocking.
  Followed the existing `CopierCopySubApp` pattern exactly when building the 
  CLI subcommand.

---

## Pull Request

**PR Link:** https://github.com/copier-org/copier/pull/2747

**PR Description:** Added a new `copier preview` CLI command that renders 
a template locally and automatically re-renders it whenever a file change 
is detected using `watchfiles`, implementing the hot-reloading feature 
requested in issue #1451.

**Maintainer Feedback:**
- Awaiting review from @sisp

**Status:** Awaiting review

---

## Learnings & Reflections

### Technical Skills Gained

- Learned how to navigate a large unfamiliar Python codebase
- Understood the `Worker` class pattern and how Copier's operations are 
  structured
- Learned how to use `unittest.mock` to mock third-party library calls in tests
- Learned about Python `ContextVar` and operation context requirements
- Practised Conventional Commits format for commit messages
- Learned how CLI frameworks work and how to add new subcommands
- Gained experience with Git rebasing and working with upstream remotes
- Learned how to submit a real open source pull request

### Challenges Overcome

- `uv` not on PATH on Windows — resolved by using `python -m uv` prefix
- Network timeout during `uv sync` — resolved by retrying on stable network
- SyntaxError from placing `from watchfiles import watch` before 
  `from __future__ import annotations` — resolved by moving it to the correct 
  position in the imports section
- `LookupError` for missing operation context — resolved by adding 
  `@as_operation("copy")` decorator to the method
- Mock patching failing because import was local — resolved by moving import 
  to module level
- Git rebase failing because default branch is `master` not `main` — resolved 
  by using `upstream/master`

### What I'd Do Differently Next Time

- Set up the development environment on a Linux or Mac machine to avoid 
  Windows-specific issues with symlinks, PATH, and missing commands like `cat`
- Comment on the issue before starting work to confirm it is still wanted 
  by maintainers and get implementation guidance early
- Write tests alongside the code rather than after to catch issues sooner

---

## Resources Used

- https://github.com/copier-org/copier — Main repository
- https://github.com/copier-org/copier/issues/1451 — Issue being addressed
- https://github.com/copier-org/copier/pull/2747 — Submitted pull request
- https://github.com/samuelcolvin/watchfiles — Suggested file watching library
- Copier documentation: https://copier.readthedocs.io
- Copier CONTRIBUTING.md — Code style, testing and commit message guidelines