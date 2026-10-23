"""Rainbow test animations that light one group of three columns."""

import argparse
import sys

from .. import errors
from . import picture, run
from . import rainbow

FRAME_MS = 1000
GROUP_WIDTH = 3


def frames(width, height, group):
    """One static frame with only the selected group of columns lit."""
    first = (group - 1) * GROUP_WIDTH + 1
    if group < 1 or first > width:
        groups = (width + GROUP_WIDTH - 1) // GROUP_WIDTH
        raise errors.Rejection(errors.BAD_RANGE, f"group {group} is outside the {groups} groups")
    last = min(first + GROUP_WIDTH - 1, width)
    return [
        (
            FRAME_MS,
            picture(
                width,
                height,
                {
                    (column, row): rainbow.colour(column, row, width, height)
                    for column in range(first, last + 1)
                    for row in range(1, height + 1)
                },
            ),
        )
    ]


def _group(text):
    group = int(text)
    if group < 1:
        raise argparse.ArgumentTypeError("the group is at least 1")
    return group


def _configure(parser):
    parser.add_argument(
        "--group",
        type=_group,
        required=True,
        metavar="N",
        help="the one-based group of three columns to light",
    )


def main(argv=None):
    return run(
        "line_groups",
        "Writes one rainbow three-column test animation.",
        lambda width, height, arguments: frames(width, height, arguments.group),
        argv,
        _configure,
    )


if __name__ == "__main__":
    sys.exit(main())
