from continuousEngine import *
from math import floor, ceil
import random

# solution - latin square
# transposed relative to graphics!
puzzle4 = [
    [1,3,2,4],
    [3,4,1,2],
    [4,2,3,1],
    [2,1,4,3]
]

puzzle6 = [
    [6,2,1,5,3,4],
    [3,6,2,1,4,5],
    [4,5,3,6,2,1],
    [5,1,4,3,6,2],
    [1,4,6,2,5,3],
    [2,3,5,4,1,6]
]

solution = puzzle4

# size of instance
n=len(solution)


line_color = (0,0,0)
line_outside_color = (170, 220, 235)
text_color = (0,0,0)
highlight_color = (150, 200, 255)
win_color = (0, 255, 0)
debug_color = (255,0,0)

font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)

# size to draw circles
dot_rad = 20

#### functions implementing the skyscrapers mechanic ####

# locations line (x,y)-(lx,ly) hits grid lines. set of tuples (x,y).
crossings = lambda x, y, lx, ly: ({(float(u),y-(y-ly)*(x-u)/(x-lx)) for u in range(n+1)} if x-lx else set()) | ({(x-(x-lx)*(y-v)/(y-ly),float(v)) for v in range(n+1)} if y-ly else set())
# combat floating point errors
epsilon = 1/10**10 
purify = lambda n: floor(n) if abs(n-floor(n))<epsilon else ceil(n) if abs(n-ceil(n))<epsilon else n
purifiedcrossings = lambda *xs:{(purify(x),purify(y)) for x,y in crossings(*xs)}
# skyscrapers in line (x,y)-(lx,ly) with distance, closest to farthest. list of tuples (d,(i,j))
posVisible = lambda x,y,lx,ly:[(d,(i,j)) for d,(i,j) in sorted((((x-u)**2+(y-v)**2)**.5,(floor(u+epsilon) if lx>x else ceil(u-1-epsilon), floor(v+epsilon) if ly>y else ceil(v-1-epsilon))) for u,v in purifiedcrossings(x,y,lx,ly)) if 0<=i<n and 0<=j<n]
# set of visible skyscrapers in pos [output of posVisible]. set of tuples {(i,j)}
visibleInDir = lambda solution, pos, slope=0: (lambda d,ij: (lambda s: visibleInDir(solution, pos[1:], s)|{ij} if s>slope else visibleInDir(solution, pos[1:], slope)) (solution[ij[0]][ij[1]]/d) if d else {ij})(*pos[0]) if pos else set()
union = lambda ss: ss[0]|union(ss[1:]) if ss else set()
# set of visible skyscrapers. set of tuples (i,j)
visible = lambda solution, x, y: union([visibleInDir(solution, posVisible(x, y, i, j)) for i in range(n+1) for j in range(n+1)])
# number of visible skyscrapers
countVisible = lambda solution, x, y: len(visible(solution,x,y))
# color based on number
# ignores number and picks random color, but could be changed to rainbow or something
countColor = lambda c: tuple(random.randint(0,255) for _ in range(3))

# layers:

class Layers:
    SQUARES = 0       # selector, win square
    GRIDS   = 2       # grids
    GUESS   = 3       # guess (numbers entered)
    TRIALS  = 5       # trials

def makeDot(c):
    dot = pygame.Surface((2*dot_rad,)*2).convert_alpha(game.screen)
    dot.fill((0,0,0,0))
    pygame.draw.circle(dot, countColor(c), (dot_rad,)*2, dot_rad)
    write(dot, font, c, dot_rad, dot_rad, text_color)
    return dot
addDot = lambda x,y: CachedImg(game, Layers.TRIALS, countVisible(solution,x,y), makeDot, (x, y)) if any([x<0,y<0,x>n,y>n]) else None
    
game = Game([[0]*n for _ in range(n)], center=(n/2,n/2))

game.save_state = lambda: [[guess[i][j].text for j in range(n)] for i in range(n)]
game.load_state = lambda s: [setattr(guess[i][j],'text',s[i][j]) for i in range(n) for j in range(n)]

winSquare = Rectangle(game, Layers.SQUARES, win_color,0,0,n,n)
winSquare.GETvisible = lambda game: game.save_state() == solution
selector = Rectangle(game, Layers.SQUARES, highlight_color,0,0,1,1)
game.grid = InfiniteGrid(game, Layers.GRIDS, line_outside_color,1)
game.grid.visible = False
Grid(game, Layers.GRIDS, line_color,0,0,n)

guess = [[Text(game, Layers.GUESS, text_color,font,0,i+.5,j+.5) for j in range(n)] for i in range(n)]
[(lambda t:(setattr(t,'GETvisible',lambda _:t.text)))(guess[i][j]) for i in range(n) for j in range(n)]

# left click
game.click[1] = lambda e: (lambda x,y:(setattr(selector,'x',int(x)),setattr(selector,'y',int(y))) if 0<=x<=n and 0<=y<=n else addDot(x,y))(*game.point(*e.pos))
# middle click and drag
game.drag[1] = lambda e: (lambda x,y:addDot(x,y))(*game.point(*e.pos))
game.numKey = lambda c: (game.record_state(), setattr(guess[selector.x][selector.y],'text',c))


# debug
# show all visible skyscapers
if 0:
    [(lambda i,j: setattr(
        Rectangle(game, Layers.SQUARES, win_color, i+.1, j+.1, .8, .8),'GETvisible',
        lambda game: Layers.TRIALS in game.layers and game.layers[Layers.TRIALS] and (lambda t: (i,j) in visible(solution,t.x,t.y))(game.layers[Layers.TRIALS][-1])
        ))(i,j) 
    for j in range(n) for i in range(n)]

# show skyscrapers in line
if 0:
    [(lambda i,j: setattr(
        Disk(game, Layers.SQUARES, debug_color, i+.5, j+.5, .3),'GETvisible',
        lambda game: Layers.TRIALS in game.layers and game.layers[Layers.TRIALS] and (lambda t: (i,j) in map(lambda x:x[1],posVisible(t.x,t.y,selector.x,selector.y)))(game.layers[Layers.TRIALS][-1])
        ))(i,j) 
    for j in range(n) for i in range(n)]
# show visible skyscrapers in line
if 0:
    [(lambda i,j: setattr(
        Disk(game, Layers.SQUARES, highlight_color, i+.5, j+.5, .2),'GETvisible',
        lambda game: Layers.TRIALS in game.layers and game.layers[Layers.TRIALS] and (lambda t: (i,j) in visibleInDir(solution,posVisible(t.x,t.y,selector.x,selector.y)))(game.layers[Layers.TRIALS][-1])
        ))(i,j) 
    for j in range(n) for i in range(n)]

# draw line to top right corner of selected square
if 0:
    [(lambda i,j: 
        (lambda L:(
            setattr(L,'GETvisible',
                lambda game: Layers.TRIALS in game.layers and game.layers[Layers.TRIALS] and (i,j) == (selector.x, selector.y)),
            setattr(L,'GETp2',
                lambda game: (lambda t:(t.x,t.y))((game.layers[Layers.TRIALS][-1])))
        ))
        (Line(game, Layers.TRIALS+1, debug_color, (i,j), None)))
        (i,j)
    for j in range(n+1) for i in range(n+1)]

# show actual heights
if 0:
    [[Text(game, Layers.GUESS, text_color,font,solution[i][j],i+.25,j+.25) for j in range(n)] for i in range(n)]

game.keys.moveUp = pygame.K_UP
game.keys.moveDown = pygame.K_DOWN
game.keys.moveLeft = pygame.K_LEFT
game.keys.moveRight = pygame.K_RIGHT
game.keys.delete = pygame.K_BACKSPACE
game.keys.resetColors = pygame.K_j
game.keys.clearTrials = pygame.K_ESCAPE
game.keys.toggleGrid = pygame.K_i

game.keyPress[game.keys.moveUp]         = lambda _: setattr(selector,'y',(selector.y-1)%n)
game.keyPress[game.keys.moveDown]       = lambda _: setattr(selector,'y',(selector.y+1)%n)
game.keyPress[game.keys.moveLeft]       = lambda _: setattr(selector,'x',(selector.x-1)%n)
game.keyPress[game.keys.moveRight]      = lambda _: setattr(selector,'x',(selector.x+1)%n)
game.keyPress[game.keys.delete]         = lambda _: (game.record_state(), setattr(guess[selector.x][selector.y],'text',0))
game.keyPress[game.keys.resetColors]    = lambda _: game.clearCache()
game.keyPress[game.keys.clearTrials]    = lambda _: game.clearLayer(Layers.TRIALS)
game.keyPress[game.keys.toggleGrid]     = lambda _: setattr(game.grid,'visible',not game.grid.visible)

while 1: game.update()