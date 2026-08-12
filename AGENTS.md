# Agent Guidelines

## Developer commands

- `devbox run -- uv run -- pytest` – run all tests
- `devbox run -- uv run -- pre-commit run -a` – run all code quality checks

## Code conventions

- ALWAYS write code compatible with Python 3.10+
- ALWAYS use `snake_case` for Python functions/methods and variables, `PascalCase` for
  classes, and `UPPER_SNAKE_CASE` for constants
- ALWAYS use full type annotations except for `self` and `cls` parameters
- ALWAYS prefix internal Python modules, packages, and symbols with `_`
- ALWAYS export public Python API symbols via `__all__` in public modules
- ALWAYS use Google-style docstrings with all relevant sections (e.g., `Args`,
  `Returns`, `Raises`)
- ALWAYS use single-backticks for inline code in comments and docstrings; NEVER use
  double-backticks
- NEVER use comments to describe what the code is doing; ONLY use comments to clarify
  invariants and the reasoning behind any unusual/complex implementation decisions
- ALWAYS keep docstrings and comments short and concise

## Test conventions

- ALWAYS attempt to add a test case for changed behavior
- ALWAYS read and copy the style of similar tests when adding new cases
- PREFER running specific tests over running the entire test suite
- PREFER parametrized tests using the `@pytest.mark.parametrize` decorator over
  multiple separate test functions when testing the same logic with different inputs
- PREFER tests that assert one clearly defined behavior; split tests that validate
  multiple unrelated things into separate focused test functions
- ALWAYS test observable behavior (inputs → outputs, raised exceptions, side effects);
  NEVER assert on internal implementation details such as private attributes, call
  counts, execution order, etc.
- PREFER tests that create a minimal test template using `build_file_tree` and call
  `run_copy`/`run_recopy`/`run_update` to generate/update a test project over using
  internal API in isolation
