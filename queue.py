import redis


class BotQueue(object):
    """Queue layer that exists between the server and worker, that lines up
    bots for testing.
    """

    _KEY = "battleships/bot-queue"
    _conn = redis.Redis()

    @classmethod
    def add(cls, user_id, bot_id):
        """Add a bot to the queue for processing by the worker."""
        data = "%s,%s" % (user_id, bot_id)
        cls._conn.lpush(cls._KEY, data)

    @classmethod
    def pop_or_wait(cls):
        """Return the oldest bot in the queue and process it, or block if the
        queue is empty.
        """
        _, data = cls._conn.brpop([cls._KEY])
        user_id, bot_id = data.split(',')
        return user_id, bot_id
    
