from fnmatch import fnmatch
from functools import reduce
import errno
import io
import os
import shutil
import unicodedata

from colorama import Fore, Back, Style
import jinja2
from jinja2.sandbox import SandboxedEnvironment


COLOR_OK = 'green'
COLOR_WARNING = 'yellow'
COLOR_IGNORE = 'cyan'
COLOR_DANGER = 'red'


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


def make_folder(*lpath, pretend=False):
    path = os.path.join(*lpath)
    path = os.path.abspath(path)

    if pretend:
        return path

    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise
    return path


def read_file(path, mode='rt'):
    with io.open(path, mode=mode) as file:
        return file.read()


def write_file(path, content, mode='wt'):
    with io.open(path, mode=mode) as file:
        file.write(content)


copy_file = shutil.copy2


# The default env options for jinja2
DEFAULT_ENV_OPTIONS = {
    'autoescape': True,
    'block_start_string': '[%',
    'block_end_string': '%]',
    'variable_start_string': '[[',
    'variable_end_string': ']]',
    'keep_trailing_newline': True,
}


class Renderer(object):

    def __init__(self, env, src_path, data):
        self.env = env
        self.src_path = src_path
        self.data = data

    def __call__(self, fullpath):
        relpath = fullpath.replace(self.src_path, '').lstrip(os.path.sep)
        tmpl = self.env.get_template(relpath)
        return tmpl.render(**self.data)

    def string(self, string):
        tmpl = self.env.from_string(string)
        return tmpl.render(**self.data)


def get_jinja_renderer(src_path, data, envops=None):
    """Returns a function that can render a Jinja template.
    """
    _envops = DEFAULT_ENV_OPTIONS.copy()
    _envops.update(envops or {})
    _envops.setdefault('loader', jinja2.FileSystemLoader(src_path))

    # We want to minimize the risk of hidden malware in the templates
    # so we use the SandboxedEnvironment instead of the regular one.
    # Of couse we still have the post-copy tasks to worry about, but at least
    # they are more visible to the final user.
    env = SandboxedEnvironment(**_envops)

    return Renderer(env=env, src_path=src_path, data=data)


def normalize(text, form='NFD'):
    """Normalize unicode text. Uses the NFD algorithm by default."""
    return unicodedata.normalize(form, text)


def get_name_filter(exclude, include):
    """Returns a function that evaluates if a file or folder name must be
    filtered out.
    The compared paths are first converted to unicode and decomposed.
    This is neccesary because the way PY2.* `os.walk` read unicode
    paths in different filesystems. For instance, in OSX, it returns a
    decomposed unicode string. In those systems, u'ñ' is read as `\u0303`
    instead of `\xf1`.
    """
    exclude = [normalize(f) for f in exclude]
    include = [normalize(f) for f in include]

    def fullmatch(path, pattern):
        path = normalize(path)
        name = os.path.basename(path)
        return fnmatch(name, pattern) or fnmatch(path, pattern)

    def must_be_filtered(name):
        return reduce(
            lambda r, pattern: r or fullmatch(name, pattern),
            exclude,
            False
        )

    def must_be_included(name):
        return reduce(
            lambda r, pattern: r or fullmatch(name, pattern),
            include,
            False
        )

    def must_filter(path):
        return must_be_filtered(path) and not must_be_included(path)

    return must_filter
