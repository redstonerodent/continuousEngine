import sys, pygame
pygame.init()

size = width, height = 1000, 1000
screen = pygame.display.set_mode(size)

x_min, x_max, y_min, y_max = lambda:-x_offset, lambda:width/scale-x_offset, lambda:-y_offset, lambda:width/scale-y_offset

bg_color = (245,245,235)

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

line_width = 1.5
# diagonal_line_width = 4 # diagonal lines look thinner
alpha = 100


# for checking legality, etc.
dist_sq = lambda p1,p2: sum((p1[i]-p2[i])**2 for i in [0,1])
snap_to_line = lambda p, l, dl: ((p[0]*dl[0]**2+l[0]*dl[1]**2+(p[1]-l[1])*dl[0]*dl[1]) / (dl[0]**2+dl[1]**2) , (p[1]*dl[1]**2+l[1]*dl[0]**2+(p[0]-l[0])*dl[0]*dl[1]) / (dl[0]**2+dl[1]**2))
blocks_line = lambda piece, target, blocker: False if target==(piece.x,piece.y) else (lambda px,py:(piece.x<px<target[0] or piece.x>px>target[0] or piece.y<py<target[1] or piece.y>py>target[1]) and dist_sq((px,py),(blocker.x,blocker.y))<(piece.r+blocker.r)**2)(*snap_to_line((blocker.x,blocker.y),(piece.x,piece.y),(target[0]-piece.x,target[1]-piece.y)))
snap_to_segment = lambda p,l1,l2: (lambda x,y: l2 if l1[0]>l2[0]>x or l1[0]<l2[0]<x or l1[1]>l2[1]>y or l1[1]<l2[1]<y else l1 if l2[0]>l1[0]>x or l2[0]<l1[0]<x or l2[1]>l1[1]>y or l2[1]<l1[1]<y else (x,y)) (*snap_to_line(p,l1,(l2[0]-l1[0],l2[1]-l1[1])))

# convert between pixels on screen and points in abstract game space
scale = 100
x_offset, y_offset = 5, 5
pixel = lambda x,y: (int((x+x_offset)*scale), int((y+y_offset)*scale))
point = lambda x,y: (x/scale-x_offset, y/scale-y_offset)

# draws a line capped with semicircles; better than pygame.draw.line
def draw_line(screen, color, p1, p2, width):
    x1,y1 = pixel(*p1)
    x2,y2 = pixel(*p2)

    dx, dy = y2-y1, x1-x2

    dx, dy = int(dx*width/(dx**2+dy**2)**.5), int(dy*width/(dx**2+dy**2)**.5)

    pygame.draw.polygon(screen, color, [(x1+dx,y1+dy), (x1-dx,y1-dy), (x2-dx,y2-dy), (x2+dx,y2+dy)])
    pygame.draw.circle(screen, color, (x2,y2), int(width))
    pygame.draw.circle(screen, color, (x1,y1), int(width))

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

Constants.SPRITE = {(c,p):pygame.image.load('Sprites/{}{}.png'.format(c,p)).convert_alpha(screen) for c in Constants.COLORS for p in Constants.PIECES}



class Piece:
    def __init__(self, name, color, x, y):
        self.name, self.color, self.x, self.y = name, color, x, y
        self.r, self.sprite = Constants.RADIUS[name], Constants.SPRITE[color, name]
        self.sign = {Constants.BLACK:1, Constants.WHITE:-1}[color]
        
class Rook(Piece):
    __init__ = lambda self, color, x, y: super().__init__(Constants.ROOK, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width):
        x,y = x or self.x, y or self.y
        draw_line(screen, color, (x_min(), y), (x_max(), y), width)
        draw_line(screen, color, (x, y_min()), (x, y_max()), width)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_line((x,y),(self.x,self.y),p) for p in [(0,1),(1,0)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return (move_x,move_y), blocking, capture

class Bishop(Piece):
    __init__ = lambda self, color, x, y: super().__init__(Constants.BISHOP, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width):
        x,y = x or self.x, y or self.y
        draw_line(screen, color, (x_min()-2*self.r,y+x-x_min()+2*self.r), (x_max()+2*self.r,y+x-x_max()-2*self.r), width)
        draw_line(screen, color, (x_min()-2*self.r,y-x+x_min()-2*self.r), (x_max()+2*self.r,y-x+x_max()+2*self.r), width)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_line((x,y),(self.x,self.y),p) for p in [(1,1),(1,-1)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return (move_x,move_y), blocking, capture

class Queen(Piece):
    __init__ = lambda self, color, x, y: super().__init__(Constants.QUEEN, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width):
        x,y = x or self.x, y or self.y
        draw_line(screen, color, (x_min(), y), (x_max(), y), width)
        draw_line(screen, color, (x, y_min()), (x, y_max()), width)
        draw_line(screen, color, (x_min()-2*self.r,y+x-x_min()+2*self.r), (x_max()+2*self.r,y+x-x_max()-2*self.r), width)
        draw_line(screen, color, (x_min()-2*self.r,y-x+x_min()-2*self.r), (x_max()+2*self.r,y-x+x_max()+2*self.r), width)

    def find_move(self, x, y, pieces):
        # returns ((int move_x, int move_y), [Piece] blocking, [Piece] capture)

        move_x, move_y = min([snap_to_line((x,y),(self.x,self.y),p) for p in [(0,1),(1,0),(1,1),(1,-1)]], key = lambda p:dist_sq(p,(x,y)))

        intersecting = {p for p in pieces if blocks_line(self, (move_x,move_y), p) or dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        capture = {p for p in pieces if p.color != self.color and dist_sq((move_x,move_y),(p.x,p.y))<(self.r+p.r)**2}
        blocking = intersecting - capture - {self}

        return (move_x,move_y), blocking, capture

class Knight(Piece):
    __init__ = lambda self, color, x, y: super().__init__(Constants.KNIGHT, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width):
        x,y = x or self.x, y or self.y
        pygame.draw.circle(screen, color, pixel(x,y), int(scale*5**.5+width), int(2*width))
        # pygame.draw.circle(screen, color, pixel(x,y), int(scale*5**.5+width/2), line_width)

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
    __init__ = lambda self, color, x, y: super().__init__(Constants.KING, color, x, y)

    def draw_guide(self, x=None, y=None, color=guide_color, width=line_width):
        x,y = x or self.x, y or self.y
        for dx1,dy1,dx2,dy2 in [(1,1,1,-1),(1,-1,-1,-1),(-1,-1,-1,1),(-1,1,1,1)]:
            draw_line(screen, color, (x+dx1,y+dy1), (x+dx2,y+dy2), width)

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
    __init__ = lambda self, color, x, y: super().__init__(Constants.PAWN, color, x, y)

    def draw_guide(self, x=None, y=None, color=None, width=line_width):
        x,y = x or self.x, y or self.y
        if color==None:
            draw_line(screen, move_guide_color, (x, y), (x, y+self.sign*(1+(y==-2.5*self.sign))), width)
        draw_line(screen, color or capture_guide_color, (x, y), (x-1, y+self.sign), width)
        draw_line(screen, color or capture_guide_color, (x, y), (x+1, y+self.sign), width)
        

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




def draw_piece (piece, color, outline=None):
    pygame.draw.circle(screen, color, pixel(piece.x, piece.y), int(piece.r*scale))
    if outline:
        try:
            pygame.draw.circle(screen, outline, pixel(piece.x, piece.y), int(piece.r*scale), 1)
        except:
            pass
    screen.blit(piece.sprite, (lambda x,y:(x-24,y-27))(*pixel(piece.x, piece.y)))
        

# zoom out by factor
def zoom(factor, x, y):
    global scale, x_offset, y_offset, ghost
    scale, x_offset, y_offset = scale/factor, (x_offset+x)*factor-x, y_offset*factor + y*(factor-1)
    if active_piece:
        ghost = makeghost(active_piece)

# returns a surface with transparent piece on it
def makeghost(piece):
    diameter = int(piece.r*2*scale)
    size = max(diameter, 60)
    ghost = pygame.Surface((size, size)).convert_alpha(screen)
    ghost.fill((0,0,0,0))
    pygame.draw.circle(ghost, active_color, (size//2,size//2), diameter//2)
    ghost.blit(piece.sprite, (size//2-25, size//2-25))
    ghost.fill((255, 255, 255, alpha), None, pygame.BLEND_RGBA_MULT)
    return ghost


# for undo/redo
load_state = lambda pieces: [name(color, x, y) for name, color, x, y in pieces]
save_state = lambda pieces: [(type(p), p.color, p.x, p.y) for p in pieces]
history = []
future = []


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

# current game state
pieces = load_state(start_state)

# pieces you've middle clicked on to show attacks
shown_pieces = []


# piece you're moving
active_piece = None

while 1:

    # take events from queue until empty
    event = pygame.event.wait() # this used to be poll(); wait() should make it use less cpu by sleeping
    while event:
        if event.type == pygame.QUIT: sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # left click: attempt to select or move piece
                mouse_pos = point(*event.pos)
                if active_piece: # attempt to move active_piece
                    pos, blocking, capture = active_piece.find_move(*mouse_pos, pieces)

                    if not blocking and len(capture)<2: # move is legal
                        history.append(save_state(pieces))
                        future = []

                        active_piece.x, active_piece.y = pos
                        for piece in capture:
                            pieces.remove(piece)

                        if isinstance(active_piece, Pawn) and abs(active_piece.y)>=3.5: # pawn promotes
                            pieces.append(Queen(active_piece.color, active_piece.x, active_piece.y))
                            pieces.remove(active_piece)


                        active_piece = None
                        shown_pieces = []

                else: # set active_piece to the one you clicked on
                    clicked_on = [p for p in pieces if dist_sq(mouse_pos,(p.x,p.y)) < p.r**2]
                    if len(clicked_on) > 1:
                        raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
                    elif clicked_on:
                       active_piece = clicked_on[0]
                       target, blocking, capture = active_piece.find_move(*mouse_pos, pieces)
                       ghost = makeghost(active_piece)

            elif event.button == 2: # middle click: toggle showing piece moves
                clicked_on = [p for p in pieces if dist_sq(point(*event.pos),(p.x,p.y)) < p.r**2]
                if len(clicked_on) > 1:
                    raise ValueError('overlapping pieces: {}'.format(str(clicked_on)))
                elif clicked_on:
                    piece = clicked_on[0]
                    if piece in shown_pieces:
                        shown_pieces.remove(piece)
                    else:
                        shown_pieces.append(piece)

            elif event.button == 4: # scroll up: zoom in
                if scale<500:
                    zoom(.8,*point(*event.pos))
            elif event.button == 5: # scroll down: zoom out
                if scale>2:
                    zoom(1.25,*point(*event.pos))

        elif event.type == pygame.MOUSEMOTION:
            if active_piece: # update attempted move info
                target, blocking, capture = active_piece.find_move(*point(*event.pos), pieces)
            if event.buttons[2]:  # right click and drag: pan
                x_offset += event.rel[0]/scale
                y_offset += event.rel[1]/scale

        elif event.type == pygame.KEYDOWN:
            if event.key == 27: # escape: cancel active piece
                active_piece = None
            elif event.key == 112: # p: restart
                history.append(save_state(pieces))
                future = []
                pieces = load_state(start_state)
                active_piece = None
                shown_pieces = []
                scale = 100
                x_offset, y_offset = 5, 5
            elif event.key == 59: # ;: undo
                if history:
                    future.append(save_state(pieces))
                    pieces = load_state(history.pop())
                    shown_pieces = []
                    active_piece = None
            elif event.key == 113: # q: redo
                if future:
                    history.append(save_state(pieces))
                    pieces = load_state(future.pop())
                    shown_pieces = []
                    active_piece = None
            elif event.key == 270: # +: zoom in
                if scale<500:
                    zoom(.8, 0, 0)
            elif event.key == 269: # -: zoom out
                if scale>2:
                    zoom(1.25, 0, 0)
            elif 273 <= event.key <= 276: # arrow keys: pan
                x_offset += (event.key==276)-(event.key==275)
                y_offset += (event.key==273)-(event.key==274)
            elif event.key == 278: # home: reset zoom and pan
                scale, x_offset, y_offset = 100, 5, 5
            elif event.key == 32: # space: print game history
                print("   CURRENT STATE")
                print(save_state(pieces))
                print("   HISTORY")
                print(history)
                print("   FUTURE")
                print(future)
            else: print(event.key)
        # next event from queue
        event = pygame.event.poll()
        
    # printing screen
    screen.fill(bg_color)

    # draw attacked region for selected move
    if active_piece:
        active_piece.draw_guide(*target, future_guide_color, int(scale*active_piece.r))

    # draw attacked region for middle-clicked pieces
    for piece in shown_pieces:
        piece.draw_guide(color={Constants.WHITE:bg_white_guide_color, Constants.BLACK:bg_black_guide_color}[piece.color], width=int(scale*piece.r))

    # draw pieces
    for piece in pieces:
        draw_piece(piece, {Constants.WHITE:white_color,Constants.BLACK:black_color}[piece.color], {Constants.WHITE:white_outline_color,Constants.BLACK:black_outline_color}[piece.color])

    if active_piece:
        # selected piece green
        draw_piece(active_piece, active_color)
        for piece in capture: # would-capture pieces blue
            draw_piece(piece, capture_color)
        for piece in blocking: # blocking pieces red
            draw_piece(piece, blocking_color)

        # selected piece's moves
        active_piece.draw_guide()
        # ghost of current move
        screen.blit(ghost, (lambda x,y:(x-ghost.get_width()//2,y-ghost.get_height()//2))(*pixel(*target)))

    pygame.display.flip()