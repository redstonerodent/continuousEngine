from continuousEngine import *


puzzle1 = [ # xoned72 | https://puzz.link/p?angleloop/7/7/b1c4a3c0a1a5b4c3c0c3b3a3c0b1a0a0b
    ((0,0), 4),
    ((3,0), 5),
    ((1,1), 3),
    ((6,1), 5),
    ((0,2), 3),
    ((3,2), 3),
    ((2,3), 4),
    ((0,4), 5),
    ((5,4), 5),
    ((7,4), 5),
    ((4,5), 4),
    ((1,6), 3),
    ((6,6), 5),
    ((0,7), 4),
    ((7,7), 4),
    ((3,7), 3),
    ((5,7), 3),
    ((7,7), 4),
]

puzzle2 = [ # nu_n_notami | https://puzz.link/p?angleloop/9/9/1a96b0b3b2b5c0a2bb95b3b7a1c90c2c3
    ((2,0), 3),
    ((0,2), 4),
    ((2,2), 4),
    ((7,2), 4),
    ((1,3), 4),
    ((8,3), 5),
    ((0,4), 3),
    ((4,4), 4),
    ((5,4), 4),
    ((2,6), 4),
    ((7,6), 4),
    ((6,7), 3),
    ((9,7), 5),
    ((1,9), 5),
    ((5,9), 5),
]

puzzle = puzzle2

# rotate it by some angle, for extra fun
t = .3
puzzle = [((math.cos(t)*x-math.sin(t)*y, math.sin(t)*x+math.cos(t)*y), s) for (x,y), s in puzzle]

class Layers:
    NEWEDGE = 1
    EDGE = 2
    BADEDGE = 3
    CLUE = 4
class Colors:
    CLUE = {3:(80,80,80), 4:(160,160,160), 5:(240,240,240)}
    CLUE_BORDER = (30,30,30)
    EDGE = (0,0,0)
    NEWEDGE = (0,0,255)
    ILLEGAL = (255,0,0)
    BACKGROUND = (245,245,235)
    WIN = (0,255,0)

class Constants:
    CLUE_RAD = 20
    CLUE_BORDER = 3

class Clue(PolygonIcon):
    def __init__(self, game, center, sides):
        # 3=acute, 4=right, 5=obtuse
        super().__init__(game, Layers.CLUE, center, sides,
                None, Colors.CLUE_BORDER, Constants.CLUE_RAD, Constants.CLUE_BORDER,
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
    def __init__(self, **kwargs):
        self.puzzle = puzzle

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

        p, q = bounding_box([c.center for c in self.layers[Layers.CLUE]])
        self.center = p%q
        self.spread = max((q-p).coords)/2+2

        self.nearest_clue = lambda p: min(self.layers[Layers.CLUE], key=lambda c: p >> c.center)

        self.click[1] = lambda e: setattr(self.newedge, 'p1', self.nearest_clue(self.point(*e.pos)).center)

        def mouseup(e):
            if e.button != 1: return
            self.attemptMove({'player':self.turn, 'p1':self.newedge.p1, 'p2':self.point(*e.pos)})
            self.newedge.p1 = None

        self.handlers[pygame.MOUSEBUTTONUP] = mouseup

        self.prep_turn()
        self.reset_view()

    def load_state(self, state):
        clues, segments = state
        self.clearLayer(Layers.CLUE)
        for c, s in clues: Clue(self, Point(*c), s)
        self.edges.segments = [{Point(*p1), Point(*p2)} for p1, p2 in segments]

    def save_state(self):
        return ([(clue.center.coords, clue.sides) for clue in self.layers[Layers.CLUE]],
                [(p1.coords, p2.coords) for p1, p2 in self.edges.segments])

    def make_initial_state(self):
        return (self.puzzle, [])

    def attemptGameMove(self, move):
        p1 = self.nearest_clue(move['p1']).center
        p2 = self.nearest_clue(move['p2']).center
        if p1 == p2:
            return False
        self.record_state()
        if {self.newedge.p1, p2} in self.edges.segments:
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
        edges = {c.center:[] for c in self.layers[Layers.CLUE]}
        for e in self.edges.segments:
            p, q = e
            edges[p].append(q)
            edges[q].append(p)

        # too high degree or wrong angle
        for c in self.layers[Layers.CLUE]:
            if len(edges[c.center]) < 2:
                continue
            if len(edges[c.center]) > 2:
                c.illegal = True
                continue
            p, q = edges[c.center]
            d = (p-c.center) & (q-c.center)
            print(d)
            c.illegal = {
                    3: lambda x: x<epsilon,
                    4: lambda x: abs(x)>epsilon,
                    5: lambda x: x>-epsilon }[c.sides](d)
        # intersecting edges
        for e1 in self.edges.segments:
            for e2 in self.edges.segments:
                if not (e1 & e2) and intersect_segments(*e1, *e2):
                    self.bad_edges.segments += [e1,e2]

        # edge through vertex
        for e in self.edges.segments:
            for c in self.layers[Layers.CLUE]:
                if c.center not in e and dist_to_segment(c.center, *e) < epsilon:
                    c.illegal = True
                    self.bad_edges.segments.append(e)

        good_so_far = not self.bad_edges.segments and not any(c.illegal for c in self.layers[Layers.CLUE])
        # too small loop: only display if nothing else wrong
        # code assumes degrees at most two
        if good_so_far:
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
                    good_so_far = False

        self.background.color = Colors.WIN if good_so_far and all(len(edges[v])==2 for v in edges) else Colors.BACKGROUND


if __name__=="__main__":
    pygame.init()
    run_local(Angle, sys.argv[1:])
