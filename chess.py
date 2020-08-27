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
move_guide_color = (150,0,255)
capture_guide_color = (255,0,150)

outline_color = (100,100,100)
turn_indicator_color = {'white':(255,255,255), 'black':(0,0,0)}

threatened_color = (255,0,0)

alpha = 100
line_width = 3

# does blocker prevent a piece at loc with radius r from moving in a straight line to target?
blocks_segment = lambda loc, r, target, blocker: dist_to_segment(blocker.loc, loc, target) < r + blocker.r

# if a piece at loc with radius r moves in dir, will it hit blocker?
blocks_ray = lambda loc, r, dir, blocker: dist_to_ray(blocker.loc, loc, dir) < r + blocker.r

# if a piece at loc with radius r moves distance d, can it hit blocker?
blocks_circle = lambda loc, r, d, blocker: dist_to_circle(blocker.loc, loc, d) < r + blocker.r

# how far does a piece at loc with radius r need to move in direction dir to capture cap?
dist_to_capture = lambda loc, r, dir, cap: dist_along_line(cap.loc, loc, loc+dir) - ((r + cap.r)**2 - dist_to_line(cap.loc, loc, loc+dir)**2)**.5

knight_dist = 5**.5
king_deltas = [(Point(1,1),Point(1,-1)), (Point(1,-1),Point(-1,-1)), (Point(-1,-1),Point(-1,1)), (Point(-1,1),Point(1,1))]

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
    OUTLINE         = .3
    TURN_INDICATOR  = .5
    SHOWN_PIECES    = 1 # middle-clicked attacks, Guides
    FUTURE_MOVES    = 2 # future_guide for range after this move 
    PIECES          = 3 # pieces
    ACTIVE          = 4 # active_piece
    GUIDE           = 7 # move_guide for this move
    GHOST           = 8 # ghost

class Piece(Renderable):
    def __init__(self, game, layer, name, color, loc):
        super().__init__(game, layer)
        self.name, self.color, self.loc = name, color, loc
        self.r, self.sprite = Constants.RADIUS[name], Constants.SPRITE[color, name] if not game.headless else None
        self.sign = {Constants.BLACK:1, Constants.WHITE:-1}[color]
        self.GEToutline_color = lambda g: threatened_color if any(self in p.threatening for p in g.shown) or (g.active_piece and self in g.ghost.threatening) else {Constants.WHITE:white_outline_color,Constants.BLACK:black_outline_color}[self.color]

    def render(self, color=None):
        pygame.draw.circle(self.game.screen, color or capture_color if self in self.game.capture else blocking_color if self in self.game.blocking else {Constants.WHITE:white_color,Constants.BLACK:black_color}[self.color], self.game.pixel(self.loc), int(self.r*self.game.scale))
        pygame.draw.circle(self.game.screen, self.outline_color, self.game.pixel(self.loc), int(self.r*self.game.scale), 2)
        self.game.screen.blit(self.sprite, (lambda x,y:(x-24,y-27))(*self.game.pixel(self.loc)))

    def update_threatening_cache(self, pieces):
        self.threatening_cache = self.capturable(pieces)
        self.threatening = self.threatening_cache

class Runner(Piece):
    def __init__(self, game, name, color, loc, dirs):
        super().__init__(game, Layers.PIECES, name, color, loc)
        self.dirs = dirs

    def draw_guide(self, loc=None, color=guide_color, width=line_width, realWidth=False):
        [drawRay(self.game, color, loc or self.loc, d, width, realWidth) for d in self.dirs]

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)

        move = min((nearest_on_line(loc,self.loc,self.loc+p) for p in self.dirs), key = lambda p: p>>loc)

        intersecting = {p for p in pieces if blocks_segment(self.loc, self.r, move, p)}
        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return move, blocking, capture
    
    def in_range(self, piece, loc=None):
        # could I capture piece if there were no other pieces on the board?
        loc = loc or self.loc
        return any(blocks_ray(loc, self.r, dir, piece) for dir in self.dirs)

    def capturable(self, pieces, loc=None):
        # which pieces can I capture?
        loc = loc or self.loc
        return [p for p in (min((p for p in pieces if p != self and blocks_ray(loc, self.r, dir, p)), key=lambda p: dist_to_capture(loc, self.r, dir, p), default=None) for dir in self.dirs) if p != None and p.color != self.color]



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
        pygame.draw.circle(self.game.screen, color, self.game.pixel(loc), int(self.game.scale*knight_dist+width/2), int(width))

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)

        move = nearest_on_circle(loc, self.loc, knight_dist)

        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}
        blocking = {p for p in pieces if p.color == self.color and move>>p.loc < (self.r+p.r)**2}
        
        return move, blocking, capture

    def in_range(self, piece, loc=None):
        # could I capture piece if there were no other pieces on the board?
        loc = loc or self.loc
        return blocks_circle(loc, self.r, knight_dist, piece)

    def capturable(self, pieces, loc=None):
        # which pieces can I capture?
        loc = loc or self.loc
        possible = [p for p in pieces if self.in_range(p, loc)]

        return[p for p in ((lambda overlapping: p if not overlapping else overlapping[0] if len(overlapping)==1 else None)([p for p in possible if p.loc>>tangency < (self.r+p.r)**2]) for p in possible for tangency in intersect_circles(loc, p.loc, knight_dist, self.r+p.r)) if p and p.color != self.color]


class King(Piece):
    __init__ = lambda self, game, color, loc: super().__init__(game, Layers.PIECES, Constants.KING, color, loc)

    def draw_guide(self, loc=None, color=guide_color, width=line_width, realWidth=False):
        loc = loc or self.loc
        [drawSegment(self.game, color, loc+d1, loc+d2, width, realWidth) for d1,d2 in king_deltas]

    def find_move(self, loc, pieces):
        # returns (Point move, [Piece] blocking, [Piece] capture)

        move = min((nearest_on_segment(loc,self.loc+d1,self.loc+d2) for d1,d2 in king_deltas),
                key = lambda p: p>>loc)

        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}
        blocking = {p for p in pieces if p.color == self.color and move>>p.loc < (self.r+p.r)**2}
        
        return move, blocking, capture

    def in_range(self, piece, loc=None):
        # could I capture piece if there were no other pieces on the board?
        loc = loc or self.loc
        return any(blocks_segment(loc+d1, self.r, loc+d2, piece) for d1, d2 in king_deltas)

    def capturable(self, pieces, loc=None):
        # which pieces can I capture?
        loc = loc or self.loc
        ans = []
        for d1, d2 in king_deltas:
            possible = [p for p in pieces if blocks_segment(loc+d1, self.r, loc+d2, p)]
            ans += [p for p in ((lambda overlapping: p if not trace(overlapping, tangency) else overlapping[0] if len(overlapping)==1 else None)([p for p in possible if p.loc>>tangency < (self.r+p.r)**2]) for p in possible for tangency in intersect_segment_circle(loc+d1, loc+d2, p.loc, self.r+p.r)) if p and p.color != self.color]

        return ans

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

        intersecting = {p for p in pieces if blocks_segment(self.loc, self.r, move, p)} - {self}
        capture = {p for p in pieces if p.color != self.color and move>>p.loc < (self.r+p.r)**2}

        if move.x == self.loc.x:
            blocking = intersecting | capture
            capture = {}
        elif capture:
            blocking = intersecting - capture
        else:
            blocking = intersecting | {self}

        return move, blocking, capture

    def in_range(self, piece, loc=None):
        # could I capture piece if there were no other pieces on the board?
        loc = loc or self.loc
        return any(blocks_segment(loc, self.r, loc+Point(d,self.sign), piece) for d in [1,-1])

    def capturable(self, pieces, loc=None):
        # which pieces can I capture?
        loc = loc or self.loc
        return [p for p in (min((p for p in pieces if p != self and blocks_segment(loc, self.r, loc+dir, p)), key=lambda p: dist_to_capture(loc, self.r, dir, p), default=None) for dir in [Point(1,self.sign),Point(-1,self.sign)]) if p != None and p.color != self.color]

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
        self.GETvisible = lambda g: self.piece in g.shown
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

class Ghost(Renderable):
    def __init__(self, game):
        super().__init__(game, Layers.GHOST)
        self.state = None
        self.GETr = lambda g: g.active_piece.r
        self.GETcolor = lambda g: g.active_piece.color
    def render(self):
        if self.game.active_piece:
            threatened = any(self in p.threatening for p in self.game.shown)
            if self.state != (self.game.scale, self.game.active_piece, threatened):
                self.state = self.game.scale, self.game.active_piece, threatened
                diameter = int(self.game.active_piece.r*2*self.game.scale)
                size = max(diameter, 60)
                self.surf = pygame.Surface((size, size)).convert_alpha(self.game.screen)
                self.surf.fill((0,0,0,0))
                pygame.draw.circle(self.surf, active_color, (size//2,size//2), diameter//2)
                if threatened: pygame.draw.circle(self.surf, threatened_color, (size//2,size//2), diameter//2, 2)
                self.surf.blit(self.game.active_piece.sprite, (size//2-25, size//2-25))
                self.surf.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
            self.game.screen.blit(self.surf,(lambda x,y:(x-self.surf.get_width()//2,y-self.surf.get_height()//2))(*self.game.pixel(self.loc)))

Constants.PIECE_CLASSES = {
        Constants.KING: King,
        Constants.QUEEN: Queen,
        Constants.ROOK: Rook,
        Constants.BISHOP: Bishop,
        Constants.KNIGHT: Knight,
        Constants.PAWN: Pawn
    }


class Chess(Game):
    make_initial_state = lambda self: ("white", [
        (Constants.ROOK,    Constants.BLACK, (-3.5,-3.5)),
        (Constants.KNIGHT,  Constants.BLACK, (-2.5,-3.5)),
        (Constants.BISHOP,  Constants.BLACK, (-1.5,-3.5)),
        (Constants.QUEEN,   Constants.BLACK, (-0.5,-3.5)),
        (Constants.KING,    Constants.BLACK, ( 0.5,-3.5)),
        (Constants.BISHOP,  Constants.BLACK, ( 1.5,-3.5)),
        (Constants.KNIGHT,  Constants.BLACK, ( 2.5,-3.5)),
        (Constants.ROOK,    Constants.BLACK, ( 3.5,-3.5)),
    ] + [
        (Constants.PAWN,    Constants.BLACK, (i+.5,-2.5)) for i in range(-4,4)

    ] + [
        (Constants.PAWN,    Constants.WHITE, (i+.5, 2.5)) for i in range(-4,4)
    ] + [
        (Constants.ROOK,    Constants.WHITE, (-3.5, 3.5)),
        (Constants.KNIGHT,  Constants.WHITE, (-2.5, 3.5)),
        (Constants.BISHOP,  Constants.WHITE, (-1.5, 3.5)),
        (Constants.QUEEN,   Constants.WHITE, (-0.5, 3.5)),
        (Constants.KING,    Constants.WHITE, ( 0.5, 3.5)),
        (Constants.BISHOP,  Constants.WHITE, ( 1.5, 3.5)),
        (Constants.KNIGHT,  Constants.WHITE, ( 2.5, 3.5)),
        (Constants.ROOK,    Constants.WHITE, ( 3.5, 3.5)),
    ])

    teams = ['white', 'black']
    
    def __init__(self,**kwargs):
        super().__init__(name='continuous chess', **kwargs)
        if not self.headless:
            Constants.SPRITE = {(c,p):pygame.image.load('Sprites/{}{}.png'.format(c,p)).convert_alpha(self.screen) for c in Constants.COLORS for p in Constants.PIECES}
        self.save_state = lambda: (self.turn, [(p.name, p.color, p.loc.coords) for p in self.layers[Layers.PIECES]])
        self.load_state = lambda state: (setattr(self, 'turn', state[0]), (lambda pieces: (
            self.clearLayer(Layers.PIECES),
            [Constants.PIECE_CLASSES[name](self,color,Point(*loc)) for name, color, loc in pieces],
            self.clearLayer(Layers.SHOWN_PIECES),
            [Guide(self,Layers.SHOWN_PIECES,p,{Constants.WHITE:bg_white_guide_color, Constants.BLACK:bg_black_guide_color}[p.color]) for p in self.layers[Layers.PIECES]],
            setattr(self, 'active_piece', None),
            setattr(self, 'shown', []),
            setattr(self, 'capture', []),
            setattr(self, 'blocking', []),
        ))(state[1]))

        self.next_turn = lambda: {'white':'black', 'black':'white'}[self.turn]
        
        self.reset_state()

        self.process = lambda : updateMove(self)

        self.future_guide = Guide(self,Layers.FUTURE_MOVES,None, future_guide_color)
        self.future_guide.GETvisible = lambda game: self.active_piece != None


        ActivePiece(self)

        self.move_guide = Guide(self, Layers.GUIDE, None, thick=False)
        self.move_guide.GETvisible = lambda g: g.active_piece != None

        self.ghost = Ghost(self)
        self.ghost.threatening = []

        ScreenBorder(self, Layers.OUTLINE, outline_color, 12)
        self.turn_indicator =  ScreenBorder(self, Layers.TURN_INDICATOR, None, 10)
        self.turn_indicator.GETcolor = lambda g: turn_indicator_color[g.turn]

        self.click[1] = lambda e: self.attemptMove({"player":self.active_piece.color, "selected":self.active_piece.loc.coords, "location":self.point(*e.pos).coords}) if self.active_piece else selectPiece(self, self.point(*e.pos))
        self.click[2] = lambda e: toggleShown(self, self.point(*e.pos))
        self.drag[-1] = lambda e: setattr(self, 'rawMousePos', e.pos)
        
        self.keyPress[self.keys.cancel]         = lambda e: (setattr(self,'active_piece',None), [p.update_threatening_cache(self.layers[Layers.PIECES]) for p in self.shown])

    def attemptMove(self, move):
        """a move contains whose turn, a location that is being picked up, and a location that is being placed."""
        print("attempting move \n"+str(move))
        if not self.turn == move["player"]:
            return False
        selected_loc = Point(*move["selected"])
        self.active_piece = next(p for p in self.layers[Layers.PIECES] if selected_loc>>p.loc < p.r**2)
        #selectPiece(self, move["selected"])
        return attemptMove(self, move["location"])

def attemptMove(game, mouse_pos):
    mouse_pos = Point(*mouse_pos)
    pos, blocking, capture = game.active_piece.find_move(mouse_pos, game.layers[Layers.PIECES])

    if not blocking and len(capture)<2: # move is legal
        game.record_state()
        
        game.shown = []

        game.active_piece.loc = pos
        for piece in capture:
            game.layers[Layers.PIECES].remove(piece)

        if isinstance(game.active_piece, Pawn) and abs(game.active_piece.loc.y)>=3.5: # pawn promotes
            Guide(game, Layers.SHOWN_PIECES, Queen(game, game.active_piece.color, game.active_piece.loc), {Constants.WHITE:bg_white_guide_color, Constants.BLACK:bg_black_guide_color}[game.active_piece.color])
            game.layers[Layers.PIECES].remove(game.active_piece)

        game.active_piece = None
        updateMove(game)
        game.turn = game.next_turn()
        return True
    return False

def selectPiece(game, mouse_pos):
    clicked_on = [p for p in game.layers[Layers.PIECES] if mouse_pos>>p.loc < p.r**2]
    if len(clicked_on) > 1:
        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
    elif clicked_on and clicked_on[0].color==game.turn:
        game.active_piece = clicked_on[0]
        game.move_guide.piece = game.active_piece
        game.future_guide.piece = game.active_piece
        updateMove(game)
        game.move_guide.piece = game.active_piece
        game.move_guide.loc = game.active_piece.loc
        game.future_guide.piece = game.active_piece
        for p in game.shown:
            p.update_threatening_cache([p for p in game.layers[Layers.PIECES] if p != game.active_piece])

def updateMove(game):
    pos = game.mousePos()
    if game.active_piece:
        move, game.blocking, game.capture = game.active_piece.find_move(pos, game.layers[Layers.PIECES])
        game.future_guide.loc = move
        game.ghost.loc = move
        for p in game.shown: 
            if p.in_range(game.ghost) or any(p.in_range(cap) for cap in game.capture):
                p.threatening = p.capturable([p for p in game.layers[Layers.PIECES] if p != game.active_piece and p not in game.capture] + [game.ghost])
            else:
                p.threatening = p.threatening_cache
        game.ghost.threatening = game.active_piece.capturable([p for p in game.layers[Layers.PIECES] if p != game.active_piece and p not in game.capture], game.ghost.loc)
    else:
        game.blocking, game.capture = [], []

def toggleShown(game, mouse_pos):
    clicked_on = [p for p in game.layers[Layers.PIECES] if mouse_pos>>p.loc < p.r**2]
    if len(clicked_on) > 1:
        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
    elif clicked_on:
        p = clicked_on[0]
        if p in game.shown: game.shown.remove(p)
        else:
            game.shown.append(p)
            p.update_threatening_cache([p for p in game.layers[Layers.PIECES] if p != game.active_piece])


if __name__=="__main__":
    run_local(Chess)
