"""Worker that plays a set number of games against a bot in order to test it.

For game rules see:
http://en.wikipedia.org/wiki/Battleship_(game)
"""

import os
import os.path
import random
import subprocess
import time
import traceback
import yaml
from data import UsersDataSync as UsersData
from queue import BotQueue


# Grids ------------------------------------------------------------------------

class ShipGridSquareState(object):
    SEA =       0
    SHIP =      1


class ShotGridSquareState(object):
    UNKNOWN =   0
    MISS =      -1
    HIT =       1


class Grid(object):

    SIZE = 10

    def __init__(self, init_val):
        """Populate the grid with an initial value."""
        self.squares = [init_val] * (self.SIZE ** 2)

    def get(self, x, y):
        return self.squares[(y * self.SIZE) + x]

    def put(self, x, y, val):
        self.squares[(y * self.SIZE) + x] = val

    def valid_coord(self, x, y):
        """Return whether x,y are valid grid coordinates."""
        return x >= 0 and x < self.SIZE and y >= 0 and y < self.SIZE

    def rand_square(self):
        """Return the coordinates of a random grid square."""
        x = random.randint(0, self.SIZE-1)
        y = random.randint(0, self.SIZE-1)
        return x, y

    def __str__(self):
        """Return string representation of the grid.

        Used for serialising the grid for transmission to bot script.
        """
        return ','.join(map(str, self.squares))

    @classmethod
    def index_to_coord(cls, i):
        y = i / cls.SIZE
        x = i % cls.SIZE
        return x, y


# Ship Manager -----------------------------------------------------------------

class ShipManager(object):

    SHIPS = [
        5,  # aircraft carrier
        4,  # battleship
        3,  # submarine
        3,  # destroyer (or cruiser)
        2,  # patrol board (or destroyer)
        ]

    @classmethod
    def arrange_on_grid(cls, ship_grid):
        """Randomly arrange the ships `SHIPS` in the grid `ship_grid`.

        To place a ship, first a random start square in the grid is picked, 
        then a random orientation is picked (horizontal, vertical). The 
        sequence of coordinates in the grid that would occupy the ship given 
        the random start square and orientation is then identified. An attempt 
        to place the ship in this sequence of coordinates is then made. If the 
        attempt fails (see `attempt_to_place_ship_in_seq' for possible reasons) 
        then start again by picking a new random start square.

        Finish when all ships have been successfully placed.
        """

        for ship in cls.SHIPS:
            while True:
                r_x, r_y = ship_grid.rand_square()
                if random.choice([True, False]):
                    # vertical
                    seq = [(x, r_y) for x in range(r_x, r_x + ship)]
                else:
                    # horizontal
                    seq = [(r_x, y) for y in range(r_y, r_y + ship)]
                success = \
                    cls._attempt_to_place_ship_in_seq(ship_grid, ship, seq)
                if success:
                    break

    @staticmethod
    def _attempt_to_place_ship_in_seq(ship_grid, ship, seq):
        """Attempt to place the ship of length `ship` in the grid `ship_grid`
        in the squares identified by the list of coordinates `seq`.

        The attempt will fail if:
            * Any coordinates are invalid for the grid
            * A square identified by a coordinate already contains a ship part

        Returns whether the ship was successfully placed.
        """

        for x, y in seq:
            if not ship_grid.valid_coord(x, y) or \
                ship_grid.get(x, y) != ShipGridSquareState.SEA:
                return False

        for x, y in seq:
            ship_grid.put(x, y, ShipGridSquareState.SHIP)
        return True


# Game Manager -----------------------------------------------------------------

class GameManager(object):

    @classmethod
    def play(cls, bot_path, interactive=False):
        """Generate a random ship arragement and play the game until the bot
        has hit/sunk all ships. The number of moves taken by the bot is
        returned.

        A BotIllegalMoveException is raised if the bot attempts to play an
        illegal move.

        If `interactive` is true then the game state is printed to stdout
        after every bot move. The user is required to press the return key
        to proceed to the next move.
        """

        # init game state
        ship_grid = Grid(ShipGridSquareState.SEA)
        shot_grid = Grid(ShotGridSquareState.UNKNOWN)
        ShipManager.arrange_on_grid(ship_grid)
        bot_turns = 0

        # repeatedly ask the bot to play moves until all ships are hit/sunk,
        # counting the number of moves made
        while not cls._all_ships_hit(shot_grid):
            cls._play_next_bot_move(bot_path, ship_grid, shot_grid)
            if interactive:
                print_game_state(ship_grid, shot_grid)
                raw_input()
            bot_turns += 1

        return bot_turns

    @staticmethod
    def _all_ships_hit(shot_grid):
        """Return whether all ships have been hit/sunk.

        This is calculated by comparing the number of hits in the shot grid 
        with the number of squares occupied by ships in the ship grid.
        """
        hits = filter(
            lambda x: x == ShotGridSquareState.HIT, shot_grid.squares)
        return len(hits) == sum(ShipManager.SHIPS)

    @staticmethod
    def _play_next_bot_move(bot_path, ship_grid, shot_grid):
        """Run the bot script against the current `shot_grid` to obtain the
        next move, then attempt to update the `shot_grid` by playing the move.
        """

        # get next bot move from bot script
        bot_move = subprocess.check_output([bot_path, str(shot_grid)])

        # validate the bot move
        try:
            bot_move = int(bot_move)
        except ValueError:
            raise IllegalBotMoveException
        if bot_move < 0 or bot_move >= len(shot_grid.squares):
            raise IllegalBotMoveException
        x, y = Grid.index_to_coord(bot_move)
        if shot_grid.get(x, y) != ShotGridSquareState.UNKNOWN:
            raise IllegalBotMoveException

        # make bot move
        hit = ship_grid.get(x, y) == ShipGridSquareState.SHIP
        val = ShotGridSquareState.HIT if hit else ShotGridSquareState.MISS
        shot_grid.put(x, y, val)


class IllegalBotMoveException(Exception):
    pass


# Tournament Manager -----------------------------------------------------------

class TournamentManager(object):
    """Return the average number of moves taken by a bot to win after playing
    `num_games` games.
    """

    @staticmethod
    def play(bot_path, num_games):
        scores = []
        for _ in range(num_games):
            bot_turns = GameManager.play(bot_path)
            scores.append(bot_turns)
        average = sum(scores) / float(num_games)
        return average


# Debug ------------------------------------------------------------------------

def print_grid(grid):
    """Print a 2D representation of a Grid object to stdout."""
    output = []
    for y in range(grid.SIZE):
        for x in range(grid.SIZE):
            val = grid.get(x, y)
            output.append("%02d " % val)
        output.append('\n')
    print ''.join(output) 

def print_game_state(ship_grid, shot_grid):
    """Print the ship and shot grids to stdout."""
    os.system("clear")
    print "SHIPS"
    print_grid(ship_grid)
    print
    print "SHOTS"
    print_grid(shot_grid)
 

# Main -------------------------------------------------------------------------

def main():

    # load config
    with open(os.path.join(os.path.dirname(__file__), "config.yaml")) as f:
        conf = yaml.load(f)

    # indefinitely process bot queue
    while True:
        user_id, bot_id = BotQueue.pop_or_wait()
        bot = os.path.join(conf["bot-path"], bot_id)

        try:
            av_num_moves_to_win = TournamentManager.play(
                bot, conf["num-games-per-tournament"])
        except IllegalBotMoveException:
            UsersData.update_bot_illegal_move(user_id)
        except (subprocess.CalledProcessError, OSError):
            traceback.print_exc()
            UsersData.update_bot_error(user_id)
        else:
            UsersData.update_bot_success(user_id, av_num_moves_to_win)


if __name__ == "__main__":
    main()

