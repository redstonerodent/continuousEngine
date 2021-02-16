def watch(file):
    import json, importlib, pygame, continuousEngine
    pygame.init()
    with open(file) as f:
        info = json.loads(f.read())

    name = info['type']
    game = continuousEngine.game_class(name)(*info['args'])
    def _f(_=None):
        game.future = [info['state']]+info['history'][:0:-1]
        game.load_state(info['history'][0])
    game.keyPress[game.keys.resetGame] = _f
    _f()


    game.attemptMove = lambda _: False

    continuousEngine.GameInfo(game,
        lambda _: [
            ('file', file),
            ('game', name),
            ('turn', game.turn),
            (None, None),
            *((t, info['players'][t]) for t in game.teams),
            *([] if game.future else [('winner',info['winner']), ('ending',info['ending'])])
        ]
    )

    print(f'turns: {len(game.future)}')
    print(f'winner: {info["winner"]}')
    if info['ending'] == 'error': print('game ended in error')

    game.run()
