"""Jinja2 extensions built for Copier."""

from __future__ import annotations

from typing import Any, Callable, Sequence

from jinja2 import nodes
from jinja2.exceptions import UndefinedError
from jinja2.ext import Extension
from jinja2.parser import Parser
from jinja2.sandbox import SandboxedEnvironment


class YieldEnvironment(SandboxedEnvironment):
    """Jinja2 environment with a `yield_context` attribute.

    This is simple environment class that extends the SandboxedEnvironment
    for use with the YieldExtension, mainly for avoiding type errors.

    We use the SandboxedEnvironment because we want to minimize the risk of hidden malware
    in the templates so we use the SandboxedEnvironment instead of the regular one.
    Of course we still have the post-copy tasks to worry about, but at least
    they are more visible to the final user.
    """

    yield_context: dict[str, Any]

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.extend(yield_context=dict())


class YieldExtension(Extension):
    """`Jinja2 extension for the `yield` tag.

    If `yield` tag is used in a template, this extension sets the `yield_context` attribute to the
    jinja environment. `yield_context` is a dictionary with the following keys:
    - `single_var`: The name of the variable that will be yielded.
    - `looped_var`: The variable that will be looped over.

    Note that this extension just sets the `yield_context` attribute but renders template
    as usual. It is caller's responsibility to use the `yield_context` attribute in the
    template to generate the desired output.

    Example:
        template: "{% yield single_var from looped_var %}"
        context: {"looped_var": [1, 2, 3], "single_var": "item"}

        then,
        >>> from copier.jinja_ext import YieldEnvironment, YieldExtension
        >>> env = YieldEnvironment(extensions=[YieldExtension])
        >>> template = env.from_string("{% yield single_var from looped_var %}{{ single_var }}{% endyield %}")
        >>> template.render({"looped_var": [1, 2, 3]})
        ''
        >>> env.yield_context
        {'single_var': 'single_var', 'looped_var': [1, 2, 3]}
    """

    tags = {"yield"}

    environment: YieldEnvironment

    def __init__(self, environment: YieldEnvironment):
        super().__init__(environment)

    def parse(self, parser: Parser) -> nodes.Node:
        """Parse the `yield` tag."""
        lineno = next(parser.stream).lineno

        single_var: nodes.Name = parser.parse_assign_target(name_only=True)
        parser.stream.expect("name:from")
        looped_var = parser.parse_expression()
        body = parser.parse_statements(("name:endyield",), drop_needle=True)

        return nodes.CallBlock(
            self.call_method(
                "_yield_support",
                [looped_var, nodes.Const(single_var.name)],
            ),
            [],
            [],
            body,
            lineno=lineno,
        )

    def _yield_support(
        self, looped_var: Sequence[Any], single_var_name: str, caller: Callable[[], str]
    ) -> str:
        """Support function for the yield tag.

        Sets the yield context in the environment with the given
        looped variable and single variable name, then calls the provided caller
        function. If an UndefinedError is raised, it returns an empty string.

        """
        self.environment.yield_context = {
            "single_var": single_var_name,
            "looped_var": looped_var,
        }

        try:
            res = caller()

        # expression like `dict.attr` will always raise UndefinedError
        # so we catch it here and return an empty string
        except UndefinedError:
            res = ""

        return res
