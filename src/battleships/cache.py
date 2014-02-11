import json
import redis
from battleships.conf import Conf


class _ThreadSafeCacheConnection(object):

    @classmethod
    def get(cls):
        if not hasattr(cls, "_conn"):
            cls._conn = redis.Redis(
                host=Conf["redis"]["host"],
                port=Conf["redis"]["port"],
                )
        return cls._conn


class _CacheBase(object):
    """Superclass for cache classes that provides access to a single 
    thread-safe connection to the caching service.
    """

    @staticmethod
    def get_conn():
        return _ThreadSafeCacheConnection.get()


class CacheBotGame(_CacheBase):
    """Cache the results of a game for the client to collect using a token."""

    # 1 hour in seconds, plenty of time for the client to collect the results
    # of a game
    _EXPIRE = 3600

    _KEY_TEMPLATE = "bot-game/%s"

    @classmethod
    def add(cls, token, result):
        k = cls._KEY_TEMPLATE % token
        value = json.dumps(result)
        conn = cls.get_conn()
        conn.set(k, value)
        conn.expire(k, cls._EXPIRE)

    @classmethod
    def get(cls, token):
        k = cls._KEY_TEMPLATE % token
        conn = cls.get_conn()
        value = conn.get(k)
        if value is None:
            return None
        else:
            conn.delete(k)
            return json.loads(value)

