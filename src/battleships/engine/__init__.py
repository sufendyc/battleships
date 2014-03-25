"""Interface for all game engines."""

from abc import ABCMeta, abstractmethod


class Game:
    __metaclass__ = ABCMeta

    @abstractmethod
    def __init__(self, seed):
        """Create a new game.

        The `seed` is a float between 0 and 1 used to seed the game random
        number generator. This allows game play to be deterministic.
        """
        pass

    @abstractmethod
    def get_state(self):
        """Return the current game state.

        The return type is dict and can have any schema.

        This is used to render the game in the web UI and during bot
        development.
        """
        pass

    @abstractmethod
    def get_next_bot_request(self):
        """Return a string that will be passed to the bot executable when it's
        called to make its next move.

        There is no restriction on the format of this string. It must contain
        sufficient data for the bot to be able to decide on a move to make.
        """
        pass

    @abstractmethod
    def update_state_with_bot_response(self, bot_response):
        """Update the game state to reflect the bot move.

        The bot move is the string value `bot_response` that was returned
        from the bot executable.

        This method should return a boolean indicating whether the bot move
        was accepted (ie. return False if the bot made an illegal move).
        """
        pass

    @abstractmethod
    def is_complete(self):
        """Return whether the game is complete (over).

        The return type is boolean.
        """
        pass

    @abstractmethod
    def get_score(self):
        """Return a score between 0 and 1 indicating the bot score.

        1 indicates that the bot played perfectly; 0 indicates that the bot
        played the worst possible game.

        The return type is float.
        """
        pass