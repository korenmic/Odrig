"""The current limits: WLED's estimate of the current the LEDs draw, the fade that dims
them, the level that keeps an estimate within a budget, the order in which the budgets of
the legs and of the wall are applied, and the budgets' file `limits.json`.

A leg's bytes are what the core sends its LEDs at a refresh, three for each LED, after the
brightness. A budget is a ceiling in whole mA on the estimate; 0 is no limit.
"""

import dataclasses

from . import errors, files, strictjson

VERSION = 1
NAME = "limits.json"
# WLED's figures: an LED at full white draws 55 mA, and every LED 1 mA at rest.
LED_MA = 55
REST_MA = 1
FULL_WHITE = 3 * 255
# The level at which nothing is dimmed.
UNDIMMED = 255
# The halving over the levels 1 to 254 always takes this many fades.
FADES = 8
LARGEST_WALL = 250000
LARGEST_BUDGET = 65535
LARGEST_LEG = 255

_MEMBERS = ("version", "wall", "legs")


def estimate(data):
    """The estimate in mA of a leg's bytes: floor(S * 55 / 765) + N, S the sum of the bytes
    and N the number of LEDs."""
    return sum(data) * LED_MA // FULL_WHITE + len(data) // 3 * REST_MA


def fade(data, level):
    """WLED's video fade of a leg's bytes to a level from 1 to 255. At 255 nothing changes.
    An LED whose three bytes are 0 stays so; each byte b of another LED becomes
    (b * level + 127) >> 8, with its lowest bit set when b is above a quarter of the LED's
    largest byte, (largest >> 2) + 1."""
    if type(level) is not int or level < 1 or level > UNDIMMED:
        raise ValueError(f"the level {level!r} is not from 1 to {UNDIMMED}")
    if level == UNDIMMED:
        return bytes(data)
    made = bytearray(data)
    for at in range(0, len(made) - len(made) % 3, 3):
        red, green, blue = made[at], made[at + 1], made[at + 2]
        if red == 0 and green == 0 and blue == 0:
            continue
        kept = (max(red, green, blue) >> 2) + 1
        made[at] = ((red * level + 127) >> 8) | (red > kept)
        made[at + 1] = ((green * level + 127) >> 8) | (green > kept)
        made[at + 2] = ((blue * level + 127) >> 8) | (blue > kept)
    return bytes(made)


def level(data, budget):
    """The level at which a leg's budget dims its bytes; 255 when it dims nothing."""
    return _level((data,), budget)


def wall_level(legs, budget):
    """The level at which the wall's budget dims every leg; 255 when it dims nothing. The
    wall's estimate is the sum of its legs', and its LEDs are those of all legs."""
    return _level(tuple(legs), budget)


def _level(parts, budget):
    """With a budget B above 0 and an estimate E above B: 1 when B is at most the number of
    LEDs, N, which the LEDs draw at rest; otherwise the largest level from 1 to 254 whose
    fade gives bytes estimated at B or less, and 1 when none does. Otherwise 255.

    The level is found by halving, always with all eight fades: a candidate is the level
    found so far with the next lower bit added, kept when its fade is within the budget.
    That finds the largest such level because the estimate of the faded bytes never falls
    as the level rises; a candidate of 255 is the bytes as they are, above the budget."""
    if budget <= 0 or sum(estimate(part) for part in parts) <= budget:
        return UNDIMMED
    if budget <= sum(len(part) // 3 for part in parts) * REST_MA:
        return 1
    found = 0
    for bit in (1 << shift for shift in range(FADES - 1, -1, -1)):
        candidate = found + bit
        if sum(estimate(fade(part, candidate)) for part in parts) <= budget:
            found = candidate
    return max(found, 1)


@dataclasses.dataclass(frozen=True)
class Limited:
    """What one refresh sends after its limiting."""

    legs: tuple[bytes, ...]       # the bytes sent, for each leg
    estimates: tuple[int, ...]    # the estimate of each leg's bytes sent, in mA
    limited: tuple[bool, ...]     # whether a level below 255 was used for the leg
    wall_estimate: int            # the sum of the legs' estimates
    wall_limited: bool            # whether the wall's level was below 255


def limit(legs, budgets, wall):
    """Applies the budgets to the bytes of one refresh, given for each leg, with each
    leg's budget and the wall's.

    First each leg is faded by its own budget. Then every leg is faded by the wall's level,
    found from the bytes the legs' own budgets left. The wall's fade can raise a low even
    byte by 1, so last a leg that its own pass brought within its budget, and that the
    wall's fade took above it, is faded again by its own rule from the bytes the wall left.
    A leg that its own pass left above its budget, at level 1, is not faded at level 1 a
    second time. A leg is limited when a level below 255 was used for it in either of its
    passes, the wall when its level was below 255."""
    legs = [bytes(data) for data in legs]
    budgets = list(budgets)
    if len(budgets) != len(legs):
        raise ValueError(f"{len(legs)} legs and {len(budgets)} budgets")
    limited = [False] * len(legs)
    within = [True] * len(legs)
    for i, budget in enumerate(budgets):
        used = level(legs[i], budget)
        if used < UNDIMMED:
            legs[i] = fade(legs[i], used)
            limited[i] = True
        within[i] = budget <= 0 or estimate(legs[i]) <= budget
    used = wall_level(legs, wall)
    wall_limited = used < UNDIMMED
    if wall_limited:
        legs = [fade(data, used) for data in legs]
        for i, budget in enumerate(budgets):
            if budget > 0 and within[i] and estimate(legs[i]) > budget:
                legs[i] = fade(legs[i], level(legs[i], budget))
                limited[i] = True
    estimates = tuple(estimate(data) for data in legs)
    return Limited(tuple(legs), estimates, tuple(limited), sum(estimates), wall_limited)


@dataclasses.dataclass(frozen=True)
class Budgets:
    """The budgets of a `limits.json`: the wall's, and those of the legs it names, as
    `(leg, mA)` in the file's order."""

    wall: int
    legs: tuple[tuple[int, int], ...]

    def of(self, leg):
        """The budget of a leg; 0 for a leg the file does not name."""
        return dict(self.legs).get(leg, 0)


def read(path):
    """Reads a budgets' file. A file that is absent is `not-found`."""
    data = files.read(path)
    with errors.naming(path):
        return loads(data)


def loads(data):
    """Reads a budgets' file given as bytes, as strictly as the core reads it: exactly the
    members `version`, 1, `wall`, 0 to 250,000, and `legs`, each entry an array of a leg
    number from 1 to 255 and its budget from 0 to 65,535, no leg named twice. Every broken
    rule is `limits-malformed`."""
    try:
        return _budgets(data)
    except errors.Rejection as rejection:
        if rejection.reason == errors.LIMITS_MALFORMED:
            raise
        raise errors.Rejection(errors.LIMITS_MALFORMED, f"{rejection.reason}: {rejection.detail}") from None


def _malformed(detail):
    return errors.Rejection(errors.LIMITS_MALFORMED, detail)


def _budgets(data):
    top = strictjson.loads(data)
    strictjson.members(top, _MEMBERS)
    version = strictjson.integer(top["version"], what="version")
    if version != VERSION:
        raise errors.Rejection(errors.BAD_VERSION, f"version is {version}, not {VERSION}")
    wall = strictjson.integer(top["wall"], 0, LARGEST_WALL, what="wall")
    legs = []
    seen = set()
    for place, entry in enumerate(strictjson.array(top["legs"], what="legs"), 1):
        what = f"entry {place} of legs"
        strictjson.array(entry, what=what)
        if len(entry) != 2:
            raise _malformed(f"{what} has {len(entry)} values, not a leg and its budget")
        leg = strictjson.integer(entry[0], 1, LARGEST_LEG, what=f"the leg of {what}")
        budget = strictjson.integer(entry[1], 0, LARGEST_BUDGET, what=f"the budget of leg {leg}")
        if leg in seen:
            raise _malformed(f"leg {leg} is named twice")
        seen.add(leg)
        legs.append((leg, budget))
    return Budgets(wall, tuple(legs))


def dumps(wall, legs):
    """The bytes the core writes for the wall's budget and the legs' budgets, given as
    `(leg, mA)` in the order to write them: one line of JSON without spaces, which leaves
    out every leg whose budget is 0."""
    if type(wall) is not int or not 0 <= wall <= LARGEST_WALL:
        raise ValueError(f"the wall's budget {wall!r} is not from 0 to {LARGEST_WALL}")
    written = []
    seen = set()
    for leg, budget in legs:
        if type(leg) is not int or not 1 <= leg <= LARGEST_LEG or leg in seen:
            raise ValueError(f"the leg {leg!r} is not from 1 to {LARGEST_LEG} or is named twice")
        if type(budget) is not int or not 0 <= budget <= LARGEST_BUDGET:
            raise ValueError(f"the budget {budget!r} of leg {leg} is not from 0 to {LARGEST_BUDGET}")
        seen.add(leg)
        if budget > 0:
            written.append(f"[{leg},{budget}]")
    return f'{{"version":{VERSION},"wall":{wall},"legs":[{",".join(written)}]}}\n'.encode("ascii")
