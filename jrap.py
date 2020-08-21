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
        for p in game.voronoi.player:
            drawCircle(self.game, Colors.debug[int(game.new_hole.contains_cell(p))], p, 3, fixedRadius=True)
        if game.mousePos():
            for p in game.voronoi.board_pts[game.voronoi.diagram.nearest(game.mousePos())]:
                drawCircle(self.game, Colors.debug[(p in game.new_hole)+1], p, 3, fixedRadius=True)


players = ['white', 'blue']
inc_turn = {'white':'blue','blue':'white'}

start_state = ('white',
    [(tuple(random.uniform(-board_rad,board_rad) for _ in range(2)), p) for _ in range(num_cells) for p in players],
    # [((lambda r, theta: (r*math.cos(theta), r*math.sin(theta)))(random.uniform(0,board_rad), random.uniform(0, 2*math.pi)),p) for _ in range(num_cells) for p in players],
    []
    )

game = Game(start_state, backgroundColor=Colors.background)

game.save_state = lambda: (game.turn, [(p.coords, game.voronoi.player[p]) for p in game.voronoi.player], [h.hits for h in game.layers[Layers.holes]])
game.load_state = lambda x:(lambda player, cells, holes: (
    game.clearCache(),
    setattr(game, 'turn', player),
    game.voronoi.reset([(Point(*p), c) for p,c in cells]),
    game.clearLayer(Layers.holes),
    [JrapHole(game, Layers.holes, h) for h in holes],
    setattr(game, 'valid_move', False),
    setattr(game, 'over', any(Point(0,0) in h for h in game.layers[Layers.holes])),
    updateMove(game.mousePos())
    ))(*x)

game.hammer = Disk(game, Layers.hammer, None, None, hammer_rad)
game.hammer.GETvisible = lambda g: bool(g.mousePos())
game.hammer.GETloc = lambda g: g.mousePos()
game.hammer.GETcolor = lambda g: Colors.hammer[g.turn]

game.hammer_border = Circle(game, Layers.hammer_border, None, None, hammer_rad)
game.hammer_border.GETvisible = lambda g: g.hammer.visible
game.hammer_border.GETloc = lambda g: g.hammer.loc
game.hammer_border.GETcolor = lambda g: Colors.legal if g.valid_move else Colors.illegal

game.new_hole = JrapHole(game, Layers.new_hole, [])
game.new_hole.GETcolor = lambda g: Colors.ghost_hole[g.turn]

game.voronoi = JrapVoronoi(game, Layers.voronoi)

game.penguin = JrapPenguin(game)

game.warning = Disk(game, Layers.warning, Colors.illegal, Point(0,0), 34, fixedRadius=True)
game.warning.GETvisible = lambda g: Point(0,0) in game.new_hole

Circle(game, Layers.boundary, None, Point(0,0), board_rad).GETcolor = lambda g: Colors.boundary if g.mousePos() and on_board(g.mousePos()) else Colors.illegal

font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)
gameOverMessage = FixedText(game, Layers.game_over, Colors.text, font, "", game.width//2, game.height//2)
gameOverMessage.GETtext = lambda g: "{} sent the penguin swimming. :(".format(inc_turn[game.turn])
gameOverMessage.GETvisible = lambda g: g.over

game.debugger = JrapDebugger(game, Layers.debug)

def attemptMove(pos):
    updateMove(pos)
    if not game.valid_move: return
    game.record_state()
    if Point(0,0) in JrapHole(game, Layers.holes, game.new_hole.hits):
        game.over = True
    for h in game.to_remove:
        game.layers[Layers.holes].remove(h)
    game.turn = inc_turn[game.turn]


def updateMove(pos):
    if pos:
        game.new_hole.update([pos])
        holes = game.layers[Layers.holes].copy()
        game.to_remove = []
        while any(game.new_hole.intersecting(h) for h in holes):
            hole = next(h for h in holes if game.new_hole.intersecting(h))
            game.new_hole.merge(hole)
            holes.remove(hole)
            game.to_remove.append(hole)
        game.valid_move = (not game.over
                    and on_board(pos) 
                    and game.voronoi.player[game.voronoi.diagram.nearest(pos)] == game.turn
                    and not any(pos in h for h in game.layers[Layers.holes])
                    )

game.keys.skipTurn = pygame.K_u

game.keyPress[game.keys.skipTurn] = lambda _: setattr(game, 'turn', inc_turn[game.turn])


game.process = lambda: updateMove(game.mousePos())
game.click[1] = lambda _: attemptMove(game.mousePos())
game.viewChange = lambda: game.clearCache()


game.load_state(start_state)

while 1:
    game.update()