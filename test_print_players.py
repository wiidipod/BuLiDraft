import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

import print_players


class PrintPlayersTest(unittest.TestCase):
    def test_prints_player_name_and_id(self):
        with patch.object(print_players, "fetch_player", lambda player_id: {"name": f"Player {player_id}"}):
            output = io.StringIO()
            with redirect_stdout(output):
                print_players.main()

        self.assertIn("Boardgames go Football/A3rYs", output.getvalue())
        self.assertIn("GK Player 1873 (1873)", output.getvalue())


if __name__ == "__main__":
    unittest.main()
