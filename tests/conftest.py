from os import SEEK_END
from pathlib import Path
from tempfile import mkdtemp
import six
import shutil

import pytest
from unittest import mock


@pytest.fixture()
def dst(request):
    """Return a real temporary folder path which is unique to each test
    function invocation. This folder is deleted after the test has finished.
    """
    dst = mkdtemp()
    request.addfinalizer(lambda: shutil.rmtree(dst))
    return Path(dst)


class AppendableStringIO(six.StringIO):
    def append(self, text):
        pos = self.tell()
        self.seek(0, SEEK_END)
        self.write(text)
        self.seek(pos)


@pytest.fixture()
def stdin():
    buffer = AppendableStringIO()
    with mock.patch("sys.stdin", buffer):
        yield buffer
