"""Return the database to an initial state."""

import pymongo
from battleships.conf import Conf


def main():
    Conf.init()
    conn = pymongo.MongoClient(
        host=Conf["mongodb"]["host"],
        port=Conf["mongodb"]["port"],
        ).battleships
    conn.bots.remove()
    conn.users.remove()
    conn.users.save({"verify_token": "25848a988e544e88986b46324887f675"})

if __name__ == "__main__":
    main()