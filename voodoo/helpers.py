# -*- coding: utf-8 -*-
import io
import os
import errno
import filecmp
import shutil
import unicodedata

from colorama import Fore, Back, Style

from ._compat import to_unicode


def formatm(action, msg='', color='', on_color='', bright=True, indent=12):
    action = action.rjust(indent, ' ')
    color = getattr(Fore, color.upper(), '')
    on_color = getattr(Back, on_color.upper(), '')
    style = Style.BRIGHT if bright else Style.DIM if bright is False else ''

    return ''.join([
        color, on_color, style,
        action,
        Fore.RESET, Back.RESET, Style.RESET_ALL,
        '  ',
        msg,
    ])


def pformat(*args, **kwargs):
    print(formatm(*args, **kwargs))


def make_dirs(*lpath):
    path = os.path.join(*lpath)
    try:
        os.makedirs(os.path.dirname(path))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return os.path.abspath(path)


def read_file(path, encoding='utf8'):
    with io.open(path, 'rt', encoding=encoding) as f:
        content = f.read()
    return content


def file_has_this_content(path, content, encoding='utf8'):
    with io.open(path, 'rt', encoding=encoding) as f:
        indeed = content == f.read()
    return indeed


def files_are_identical(path_1, path_2):
    return filecmp.cmp(path_1, path_2, shallow=False)


def unormalize(text, form='NFD'):
    return unicodedata.normalize(form, text)


def create_file(path, content, encoding='utf8'):
    content = to_unicode(content, encoding)
    with io.open(path, 'wt', encoding=encoding) as f:
        f.write(content)


def copy_file(path_in, path_out):
    shutil.copy2(path_in, path_out)
