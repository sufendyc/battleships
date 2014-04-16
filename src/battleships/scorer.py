import logging

from battleships.conf import Conf
from battleships.data.bots import BotsDataSync as BotsData
from battleships.data.users import UsersDataSync as UsersData
from battleships.engine.battleships2 import BattleshipsGame
from battleships.player import Player
import time

class Scorer(object):
    """Score a bot by playing it against a number of games and taking the
    average score.

    The user and bot records are updated following the scoring.
    """

    _log = logging.getLogger("tournament")

    @classmethod
    def score(cls, user_id, bot_id, bot_path):

        num_games = Conf["num-games-per-tournament"]

        try:
            # run games
            runner_game = Player(BattleshipsGame)
            scores = []
            times = []
            for i in range(num_games):
                start_time = time.time()
                game_result = runner_game.play(bot_path)
                if not game_result["success"]:
                    raise _ScoringException(game_result)

                times.append(time.time() - start_time)
                scores.append(game_result["score"])
                cls._log.info("%s played %s/%s" % (bot_path, i+1, num_games))

            # update database with success
            score = sum(scores) / float(num_games) # average
            avg_time = sum(times) / float(num_games)
            BotsData.score_success(bot_id, score, avg_time)
            UsersData.set_state_to_scored_success(user_id, bot_id, score, avg_time)

        except _ScoringException as e:
            cls._log.warning("%s scoring aborted: %s" % \
                (bot_id, e.game_result["error_type"]))

            # update database with failure
            BotsData.score_error(bot_id, e.game_result["game_seed"])
            UsersData.set_state_to_scored_error(user_id)


class _ScoringException(Exception):
    """During scoring the bot raised an error."""

    def __init__(self, game_result):
        self.game_result = game_result