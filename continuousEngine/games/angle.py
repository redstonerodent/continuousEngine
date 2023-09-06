from continuousEngine import *

default_puzzle = [
        ((0,0), 4),
        ((0,1), 4),
        ((2,0), 5),
        ((3,1), 3),
    ]

def parse_file(file):
    with open(file) as f:
        out = []
        for l in f.readlines():
            if l[0] == '#' or l == '\n':
                continue
            x, y, s = l.split()
            if s not in ['3','4','5']:
                raise ValueError(f'{s} is an illegal number of sides')
            out.append(((float(x),float(y)),int(s)))
    return out

class Layers:
    NEWEDGE = 1
    EDGE = 2
    BADEDGE = 3
    CLUE = 4
class Colors:
    CLUE = {3:(80,80,80), 4:(160,160,160), 5:(240,240,240)}
    CLUEBORDER = (30,30,30)
    EDGE = (0,0,0)
    NEWEDGE = (0,0,255)
    ILLEGAL = (255,0,0)
    BACKGROUND = (245,245,235)
    WIN = (120,245,120)

class Constants:
    CLUERAD = 20
    CLUEBORDER = 3

class Clue(PolygonIcon):
    def __init__(self, game, loc, sides):
        # 3=acute, 4=right, 5=obtuse
        super().__init__(game, Layers.CLUE, loc, sides,
                None, Colors.CLUEBORDER, Constants.CLUERAD, Constants.CLUEBORDER,
                rotation=math.pi/4 if sides==4 else math.pi)
        self.GETfill_color = lambda g: Colors.ILLEGAL if self.illegal else Colors.CLUE[sides]

class Edges(Renderable):
    def __init__(self, game, layer, color):
        super().__init__(game, layer)
        self.color = color
        self.segments = []
    def render(self):
        for e in self.segments:
            drawSegment(self.game, self.color, *e)

class Angle(Game):
    def __init__(self, file=None, **kwargs):
        try:
            self.puzzle = parse_file(file)
        except Exception as e:
            print(f'failed to load puzzle (using default): {e}')
            self.puzzle = default_puzzle

        self.turn = 'solver'
        self.teams = [self.turn]

        super().__init__(name='angle loop', **kwargs)

        self.newedge = Segment(self, Layers.NEWEDGE, Colors.NEWEDGE, None, None)
        self.newedge.GETp2 = lambda g: g.mousePos()
        self.newedge.GETvisible = lambda g: self.newedge.p1 and self.newedge.p2

        self.edges = Edges(self, Layers.EDGE, Colors.EDGE)
        self.bad_edges = Edges(self, Layers.BADEDGE, Colors.ILLEGAL)

        self.background = self.layers[-10**10][0] # hacky

        self.reset_state()
        if not self.headless: self.reset_view()

        self.nearest_clue = lambda p: min(self.layers[Layers.CLUE], key=lambda c: p >> c.loc)

        self.click[1] = lambda e: setattr(self.newedge, 'p1', self.nearest_clue(self.point(*e.pos)).loc)

        def mouseup(e):
            if e.button != 1: return
            self.attemptMove({'player':self.turn, 'p1':self.newedge.p1.coords, 'p2':self.point(*e.pos).coords})
            self.newedge.p1 = None

        self.handlers[pygame.MOUSEBUTTONUP] = mouseup

        self.prep_turn()

    def load_state(self, state):
        clues, segments = state
        self.clearLayer(Layers.CLUE)
        for c, s in clues: Clue(self, Point(*c), s)
        self.edges.segments = [{Point(*p1), Point(*p2)} for p1, p2 in segments]

        p, q = bounding_box([c.loc for c in self.layers[Layers.CLUE]])
        self.center = p%q
        self.spread = max((q-p).coords)/2+2

    def save_state(self):
        return ([(clue.loc.coords, clue.sides) for clue in self.layers[Layers.CLUE]],
                [(p1.coords, p2.coords) for p1, p2 in self.edges.segments])

    def make_initial_state(self):
        return (self.puzzle, [])

    def attemptGameMove(self, move):
        p1 = self.nearest_clue(Point(*move['p1'])).loc
        p2 = self.nearest_clue(Point(*move['p2'])).loc
        if p1 == p2:
            return False
        self.record_state()
        if {p1, p2} in self.edges.segments:
            self.edges.segments.remove({p1, p2})
        else:
            self.edges.segments.append({p1, p2})
        return True

    def prep_turn(self):
        # reset
        for c in self.layers[Layers.CLUE]:
            c.illegal = False
        self.bad_edges.segments = []
        self.background.color = Colors.BACKGROUND

        # make adjacency list
        edges = {c.loc:[] for c in self.layers[Layers.CLUE]}
        for p,q in self.edges.segments:
            edges[p].append(q)
            edges[q].append(p)

        # too high degree or wrong angle
        for c in self.layers[Layers.CLUE]:
            if len(edges[c.loc]) < 2:
                continue
            if len(edges[c.loc]) > 2:
                c.illegal = True
                continue
            p, q = edges[c.loc]
            x,y = p-c.loc, q-c.loc
            normdot = x&y/(+x*+y)**.5
            c.illegal = {
                    3: lambda d: d<epsilon,
                    4: lambda d: abs(d)>epsilon,
                    5: lambda d: d>-epsilon or abs(d+1) < epsilon }[c.sides](normdot)

        # intersecting edges
        for e1 in self.edges.segments:
            for e2 in self.edges.segments:
                if not (e1 & e2) and intersect_segments(*e1, *e2):
                    self.bad_edges.segments += [e1,e2]

        # edge through vertex
        for e in self.edges.segments:
            for c in self.layers[Layers.CLUE]:
                if c.loc not in e and dist_to_segment(c.loc, *e) < epsilon:
                    c.illegal = True
                    self.bad_edges.segments.append(e)

        # stop if any problems so far
        if self.bad_edges.segments or any(c.illegal for c in self.layers[Layers.CLUE]):
            return

        # too small loop: code assumes degrees at most two
        vertices = set(edges)

        while vertices:
            v0 = next(iter(vertices))
            vertices.remove(v0)
            if not edges[v0]: continue
            vold, v = v0, next(iter(edges[v0]))
            cycle = [v0]
            while v != v0 and len(edges[v]) == 2:
                cycle.append(v)
                if v in vertices: vertices.remove(v)
                vold, v = v, *(set(edges[v])-{vold})
            if v == v0 and len(cycle) < len(edges):
                self.bad_edges.segments.extend([{cycle[i], cycle[i-1]} for i in range(len(cycle))])

        # again stop if issues
        if self.bad_edges.segments:
            return

        self.background.color = Colors.WIN if all(len(edges[v])==2 for v in edges) else Colors.BACKGROUND


if __name__=="__main__":
    pygame.init()
    run_local(Angle, sys.argv[1:])
