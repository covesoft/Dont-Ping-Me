import unittest

from nuhuh.engine import Game
from nuhuh.helptext import mention_kind
from nuhuh.phrases import PhraseBook


class HelpTests(unittest.TestCase):
    def test_exact_help_and_extra_help_are_distinct(self):
        cases = {
            "<@99> help": "help",
            " \n<@!99> HELP\t ": "help",
            "<@99> help me please": "help_extra",
            "<@99> help!": "help_extra",
            "<@99> help\nplease": "help_extra",
            "<@99> help <@99>": "help_extra",
            "<@99> helpful": "ping",
            "<@99> helpme": "ping",
            "before <@99> help": "ping",
            "<@12> help": "ping",
            "<@99>": "ping",
        }
        for content, expected in cases.items():
            with self.subTest(content=content):
                self.assertEqual(mention_kind(content, 99), expected)

    def test_help_does_not_create_participants_or_consume_first_contact(self):
        with Game(PhraseBook.load()) as game:
            for user in range(1, 7):
                self.assertEqual(game.help(1, user, now=1000).count, 0)
            self.assertEqual(game.ping(1, 7, now=1005).event_id, "first_guild_ping")
            second = game.ping(1, 1, now=1005)
            self.assertEqual((second.event_id, second.other_users), ("first_user_ping", 1))

    def test_help_experience_is_guild_specific_and_does_not_change_ping_timing(self):
        with Game(PhraseBook.load()) as game:
            game.ping(1, 1, now=1000)
            self.assertEqual(game.help(1, 1, now=87400).count, 1)
            self.assertEqual(game.help(2, 1, now=87400).count, 0)
            reply = game.ping(1, 1, now=87401)
            self.assertEqual((reply.count, reply.event_id), (2, "returning_user"))

    def test_help_and_pings_share_message_replay_protection(self):
        with Game(PhraseBook.load()) as game:
            game.help(1, 1, now=1000, message_id=10)
            self.assertIsNone(game.help(1, 1, now=1001, message_id=10))
            self.assertIsNone(game.ping(1, 1, now=1001, message_id=10))
            self.assertEqual(game.ping(1, 1, now=1002, message_id=11).count, 1)

    def test_extra_help_counts_and_overrides_context_events(self):
        with Game(PhraseBook.load()) as game:
            first = game.ping(1, 1, now=1000, response_event="help_extra")
            self.assertEqual((first.count, first.event_id), (1, "help_extra"))
            game.delivered(first)
            second = game.ping(1, 1, now=1001, response_event="help_extra")
            self.assertEqual((second.count, second.event_id), (2, "help_extra"))
            self.assertNotEqual(first.phrase_id, second.phrase_id)

    def test_disabled_help_extra_pool_falls_back_to_normal_play(self):
        book = PhraseBook.load()
        book = PhraseBook(book.tiers, tuple(pool for pool in book.events if pool.id != "help_extra"), book.rules)
        with Game(book) as game:
            reply = game.ping(1, 1, response_event="help_extra")
            self.assertEqual((reply.count, reply.event_id), (1, "first_guild_ping"))
