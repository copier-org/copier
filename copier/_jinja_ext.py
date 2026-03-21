"""Jinja2 extensions built for Copier."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any
from weakref import WeakKeyDictionary

from jinja2 import Environment, nodes
from jinja2.exceptions import UndefinedError
from jinja2.ext import Extension
from jinja2.parser import Parser

from copier.errors import MultipleYieldTagsError


@dataclass
class YieldContext:
    yield_name: str | None = None
    yield_iterable: Iterable[Any] | None = None


_yield_contexts: WeakKeyDictionary[Environment, YieldContext] = WeakKeyDictionary()


def get_yield_context(env: Environment) -> YieldContext:
    """Get or create yield context for an environment."""
    if env not in _yield_contexts:
        _yield_contexts[env] = YieldContext()
    return _yield_contexts[env]


class YieldExtension(Extension):
    """Jinja2 extension for the `yield` tag.

    If `yield` tag is used in a template, this extension stores the yield context
    which can be accessed via `get_yield_context(env)`:

    - `yield_name`: The name of the variable that will be yielded.
    - `yield_iterable`: The variable that will be looped over.

    Note that this extension just sets the context but renders templates as usual.
    It is the caller's responsibility to use the yield context to generate the
    desired output.

    !!! example

        ```pycon
        >>> from jinja2.sandbox import SandboxedEnvironment
        >>> from copier._jinja_ext import YieldExtension, get_yield_context
        >>> env = SandboxedEnvironment(extensions=[YieldExtension])
        >>> template = env.from_string(
        ...     "{% yield single_var from looped_var %}{{ single_var }}{% endyield %}"
        ... )
        >>> template.render({"looped_var": [1, 2, 3]})
        ''
        >>> get_yield_context(env).yield_name
        'single_var'
        >>> get_yield_context(env).yield_iterable
        [1, 2, 3]
        ```
    """

    tags = {"yield"}

    def preprocess(
        self, source: str, name: str | None, filename: str | None = None
    ) -> str:
        """Preprocess hook to reset context before rendering."""
        _ = name, filename
        ctx = get_yield_context(self.environment)
        ctx.yield_name = None
        ctx.yield_iterable = None
        return source

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the `yield` tag."""
        lineno = next(parser.stream).lineno

        yield_name: nodes.Name = parser.parse_assign_target(name_only=True)
        parser.stream.expect("name:from")
        yield_iterable = parser.parse_expression()
        body = parser.parse_statements(("name:endyield",), drop_needle=True)

        return nodes.CallBlock(
            self.call_method(
                "_yield_support",
                [nodes.Const(yield_name.name), yield_iterable],
            ),
            [],
            [],
            body,
            lineno=lineno,
        )

    def _yield_support(
        self, yield_name: str, yield_iterable: Iterable[Any], caller: Callable[[], str]
    ) -> str:
        """Support function for the yield tag.

        Sets the `yield_name` and `yield_iterable` in the yield context then
        calls the provided caller function. If an UndefinedError is raised, it returns
        an empty string.
        """
        ctx = get_yield_context(self.environment)
        if ctx.yield_name is not None or ctx.yield_iterable is not None:
            raise MultipleYieldTagsError(
                "Attempted to parse the yield tag twice. Only one yield tag is allowed per path name.\n"
                f'A yield tag with the name: "{ctx.yield_name}" and iterable: "{ctx.yield_iterable}" already exists.'
            )

        ctx.yield_name = yield_name
        ctx.yield_iterable = yield_iterable

        try:
            res = caller()

        except UndefinedError:
            res = ""

        return res


class UnsetError(UndefinedError): ...
