#!/usr/bin/env python3
"""Send the highest-market-value 3-4-3 lineup for every file in Leagues/."""

import argparse
import csv
import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


FORMATION = {"GK": 1, "DEF": 3, "MID": 4, "FWD": 3}
API_URL = "https://www.base-xi.de/api/modal/player/{}"
TELEGRAM_URL = "https://api.telegram.org/bot{}/sendMessage"
CHAT_IDS = {
    "wiidipod": "66421324",
    "A3rYs": "66421324",
}


def json_value(data, key):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            found = json_value(value, key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = json_value(value, key)
            if found is not None:
                return found
    return None


def market_number(value):
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower().replace(" ", "").replace("€", "")
    multiplier = 1_000_000 if text.endswith(("m", "mio.")) else 1
    text = re.sub(r"(mio\.|m)$", "", text)
    if "." in text and "," in text:
        decimal = "." if text.rfind(".") > text.rfind(",") else ","
        text = text.replace("," if decimal == "." else ".", "").replace(decimal, ".")
    elif multiplier == 1 and re.fullmatch(r"\d{1,3}([.,]\d{3})+", text):
        text = text.replace(".", "").replace(",", "")
    else:
        text = text.replace(",", ".")
    return float(text) * multiplier


def human_format(num):
    num = float("{:.3g}".format(num))
    magnitude = 0
    while abs(num) >= 1000:
        magnitude += 1
        num /= 1000.0
    digits = len(str(int(abs(num))))
    value = f"{num:.{max(0, 3 - digits)}f}"
    return f"{' ' * (3 - digits)}{value}{' ' * (digits * (digits - 1) // 2)}{['', 'K', 'M', 'B', 'T'][magnitude]}"


def fetch_player(player_id):
    request = Request(API_URL.format(player_id), headers={"User-Agent": "BuLiDraft/1.0"})
    with urlopen(request, timeout=20) as response:
        data = json.load(response)
    name, market_value, status = json_value(data, "name"), json_value(data, "marketValue"), json_value(data, "status")
    if not name or market_value is None or status is None:
        raise ValueError(f"player {player_id}: missing name, marketValue, or status")
    return {"id": player_id, "name": str(name), "market_value": market_value, "status": status, "value": market_number(market_value)}


def read_squad(path):
    squad = []
    with path.open(newline="", encoding="utf-8") as file:
        for line, row in enumerate(csv.reader(file), 1):
            if len(row) != 2 or row[1].strip().upper() not in FORMATION or not row[0].strip().isdigit():
                raise ValueError(f"{path}:{line}: expected PLAYER_ID,GK|DEF|MID|FWD")
            squad.append((row[0].strip(), row[1].strip().upper()))
    return squad


def chat_id_for_manager(manager):
    try:
        return CHAT_IDS[manager]
    except KeyError:
        raise ValueError(f"no chat_id configured for manager {manager}") from None


def pick_lineup(squad, fetch=fetch_player):
    players = defaultdict(list)
    for player_id, position in squad:
        player = fetch(player_id)
        player["position"] = position
        player["available"] = str(player["status"]) == "0"
        players[position].append(player)
    for position, count in FORMATION.items():
        if len(players[position]) < count:
            raise ValueError(f"need {count} {position}, found {len(players[position])}")
        players[position].sort(key=lambda player: (player["available"], player["value"]), reverse=True)
    lineup = [player for position, count in FORMATION.items() for player in players[position][:count]]
    bench = [player for position in FORMATION for player in players[position][FORMATION[position]:]]
    return lineup, bench


def format_player(player, captain):
    name = html.escape(player["name"].split(maxsplit=1)[-1])
    if player["id"] == captain["id"]:
        name = f"<b><u>{name} C 👑</u></b>"
    status = "✅" if player["available"] else "🚑"
    value = human_format(player["value"]).removeprefix(" ")
    return f"<code>{player['position']:<3}</code> <code>{value}</code> {status} {name}"


def format_players(players, captain, separator="\n\n"):
    return separator.join(
        "\n".join(format_player(player, captain) for player in players if player["position"] == position)
        for position in FORMATION
        if any(player["position"] == position for player in players)
    )


def format_league(name, lineup, bench):
    captain = max(lineup, key=lambda player: player["value"])
    bench_players = format_players(bench, captain, "\n")
    return (
        f"<b>{html.escape(name)}</b>\n\n"
        f"<b>Lineup</b>\n{format_players(lineup, captain)}\n\n"
        f"<b>Bench</b>\n{bench_players}"
    )


def send_telegram(token, chat_id, text):
    body = urlencode({"chat_id": chat_id, "text": text, "parse_mode": "HTML"}).encode()
    with urlopen(Request(TELEGRAM_URL.format(token), data=body), timeout=20) as response:
        result = json.load(response)
    if not result.get("ok"):
        raise RuntimeError("Telegram rejected the message")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="print messages instead of sending them")
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    league_files = sorted((root / "Leagues").glob("*/*.csv"))
    if not league_files:
        raise FileNotFoundError("no squad files found in Leagues/*/")
    token = (root / "token").read_text(encoding="utf-8").strip()
    if not token and not args.dry_run:
        raise ValueError("token is empty")
    for path in league_files:
        chat_id = chat_id_for_manager(path.stem)
        lineup, bench = pick_lineup(read_squad(path))
        message = format_league(path.parent.name, lineup, bench)
        if args.dry_run:
            print(message)
        else:
            send_telegram(token, chat_id, message)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        sys.exit(f"Error: {error}")
