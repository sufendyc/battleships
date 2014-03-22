#!/usr/bin/python
"""Run a bot locally in the console during development."""

import argparse
import os
import os.path
import pprint
from battleships.engine.battleships import BattleshipsGame
from battleships.player import Player


def run_locally():

    parser = argparse.ArgumentParser(
        description="Run bots locally during development.")
    parser.add_argument(
        "-hs", action="store_true", help="include full game history in output")
    parser.add_argument(
        "-r", action="store_true", help="raw output, not pretty printed")
    parser.add_argument(
        "--seed", type=float, help="game seed for deterministic game play",
        metavar="")
    parser.add_argument(
        "game_class", help="the game class to use (eg. 'Battleships')")
    parser.add_argument(
        "bot_path", help="the path of the bot file to use")
    args = parser.parse_args()

    available_games = {
        "battleships":  BattleshipsGame,
        }

    try:
        game_class = available_games[args.game_class]
    except KeyError:
        print "The game class doesn't exist"
        return
    if not os.path.isfile(args.bot_path):
        print "The bot path doesn't exist"
        return
    if not os.access(args.bot_path, os.X_OK):
        print "The bot isn't executable"
        return

    result = Player(game_class).play(args.bot_path, args.seed)

    # remove the history data from the game result unless explicitly requested
    # by the user, because it's big
    if not args.hs:
        del result["history"]

    if args.r: # raw output
        print result
    else:
        pprint.pprint(result)

if __name__ == "__main__":
    run_locally()
