from pathlib import Path

from ..copier import tools

from .helpers import PROJECT_TEMPLATE, DATA


def test_render(dst):
    render = tools.get_jinja_renderer(PROJECT_TEMPLATE, DATA)

    assert render.string("/hello/[[ what ]]/") == "/hello/world/"
    assert render.string("/hello/world/") == "/hello/world/"

    sourcepath = PROJECT_TEMPLATE / "pyproject.toml.tmpl"
    result = render(sourcepath)
    expected = Path("./tests/pyproject.toml.ref").read_text()
    print(result)
    assert result == expected
