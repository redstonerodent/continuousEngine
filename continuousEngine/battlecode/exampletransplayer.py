import random
from continuousEngine import *
from continuousEngine.games.trans import *
from continuousEngine.battlecode.player import *

class Player(PlayerTemplate):
    def on_move(self, move, state):
        self.game.load_state(state)

    def make_move(self):
        goals = [g.loc for g in self.game.layers[Layers.GOAL]]
        if self.team in self.game.team_trees:
            current_tree = TransTree(self.game, self.game.team_trees[self.team].edges.copy(), layer=-5)
        else:
            start = random.choice(goals)
            current_tree = TransTree(self.game, [(start, start)], layer=-5)
            goals.remove(start)
        
        edges = []
        distance_left = 1
        
        while distance_left > epsilon and goals:
            goal = random.choice(goals)
            nearest = current_tree.snap(goal)
            dist = (nearest >> goal)**.5
            if dist <= distance_left:
                target = goal
                goals.remove(goal)
            else:
                target = nearest + (goal - nearest) @ distance_left
            current_tree.add_edge(nearest, target)
            edges.append((nearest, target))
            distance_left -= (nearest >> target)**.5

        return {"player":self.team, "edges":[(p.coords, q.coords) for p,q in edges]}