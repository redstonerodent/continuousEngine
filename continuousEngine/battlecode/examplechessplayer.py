import random
from continuousEngine import *
from continuousEngine.games.chess import *
from continuousEngine.battlecode.player import *

class Player(PlayerTemplate):
    def make_move(self):
        my_pieces = [p for p in self.game.layers[Layers.PIECES] if p.color == self.team]
        print(my_pieces)
        while 1:
            self.game.active_piece = random.choice(my_pieces)
            target = random.uniform(-5,5), random.uniform(-5,5)

            self.game.updateMove(target)

            if not self.game.blocking and len(self.game.capture)<2:
                return {"player":self.team, "selected":self.game.active_piece.loc.coords, "location":target}