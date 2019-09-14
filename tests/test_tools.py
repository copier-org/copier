from pathlib import Path

from copier import tools
from copier.config.factory import EnvOps

from .helpers import DATA, PROJECT_TEMPLATE


def test_render(dst):
    envops = EnvOps().dict()
    render = tools.get_jinja_renderer(PROJECT_TEMPLATE, DATA, envops=envops)

    assert render.string("/hello/[[ what ]]/") == "/hello/world/"
    assert render.string("/hello/world/") == "/hello/world/"

    sourcepath = PROJECT_TEMPLATE / "pyproject.toml.tmpl"
    result = render(sourcepath)
    expected = Path("./tests/pyproject.toml.ref").read_text()
    assert result == expected
