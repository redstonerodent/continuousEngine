# game must implement
#   attemptMove
#   is_over()
#   winner()

import random, json, os

def run(name, game_class, player_files, player_modules, *args):
	game = game_class(*args, headless=True)
	players = {}
	for m, t in zip(player_modules, game.teams):
		players[t] = m.Player(game_class, t)

	state = game.save_state()
	for t in players:
		players[t].game.load_state(state)

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
	    f.write(json.dumps({'type':name, 'state':game.save_state(), 'history':game.history, 'args':args}))
	print("saved as {}".format(file))