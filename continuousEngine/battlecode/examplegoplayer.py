import random
from continuousEngine import *
from continuousEngine.games.go import *
from continuousEngine.battlecode.player import *

class Player(PlayerTemplate):
    def make_move(self):
        while 1:
            if random.random() < .001:
                return {"player":self.team, "action":"skip"}

            pos = Point(*(random.uniform(-board_rad,board_rad) for _ in range(2)))

            if on_board(pos) and not any(overlap(pos, pc.loc) for t in self.game.teams for pc in self.game.layers[Layers.PIECES[t]]):
                return {"player":self.team, "action":"place", "location":pos.coords}