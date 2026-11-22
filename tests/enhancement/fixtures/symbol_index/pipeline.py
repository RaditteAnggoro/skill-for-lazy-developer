import units as unit_math
from units import clamp
from units import convert as as_units


def prepare(amount):
    return as_units(amount)


def prepare_many(amounts):
    return unit_math.convert(amounts[0])


def cap(amount):
    return clamp(amount)


def with_callback(convert, clamp, amount):
    return convert(clamp(amount))


def with_local_override(amount):
    as_units = lambda value: value
    return as_units(amount)


def select_dynamic(name, value):
    method = getattr(unit_math, name)
    return method(value)


# A string example for documentation: convert(125)
