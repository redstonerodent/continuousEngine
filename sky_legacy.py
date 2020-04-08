import sys, pygame, random
from math import floor, ceil
pygame.init()


# solution - latin square
# transposed relative to graphics!
curved = [
    [4,1,3,1],
    [1,1,1,1],
    [1,1,1,3],
    [1,1,1,1]
]

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

guess = [[0]*n for _ in range(n)]

# set up screen
size = width, height = 1000, 1000
screen = pygame.display.set_mode(size)
font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)

x_min, x_max, y_min, y_max = lambda:-x_offset, lambda:width/scale-x_offset, lambda:-y_offset, lambda:width/scale-y_offset

# colors
bg_color = (245,245,235)
line_color = (0,0,0)
line_outside_color = (170, 220, 235)
text_color = (0,0,0)
highlight_color = (150, 200, 255)
win_color = (0, 255, 0)
debug_color = (255,0,0)

# convert between pixels on screen and points in abstract game space
scale_home = 100
x_offset_home, y_offset_home = 5-n/2, 5-n/2

scale = scale_home
x_offset, y_offset = x_offset_home, y_offset_home
pixel = lambda x,y: (int((x+x_offset)*scale), int((y+y_offset)*scale))
point = lambda x,y: (x/scale-x_offset, y/scale-y_offset)

def zoom(factor, x, y):
    global scale, x_offset, y_offset, ghost
    scale, x_offset, y_offset = scale/factor, (x_offset+x)*factor-x, y_offset*factor + y*(factor-1)


# size to draw circles
dot_rad = 20


def write(screen, font, text, x, y, color): # x and y are pixel values
    text = str(text)
    written = font.render(text,True,color)
    width, height = font.size(text)
    screen.blit(written, (x-width//2, y-height//2))

# places line (x,y)-(lx,ly) hits grid lines. set of tuples (x,y).
crossings = lambda x, y, lx, ly: ({(float(u),y-(y-ly)*(x-u)/(x-lx)) for u in range(n+1) if 0 <= y*abs(x-lx)-(y-ly)*(x-u)*(-1)**(x<lx) <= n*abs(x-lx)} if x-lx else set()) | ({(x-(x-lx)*(y-v)/(y-ly),float(v)) for v in range(n+1) if 0 <= x*abs(y-ly)-(x-lx)*(y-v)*(-1)**(y<ly) <= n*abs(y-ly)} if y-ly else set())

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
# currently ignores number and picks random color; this is fine because colors get cached
countColor = lambda c: tuple(random.randint(0,255) for _ in range(3))

# cache to reduce rendering & reuse color for the same number
dot_cache = {}
def draw_dot(screen, font, count, x, y):
    if count not in dot_cache:
        # print('updating cache: %s'%count)
        dot = pygame.Surface((2*dot_rad,)*2).convert_alpha(screen)
        dot.fill((0,0,0,0))
        pygame.draw.circle(dot, countColor(count), (dot_rad,)*2, dot_rad)
        write(dot, font, count, dot_rad, dot_rad, text_color)
        dot_cache[count] = dot
    screen.blit(dot_cache[count], (x-dot_rad, y-dot_rad))


class Trial:
    def __init__(self, x, y, sol):
        self.x, self.y = x, y
        self.count = countVisible(sol, x, y)


# list of trials
trials = []

# for entering solution
fi, fj = 0, 0

# undoing edits to guess
history = []
future = []

save_state = lambda s:[i.copy() for i in s]

while 1:

    # take events from queue until empty
    event = pygame.event.wait()
    while event:
        if event.type == pygame.QUIT: sys.exit()

        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1: # left click
                mouse_x,mouse_y = point(*event.pos)
                if 0 < mouse_x < n and 0 < mouse_y < n: # inside city: select square
                    fi, fj = int(mouse_x), int(mouse_y)
                else: # outside city: run trial
                    trials.append(Trial(mouse_x,mouse_y, solution))
                    # print(mouse_x,mouse_y)

            elif event.button == 4: # scroll up: zoom in
                if scale<500:
                    zoom(.8,*point(*event.pos))
            elif event.button == 5: # scroll down: zoom out
                if scale>2:
                    zoom(1.25,*point(*event.pos))

        elif event.type == pygame.MOUSEMOTION:
            if event.buttons[1]:  # hold middle click: more trials
                mouse_x,mouse_y = point(*event.pos)
                if not (0 < mouse_x < n and 0 < mouse_y < n):
                    trials.append(Trial(mouse_x,mouse_y,solution))
            if event.buttons[2]:  # right click and drag: pan
                x_offset += event.rel[0]/scale
                y_offset += event.rel[1]/scale

        elif event.type == pygame.KEYDOWN:
            if event.key == 112: # p: restart
                history.append(save_state(guess))
                future = []
                guess = [[0]*n for _ in range(n)]
            elif event.key == 59: # ;: undo
                if history:
                    future.append(save_state(guess))
                    guess = history.pop()
            elif event.key == 113: # q: redo
                if future:
                    history.append(save_state(guess))
                    guess = future.pop()

            elif event.key == 270: # +: zoom in
                if scale<500:
                    zoom(.8, 0, 0)
            elif event.key == 269: # -: zoom out
                if scale>2:
                    zoom(1.25, 0, 0)
            elif event.key in {44,111,97,101}: # ,aoe: pan
                x_offset += (event.key==97)-(event.key==101)
                y_offset += (event.key==44)-(event.key==111)
            elif event.key == 278: # home: reset zoom and pan
                scale, x_offset, y_offset = scale_home, x_offset_home, y_offset_home

            elif 273 <= event.key <= 276: # arrow keys: move selected
                fi -= (event.key==276)-(event.key==275)
                fi %= n
                fj -= (event.key==273)-(event.key==274)
                fj %= n
            elif 49 <= event.key <= 57: # numbers: set selected
                history.append(save_state(guess))
                future = []
                guess[fi][fj] = event.key-48
            elif event.key == 8: # backspace: remove number
                history.append(save_state(guess))
                future = []
                guess[fi][fj] = 0
            elif event.key == 106: # j: clear cache, reset colors
                dot_cache = {}
            elif event.key == 27: # escape: clear trials
                trials = []
            elif event.key == 32: # space: debug
                pass
            else: print(event.key)
        # next event from queue
        event = pygame.event.poll()
        
    # printing screen
    screen.fill(bg_color)

    # debug
    if trials:
        # show skyscrapers in line
        if 0:
            for d,(i,j) in posVisible(trials[-1].x, trials[-1].y, fi,fj):
                pygame.draw.polygon(screen, win_color, list(map(pixel,[i,i+1,i+1,i],[j,j,j+1,j+1])))
                if 0: # show distance to crossings
                    write(screen, font, d, *pixel(i+1/2,j+1/2), text_color)

        # show all visible skyscrapers
        if 0:
            for (i,j) in visible(solution, trials[-1].x, trials[-1].y):
                pygame.draw.polygon(screen, win_color, list(map(pixel,[i,i+1,i+1,i],[j,j,j+1,j+1])))


        # show line, crossings
        if 0:
            pygame.draw.line(screen, debug_color, pixel(trials[-1].x, trials[-1].y), pixel(fi, fj))
            print(crossings(trials[-1].x, trials[-1].y, fi,fj))
            print(posVisible(trials[-1].x, trials[-1].y, fi,fj))
            for u,v in crossings(trials[-1].x, trials[-1].y, fi,fj):
                pygame.draw.circle(screen, debug_color, pixel(u,v), 10)


    # winning
    if guess == solution:
        pygame.draw.polygon(screen, win_color, list(map(pixel,[0,n,n,0],[0,0,n,n])))

    # selected square
    pygame.draw.polygon(screen, highlight_color, list(map(pixel,[fi,fi+1,fi+1,fi],[fj,fj,fj+1,fj+1])))
    
        # show visible skyscrapers in line
    if trials:
        if 0:
            for i,j in visibleInDir(solution,posVisible(trials[-1].x, trials[-1].y, fi,fj)):
                pygame.draw.circle(screen, debug_color, pixel(i+1/2,j+1/2),15)

    # numbers
    for i in range(n):
        for j in range(n):
            if guess[i][j]: write(screen, font, guess[i][j], *pixel(i+1/2, j+1/2), text_color)


    # show actual heights
    if 0:
        for i in range(n):
            for j in range(n):
                write(screen, font, solution[i][j], *pixel(i+1/4, j+1/4), text_color)



    # grid outside city
    for x in range(floor(x_min()),ceil(x_max())):
        pygame.draw.line(screen, line_outside_color, pixel(x,y_min()), pixel(x,y_max()))
    for y in range(floor(y_min()),ceil(y_max())):
        pygame.draw.line(screen, line_outside_color, pixel(x_min(),y), pixel(x_max(),y))

    # city grid
    for i in range(n+1):
        pygame.draw.line(screen, line_color, pixel(0,i), pixel(n,i))
        pygame.draw.line(screen, line_color, pixel(i,0), pixel(i,n))


    # trials
    for t in trials:
        if x_min() - dot_rad <= t.x <= x_max() + dot_rad and y_min() - dot_rad <= t.y <= y_max() + dot_rad:
            draw_dot(screen, font, t.count, *pixel(t.x,t.y))

    pygame.display.flip()
