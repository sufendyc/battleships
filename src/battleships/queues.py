import logging
import os.path
from battleships.conf import Conf
from battleships.engine.battleships2 import BattleshipsGame
from battleships.player import Player
from battleships.scorer import Scorer
from bson.objectid import ObjectId
from cache import CacheBotGame
from multiprocessing import Process, Queue
from Queue import Full


class QueueBotGame(object):
    """Fast moving queue for evaluating individual games for the purpose of
    visualisation.
    """

    # limit the queue to prevent excess memory consumption in the event of the
    # queue backing up due to an error
    _q = Queue(maxsize=100)

    _log = logging.getLogger("queue-bot-game")

    @classmethod
    def start(cls):
        """Spawn a separate process to process the queue."""
        p = Process(target=cls._work, args=(cls._q,))
        p.daemon = True # terminate when the process process ends
        p.start()

    @classmethod
    def add(cls, bot_id, seed):
        """Add a bot to the queue to be played."""
        cls._log.info("%s queued" % bot_id)
        token = str(ObjectId())
        msg = (token, bot_id, seed)
        try:
            cls._q.put_nowait(msg)
            return token

        except Full:
            cls._log.critical("queue full")
            raise Exception("Bot game queue is full")

    @classmethod
    def _work(cls, q):
        while True:
            msg = q.get()
            token, bot_id, seed = msg
            bot_path = _get_bot_path(bot_id)
            result = Player(BattleshipsGame).play(bot_path, seed)
            CacheBotGame.add(token, result)
            cls._log.info("%s played" % bot_id)


class QueueBotScoring(object):
    """Slow moving queue for scoring bots.

    Bots are scored by playing them in a several games (a tournament) and
    taking an average of the number of moves taken to complete each game.
    """

    # limit the queue to prevent excess memory consumption in the event of the
    # queue backing up due to an error
    _q = Queue(maxsize=500)

    _log = logging.getLogger("queue-bot-scoring")

    @classmethod
    def start(cls):
        """Spawn a separate process to process the queue."""
        p = Process(target=cls._work, args=(cls._q,))
        p.daemon = True # terminate when the process process ends
        p.start()

    @classmethod
    def add(cls, user_id, bot_id):
        """Add a bot to the queue to be scored."""
        cls._log.info("%s queued" % bot_id)
        msg = (user_id, bot_id)
        try:
            cls._q.put_nowait(msg)
        except Full:
            cls._log.critical("queue full")
            raise Exception("Scoring queue is full")

    @classmethod
    def _work(cls, q):
        while True:
            msg = q.get()
            user_id, bot_id = msg
            bot_path = _get_bot_path(bot_id)
            Scorer.score(user_id, bot_id, bot_path)
            cls._log.info("%s scored" % bot_id)


def _get_bot_path(bot_id):
    return os.path.join(Conf["bot-path"], str(bot_id))