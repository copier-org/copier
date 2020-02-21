from pathlib import Path

from copier import tools
from copier.config.factory import ConfigData, EnvOps

from .helpers import DATA, PROJECT_TEMPLATE


def test_render(dst):
    envops = EnvOps().dict()
    render = tools.Renderer(
        ConfigData(src_path=PROJECT_TEMPLATE, dst_path=dst, data=DATA, envops=envops)
    )

    assert render.string("/hello/[[ what ]]/") == "/hello/world/"
    assert render.string("/hello/world/") == "/hello/world/"

    sourcepath = PROJECT_TEMPLATE / "pyproject.toml.tmpl"
    result = render(sourcepath)
    expected = Path("./tests/reference_files/pyproject.toml").read_text()
    assert result == expected
