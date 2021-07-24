from continuousEngine import *
import random

# todo
# better scoring: either compute steiner tree or interface for players to build it
# make score look better
# choose distributions (number, size, position, randomness)
# battlecode compatibility
# update readme
# tweak colors / sizes / etc.

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
    START_PEG       = {'red':(255,50,50), 'blue':(50,50,255), 'green':(50,255,50), 'yellow':(255,255,0), 'brown':(138,85,15), 'white':(235,235,235)}
    RANGE_GUIDE     = {'red':(255,150,150), 'blue':(150,150,255), 'green':(150,255,150), 'yellow':(255,255,150), 'brown':(180, 150, 100), 'white':(225,225,225)}
    NEW_TREE        = (100, 100, 100)
    NEW_EDGE        = (150, 150, 150)
    BACKGROUND      = (192, 230, 168)
    DISTRIBUTION    = {'pink':(247,168,184), 'cyan':(85,205,252), 'white':(255,255,255)}
    GOAL_FILL       = {'pink':(227,148,164), 'cyan':(55,175,222), 'white':(225,225,225)}
    GOAL_BORDER     = {'red':(255,50,50), 'blue':(50,50,255), 'green':(50,255,50), 'yellow':(255,255,0), 'brown':(138,85,15), 'white':(235,235,235)}
    SCORE_TICK      = {0: (255,0,0), 1:(0,0,0)}
    SCORE_MARKER    = {'red':(255,50,50), 'blue':(50,50,255), 'green':(50,255,50), 'yellow':(255,255,0), 'brown':(138,85,15), 'white':(235,235,235)}

class Constants:
    INITIAL_SCORE   = 10

    # pixels
    SNAP_TARGET     = 5
    START_PEG       = 8
    GOAL            = 9
    SNAP_DIST       = 10
    SCORE_MARGIN    = 20
    SCORE_VSEP      = 10

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
        super().__init__(game, layer, Colors.START_PEG[team], loc, Constants.START_PEG, realRadius=False)
        self.team = team

class TransGoal(BorderDisk):
    def __init__(self, game, team, color_name, loc):
        super().__init__(game, Layers.GOAL, Colors.GOAL_FILL[color_name], Colors.GOAL_BORDER[team], loc, Constants.GOAL, realRadius=False)
        self.color_name = color_name
        self.team = team

class TransScore(Renderable):
    def __init__(self, game):
        super().__init__(game, Layers.SCORE)
    def render(self):
        left = Constants.SCORE_MARGIN
        bot = self.game.height() - Constants.SCORE_MARGIN
        top = bot - (3 + len(self.game.teams))*Constants.SCORE_VSEP # todo
        sep = (self.game.width() - 2*Constants.SCORE_MARGIN)/Constants.INITIAL_SCORE
        scoretopixel = lambda s: left + s * sep
        
        for i in range(Constants.INITIAL_SCORE+1):
            # draw line
            pygame.draw.line(self.game.screen, Colors.SCORE_TICK[bool(i)], (scoretopixel(i), bot), (scoretopixel(i), top), 3)
        for i, t in enumerate(self.game.teams):
            # score marker
            pygame.draw.circle(self.game.screen, Colors.SCORE_MARKER[t], (scoretopixel(self.game.score[t]), top + (i+2)*Constants.SCORE_VSEP), 10)

# distributions for sampling goals
# should be a Renderable with a sample() function

class UniformDiskDist(Disk):
    def __init__(self, game, color_name, coords, r):
        super().__init__(game, Layers.DISTRIBUTION, Colors.DISTRIBUTION[color_name], Point(*coords), r)
        self.color_name, _, _ = self.args = (color_name, coords, r)
        self.type = 'UniformDiskDist'
    def sample(self):
        while (p := Point(random.uniform(-1,1), random.uniform(-1,1))) >> Point(0,0) > 1: pass
        return self.loc + p*self.r

class UniformRectangleDist(Rectangle):
    def __init__(self, game, color_name, coords, dx, dy):
        super().__init__(game, Layers.DISTRIBUTION, Colors.DISTRIBUTION[color_name], Point(*coords), dx, dy)
        self.args = (color_name, coords, dx, dy)
        self.type = 'UniformRectangleDist'
    def sample(self):
        return self.loc + Point(random.uniform(0,self.dx), random.uniform(0,self.dy))


DISTRIBUTION_TYPE = {
    'UniformDiskDist' : UniformDiskDist,
    'UniformRectangleDist' : UniformRectangleDist,
}


# steps:
#     start_tree: you don't have a tree yet and are placing your start peg
#     start_edge: you have a tree, and are picking a point on it to start an edge
#     finish_edge: you are placing the second end of an edge, off the tree


class Trans(Game):

    def __init__(self, teams=2, **kwargs):
        teams = int(teams)
        if teams > len(self.possible_teams):
            print('{} is too many teams (max {}); defaulting to 2'.format(teams, len(self.possible_teams)), flush=True)
            teams = 2
        self.teams = self.possible_teams[:teams]
        super().__init__(backgroundColor=Colors.BACKGROUND, name='continuous trans', **kwargs)
        
        # edges drawn this turn
        self.new_tree = TransTree(self, layer=Layers.AUX_TREE, color=Colors.NEW_TREE)

        # currently accessible tree, for snapping to
        self.current_tree = TransTree(self, layer=Layers.AUX_TREE)
        self.current_tree.visible = False

        self.snap_target = Disk(self, Layers.SNAP_TARGET, Colors.TREE, None, Constants.SNAP_TARGET, realRadius=False)
        self.snap_target.GETloc = lambda _: self.tree.snap(self.mousePos())
        self.snap_target.GETvisible = lambda _: self.mousePos() and self.step == 'start_edge'

        self.new_edge = Segment(self, Layers.NEW_EDGE, Colors.NEW_EDGE, None, None)
        self.new_edge.GETvisible = lambda _: self.step == 'finish_edge'

        self.range_guide = Circle(self, Layers.RANGE_GUIDE, None, None, None)
        self.range_guide.GETr = lambda _: self.distance_left
        self.range_guide.GETcolor = lambda _: Colors.RANGE_GUIDE[self.turn]
        self.range_guide.GETvisible = lambda _: self.mousePos() or self.step == 'finish_edge'

        # temporary
        self.score_shower = TransScore(self)

        self.click[1] = lambda _: self.on_click()

        self.keyPress[self.keys.cancelTree] = lambda e: self.prep_turn()

        self.reset_state()

    def make_initial_state(self, score=None):
        score = score or {t:Constants.INITIAL_SCORE for t in self.teams}
        dists = [
            UniformDiskDist(self, 'cyan', ( 5, 5), 2),
            # UniformDiskDist(self, 'pink', (-5, 5), 2),
            # UniformDiskDist(self,'white', ( 0, 0), 3),
            # UniformDiskDist(self, 'pink', ( 5,-5), 2),
            # UniformDiskDist(self, 'cyan', (-5,-5), 2),
        ]
        return (
            'red',
            score,
            [],
            {},
            [(dist.type, dist.args) for dist in dists],
            [(t, d.color_name, d.sample()) for t in self.teams for d in dists],
        )

    possible_teams = ['red', 'blue', 'green', 'yellow', 'brown', 'white']

    def get_state(self, team):
        return (
            self.turn,
            self.score.copy(),
            [([(p.coords, q.coords) for p,q in t.edges], t.teams.copy()) for t in self.layers[Layers.TREE]],
            [(p.team, p.loc.coords) for p in self.layers[Layers.START_PEG]],
            [(dist.type, dist.args) for dist in self.layers[Layers.DISTRIBUTION]],
            [(g.team, g.color_name, g.loc.coords) for g in self.layers[Layers.GOAL] if team in [g.team, 'spectator']],
        )

    def save_state(self):
        return self.get_state('spectator')

    def load_state(self, state):
        self.turn, score, trees, pegs, dists, goals = state
        self.score = score.copy()

        for layer in [Layers.START_PEG, Layers.TREE, Layers.DISTRIBUTION, Layers.GOAL]:
            self.clearLayer(layer)
        self.team_trees = {}

        for edges, teams in trees:
            tree = TransTree(self, [(Point(*p), Point(*q)) for p,q in edges], teams)
            for team in teams: self.team_trees[team] = tree
        for t,l in pegs:
            StartPeg(self, t, Point(*l))

        for d, args in dists:
            DISTRIBUTION_TYPE[d](self, *args)
        for t,c,l in goals:
            TransGoal(self, t, c, Point(*l))


    def prep_turn(self, team=None):
        team = team or self.turn
        self.clearLayer(Layers.NEW_START_PEG)
        self.new_tree.edges = []
        self.step = 'start_edge' if team in self.team_trees else 'start_tree'
        self.current_tree.edges = self.team_trees[team].edges.copy() if team in self.team_trees else []
        self.other_trees = self.layers[Layers.TREE].copy()
        if team in self.team_trees: self.other_trees.remove(self.team_trees[team])
        self.distance_left = Constants.TURN_DISTANCE
        if self.step == 'start_tree':
            self.new_start_peg = StartPeg(self, self.turn, None, Layers.NEW_START_PEG)


    # for battlecode
    def is_over(self):
        pass
    def winner(self):
        pass

    def process(self):
        pos = self.mousePos()
        nearest_goal = min(self.layers[Layers.GOAL], key=lambda g:pos >> g.loc)
        if pos >> nearest_goal.loc < (Constants.SNAP_DIST/self.scale)**2:
            pos = nearest_goal.loc
        if self.step == 'start_tree':
            self.new_start_peg.loc = self.range_guide.loc = pos
        elif self.step == 'start_edge':
            self.snap_target.loc = self.range_guide.loc = self.current_tree.snap(pos)
        elif self.step == 'finish_edge':
            self.new_edge.p2 = nearest_on_disk(pos, self.new_edge.p1, self.distance_left)
        return pos

    def on_click(self):
        pos = self.process()
        if self.step == 'start_tree':
            self.new_start_peg.loc = pos
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
        if dist > Constants.TURN_DISTANCE+epsilon:
            print(dist)
            fail
        # does the round end
        if all(goal.team != self.turn or self.team_trees[self.turn].distsq(goal.loc) < epsilon for goal in self.layers[Layers.GOAL]): # issue: only checks current player's goals
            # simple version: the score you lose is the sum of distances from your tree to your goals
            for goal in self.layers[Layers.GOAL]:
                self.score[goal.team] -= trace(self.team_trees[goal.team].distsq(goal.loc)**.5)
            # just go straight to the next round
            self.load_state(self.make_initial_state(self.score))

        return True




if __name__=="__main__":
    pygame.init()
    run_local(Trans, sys.argv[1:])
