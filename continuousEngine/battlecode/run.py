# game must implement
#   attemptMove
#   is_over()
#   winner()
#   next_turn()

import json, os

def run(name, game_class, player_files, player_modules, file, *args):
    game = game_class(*args, headless=True)
    players = {}
    for m, t in zip(player_modules, game.teams):
        players[t] = m.Player(game_class, t)

    state = game.save_state()
    for t in players:
        players[t].game.load_state(state)

    ending = 'error'
    try:
        while not game.is_over():
            try:
                move = players[game.turn].make_move()
            except:
                raise ValueError(game.next_turn())

            print(move)
            if not game.attemptMove(move):
                print(f"{game.turn} attempted illegal move: {move}")
                raise ValueError(game.next_turn())

            for t in players:
                try:
                    players[t]._receive_move(move, game.save_state())
                except:
                    raise ValueError(game.next_turn(t))
    except ValueError as e:
        ending = 'error'
        winner = e.args[0]
    else:
        ending = 'standard'
        winner = game.winner()

    finally:
        print(winner)

        if not os.path.exists("saves"):
            os.mkdir("saves")

        with open(file,'w') as f:
            f.write(json.dumps({
                'type':name,
                'players':dict(zip(game.teams, player_files)),
                'ending':ending,
                'winner':winner,
                'state':game.save_state(),
                'history':game.history,
                'args':args,
            }))
        print("saved as {}".format(file))
