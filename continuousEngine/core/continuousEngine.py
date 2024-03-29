import sys, pygame, asyncio, threading, os, shutil, importlib, time, math
from continuousEngine.core.geometry import *

# current games, as {file: class_name}
ALL_GAMES = {
    'chess' : 'Chess',
    'reversi' : 'Reversi',
    'go' : 'Go',
    'jrap' : 'Jrap',
    'trans' : 'Trans',
    'quoridor': 'Quoridor',
    'sky' : 'Sky',
    'angle' : 'Angle',
    'kouchoku' : 'Kouchoku',
    'sample' : 'Sample',
    }

game_class = lambda name: getattr(importlib.import_module('continuousEngine.games.'+name), ALL_GAMES[name])

PACKAGEPATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

identity = lambda x:x

def run_local(game_class, args=[], kwargs={}):
    game_class(*args, **kwargs).run()

MONO_FONTS = [
    'ubuntu-mono',
    'dejavu-sans-mono',
    'monospace',
    'mono'
]

class Game:
    # def pygame_event_loop(self, loop):
    #     while 1:
    #         #print("waiting  for event",flush=True)
    #         #print("in Thread {}".format(threading.currentThread().getName()), flush=True)
    #         event=pygame.event.wait()
    #         #print("event!",flush=True)
    #         asyncio.run_coroutine_threadsafe(self.event_queue.put(event),loop)
    def run(self):
        #creates a window with the game, and the current thread becomes an event monitoring thread for the game
        #self.event_queue = asyncio.Queue()
        #asyncio.get_running_loop().run_in_executor(None, self.pygame_event_loop, asyncio.get_running_loop())
        while 1:
            #print("hi",flush=True)
            self.update()
    def __init__(self,backgroundColor=(245,245,235),center=Point(0,0), spread=5, headless=False, name='continuous engine', timectrl=None):
        self.headless = headless
        self.size = lambda: pygame.display.get_window_size()
        self.width = lambda: self.size()[0]
        self.height = lambda: self.size()[1]
        self.spread = spread
        self.center = center

        if not headless:
            self.screen = pygame.display.set_mode(flags=pygame.RESIZABLE)
            self.font = pygame.font.Font(pygame.font.match_font(MONO_FONTS),36)
            self.reset_view()
        else:
            self.font = None

        pygame.display.set_caption(name)

        # objects are assigned to 'layers' which give rendering order
        self.layerlist = []
        self.layers = {}
        Background(self, backgroundColor)

        self.handlers = {
            pygame.QUIT: lambda e: sys.exit(),
            pygame.MOUSEBUTTONDOWN: lambda e: self.click[e.button](e) if e.button in self.click else None,
            pygame.MOUSEMOTION: lambda e: ([self.drag[k](e) if k in self.drag else None for k in range(-1,3) if k<0 or e.buttons[k]]),
            pygame.KEYDOWN: lambda e: self.keyPress[e.key](e) if e.key in self.keyPress else self.numKey((e.key%1073741864-8)%10) if pygame.K_KP_1<=e.key<=pygame.K_KP_0 or pygame.K_0<=e.key<=pygame.K_9 else None,
            pygame.VIDEORESIZE: lambda e: (setattr(self, 'needViewChange', True), setattr(self, 'needResize', True)),
        }

        self.panDist = 100
        self.zoomFactor = .8
        self.scale_min = 2
        self.scale_max = 500

        self.click = {
            4: lambda e: self.zoom(self.zoomFactor, *self.point(*e.pos)),
            5: lambda e: self.zoom(1/self.zoomFactor, *self.point(*e.pos)),
        }

        keysdict = {}

        with open(os.path.join(PACKAGEPATH,'config.default')) as f:
            for line in f:
                if line[0] not in "#\n":
                    (lambda k,v: keysdict.__setitem__(k, getattr(pygame, 'K_'+v)))(*line.split())


        if not os.path.exists(os.path.join(PACKAGEPATH,'config')):
            shutil.copy(os.path.join(PACKAGEPATH,'config.default'), os.path.join(PACKAGEPATH,'config'))


        with open(os.path.join(PACKAGEPATH,'config')) as f:
            for line in f:
                if line[0] not in "#\n":
                    (lambda k,v: keysdict.__setitem__(k, getattr(pygame, 'K_'+v)))(*line.split())

        self.keys = type('',(),keysdict)

        self.keyPress = {
            self.keys.zoomIn        : lambda e: self.zoom(self.zoomFactor,0,0),
            self.keys.zoomOut       : lambda e: self.zoom(1/self.zoomFactor,0,0),
            self.keys.panUp         : lambda e: self.pan(0,self.panDist),
            self.keys.panDown       : lambda e: self.pan(0,-self.panDist),
            self.keys.panLeft       : lambda e: self.pan(self.panDist,0),
            self.keys.panRight      : lambda e: self.pan(-self.panDist,0),
            self.keys.resetView     : lambda e: self.reset_view(),
            self.keys.resetGame     : lambda e: (self.record_state(), self.reset_state(), self.prep_turn()),
            self.keys.fastForward   : lambda e: (self.history.append(self.save_state()), self.history.extend(reversed(self.future)), self.future.clear(), self.load_state(self.history.pop()), self.prep_turn()),
            self.keys.undo          : lambda e: (self.future.append(self.save_state()), self.load_state(self.history.pop()), self.prep_turn()) if self.history else None,
            self.keys.redo          : lambda e: (self.history.append(self.save_state()), self.load_state(self.future.pop()), self.prep_turn()) if self.future else None,
            self.keys.printState    : lambda e: print(self.save_state()),
            self.keys.skipTurn      : lambda e: (setattr(self, 'turn', self.next_turn()), self.prep_turn()),
            self.keys.reloadState   : lambda e: (self.load_state(self.save_state()), self.prep_turn()),
        }

        self.drag = {
            -1 : lambda e: setattr(self, 'rawMousePos', e.pos), # any movement: update mouse position
            2  :  lambda e: self.pan(e.rel[0],e.rel[1]), # right: pan

        }

        # in pixels
        self.rawMousePos = None
        # as a point, or None if there haven't been any mouse movements
        self.mousePos = lambda: self.rawMousePos and self.point(*self.rawMousePos)

        self.numKey = lambda _:None

        self.cache = {}
        self.clearCache = lambda: setattr(self, 'cache', {})

        self.initialState = self.make_initial_state()
        self.history = []
        self.future = []
        self.record_state = lambda:(self.history.append(self.save_state()),setattr(self,'future',[]))

        self.reset_state = lambda: (self.load_state(self.initialState))


        # time controls
        self.enforce_time = bool(timectrl)
        if timectrl:
            self.timer = TimerInfo(self, timectrl)

    is_over = lambda: False
    winner = lambda: None

    # for anything that should be recomputed before each render
    process = lambda self: None
    # for anything that should be recomputed whenever the camera moves
    viewChange = lambda self: None
    # for anything that should be recomputed whenever the window size changes
    resize = lambda self: None
    # for anything that should be recomputed before each turn; if you use this you should probably have load_state call it
    prep_turn = lambda self: None

    # should be overwritten by user
    save_state = lambda self: None # returns description of state
    load_state = lambda self, _: None # implements description of state
    get_state = lambda self, team: self.save_state() #returns state from point of view of team
    make_initial_state = lambda self: None # creates a fresh initial state (perhaps with randomness)

    # can be overwritten for games with weird turn orders
    next_turn = lambda self, turn=None: self.teams[(self.teams.index(turn or self.turn)+1) % len(self.teams)]
    
    # is skipping your turn a legal move?
    allow_skip = False

    # screen borders
    x_min = lambda self:-self.x_offset
    x_max = lambda self:self.width()/self.scale-self.x_offset
    y_min = lambda self:-self.y_offset
    y_max = lambda self:self.height()/self.scale-self.y_offset

    # convert between pixels on screen and points in abstract game space
    pixel = lambda self,p: (int((p.x+self.x_offset)*self.scale), int((p.y+self.y_offset)*self.scale))
    point = lambda self,x,y: Point(x/self.scale-self.x_offset, y/self.scale-self.y_offset)

    def pan(self, dx, dy): # in pixels
        self.x_offset += dx/self.scale
        self.y_offset += dy/self.scale
        self.needViewChange = True

    def zoom(self,factor,x,y): # in gamespace
        if self.scale_min <= self.scale/factor <= self.scale_max:
            self.scale, self.x_offset, self.y_offset = self.scale/factor, (self.x_offset+x)*factor-x, self.y_offset*factor + y*(factor-1)
            self.needViewChange = True

    def reset_view(self):
        self.scale = min(self.size()) / 2 / self.spread
        self.x_offset, self.y_offset = Point(*self.size())/2/self.scale - self.center
        self.needViewChange = True

 
    def add(self, obj, layer=0):
        if layer not in self.layerlist:
            self.layerlist.append(layer)
            self.layerlist.sort()
            self.layers[layer] = [obj]
        else:
            self.layers[layer].append(obj)

    def clearLayer(self, layer):
        self.layers[layer] = []
        if layer not in self.layerlist:
            self.layerlist.append(layer)
            self.layerlist.sort()

    def handle(self, event):
        if event.type in self.handlers:
            self.handlers[event.type](event)

    def render(self):
        for l in self.layerlist:
            for obj in self.layers[l]:
                if obj.visible:
                    obj.render()
        pygame.display.flip()

    def update(self):
        #print("in thread {}".format(threading.currentThread().getName()),flush=True)
        #event = await self.event_queue.get()
        event = pygame.event.wait(timeout=50)
        self.needViewChange = False
        self.needResize = False
        while event:
            self.handle(event)
            event = pygame.event.poll()
        if self.needResize:
            self.resize()
        if self.needViewChange:
            self.viewChange()
        self.process()
        self.render()

    def attemptMove(self, move):
        if self.enforce_time:
            if self.timer.calculate_time(self.turn) <= 0: return False
            self.timer.move()
        if self.turn != move["player"]: return False
        if not self.attemptGameMove(move): return False

        self.turn = self.next_turn()
        self.prep_turn()
        return True

def drawCircle(game, color, center, radius, width=0, realWidth=False, realRadius=True, surface=None, borderGrowth=1):
    # draws a circle with given center and radius
    # if width is given, draws the boundary; if width is 0, fills the circle
    # realWidth/Radius=False  -> given in pixels (on screen) 
    # realWidth/Radius=True -> given in points (in-game distance)
    # borderGrowth controls how the border is placed: 1 -> radius at inner edge; 0 -> radius at outer edge; 1/2 -> radius in center
    if surface == None: surface = game.screen
    if realWidth: width *= game.scale
    if realRadius: radius *= game.scale

    pygame.draw.circle(surface, color, game.pixel(center), int(radius+width*borderGrowth), int(width))

def drawArc(game, color, center, radius, start_angle, stop_angle, width=3, realWidth=False, realRadius=True, surface=None, borderGrowth=1):
    if surface == None: surface = game.screen
    if realWidth: width *= game.scale
    if realRadius: radius *= game.scale

    radius = int(radius + width*borderGrowth)
    x,y = game.pixel(center)
    rect = pygame.Rect(x-radius, y-radius, 2*radius, 2*radius)
    pygame.draw.arc(surface, color, rect, -stop_angle, -start_angle, width) # negative because coordinate system is flipped

def drawPolygon(game, color, ps, width=0, realWidth=False, surface=None):
    # draws a polygon with vertices ps
    # if width is given, draws the boundary; if width is 0, fills the polygon
    # realWidth=False  -> width given in pixels (on screen) 
    # realWidth=True -> width given in points (in-game distance)
    if surface == None: surface = game.screen
    if width:
        for i in range(len(ps)):
            drawSegment(game, color, ps[i], ps[(i+1)%len(ps)], width, realWidth, surface) # yes, drawSegment and drawPolygon call each other, but drawPolygon only uses drawSegment for outlines, and drawSegment draws filled in
    else:
        # for performance, only draw the portion of the polygon which is on the screen
        for asp in [(0,1,game.x_min()), (0,-1,game.x_max()),(1,1,game.y_min()), (1,-1,game.y_max())]:
            ps = intersection_polygon_halfplane(ps, *asp)
        if len(ps) >= 3:
            pygame.draw.polygon(surface, color, [game.pixel(p) for p in ps])

def drawSegment(game, color, p1, p2, width=3, realWidth=False, surface=None, caps=(True,True)):
    # draws a line with ends capped by circles, better than pygame.draw.line
    # realWidth=False  -> width given in pixels (on screen) 
    # realWidth=True -> width given in points (in-game distance)
    if surface == None: surface = game.screen
    if not realWidth: width /= game.scale

    dp = ~(p2-p1) @ (width/2)

    drawPolygon(game, color, [p1+dp, p2+dp, p2-dp, p1-dp], surface=surface)

    if caps[0]: drawCircle(game, color, p1, width/2, realWidth=realWidth, surface=surface)
    if caps[1]: drawCircle(game, color, p2, width/2, realWidth=realWidth, surface=surface)

def drawRay(game, color, loc, dir, width=2, realWidth=False, surface=None):
    # draws a ray from loc to the edge of the screen, in direction dir
    end = max((p for p in (intersection_line_border(loc, loc+dir, axis, pos) for axis, pos in [(0,game.x_min()),(0,game.x_max()),(1,game.y_min()),(1,game.y_max())] if dir[axis] != 0) if not between(loc+dir, loc, p)), key=lambda p:p>>loc, default=loc)
    drawSegment(game, color, loc, end, width, realWidth, surface, (True, False))

class Renderable:
    # this modifies setting and getting attributes to be more convenient
    # attributes are saved in self._dict as functions which take a game and give the value
    # usually (when an attribute is constant) this wrapping and unwrapping is done automatically
    # you can use 'obj.x = y' and 'obj.x' as normal
    # but this also provides the feature that you can set a custom function using 'obj.GETx = f'
    # then 'obj.x' will return f(obj.game)
    # this makes it easier to put code which tells an object to change based on game state inside the object
    # this is probably terrible practice, but I don't really care, and I don't know a 'better' way to implement this
    __setattr__ = lambda self, k, v: self._dict.__setitem__(k[3:], v) if k[:3]=='GET' else self._dict.__setitem__(k, lambda game: v)
    __getattr__ = lambda self, k: self._dict[k](self.game)
    def __init__(self, game, layer):
        # creating a renderable adds it to the game
        # This might also be terrible practice, but it's more convenient than saying 'add' every time
        game.add(self, layer)
        self.__dict__['game'] = game
        self.__dict__['_dict'] = {}
        self.visible = True
    def render(self):
        pass

class Background(Renderable):
    def __init__(self, game, color):
        super().__init__(game, -10**10)
        self.color = color
    def render(self):
        self.game.screen.fill(self.color)

class Segment(Renderable):
    def __init__(self, game, layer, color, p1, p2, width=3, realWidth=False):
        super().__init__(game, layer)
        self.color, self.p1, self.p2, self.width, self.realWidth = color, p1, p2, width, realWidth
    def render(self):
        drawSegment(self.game, self.color, self.p1, self.p2, self.width, self.realWidth)

class Line(Renderable):
    def __init__(self, game, layer, color, p1, p2, width=3):
        super().__init__(game, layer)
        self.color, self.p1, self.p2, self.width = color, p1, p2, width
    def render(self):
        x1,y1 = self.p1
        x2,y2 = self.p2
        dx, dy = x2-x1, y2-y1
        intersections = ({(u,y2-dy*(x2-u)/dx) for u in (self.game.x_min(),self.game.x_max())} if dx else set()) | ({(x2-dx*(y2-v)/dy,v) for v in (self.game.y_min(),self.game.y_max())} if dy else set())
        pygame.draw.line(self.game.screen, self.color, self.game.pixel(Point(*max(intersections))), self.game.pixel(Point(*min(intersections))), int(self.width))

class Grid(Renderable):
    # nx by ny grid of sizex by sizey rectangles starting at x,y
    # by default ny=nx, sizey=sizex
    def __init__(self, game, layer, color, loc, nx, sizex=1, ny=None, sizey=None):
        super().__init__(game, layer)
        if ny==None: ny=nx
        if sizey==None: sizey=sizex
        self.color, self.loc, self.nx, self.ny, self.sizex, self.sizey = color, loc, nx, ny, sizex, sizey
    def render(self):
        for i in range(self.ny+1):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel((self.loc+Point(0,self.sizey*i))), self.game.pixel((self.loc+Point(self.sizex*self.nx,self.sizey*i))))
        for i in range(self.nx+1):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel((self.loc+Point(self.sizex*i,0))), self.game.pixel((self.loc+Point(self.sizex*i,self.sizey*self.ny))))

class InfiniteGrid(Renderable):
    # infinite grid of sizex by sizey rectangles offset by x,y
    # by default sizey=sizex
    def __init__(self, game, layer, color, sizex, sizey=None, loc=Point(0,0)):
        super().__init__(game, layer)
        if sizey==None: sizey=sizex
        self.color, self.sizex, self.sizey, self.loc = color, sizex, sizey, loc
    def render(self):
        for i in range( int((self.game.x_min()-self.loc.x)/self.sizex) , int((self.game.x_max()-self.loc.x)/self.sizex)+1 ):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel(Point(self.loc.x+i*self.sizex,self.game.y_min())), self.game.pixel(Point(self.loc.x+i*self.sizex,self.game.y_max())))
        for i in range( int((self.game.y_min()-self.loc.y)/self.sizey) , int((self.game.y_max()-self.loc.y)/self.sizey)+1 ):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel(Point(self.game.x_min(),self.loc.y+i*self.sizey)), self.game.pixel(Point(self.game.x_max(),self.loc.y+i*self.sizey)))

class CachedImg(Renderable):
    # gen(key) creates image which is saved at self.game.cache[key]
    # rendered with center at loc
    def __init__(self, game, layer, key, gen, loc=None, halign='c', valign='c'):
        super().__init__(game, layer)
        self.key, self.gen, self.loc, self.halign, self.valign = key, gen, loc, halign, valign
    def render(self):
        if self.key not in self.game.cache:
            self.game.cache[self.key] = self.gen(self.key)
        surf = self.game.cache[self.key]
        if self.loc:
            px,py = self.game.pixel(self.loc)
            if -surf.get_width() <= px <= self.game.width()+surf.get_width() and -surf.get_height() <= py <= self.game.height()+surf.get_height():
                shiftx = {'l':0,'c':surf.get_width()//2,'r':surf.get_width()}[self.halign]
                shifty = {'t':0,'c':surf.get_height()//2,'b':surf.get_height()}[self.valign]
                self.game.screen.blit(surf, (px-shiftx, py-shifty))
        else:
            self.game.screen.blit(surf, (0,0))


class Text(Renderable):
    # default centered at x,y
    def __init__(self, game, layer, color, font, text, loc, halign='c', valign='c'):
        super().__init__(game, layer)
        self.font, self.text, self.loc, self.color, self.halign, self.valign = font, text, loc, color, halign, valign
    def render(self):
        write(self.game.screen, self.font, self.text, *self.game.pixel(self.loc), self.color, self.halign, self.valign)

class FixedText(Renderable):
    # text centered at pixel (x,y); fixed on screen. doesn't move with zoom/pan
    def __init__(self, game, layer, color, font, text, x, y, **kwargs):
        super().__init__(game, layer)
        self.font, self.text, self.x, self.y, self.color, self.kwargs = font, text, x, y, color, kwargs
    def render(self):
        write(self.game.screen, self.font, self.text, self.x, self.y, self.color, **self.kwargs)

class Rectangle(Renderable):
    def __init__(self, game, layer, color, loc, dx, dy):
        super().__init__(game, layer)
        self.color, self.loc, self.dx, self.dy = color, loc, dx, dy
    def render(self):
        pygame.draw.rect(self.game.screen, self.color, pygame.Rect(*self.game.pixel(self.loc), int(self.dx*self.game.scale), int(self.dy*self.game.scale)))

class Polygon(Renderable):
    def __init__(self, game, layer, color, points, width=3, realWidth=False):
        super().__init__(game, layer)
        self.color, self.points, self.width, self.realWidth = color, points, width, realWidth
    def render(self):
        drawPolygon(self.game, self.color, self.points, self.width, self.realWidth)

class FilledPolygon(Polygon):
    def __init__(self, game, layer, color, points):
        super().__init__(game, layer, color, points, 0)

class PolygonIcon(Renderable):
    # regular polygon representing a point, fixed size in pixels
    def __init__(self, game, layer, loc, sides, fill_color, border_color, radius, line_width,rotation=math.pi):
        # radius, line_width in pixels
        super().__init__(game, layer)
        self.offsets = [(radius*math.sin(rotation+math.pi*2/sides*i),
                         radius*math.cos(rotation+math.pi*2/sides*i)) for i in range(sides)]
        self.loc, self.sides, self.fill_color, self.border_color, self.line_width = loc, sides, fill_color, border_color, line_width
    def render(self):
        x,y = self.game.pixel(self.loc)
        points = [(x+dx, y+dy) for dx,dy in self.offsets]
        pygame.draw.polygon(self.game.screen, self.fill_color, points)
        pygame.draw.lines(self.game.screen, self.border_color, True, points, width=self.line_width)
        # todo: make this not look terrible when the lines are thick

class Circle(Renderable):
    def __init__(self, game, layer, color, loc, r, width=3, **kwargs):
        super().__init__(game, layer)
        self.color, self.loc, self.r, self.width, self.kwargs = color, loc, r, width, kwargs
    def render(self, color=None, width=None):
        if color == None: color = self.color
        if width == None: width = self.width
        drawCircle(self.game, color, self.loc, self.r, width, **self.kwargs)

class Disk(Circle):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.width = 0

class BorderDisk(Circle):
    def __init__(self, game, layer, fill_color, border_color, *args, **kwargs):
        super().__init__(game, layer, None, *args, **kwargs)
        self.fill_color, self.border_color = fill_color, border_color
    def render(self):
        if self.fill_color: super().render(color=self.fill_color, width=0)
        if self.border_color: super().render(color=self.border_color)

class ScreenBorder(Renderable):
    def __init__(self, game, layer, color, width):
        super().__init__(game, layer)
        self.color, self.width = color, width
    def render(self):
        pygame.draw.rect(self.game.screen, self.color, pygame.Rect((0,0), (self.game.width(), self.game.height())), self.width)

def write(screen, font, text, x, y, color, halign='c', valign='c', hborder='l', vborder='t'):
    # x and y are pixel values
    # halign is horizontal alignment:
    #   c -> centered around x
    #   l -> left edge at x
    #   r -> right edge at x
    # valign is vertical alignment:
    #   c -> centered around y
    #   t -> top edge at y
    #   b -> bottom edge at y
    # hborder is which boundary of the screen to follow:
    #   l -> fixed distance from left edge
    #   c -> fixed distance from horizontal center
    #   r -> fixed distance from right edge (x should be negative)
    # vborder is which boundary of the screen to follow:
    #   t -> fixed distance from top edge
    #   c -> fixed distance from vertical center
    #   b -> fixed distance from bottom edge (y should be negative)

    if not ({halign, hborder} < set('lcr') and {valign, vborder} < set('tcb')): raise ValueError

    text = str(text)
    written = font.render(text,True,color)
    twidth, theight = font.size(text)
    swidth, sheight = screen.get_size()
    hdic = {'l':0, 'c': 1/2, 'r': 1}
    vdic = {'t':0, 'c': 1/2, 'b': 1}
    shiftx = int(hdic[halign]*twidth - hdic[hborder]*swidth)
    shifty = int(vdic[valign]*theight - vdic[vborder]*sheight)
    screen.blit(written, (int(x - hdic[halign]*twidth + hdic[hborder]*swidth), int(y - vdic[valign]*theight + vdic[vborder]*sheight)))

class GameInfo(Renderable):
    # vals should be a function with one argument that returns a list of pairs
    def __init__(self, game, vals, font_size=24, **kwargs):
        super().__init__(game, 10**10)
        self.GETvals = vals
        self.font_size = font_size
        self.kwargs = {'halign':'l', 'valign':'t', 'hborder':'l', 'vborder':'t'}
        self.kwargs.update(kwargs)
        if not game.headless:
            self.font = pygame.font.Font(pygame.font.match_font(MONO_FONTS), font_size)


    def render(self):
        vanchor = delta = self.font_size * {'t':1, 'b':-1}[self.kwargs['vborder']]
        hanchor = self.font_size * {'l':1, 'r':-1}[self.kwargs['hborder']]
        for i, (k, v) in {'t':identity, 'b':reversed}[self.kwargs['vborder']](list(enumerate(self.vals))):
            if k:
                write(self.game.screen, self.font, f'{k}: {v}', hanchor, vanchor + delta*i, (0,0,0), **self.kwargs)

class TimerInfo(GameInfo):
    def __init__(self, game, timectrl):
        val = lambda g: ((team, f'{int(t)//60: >2}:{t%60:05.2f}' if (t:=self.calculate_time(team)) > 0 else f'XX:XX.XX') for team in g.teams)
        super().__init__(game, val, 36, halign='r', valign='b', hborder='r', vborder='b')
        
        self.GETturn = lambda g: g.turn
        self.tc_initial, self.tc_increment = timectrl
        self.time_left = {}
        self.turn_started = None
    
    def calculate_time(self, team):
        return self.time_left.get(team, self.tc_initial) - (time.time() - self.turn_started if self.turn_started and self.turn == team else 0) if self.tc_initial else 1

    def move(self):
        if self.turn_started:
            self.time_left[self.turn] = self.calculate_time(self.game.turn) + self.tc_increment
        self.turn_started = time.time()

# utility method for command line tools
# throwing a ValueError causes argparse to reject the argument,
# so the implicit ValueError on float()ing a non-float is actually what we want
def tcparse(tc):
    parts = [float(x) for x in tc.split('+')]
    if 1 <= len(parts) <= 2:
        return (60*parts[0], parts[1] if len(parts) == 2 else 0)
    raise ValueError
