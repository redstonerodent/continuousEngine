from continuousEngine import *
from geometry import *
import random
import math

hammer_rad = .5
board_rad = 5
num_cells = 40

# is point p on the board?
on_board = lambda p: +p < board_rad**2

class Colors:
    hole = (0,0,150)
    debug = [(255,0,0),(0,255,0),(0,0,255),(0,0,0),(255,255,255)]
    hammer = {'white':(200,200,255), 'blue':(0,100,255)}
    ghost_hole = {'white':(0,125,125), 'blue': (25,25,125)}
    boundary = (120,120,120)
    legal = (0,255,0)
    illegal = (255,0,0)
    ice = {'white':(0,255,255), 'blue':(0,0,255)}
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
        print(circle_ints)
        self.intervals = poly_ints+circle_ints


    def render(self):
        for h in self.hits:
            drawCircle(self.game, self.color, h, hammer_rad)
        drawPolygon(self.game, self.color, self.poly)
        if 1:
            for h in self.hits:
                drawCircle(self.game, Colors.debug[0], h, hammer_rad, width=2)
            drawPolygon(self.game, Colors.debug[0], self.poly, width=2)
            for a,b in filter(lambda x:x, ((intersect_circles(Point(0,0), p, board_rad, hammer_rad)) for p in self.hits)):
                drawCircle(self.game, Colors.debug[3], a, 5, fixedRadius=True)
                drawCircle(self.game, Colors.debug[4], b, 5, fixedRadius=True)


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
            self.mask.fill((0,0,0,0))
            self.scratch.fill((0,0,0,0))
            drawCircle(self.game, (255,255,255, Colors.voronoi_opacity), Point(0,0), board_rad, surface=self.mask)
            for p in self.player:
                drawPolygon(self.game, Colors.ice[self.player[p]], self.diagram.voronoi_vertices[p], surface=self.scratch)
            self.mask.blit(self.scratch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            return self.mask
        super().__init__(game, layer, 'voronoi', gen)
        self.mask = pygame.Surface(self.game.size).convert_alpha(self.game.screen)
        self.scratch = pygame.Surface(self.game.size).convert_alpha(self.mask)
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


class JrapPenguin(CachedImg):
    def __init__(self, game):
        # penguin icon from Freepik
        super().__init__(game, Layers.penguin, 'penguin', lambda _: pygame.image.load('Sprites/penguin.png').convert_alpha(game.screen), loc=Point(0,0))

class JrapDebugger(Renderable):
    def render(self):
        for p in self.game.voronoi.player:
            drawCircle(self.game, Colors.debug[int(self.game.new_hole.contains_cell(p))], p, 3, fixedRadius=True)
        if self.game.mousePos():
            for p in self.game.voronoi.board_pts[self.game.voronoi.diagram.nearest(self.game.mousePos())]:
                drawCircle(self.game, Colors.debug[(p in self.game.new_hole)+1], p, 3, fixedRadius=True)

class Jrap(Game):
    make_initial_state = lambda self:('white',
        [(tuple(random.uniform(-board_rad,board_rad) for _ in range(2)), p) for _ in range(num_cells) for p in self.teams],
        # [((lambda r, theta: (r*math.cos(theta), r*math.sin(theta)))(random.uniform(0,board_rad), random.uniform(0, 2*math.pi)),p) for _ in range(num_cells) for p in self.teams],
        []
        )

    teams = ['white', 'blue']
    inc_turn = {'white':'blue','blue':'white'}


    def __init__(self, **kwargs):
        super().__init__(backgroundColor=Colors.background, **kwargs)

        self.save_state = lambda: (self.turn, [(p.coords, self.voronoi.player[p]) for p in self.voronoi.player], [h.hits for h in self.layers[Layers.holes]])
        self.load_state = lambda x:(lambda player, cells, holes: (
            self.clearCache(),
            setattr(self, 'turn', player),
            print(self.turn),
            self.voronoi.reset([(Point(*p), c) for p,c in cells]),
            self.clearLayer(Layers.holes),
            [JrapHole(self, Layers.holes, h) for h in holes],
            setattr(self, 'valid_move', False),
            setattr(self, 'over', any(Point(0,0) in h for h in self.layers[Layers.holes])),
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

        self.warning = Disk(self, Layers.warning, Colors.illegal, Point(0,0), 34, fixedRadius=True)
        self.warning.GETvisible = lambda g: Point(0,0) in self.new_hole

        Circle(self, Layers.boundary, None, Point(0,0), board_rad).GETcolor = lambda g: Colors.boundary if g.mousePos() and on_board(g.mousePos()) else Colors.illegal

        font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)
        self.gameOverMessage = FixedText(self, Layers.game_over, Colors.text, font, "", self.width//2, self.height//2)
        self.gameOverMessage.GETtext = lambda g: "{} sent the penguin swimming. :(".format(self.inc_turn[self.turn])
        self.gameOverMessage.GETvisible = lambda g: g.over

        self.debugger = JrapDebugger(self, Layers.debug)

        self.keys.skipTurn = pygame.K_u

        self.keyPress[self.keys.skipTurn] = lambda _: setattr(self, 'turn', self.inc_turn[self.turn])

        self.click[1] = lambda _: self.attemptMove({"player":self.turn, "location":self.mousePos().coords})

        self.reset_state()

        self.process = lambda: self.updateMove(self.mousePos())
        self.viewChange = lambda: self.clearCache()



    def attemptMove(self, move):
        print(move, flush=True)
        if self.turn != move["player"]: return False
        pos = Point(*move["location"])
        self.updateMove(pos)
        if not self.valid_move: return
        self.record_state()
        if Point(0,0) in JrapHole(self, Layers.holes, self.new_hole.hits):
            self.over = True
        for h in self.to_remove:
            self.layers[Layers.holes].remove(h)
        self.turn = self.inc_turn[self.turn]


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
            self.valid_move = (not self.over
                        and on_board(pos) 
                        and self.voronoi.player[self.voronoi.diagram.nearest(pos)] == self.turn
                        and not any(pos in h for h in self.layers[Layers.holes])
                        )


if __name__=="__main__":
    run_local(Jrap)