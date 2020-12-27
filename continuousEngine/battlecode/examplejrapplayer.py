import random
from continuousEngine import *
from continuousEngine.games.jrap import *
from continuousEngine.battlecode.player import *

class Player(PlayerTemplate):
    def make_move(self):
        while 1:
            pos = Point(*(random.uniform(-board_rad,board_rad) for _ in range(2)))

            self.game.updateMove(pos)

            if self.game.valid_move:
                return {"player":self.team, "location":pos.coords}