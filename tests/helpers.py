from hashlib import sha1
from pathlib import Path
import filecmp
import os

from .. import copier


PROJECT_TEMPLATE = Path(__file__).parent / "demo"

DATA = {
    "py3": True,
    "make_secret": lambda: sha1(os.urandom(48)).hexdigest(),
    "myvar": "awesome",
    "what": "world",
    "project_name": "Copier",
    "version": "2.0.0",
    "description": "A library for rendering projects templates",
}


def render(dst, **kwargs):
    kwargs.setdefault("quiet", True)
    copier.copy(PROJECT_TEMPLATE, dst, data=DATA, **kwargs)


def assert_file(dst, *path):
    p1 = os.path.join(dst, *path)
    p2 = os.path.join(PROJECT_TEMPLATE, *path)
    assert filecmp.cmp(p1, p2)
