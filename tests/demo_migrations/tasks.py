#!/usr/bin/env python
import os
import os.path
import sys
from contextlib import suppress

with open("created-with-tasks.txt", "a", newline="\n") as cwt:
    cwt.write(" ".join([os.environ["STAGE"]] + sys.argv[1:]) + "\n")
    with suppress(FileNotFoundError):
        os.unlink("delete-in-tasks.txt")
