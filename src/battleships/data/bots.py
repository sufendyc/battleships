import motor
import pymongo
import time
import tornado.gen
from battleships.conf import Conf


class BotsDataAsync(object):
    """Async access to the bots data, used by the tornado server.

    Requires the following indices:

        * user_id / ascending
   
    """

    def __init__(self, db):
        self._conn = db.bots

    @tornado.gen.coroutine
    def read(self, bot_id):
        doc = yield motor.Op(self._conn.find_one, bot_id)
        raise tornado.gen.Return(doc)

    _MAX_BOTS = 100
    @tornado.gen.coroutine
    def read_by_user(self, user_id):
        cursor = self._conn.find({"user_id": user_id}).sort("created_time")
        result = yield motor.Op(cursor.to_list, length=self._MAX_BOTS)
        raise tornado.gen.Return(result) 

    @tornado.gen.coroutine
    def add(self, bot_id, user_id):
        now = long(time.time())
        doc = {
            "_id":              bot_id,
            "user_id":          user_id,
            "created_time":     now,
            "state":            _State.PENDING,
            }
        yield motor.Op(self._conn.save, doc)


class BotsDataSync(object):
    """Sync access to the bots data, used by the worker process."""

    @classmethod
    def _get_conn(cls):
        if not hasattr(cls, "_conn"):
            cls._conn = pymongo.MongoClient(
                host=Conf["mongodb"]["host"],
                port=Conf["mongodb"]["port"],
                ).battleships.bots
        return cls._conn

    @classmethod
    def score_success(cls, bot_id, score):
        doc = cls._get_conn().find_one(bot_id)
        doc.update({
            "state":        _State.SCORE_SUCCESS,
            "score":        score,
            })
        cls._get_conn().save(doc)

    @classmethod
    def score_error(cls, bot_id, game_seed):
        doc = cls._get_conn().find_one(bot_id)
        doc.update({
            "state":        _State.SCORE_ERROR,
            "game_seed":    game_seed,
            })
        cls._get_conn().save(doc)


class _State(object):
    """The different states that a bot can be in."""
    PENDING =           "pending"
    SCORE_SUCCESS =     "success"
    SCORE_ERROR =       "error"

