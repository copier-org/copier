import os

from ..copier import tools

from .helpers import PROJECT_TEMPLATE, DATA, read_content


def test_render(dst):
    render = tools.get_jinja_renderer(PROJECT_TEMPLATE, DATA)

    assert render.string('/hello/[[ what ]]/') == '/hello/world/'
    assert render.string('/hello/world/') == '/hello/world/'

    sourcepath = os.path.join(PROJECT_TEMPLATE, 'pyproject.toml.tmpl')
    result = render(sourcepath)
    expected = read_content('./tests/pyproject.toml.ref')
    print(result)
    assert result == expected
