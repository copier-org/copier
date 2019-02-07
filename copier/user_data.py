import json
import os

from ruamel.yaml import YAML

from .tools import read_file, print_format, COLOR_WARNING


__all__ = (
    'get_user_data',
    'prompt',
    'prompt_bool',
)

yaml = YAML(typ="safe", pure=True)
INDENT = '  '


def load_yaml_data(src_path, quiet=False):
    yaml_path = os.path.join(src_path, 'copier.yaml')
    if not os.path.exists(yaml_path):
        return {}

    yaml_src = read_file(yaml_path)
    try:
        return yaml.load(yaml_src)
    except Exception as e:  # pragma:no cover
        if not quiet:
            print('')
            print_format('INVALID', msg=yaml_path, color=COLOR_WARNING, indent=0)
            print('-' * 42)
            print(e)
            print('-' * 42)
        return {}


def load_json_data(src_path, quiet=False):
    json_path = os.path.join(src_path, 'copier.json')
    if not os.path.exists(json_path):
        return load_old_json_data(src_path, quiet=quiet)

    json_src = read_file(json_path)
    try:
        return json.loads(json_src)
    except ValueError as e:  # pragma:no cover
        if not quiet:
            print('')
            print_format('INVALID', msg=json_path, color=COLOR_WARNING, indent=0)
            print('-' * 42)
            print(e)
            print('-' * 42)
        return {}


def load_old_json_data(src_path, quiet=False):
    # TODO: Remove on version 2.2
    json_path = os.path.join(src_path, 'voodoo.json')
    if not os.path.exists(json_path):
        return {}

    if not quiet:
        print('')
        print_format(
            'WARNING',
            msg='`voodoo.json` is deprecated. '
                + 'Replace it with a `copier.yaml` or `copier.json`.',
            color=COLOR_WARNING, indent=10
        )

    json_src = read_file(json_path)
    try:
        return json.loads(json_src)
    except ValueError as e:  # pragma:no cover
        if not quiet:
            print_format('Invalid `{}`'.format(json_path), color=COLOR_WARNING)
            print(e)
        return {}


def load_default_data(src_path, quiet=False):
    data = load_yaml_data(src_path)
    if not data:
        data = load_json_data(src_path)
    return data


def get_user_data(src_path, **flags):
    """Query to user for information needed as per the template's ``copier.yaml``.
    """
    default_user_data = load_default_data(src_path)
    if flags['force'] or not default_user_data:
        return default_user_data

    print('')
    user_data = {}
    for key in default_user_data:  # pragma:no cover
        default = default_user_data[key]
        user_data[key] = prompt(INDENT + ' {0}?'.format(key), default)

    print('\n' + INDENT + '-' * 42)
    return user_data


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
    text += ' [%s] ' % default if default is not no_value else ' '
    while True:
        resp = input(text)

        if resp == '' and default is not no_value:
            resp = default

        try:
            return validator(resp, **kwargs)
        except ValueError as e:
            if str(e):
                print(str(e))


def prompt_bool(question, default=False, yes_choices=None, no_choices=None):
    """Prompt for a true/false yes/no boolean value"""
    yes_choices = yes_choices or ('y', 'yes', 't', 'true', 'on', '1')
    no_choices = no_choices or ('n', 'no', 'f', 'false', 'off', '0')

    def validator(value):
        value = value.lower()
        if value in yes_choices:
            return True
        if value in no_choices:
            return False
        raise ValueError('Enter yes/no. y/n, true/false, on/off')

    return prompt(
        question, default=yes_choices[0] if default else no_choices[0],
        validator=validator)
