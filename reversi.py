from continuousEngine import *

# Note to anyone reading this code: sometimes p (or p1 or p2 or pt or pv) is a pair of floats representing a point, and sometimes it's a ReversiPiece. I'm sorry.

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
double_tangents = lambda p1, p2: intersect_circles(p1, p2, 2*piece_rad)
# centers of some circles tangent to the circle centered at x on opposite sides,
#   such that one intersects the line from p1 to p2 in each region of angles in which a tangent circle can intersect the line
# if the circle intersects the line, gives one on each side in the direction parallel to the line
# if the circle doesn't intersect the line, gives one on each side in the direction perpendicular to the line
# if the circle is far away, gives nothing
# (dx, dy) is a vector of length 2*piece_rad parallel to the line
on_line_tangents = lambda x, p1, p2: (lambda dist: (lambda dx: (x+dx, x-dx)) ((p2-p1) @ 1 if dist < 1 else ~((p2-p1) @ 1)) if dist < 3 else ()) (dist_to_line(x,p1,p2))

# (lambda d:
#         (lambda dx, dy: ( (x[0]+dx*(1+epsilon),x[1]+dy*(1+epsilon)) , (x[0]-dx*(1+epsilon),x[1]-dy*(1+epsilon)) ) )
#             (2*piece_rad*(p2[0]-p1[0])/dist_sq(p1,p2)**.5,2*piece_rad*(p2[1]-p1[1])/dist_sq(p1,p2)**.5) if d < 1 else
#         (lambda dx, dy: ( (x[0]+dy*(1+epsilon),x[1]-dx*(1+epsilon)) , (x[0]-dy*(1+epsilon),x[1]+dx*(1+epsilon)) ) )
#             (2*piece_rad*(p2[0]-p1[0])/dist_sq(p1,p2)**.5,2*piece_rad*(p2[1]-p1[1])/dist_sq(p1,p2)**.5) if d < 3 else
#         ()
#     )(dist_to_line(x,p1,p2)/piece_rad)



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

inc_turn = {'WHITE':'BLACK', 'BLACK':'WHITE'}

class Layers:
    BOUNDARY    = 1
    PIECES      = 2
    GUIDES      = 3
    CORES       = 2 # added to piece layer
    NEWPIECE    = 5 # newpiece core: 7
    COUNT       = 10

class Colors:
    fill        = {'WHITE': (205,205,205), 'BLACK': (50, 50, 50 )}
    core        = {'WHITE': (225,225,225), 'BLACK': (30, 30, 30 )}
    border      = {'WHITE': (80, 80, 80 ), 'BLACK': (135,135,135)}
    newfill     = {'WHITE': (255,255,255), 'BLACK':(0,0,0)}
    flipper     = (0,255,0)
    blocker     = (255,0,0)
    guide       = (0,255,255)
    background  = (0,130,30)
    text        = {'WHITE': (255,255,255), 'BLACK':(0,0,0), 'GAMEOVER':(230,20,128)}
    boundary    = (0,0,0)
    debug       = (255,0,0)

font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)

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
    if 1:
        def render(self):
            super().render()
            for pt in self.valid_tangents:
                pygame.draw.line(self.game.screen, Colors.debug, self.game.pixel(*self.loc), self.game.pixel(*pt), 3)

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
        self.GETvisible = lambda g: g.getMousePos() and self.piece in g.pivots
        self.GETp2 = lambda g: g.getMousePos()

start_state = ('WHITE',
    [('WHITE', ( .5, .5)),
     ('WHITE', (-.5,-.5)),
     ('BLACK', ( .5,-.5)),
     ('BLACK', (-.5, .5))],
    )

game = Game(
    initialState=start_state,
    backgroundColor=Colors.background
)

game.save_state = lambda: (game.turn, [(p.team, p.loc.coords) for p in game.layers[Layers.PIECES]])
game.load_state = lambda x: (lambda turn, pieces:(
    game.clearLayer(Layers.PIECES),
    game.clearLayer(Layers.PIECES + Layers.CORES),
    game.clearLayer(Layers.GUIDES),
    [game.makePiece(team, Point(*coords)) for team, coords in pieces],
    setattr(game, 'flippers', set()),
    setattr(game, 'blockers', set()),
    setattr(game, 'pivots', []),
    setattr(game, 'turn', turn),
    setattr(game, 'over', not any(p.valid_tangents for p in game.layers[Layers.PIECES]))
    ))(*x)

Circle(game, Layers.BOUNDARY, Colors.boundary, Point(0,0), board_rad, 3).GETcolor = lambda g: Colors.boundary if game.rawMousePos == None or game.over or on_board(game.getMousePos()) else Colors.blocker

FixedText(game, Layers.COUNT, Colors.text['BLACK'], font, 0, game.width-30,30, *'rt').GETtext = lambda g: len([0 for p in g.layers[Layers.PIECES] if p.team == 'BLACK'])
FixedText(game, Layers.COUNT, Colors.text['WHITE'], font, 0, game.width-30,60, *'rt').GETtext = lambda g: len([0 for p in g.layers[Layers.PIECES] if p.team == 'WHITE'])

gameOverMessage = FixedText(game, Layers.COUNT, Colors.text['GAMEOVER'], font, "", game.width//2, game.height//2, *'cc')
gameOverMessage.GETvisible = lambda g: g.over
gameOverMessage.GETtext = lambda g: "Game Over!  "+(
    lambda w,b: "White wins!" if w>b else "Black wins!" if b>w else "It's a tie!")(
    len([0 for p in g.layers[Layers.PIECES] if p.team == 'WHITE']), len([0 for p in g.layers[Layers.PIECES] if p.team == 'BLACK']))

game.rawMousePos = None
game.getMousePos = lambda: game.rawMousePos and game.point(*game.rawMousePos)

game.makePiece = lambda t,loc: (lambda pieces,new: (
    # we keep track of the locations a piece could fit tangent to two existing pieces
    # this is only updated when a new piece is placed, for speed
    # each such locations is in the set 'p.valid_tangents,' where p is the later of the two pieces it's tangent to
    # when we add a piece, we need to compute all the new valid tangents:
    setattr(new, 'valid_tangents', {pt for pc in pieces for pt in double_tangents(loc, pc) if on_board(pt) and all(pt>>p > (2*piece_rad)**2 for p in pieces)}),
    # and remove any points the new piece overlaps:
    [setattr(p, 'valid_tangents', {pt for pt in p.valid_tangents if pt>>loc > (2*piece_rad)**2}) for p in game.layers[Layers.PIECES]]
    ))([p.loc for p in game.layers[Layers.PIECES]], ReversiPiece(game, t, loc))

nextPiece = ReversiPiece(game, None, None, Layers.NEWPIECE)
nextPiece.GETteam = lambda g: g.turn
nextPiece.GETvisible = lambda g: g.getMousePos() and not g.over
nextPiece.GETloc = lambda g: g.getMousePos()
nextPiece.GETborder_color = lambda g: Colors.flipper if g.pivots and not g.blockers else Colors.blocker
nextPiece.GETfill_color = lambda g: Colors.newfill[g.turn]

def attemptMove(game):
    updateMove(game)
    if game.blockers or not game.pivots: return
    game.record_state()
    game.makePiece(game.turn, game.getMousePos())
    for p in game.flippers: p.team = inc_turn[p.team]
    game.turn = inc_turn[game.turn]
    # game is over if there's nowhere to fit another piece
    # note: this does NOT detect when none of the places a piece fits flips anything, so you can get "stuck"
    if not any(p.valid_tangents for p in game.layers[Layers.PIECES]):
        game.over = True

def updateMove(game, pos=None):
    if pos:
        game.rawMousePos = pos
    pos = game.getMousePos()
    if not game.over and pos and on_board(pos):
        game.blockers = {p for p in game.layers[Layers.PIECES] if overlap(pos, p.loc)}
        game.pivots, flipped = (lambda t: zip(*t) if t else ([],[]))(pivots(game.layers[Layers.PIECES], game.turn, pos))
        game.flippers = {p for ps in flipped for p in ps}
    else: game.blockers, game.pivots, game.flippers = set(), [], set()

game.process = lambda: updateMove(game)

game.load_state(start_state)

# test speed:
if 1:
    import random
    spread = 10
    count = 100
    [game.makePiece(random.choice(['WHITE','BLACK']),Point(random.random()*spread-spread/2,random.random()*spread-spread/2)) for _ in range(count)]

game.click[1] = lambda e: attemptMove(game)
game.drag[-1] = lambda e: setattr(game, 'rawMousePos', e.pos)

game.keys.skipTurn = pygame.K_u

game.keyPress[game.keys.skipTurn] = lambda _: setattr(game, 'turn', inc_turn[game.turn])

while 1: 
    game.update()