import random, json, importlib, os

def run(name, player_files, player_modules, **kwargs):
	game_type = getattr(importlib.import_module('continuousEngine.games.'+name), name.capitalize())
	game = game_type(headless=True, **kwargs)
	players = {}
	for m, t in zip(player_modules, game.teams):
		players[t] = m.Player(game_type, t)

	print(game.teams)
	print(players)

	turn = 0
	while not game.is_over():
		move = players[game.teams[turn]].make_move()
		print(move)
		if not game.attemptMove(move):
			raise ValueError
		for t in players:
			players[t]._receive_move(move)
		turn += 1
		turn %= len(game.teams)

	print(game.winner())

	file = os.path.join("saves", "-vs-".join(player_files)+"-"+str(random.randint(0,100)))
	with open(file,'w') as f:
	    f.write(json.dumps({'type':name, 'state':game.save_state(), 'history':game.history, 'kwargs':kwargs}))
	print("saved as {}".format(file))