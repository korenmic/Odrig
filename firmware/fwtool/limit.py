"""The limit on LED current: a limit file read and checked, and the limit set in WLED's
stored settings in a storage image."""

import copy

from . import Failure, paths, settingsfile, wledfiles

# Where WLED keeps its maximum: hw.led.maxpwr of its configuration.
CONFIG = wledfiles.CONFIG
WHERE = ("hw", "led")
NAME = "maxpwr"

MEMBER = "milliamps"
# WLED keeps its maximum as a 16-bit number. 0 switches its limiter off.
LOWEST, HIGHEST = 0, 65535


def read(path=paths.LIMIT_SETTINGS):
    """The limit of a limit file, in milliamps, checked."""
    value = settingsfile.value_of(path, "limit-settings-missing", "limit-settings-malformed")
    if not isinstance(value, dict) or list(value) != [MEMBER] or type(value[MEMBER]) is not int:
        raise Failure("limit-settings-malformed", f"{path} is not an object with exactly the whole number {MEMBER}")
    milliamps = value[MEMBER]
    if not LOWEST <= milliamps <= HIGHEST:
        raise Failure("limit-invalid", f"the limit is {milliamps} mA; a limit is {LOWEST} to {HIGHEST}, and 0 switches the limiter off")
    return milliamps


def line(milliamps):
    """The limit in the words the tool prints."""
    return "limit: off" if milliamps == 0 else f"limit: {milliamps} mA"


def _stored(config):
    """The limit in a configuration object, or None when it holds none."""
    led = wledfiles.inner(config, CONFIG, *WHERE)
    value = None if led is None else led.get(NAME)
    return value if type(value) is int else None


def _without_the_limit(config):
    """A configuration without the limit, as text, so that the order of the members
    counts. An object left empty by this counts as absent."""
    left = copy.deepcopy(config)
    outer = left.get(WHERE[0])
    if isinstance(outer, dict):
        if isinstance(outer.get(WHERE[1]), dict):
            outer[WHERE[1]].pop(NAME, None)
            if not outer[WHERE[1]]:
                del outer[WHERE[1]]
        if not outer:
            del left[WHERE[0]]
    return wledfiles.text_of(left)


def apply(image, milliamps):
    """A storage image with the limit in WLED's stored settings, and everything else as
    it was. The result is checked before it is returned. An image that holds the limit
    already is returned as it is."""
    old = wledfiles.object_of(wledfiles.files_of(image), CONFIG)
    wledfiles.inner(old, CONFIG, *WHERE)
    new = copy.deepcopy(old)
    new.setdefault(WHERE[0], {}).setdefault(WHERE[1], {})[NAME] = milliamps
    if wledfiles.text_of(new) == wledfiles.text_of(old):
        return image
    made, after = wledfiles.written(image, {CONFIG: new})
    if stored(made) != milliamps:
        raise Failure("verify-failed", f"{CONFIG} in the new image does not hold the limit")
    if _without_the_limit(wledfiles.object_of(after, CONFIG)) != _without_the_limit(old):
        raise Failure("verify-failed", f"{CONFIG} in the new image differs in more than the limit")
    return made


def stored(image):
    """The limit in WLED's stored settings of a storage image, or None when they hold
    none."""
    try:
        return _stored(wledfiles.object_of(wledfiles.files_of(image), CONFIG))
    except Failure:
        return None
