from os import SEEK_END
from unittest import mock

import pytest
import six
from plumbum import local

# Workaround to let plumbum.local and plumbum.cmd run in virtualenv
local.env.path.insert(0, local.cwd / ".venv" / "bin")


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
