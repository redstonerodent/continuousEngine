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

<<<<<<< Updated upstream
solution = puzzle4
=======
maybe_broken = [
    [1,1,1,1],
    [4,1,3,1],
    [1,1,1,1],
    [1,1,1,3],
]

solution = maybe_broken
>>>>>>> Stashed changes

# size of instance
n=len(solution)


line_color = (0,0,0)
line_outside_color = (170, 220, 235)
text_color = (0,0,0)
highlight_color = (150, 200, 255)
win_color = (0, 255, 0)
debug_color = (255,0,0)

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


class Sky(Game):
    make_initial_state = lambda self: [[0]*n for _ in range(n)]

    def makeDot(self, c):
        dot = pygame.Surface((2*dot_rad,)*2).convert_alpha(self.screen)
        dot.fill((0,0,0,0))
        pygame.draw.circle(dot, countColor(c), (dot_rad,)*2, dot_rad)
        write(dot, self.font, c, dot_rad, dot_rad, text_color)
        return dot

    def __init__(self, **kwargs):
        super().__init__(center=Point(n/2,n/2), spread=n, name='sky', **kwargs)


        self.addDot = lambda x,y: CachedImg(self, Layers.TRIALS, countVisible(solution,x,y), self.makeDot, Point(x, y)) if any([x<0,y<0,x>n,y>n]) else None

        self.save_state = lambda: [[guess[i][j].text for j in range(n)] for i in range(n)]
        self.load_state = lambda s: [setattr(guess[i][j],'text',s[i][j]) for i in range(n) for j in range(n)]

        self.winSquare = Rectangle(self, Layers.SQUARES, win_color, Point(0,0), n,n)
        self.winSquare.GETvisible = lambda self: self.save_state() == solution
        self.selector = Rectangle(self, Layers.SQUARES, highlight_color, Point(0,0), 1,1)
        self.grid = InfiniteGrid(self, Layers.GRIDS, line_outside_color, 1)
        self.grid.visible = False
        Grid(self, Layers.GRIDS, line_color, Point(0,0) ,n)

        guess = [[Text(self, Layers.GUESS, text_color,self.font,0, Point(i+.5,j+.5)) for j in range(n)] for i in range(n)]
        [(lambda t:(setattr(t,'GETvisible',lambda _:t.text)))(guess[i][j]) for i in range(n) for j in range(n)]

        # left click
        self.click[1] = lambda e: (lambda x,y:(setattr(self.selector, 'loc', Point(int(x), int(y))) if 0<=x<=n and 0<=y<=n else self.addDot(x,y)))(*self.point(*e.pos))
        # middle click and drag
        self.drag[1] = lambda e: (lambda x,y:self.addDot(x,y))(*self.point(*e.pos))
        self.numKey = lambda c: (self.record_state(), setattr(guess[int(self.selector.loc.x)][int(self.selector.loc.y)],'text',c))


        # debug
        # show all visible skyscapers
        if 1:
            [(lambda i,j: setattr(
                Rectangle(self, Layers.SQUARES, win_color, Point(i+.1, j+.1), .8, .8),'GETvisible',
                lambda g: Layers.TRIALS in g.layers and g.layers[Layers.TRIALS] and (lambda t: (i,j) in visible(solution,*t.loc))(g.layers[Layers.TRIALS][-1])
                ))(i,j) 
            for j in range(n) for i in range(n)]

        # show skyscrapers in line
        if 1:
            [(lambda i,j: setattr(
                Disk(self, Layers.SQUARES, debug_color, Point(i+.5, j+.5), .3),'GETvisible',
                lambda g: Layers.TRIALS in g.layers and g.layers[Layers.TRIALS] and (lambda t: (i,j) in map(lambda x:x[1],posVisible(*t.loc, *g.selector.loc)))(g.layers[Layers.TRIALS][-1])
                ))(i,j) 
            for j in range(n) for i in range(n)]
        # show visible skyscrapers in line
        if 1:
            [(lambda i,j: setattr(
                Disk(self, Layers.SQUARES, highlight_color, Point(i+.5, j+.5), .2),'GETvisible',
                lambda g: Layers.TRIALS in g.layers and g.layers[Layers.TRIALS] and (lambda t: (i,j) in visibleInDir(solution,posVisible(*t.loc, *g.selector.loc)))(g.layers[Layers.TRIALS][-1])
                ))(i,j) 
            for j in range(n) for i in range(n)]

        # draw line to top right corner of selected square
        if 1:
            L = Line(self, Layers.TRIALS+1, debug_color, None, None)
            L.GETp1 = lambda g:g.selector.loc
            L.GETp2 = lambda g:g.layers[Layers.TRIALS][-1].loc
            L.GETvisible = lambda g:Layers.TRIALS in g.layers and g.layers[Layers.TRIALS]

        # show actual heights
        if 1:
            [[Text(self, Layers.GUESS, text_color,self.font,solution[i][j], Point(i+.25,j+.25)) for j in range(n)] for i in range(n)]

        allow_out_of_range = 1

        self.keyPress[self.keys.moveUp]         = lambda _: setattr(self.selector, 'loc', Point(self.selector.loc.x, (self.selector.loc.y-1)%(n+allow_out_of_range)))
        self.keyPress[self.keys.moveDown]       = lambda _: setattr(self.selector, 'loc', Point(self.selector.loc.x, (self.selector.loc.y+1)%(n+allow_out_of_range)))
        self.keyPress[self.keys.moveLeft]       = lambda _: setattr(self.selector, 'loc', Point((self.selector.loc.x-1)%(n+allow_out_of_range), self.selector.loc.y))
        self.keyPress[self.keys.moveRight]      = lambda _: setattr(self.selector, 'loc', Point((self.selector.loc.x+1)%(n+allow_out_of_range), self.selector.loc.y))
        self.keyPress[self.keys.delete]         = lambda _: (self.record_state(), setattr(guess[int(self.selector.loc.x)][int(self.selector.loc.y)],'text',0))
        self.keyPress[self.keys.resetColors]    = lambda _: self.clearCache()
        self.keyPress[self.keys.clearTrials]    = lambda _: self.clearLayer(Layers.TRIALS)
        self.keyPress[self.keys.toggleGrid]     = lambda _: setattr(self.grid,'visible',not self.grid.visible)


if __name__=="__main__":
    pygame.init()
    run_local(Sky)