import pymongo


conn = pymongo.MongoClient().battleships.users
conn.remove()
conn.save({
    "verify_token":         "1111",
    "experian_data": {
                            "name": "James",
                            "role": "Software Engineer",
        },
    })
conn.save({
    "verify_token":         "2222",
    "experian_data": {
                            "name": "Luke",
                            "role": "Software Engineer",
        },
    })
conn.save({
    "verify_token":         "3333",
    "experian_data": {
                            "name": "Daniel",
                            "role": "Manager",
        },
    })

