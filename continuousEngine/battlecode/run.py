# game must implement
#   attemptMove
#   is_over()
#   winner()
#   next_turn()

import json, os, traceback

def run(name, game_class, game_name, player_files, player_modules, file, max_turns=None, *args):
    game = game_class(*args, headless=True)
    players = {}

    try:
        for m, t in zip(player_modules, game.teams):
            try:
                players[t] = m.Player(game_class, game_name, t, *args)
                players[t]._receive_state(game.get_state(t))
            except:
                traceback.print_exc()
                raise ValueError(game.next_turn(t))

        while not game.is_over():
            try:
                move = players[game.turn].make_move()
            except:
                traceback.print_exc()
                raise ValueError(game.next_turn())

            if not game.attemptMove(move):
                print(f"{game.turn} attempted illegal move: {move}")
                raise ValueError(game.next_turn())

            for t in players:
                try:
                    players[t]._receive_move(move, game.get_state(t))
                except:
                    traceback.print_exc()
                    raise ValueError(game.next_turn(t))
            if max_turns and len(game.history)>=max_turns:
                raise TypeError()
    except ValueError as e:
        ending = 'error'
        winner = e.args[0]
    except TypeError:
        ending = 'draw'
        winner = 'draw'
        traceback.print_exc()
    else:
        ending = 'standard'
        winner = game.winner()

    finally:
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
