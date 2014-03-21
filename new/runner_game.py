import random
import signal
import subprocess
import traceback
from game import Game
from game_battleships import BattleshipsGame


class GameRunner(object):

    _BOT_MOVE_TIMEOUT = 10 # max secs a bot can take to make a move

    def run(self, bot_path, game_class, game_seed=None):
        """Play a single game with a bot until the game is complete or the bot
        raises an error.

        A `game_seed` can be provided to ensure that random elements of game
        play are deterministic and therefore repeatable.
        """

        game_seed = game_seed or random.random()
        game = game_class(game_seed)

        game_state = game.get_state()
        history = [(None, None, game_state)]
        bot_request = None

        try:
            while not game.is_complete():
                bot_request = game.get_next_bot_request()
                bot_response = self._call_bot(bot_path, bot_request)
                accepted = game.update_state_with_bot_response(bot_response)
                if not accepted:
                    raise _BotIllegalMoveException(bot_response=bot_response)
                game_state = game.get_state()
                history.append((bot_request, bot_response, game_state))

            score = game.get_score()
            result = {
                "success":          True,
                "score":            score,
                "history":          history,
                "game_seed":        game_seed,
                }

        except _BotException as e:
            result = {
                "success":          False,
                "history":          history,
                "game_seed":        game_seed,
                "bot_request":      bot_request,
                "error_type":       e.error_type,
                "error_message":    e.error_message,
                }
            result.update(e.extra)

        return result

    def _call_bot(self, bot_path, bot_request):
        """Execute the bot as a separate process using the OS, passing in the
        `bot_request` string and returning the bot response string.

        Will raise an exception of type `_BotException` if the bot results in
        an error.
        """
        def alarm_handler(signum, frame):
            raise _BotMoveTimeoutException
        signal.signal(signal.SIGALRM, alarm_handler)
        signal.alarm(self._BOT_MOVE_TIMEOUT)
        try:
            return subprocess.check_output([bot_path, bot_request])
        except (subprocess.CalledProcessError, OSError):
            traceback.print_exc() # dump stack trace to console
            raise _BotErrorException
        finally:
            signal.alarm(0)


class _BotException(Exception):
    """Abstract superclass for all bot exception."""

    error_type = None
    error_message = None

    def __init__(self, **extra):
        self.extra = extra


class _BotIllegalMoveException(_BotException):
    """The bot made an illegal move."""

    error_type = "BOT_MOVE_ILLEGAL"
    error_message = "The bot made an illegal move"


class _BotMoveTimeoutException(_BotException):
    """The bot took too long to make a move."""

    error_type = "BOT_TIMEOUT"
    error_message = "The bot took too long to make a move"


class _BotErrorException(_BotException):
    """The bot encountered an error during execution (including a syntax
    error).
    """

    error_type = "BOT_ERROR"
    error_message = "The bot raised an error (maybe a syntax error)"


# TODO move to separate module
import argparse
import os.path
import pprint

def run_locally():
    """Run a bot locally during bot development."""

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

    # TODO: preload all available games into a dict and lookup by key. Safer.
    try:
        game_class = globals()[args.game_class]
    except KeyError:
        print "Can't find game class '%s'" % args.game_class
        return

    if not os.path.isfile(args.bot_path):
        print "Can't find bot '%s'" % args.bot_path
        return

    result = GameRunner().run(args.bot_path, game_class, args.seed)

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

