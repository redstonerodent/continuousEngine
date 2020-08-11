from continuousEngine import *
from geometry import *

# always-present guides
bg_white_guide_color = (230,230,210)
bg_black_guide_color = (210,230,230)

# piece circles
white_color = (255,255,0)
white_outline_color = (205,205,0)
black_color = (0,255,255)
black_outline_color = (0,205,205)

# current move attempt
active_color = (0,255,0)
capture_color = (0,0,255)
blocking_color = (255,0,0)
guide_color = (255,0,255)
future_guide_color = (245, 200, 245)

# for pawns
move_guide_color  =(150,0,255)
capture_guide_color  =(255,0,150)

alpha = 100
line_width = 3

# does blocker prevent piece from moving in a straight line to target?
blocks_line = lambda piece, target, blocker: dist_to_segment(blocker.loc, piece.loc, target) < piece.r + blocker.r

class Constants:
    COLORS = WHITE, BLACK = 'white', 'black'
    PIECES = KING, QUEEN, ROOK, BISHOP, KNIGHT, PAWN = 'King', 'Queen', 'Rook', 'Bishop', 'Knight', 'Pawn'

    RADIUS = {
        KING:   .36,
        QUEEN:  .34,
        ROOK:   .27,
        BISHOP: .32,
        KNIGHT: .30,
        PAWN:   .25,
    }

class Layers:
#     0: background
    SHOWN_PIECES    = 1 # middle-clicked attacks, Guides
    FUTURE_MOVES    = 2 # future_guide for range after this move 
    PIECES          = 3 # pieces
    ACTIVE          = 4 # active_piece
    CAPBLOCK        = 6 # blocking+capturable pieces
    GUIDE           = 7 # move_guide for this move
    GHOST           = 8 # ghost

class Piece(Renderable):
    def __init__(self, game, layer, name, color, loc):
        super().__init__(game, layer)
        self.name, self.color, self.loc = name, color, loc
        self.r, self.sprite = Constants.RADIUS[name], Constants.SPRITE[color, name]
        self.sign = {Constants.BLACK:1, Constants.WHITE:-1}[color]

    def render(self, color=None, outline_color=None):
        pygame.draw.circle(self.game.screen, color or {Constants.WHITE:white_color,Constants.BLACK:black_color}[self.color], self.game.pixel(*self.loc), int(self.r*self.game.scale))
        pygame.draw.circle(self.game.screen, outline_color or {Constants.WHITE:white_outline_color,Constants.BLACK:black_outline_color}[self.color], self.game.pixel(*self.loc), int(self.r*self.game.scale), 1)
        self.game.screen.blit(self.sprite, (lambda x,y:(x-24,y-27))(*self.game.pixel(*self.loc)))

class Runner(Piece):
    def __init__(self, game, name, color, loc, dirs):
        super().__init__(game, Layers.PIECES, name, color, loc)
        self.dirs = dirs

    def draw_guide(self, loc=None, color=guide_color, width=line_width, realWidth=False):
        [drawRay(self.game, color, loc or self.loc, d, width, realWidth) for d in self.dirs]

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)

        move = min((nearest_on_line(loc,self.loc,self.loc+p) for p in self.dirs), key = lambda p: p>>loc)

        intersecting = {p for p in pieces if blocks_line(self, move, p)}
        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return move, blocking, capture


class Rook(Runner):
    __init__ = lambda self, game, color, loc: super().__init__(game, Constants.ROOK, color, loc, [Point(1,0), Point(-1,0), Point(0,1), Point(0,-1)])

class Bishop(Runner):
    __init__ = lambda self, game, color, loc: super().__init__(game, Constants.BISHOP, color, loc, [Point(1,1), Point(-1,-1), Point(-1,1), Point(1,-1)])

class Queen(Runner):
    __init__ = lambda self, game, color, loc: super().__init__(game, Constants.QUEEN, color, loc, [Point(1,0), Point(-1,0), Point(0,1), Point(0,-1), Point(1,1), Point(-1,-1), Point(-1,1), Point(1,-1)])

class Knight(Piece):
    __init__ = lambda self, game, color, loc: super().__init__(game, Layers.PIECES, Constants.KNIGHT, color, loc)

    def draw_guide(self, loc=None, color=guide_color, width=line_width, realWidth=False):
        loc = loc or self.loc
        width *= self.game.scale if realWidth else 1
        pygame.draw.circle(self.game.screen, color, self.game.pixel(*loc), int(self.game.scale*5**.5+width/2), int(width))

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)

        move = nearest_on_circle(loc, self.loc, 5**.5)

        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}
        blocking = {p for p in pieces if p.color == self.color and move>>p.loc < (self.r+p.r)**2}
        
        return move, blocking, capture

class King(Piece):
    __init__ = lambda self, game, color, loc: super().__init__(game, Layers.PIECES, Constants.KING, color, loc)

    def draw_guide(self, loc=None, color=guide_color, width=line_width, realWidth=False):
        loc = loc or self.loc
        [drawSegment(self.game, color, loc+d1, loc+d2, width, realWidth) for d1,d2 in [(Point(1,1),Point(1,-1)), (Point(1,-1),Point(-1,-1)), (Point(-1,-1),Point(-1,1)), (Point(-1,1),Point(1,1))]]

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)

        move = min((nearest_on_segment(loc,self.loc+d1,self.loc+d2) for d1,d2 in [(Point(1,1),Point(1,-1)), (Point(1,-1),Point(-1,-1)), (Point(-1,-1),Point(-1,1)), (Point(-1,1),Point(1,1))]),
                key = lambda p: p>>loc)

        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}
        blocking = {p for p in pieces if p.color == self.color and move>>p.loc < (self.r+p.r)**2}
        
        return move, blocking, capture

class Pawn(Piece):
    __init__ = lambda self, game, color, loc: super().__init__(game, Layers.PIECES, Constants.PAWN, color, loc)

    def draw_guide(self, loc=None, color=None, width=line_width, realWidth=False):
        loc = loc or self.loc
        if color==None:
            drawSegment(self.game, move_guide_color, loc, loc + Point(0,self.sign*(1+(loc.y==-2.5*self.sign))), width, realWidth)
        drawSegment(self.game, color or capture_guide_color, loc, loc + Point(-1, self.sign), width, realWidth)
        drawSegment(self.game, color or capture_guide_color, loc, loc + Point( 1, self.sign), width, realWidth)
        

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)
        move = min((nearest_on_segment(loc,self.loc,self.loc+p) for p in [Point(0,self.sign*(1+(self.loc.y==-2.5*self.sign))), Point(1,self.sign), Point(-1,self.sign)]), key = lambda p: p>>loc)

        intersecting = {p for p in pieces if blocks_line(self, move, p)} - {self}
        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}

        if move.x == self.loc.x:
            print('branch 1')
            blocking = intersecting | capture
            capture = {}
        elif capture:
            print('branch 2')
            blocking = intersecting - capture
        else:
            print('branch 3')
            blocking = intersecting | {self}

        return move, blocking, capture

class Guide(Renderable):
    # thick => show region attacked
    # not thick => show just lines
    def __init__(self, game, layer, piece, color=None, thick=True):
        super().__init__(game, layer)
        self.piece = piece
        self.thick = thick
        self.color = color
        if piece: 
            self.piece.guide = self
        self.loc = None
        self.visible = False
    def render(self):
        loc = self.loc or self.piece.loc
        if self.color:
            self.piece.draw_guide(loc, color=self.color, width=2*self.piece.r if self.thick else line_width, realWidth=self.thick)
        else:
            self.piece.draw_guide(loc, width=2*self.piece.r if self.thick else line_width, realWidth=self.thick)

class ActivePiece(Renderable):
    def __init__(self, game):
        super().__init__(game, Layers.ACTIVE)
    def render(self):
        if self.game.active_piece:
            self.game.active_piece.render(active_color)

class LitPiece(Renderable):
    def __init__(self, game, piece, color):
        super().__init__(game, Layers.CAPBLOCK)
        self.piece = piece
        self.color = color
    def render(self):
        self.piece.render(self.color)

class Ghost(Renderable):
    def __init__(self, game):
        super().__init__(game, Layers.GHOST)
        self.state = None
    def render(self):
        if self.game.active_piece:
            if self.state != (self.game.scale, self.game.active_piece):
                self.state = self.game.scale, self.game.active_piece
                diameter = int(self.game.active_piece.r*2*self.game.scale)
                size = max(diameter, 60)
                self.surf = pygame.Surface((size, size)).convert_alpha(self.game.screen)
                self.surf.fill((0,0,0,0))
                pygame.draw.circle(self.surf, active_color, (size//2,size//2), diameter//2)
                self.surf.blit(self.game.active_piece.sprite, (size//2-25, size//2-25))
                self.surf.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
            self.game.screen.blit(self.surf,(lambda x,y:(x-self.surf.get_width()//2,y-self.surf.get_height()//2))(*self.game.pixel(*self.loc)))


start_state = [
    (Rook,    Constants.BLACK, (-3.5,-3.5)),
    (Knight,  Constants.BLACK, (-2.5,-3.5)),
    (Bishop,  Constants.BLACK, (-1.5,-3.5)),
    (Queen,   Constants.BLACK, (-0.5,-3.5)),
    (King,    Constants.BLACK, ( 0.5,-3.5)),
    (Bishop,  Constants.BLACK, ( 1.5,-3.5)),
    (Knight,  Constants.BLACK, ( 2.5,-3.5)),
    (Rook,    Constants.BLACK, ( 3.5,-3.5)),
] + [
    (Pawn,    Constants.BLACK, (i+.5,-2.5)) for i in range(-4,4)

] + [
    (Pawn,    Constants.WHITE, (i+.5, 2.5)) for i in range(-4,4)
] + [
    (Rook,    Constants.WHITE, (-3.5, 3.5)),
    (Knight,  Constants.WHITE, (-2.5, 3.5)),
    (Bishop,  Constants.WHITE, (-1.5, 3.5)),
    (Queen,   Constants.WHITE, (-0.5, 3.5)),
    (King,    Constants.WHITE, ( 0.5, 3.5)),
    (Bishop,  Constants.WHITE, ( 1.5, 3.5)),
    (Knight,  Constants.WHITE, ( 2.5, 3.5)),
    (Rook,    Constants.WHITE, ( 3.5, 3.5)),
]



game = Game(start_state)

Constants.SPRITE = {(c,p):pygame.image.load('Sprites/{}{}.png'.format(c,p)).convert_alpha(game.screen) for c in Constants.COLORS for p in Constants.PIECES}

game.save_state = lambda: [(type(p), p.color, p.loc.coords) for p in game.layers[Layers.PIECES]]
game.load_state = lambda pieces: (
    game.clearLayer(Layers.PIECES),
    [name(game,color,Point(*loc)) for name, color, loc in pieces],
    game.clearLayer(Layers.SHOWN_PIECES),
    [Guide(game,Layers.SHOWN_PIECES,p,{Constants.WHITE:bg_white_guide_color, Constants.BLACK:bg_black_guide_color}[p.color]) for p in game.layers[Layers.PIECES]],
    setattr(game, 'active_piece', None),
)
game.load_state(start_state)

game.rawMousePos = None
game.getMousePos = lambda: game.rawMousePos and game.point(*game.rawMousePos)

game.process = lambda: updateMove(game)

game.future_guide = Guide(game,Layers.FUTURE_MOVES,None, future_guide_color)
game.future_guide.GETvisible = lambda game: game.active_piece != None

ActivePiece(game)

game.move_guide = Guide(game, Layers.GUIDE, None, thick=False)
game.move_guide.GETvisible = lambda game: game.active_piece != None

game.ghost = Ghost(game)

game.click[1] = lambda e: (attemptMove if game.active_piece else selectPiece)(game.point(*e.pos))

def attemptMove(mouse_pos):
    pos, blocking, capture = game.active_piece.find_move(mouse_pos, game.layers[Layers.PIECES])

    if not blocking and len(capture)<2: # move is legal
        game.record_state()
        
        [setattr(p.guide,'visible',False) for p in game.layers[Layers.PIECES]]

        game.active_piece.loc = pos
        for piece in capture:
            game.layers[Layers.PIECES].remove(piece)

        if isinstance(game.active_piece, Pawn) and abs(game.active_piece.loc.y)>=3.5: # pawn promotes
            Guide(game, Layers.SHOWN_PIECES, Queen(game, game.active_piece.color, game.active_piece.loc), {Constants.WHITE:bg_white_guide_color, Constants.BLACK:bg_black_guide_color}[game.active_piece.color])
            game.layers[Layers.PIECES].remove(game.active_piece)

        game.active_piece = None
        updateMove(game)

def selectPiece(mouse_pos):
    clicked_on = [p for p in game.layers[Layers.PIECES] if mouse_pos>>p.loc < p.r**2]
    if len(clicked_on) > 1:
        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
    elif clicked_on:
       game.active_piece = clicked_on[0]
       game.move_guide.piece = game.active_piece
       game.future_guide.piece = game.active_piece
       updateMove(game)
       game.move_guide.piece = game.active_piece
       game.move_guide.loc = game.active_piece.loc
       game.future_guide.piece = game.active_piece

def updateMove(game):
    pos = game.getMousePos()
    game.clearLayer(Layers.CAPBLOCK)
    if game.active_piece:
        target, blocking, capture = game.active_piece.find_move(pos, game.layers[Layers.PIECES])
        [LitPiece(game,b,blocking_color) for b in blocking]
        [LitPiece(game,c,capture_color) for c in capture]
        game.future_guide.loc = target
        game.ghost.loc = target

game.click[2] = lambda e: toggleShown(game.point(*e.pos))

def toggleShown(mouse_pos):
    clicked_on = [p for p in game.layers[Layers.PIECES] if mouse_pos>>p.loc < p.r**2]
    if len(clicked_on) > 1:
        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
    elif clicked_on:
        g = clicked_on[0].guide
        g.visible = not g.visible

game.drag[-1] = lambda e: setattr(game, 'rawMousePos', e.pos)

game.keys.cancel = pygame.K_ESCAPE # escape
game.keys.printHistory = pygame.K_SPACE # space

game.keyPress[game.keys.cancel]         = lambda e: (setattr(game,'active_piece',None), game.clearLayer(Layers.CAPBLOCK))
game.keyPress[game.keys.printHistory]   = lambda e: (print("   CURRENT STATE"),print(game.save_state()),print("   HISTORY"),print(game.history),print("   FUTURE"),print(game.future))


while 1: game.update()