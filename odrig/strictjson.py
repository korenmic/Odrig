"""Strict JSON loading shared by every reader of a JSON file.

A file is refused when it is not UTF-8, starts with a byte-order mark, is not exactly one
JSON value, or names a member twice in one object. An integer is a number written without a
fraction and without an exponent.
"""

import json

from . import errors

_LONGEST_INTEGER = 30


class _NotAnInteger:
    """A number written with a fraction or an exponent. It passes no integer check."""

    def __init__(self, text):
        self.text = text


def loads(data):
    """The value of a JSON text given as bytes."""
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        raise errors.Rejection(errors.BAD_JSON, "not UTF-8") from None
    if text.startswith("﻿"):
        raise errors.Rejection(errors.BAD_JSON, "starts with a byte-order mark")
    try:
        return json.loads(
            text,
            object_pairs_hook=_object,
            parse_constant=_constant,
            parse_float=_NotAnInteger,
            parse_int=_integer,
        )
    except json.JSONDecodeError as error:
        raise errors.Rejection(
            errors.BAD_JSON, f"line {error.lineno}, column {error.colno}: {error.msg}"
        ) from None
    except RecursionError:
        raise errors.Rejection(errors.BAD_JSON, "nested too deeply") from None


def _object(pairs):
    result = {}
    for name, value in pairs:
        if name in result:
            raise errors.Rejection(errors.BAD_JSON, f'member "{name}" appears twice in one object')
        result[name] = value
    return result


def _constant(name):
    raise errors.Rejection(errors.BAD_JSON, f"{name} is not a JSON value")


def _integer(text):
    """The value of an integer; one too long to matter becomes a value outside every range."""
    if len(text) > _LONGEST_INTEGER:
        huge = 10 ** _LONGEST_INTEGER
        return -huge if text.startswith("-") else huge
    return int(text)


def members(obj, required, optional=(), what="the file"):
    """Checks that `obj` is an object with every required member and no unlisted one."""
    if type(obj) is not dict:
        raise errors.Rejection(errors.BAD_TYPE, f"{what} is not an object")
    for name in required:
        if name not in obj:
            raise errors.Rejection(errors.MISSING_MEMBER, f'{what} has no member "{name}"')
    for name in obj:
        if name not in required and name not in optional:
            raise errors.Rejection(errors.UNKNOWN_MEMBER, f'{what} has the unknown member "{name}"')


def integer(value, low=None, high=None, what="a value"):
    """Checks that `value` is an integer from `low` to `high` and returns it."""
    if type(value) is not int:
        raise errors.Rejection(errors.BAD_TYPE, f"{what} is not an integer")
    if low is not None and value < low:
        raise errors.Rejection(errors.OUT_OF_RANGE, f"{what} is below {low}")
    if high is not None and value > high:
        raise errors.Rejection(errors.OUT_OF_RANGE, f"{what} is above {high}")
    return value


def array(value, what="a value"):
    """Checks that `value` is an array and returns it."""
    if type(value) is not list:
        raise errors.Rejection(errors.BAD_TYPE, f"{what} is not an array")
    return value
