
# defining abstract base class
# http://stackoverflow.com/questions/13646245/is-it-possible-to-make-abstract-classes-in-python

class Game(object):

    def __init__(self, seed):
        pass

    def get_state():
        # return a dict of the current game state
        pass

    def get_next_bot_request():
        # return string
        pass

    def update_with_bot_response(bot_response):
        # `bot_response` is a string
        # return boolean indicating whether move was legal
        pass

    def is_complete():
        # return boolean indicating whether the game is complete/over
        pass

    def get_score():
        # return score between 0 and 1
