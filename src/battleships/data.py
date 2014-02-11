import motor
import pymongo
import time
import tornado.gen


class UsersDataAsync(object):
    """Async access to the users data, used by the tornado server."""

    def __init__(self, db):
        self._conn = db.users

    @tornado.gen.coroutine
    def create(self, facebook_user):
        doc = {
            "_id":                  facebook_user["id"],
            "facebook_data":        facebook_user,
            "state":                _State.NEW,
            "score_best":           {"value": None},
            }
        yield motor.Op(self._conn.insert, doc) 

    @tornado.gen.coroutine
    def read(self, user_id):
        doc = yield motor.Op(self._conn.find_one, user_id)
        raise tornado.gen.Return(doc)

    _MAX_NUM_USERS = 1000
    @tornado.gen.coroutine
    def read_ranked_users(self):
        projection = dict.fromkeys([
            "facebook_data.name", 
            "facebook_data.picture.data.url",
            "score_history", 
            "state",
            "score_best.value"], 1)
        cursor = self._conn.find({}, projection).sort("score_best.value")
        result = yield motor.Op(cursor.to_list, length=self._MAX_NUM_USERS)
        raise tornado.gen.Return(result) 

    @tornado.gen.coroutine
    def update_after_bot_submit(self, user_id, bot_id):

        user = yield motor.Op(self._conn.find_one, user_id)
        now = long(time.time())

        user["state"] = _State.PENDING
        user.setdefault("bot_history", []).append({
            "time":     now,
            "bot_id":   bot_id,
            })

        yield motor.Op(self._conn.save, user)


class UsersDataSync(object):
    """Sync access to the users data, used by the worker process."""

    _conn = pymongo.MongoClient().battleships.users 

    @classmethod
    def update_after_scoring_success(cls, user_id, bot_id, score):

        user = cls._conn.find_one(user_id)
        now = long(time.time())

        # maybe update the best score
        score_best = user["score_best"]["value"]
        if score_best is None or score < score_best: # lower is better
            is_best = True
            user["score_best"] = {
                "time":     now,
                "bot_id":   bot_id,
                "value":    score,
                }
        else:
            is_best = False

        # update the score history
        user.setdefault("score_history", []).append({
            "time":     now,
            "bot_id":   bot_id,
            "value":    score,
            "success":  True,
            })

        # update the user's state
        user["state"] = _State.BEST if is_best else _State.SUCCESS

        cls._conn.save(user)

    @classmethod
    def update_after_scoring_error(cls, user_id, bot_id, error):

        user = cls._conn.find_one(user_id)
        now = long(time.time())

        # update the score history
        user.get("score_history", []).append({
            "time":     now,
            "bot_id":   bot_id,
            "error":    str(error),
            "success":  False,
            })

        # update the user's state
        user["state"] = _State.ERROR

        cls._conn.save(user)


class _State(object):
    """The different states that a user can be in."""
    NEW =       "new"       # user is yet to submit a bot
    PENDING =   "pending"   # the user has submitted a bot but it hasn't been
                            # scored yet
    ERROR =     "error"     # the last bot submitted failed
    SUCCESS =   "success"   # the last bot submitted succeeded, but wasn't the
                            # the user's best score
    BEST =      "best"      # the last bot submitted was the user's best score

