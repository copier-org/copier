# coding=utf-8
import io
import os
import errno
import filecmp
import shutil
import unicodedata

from colorama import Fore, Back, Style

from ._compat import to_unicode


def format_message(action, msg='', color='', on_color='', bright=True, indent=12):
    """Format message."""
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


def print_format(*args, **kwargs):
    """Like format_message but prints it."""
    print(format_message(*args, **kwargs))


def make_dirs(*lpath):
    """Ensure the directories exist.

    lpath: list of directories
    """
    path = os.path.join(*lpath)
    try:
        os.makedirs(os.path.dirname(path))
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return os.path.abspath(path)


def read_file(path, encoding='utf8'):
    """Open file and return the content. By default the file is assumed to be
    encoded in UTF-8.
    """
    with io.open(path, 'rt', encoding=encoding) as f:
        content = f.read()
    return content


def file_has_this_content(path, content, encoding='utf8'):
    """True if the file is identical to the content.

    When comparing two files it is best to use the files_are_identical
    function.
    """
    with io.open(path, 'rt', encoding=encoding) as f:
        indeed = content == f.read()
    return indeed


def files_are_identical(path_1, path_2):
    """True if files are identical, False otherwise."""
    return filecmp.cmp(path_1, path_2, shallow=False)


def normalize(text, form='NFD'):
    """Normalize unicode text. Uses the NFD algorithm by default."""
    return unicodedata.normalize(form, text)


def create_file(path, content, encoding='utf8'):
    """Create a file at path the content. Content is assumed to be a utf-8 encoded
    string.
    """
    content = to_unicode(content, encoding)
    with io.open(path, 'wt', encoding=encoding) as f:
        f.write(content)


def copy_file(path_in, path_out):
    shutil.copy2(path_in, path_out)

copy_file.__doc__ = shutil.copy2.__doc__
