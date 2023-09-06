from continuousEngine import *

default_puzzle = [
        ((0,0), None),
        ((0,1), 'A'),
        ((1,1), None),
        ((1,0), 'B'),
    ]

def parse_file(file):
    with open(file) as f:
        out = []
        for l in f.readlines():
            if l[0] == '#':
                continue
            x, y, *s = l.split()
            s = (s+[None])[0] # leave blank for dot, represented as None
            out.append(((float(x),float(y)),s))
    return out

class Layers:
    NEWEDGE = 1
    EDGE = 2
    BADEDGE = 3
    CLUE = 4
    CLUETEXT = 5
class Colors:
    CLUE = (255,255,255)
    CLUEBORDER = (20,20,20)
    CLUEDOT = (30,30,30)
    EDGE = (0,0,0)
    NEWEDGE = (0,0,255)
    ILLEGAL = (255,0,0)
    BACKGROUND = (245,245,235)
    WIN = (120,245,120)
    FONT = (0,0,0)

class Constants:
    CLUERAD = 20
    CLUEBORDER = 3
    DOTRAD = 10

class Clue(BorderDisk):
    def __init__(self, game, loc, symbol):
        super().__init__(game, Layers.CLUE, None,
                Colors.CLUEBORDER, loc, Constants.CLUERAD if symbol else Constants.DOTRAD,
                width=Constants.CLUEBORDER, realRadius=False)
        normal_color = Colors.CLUE if symbol else Colors.CLUEDOT,
        self.GETfill_color = lambda g: Colors.ILLEGAL if self.illegal else normal_color
        self.loc, self.symbol = loc, symbol

        if symbol and not game.headless:
            Text(game, Layers.CLUETEXT, Colors.FONT, game.font, symbol, loc)

class Edges(Renderable):
    def __init__(self, game, layer, color):
        super().__init__(game, layer)
        self.color = color
        self.segments = []
    def render(self):
        for e in self.segments:
            drawSegment(self.game, self.color, *e)

class Kouchoku(Game):
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
        for l in [Layers.CLUE, Layers.CLUETEXT]: self.clearLayer(l)
        for c, s in clues: Clue(self, Point(*c), s)
        self.edges.segments = [{Point(*p1), Point(*p2)} for p1, p2 in segments]

        p, q = bounding_box([c.loc for c in self.layers[Layers.CLUE]])
        self.center = p%q
        self.spread = max((q-p).coords)/2+2

        self.clue_map = {c.loc:c.symbol for c in self.layers[Layers.CLUE]}
        self.clue_set = {c.symbol for c in self.layers[Layers.CLUE]} - {None}

    def save_state(self):
        return ([(clue.loc.coords, clue.symbol) for clue in self.layers[Layers.CLUE]],
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

        # make adjacency list
        edges = {c.loc:[] for c in self.layers[Layers.CLUE]}
        for p,q in self.edges.segments:
            edges[p].append(q)
            edges[q].append(p)

        # intersecting nonperpendicular edges
        for e1 in self.edges.segments:
            for e2 in self.edges.segments:
                a,b,c,d = *e1,*e2
                if not (e1 & e2) and intersect_segments(*e1, *e2) and abs((a-b)&(c-d)) > epsilon:
                    self.bad_edges.segments += [e1,e2]

        # edge through vertex
        for e in self.edges.segments:
            for c in self.layers[Layers.CLUE]:
                if c.loc not in e and dist_to_segment(c.loc, *e) < epsilon:
                    c.illegal = True
                    self.bad_edges.segments.append(e)

        # too high degree
        for c in self.layers[Layers.CLUE]:
            if len(edges[c.loc]) > 2:
                c.illegal = True

        # connected different symbols
        for e in self.edges.segments:
            p,q = e
            if len({self.clue_map[p], self.clue_map[q]}-{None})==2:
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

        # stop if issues, or if not a full loop yet
        if self.bad_edges.segments or len(self.edges.segments) < len(self.layers[Layers.CLUE]):
            return

        # matching clues not consecutive: assumes there's a single cycle and no connected different clues
        # just checks if more than 2 edges between s clues and dots
        counts = {s:0 for s in self.clue_set}
        for e in self.edges.segments:
            ss = {self.clue_map[v] for v in e}
            print(ss)
            if len(ss) == 2:
                s, = ss - {None}
                counts[s] += 1
        print(counts)
        for c in self.layers[Layers.CLUE]:
            if c.symbol and counts[c.symbol] != 2:
                c.illegal = True

        if any(c.illegal for c in self.layers[Layers.CLUE]):
            return

        self.background.color = Colors.WIN

if __name__=="__main__":
    pygame.init()
    run_local(Kouchoku, sys.argv[1:])
