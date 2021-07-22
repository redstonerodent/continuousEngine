from continuousEngine import *
import random

# distribution abstract class & instances

class Layers:
    DISTRIBUTION    = 1
    GOAL            = 2
    RANGE_GUIDE     = 3
    START_PEG       = 4
    NEW_START_PEG   = 4.1
    NEW_EDGE        = 6
    AUX_TREE        = 7.9
    TREE            = 8
    SNAP_TARGET     = 9
    SCORE           = 10
    DEBUG           = 20

class Colors:
    TREE            = (0, 0, 0)
    START_PEG       = {'red':(255,50,50), 'blue':(50,50,255), 'green':(50,255,50), 'yellow':(255,255,0), 'brown':(138,85,15), 'white':(255,255,255)}
    RANGE_GUIDE     = {'red':(255,150,150), 'blue':(150,150,255), 'green':(150,255,150), 'yellow':(255,255,150), 'brown':(180, 150, 100), 'white':(255,255,255)}
    NEW_TREE        = (100, 100, 100)
    NEW_EDGE        = (150, 150, 150)
    BACKGROUND      = (192, 230, 168)

class Sizes:
    # pixels
    SNAP_TARGET     = 5
    START_PEG       = 10

    # in-game units
    TURN_DISTANCE   = 1


class TransTree(Renderable):
    def __init__(self, game, edges=None, teams=None, layer=Layers.TREE, color=Colors.TREE):
        super().__init__(game, layer)
        self.edges = edges or []
        self.teams = teams or []
        self.color = color

    def add_edge(self, p, q):
        self.edges.append((p,q))

    def merge(self, other):
        self.edges.extend(other.edges)
        self.teams.extend(other.teams)

    def snap(self, p): # nearest point on tree to p
        return min((nearest_on_segment(p, *edge) for edge in self.edges), key=p.__rshift__)

    def distsq(self, p): # distance of nearest point to p
        return self.snap(p) >> p

    def intersect_segment(self, p, q): # does the segment between p and q cross the tree?
        return any(intersect_segments(p, q, *e) for e in self.edges) or self.distsq(p) < epsilon or self.distsq(q) < epsilon

    def render(self):
        for e in self.edges:
            drawSegment(self.game, self.color, *e)

    def __bool__(self):
        return bool(self.edges)

class StartPeg(Disk):
    def __init__(self, game, team, loc, layer=Layers.START_PEG):
        super().__init__(game, layer, Colors.START_PEG[team], loc, Sizes.START_PEG, realRadius=False)
        self.team = team

# steps:
#     start_tree: you don't have a tree yet and are placing your start peg
#     start_edge: you have a tree, and are picking a point on it to start an edge
#     finish_edge: you are placing the second end of an edge, off the tree


class Trans(Game):

    def __init__(self, teams=2, **kwargs):
        super().__init__(backgroundColor=Colors.BACKGROUND, name='continuous trans', **kwargs)
        teams = int(teams)
        if teams > len(self.possible_teams):
            print('{} is too many teams (max {}); defaulting to 2'.format(teams, len(self.possible_teams)), flush=True)
            teams = 2
        self.teams = self.possible_teams[:teams]
        
        # edges drawn this turn
        self.new_tree = TransTree(self, layer=Layers.AUX_TREE, color=Colors.NEW_TREE)

        # currently accessible tree, for snapping to
        self.current_tree = TransTree(self, layer=Layers.AUX_TREE)
        self.current_tree.visible = False

        self.snap_target = Disk(self, Layers.SNAP_TARGET, Colors.TREE, None, Sizes.SNAP_TARGET, realRadius=False)
        self.snap_target.GETloc = lambda _: self.tree.snap(self.mousePos())
        self.snap_target.GETvisible = lambda _: self.mousePos() and self.step == 'start_edge'

        self.new_edge = Segment(self, Layers.NEW_EDGE, Colors.NEW_EDGE, None, None)
        self.new_edge.GETvisible = lambda _: self.step == 'finish_edge'

        self.range_guide = Circle(self, Layers.RANGE_GUIDE, None, None, None)
        self.range_guide.GETr = lambda _: self.distance_left
        self.range_guide.GETcolor = lambda _: Colors.RANGE_GUIDE[self.turn]
        self.range_guide.GETvisible = lambda _: self.mousePos() or self.step == 'finish_edge'

        self.click[1] = lambda _: self.on_click(self.mousePos())

        self.keyPress[self.keys.cancelTree] = lambda e: self.prep_turn()

        self.reset_state()

    def make_initial_state(self):
        return (
            'red',
            [],
            {},
        )

    possible_teams = ['red', 'blue', 'green', 'yellow', 'brown', 'white']

    def save_state(self):
        return (
            self.turn,
            [(t.edges.copy(), t.teams.copy()) for t in self.layers[Layers.TREE]],
            [(p.team, p.loc) for p in self.layers[Layers.START_PEG]],
        )
    def load_state(self, state):
        self.turn, trees, pegs = state
        for layer in [Layers.START_PEG, Layers.TREE]:
            self.clearLayer(layer)
        self.team_trees = {}

        for edges, teams in trees:
            tree = TransTree(self, [(Point(*p), Point(*q)) for p,q in edges], teams)
            for team in teams: self.team_trees[team] = tree
        for t,l in pegs:
            StartPeg(self, t, Point(*l))

    def prep_turn(self, team=None):
        team = team or self.turn
        self.clearLayer(Layers.NEW_START_PEG)
        self.new_tree.edges = []
        self.step = 'start_edge' if team in self.team_trees else 'start_tree'
        self.current_tree.edges = self.team_trees[team].edges.copy() if team in self.team_trees else []
        self.other_trees = self.layers[Layers.TREE].copy()
        if team in self.team_trees: self.other_trees.remove(self.team_trees[team])
        self.distance_left = Sizes.TURN_DISTANCE



    def is_over(self):
        pass
    def winner(self):
        pass

    def attemptGameMove(self, move):
        pass

    def process(self):
        pos = self.mousePos()
        if self.step == 'start_tree':
            self.range_guide.loc = pos
        elif self.step == 'start_edge':
            self.snap_target.loc = self.range_guide.loc = self.current_tree.snap(pos)
        elif self.step == 'finish_edge':
            self.new_edge.p2 = nearest_on_disk(pos, self.new_edge.p1, self.distance_left)

    def on_click(self, pos):
        self.process()
        if self.step == 'start_tree':
            StartPeg(self, self.turn, pos, Layers.NEW_START_PEG)
            self.new_edge.p1 = pos
            self.step = 'finish_edge'
        elif self.step == 'start_edge':
            pos = self.range_guide.loc
            self.new_edge.p1 = pos
            self.step = 'finish_edge'
        elif self.step == 'finish_edge':
            self.new_tree.add_edge(self.new_edge.p1, self.new_edge.p2)
            self.current_tree.add_edge(self.new_edge.p1, self.new_edge.p2)
            self.distance_left -= (self.new_edge.p1 >> self.new_edge.p2)**.5
            if self.distance_left > epsilon:
                # see if other trees have been connected
                for t in self.other_trees.copy():
                    if t.intersect_segment(self.new_edge.p1, self.new_edge.p2):
                        self.current_tree.merge(t)
                        self.other_trees.remove(t)
                self.step = 'start_edge'
            else:
                print('out of distance')
                self.attemptMove({'player':self.turn, 'edges': [(p.coords, q.coords) for p,q in self.new_tree.edges]})
        print(self.turn, self.step)
        for x in self.history: print(x)

    def attemptGameMove(self, move):
        self.record_state()
        dist = 0
        for p,q in move['edges']:
            p, q = Point(*p), Point(*q)
            dist += (p >> q)**.5
            if self.turn not in self.team_trees:
                StartPeg(self, self.turn, p)
                self.team_trees[self.turn] = TransTree(self, teams=[self.turn])
            if self.team_trees[self.turn] and self.team_trees[self.turn].distsq(p) > epsilon:
                print(self.team_trees[self.turn].distsq(p))
                fail
            self.team_trees[self.turn].add_edge(p, q)
            for t in self.layers[Layers.TREE].copy():
                if t != self.team_trees[self.turn] and t.intersect_segment(p,q):
                    # merge t into self.team_trees[self.turn]
                    self.team_trees[self.turn].merge(t)
                    for team in t.teams: self.team_trees[team] = self.team_trees[self.turn]
                    self.layers[Layers.TREE].remove(t)
        if dist > Sizes.TURN_DISTANCE+epsilon:
            print(dist)
            fail
        return True




if __name__=="__main__":
    pygame.init()
    run_local(Trans, sys.argv[1:])
