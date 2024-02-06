#!/usr/bin/env python
import json
import os
import sys

NAMES = (
    "{VERSION_FROM}-{VERSION_CURRENT}-{VERSION_TO}-{STAGE}.json",
    "PEP440-{VERSION_PEP440_FROM}-{VERSION_PEP440_CURRENT}-{VERSION_PEP440_TO}-{STAGE}.json",
)

for name in NAMES:
    with open(name.format(**os.environ), "w") as fd:
        json.dump(sys.argv, fd)
