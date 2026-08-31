#!/usr/bin/env python3
"""Print player names and IDs for every squad CSV."""

from pathlib import Path

from optimize_lineups import fetch_player, read_squad


def main():
    root = Path(__file__).resolve().parent
    for path in sorted((root / "Leagues").glob("*/*.csv")):
        print(f"{path.parent.name}/{path.stem}")
        for player_id, position in read_squad(path):
            print(f"{position} {fetch_player(player_id)['name']} ({player_id})")
        print()


if __name__ == "__main__":
    main()
