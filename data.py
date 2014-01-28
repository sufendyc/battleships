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
            "facebook":             facebook_user,
            "last_played":          None, 
            "state":                "new",
            "state_category":       "default",
            "av_num_moves_to_win":  None,
            "bots":                 [],
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
            "facebook.name", 
            "facebook.picture.data.url",
            "last_played", 
            "state",
            "state_category",
            "av_num_moves_to_win"], 1)
        cursor = self._conn.find({}, projection).sort("av_num_moves_to_win")
        result = yield motor.Op(cursor.to_list, length=self._MAX_NUM_USERS)
        raise tornado.gen.Return(result) 

    @tornado.gen.coroutine
    def update_bot_pending(self, user_id, bot_id):
        """A bot has successfully been uploaded and is queued for testing."""
        now = long(time.time())
        update = {
            "$set": {
                "state":            "playing...",
                "state_category":   "warning",
                }, 
            "$push": {
                "bots": {
                    "bot_id":       bot_id, 
                    "created_time": now,
                    }
                },
            }
        yield motor.Op(self._conn.update, {"_id": user_id}, update)


class UsersDataSync(object):
    """Sync access to the users data, used by the worker process."""

    _conn = pymongo.MongoClient().battleships.users 

    @classmethod
    def update_bot_rejected(cls, user_id, error):
        """Update a user's record following the latest bot to be uploaded 
        raising an error during testing.
        """
        now = long(time.time())
        cls._conn.update({"_id": user_id}, {
            "$set": {
                "last_played":      now, 
                "state":            "rejected",
                "state_category":   "danger",
                "bot_error":        error.data,
                }
            }) 

    @classmethod
    def update_bot_success(cls, user_id, av_num_moves_to_win):
        """Update a user's record following the latest bot to be uploaded 
        succeeding.
        """

        now = long(time.time())
        update = { 
            "last_played":      now, 
            "state":            "success",
            "bot_error":        None,
            }
        
        # if this is the user's best effort, update their score
        user = cls._conn.find_one(user_id)
        if user["av_num_moves_to_win"] is None or \
            av_num_moves_to_win < user["av_num_moves_to_win"]:
            update["av_num_moves_to_win"] = av_num_moves_to_win
            update["state_category"] = "info"
        else:
            update["state_category"] = "success"

        cls._conn.update({"_id": user_id}, {"$set": update})
        
