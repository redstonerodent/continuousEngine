from continuousEngine import *

# Note to anyone reading this code: sometimes p (or p1 or p2 or pt or pv) is a Point, and sometimes it's a ReversiPiece. I'm sorry.

# needs to be more than 1/sqrt(6)~=0.408 for diagonals to work the same as in the discrete game
piece_rad = .45
piece_core = 0.5 * piece_rad

board_rad = 5
# is this piece within the (circular) board?
on_board = lambda p: +p < (board_rad - piece_rad)**2

# squared distance
dist_sq = lambda p1,p2: (p1[0]-p2[0])**2+(p1[1]-p2[1])**2

# does a piece centered at x intersect the path between pieces centered at p1 and p2?
in_path = lambda x, p1, p2: p1 != p2 and dist_to_line(x, p1, p2) < piece_rad and epsilon < dist_along_line(x, p1, p2) < (p1>>p2)**.5 - epsilon
# is the core a piece centered at x on the path between pieces centered at p1 and p2?
core_in_path = lambda x, p1, p2: p1 != p2 and dist_to_line(x, p1, p2) < piece_core and epsilon < dist_along_line(x, p1, p2) < (p1>>p2)**.5 - epsilon
# do pieces centered at p1 and p2 overlap?
overlap = lambda p1, p2: p1>>p2 < (2*piece_rad)**2
# combat floating point errors. In particular, tangent circles shouldn't intersect
epsilon = 10**-10
# centers of circles tangent to both circles centered at p1 and p2
double_tangents = lambda p1, p2: intersection_circles(p1, p2, 2*piece_rad)
# centers of some circles tangent to the circle centered at x on opposite sides,
#   such that one intersects the line from p1 to p2 in each region of angles in which a tangent circle can intersect the line
# if the circle intersects the line, gives one on each side in the direction parallel to the line
# if the circle doesn't intersect the line, gives one on each side in the direction perpendicular to the line
# if the circle is far away, gives nothing
# (dx, dy) is a vector of length 2*piece_rad parallel to the line
on_line_tangents = lambda x, p1, p2: (lambda dist: (lambda dx: (x+dx, x-dx)) ((p2-p1) @ 1 if dist < 1 else ~((p2-p1) @ 1)) if dist < 3 else ()) (dist_to_line(x,p1,p2))

# THE RULE: a piece at P is a "pivot" for your move M if
#               1. P is on your team
#               2. at least one piece's core intersects PM
#               3. no piece on your team (other than P and M) intersects the line segment PM
#               4. the set of pieces (other than P and M) which intersect the line segment PM is maximal;
#                   i.e. there's nowhere a piece could be placed such that it doesn't intersect any existing pieces and it intersects PM
#           you can only place a piece if there's at least one pivot.
#           when you place a piece, all pieces with cores intersecting lines from the new piece to pivots flip.
# suppose player t (str) places a piece at pt ((float,float)) given pieces pcs ([ReversiPiece])
# pivots(pcs, t, pt) is the list of tuples (pv, flipped) where 
#   pv is a "pivot"
#   flipped is the list of pieces along the line from pt to pv; i.e. pieces that would flip because of pv
# this is slow for more than ~30 pieces
# 1-3 are checked by the first three clauses of the if
# 4 is the hard one. To check it, we try a particular set of potential placements such that (I've convinced myself) if none of them work, then nothing does
#   these potential placements are:
#       4.1. tangent to one existing piece in a particular direction (on_line_tangents). each piece close to the line gives 2 of these
#               the direction is parallel to the line if the piece intersects it, and perpendicular otherwise
#       4.2. tangent to two existing pieces (from p.valid_tangents)
#       4.3. tangent to an existing piece and the newly placed piece
# we save some time by only considering pieces close enough to the line to matter (i.e. within 3*piece_rad)
# it's slowest when finding real pivots, since it has to check every potential location (and can be lazy when it fails to find a pivot)
# there are pathological cases meaning you can't just look at pieces on the line or something clever like that
pivots = lambda pcs, t, pt: [(pv,[pc for pc in pcs if core_in_path(pc.loc, pt, pv.loc)]) for pv in pcs
            if pv.team==t # 1. pv is on your team
            and any(core_in_path(pc.loc, pt, pv.loc) for pc in pcs) # 2. there's a piece with core on the line
            and not any(pc.team == t and in_path(pc.loc, pt, pv.loc) for pc in pcs) # 3. no piece on your team intersects the line
            # 4. you can't fit another piece on the line without overlap: try some potential locations for each piece near the line
            and (lambda closePieces: 
                # 4.1. tangent to one piece, in the direction (parrallel|perpendicular) to the line
                not any(on_board(p) and in_path(p, pt, pv.loc) and not any(overlap(p,q.loc) for q in closePieces) and not overlap(p,pt) for pc in closePieces for p in on_line_tangents(pc.loc, pt, pv.loc))
                # 4.2. tangent to two existing pieces
                and not any(in_path(p, pt, pv.loc) and not overlap(p,pt) for pc in closePieces for p in pc.valid_tangents)
                # 4.3. tangent to existing piece and new piece
                and not any(in_path(p, pt, pv.loc) and not any(overlap(p,q.loc) for q in closePieces) for pc in closePieces for p in double_tangents(pt,pc.loc))
                ) ({p for p in pcs if dist_to_line(p.loc, pt, pv.loc) < 3*piece_rad})
            ]

class Layers:
    BOUNDARY    = 1
    PIECES      = 2
    GUIDES      = 3
    CORES       = 2 # added to piece layer
    NEWPIECE    = 5 # newpiece core: 7
    COUNT       = 10

class Colors:
    fill        = {'white': (205,205,205), 'black': (50, 50, 50 )}
    core        = {'white': (225,225,225), 'black': (30, 30, 30 )}
    border      = {'white': (80, 80, 80 ), 'black': (135,135,135)}
    newfill     = {'white': (255,255,255), 'black':(0,0,0)}
    flipper     = (0,255,0)
    blocker     = (255,0,0)
    guide       = (0,255,255)
    background  = (0,130,30)
    text        = {'white': (255,255,255), 'black':(0,0,0), 'GAMEOVER':(230,20,128)}
    boundary    = (0,0,0)
    debug       = (255,0,0)

class ReversiPiece(BorderDisk):
    def __init__(self, game, team, loc, layer=Layers.PIECES):
        super().__init__(game, layer, None, None, loc, piece_rad)
        self.team = team
        self.GETfill_color = lambda g: Colors.fill[self.team]
        self.GETborder_color = lambda g: Colors.blocker if self in g.blockers else Colors.flipper if self in g.flippers else Colors.border[self.team]
        self.valid_tangents = set()
        if team:
            ReversiGuide(game, self)
        self.core = ReversiPieceCore(game, self, layer)
    if 0:
        def render(self):
            super().render()
            for pt in self.valid_tangents:
                pygame.draw.line(self.game.screen, Colors.debug, self.game.pixel(self.loc), self.game.pixel(pt), 3)

class ReversiPieceCore(Disk):
    def __init__(self, game, piece, layer):
        super().__init__(game, layer + 2, None, piece.loc, piece_core)
        self.piece = piece
        self.GETcolor = lambda g: Colors.core[self.piece.team]
        self.GETvisible = lambda g: self.piece.visible
        self.GETloc = lambda g: self.piece.loc

class ReversiGuide(Segment):
    def __init__(self, game, piece):
        super().__init__(game, Layers.GUIDES, Colors.guide, piece.loc, None)
        self.piece = piece
        self.GETvisible = lambda g: g.mousePos() and self.piece in g.pivots
        self.GETp2 = lambda g: g.mousePos()

class Reversi(Game):
    make_initial_state = lambda self: ('black',
        [('white', ( .5, .5)),
         ('white', (-.5,-.5)),
         ('black', ( .5,-.5)),
         ('black', (-.5, .5))],
        )

    teams = ['black', 'white']

    def __init__(self, **kwargs):
        super().__init__(backgroundColor=Colors.background, spread=board_rad, name='continuous reversi', **kwargs)

        self.save_state = lambda: (self.turn, [(p.team, p.loc.coords) for p in self.layers[Layers.PIECES]])
        self.load_state = lambda x: (lambda turn, pieces:(
            self.clearLayer(Layers.PIECES),
            self.clearLayer(Layers.PIECES + Layers.CORES),
            self.clearLayer(Layers.GUIDES),
            [self.makePiece(team, Point(*coords)) for team, coords in pieces],
            setattr(self, 'flippers', set()),
            setattr(self, 'blockers', set()),
            setattr(self, 'pivots', []),
            setattr(self, 'turn', turn),
            setattr(self, 'over', not any(p.valid_tangents for p in self.layers[Layers.PIECES]))
            ))(*x)

        Circle(self, Layers.BOUNDARY, Colors.boundary, Point(0,0), board_rad).GETcolor = lambda g: Colors.boundary if self.rawMousePos == None or self.over or on_board(self.mousePos()) else Colors.blocker

        FixedText(self, Layers.COUNT, Colors.text['black'], self.font, 0, -30,30, halign='r', valign='t', hborder='r').GETtext = lambda g: len([0 for p in g.layers[Layers.PIECES] if p.team == 'black'])
        FixedText(self, Layers.COUNT, Colors.text['white'], self.font, 0, -30,60, halign='r', valign='t', hborder='r').GETtext = lambda g: len([0 for p in g.layers[Layers.PIECES] if p.team == 'white'])

        self.gameOverMessage = FixedText(self, Layers.COUNT, Colors.text['GAMEOVER'], self.font, "", 0,0, hborder='c', vborder='c')
        self.gameOverMessage.GETvisible = lambda g: g.over
        self.gameOverMessage.GETtext = lambda g: "Game Over!  "+(
            lambda w,b: "White wins!" if w>b else "Black wins!" if b>w else "It's a tie!")(
            len([0 for p in g.layers[Layers.PIECES] if p.team == 'white']), len([0 for p in g.layers[Layers.PIECES] if p.team == 'black']))

        self.makePiece = lambda t,loc: (lambda pieces,new: (
            # we keep track of the locations a piece could fit tangent to two existing pieces
            # this is only updated when a new piece is placed, for speed
            # each such locations is in the set 'p.valid_tangents,' where p is the later of the two pieces it's tangent to
            # when we add a piece, we need to compute all the new valid tangents:
            setattr(new, 'valid_tangents', {pt for pc in pieces for pt in double_tangents(loc, pc) if on_board(pt) and all(pt>>p > (2*piece_rad)**2 for p in pieces)}),
            # and remove any points the new piece overlaps:
            [setattr(p, 'valid_tangents', {pt for pt in p.valid_tangents if pt>>loc > (2*piece_rad)**2}) for p in self.layers[Layers.PIECES]]
            ))([p.loc for p in self.layers[Layers.PIECES]], ReversiPiece(self, t, loc))

        self.nextPiece = ReversiPiece(self, None, None, Layers.NEWPIECE)
        self.nextPiece.GETteam = lambda g: g.turn
        self.nextPiece.GETvisible = lambda g: g.mousePos() and not g.over
        self.nextPiece.GETloc = lambda g: g.mousePos()
        self.nextPiece.GETborder_color = lambda g: Colors.flipper if g.pivots and not g.blockers else Colors.blocker
        self.nextPiece.GETfill_color = lambda g: Colors.newfill[g.turn]

        self.process = self.updateMove

        self.reset_state()


        # test speed:
        if 0:
            import random
            spread = 10
            count = 100
            [self.makePiece(random.choice(['white','black']),Point(random.random()*spread-spread/2,random.random()*spread-spread/2)) for _ in range(count)]

        self.click[1] = lambda _: self.attemptMove({"player":self.turn, "location":self.mousePos().coords})


    def attemptGameMove(self, move):
        pos = Point(*move["location"])
        self.updateMove(pos)
        if self.blockers or not self.pivots: return False
        self.record_state()
        self.makePiece(self.turn, pos)
        for p in self.flippers: p.team = self.turn
        # game is over if there's nowhere to fit another piece
        # note: this does NOT detect when none of the places a piece fits flips anything, so you can get "stuck"
        if not any(p.valid_tangents for p in self.layers[Layers.PIECES]):
            self.over = True
        return True

    def updateMove(self, pos=None):
        pos = pos or self.mousePos()
        if not self.over and pos and on_board(pos):
            self.blockers = {p for p in self.layers[Layers.PIECES] if overlap(pos, p.loc)}
            self.pivots, flipped = (lambda t: zip(*t) if t else ([],[]))(pivots(self.layers[Layers.PIECES], self.turn, pos))
            self.flippers = {p for ps in flipped for p in ps}
        else: self.blockers, self.pivots, self.flippers = set(), [], set()


if __name__=="__main__":
    pygame.init()
    run_local(Reversi)
