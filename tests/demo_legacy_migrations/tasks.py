#!/usr/bin/env python
import os
import sys
from contextlib import suppress
from pathlib import Path

with Path("created-with-tasks.txt").open("a", newline="\n") as cwt:
    cwt.write(" ".join([os.environ["STAGE"]] + sys.argv[1:]) + "\n")
    with suppress(FileNotFoundError):
        Path("delete-in-tasks.txt").unlink()
