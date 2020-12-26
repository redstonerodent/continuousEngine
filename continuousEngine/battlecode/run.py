# game must implement
#   attemptMove
#   is_over()
#   winner()

import random, json, importlib, os

def run(name, player_files, player_modules, **kwargs):
	game_type = getattr(importlib.import_module('continuousEngine.games.'+name), name.capitalize())
	game = game_type(headless=True, **kwargs)
	players = {}
	for m, t in zip(player_modules, game.teams):
		players[t] = m.Player(game_type, t)

	state = game.save_state()
	for t in players:
		players[t].game.load_state(state)

	# print(game.teams)
	# print(players)

	while not game.is_over():
		move = players[game.turn].make_move()
		print(move)
		if not game.attemptMove(move):
			raise ValueError("{} attempted illegal move: {}".format(game.turn, move))
		for t in players:
			players[t]._receive_move(move, game.save_state())


	print(game.winner())

	if not os.path.exists("saves"):
		os.mkdir("saves")

	file = os.path.join("saves", "-vs-".join(player_files)+"-"+str(random.randint(0,100)))
	with open(file,'w') as f:
	    f.write(json.dumps({'type':name, 'state':game.save_state(), 'history':game.history, 'kwargs':kwargs}))
	print("saved as {}".format(file))