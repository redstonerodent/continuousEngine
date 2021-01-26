def watch(file):
    import json, importlib, pygame, continuousEngine
    pygame.init()
    with open(file) as f:
        info = json.loads(f.read())

    name = info['type']
    game = continuousEngine.game_class(name)(*info['args'])
    game.future = [info['state']]+info['history'][:0:-1]
    game.load_state(info['history'][0])

    game.attemptMove = lambda _: False

    continuousEngine.GameInfo(game, 10**10,
        lambda _: [
            ('file', file),
            ('game', name),
            ('turn', game.turn),
            (None, None),
            *((t, info['players'][t]) for t in game.teams),
            *([] if game.future else [('winner',info['winner']), ('ending',info['ending'])])
        ]
    )

    print(f'winner: {info["winner"]}')
    if info['ending'] == 'error': print('game ended in error')

    game.run()
