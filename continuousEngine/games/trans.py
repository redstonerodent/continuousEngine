from continuousEngine import *
import random

# turns & separate trees
# merging trees
# distribution abstract class & instances (core)

class Layers:
    DISTRIBUTION    = 1
    GOAL            = 2
    RANGE_GUIDE     = 3
    START_PEG       = 4
    SNAP_TARGET     = 5
    NEW_EDGE        = 6
    TREE            = 8
    SCORE           = 10
    DEBUG           = 20

class Colors:
    TREE            = (0, 0, 0)
    START_PEG       = {'red':(255,50,50), 'blue':(50,50,255), 'green':(50,255,50), 'yellow':(255,255,0), 'brown':(150, 150, 70), 'white':(255,255,255)}
    NEW_EDGE        = (100, 100, 100)
    RANGE_GUIDE     = (255,255,255)

class Sizes:
    # pixels
    SNAP_TARGET     = 5
    START_PEG       = 10


class TransTree(Renderable):
    def __init__(self, game):
        super().__init__(game, Layers.TREE)
        self.edges = {} # dictionary saying color of each edge

    def add_edge(self, edge, color=Colors.TREE):
        self.edges[edge] = color

    def merge(self, other):
        self.edges.update(other.edges)

    def snap(self, p): # nearest point on tree to p
        return min((nearest_on_segment(p, *edge) for edge in self.edges), key=p.__rshift__)

    def render(self):
        for e, c in self.edges.items():
            drawSegment(self.game, c, *e)

    def __bool__(self):
        return bool(self.edges)




class Trans(Game):

    def __init__(self, teams=2, **kwargs):
        super().__init__(name='continuous trans', **kwargs)
        teams = int(teams)
        if teams > len(self.possible_teams):
            print('{} is too many teams (max {}); defaulting to 2'.format(teams, len(self.possible_teams)), flush=True)
            teams = 2
        self.teams = self.possible_teams[:teams]
        # todo: generate objects, set keybinds

        self.tree = TransTree(self) # there needs to be a tree per player
        self.snap_target = Disk(self, Layers.SNAP_TARGET, Colors.TREE, None, Sizes.SNAP_TARGET, realRadius=False)
        self.snap_target.GETloc = lambda _: self.tree.snap(self.mousePos())
        self.snap_target.GETvisible = lambda _: self.mousePos() and self.tree and self.step == 'start_edge'

        self.new_edge = Segment(self, Layers.NEW_EDGE, Colors.NEW_EDGE, None, None)
        self.new_edge.GETvisible = lambda _: self.step == 'finish_edge'

        self.range_guide = Circle(self, Layers.RANGE_GUIDE, Colors.RANGE_GUIDE, None, None)
        self.range_guide.GETr = lambda _: self.distance_left
        self.range_guide.GETvisible = lambda _: self.mousePos() or self.step == 'finish_edge'

        self.click[1] = lambda _: self.on_click(self.mousePos())

        self.reset_state()

    def make_initial_state(self):
        pass

    possible_teams = ['red', 'blue', 'green', 'yellow', 'brown', 'white']

    def save_state(self):
        pass
    def load_state(self, state):
        self.step = 'start_tree'
        self.distance_left = 1
        self.turn = 'red'
        pass

    def is_over(self):
        pass
    def winner(self):
        pass

    def attemptGameMove(self, move):
        pass

    def process(self):
        pos = self.mousePos()
        if self.step == 'start_tree':
            self.range_guide.loc = self.mousePos()
        elif self.step == 'start_edge':
            self.range_guide.loc = self.tree.snap(self.mousePos())
        elif self.step == 'finish_edge':
            self.new_edge.p2 = self.mousePos() if self.mousePos() >> self.new_edge.p1 < self.distance_left ** 2 else nearest_on_circle(self.mousePos(), self.new_edge.p1, self.distance_left)
            self.range_guide.loc = self.new_edge.p1

    def on_click(self, pos):
        self.process()
        if self.step == 'start_tree':
            self.tree.add_edge((pos,pos))
            Disk(self, Layers.START_PEG, Colors.START_PEG[self.turn], pos, Sizes.START_PEG, realRadius=False)
            self.new_edge.p1 = pos
            self.step = 'finish_edge'
        elif self.step == 'start_edge':
            pos = self.range_guide.loc
            self.new_edge.p1 = pos
            self.step = 'finish_edge'
        elif self.step == 'finish_edge':
            self.tree.add_edge((self.new_edge.p1, self.new_edge.p2))
            self.distance_left -= (self.new_edge.p1 >> self.new_edge.p2)**.5
            if self.distance_left > epsilon:
                self.step = 'start_edge'
            else:
                self.turn = self.next_turn()
                self.distance_left = 1
                self.record_state()

if __name__=="__main__":
    pygame.init()
    run_local(Trans, sys.argv[1:])
