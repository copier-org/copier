#!/usr/bin/env python
# coding=utf-8
from __future__ import print_function

import functools

try:
    input = raw_input
except NameError:
    pass


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


def as_validated_prompt(func):
    """
    Make a validator function in to a prompt function that uses that validator
    """
    @functools.wraps(func)
    def wrapped(text, default=no_value, **kwargs):
        return prompt(text, default, validator=func, **kwargs)
    return wrapped


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


@as_validated_prompt
def prompt_int(value, min_value=None, max_value=None):
    try:
        value = int(value)
    except ValueError:
        raise ValueError('Enter a whole number')

    if min_value and value < min_value:
        raise ValueError('Value must be equal to or greater than {}'.format(min_value))
    if max_value and value > max_value:
        raise ValueError('Value must be equal to or lower than {}'.format(max_value))
    return value
