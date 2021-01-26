# game must implement
#   attemptMove
#   is_over()
#   winner()
#   next_turn()

class PlayerTemplate:
    def __init__(self, game, game_name, team, *args):
        self.game = game(*args, headless=True)
        self.team = team
    def _receive_state(self, state):
        self.game.load_state(state)
    def _receive_move(self, move, state):
        self.game.attemptMove(move)
        self.on_move(move, state)
    
    def on_move(self, move, state):
        # each move updates self.game, and then calls this function
        pass
    def make_move(self):
        # return the move you want to make
        return None