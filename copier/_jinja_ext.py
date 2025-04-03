"""Jinja2 extensions built for Copier."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Callable

from jinja2 import nodes
from jinja2.exceptions import UndefinedError
from jinja2.ext import Extension
from jinja2.parser import Parser
from jinja2.sandbox import SandboxedEnvironment

from copier.errors import MultipleYieldTagsError


class YieldEnvironment(SandboxedEnvironment):
    """Jinja2 environment with attributes from the YieldExtension.

    This is simple environment class that extends the SandboxedEnvironment
    for use with the YieldExtension, mainly for avoiding type errors.

    We use the SandboxedEnvironment because we want to minimize the risk of hidden malware
    in the templates. Of course we still have the post-copy tasks to worry about, but at least
    they are more visible to the final user.
    """

    yield_name: str | None
    yield_iterable: Iterable[Any] | None

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.extend(yield_name=None, yield_iterable=None)


class YieldExtension(Extension):
    """Jinja2 extension for the `yield` tag.

    If `yield` tag is used in a template, this extension sets following attribute to the
    jinja environment:

    - `yield_name`: The name of the variable that will be yielded.
    - `yield_iterable`: The variable that will be looped over.

    Note that this extension just sets the attributes but renders templates as usual.
    It is the caller's responsibility to use the `yield_context` attribute in the template to
    generate the desired output.

    !!! example

        ```pycon
        >>> from copier.jinja_ext import YieldEnvironment, YieldExtension
        >>> env = YieldEnvironment(extensions=[YieldExtension])
        >>> template = env.from_string("{% yield single_var from looped_var %}{{ single_var }}{% endyield %}")
        >>> template.render({"looped_var": [1, 2, 3]})
        ''
        >>> env.yield_name
        'single_var'
        >>> env.yield_iterable
        [1, 2, 3]
        ```
    """

    tags = {"yield"}

    environment: YieldEnvironment

    def preprocess(
        self, source: str, _name: str | None, _filename: str | None = None
    ) -> str:
        """Preprocess hook to reset attributes before rendering."""
        self.environment.yield_name = self.environment.yield_iterable = None

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

        Sets the `yield_name` and `yield_iterable` attributes in the environment then calls
        the provided caller function. If an UndefinedError is raised, it returns an empty string.
        """
        if (
            self.environment.yield_name is not None
            or self.environment.yield_iterable is not None
        ):
            raise MultipleYieldTagsError(
                "Attempted to parse the yield tag twice. Only one yield tag is allowed per path name.\n"
                f'A yield tag with the name: "{self.environment.yield_name}" and iterable: "{self.environment.yield_iterable}" already exists.'
            )

        self.environment.yield_name = yield_name
        self.environment.yield_iterable = yield_iterable

        try:
            res = caller()

        # expression like `dict.attr` will always raise UndefinedError
        # so we catch it here and return an empty string
        except UndefinedError:
            res = ""

        return res
