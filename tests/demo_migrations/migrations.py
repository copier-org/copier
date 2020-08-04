#!/usr/bin/env python
import json
import os
import sys

NAME = "{VERSION_FROM}-{VERSION_CURRENT}-{VERSION_TO}-{STAGE}.json"

with open(NAME.format(**os.environ), "w") as fd:
    json.dump(sys.argv, fd)
