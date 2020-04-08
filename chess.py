from continuousEngine import *

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

# for checking legality, etc.
dist_sq = lambda p1,p2: sum((p1[i]-p2[i])**2 for i in [0,1])
snap_to_line = lambda p, l, dl: ((p[0]*dl[0]**2+l[0]*dl[1]**2+(p[1]-l[1])*dl[0]*dl[1]) / (dl[0]**2+dl[1]**2) , (p[1]*dl[1]**2+l[1]*dl[0]**2+(p[0]-l[0])*dl[0]*dl[1]) / (dl[0]**2+dl[1]**2))
blocks_line = lambda piece, target, blocker: False if target==(piece.x,piece.y) else (lambda px,py:(piece.x<px<target[0] or piece.x>px>target[0] or piece.y<py<target[1] or piece.y>py>target[1]) and dist_sq((px,py),(blocker.x,blocker.y))<(piece.r+blocker.r)**2)(*snap_to_line((blocker.x,blocker.y),(piece.x,piece.y),(target[0]-piece.x,target[1]-piece.y)))
snap_to_segment = lambda p,l1,l2: (lambda x,y: l2 if l1[0]>l2[0]>x or l1[0]<l2[0]<x or l1[1]>l2[1]>y or l1[1]<l2[1]<y else l1 if l2[0]>l1[0]>x or l2[0]<l1[0]<x or l2[1]>l1[1]>y or l2[1]<l1[1]<y else (x,y)) (*snap_to_line(p,l1,(l2[0]-l1[0],l2[1]-l1[1])))

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
    def __init__(self, game, layer, name, color, x, y):
        super().__init__(game, layer)
        self.name, self.color, self.x, self.y = name, color, x, y
        self.r, self.sprite = Constants.RADIUS[name], Constants.SPRITE[color, name]
        self.sign = {Constants.BLACK:1, Constants.WHITE:-1}[color]

    def render(self, color=None):
        pygame.draw.circle(self.game.screen, color or {Constants.WHITE:white_color,Constants.BLACK:black_color}[self.color], self.game.pixel(self.x, self.y), int(self.r*self.game.scale))
        if not color:
            pygame.draw.circle(self.game.screen, {Constants.WHITE:white_outline_color,Constants.BLACK:black_outline_color}[self.color], self.game.pixel(self.x, self.y), int(self.r*self.game.scale), 1)
        self.game.screen.blit(self.sprite, (lambda x,y:(x-24,y-27))(*self.game.pixel(self.x, self.y)))
        
class Rook(Piece):
    __init__ = lambda self, game, color, x, y: super().__init__(game, Layers.PIECES, Constants.ROOK, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width, realWidth=False):
        x,y = x or self.x, y or self.y
        drawSegment(self.game, color, (self.game.x_min(), y), (self.game.x_max(), y), width, realWidth)
        drawSegment(self.game, color, (x, self.game.y_min()), (x, self.game.y_max()), width, realWidth)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_line((x,y),(self.x,self.y),p) for p in [(0,1),(1,0)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return (move_x,move_y), blocking, capture

class Bishop(Piece):
    __init__ = lambda self, game, color, x, y: super().__init__(game, Layers.PIECES, Constants.BISHOP, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width, realWidth=False):
        x,y = x or self.x, y or self.y
        drawSegment(self.game, color, (self.game.x_min()-2*self.r,y+x-self.game.x_min()+2*self.r), (self.game.x_max()+2*self.r,y+x-self.game.x_max()-2*self.r), width, realWidth)
        drawSegment(self.game, color, (self.game.x_min()-2*self.r,y-x+self.game.x_min()-2*self.r), (self.game.x_max()+2*self.r,y-x+self.game.x_max()+2*self.r), width, realWidth)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_line((x,y),(self.x,self.y),p) for p in [(1,1),(1,-1)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return (move_x,move_y), blocking, capture

class Queen(Piece):
    __init__ = lambda self, game, color, x, y: super().__init__(game, Layers.PIECES, Constants.QUEEN, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width, realWidth=False):
        x,y = x or self.x, y or self.y
        drawSegment(self.game, color, (self.game.x_min(), y), (self.game.x_max(), y), width, realWidth)
        drawSegment(self.game, color, (x, self.game.y_min()), (x, self.game.y_max()), width, realWidth)
        drawSegment(self.game, color, (self.game.x_min()-2*self.r,y+x-self.game.x_min()+2*self.r), (self.game.x_max()+2*self.r,y+x-self.game.x_max()-2*self.r), width, realWidth)
        drawSegment(self.game, color, (self.game.x_min()-2*self.r,y-x+self.game.x_min()-2*self.r), (self.game.x_max()+2*self.r,y-x+self.game.x_max()+2*self.r), width, realWidth)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_line((x,y),(self.x,self.y),p) for p in [(0,1),(1,0),(1,1),(1,-1)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return (move_x,move_y), blocking, capture

class Knight(Piece):
    __init__ = lambda self, game, color, x, y: super().__init__(game, Layers.PIECES, Constants.KNIGHT, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width, realWidth=False):
        x,y = x or self.x, y or self.y
        width *= self.game.scale if realWidth else 1
        pygame.draw.circle(self.game.screen, color, self.game.pixel(x,y), int(self.game.scale*5**.5+width/2), int(width))

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)
        dx, dy = x-self.x, y-self.y

        try:
            s = (5/(dx**2+dy**2))**.5
            move_x, move_y = self.x+dx*s, self.y+dy*s
        except ZeroDivisionError:
            move_x, move_y = x+5**.5, y

        capture = {p for p in pieces if
                p.color != self.color and 
                dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2
            }
        blocking = {p for p in pieces if
                p.color == self.color and 
                dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2
            }
        
        return (move_x,move_y), blocking, capture

class King(Piece):
    __init__ = lambda self, game, color, x, y: super().__init__(game, Layers.PIECES, Constants.KING, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width, realWidth=False):
        x,y = x or self.x, y or self.y
        for dx1,dy1,dx2,dy2 in [(1,1,1,-1),(1,-1,-1,-1),(-1,-1,-1,1),(-1,1,1,1)]:
            drawSegment(self.game, color, (x+dx1,y+dy1), (x+dx2,y+dy2), width, realWidth)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_segment((x,y),(self.x+dx1,self.y+dy1),(self.x+dx2,self.y+dy2)) for dx1,dy1,dx2,dy2 in [(1,1,1,-1),(1,-1,-1,-1),(-1,-1,-1,1),(-1,1,1,1)]], key = lambda p:dist_sq(p,(x,y)))

        capture = {p for p in pieces if
                p.color != self.color and 
                dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2
            }
        blocking = {p for p in pieces if
                p.color == self.color and 
                dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2
            }
        
        return (move_x,move_y), blocking, capture

class Pawn(Piece):
    __init__ = lambda self, game, color, x, y: super().__init__(game, Layers.PIECES, Constants.PAWN, color, x, y)

    def draw_guide(self, x=None, y=None, color=None, width=line_width, realWidth=False):
        x,y = x or self.x, y or self.y
        if color==None:
            drawSegment(self.game, move_guide_color, (x, y), (x, y+self.sign*(1+(y==-2.5*self.sign))), width, realWidth)
        drawSegment(self.game, color or capture_guide_color, (x, y), (x-1, y+self.sign), width, realWidth)
        drawSegment(self.game, color or capture_guide_color, (x, y), (x+1, y+self.sign), width, realWidth)
        

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_segment((x,y),(self.x,self.y),(self.x+dx,self.y+dy)) for dx,dy in [(0,self.sign*(1+(self.y==-2.5*self.sign))), (1,self.sign), (-1,self.sign)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2} - {self}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}

        if move_x == self.x:
            blocking = intersecting | capture
            capture = {}
        elif capture:
            blocking = intersecting - capture
        else:
            blocking = intersecting | {self}

        return (move_x,move_y), blocking, capture

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
        self.x = None
        self.y = None
        self.visible = False
    def render(self):
        x = self.piece.x if self.x == None else self.x
        y = self.piece.y if self.y == None else self.y
        if self.color:
            self.piece.draw_guide(x, y, color=self.color, width=2*self.piece.r if self.thick else line_width, realWidth=self.thick)
        else:
            self.piece.draw_guide(x, y, width=2*self.piece.r if self.thick else line_width, realWidth=self.thick)

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
            self.game.screen.blit(self.surf,(lambda x,y:(x-self.surf.get_width()//2,y-self.surf.get_height()//2))(*self.game.pixel(self.x,self.y)))


start_state = [
    (Rook,    Constants.BLACK,-3.5,-3.5),
    (Knight,  Constants.BLACK,-2.5,-3.5),
    (Bishop,  Constants.BLACK,-1.5,-3.5),
    (Queen,   Constants.BLACK,-0.5,-3.5),
    (King,    Constants.BLACK, 0.5,-3.5),
    (Bishop,  Constants.BLACK, 1.5,-3.5),
    (Knight,  Constants.BLACK, 2.5,-3.5),
    (Rook,    Constants.BLACK, 3.5,-3.5),
] + [
    (Pawn,    Constants.BLACK,i+.5,-2.5) for i in range(-4,4)

] + [
    (Pawn,    Constants.WHITE,i+.5, 2.5) for i in range(-4,4)
] + [
    (Rook,    Constants.WHITE,-3.5, 3.5),
    (Knight,  Constants.WHITE,-2.5, 3.5),
    (Bishop,  Constants.WHITE,-1.5, 3.5),
    (Queen,   Constants.WHITE,-0.5, 3.5),
    (King,    Constants.WHITE, 0.5, 3.5),
    (Bishop,  Constants.WHITE, 1.5, 3.5),
    (Knight,  Constants.WHITE, 2.5, 3.5),
    (Rook,    Constants.WHITE, 3.5, 3.5),
]



game = Game(start_state)

Constants.SPRITE = {(c,p):pygame.image.load('Sprites/{}{}.png'.format(c,p)).convert_alpha(game.screen) for c in Constants.COLORS for p in Constants.PIECES}

game.save_state = lambda: [(type(p), p.color, p.x, p.y) for p in game.layers[Layers.PIECES]]
game.load_state = lambda pieces: (
    game.clearLayer(Layers.PIECES),
    [name(game,color,x,y) for name, color, x, y in pieces],
    game.clearLayer(Layers.SHOWN_PIECES),
    [Guide(game,Layers.SHOWN_PIECES,p,{Constants.WHITE:bg_white_guide_color, Constants.BLACK:bg_black_guide_color}[p.color]) for p in game.layers[Layers.PIECES]],
    setattr(game, 'active_piece', None),
)
game.load_state(start_state)

game.target = None

game.future_guide = Guide(game,Layers.FUTURE_MOVES,None, future_guide_color)
game.future_guide.GETvisible = lambda game: game.active_piece != None

ActivePiece(game)

game.move_guide = Guide(game, Layers.GUIDE, None, thick=False)
game.move_guide.GETvisible = lambda game: game.active_piece != None

game.ghost = Ghost(game)

game.click[1] = lambda e: (attemptMove if game.active_piece else selectPiece)(game.point(*e.pos))

def attemptMove(mouse_pos):
    pos, blocking, capture = game.active_piece.find_move(*mouse_pos, game.layers[Layers.PIECES])

    if not blocking and len(capture)<2: # move is legal
        game.record_state()
        
        [setattr(p.guide,'visible',False) for p in game.layers[Layers.PIECES]]

        game.active_piece.x, game.active_piece.y = pos
        for piece in capture:
            game.layers[Layers.PIECES].remove(piece)

        if isinstance(game.active_piece, Pawn) and abs(game.active_piece.y)>=3.5: # pawn promotes
            Queen(game, game.active_piece.color, game.active_piece.x, game.active_piece.y)
            game.layers[Layers.PIECES].remove(game.active_piece)

        game.active_piece = None
        updateMove(mouse_pos)

def selectPiece(mouse_pos):
    clicked_on = [p for p in game.layers[Layers.PIECES] if dist_sq(mouse_pos,(p.x,p.y)) < p.r**2]
    if len(clicked_on) > 1:
        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
    elif clicked_on:
       game.active_piece = clicked_on[0]
       game.move_guide.piece = game.active_piece
       game.future_guide.piece = game.active_piece
       updateMove(mouse_pos)
       game.move_guide.piece = game.active_piece
       game.move_guide.x = game.active_piece.x
       game.move_guide.y = game.active_piece.y
       game.future_guide.piece = game.active_piece

def updateMove(mouse_pos):
    game.clearLayer(Layers.CAPBLOCK)
    if game.active_piece:
        target, blocking, capture = game.active_piece.find_move(*mouse_pos, game.layers[Layers.PIECES])
        [LitPiece(game,b,blocking_color) for b in blocking]
        [LitPiece(game,c,capture_color) for c in capture]
        game.future_guide.x, game.future_guide.y = target
        game.ghost.x, game.ghost.y = target

game.click[2] = lambda e: toggleShown(game.point(*e.pos))

def toggleShown(mouse_pos):
    clicked_on = [p for p in game.layers[Layers.PIECES] if dist_sq(mouse_pos,(p.x,p.y)) < p.r**2]
    if len(clicked_on) > 1:
        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
    elif clicked_on:
        g = clicked_on[0].guide
        g.visible = not g.visible

game.drag[-1] = lambda e: updateMove(game.point(*e.pos))

game.keys.cancel = 27 # escape
game.keys.printHistory = 32 # space

game.keyPress[game.keys.cancel]         = lambda e: (setattr(game,'active_piece',None), game.clearLayer(Layers.CAPBLOCK))
game.keyPress[game.keys.printHistory]   = lambda e: (print("   CURRENT STATE"),print(game.save_state()),print("   HISTORY"),print(game.history),print("   FUTURE"),print(game.future))


while 1: game.update()