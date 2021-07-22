from continuousEngine import *
import random
import math

hammer_rad = 1
board_rad = 7
num_cells = 60

# is point p on the board?
on_board = lambda p: +p < board_rad**2

class Colors:
    ice         = {'white': (255,255,255), 'blue':   (0,0,255), 'silver': (100,140,140), 'lightblue': (0,255,255)}
    hammer      = {'white': (255,255,255), 'blue':   (0,0,255), 'silver': (170,170,170), 'lightblue': (0,150,255)}
    ghost_hole  = {'white': (150,150,150), 'blue': (25,25,125), 'silver': (100,100,100), 'lightblue': (80,80,150)}
    hole = (0,0,150)
    debug = [(255,0,0),(0,255,0),(0,0,255),(0,0,0),(255,255,255)]
    boundary = (120,120,120)
    legal = (0,255,0)
    illegal = (255,0,0)
    text = (190,80,0)
    voronoi_opacity = 80
    background = (140,220,255)

class Layers:
    new_hole = 2
    hammer = 2.5
    voronoi = 3
    holes = 5
    boundary = 10
    warning = 14
    hammer_border=14.5
    penguin = 15
    game_over = 16
    debug = 20

class JrapHole(Renderable):
    def __init__(self, game, layer, hits, color=Colors.hole):
        super().__init__(game, layer)
        self.update(hits)
        self.color = color

    def update(self, hits):
        self.hits = convex_hull(hits)
        self.segments = [(lambda d:[self.hits[i-1]+d,self.hits[i]+d])(~(self.hits[i-1]-self.hits[i]) @ hammer_rad) for i in range(len(self.hits))]
        self.poly = sum(self.segments, [])

        # angular intervals the polygon covers
        poly_ints = intersect_polygon_circle_arcs(self.poly, Point(0,0), board_rad)
        # angular intervals circles cover
        circle_ints = [(atan2(*a),atan2(*b)) for a,b in filter(lambda x:x, ((intersect_circles(Point(0,0), p, board_rad, hammer_rad)) for p in self.hits))]
        self.intervals = poly_ints+circle_ints


    def render(self):
        for h in self.hits:
            drawCircle(self.game, self.color, h, hammer_rad)
        drawPolygon(self.game, self.color, self.poly)
        if 0:
            for h in self.hits:
                drawCircle(self.game, Colors.debug[0], h, hammer_rad, width=2)
            drawPolygon(self.game, Colors.debug[1], self.poly, width=2)
            for a,b in self.intervals:
                drawCircle(self.game, Colors.debug[3], Point(math.sin(a), math.cos(a))*board_rad, 7, realRadius=False)
                drawCircle(self.game, Colors.debug[4], Point(math.sin(b), math.cos(b))*board_rad, 7, realRadius=False)


    def intersecting(self, other):
        return (any(p1>>p2 < (2*hammer_rad)**2 for p1 in self.hits for p2 in other.hits)
            or any(dist_to_segment(p,*seg) < hammer_rad for p in self.hits for seg in other.segments)
            or any(dist_to_segment(p,*seg) < hammer_rad for p in other.hits for seg in self.segments)
            or any(intersect_segments(*seg1, *seg2) for seg1 in self.segments for seg2 in other.segments)
            )

    def merge(self, other):
        self.update(self.hits + other.hits)

    def __contains__(self, point):
        return point_in_polygon(point, self.poly) or any(h>>point < hammer_rad**2 for h in self.hits)

    def contains_cell(self, cell):
        # is the intersection of the voronoi cell and the board completely inside this hole?
        return all(p in self for p in self.game.voronoi.board_pts[cell]) and (self.game.voronoi.uncovered_arcs[cell]==[] or interval_cover_circle(self.intervals + self.game.voronoi.uncovered_arcs[cell]))


class JrapVoronoi(CachedImg):
    def __init__(self, game, layer):
        def gen(_):
            self.mask = pygame.Surface(self.game.size()).convert_alpha(self.game.screen)
            self.scratch = pygame.Surface(self.game.size()).convert_alpha(self.mask)
            self.mask.fill((0,0,0,0))
            self.scratch.fill((0,0,0,0))
            drawCircle(self.game, (255,255,255, Colors.voronoi_opacity), Point(0,0), board_rad, surface=self.mask)
            for p in self.player:
                drawPolygon(self.game, Colors.ice[self.player[p]], self.diagram.voronoi_vertices[p], surface=self.scratch)
            self.mask.blit(self.scratch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            return self.mask
        super().__init__(game, layer, 'voronoi', gen)
    def reset(self, cells):
        # cells is a list of ( point, color )
        self.diagram = Voronoi(Point(board_rad, board_rad), Point(-board_rad, -board_rad))
        
        for p,_ in cells: self.diagram.add(p)

        self.player = dict(cells)

        # arcs of the board boundary not in this cell (empty list of the cell doesn't intersect the boundary)
        # relies on voronoi vertices being listed 'backwards'
        self.uncovered_arcs = {p: intersect_polygon_circle_arcs(self.diagram.voronoi_vertices[p], Point(0,0), board_rad) for p,_ in cells}
        # vertices on the board and intersections with the boundary
        self.board_pts = {p: (lambda pts: sum(([pts[i]] if on_board(pts[i]) else [slide_to_circle(pts[i], pts[i-1], Point(0,0), board_rad)]*on_board(pts[i-1])+[slide_to_circle(pts[i], pts[(i+1)%len(pts)], Point(0,0), board_rad)]*on_board(pts[(i+1)%len(pts)]) for i in range(len(pts))),[]))(self.diagram.voronoi_vertices[p]) for p,_ in cells}

        self.game.clearCache()

class JrapPenguin(CachedImg):
    def __init__(self, game):
        # penguin icon from Freepik
        super().__init__(game, Layers.penguin, 'penguin', lambda _: pygame.image.load(os.path.join(PACKAGEPATH, 'Sprites/penguin.png')).convert_alpha(game.screen), loc=Point(0,0))

class JrapDebugger(Renderable):
    def render(self):
        for p in self.game.voronoi.player:
            drawCircle(self.game, Colors.debug[p in self.game.open_cells[self.game.voronoi.player[p]]], p, 3, realRadius=False)
        if self.game.mousePos():
            n = self.game.voronoi.diagram.nearest(self.game.mousePos())
            for p in self.game.voronoi.board_pts[n]:
                drawCircle(self.game, Colors.debug[(p in self.game.new_hole)+1], p, 3, realRadius=False)

            for a,b in self.game.voronoi.uncovered_arcs[n]:
                drawCircle(self.game, Colors.debug[3], Point(math.sin(a), math.cos(a))*board_rad, 7, realRadius=False)
                drawCircle(self.game, Colors.debug[4], Point(math.sin(b), math.cos(b))*board_rad, 7, realRadius=False)


class Jrap(Game):
    make_initial_state = lambda self:('white', self.teams,
        [(tuple(random.uniform(-board_rad,board_rad) for _ in range(2)), p) for _ in range(num_cells//len(self.teams)) for p in self.teams],
        # [((lambda r, theta: (r*math.cos(theta), r*math.sin(theta)))(random.uniform(0,board_rad), random.uniform(0, 2*math.pi)),p) for _ in range(num_cells) for p in self.teams],
        []
        )

    possible_teams = ['white', 'blue', 'silver', 'lightblue']

    def __init__(self, teams=2, **kwargs):
        teams = int(teams)
        if teams > len(self.possible_teams):
            print('{} is too many teams (max {}); defaulting to 2'.format(teams, len(self.possible_teams)), flush=True)
            teams = 2

        self.teams = self.possible_teams[:teams]
        self.prev_turn = lambda: {self.teams[i]:self.teams[i-1] for i in range(len(self.teams))}[self.turn]

        super().__init__(backgroundColor=Colors.background, spread=board_rad, **kwargs, name='continuous penguin jrap')

        self.save_state = lambda: (self.turn, self.teams, [(p.coords, self.voronoi.player[p]) for p in self.voronoi.player], [[x.coords for x in h.hits] for h in self.layers[Layers.holes]])
        self.load_state = lambda x:(lambda player, teams, cells, holes: (
            self.clearCache(),
            setattr(self, 'turn', player),
            setattr(self, 'teams', teams),
            self.voronoi.reset([(Point(*p), c) for p,c in cells]),
            self.clearLayer(Layers.holes),
            [JrapHole(self, Layers.holes, [Point(*x) for x in h]) for h in holes],
            setattr(self, 'valid_move', False),
            setattr(self, 'open_cells', self.get_open_cells()),
            setattr(self, 'swimming', any(Point(0,0) in h for h in self.layers[Layers.holes])),
            self.updateMove(self.mousePos())
            ))(*x)


        self.hammer = Disk(self, Layers.hammer, None, None, hammer_rad)
        self.hammer.GETvisible = lambda g: bool(g.mousePos())
        self.hammer.GETloc = lambda g: g.mousePos()
        self.hammer.GETcolor = lambda g: Colors.hammer[g.turn]

        self.hammer_border = Circle(self, Layers.hammer_border, None, None, hammer_rad)
        self.hammer_border.GETvisible = lambda g: g.hammer.visible
        self.hammer_border.GETloc = lambda g: g.hammer.loc
        self.hammer_border.GETcolor = lambda g: Colors.legal if g.valid_move else Colors.illegal

        self.new_hole = JrapHole(self, Layers.new_hole, [])
        self.new_hole.GETcolor = lambda g: Colors.ghost_hole[g.turn]

        self.voronoi = JrapVoronoi(self, Layers.voronoi)

        self.penguin = JrapPenguin(self)

        self.warning = Disk(self, Layers.warning, Colors.illegal, Point(0,0), 34, realRadius=False)
        self.warning.GETvisible = lambda g: Point(0,0) in self.new_hole

        Circle(self, Layers.boundary, None, Point(0,0), board_rad).GETcolor = lambda g: Colors.boundary if g.mousePos() and on_board(g.mousePos()) else Colors.illegal

        self.is_over = lambda _=None: self.swimming or self.open_cells[self.turn]==[]
        self.winner = lambda: self.turn if self.swimming else self.prev_turn()

        self.gameOverMessage = FixedText(self, Layers.game_over, Colors.text, self.font, "", 0,0, hborder='c',vborder='c')
        self.gameOverMessage.GETtext = lambda g: "{} sent the penguin swimming. :(".format(self.prev_turn()) if self.swimming else "{} has no moves. :(".format(self.turn)
        self.gameOverMessage.GETvisible = self.is_over

        if 0:
            self.debugger = JrapDebugger(self, Layers.debug)

        self.click[1] = lambda _: self.attemptMove({"player":self.turn, "location":self.mousePos().coords})

        self.reset_state()

        self.process = lambda: self.updateMove(self.mousePos())
        self.viewChange = lambda: self.clearCache()



    get_open_cells = lambda self: {t: [cell for cell in self.voronoi.player if self.voronoi.player[cell]==t and not any(h.contains_cell(cell) for h in self.layers[Layers.holes])] for t in self.teams}


    def attemptGameMove(self, move):
        if self.turn != move["player"]: return False
        pos = Point(*move["location"])
        self.updateMove(pos)
        if not self.valid_move: return
        self.record_state()
        for h in self.to_remove:
            self.layers[Layers.holes].remove(h)
        new = JrapHole(self, Layers.holes, self.new_hole.hits)
        self.open_cells = self.get_open_cells()
        if Point(0,0) in new:
            self.swimming = True
        return True


    def updateMove(self, pos):
        if pos:
            self.new_hole.update([pos])
            holes = self.layers[Layers.holes].copy()
            self.to_remove = []
            while any(self.new_hole.intersecting(h) for h in holes):
                hole = next(h for h in holes if self.new_hole.intersecting(h))
                self.new_hole.merge(hole)
                holes.remove(hole)
                self.to_remove.append(hole)
            self.valid_move = (not self.swimming
                        and on_board(pos) 
                        and self.voronoi.player[self.voronoi.diagram.nearest(pos)] == self.turn
                        and not any(pos in h for h in self.layers[Layers.holes])
                        )

    def resize(self):
        self.voronoi.mask = pygame.Surface(self.size()).convert_alpha(self.screen)
        self.voronoi.scratch = pygame.Surface(self.size()).convert_alpha(self.voronoi.mask)



if __name__=="__main__":
    pygame.init()
    run_local(Jrap, sys.argv[1:])
