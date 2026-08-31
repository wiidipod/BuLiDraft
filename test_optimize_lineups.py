import unittest

from optimize_lineups import chat_id_for_manager, format_league, human_format, market_number, pick_lineup


class LineupTest(unittest.TestCase):
    def test_selects_highest_values_and_captain(self):
        values = {"g1": 2, "g2": 1, "d1": 1, "d2": 2, "d3": 3, "d4": 4, "m1": 1, "m2": 2, "m3": 3, "m4": 4, "m5": 5, "m6": 99, "f1": 1, "f2": 2, "f3": 9}
        squad = [(player_id, position) for position, ids in {"GK": ["g1", "g2"], "DEF": ["d1", "d2", "d3", "d4"], "MID": ["m1", "m2", "m3", "m4", "m5", "m6"], "FWD": ["f1", "f2", "f3"]}.items() for player_id in ids]

        lineup, bench = pick_lineup(squad, lambda player_id: {"id": player_id, "name": player_id, "market_value": values[player_id], "status": "1" if player_id in {"d3", "d4", "m6"} else "0", "value": values[player_id]})

        self.assertEqual(11, len(lineup))
        self.assertEqual(4, len(bench))
        self.assertIn("d4", [player["id"] for player in lineup])
        self.assertIn("d3", [player["id"] for player in bench])
        self.assertIn("m6", [player["id"] for player in bench])
        message = format_league("Test", lineup, bench)
        self.assertIn("<code>FWD</code> <code> 9.00</code> ✅ <b><u>f3 C 👑</u></b>", message)
        self.assertIn("<code>DEF</code> <code> 3.00</code> 🚑 d3", message)
        self.assertEqual(15, sum(line.startswith("<code>") for line in message.splitlines()))
        self.assertEqual(5, message.count("\n\n"))

    def test_parses_common_market_value_formats(self):
        self.assertEqual(7_500_000, market_number("7,5m"))
        self.assertEqual(7_500_000, market_number("7.500.000"))
        self.assertEqual("  7.50M", human_format(7_500_000))
        self.assertEqual(" 20.0 M", human_format(20_000_000))
        self.assertEqual("999   M", human_format(999_000_000))

    def test_maps_manager_to_chat_id(self):
        self.assertEqual("66421324", chat_id_for_manager("wiidipod"))


if __name__ == "__main__":
    unittest.main()
