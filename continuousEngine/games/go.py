from continuousEngine import *
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

class Layers:
    TERRITORY   = 0.5
    BOUNDARY    = 1
    GUIDES      = 1.5
    PIECES      = {'white':2, 'black':2.1, 'GHOST':2.2, 'NEW':5}
    COUNT       = 10
    DEBUG       = 20

class Colors:
    fill        = {'white': (205,205,205), 'black': (50, 50, 50 )}
    guide       = {'white': (225,225,225), 'black': (30, 30, 30 )}
    border      = {'white': (80, 80, 80 ), 'black': (160,160,160)}
    newfill     = {'white': (255,255,255), 'black': (0,0,0)}
    legal       = (0,255,0)
    blocker     = (255,0,0)
    capture     = (0,180,255)
    background  = (212,154,61)
    text        = {'white': (255,255,255), 'black': (0,0,0), 'GAMEOVER': (230,20,128)}
    boundary    = (0,0,0)
    debug       = [(255,0,0),(0,255,0),(0,0,255)]
    ghost       = (128,128,128)
    territory   = {'white': (222,174,81), 'black': (192,134,41)}

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
            for t in self.game.teams:
                  for p in game.layers[Layers.PIECES[t]]:
                    drawPolygon(self.game, Colors.territory[t], self.diagram.voronoi_vertices[p.loc], surface=self.scratch)
            self.mask.blit(self.scratch, (0,0), special_flags=pygame.BLEND_RGBA_MULT)
            return self.mask
        super().__init__(game, layer, None, gen)

class GoDebugger(Renderable):
    render = lambda self: (
        [(lambda col: [self.debugLine(col, *e) for e in self.game.edges[t] if set(e) <= cmp])([random.randint(0,255) for _ in '123']) for t in self.game.teams for cmp in self.game.components[t]],
        [self.debugLine(Colors.debug[0], p.loc, lib) for t in self.game.teams for p in self.game.layers[Layers.PIECES[t]] for lib in self.game.liberties[p.loc]]
        )

class Go(Game):
    make_initial_state = lambda self: ('black', {t:0 for t in self.teams}, {t:set() for t in self.teams})
    teams = ['black', 'white']

    def __init__(self, **kwargs):
        super().__init__(backgroundColor=Colors.background, spread=board_rad, name='continuous go', **kwargs)


        self.save_state = lambda: (self.turn, self.capturedCount.copy(), {team:[p.loc.coords for p in self.layers[Layers.PIECES[team]]] for team in self.teams})
        self.load_state = lambda x: (lambda turn, capCount, pieces: (
            self.clearLayer(Layers.GUIDES),
            self.add(self.nextPiece.guide, Layers.GUIDES),
            setattr(self.nextPiece.guide, 'visible', False),
            setattr(self.voronoi, 'diagram', Voronoi((-board_rad, -board_rad), (board_rad, board_rad))),
            [self.clearLayer(Layers.PIECES[team]) for team in self.teams+['GHOST']],
            [self.makePiece(team, Point(*p)) for team in self.teams for p in pieces[team]],
            setattr(self, 'turn', turn),
            setattr(self, 'capturedCount', capCount.copy()),
            setattr(self, 'guides', set()),
            self.updateLiberties(),
            self.updateGraph(),
            self.updateTerritory(),
            self.clearCache()
            ))(*x)

        self.next_turn = lambda t=None: {'white':'black', 'black':'white'}[t or self.turn]
        self.allow_skip = True

        Circle(self, Layers.BOUNDARY, None, Point(0,0), board_rad).GETcolor = lambda g: Colors.boundary if self.rawMousePos == None or on_board(self.mousePos()) else Colors.blocker

        FixedText(self, Layers.COUNT, Colors.text['black'], font, None, -30,30, halign='r', valign='t', hborder='r').GETtext = lambda g: '{} + {:4.1f} = {:5.1f}'.format(g.capturedCount['white'], g.territory['black'], g.capturedCount['white'] + g.territory['black'])
        FixedText(self, Layers.COUNT, Colors.text['white'], font, None, -30,60, halign='r', valign='t', hborder='r').GETtext = lambda g: '{} + {:4.1f} = {:5.1f}'.format(g.capturedCount['black'], g.territory['white'], g.capturedCount['black'] + g.territory['white'])
        self.debugger = GoDebugger(self, Layers.DEBUG)
        self.debugger.visible = False

        # debug
        self.edges = {t:set() for t in self.teams}
        self.components = {t:[] for t in self.teams}
        self.captures = set()

        # make a piece on team t at (x,y)
        self.makePiece = lambda t,p: (GoPiece(self, t, p), self.voronoi.diagram.add(p))

        # remove pieces at {(x,y)} ps
        self.removePieces = lambda ps: (lambda pcs: [(
            self.layers[Layers.PIECES[pc.team]].remove(pc), self.layers[Layers.GUIDES].remove(pc.guide),
            self.capturedCount.__setitem__(pc.team, self.capturedCount[pc.team]+1),
            self.voronoi.diagram.remove(pc.loc)
            ) for pc in pcs
            ])([pc for t in self.teams for pc in self.layers[Layers.PIECES[t]] if pc.loc in ps])

        self.nextPiece = GoPiece(self, 'NEW', None)
        self.nextPiece.GETteam = lambda g: g.turn
        self.nextPiece.GETvisible = lambda g: g.mousePos()
        self.nextPiece.GETloc = lambda g: g.mousePos()
        self.nextPiece.GETborder_color = lambda g: Colors.blocker if g.blockers or not on_board(self.mousePos()) else Colors.capture if self.mousePos() in self.captures else Colors.legal
        self.nextPiece.GETfill_color = lambda g: Colors.newfill[g.turn]

        self.voronoi = GoVoronoi(self, Layers.TERRITORY)
        self.viewChange = lambda: self.clearCache()

        self.process = lambda: self.updateMove()

        self.reset_state()

        # left click: place piece
        self.click[1] = lambda _: self.attemptMove({"player":self.turn, "action":"place", "location":self.mousePos().coords})
        # middle click: toggle guide
        self.piece_at = lambda pos: (lambda ps: ps[0] if ps else self.nextPiece)([p for t in self.teams for p in self.layers[Layers.PIECES[t]] if pos>>p.loc < piece_rad**2])
        self.click[2] = lambda e: (lambda g: setattr(g, 'visible', not g.visible))(self.piece_at(self.point(*e.pos)).guide)

        self.keyPress[self.keys.skipTurn] = lambda e: self.attemptMove({"player":self.turn, "action":"skip"})

        self.keyPress[self.keys.placeGhost] = lambda _: None if self.blockers or not on_board(self.mousePos()) else (lambda ghost: setattr(ghost, 'GETcolor', lambda g: Colors.blocker if ghost in g.blockers else Colors.ghost))(Circle(self, Layers.PIECES['GHOST'], Colors.ghost, self.mousePos(), piece_rad))
        self.keyPress[self.keys.clearGuides] = lambda _: ([setattr(p.guide, 'visible', False) for t in self.teams for p in self.layers[Layers.PIECES[t]]],
                                                            setattr(self.nextPiece.guide, 'visible', False),
                                                            self.clearLayer(Layers.PIECES['GHOST']))


    def attemptMove(self, move):
        print(move, flush=True)
        if self.turn != move["player"]: return False
        
        self.record_state()
        self.clearLayer(Layers.PIECES['GHOST'])
        
        if move["action"] == "place":
            pos = Point(*move["location"])
            self.updateMove(pos)
            if self.blockers or not on_board(pos): return
            self.makePiece(self.turn, pos)
            self.removePieces(self.captures)
            self.turn = self.next_turn()
            [setattr(p.guide, 'visible', False) for t in self.teams for p in self.layers[Layers.PIECES[t]]]
            self.nextPiece.guide.visible = False
            self.updateLiberties()
            self.updateGraph()
            self.updateTerritory()
            self.clearCache()
            return True
        elif move["action"] == "skip":
            self.turn = self.next_turn()
            return True


    def updateMove(self, pos=None):
        pos = pos or self.mousePos()
        if pos and on_board(pos):
            self.blockers = {p for p in sum((self.layers[Layers.PIECES[team]] for team in self.teams+['GHOST']),[]) if overlap(pos, p.loc)}

            opp = self.next_turn()
            pieces = {t:{p.loc for p in self.layers[Layers.PIECES[t]]} for t in self.teams}
            new_pc_w_es = {(pos,p) for p in pieces[self.turn] if nearby(pos,p)}
            pieces[self.turn].add(pos)
            all_pieces = union(iter(pieces.values()))

            # THE RULE: a piece is captured if there's no way to slide it continuously without bumping into opponent's pieces to an empty space
            # a 'liberty' is a location tangent to a piece which it can slide to, preventing capture
            # connected components of pieces that can slide to each others' locations are always captured together
            # when you place a piece, first any opponent's pieces are captured, and then your own
            # you're allowed to place a piece that gets immediately captured; this can even be useful because it might capture opponent's pieces first

            # figure out what we'll capture, starting with the opponent's pieces

            # graph of opponent's pieces accounting for new piece
            opp_edges = filter_edges(self.edges[opp], new_pc_w_es | boundary_cuts({pos}))

            # the pieces in the opponent's components we might capture (i.e. those with a piece within 6r), in components according to the new graph
            opp_cmps = components(union(cmp for cmp in self.components[opp] if any(sorta_nearby(pos, p) for p in cmp)), list(opp_edges))
            
            # an opponent's component is captured if...
            self.captures = union(cmp for cmp in opp_cmps if
                                    # it's not an isolated piece with nothing nearby...
                                    any(nearby(p, other) for p in cmp for other in all_pieces if p != other)
                                    # and the new piece overlaps or blocks all the component's liberties...
                                    and all(overlap(pos, lib) or not connected(p, lib, pieces[self.turn]) for p in cmp for lib in self.liberties[p])
                                    # and none of the tangencies with the new piece are new liberties
                                    and not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pc, tan, pieces[self.turn]) for pc in cmp for tan in double_tangents(pos,pc)))

            # after any opponent pieces are captured...
            pieces[opp] -= self.captures
            all_pieces = union(iter(pieces.values()))

            # we figure out which of our pieces get captured
            # some new edges are introduced, in two ways:
            # 1. edges with the new piece
            new_edges = filter_edges(new_pc_w_es, (lambda close_pcs: weak_edges(close_pcs) | boundary_cuts(close_pcs))({p for p in pieces[opp] if sorta_nearby(p, pos)}))
            # 2. edges which are de-broken by pieces being captured
            near_capture = {p for p in pieces[self.turn] if any(nearby(p,cap) for cap in self.captures)}
            new_edges |= filter_edges({e for e in self.potentialEdges[self.turn] if set(e)<=near_capture}, {e for e in self.potentialEdges[opp] if self.captures.isdisjoint(e)} | boundary_cuts(pieces[opp]))
            # some components are merged by the new edges
            my_cmps = components(None, list(new_edges), self.components[self.turn]+[{pos}])
            
            # one of our components is captured if...
            self.captures |= union(cmp for cmp in my_cmps if
                                    # it's not an isolated piece with nothing nearby...
                                    any(nearby(p, other) for p in cmp for other in all_pieces if p != other)
                                    # and the new piece overlaps all the component's liberties (it can't block movement because it's on the same team)...
                                    and all(overlap(pos, lib) for p in cmp-{pos} for lib in self.liberties[p])
                                    # and none of the tangencies with the new piece are new liberties for an existing piece...
                                    and not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pc, tan, pieces[opp]) for pc in cmp for tan in double_tangents(pos,pc))
                                    # and, if this is the component of the new piece, none of its tangencies with any piece are new liberties
                                    and (pos not in cmp or not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pos, tan, pieces[opp]) for pc in all_pieces for tan in double_tangents(pos,pc))))

        else: 
            self.blockers = set()
            self.captures = set()

    updateLiberties = lambda self: setattr(self, 'liberties', {pc.loc: (lambda close_pcs, close_opps: {tan for pc2 in close_pcs for tan in double_tangents(pc.loc, pc2) if on_board(tan) and not any(overlap(tan, p) for p in close_pcs) and connected(pc.loc, tan, close_opps)})([pc2.loc for t2 in self.teams for pc2 in self.layers[Layers.PIECES[t2]] if pc2 != pc and sorta_nearby(pc2.loc,pc.loc)], [pc2.loc for pc2 in self.layers[Layers.PIECES[self.next_turn(t)]] if sorta_nearby(pc2.loc, pc.loc)]) for t in self.teams for pc in self.layers[Layers.PIECES[t]]})

    def updateGraph(self):
        pieces = {t:[p.loc for p in self.layers[Layers.PIECES[t]]] for t in self.teams}
        w_es = {t:weak_edges(pieces[t]) for t in self.teams}
        self.edges = {t:filter_edges(w_es[t], w_es[self.next_turn(t)] | boundary_cuts(pieces[self.next_turn(t)])) for t in self.teams}
        self.potentialEdges = {t:w_es[t]-self.edges[t] for t in self.teams}
        self.components = {t:components(pieces[t], list(self.edges[t])) for t in self.teams}

    def updateTerritory(self):
        self.territory = {t:sum(intersect_polygon_circle_area(self.voronoi.diagram.voronoi_vertices[pc.loc], Point(0,0), board_rad) for pc in self.layers[Layers.PIECES[t]]) / pi * piece_rad**2 for t in self.teams}

    def resize(self):
        self.voronoi.mask = pygame.Surface(self.size()).convert_alpha(self.screen)
        self.voronoi.scratch = pygame.Surface(self.size()).convert_alpha(self.voronoi.mask)


if __name__=="__main__":
    run_local(Go)