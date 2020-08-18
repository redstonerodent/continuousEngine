from continuousEngine import *
from geometry import *
import random
from math import pi

piece_rad = 1

board_rad = 10

## HELPER FUNCTIONS FOR GEOMETRY
## points are the Point class from geometry

# is this piece within the (circular) board?
on_board = lambda p: +p < (board_rad - piece_rad)**2
# is this point on the board?
on_board_pt = lambda p: +p < board_rad**2
# which pieces (among xs) are close enough to p1 and p2 to possibly get in the way?
# those which intersect a circle at the same distance as p1 from p2; i.e. within max_dist_sq**.5 of p2 (and symmetrically of p1)
chokepoints = lambda p1, p2, xs: (lambda max_dist_sq:{x for x in xs if p1>>x < max_dist_sq and p2>>x < max_dist_sq})(((p1>>p2)**0.5 + 2*piece_rad)**2)
# separate chokepoints into those above and below the line; gives tuple of sets (above line, below line)
split_chokepoints = lambda p1, p2, xs: (lambda cps: ({x for x in cps if above_line(p1,p2,x)},{x for x in cps if not above_line(p1,p2,x)}))(chokepoints(p1,p2,xs))
# can you locally slide from p1 to p2, without touching pieces at xs?
# assumes p1 and p2 are nearby (within 4r)
# this fails if there's a pair of chokepoints within 4r and between p1 and p2, in the sense that p1 and p2 are on opposite sides of the line
#   or if there's a chokepoint within 3r of the boundary that blocks movement
connected = lambda p1, p2, xs: (lambda tops, bots: not any(nearby(top,bot) and intersect_segments(p1,p2,top,bot) for top in tops for bot in bots)
                                                    and not any(intersect_segments(p1,p2,*cut) for cut in boundary_cuts(tops|bots)))(*split_chokepoints(p1,p2,xs))
# given {p} pieces, give {(p1,p2)} of pairs of points within 4r
weak_edges = lambda pieces: {(p1,p2) for p1 in pieces for p2 in pieces if p1 != p2 and nearby(p1,p2)}
# given [p] pieces, give {(p1,b)} of lines to the boundary which might prevent movement (i.e. less than 3r)
# it's fine for the line to extend past the boundary -- we double the coordinates for simplicity; this only works because board_rad is enough bigger than piece_rad
boundary_cuts = lambda pieces: {(p, 2*p) for p in pieces if +p > (board_rad-3*piece_rad)**2}
# given {(p,p)} edges and {(p,p)} cuts, gives the set of edges which don't cross a cut
filter_edges = lambda edges, cuts: {edge for edge in edges if not any(intersect_segments(*edge, *cut) for cut in cuts)}
# union: expects an iterator of sets
union = lambda ss: (lambda s: set() if s is None else s | union(ss))(next(ss,None))
# given {p} vertices and [(p1,p2)] edges, give the partition of vertices into connected components [{p}]
# requires edges to be a list
components = lambda vertices, edges, cmps=None: components(vertices, edges, [{p} for p in vertices]) if cmps==None else \
    (lambda e: components(vertices, edges[1:], [s for s in cmps if not s&e]+[union(s for s in cmps if s&e)]))(set(edges[0])) if edges else cmps
# do pieces centered at p1 and p2 overlap?
overlap = lambda p1, p2: p1>>p2 < (2*piece_rad)**2
# are pieces centered at p1 p2 close enough to block movement between them?
nearby = lambda p1, p2: p1>>p2 < (4*piece_rad)**2
# are pieces centered at p1 p2 close enough that they might block each others' movement?
sorta_nearby = lambda p1, p2: p1>>p2 < (6*piece_rad)**2
# centers of circles tangent to both circles centered at p1 and p2
double_tangents = lambda p1, p2: intersect_circles(p1, p2, 2*piece_rad)

teams = ['WHITE', 'BLACK']
inc_turn = {'WHITE':'BLACK', 'BLACK':'WHITE'}

class Layers:
    TERRITORY   = 0.5
    BOUNDARY    = 1
    GUIDES      = 1.5
    PIECES      = {'WHITE':2, 'BLACK':2.1, 'GHOST':2.2, 'NEW':5}
    COUNT       = 10
    DEBUG       = 20

class Colors:
    fill        = {'WHITE': (205,205,205), 'BLACK': (50, 50, 50 )}
    guide       = {'WHITE': (225,225,225), 'BLACK': (30, 30, 30 )}
    border      = {'WHITE': (80, 80, 80 ), 'BLACK': (160,160,160)}
    newfill     = {'WHITE': (255,255,255), 'BLACK': (0,0,0)}
    legal       = (0,255,0)
    blocker     = (255,0,0)
    capture     = (0,180,255)
    background  = (212,154,61)
    text        = {'WHITE': (255,255,255), 'BLACK': (0,0,0), 'GAMEOVER': (230,20,128)}
    boundary    = (0,0,0)
    debug       = [(255,0,0),(0,255,0),(0,0,255)]
    ghost       = (128,128,128)
    territory   = {'WHITE': (222,174,81), 'BLACK': (192,134,41)}

font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)

class GoPiece(BorderDisk):
    def __init__(self, game, team, loc):
        super().__init__(game, Layers.PIECES[team], None, None, loc, piece_rad)
        self.team = team
        self.GETfill_color = lambda g: Colors.fill[self.team]
        self.GETborder_color = lambda g: Colors.blocker if self in g.blockers else Colors.capture if self.loc in g.captures else Colors.border[self.team]
        self.guide = GoPieceGuide(self)

class GoPieceGuide(Circle):
    def __init__(self, piece):
        super().__init__(piece.game, Layers.GUIDES, None, None, 2*piece_rad)
        self.piece = piece
        self.GETloc = lambda _: self.piece.loc
        self.GETcolor = lambda _: Colors.guide[self.piece.team]
        self.visible = False

class GoVoronoi(CachedImg):
    def __init__(self, game, layer):
        def gen(_):
            self.mask.fill((0,0,0,0))
            self.scratch.fill((0,0,0,0))
            drawCircle(self.game, (255,255,255), Point(0,0), board_rad, surface=self.mask)
            for t in teams:
                  for p in game.layers[Layers.PIECES[t]]:
                    drawPolygon(self.game, Colors.territory[t], self.diagram.voronoi_vertices[p.loc], surface=self.scratch)
            self.mask.blit(self.scratch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            return self.mask
        super().__init__(game, layer, None, gen)
        self.mask = pygame.Surface(self.game.size).convert_alpha(self.game.screen)
        self.scratch = pygame.Surface(self.game.size).convert_alpha(self.mask)


class GoDebugger(Renderable):
    render = lambda self: (
        [(lambda col: [self.debugLine(col, *e) for e in self.game.edges[t] if set(e) <= cmp])([random.randint(0,255) for _ in '123']) for t in teams for cmp in self.game.components[t]],
        [self.debugLine(Colors.debug[0], p.loc, lib) for t in teams for p in self.game.layers[Layers.PIECES[t]] for lib in self.game.liberties[p.loc]]
        )

start_state = ('WHITE', {t:0 for t in teams}, {t:set() for t in teams})

game = Game(
    initialState=start_state,
    backgroundColor=Colors.background,
    scale=50
)

game.save_state = lambda: (game.turn, game.capturedCount.copy(), {team:[p.loc.coords for p in game.layers[Layers.PIECES[team]]] for team in teams})
game.load_state = lambda x: (lambda turn, capCount, pieces: (
    game.clearLayer(Layers.GUIDES),
    game.add(game.nextPiece.guide, Layers.GUIDES),
    setattr(game.nextPiece.guide, 'visible', False),
    setattr(game.voronoi, 'diagram', Voronoi((-board_rad, -board_rad), (board_rad, board_rad))),
    [game.clearLayer(Layers.PIECES[team]) for team in teams+['GHOST']],
    [game.makePiece(team, Point(*p)) for team in teams for p in pieces[team]],
    setattr(game, 'turn', turn),
    setattr(game, 'capturedCount', capCount.copy()),
    setattr(game, 'guides', set()),
    updateLiberties(game),
    updateGraph(game),
    updateTerritory(game),
    game.clearCache()
    ))(*x)

Circle(game, Layers.BOUNDARY, None, Point(0,0), board_rad).GETcolor = lambda g: Colors.boundary if game.rawMousePos == None or on_board(game.mousePos()) else Colors.blocker

FixedText(game, Layers.COUNT, Colors.text['BLACK'], font, None, game.width-30,30, *'rt').GETtext = lambda g: '{} + {:4.1f} = {:5.1f}'.format(g.capturedCount['WHITE'], g.territory['BLACK'], g.capturedCount['WHITE'] + g.territory['BLACK'])
FixedText(game, Layers.COUNT, Colors.text['WHITE'], font, None, game.width-30,60, *'rt').GETtext = lambda g: '{} + {:4.1f} = {:5.1f}'.format(g.capturedCount['BLACK'], g.territory['WHITE'], g.capturedCount['BLACK'] + g.territory['WHITE'])
game.debugger = GoDebugger(game, Layers.DEBUG)
game.debugger.visible = False

# debug
game.edges = {t:set() for t in teams}
game.components = {t:[] for t in teams}
game.captures = set()

# make a piece on team t at (x,y)
game.makePiece = lambda t,p: (GoPiece(game, t, p), game.voronoi.diagram.add(p))

# remove pieces at {(x,y)} ps
game.removePieces = lambda ps: (lambda pcs: [(
    game.layers[Layers.PIECES[pc.team]].remove(pc), game.layers[Layers.GUIDES].remove(pc.guide),
    game.capturedCount.__setitem__(pc.team, game.capturedCount[pc.team]+1),
    game.voronoi.diagram.remove(pc.loc)
    ) for pc in pcs
    ])([pc for t in teams for pc in game.layers[Layers.PIECES[t]] if pc.loc in ps])

game.nextPiece = GoPiece(game, 'NEW', None)
game.nextPiece.GETteam = lambda g: g.turn
game.nextPiece.GETvisible = lambda g: g.mousePos()
game.nextPiece.GETloc = lambda g: g.mousePos()
game.nextPiece.GETborder_color = lambda g: Colors.blocker if g.blockers or not on_board(game.mousePos()) else Colors.capture if game.mousePos() in game.captures else Colors.legal
game.nextPiece.GETfill_color = lambda g: Colors.newfill[g.turn]

game.voronoi = GoVoronoi(game, Layers.TERRITORY)
game.viewChange = lambda: game.clearCache()

def attemptMove(_):
    updateMove(game)
    if game.blockers or not on_board(game.mousePos()): return
    game.record_state()
    game.makePiece(game.turn, game.mousePos())
    game.removePieces(game.captures)
    game.turn = inc_turn[game.turn]
    [setattr(p.guide, 'visible', False) for t in teams for p in game.layers[Layers.PIECES[t]]]
    game.nextPiece.guide.visible = False
    game.clearLayer(Layers.PIECES['GHOST'])
    updateLiberties(game)
    updateGraph(game)
    updateTerritory(game)
    game.clearCache()

updateLiberties = lambda game: setattr(game, 'liberties', {pc.loc: (lambda close_pcs, close_opps: {tan for pc2 in close_pcs for tan in double_tangents(pc.loc, pc2) if on_board(tan) and not any(overlap(tan, p) for p in close_pcs) and connected(pc.loc, tan, close_opps)})([pc2.loc for t2 in teams for pc2 in game.layers[Layers.PIECES[t2]] if pc2 != pc and sorta_nearby(pc2.loc,pc.loc)], [pc2.loc for pc2 in game.layers[Layers.PIECES[inc_turn[t]]] if sorta_nearby(pc2.loc, pc.loc)]) for t in teams for pc in game.layers[Layers.PIECES[t]]})

def updateMove(game):
    pos = game.mousePos()
    if pos and on_board(pos):
        game.blockers = {p for p in sum((game.layers[Layers.PIECES[team]] for team in teams+['GHOST']),[]) if overlap(pos, p.loc)}

        opp = inc_turn[game.turn]
        pieces = {t:{p.loc for p in game.layers[Layers.PIECES[t]]} for t in teams}
        new_pc_w_es = {(pos,p) for p in pieces[game.turn] if nearby(pos,p)}
        pieces[game.turn].add(pos)
        all_pieces = union(iter(pieces.values()))

        # THE RULE: a piece is captured if there's no way to slide it continuously without bumping into opponent's pieces to an empty space
        # a 'liberty' is a location tangent to a piece which it can slide to, preventing capture
        # connected components of pieces that can slide to each others' locations are always captured together
        # when you place a piece, first any opponent's pieces are captured, and then your own
        # you're allowed to place a piece that gets immediately captured; this can even be useful because it might capture opponent's pieces first

        # figure out what we'll capture, starting with the opponent's pieces

        # graph of opponent's pieces accounting for new piece
        opp_edges = filter_edges(game.edges[opp], new_pc_w_es | boundary_cuts({pos}))

        # the pieces in the opponent's components we might capture (i.e. those with a piece within 6r), in components according to the new graph
        opp_cmps = components(union(cmp for cmp in game.components[opp] if any(sorta_nearby(pos, p) for p in cmp)), list(opp_edges))
        
        # an opponent's component is captured if...
        game.captures = union(cmp for cmp in opp_cmps if
                                # it's not an isolated piece with nothing nearby...
                                any(nearby(p, other) for p in cmp for other in all_pieces if p != other)
                                # and the new piece overlaps or blocks all the component's liberties...
                                and all(overlap(pos, lib) or not connected(p, lib, pieces[game.turn]) for p in cmp for lib in game.liberties[p])
                                # and none of the tangencies with the new piece are new liberties
                                and not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pc, tan, pieces[game.turn]) for pc in cmp for tan in double_tangents(pos,pc)))

        # after any opponent pieces are captured...
        pieces[opp] -= game.captures
        all_pieces = union(iter(pieces.values()))

        # we figure out which of our pieces get captured
        # some new edges are introduced, in two ways:
        # 1. edges with the new piece
        new_edges = filter_edges(new_pc_w_es, (lambda close_pcs: weak_edges(close_pcs) | boundary_cuts(close_pcs))({p for p in pieces[opp] if sorta_nearby(p, pos)}))
        # 2. edges which are de-broken by pieces being captured
        near_capture = {p for p in pieces[game.turn] if any(nearby(p,cap) for cap in game.captures)}
        new_edges |= filter_edges({e for e in game.potentialEdges[game.turn] if set(e)<=near_capture}, {e for e in game.potentialEdges[opp] if game.captures.isdisjoint(e)} | boundary_cuts(pieces[opp]))
        # some components are merged by the new edges
        my_cmps = components(None, list(new_edges), game.components[game.turn]+[{pos}])
        
        # one of our components is captured if...
        game.captures |= union(cmp for cmp in my_cmps if
                                # it's not an isolated piece with nothing nearby...
                                any(nearby(p, other) for p in cmp for other in all_pieces if p != other)
                                # and the new piece overlaps all the component's liberties (it can't block movement because it's on the same team)...
                                and all(overlap(pos, lib) for p in cmp-{pos} for lib in game.liberties[p])
                                # and none of the tangencies with the new piece are new liberties for an existing piece...
                                and not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pc, tan, pieces[opp]) for pc in cmp for tan in double_tangents(pos,pc))
                                # and, if this is the component of the new piece, none of its tangencies with any piece are new liberties
                                and (pos not in cmp or not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pos, tan, pieces[opp]) for pc in all_pieces for tan in double_tangents(pos,pc))))

    else: 
        game.blockers = set()
        game.captures = set()

def updateGraph(game):
    pieces = {t:[p.loc for p in game.layers[Layers.PIECES[t]]] for t in teams}
    w_es = {t:weak_edges(pieces[t]) for t in teams}
    game.edges = {t:filter_edges(w_es[t], w_es[inc_turn[t]] | boundary_cuts(pieces[inc_turn[t]])) for t in teams}
    game.potentialEdges = {t:w_es[t]-game.edges[t] for t in teams}
    game.components = {t:components(pieces[t], list(game.edges[t])) for t in teams}

def updateTerritory(game):
    game.territory = {t:sum(intersect_polygon_circle_area(game.voronoi.diagram.voronoi_vertices[pc.loc], Point(0,0), board_rad) for pc in game.layers[Layers.PIECES[t]]) / pi * piece_rad**2 for t in teams}

piece_at = lambda pos, game: (lambda ps: ps[0] if ps else game.nextPiece)([p for t in teams for p in game.layers[Layers.PIECES[t]] if pos>>p.loc < piece_rad**2])

game.process = lambda: updateMove(game)

game.load_state(start_state)

# left click: place piece
game.click[1] = attemptMove
# middle click: toggle guide
game.click[2] = lambda e: (lambda g: setattr(g, 'visible', not g.visible))(piece_at(game.point(*e.pos), game).guide)

game.keys.skipTurn = pygame.K_u
game.keys.placeGhost = pygame.K_SPACE
game.keys.clearGuides = pygame.K_ESCAPE

game.keyPress[game.keys.skipTurn] = lambda _: setattr(game, 'turn', inc_turn[game.turn])
game.keyPress[game.keys.placeGhost] = lambda _: None if game.blockers or not on_board(game.mousePos()) else (lambda ghost: setattr(ghost, 'GETcolor', lambda g: Colors.blocker if ghost in g.blockers else Colors.ghost))(Circle(game, Layers.PIECES['GHOST'], Colors.ghost, game.mousePos(), piece_rad))
game.keyPress[game.keys.clearGuides] = lambda _: ([setattr(p.guide, 'visible', False) for t in teams for p in game.layers[Layers.PIECES[t]]],
                                                    setattr(game.nextPiece.guide, 'visible', False),
                                                    game.clearLayer(Layers.PIECES['GHOST']))

# debug tools
testGames = [
    ('BLACK', {'WHITE': 1, 'BLACK': 1}, {'WHITE': [(-7.220000000000001, 1.8399999999999999), (-6.2, 1.8599999999999994), (-4.849600000000001, 1.9071999999999996), (-3.838400000000001, 1.9328000000000003), (-2.5456000000000003, 1.984), (-1.5088000000000008, 1.984), (-0.1264000000000003, 2.0096), (0.9359999999999999, 1.9967999999999995), (2.3568000000000007, 2.0736000000000017), (3.4064000000000014, 2.150400000000001), (4.865600000000001, 2.1888000000000014), (5.876800000000001, 2.1888000000000014), (7.361600000000001, 2.201600000000001), (8.372800000000002, 2.2272000000000016), (7.3488000000000016, 0.08960000000000701), (8.411200000000001, 0.07680000000000664), (5.812800000000001, -0.06399999999999295), (4.776000000000002, 0.06400000000000716), (3.432000000000001, 0.06400000000000716), (2.420800000000001, 0.03840000000000732), (0.9513600000000011, -0.0844799999999939), (-0.062399999999999345, -0.09471999999999348), (-1.4038400000000024, -0.06399999999999917), (-2.438080000000003, -0.08447999999999878), (-3.810240000000003, -0.0742399999999992), (-4.813760000000003, -0.14591999999999894), (-6.1756800000000025, -0.17663999999999902), (-7.209920000000003, -0.2073599999999991), (-4.057120000000004, -7.641664000000003), (-3.071520000000004, -6.540864000000004), (-1.9451200000000037, -7.552064000000003), (-0.9467200000000044, -6.464064000000003), (0.11567999999999579, -7.526464000000003), (1.1652799999999957, -6.348864000000003), (2.1892799999999966, -7.372864000000003), (3.3028799999999983, -6.208064000000003), (4.262879999999997, -7.321664000000003), (5.402079999999998, -6.092864000000003), (-5.202520000000005, -6.606264000000012), (-6.758700000000008, 6.589665999999985), (-6.789420000000008, 5.565665999999985), (-5.888300000000008, 6.067425999999985), (-5.908780000000008, 5.012705999999985), (-4.997420000000008, 5.534945999999985), (-5.867820000000008, 7.070945999999985), (-4.966700000000008, 6.589665999999985), (-5.017900000000008, 7.603425999999985), (-6.820140000000008, 4.510945999999985), (-5.888300000000008, 3.927265999999985), (-4.976940000000008, 4.510945999999985), (-4.895020000000008, 3.476705999999985), (-4.034860000000008, 4.121825999999985), (-4.034860000000008, 5.135585999999985), (-4.024620000000008, 6.159585999999985), (-4.034860000000008, 7.183585999999985), (-3.1132600000000084, 6.6715859999999845), (-3.1337400000000075, 5.575905999999985), (-3.0927800000000083, 4.562145999999985), (-7.528716000000008, -2.784670000000016), (-6.2287160000000075, -4.344670000000017), (-3.128716000000008, -2.6846700000000165), (-0.2687160000000084, -3.964670000000017), (2.5712839999999932, -2.8246700000000162), (5.131283999999992, -3.744670000000016), (7.851283999999991, -3.464670000000017), (5.751283999999993, -2.3846700000000167), (-1.3487160000000085, -2.3846700000000167), (-8.388716000000008, -2.2646700000000166), (2.491283999999993, -1.7446700000000162), (-2.9687160000000077, -4.584670000000016), (-9.168716000000007, -1.4246700000000168), (4.311283999999993, 7.095329999999985), (7.2312839999999925, 4.875329999999984), (5.591283999999992, 7.195329999999984), (-2.0287160000000077, 9.115329999999984), (-1.5287160000000077, 7.815329999999985), (-3.588716000000008, 8.195329999999984), (-1.208716000000008, 3.995329999999985), (-0.08871600000000779, 3.5953299999999846), (4.911283999999992, 4.875329999999984), (8.871283999999992, 3.1953299999999842)], 'BLACK': [(-5.489599999999998, 0.9216000000000042), (-6.705599999999998, 0.8576000000000041), (-4.3375999999999975, 0.8960000000000035), (-3.147199999999998, 0.9984000000000046), (-1.9696000000000007, 0.947200000000004), (-0.8048000000000011, 1.1008000000000049), (0.3216000000000001, 0.9856000000000043), (1.7552000000000003, 1.0496000000000052), (2.984, 1.1648000000000058), (4.1616, 1.1904000000000048), (5.300800000000001, 1.1264000000000047), (6.683200000000001, 1.2800000000000074), (7.873600000000001, 1.2544000000000066), (6.670400000000001, -0.6783999999999937), (1.760320000000001, -0.7295999999999943), (4.064320000000002, -0.7603199999999957), (6.593600000000002, 2.9670400000000043), (4.0336000000000025, 2.9875200000000044), (1.5862400000000023, 2.8953600000000046), (-0.8099199999999991, 2.7929600000000026), (-3.2470399999999993, 2.7417600000000024), (-5.56128, 2.711040000000002), (-5.428160000000003, -0.9651199999999989), (-3.1241600000000025, -0.9139199999999992), (-0.7484800000000025, -0.842239999999999), (-4.133920000000004, -6.592064000000003), (-3.0203200000000043, -7.6544640000000035), (-2.009120000000004, -6.464064000000003), (-0.9211200000000037, -7.539264000000003), (0.10287999999999542, -6.4128640000000035), (1.178079999999996, -7.488064000000003), (2.266079999999995, -6.272064000000003), (3.238879999999998, -7.308864000000003), (4.326879999999997, -6.131264000000003), (5.338079999999998, -7.193664000000004), (-5.125720000000005, -7.707064000000012), (-0.39710000000000445, 5.312225999999986), (-0.3843000000000041, 6.323425999999985), (-0.39710000000000445, 7.360225999999986), (0.48251599999999595, 6.853857999999986), (0.5316679999999954, 5.731553999999986), (0.46613199999999555, 4.682977999999986), (0.48251599999999595, 7.869665999999986), (1.3099079999999956, 8.549601999999986), (1.400019999999996, 7.378145999999986), (1.400019999999996, 6.313185999999986), (1.4164039999999956, 5.174497999999986), (1.3672519999999961, 4.125921999999986), (2.3257159999999955, 4.5846739999999855), (2.3748679999999958, 5.772513999999986), (2.3666759999999956, 6.9603539999999855), (2.2929479999999955, 8.090849999999985), (3.259603999999996, 7.591137999999985), (3.2677959999999953, 6.386913999999985), (3.2514119999999957, 5.199073999999985), (-7.568716000000007, -3.9246700000000168), (-6.388716000000008, -3.124670000000016), (-4.488716000000007, -3.584670000000016), (-1.9887160000000073, -4.084670000000016), (1.2312839999999916, -2.8446700000000167), (3.871283999999992, -3.1846700000000165), (6.531283999999994, -3.8646700000000163), (6.911283999999993, -2.5246700000000164), (4.231283999999992, -2.2246700000000166), (-4.748716000000008, -2.3246700000000162), (0.11128399999999239, -2.0246700000000164), (2.1512839999999915, -3.9846700000000164), (-4.688716000000007, -4.784670000000016), (-7.008716000000008, -1.664670000000016), (4.831283999999992, 6.0153299999999845), (6.531283999999991, 5.995329999999985), (5.931283999999992, 4.195329999999984), (-0.42871600000000765, 9.175329999999985), (-1.768716000000008, 6.755329999999985), (-1.6287160000000078, 5.655329999999985), (3.9512839999999914, 4.235329999999985), (8.051283999999992, 3.955329999999984)]})
    ,
    ('BLACK', {'WHITE': 1, 'BLACK': 1}, {'WHITE': [(-3.430099999999997, -6.7109000000000005), (3.3316999999999997, -1.6439000000000092), (6.963699999999999, -1.6599000000000093), (5.1396999999999995, -4.61990000000001), (3.2996999999999996, 0.644099999999991), (5.1236999999999995, 2.1160999999999905), (7.075699999999999, 0.580099999999991), (-1.7483000000000066, 1.7200999999999929), (-2.068300000000007, 5.854499999999993), (0.46609999999999374, 4.024099999999994), (-3.962700000000007, 3.5760999999999927)], 'BLACK': [(-5.426899999999994, -4.12529999999999), (-1.5612999999999975, -4.099700000000001), (-5.593299999999996, -6.480500000000003), (-1.1132999999999953, -6.454900000000003), (-2.226899999999996, -8.554100000000004), (-5.094099999999997, -1.6037), (-1.9452999999999978, -1.5269000000000004), (2.499699999999999, -3.49990000000001), (7.491699999999998, -3.62790000000001), (3.7156999999999982, -6.13990000000001), (5.747699999999998, -6.55590000000001), (-3.924300000000007, 1.5024999999999928), (-4.205900000000007, 5.611299999999993), (-6.151500000000007, 3.371299999999993)]})
    ,
    ('WHITE', {'WHITE': 1, 'BLACK': 0}, {'WHITE': [], 'BLACK': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804), (-0.6803124999999728, -5.4562500000000265)]})
    ,
    ('BLACK', {'WHITE': 0, 'BLACK': 0}, {'WHITE': [(1.3331250000000239, -4.4271875000000165)], 'BLACK': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804)]})
    ,
    ('BLACK', {'BLACK': 1, 'WHITE': 0}, {'WHITE': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804), (-0.6803124999999728, -5.4562500000000265), (-5.1189940000000025, -4.789850000000011), (-0.2439940000000025, 7.160149999999987), (3.781005999999996, 4.085149999999988), (3.031005999999996, 6.335149999999988), (-4.643994000000003, -1.414850000000012), (-7.793994000000002, -2.339850000000011), (-4.068994000000002, 1.1851499999999895), (-3.543994000000003, 7.010149999999989), (-6.2439940000000025, 5.86014999999999), (1.2810059999999979, -4.264850000000012)], 'BLACK': [(-5.7439940000000025, 3.285149999999989), (-0.9439940000000018, 2.285149999999989), (6.781005999999996, -1.4398500000000105), (5.331005999999997, 2.585149999999988), (-1.4439940000000018, 4.285149999999989), (-2.6189940000000025, -7.714850000000011), (-8.418994000000001, 1.8601499999999884), (6.406005999999996, 5.535149999999987), (6.181005999999998, -4.664850000000011), (2.906005999999996, -8.364850000000011), (-2.893994000000003, -3.8148500000000114), (-2.0203334775390793, -0.7476746459961028)]})

]

game.numKey = lambda n: (game.record_state(), game.load_state(testGames[n])) if n<len(testGames) else print(str(n)+' not saved') # load presaved game for debugging

game.keys.printState = pygame.K_RETURN
game.keys.toggleDebug = pygame.K_RSHIFT

game.keyPress[game.keys.printState] = lambda _: print(game.save_state())
game.keyPress[game.keys.toggleDebug] = lambda _: setattr(game.debugger, 'visible', not game.debugger.visible)

while 1: 
    game.update()