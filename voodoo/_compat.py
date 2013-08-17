# -*- coding: utf-8 -*-
"""
Utilities for writing code that runs on Python 2 and 3.
"""
import sys


PY2 = sys.version_info[0] == 2


if PY2:
    string_types = basestring
    from urllib2 import urlparse
else:
    string_types = str
    from urllib import parse as urlparse


def to_unicode(txt, encoding='utf8'):
    if not isinstance(txt, string_types):
        txt = str(txt)
    if not PY2:
        return str(txt)
    if isinstance(txt, unicode):
        return txt
    return unicode(txt, encoding)
