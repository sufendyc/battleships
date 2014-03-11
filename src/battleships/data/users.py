import motor
import pymongo
import time
import tornado.gen


class UsersDataAsync(object):
    """Async access to the users data, used by the tornado server.
    
    Requires the following indices:

        * facebook_data.id / ascending
        * verify_token / ascending

    """

    def __init__(self, db):
        self._conn = db.users

    @tornado.gen.coroutine
    def bind(self, verify_token, facebook_data):
        """Using a verify token as authentication, bind a Facebook account with
        an Experian account.
        """
        if not verify_token:
            raise Exception("No verify token")
        user = yield motor.Op(
            self._conn.find_one, {"verify_token": verify_token})
        if user is None:
            raise Exception("Invalid verify token")
        if "facebook_data" in user:
            raise Exception("Verify token already used")
        user.update({
            "facebook_data":    facebook_data,
            "state":            _State.NEW,
            })
        yield motor.Op(self._conn.save, user) 
        raise tornado.gen.Return(user["_id"])

    @tornado.gen.coroutine
    def read(self, user_id):
        doc = yield motor.Op(self._conn.find_one, user_id)
        raise tornado.gen.Return(doc)

    @tornado.gen.coroutine
    def read_by_facebook_id(self, fb_user_id):
        doc = yield motor.Op(
            self._conn.find_one, {"facebook_data.id": fb_user_id})
        raise tornado.gen.Return(doc)

    _MAX_NUM_USERS = 1000
    @tornado.gen.coroutine
    def read_ranked_users(self):
        projection = dict.fromkeys([
            "facebook_data.name", 
            "facebook_data.picture.data.url",
            "state",
            "best_score.score"], 1)
        cursor = self._conn.find(
            {"facebook_data": {"$exists": True}}, # only auth'd users
            projection).sort("best_score.score")
        result = yield motor.Op(cursor.to_list, length=self._MAX_NUM_USERS)
        raise tornado.gen.Return(result) 

    @tornado.gen.coroutine
    def set_state_to_scoring(self, user_id):
        """Update the user's state to reflect that they have a bot pending
        scoring.
        """
        doc = yield motor.Op(self._conn.find_one, user_id)
        doc["state"] = _State.PENDING
        yield motor.Op(self._conn.save, doc)


class UsersDataSync(object):
    """Sync access to the users data, used by the worker process."""

    _conn = pymongo.MongoClient().battleships.users 

    @classmethod
    def set_state_to_scored_success(cls, user_id, bot_id, score):

        now = long(time.time())
        doc = cls._conn.find_one(user_id)

        def is_best_score():
            if "best_score" not in doc:
                return True
            return score < doc["best_score"]["score"] # lower is better

        if is_best_score():
            doc.update({
                "best_score": {
                    "score":        score,
                    "bot_id":       bot_id,
                    },
                "state":            _State.BEST,
                })
        else:
            doc["state"] =          _State.SUCCESS

        doc["last_score"] = {"time": now}
        cls._conn.save(doc)

    @classmethod
    def set_state_to_scored_error(cls, user_id):
        now = long(time.time())
        doc = cls._conn.find_one(user_id)
        doc.update({
            "state":            _State.ERROR,
            "last_score": {
                "time":         now,
                },
            })
        cls._conn.save(doc)


class _State(object):
    """The different states that a user can be in."""
    NEW =       "new"       # user is yet to submit a bot
    PENDING =   "pending"   # the user has submitted a bot but it hasn't been
                            # scored yet
    ERROR =     "error"     # the last bot submitted failed
    SUCCESS =   "success"   # the last bot submitted succeeded, but wasn't the
                            # the user's best score
    BEST =      "best"      # the last bot submitted was the user's best score

