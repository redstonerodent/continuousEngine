import random
from continuousEngine.games.chess import *
from continuousEngine.battlecode.player import *

class Player(PlayerTemplate):
	def make_move(self):
		my_pieces = [p for p in self.game.layers[Layers.PIECES] if p.color == self.team]
		print(my_pieces)
		while 1:
			piece = random.choice(my_pieces)
			target = random.uniform(-5,5), random.uniform(-5,5)
			move = {"player":self.team, "selected":tuple(piece.loc), "location":target}
			if self.game.attemptMove(move):
				self.game.load_state(self.game.history.pop())
				return move