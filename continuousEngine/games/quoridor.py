from continuousEngine import *

class Layers:
    BOARD = 1
    WALL = 8
    PAWN = 4
    GHOST = 6
    GUIDE = 3

class Colors:
    BACKGROUND = (181, 108, 53)
    BOARD = (0,0,0)
    WALL = (219, 159, 75)
    PAWN = {'white':(255,255,255), 'brown':(105, 63, 24), 'black':(0,0,0), 'red':(201, 26, 6)}
    SELECTED = (0,255,0)
    WRONG = (255,0,0)
    CORNER = (230,230,0)
    TURN = (0,200,200)

class Constants:
    TEAMS = ['white', 'brown', 'black', 'red']
    # game units
    PAWN_RAD = .5
    WALL_LEN = 2
    BOARD_RAD = 5
    PAWN_LIMIT = BOARD_RAD - PAWN_RAD
    MOVE_DIST = 1
    GOAL_WIDTH = 5

class Wall(Segment):
    def __init__(self, game, p1, p2, layer = Layers.WALL):
        super().__init__(game, layer, None, p1, p2)
        self.GETcolor = lambda g: Colors.WRONG if self in g.blockers else Colors.WALL

class Pawn(BorderDisk):
    def __init__(self, game, team, goal, loc, layer = Layers.PAWN):
        super().__init__(game, layer, team and Colors.PAWN[team], None, loc, Constants.PAWN_RAD, borderGrowth=0)
        self.team, self.goal = team, goal
        self.GETborder_color = lambda g: \
            Colors.SELECTED if g.current_pawn == self and self in g.blockers and g.state == 'start' else \
            Colors.WRONG if self in g.blockers else \
            Colors.TURN if g.current_pawn == self else \
            Colors.PAWN[self.team]

class Debugger(Renderable):
    def render(self):
        for p in self.game.graph.edges:
            for q in self.game.graph.edges[p]:
                drawSegment(self.game, (255,255,0), p,q, width=1)
        for p in self.game.graph.edges:
            drawCircle(self.game, (120,120,0), p, 5, realRadius=False)
        for i in range(len(self.game.cycle)):
            drawSegment(self.game, (120,120,0), self.game.cycle[i-1], self.game.cycle[i], width=3)

class Border(Circle):
    def __init__(self, game):
        super().__init__(game, Layers.BOARD, None, Point(0,0), Constants.BOARD_RAD)
        self.GETcolor = lambda g: Colors.WRONG if self in g.blockers else Colors.BOARD
    def render(self):
        super().render()
        for i,t in enumerate(self.game.teams):
            mid = 2*pi*i/len(self.game.teams) + pi
            drawArc(self.game, Colors.PAWN[t], Point(0,0), Constants.BOARD_RAD, mid - pi/6, mid + pi/6, width=Constants.GOAL_WIDTH, borderGrowth=0)

class Graph:
    # undirected graphs; vertices are Points
    # a cycle corresponds to a region that traps a pawn
    # edges is {vertex: {adjacent vertices}
    def __init__(self, x=None):
        self.edges = x or {}
    def add_edge(self, p, q):
        if p not in self.edges: self.edges[p] = set()
        if q not in self.edges: self.edges[q] = set()
        self.edges[p].add(q)
        self.edges[q].add(p)
    def __add__(self, other):
        ans = {}
        for p in self.edges | other.edges:
            ans[p] = set()
            if p in self.edges: ans[p] |= self.edges[p]
            if p in other.edges: ans[p] |= other.edges[p]
        return Graph(ans)
    def negative_cycle(self, weight):
        # bellman-ford
        value = {p:0 for p in self.edges}
        parent = {p:None for p in self.edges}

        weights = {(p,q): weight(p,q) for p,qs in self.edges.items() for q in qs}

        # this is pretty slow on dense instances
        # todo: do something smarter than bellman-ford
        # e.g. the weights have a lot of structure and bellman-ford is wasteful
        for _ in self.edges: # repeat |V| times
            for p,qs in self.edges.items():
                for q in qs:
                    if (x := value[p] + weights[p,q]) < value[q] - epsilon:
                        value[q], parent[q] = x, p

        for p in self.edges:
            for q in self.edges[p]:
                if value[p] + weight(p,q) < value[q] - epsilon:
                    # follow parent pointers to find negative cycle
                    seen = {q}
                    while p not in seen:
                        seen.add(p)
                        p = parent[p]
                    start, p = p, parent[p]
                    cycle = [start]
                    while p != start:
                        cycle.append(p)
                        p = parent[p]
                    return cycle
        return None


class Quoridor(Game):
    def __init__(self, teams=2, **kwargs):
        self.team_count = int(teams)
        super().__init__(backgroundColor=Colors.BACKGROUND, name='continuous quoridor', spread=Constants.BOARD_RAD, **kwargs)

        self.border = Border(self)

        self.wall_ghost = Wall(self, None, None, Layers.GHOST)
        self.wall_ghost.GETvisible = lambda g: g.state == 'wall'
        self.wall_ghost.GETcolor = lambda g: Colors.WRONG if g.blockers else Colors.SELECTED
        self.wall_ghost.GETp1 = lambda g: g.selected
        self.wall_ghost.GETp2 = lambda g: g.wall_end(g.selected, g.mousePos())

        pawn_corner_ghost = Pawn(self, None, None, None, Layers.GHOST)
        pawn_corner_ghost.GETvisible = lambda g: g.state == 'pawn' and g.corner
        pawn_corner_ghost.border_color = Colors.CORNER
        pawn_corner_ghost.GETloc = lambda g: g.corner

        pawn_ghost = Pawn(self, None, None, None, Layers.GHOST)
        pawn_ghost.GETvisible = lambda g: g.state == 'pawn'
        pawn_ghost.border_color = Colors.SELECTED
        pawn_ghost.GETloc = lambda g: g.curr_target

        move_guide_1 = FilledPolygon(self, Layers.GUIDE, None, None)
        move_guide_1.GETvisible = lambda g: g.state == 'pawn'
        move_guide_1.GETpoints = lambda g: g.move_rect(g.selected.loc, g.corner or g.curr_target)

        move_guide_2 = FilledPolygon(self, Layers.GUIDE, None, None)
        move_guide_2.GETvisible = lambda g: g.state == 'pawn' and g.corner
        move_guide_2.GETpoints = lambda g: g.move_rect(g.corner, g.curr_target)

        pawn_corner_ghost.GETfill_color = pawn_ghost.GETfill_color = move_guide_1.GETcolor = move_guide_2.GETcolor = lambda g: Colors.PAWN[g.turn]

        self.debug = Debugger(self, 1000)
        self.debug.visible = False
        self.keyPress[pygame.K_SPACE] = lambda e: setattr(self.debug, 'visible', not self.debug.visible)

        self.reset_state()

        self.click[1] = lambda e: self.on_click(self.point(*e.pos))

    def load_state(self, state):
        for l in [Layers.WALL, Layers.PAWN]: self.clearLayer(l)
        self.turn, teams, walls, pawns = state
        self.teams = teams.copy()
        [Wall(self, Point(*p1), Point(*p2)) for p1, p2 in walls]
        [Pawn(self, team, Point(*goal), Point(*loc)) for team, goal, loc in pawns]
        self.prep_turn()

    save_state = lambda self: (self.turn, self.teams.copy(), [(w.p1.coords, w.p2.coords) for w in self.layers[Layers.WALL]], [(p.team, p.goal.coords, p.loc.coords) for p in self.layers[Layers.PAWN]])

    def make_initial_state(self):
        teams = Constants.TEAMS[:self.team_count]
        return (teams[0], teams, [], [(t, (p:=Point(0,0,Constants.PAWN_LIMIT-epsilon,2*pi*i/len(teams))).coords, (-1*p).coords) for i,t in enumerate(teams)])

    wall_end = lambda self, p1, p2: p1 + (p2 - p1) @ Constants.WALL_LEN

    def pawn_target(self, pawn, end):
        # player attempts to move pawn to end
        # where does it actually go?
        blockers = []
        corner = None

        # 1: cap at MOVE_DIST
        end = nearest_on_disk(end, pawn.loc, Constants.MOVE_DIST)

        # 2: get blocked by border and walls, and adjust to the first tangency
        if +end > Constants.PAWN_LIMIT**2:
            end = slide_to_circle(pawn.loc, end, Point(0,0), Constants.PAWN_LIMIT)
            blockers = [self.border]
        for b in self.layers[Layers.WALL]:
            if (x:=intersection_segment_oval(pawn.loc, end, b.p1, b.p2, Constants.PAWN_RAD)):
                end = min(x, key = lambda x: pawn.loc >> x)
                blockers = [b]
        if blockers:
            end -= (end - pawn.loc) @ epsilon # avoid floating point issues

        # 3: if the final position overlaps a pawn...
        ps = self.pawn_pawn_blockers(pawn, end)
        blockers += ps
        if len(ps) > 1: raise NotImplementedError # todo idk what should happen here (when it overlaps two pawns)
        elif ps:
            p_on = ps[0]
            corner = end
            # 3a: continue past the pawn to tangency
            end = slide_to_circle(end, 2*end - pawn.loc, p_on.loc, 2*Constants.PAWN_RAD)

            # everything the new location overlaps is a blocker
            blockers += self.pawn_pawn_blockers(pawn, end, [p_on]) + self.nonpawn_pawn_blockers(pawn, end, corner)
            # as is the last thing in its way while adjusting
            last_blocker = None

            # 3b: the move makes a sharp turn at corner, which is where it'd end if there weren't a pawn
            # change the angle of the leg after corner to avoid collisions, remaining tangent
            # we will bend in the direction base on which side of p_on the corner is
            sign = above_line(corner, pawn.loc, p_on.loc)
            while (b := next(iter(self.pawn_pawn_blockers(pawn, end, [p_on]) + self.nonpawn_pawn_blockers(pawn, end, corner)), None)):
                if isinstance(b, Border):
                    candidates = intersection_circles(p_on.loc, Point(0,0), 2*Constants.PAWN_RAD, Constants.BOARD_RAD - Constants.PAWN_RAD)
                elif isinstance(b, Wall):
                    delta = (~(b.p1-b.p2) @ Constants.PAWN_RAD)
                    # 2 kinds of candidate: intersections with oval around b
                    # and moves tangent to the oval, so the path touches the end of the wall
                    candidates = \
                        intersection_circle_oval(p_on.loc, 2*Constants.PAWN_RAD, b.p1, b.p2, Constants.PAWN_RAD) + \
                        [p for u, v in [(b.p1, b.p2), (b.p2, b.p1)] for l in tangents_to_circle(corner, u, Constants.PAWN_RAD) if (l-u)&(u-v)>=0 for p in intersection_ray_circle(corner, l, p_on.loc, 2*Constants.PAWN_RAD) if between(corner, l, p)]

                    # remove candidates that would involve moving through the wall
                    candidates = [p for p in candidates if not intersect_segment_conv_polygon(b.p1, b.p2, self.move_rect(corner, p))]
                    # in theory there should be exactly two candidates now (one on each side of the wall)
                    if len(candidates) != 2: print(f'WARNING: there are {len(candidates)} candidates; expected 2')

                elif isinstance(b, Pawn):
                    candidates = intersection_circles(p_on.loc, b.loc, 2*Constants.PAWN_RAD)
                # pick the candidate so the path bends in the direction indicated by sign
                # there should always be exactly one of them
                end, = [c for c in candidates if above_line(c, corner, end) == sign]
                # avoid floating point issues
                end += ~((-1)**sign * (p_on.loc-end)) @ epsilon

                last_blocker = b


            if last_blocker: blockers.append(last_blocker)
        return end, blockers, corner

    def move_rect(self, loc, end): # rectangle that the pawn moves through
        delta = ~(end-loc) @ (Constants.PAWN_RAD - epsilon)
        return [end-delta, end+delta, loc+delta, loc-delta]

    def on_click(self, loc):
        if self.state == 'start':
            if Point(0,0) >> loc > Constants.BOARD_RAD**2: return
            on_pawns = [p for p in self.layers[Layers.PAWN] if p.loc >> loc < Constants.PAWN_RAD**2]
            if len(on_pawns)>1: raise ValueError
            if on_pawns:
                if on_pawns[0].team == self.turn:
                    self.state = 'pawn'
                    self.selected = on_pawns[0]
            else:
                self.state = 'wall'
                self.selected = loc
        elif self.state == 'pawn':
            self.attemptMove({'player':self.turn, 'type':'pawn', 'location':loc.coords})
        elif self.state == 'wall':
            self.attemptMove({'player':self.turn, 'type':'wall', 'p1':self.selected.coords, 'p2':loc.coords})

    def attemptGameMove(self, move):
        if move['type'] == 'pawn':
            target, *_ = self.pawn_target(self.current_pawn, Point(*move['location']))
            self.record_state()
            self.current_pawn.loc = target
        elif move['type'] == 'wall':
            p1 = Point(*move['p1'])
            p2 = self.wall_end(p1, Point(*move['p2']))
            if self.wall_blockers(p1, p2): return
            if p1 == p2: return
            self.record_state()
            Wall(self, p1, self.wall_end(p1, p2))
        return True

    def prep_turn(self):
        self.state = 'start'
        self.selected = None
        self.blockers = []
        self.current_pawn = next(p for p in self.layers[Layers.PAWN] if p.team == self.turn)
        self.graph_cache = self.bottlenecks()

    def bottlenecks(self, wall=None):
        # graph of bottlenecks pawns can't fit through
        # if wall is given, only the new bottlenecks that wall causes
        # otherwise all of them

        # start with diamond surrounding the board to represent the boundary
        g = Graph() if wall else \
            Graph({Point(0, i*2*Constants.BOARD_RAD): {Point(j*2*Constants.BOARD_RAD, 0) for j in [-1,1]} for i in [-1,1]} | \
                {Point(i*2*Constants.BOARD_RAD, 0): {Point(0, j*2*Constants.BOARD_RAD) for j in [-1,1]} for i in [-1,1]})

        for w in [wall] if wall else self.layers[Layers.WALL]:
            # count walls as bottlenecks
            g.add_edge(w.p1, w.p2)
            for p in [w.p1,w.p2]:
                # bottlenecks with border: connect to the diamond, staying outside the board
                if +p > (Constants.BOARD_RAD-2*Constants.PAWN_RAD)**2:
                    g.add_edge(p, (x := p@2*Constants.BOARD_RAD))
                    g.add_edge(x, Point(2*Constants.BOARD_RAD*(-1)**(p.x < 0), 0))
            for other in self.layers[Layers.WALL]:
                # bottlenecks between walls: edge from end of wall to point on another wall, and connect that to p1
                for p in [w.p1,w.p2]:
                    m = nearest_on_segment(p, other.p1, other.p2)
                    if p>>m < (2*Constants.PAWN_RAD)**2:
                        g.add_edge(p, m)
                        g.add_edge(m, other.p1)
                if wall: # need to check wall-wall bottlenecks the other way
                    for p in [other.p1, other.p2]:
                        m = nearest_on_segment(p, w.p1, w.p2)
                        if p>>m < (2*Constants.PAWN_RAD)**2:
                            g.add_edge(p, m)
                            g.add_edge(m, w.p1)
        return g


    def nonpawn_pawn_blockers(self, pawn, end, loc = None):
        rect = self.move_rect(loc or pawn.loc, end)
        return  [w for w in self.layers[Layers.WALL] if intersect_segment_disk(w.p1, w.p2, end, Constants.PAWN_RAD) or intersect_segment_conv_polygon(w.p1, w.p2, rect)] + \
                [b for b in self.layers[Layers.BOARD] if (+end > (Constants.BOARD_RAD - Constants.PAWN_RAD)**2)]

    def pawn_pawn_blockers(self, pawn, end, ignore = []):
        return [p for p in self.layers[Layers.PAWN] if p not in ignore + [pawn] and p.loc >> end < (2*Constants.PAWN_RAD)**2]

    def wall_blockers(self, start, end):
        return [p for p in self.layers[Layers.PAWN] if intersect_segment_disk(start, end, p.loc, Constants.PAWN_RAD)] + \
            [w for w in self.layers[Layers.WALL] if intersect_segments(start, end, w.p1, w.p2)] + \
            [b for b in self.layers[Layers.BOARD] if (Point(0,0) >> start > Constants.BOARD_RAD**2 or Point(0,0) >> end > Constants.BOARD_RAD**2)]

    def pawns_under(self, pt):
        return [p for p in self.layers[Layers.PAWN] if p.loc >> pt < Constants.PAWN_RAD**2]

    def process(self):
        if self.mousePos():
            self.graph = self.graph_cache # remove when done
            self.cycle = []
            if self.state == 'start':
                self.blockers = self.pawns_under(self.mousePos())
            elif self.state == 'pawn':
                self.curr_target, self.blockers, self.corner = self.pawn_target(self.selected, self.mousePos())
            elif self.state == 'wall':
                self.blockers = self.wall_blockers(self.wall_ghost.p1, self.wall_ghost.p2)
                if self.blockers: return
                self.graph = self.graph_cache + self.bottlenecks(self.wall_ghost)
                for pawn in self.layers[Layers.PAWN]:
                    if (cycle := self.graph.negative_cycle(lambda p,q: signed_angle(p,pawn.loc,q) - signed_angle(p,pawn.goal,q))):
                        # mark objects involved in cycle as blockers
                        for p in cycle:
                            if +p > Constants.BOARD_RAD**2:
                                self.blockers.extend(self.layers[Layers.BOARD])
                            else:
                                self.blockers.extend(w for w in self.layers[Layers.WALL] if dist_to_segment(p, w.p1, w.p2) < epsilon)
                        self.cycle = cycle
                        return


if __name__=='__main__':
    pygame.init()
    run_local(Quoridor, sys.argv[1:])
