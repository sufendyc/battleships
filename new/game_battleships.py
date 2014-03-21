"""Battleships

http://en.wikipedia.org/wiki/Battleship_(game)
"""

import logging.config
import os
import os.path
import random
import signal
import subprocess
import time
import traceback
import yaml
from battleships.conf import Conf
from battleships.data.bots import BotsDataSync as BotsData
from battleships.data.users import UsersDataSync as UsersData
from operator import itemgetter


class ShipGridSquareState(object):
    SEA =                   0
    AIRCRAFT_CARRIER =      1
    BATTLESHIP =            2
    SUBMARINE =             3
    DESTROYER =             4
    PATROL_BOAT =           5


class ShotGridSquareState(object):
    UNKNOWN =   0
    MISS =      -1
    HIT =       1
    SUNK =      2


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


class ShipGrid(Grid):

    def get_ship_squares(self, ship_type):
        """Generate a list of index positions for the squares that contain the
        ship `ship_type`.
        """
        for i, val in enumerate(self.squares):
            if val == ship_type:
                yield i


class ShipManager(object):

    # (ship_type, ship_size)
    SHIPS = [
        (ShipGridSquareState.AIRCRAFT_CARRIER,  5),
        (ShipGridSquareState.BATTLESHIP,        4),
        (ShipGridSquareState.SUBMARINE,         3),
        (ShipGridSquareState.DESTROYER,         3),
        (ShipGridSquareState.PATROL_BOAT,       2),
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

        ships = list(cls.SHIPS)
        random.shuffle(ships)
        for ship_type, ship_size in ships:
            while True:
                r_x, r_y = ship_grid.rand_square()
                if random.choice([True, False]):
                    # vertical
                    seq = [(x, r_y) for x in range(r_x, r_x + ship_size)]
                else:
                    # horizontal
                    seq = [(r_x, y) for y in range(r_y, r_y + ship_size)]
                success = \
                    cls._attempt_to_place_ship_in_seq(
                        ship_grid, ship_type, ship_size, seq)
                if success:
                    break

    @staticmethod
    def _attempt_to_place_ship_in_seq(ship_grid, ship_type, ship_size, seq):
        """Attempt to place the ship of type `ship_type` with length 
        `ship_size` in the grid `ship_grid` in the squares identified by the 
        list of coordinates `seq`.

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
            ship_grid.put(x, y, ship_type)
        return True


class BattleshipsGame(Game):

    def __init__(self, seed):
        """Prepare a new game.
        
        Generate a random ship arragement. To make the game deterministic a 
        seed can be provided for the random number generator.

        The game stats consists of:

            `_ship_grid`: a list of grid squares indicating which are occupied
                by ships (1) and which are just sea (0)

            `_shot_grid`: a list of moves made by the bot and their outcome, of 
                the form [(move_grid_index, hit_or_miss), ...] eg:

                    [(3, -1), (13, 1), (14, 1), (39, -1), ...]

        """

        random.seed(seed)

        # init game state
        self._ship_grid = ShipGrid(ShipGridSquareState.SEA)
        self._shot_grid = Grid(ShotGridSquareState.UNKNOWN)
        ShipManager.arrange_on_grid(ship_grid)

        # count the number of moves made by the bot to determine its score
        self._num_moves = 0

    def get_state(self):
        return {
            "ships":    self._ship_grid,
            "moves":    self._shot_grid,
            }

    def get_next_bot_request(self):
        """The bot is passed the `_shot_grid` as a string when requested to
        make its next move.
        """
        return str(self._shot_grid)

    def update_with_bot_response(self, bot_response):

        try:
            bot_response = int(bot_response)
        except ValueError:
            return False

        if bot_response < 0 or bot_response >= len(self._shot_grid.squares):
            return False

        x, y = Grid.index_to_coord(bot_response)
        if shot_grid.get(x, y) != ShotGridSquareState.UNKNOWN:
            return False

        square_revealed = self._ship_grid.get(x, y)

        # miss
        if square_revealed == ShipGridSquareState.SEA:
            move_result = ShotGridSquareState.MISS
            self._shot_grid.put(x, y, ShotGridSquareState.MISS)

        # hit (maybe sunk)
        else:
            move_result = ShotGridSquareState.HIT
            self._shot_grid.put(x, y, ShotGridSquareState.HIT)

            ship_type = square_revealed
            is_sunk = True
            for i in self._ship_grid.get_ship_squares(ship_type):
                if self._shot_grid.squares[i] == ShotGridSquareState.UNKNOWN:
                    is_sunk = False
                    break
                    
            if is_sunk:
                move_result = ShotGridSquareState.SUNK
                for i in self._ship_grid.get_ship_squares(ship_type):
                    shot_grid.squares[i] = ShotGridSquareState.SUNK

        self._num_moves += 1

        return True # bot response accepted

    def is_complete(self):
        """Return whether all ships have been hit/sunk.

        This is calculated by comparing the number of hits in the shot grid 
        `hits_made` with the number of squares occupied by ships in the ship 
        grid `hits_to_win`.
        """
        hits_made = len(filter(
            lambda x: x == ShotGridSquareState.SUNK, shot_grid.squares))
        # index 1 of `SHIPS` is the ship size
        hits_to_win = sum(map(itemgetter(1), ShipManager.SHIPS))
        return hits_made == hits_to_win

    def get_score(self):

        num_ship_squares = \
            ShipGridSquareState.SEA + \
            ShipGridSquareState.AIRCRAFT_CARRIER + \
            ShipGridSquareState.BATTLESHIP + \
            ShipGridSquareState.SUBMARINE + \
            ShipGridSquareState.DESTROYER + \
            ShipGridSquareState.PATROL_BOAT

        num_squares = len(self._ship_grid.squares)

        num_errors_possible = num_squares - num_ship_squares

        num_errors_made = self._num_moves - num_ship_squares

        score = (num_error_possible - num_errors_made) / \
            float(num_errors_possible)
    
        return score
        
