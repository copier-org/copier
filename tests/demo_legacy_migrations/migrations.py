#!/usr/bin/env python
import json
import os
import sys
from pathlib import Path

NAMES = (
    "{VERSION_FROM}-{VERSION_CURRENT}-{VERSION_TO}-{STAGE}.json",
    "PEP440-{VERSION_PEP440_FROM}-{VERSION_PEP440_CURRENT}-{VERSION_PEP440_TO}-{STAGE}.json",
)

for name in NAMES:
    with Path(name.format(**os.environ)).open("w") as fd:
        json.dump(sys.argv, fd)
