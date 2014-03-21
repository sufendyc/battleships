from abc import ABCMeta, abstractmethod

# defining abstract base class
# http://stackoverflow.com/questions/13646245/is-it-possible-to-make-abstract-classes-in-python

class Game(object):
    __metaclass__ = ABCMeta

    def __init__(self, seed):
        pass

    @abstractmethod
    def get_state(self):
        # return a dict of the current game state
        pass

    @abstractmethod
    def get_next_bot_request(self):
        # return string
        pass

    @abstractmethod
    def update_state_with_bot_response(self, bot_response):
        # `bot_response` is a string
        # return boolean indicating whether move was legal
        pass

    @abstractmethod
    def is_complete(self):
        # return boolean indicating whether the game is complete/over
        pass

    @abstractmethod
    def get_score(self):
        # return score between 0 and 1
        pass