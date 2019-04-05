from fnmatch import fnmatch
from functools import reduce
import errno
import os
import shutil
import unicodedata

import jinja2
from jinja2.sandbox import SandboxedEnvironment
import colorama
from colorama import Fore, Style


_all__ = (
    "STYLE_OK",
    "STYLE_WARNING",
    "STYLE_IGNORE",
    "STYLE_DANGER",
    "printf",
    "prompt",
    "prompt_bool",
)

colorama.init()

STYLE_OK = [Fore.GREEN, Style.BRIGHT]
STYLE_WARNING = [Fore.YELLOW, Style.BRIGHT]
STYLE_IGNORE = [Fore.CYAN]
STYLE_DANGER = [Fore.RED, Style.BRIGHT]


def printf(action, msg="", style=None, indent=12):
    action = action.rjust(indent, " ")
    if not style:
        return action + msg

    out = style + [action, Fore.RESET, Style.RESET_ALL, "  ", msg]
    print(*out, sep="")


no_value = object()


def required(value):
    if not value:
        raise ValueError()
    return value


def prompt(text, default=no_value, validator=required, **kwargs):
    """
    Prompt for a value from the command line. A default value can be provided,
    which will be used if no text is entered by the user. The value can be
    validated, and possibly changed by supplying a validator function. Any
    extra keyword arguments to this function will be passed along to the
    validator. If the validator raises a ValueError, the error message will be
    printed and the user asked to supply another value.
    """
    text += " [%s] " % default if default is not no_value else " "
    while True:
        resp = input(text)

        if resp == "" and default is not no_value:
            resp = default

        try:
            return validator(resp, **kwargs)
        except ValueError as e:
            if str(e):
                print(str(e))


def prompt_bool(question, default=False, yes_choices=None, no_choices=None):
    """Prompt for a true/false yes/no boolean value"""
    yes_choices = yes_choices or ("y", "yes", "t", "true", "on", "1")
    no_choices = no_choices or ("n", "no", "f", "false", "off", "0")

    def validator(value):
        value = value.lower()
        if value in yes_choices:
            return True
        if value in no_choices:
            return False
        raise ValueError("Enter yes/no. y/n, true/false, on/off")

    return prompt(
        question,
        default=yes_choices[0] if default else no_choices[0],
        validator=validator,
    )


def make_folder(folder, pretend=False):
    if not folder.exists():
        try:
            os.makedirs(str(folder))
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise


def copy_file(src, dst):
    shutil.copy2(str(src), str(dst))


# The default env options for jinja2
DEFAULT_ENV_OPTIONS = {
    "autoescape": True,
    "block_start_string": "[%",
    "block_end_string": "%]",
    "variable_start_string": "[[",
    "variable_end_string": "]]",
    "keep_trailing_newline": True,
}


class Renderer(object):
    def __init__(self, env, src_path, data):
        self.env = env
        self.src_path = src_path
        self.data = data

    def __call__(self, fullpath):
        relpath = str(fullpath) \
            .replace(self.src_path, "", 1) \
            .lstrip(os.path.sep)
        tmpl = self.env.get_template(relpath)
        return tmpl.render(**self.data)

    def string(self, string):
        tmpl = self.env.from_string(string)
        return tmpl.render(**self.data)


def get_jinja_renderer(src_path, data, envops=None):
    """Returns a function that can render a Jinja template.
    """
    # Jinja <= 2.10 does not work with `pathlib.Path`s
    src_path = str(src_path)
    _envops = DEFAULT_ENV_OPTIONS.copy()
    _envops.update(envops or {})
    _envops.setdefault("loader", jinja2.FileSystemLoader(src_path))

    # We want to minimize the risk of hidden malware in the templates
    # so we use the SandboxedEnvironment instead of the regular one.
    # Of couse we still have the post-copy tasks to worry about, but at least
    # they are more visible to the final user.
    env = SandboxedEnvironment(**_envops)

    return Renderer(env=env, src_path=src_path, data=data)


def normalize(text, form="NFD"):
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
        path = normalize(str(path))
        name = os.path.basename(path)
        return fnmatch(name, pattern) or fnmatch(path, pattern)

    def must_be_filtered(name):
        return reduce(lambda r, pattern: r or fullmatch(name, pattern), exclude, False)

    def must_be_included(name):
        return reduce(lambda r, pattern: r or fullmatch(name, pattern), include, False)

    def must_filter(path):
        return must_be_filtered(path) and not must_be_included(path)

    return must_filter
