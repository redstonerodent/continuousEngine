import json, importlib, pygame

pygame.init()

def watch(file):
	with open(file) as f:
		info = json.loads(f.read())

	name = info["type"]
	game = getattr(importlib.import_module('continuousEngine.games.'+name), name.capitalize())(*info["args"])
	game.future = [info['state']]+info['history'][:0:-1]
	game.load_state(info['history'][0])

	game.run()