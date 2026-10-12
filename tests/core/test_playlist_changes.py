import json
import unittest

from . import support
from .test_content import OK, refused
from .test_playback import T0, refreshes
from .test_playlist import CANVAS, CYCLE, loop_of, show_of, three, with_a_cycle
from .test_upload import Script, Uploads

# An animation whose turn is one loop.
ONCE = {"repeat": 1}


class Session(Script):
    """A script against a clock that can be set."""

    def at(self, time):
        """Moves the clock to this time after power-on."""
        assert T0 + time >= self.time
        self.time = T0 + time
        return self

    def seen(self):
        """A refresh at the time of the clock, and `status` after it."""
        self.lines.append(f"poll {self.time}")
        self.polled = self.time
        return self.line("status")


def first_picture(data):
    """The LED data of the first refresh of a show that has this animation alone."""
    files = show_of([{"id": 1, "file": "alone.odrg"}], {"alone.odrg": data})
    produced, _ = refreshes(support.start(files, [f"poll {T0}"]).lines)
    return produced[0][1][1]


class Changes(Uploads):
    def seen(self, files, session):
        """What `status` says plays and what is on the LEDs, for each `status` of a session
        that runs on the core and on the reference player alike."""
        given = self.play(files, session)
        return [(json.loads(reply)["playing"], json.loads(reply)["animation"]) for text, reply in zip(self.sent, given) if text == "status"]

    def pictures(self):
        """The LED data of each refresh of the session, by its time after power-on."""
        produced, _ = refreshes([line for line in self.printed if line.startswith(("refresh", "data", "idle"))])
        return {time - T0: legs[1] for time, legs in produced}

    def items_left(self):
        return json.loads(self.left["show.json"])["items"]


class AnItemIsAdded(Changes):
    def test_a_new_animation_has_its_turn_after_the_last_one(self):
        # Turns of 4, 10 and 45 seconds. The new animation, 2 seconds long, has no numbers
        # of its own: 15 loops, from 59,000 to 89,000 ms.
        files = three(ONCE, ONCE, ONCE)
        new = loop_of(2, 9)
        session = Session().polls(1).at(1000).upload(9, "new.odrg", new).line("list")
        for time in (3980, 4000, 58980, 59000, 88980, 89000):
            session.at(time).seen()
        self.assertEqual(self.seen(files, session), [("all", 1), ("all", 2), ("all", 3), ("all", 9), ("all", 9), ("all", 1)])
        self.assertEqual(self.answers("upload end"), [OK])
        self.assertEqual([item["id"] for item in json.loads(self.answers("list")[0])["items"]], [1, 2, 3, 9])
        self.assertEqual(self.pictures()[59000], first_picture(new))
        self.assertEqual(self.items_left()[-1], {"id": 9, "file": "new.odrg"})

    def test_the_upload_of_a_new_animation_does_not_disturb_the_turn_it_falls_into(self):
        files = three()
        new = loop_of(2, 9)
        with_upload = Session().polls(50).upload(9, "new.odrg", new).polls(100)
        self.play(files, with_upload)
        added = self.pictures()
        self.play(files, Session().polls(len(added)))
        self.assertEqual(added, self.pictures())

    def test_into_a_show_without_an_animation_it_starts_the_playlist(self):
        first, second = loop_of(2, 5), loop_of(3, 6)
        session = Session().polls(1).line("status").at(1000).upload(5, "first.odrg", first).line("status")
        began = session.time - T0
        session.seen().at(began + 20).upload(7, "second.odrg", second)
        # Each has the fewest loops that last 30 seconds: 15 of 2 seconds, 10 of 3.
        for time in (began + 29980, began + 30000, began + 59980, began + 60000):
            session.at(time).seen()
        seen = self.seen(show_of([], {}), session)
        self.assertEqual(seen, [(None, None), ("all", 5), ("all", 5), ("all", 5), ("all", 7), ("all", 7), ("all", 5)])
        self.assertEqual(self.pictures()[began], first_picture(first))
        self.assertEqual(self.pictures()[began + 30000], first_picture(second))
        self.assertEqual(self.items_left(), [{"id": 5, "file": "first.odrg"}, {"id": 7, "file": "second.odrg"}])

    def test_after_the_last_animation_was_removed_an_upload_starts_the_playlist_again(self):
        files = show_of([{"id": 1, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)})
        new = loop_of(2, 9)
        session = Session().polls(1).at(1000).line("remove 1").seen().at(2000).upload(4, "new.odrg", new).seen()
        self.assertEqual(self.seen(files, session), [(None, None), ("all", 4)])
        self.assertEqual(self.pictures()[session.time - T0], first_picture(new))

    def test_while_a_cycle_plays_a_new_animation_leaves_the_cycle_playing(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        session = Session().polls(1).at(1000).upload(9, "new.odrg", loop_of(2, 9)).seen()
        self.assertEqual(self.seen(files, session), [(8, 3)])


class AnAnimationIsReplaced(Changes):
    def test_onto_the_animation_whose_turn_it_is_the_turn_begins_again(self):
        # At 10 seconds, in the turn of animation 1. The new animation is 2 seconds long:
        # its 15 loops begin at the refresh after the upload's end.
        new = loop_of(2, 9)
        session = Session().polls(1).at(10000).upload(1, "four.odrg", new)
        began = session.time - T0
        for time in (began, began + 29980, began + 30000):
            session.at(time).seen()
        self.assertEqual(self.seen(three(), session), [("all", 1), ("all", 1), ("all", 2)])
        self.assertEqual(self.pictures()[began], first_picture(new))
        self.assertEqual(self.left["four.odrg"], new)

    def test_under_another_name_the_item_keeps_its_numbers_and_the_turn_begins_again(self):
        # Twenty loops, whatever the animation: 80 seconds before, 40 seconds after.
        new = loop_of(2, 9)
        session = Session().polls(1).at(10000).upload(1, "other.odrg", new)
        began = session.time - T0
        for time in (began, began + 39980, began + 40000):
            session.at(time).seen()
        self.assertEqual(self.seen(three(first={"repeat": 20}), session), [("all", 1), ("all", 1), ("all", 2)])
        self.assertEqual(self.pictures()[began], first_picture(new))
        self.assertEqual(self.items_left()[0], {"id": 1, "file": "other.odrg", "repeat": 20})
        self.assertNotIn("four.odrg", self.left)

    def test_onto_another_animation_the_turn_goes_on_and_the_new_one_plays_when_its_turn_comes(self):
        new = loop_of(2, 9)
        with_upload = Session().polls(50).upload(2, "ten.odrg", new).polls(100)
        self.play(three(), with_upload)
        replaced = self.pictures()
        self.play(three(), Session().polls(len(replaced)))
        self.assertEqual(replaced, self.pictures())
        # The turn of animation 1 ends at 32 seconds, and the new animation has 15 loops.
        session = Session().polls(1).at(10000).upload(2, "ten.odrg", new)
        for time in (31980, 32000, 61980, 62000):
            session.at(time).seen()
        self.assertEqual(self.seen(three(), session), [("all", 1), ("all", 2), ("all", 2), ("all", 3)])
        self.assertEqual(self.pictures()[32000], first_picture(new))


class AnItemLeaves(Changes):
    def test_the_animation_whose_turn_it_is_leaves_and_the_playlist_goes_on_with_the_one_after_it(self):
        files = three(ONCE, ONCE, ONCE)
        session = Session().polls(1).at(980).seen().at(1000).line("remove 1").seen()
        # The 10 seconds of animation 2 begin at 1,000, then the 45 of animation 3, and
        # after it animation 2 again.
        for time in (10980, 11000, 55980, 56000, 65980, 66000):
            session.at(time).seen()
        self.assertEqual(self.seen(files, session), [("all", 1), ("all", 2), ("all", 2), ("all", 3), ("all", 3), ("all", 2), ("all", 2), ("all", 3)])
        self.assertEqual(self.answers("remove"), [OK])
        self.assertEqual(self.pictures()[1000], first_picture(files["ten.odrg"]))
        self.assertEqual([item["id"] for item in self.items_left()], [2, 3])
        self.assertNotIn("four.odrg", self.left)

    def test_after_the_last_animation_of_the_order_comes_the_first(self):
        files = three(ONCE, ONCE, ONCE, start=3)
        session = Session().polls(1).at(1000).line("remove 3").seen().at(4980).seen().at(5000).seen()
        self.assertEqual(self.seen(files, session), [("all", 1), ("all", 1), ("all", 2)])
        self.assertEqual(self.pictures()[1000], first_picture(files["four.odrg"]))

    def test_an_animation_before_the_one_whose_turn_it_is_leaves_and_the_turn_goes_on(self):
        files = three(ONCE, ONCE, ONCE, start=2)
        with_removal = Session().polls(50).line("remove 1").polls(100)
        self.play(files, with_removal)
        removed = self.pictures()
        self.play(files, Session().polls(len(removed)))
        self.assertEqual(removed, self.pictures())
        # Animation 2 from 0 to 10 seconds, animation 3 to 55, and then animation 2 again.
        session = Session().polls(1).at(1000).line("remove 1")
        for time in (9980, 10000, 54980, 55000):
            session.at(time).seen()
        self.assertEqual(self.seen(files, session), [("all", 2), ("all", 3), ("all", 3), ("all", 2)])

    def test_an_animation_after_the_one_whose_turn_it_is_leaves_and_has_no_turn(self):
        files = three(ONCE, ONCE, ONCE)
        with_removal = Session().polls(50).line("remove 2").polls(100)
        self.play(files, with_removal)
        removed = self.pictures()
        self.play(files, Session().polls(len(removed)))
        self.assertEqual(removed, self.pictures())
        session = Session().polls(1).at(1000).line("remove 2")
        for time in (3980, 4000, 48980, 49000):
            session.at(time).seen()
        self.assertEqual(self.seen(files, session), [("all", 1), ("all", 3), ("all", 3), ("all", 1)])

    def test_the_last_animation_of_the_show_leaves_and_nothing_plays(self):
        files = show_of([{"id": 1, "file": "four.odrg"}], {"four.odrg": loop_of(4, 1)})
        session = Session().polls(1).at(980).seen().at(1000).line("remove 1").seen().at(1020).seen().line("play all", "space")
        self.assertEqual(self.seen(files, session), [("all", 1), (None, None), (None, None)])
        shown = self.pictures()
        self.assertTrue(any(shown[980]))
        self.assertEqual((shown[1000], shown[1020]), (bytes(3 * CANVAS[0] * CANVAS[1]),) * 2)
        self.assertEqual(self.answers("play all"), [refused("unknown-id")])
        self.assertEqual(json.loads(self.answers("space")[0])["animations"], 0)
        self.assertEqual(json.loads(self.given[-3])["error"], None)

    def test_the_cycle_that_plays_leaves_and_the_playlist_plays_from_its_first_animation(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        session = Session().polls(1).at(980).seen().at(1000).line("remove 8").seen().at(32980).seen().at(33000).seen()
        self.assertEqual(self.seen(files, session), [(8, 3), ("all", 1), ("all", 1), ("all", 2)])
        self.assertEqual(self.pictures()[1000], first_picture(files["four.odrg"]))
        self.assertNotIn("start", json.loads(self.left["show.json"]))

    def test_a_cycle_that_does_not_play_leaves_and_the_playlist_goes_on(self):
        files = with_a_cycle(three(), CYCLE, first=True)
        with_removal = Session().polls(50).line("remove 8").polls(100)
        self.play(files, with_removal)
        removed = self.pictures()
        self.play(files, Session().polls(len(removed)))
        self.assertEqual(removed, self.pictures())
        session = Session().polls(1).at(1000).line("remove 8").seen().at(32000).seen()
        self.assertEqual(self.seen(files, session), [("all", 1), ("all", 2)])

    def test_an_animation_leaves_while_a_cycle_plays_and_the_cycle_goes_on(self):
        files = with_a_cycle(three(), CYCLE, start=8)
        with_removal = Session().polls(50).line("remove 2").polls(150)
        self.play(files, with_removal)
        removed = self.pictures()
        self.play(files, Session().polls(len(removed)))
        self.assertEqual(removed, self.pictures())
        session = Session().polls(1).at(1000).line("remove 2").seen().at(2000).seen()
        self.assertEqual(self.seen(files, session), [(8, 3), (8, 1)])

    def test_an_animation_that_a_cycle_lists_is_still_in_use(self):
        files = with_a_cycle(three(), CYCLE)
        session = Session().polls(1).at(1000).line("remove 1", "remove 3").seen().at(32000).seen().at(62000).seen().at(107000).seen()
        self.assertEqual(self.seen(files, session), [("all", 1), ("all", 2), ("all", 3), ("all", 1)])
        self.assertEqual(self.answers("remove"), [refused("in-use")] * 2)
        self.assertEqual([item["id"] for item in self.items_left()], [1, 2, 3, 8])

    def test_switched_off_the_animation_after_the_one_that_left_begins_at_the_next_refresh(self):
        files = three(ONCE, ONCE, ONCE)
        session = Session().polls(1).at(1000).line("off", "remove 1").seen().at(10980).seen().at(11000).seen().line("on").at(11020).seen()
        self.assertEqual(self.seen(files, session), [("all", 2), ("all", 2), ("all", 3), ("all", 3)])

    def test_every_animation_leaves_one_after_the_other(self):
        session = Session().polls(1)
        for number, time in ((2, 1000), (1, 2000), (3, 3000)):
            session.at(time).line(f"remove {number}").seen()
        self.assertEqual(self.seen(three(), session), [("all", 1), ("all", 3), (None, None)])
        self.assertEqual(self.items_left(), [])
        self.assertEqual(sorted(self.left), ["mapping.json", "show.json"])


if __name__ == "__main__":
    unittest.main()
