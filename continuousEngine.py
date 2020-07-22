import sys, pygame

pygame.init()

class Game:
    def __init__(self,initialState=None,size=(1000,1000),backgroundColor=(245,245,235),scale=100,center=(0,0)):
        self.size = self.width, self.height = size
        self.screen = pygame.display.set_mode(size)
        self.scale_home = scale
        centerX, centerY = center
        self.x_offset_home, self.y_offset_home = self.width/scale/2 - centerX, self.height/scale/2 - centerY
        self.scale, self.x_offset, self.y_offset = self.scale_home, self.x_offset_home, self.y_offset_home

        # objects are assigned to 'layers' which give rendering order
        self.layerlist = []
        self.layers = {}
        Background(self, backgroundColor)

        self.handlers = {
            pygame.QUIT: lambda e: sys.exit(),
            pygame.MOUSEBUTTONDOWN: lambda e: self.click[e.button](e) if e.button in self.click else print('unknown click:',e.button),
            pygame.MOUSEMOTION: lambda e: ([self.drag[k](e) if k in self.drag else print('unknown motion:',k) for k in range(-1,3) if k<0 or e.buttons[k]]),
            pygame.KEYDOWN: lambda e: self.keyPress[e.key](e) if e.key in self.keyPress else self.numKey(e.key%208-48) if 256<=e.key<=265 or 48<=e.key<=57 else print('unknown key:',e.key)
        }

        self.panDist = 100
        self.zoomFactor = .8
        self.scale_min = 2
        self.scale_max = 500

        self.click = {
            4: lambda e: self.zoom(self.zoomFactor, *self.point(*e.pos)),
            5: lambda e: self.zoom(1/self.zoomFactor, *self.point(*e.pos)),
        }

        self.keys = type('keys',(object,),{
            'zoomIn'    : 270, # +
            'zoomOut'   : 269, # -
            'panUp'     : 44,  # ,
            'panDown'   : 111, # o
            'panLeft'   : 97,  # a
            'panRight'  : 101, # e
            'resetView' : 278, # home
            'undo'      : 59,  # ;
            'redo'      : 113, # q
            'resetGame' : 112, # p
        })

        self.keyPress = {
            self.keys.zoomIn    : lambda e: self.zoom(self.zoomFactor,0,0),
            self.keys.zoomOut   : lambda e: self.zoom(1/self.zoomFactor,0,0),
            self.keys.panUp     : lambda e: self.pan(0,self.panDist),
            self.keys.panDown   : lambda e: self.pan(0,-self.panDist),
            self.keys.panLeft   : lambda e: self.pan(self.panDist,0),
            self.keys.panRight  : lambda e: self.pan(-self.panDist,0),
            self.keys.resetView : lambda e: self.resetView(),
            self.keys.resetGame : lambda e: (self.record_state(), self.load_state(self.initialState)),
            self.keys.undo      : lambda e: (self.future.append(self.save_state()), self.load_state(self.history.pop())) if self.history else None,
            self.keys.redo      : lambda e: (self.history.append(self.save_state()), self.load_state(self.future.pop())) if self.future else None,
        }

        self.drag = {
            2: lambda e: self.pan(e.rel[0],e.rel[1]), # right: pan
        }

        self.numKey = lambda _:None

        self.cache = {}
        self.clearCache = lambda: setattr(self, 'cache', {})

        self.history = [initialState]
        self.future = []
        self.initialState = initialState
        self.record_state = lambda:(self.history.append(self.save_state()),setattr(self,'future',[]))

        # should be overwritten by user
        self.save_state = lambda :None # returns description of state
        self.load_state = lambda _:None # implements description of state

        # for anything that should be recomputed before each render
        self.process = lambda: None
        # for anything that should be recomputed whenever the camera moves
        self.viewChange = lambda: None



    # screen borders
    x_min = lambda self:-self.x_offset
    x_max = lambda self:self.width/self.scale-self.x_offset
    y_min = lambda self:-self.y_offset
    y_max = lambda self:self.width/self.scale-self.y_offset

    # convert between pixels on screen and points in abstract game space
    pixel = lambda self,x,y: (int((x+self.x_offset)*self.scale), int((y+self.y_offset)*self.scale))
    point = lambda self,x,y: (x/self.scale-self.x_offset, y/self.scale-self.y_offset)

    def pan(self, dx, dy): # in pixels
        self.x_offset += dx/self.scale
        self.y_offset += dy/self.scale
        self.needViewChange = True

    def zoom(self,factor,x,y): # in gamespace
        if self.scale_min <= self.scale/factor <= self.scale_max:
            self.scale, self.x_offset, self.y_offset = self.scale/factor, (self.x_offset+x)*factor-x, self.y_offset*factor + y*(factor-1)
            self.needViewChange = True

    def resetView(self):
        self.scale, self.x_offset, self.y_offset = self.scale_home, self.x_offset_home, self.y_offset_home
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
        event = pygame.event.wait()
        self.needViewChange = False
        while event:
            self.handle(event)
            event = pygame.event.poll()
        if self.needViewChange:
            self.viewChange()
        self.process()
        self.render()

def drawSegment(game, color, p1, p2, width=3, realWidth=False, surface=None): 
    # draws a line with ends capped by circles, better than pygame.draw.line
    # realWidth=True  -> width given in pixels (on screen) 
    # realWidth=False -> width given in points (in-game distance)
    if surface == None: surface = game.screen
    if realWidth: width *= game.scale

    x1,y1 = game.pixel(*p1)
    x2,y2 = game.pixel(*p2)

    if (x1,y1) == (x2,y2):
        pygame.draw.circle(surface, color, (x1,y1), int(width/2))
        return
    
    dx, dy = y2-y1, x1-x2 # rotated by 90 degrees
    dx, dy = int(dx*width/2/(dx**2+dy**2)**.5), int(dy*width/2/(dx**2+dy**2)**.5)
    
    pygame.draw.polygon(surface, color, [(x1+dx,y1+dy), (x1-dx,y1-dy), (x2-dx,y2-dy), (x2+dx,y2+dy)])
    pygame.draw.circle(surface, color, (x2,y2), int(width/2))
    pygame.draw.circle(surface, color, (x1,y1), int(width/2))

def intesectHalfPlane(polygon, axis, sign, position):
    # the intersection of the polygon (list of points) with the half-plane described by axis, sign, position
    # the equation for the half-plane is <Z><rel>position, where Z={0:x,1:y}[axis] and rel={1:>,-1:<}[sign]
    # e.g. (_, 1, -1, 3) means the half-plane is given by y<3
    half_plane = lambda p: (p[axis] - position)*sign > 0
    vertices = []
    for i in range(len(polygon)):
        if half_plane(polygon[i]):
            vertices.append(polygon[i])
        else:
            vertices.extend(
                (position,)*(1-axis)+(polygon[i][1-axis] + (polygon[j][1-axis]-polygon[i][1-axis]) * (position-polygon[i][axis]) / (polygon[j][axis]-polygon[i][axis]),)+(position,)*axis
                for j in [i-1,(i+1)%len(polygon)] if half_plane(polygon[j]))
    return [vertices[i] for i in range(len(vertices)) if vertices[i-1] != vertices[i]]


def drawPolygon(game, color, ps, width=0, realWidth=False, surface=None):
    # draws a polygon with vertices ps
    # if width is given, draws the boundary; if width is 0, fills the polygon
    # realWidth=True  -> width given in pixels (on screen) 
    # realWidth=False -> width given in points (in-game distance)
    if surface == None: surface = game.screen
    if width:
        for i in range(len(ps)):
            drawSegment(game, color, ps[i], ps[(i+1)%len(ps)], width, realWidth, surface)
    else:
        # for performance, only draw the portion of the polygon which is on the screen
        for asp in [(0,1,game.x_min()), (0,-1,game.x_max()),(1,1,game.y_min()), (1,-1,game.y_max())]:
            ps = intesectHalfPlane(ps, *asp)
        if len(ps) >= 3:
            pygame.draw.polygon(surface, color, [game.pixel(*p) for p in ps])
    

def drawCircle(game, color, center, radius, width=0, realWidth=False, surface=None):
    # draws a circle with given center and radius
    # if width is given, draws the boundary; if width is 0, fills the circle
    # realWidth=True  -> width given in pixels (on screen) 
    # realWidth=False -> width given in points (in-game distance)
    if surface == None: surface = game.screen
    if realWidth: width *= game.scale

    pygame.draw.circle(surface, color, game.pixel(*center), int(radius*game.scale+width), int(width))



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
    def debugLine(self, color, p1, p2, width=3):
        pygame.draw.line(self.game.screen, color, self.game.pixel(*p1), self.game.pixel(*p2), width)

class Background(Renderable):
    def __init__(self, game, color):
        super().__init__(game, 0)
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
        pygame.draw.line(self.game.screen, self.color, self.game.pixel(*max(intersections)), self.game.pixel(*min(intersections)), int(self.width))

class Grid(Renderable):
    # nx by ny grid of sizex by sizey rectangles starting at x,y
    # by default ny=nx, sizey=sizex
    def __init__(self, game, layer, color, x, y, nx, sizex=1, ny=None, sizey=None):
        super().__init__(game, layer)
        if ny==None: ny=nx
        if sizey==None: sizey=sizex
        self.color, self.x, self.y, self.nx, self.ny, self.sizex, self.sizey = color, x, y, nx, ny, sizex, sizey
    def render(self):
        for i in range(self.ny+1):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel(self.x,self.y+self.sizey*i), self.game.pixel(self.x+self.sizex*self.nx,self.y+self.sizey*i))
        for i in range(self.nx+1):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel(self.x+self.sizex*i,self.y), self.game.pixel(self.x+self.sizex*i,self.y+self.sizey*self.ny))

class InfiniteGrid(Renderable):
    # infinite grid of sizex by sizey rectangles offset by x,y
    # by default sizey=sizex
    def __init__(self, game, layer, color, sizex, sizey=None, x=0, y=0):
        super().__init__(game, layer)
        if sizey==None: sizey=sizex
        self.color, self.sizex, self.sizey, self.x, self.y = color, sizex, sizey, x, y
    def render(self):
        for i in range( int((self.game.x_min()-self.x)/self.sizex) , int((self.game.x_max()-self.x)/self.sizex)+1 ):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel(self.x+i*self.sizex,self.game.y_min()), self.game.pixel(self.x+i*self.sizex,self.game.y_max()))
        for i in range( int((self.game.y_min()-self.y)/self.sizey) , int((self.game.y_max()-self.y)/self.sizey)+1 ):
            pygame.draw.line(self.game.screen, self.color, self.game.pixel(self.game.x_min(),self.y+i*self.sizey), self.game.pixel(self.game.x_max(),self.y+i*self.sizey))

class CachedImg(Renderable):
    # gen(key) creates image which is saved at self.game.cache[key]
    # rendered with center at x,y
    def __init__(self, game, layer, key, gen, loc=None, halign='c', valign='c'):
        super().__init__(game, layer)
        self.key, self.gen, self.loc, self.halign, self.valign = key, gen, loc, halign, valign
    def render(self):
        if self.key not in self.game.cache:
            self.game.cache[self.key] = self.gen(self.key)
        surf = self.game.cache[self.key]
        if self.loc:
            px,py = self.game.pixel(*self.loc)
            if -surf.get_width() <= px <= self.game.width+surf.get_width() and -surf.get_height() <= py <= self.game.height+surf.get_height():
                shiftx = {'l':0,'c':surf.get_width()//2,'r':surf.get_width()}[self.halign]
                shifty = {'t':0,'c':surf.get_height()//2,'b':surf.get_height()}[self.valign]
                self.game.screen.blit(surf, (px-shiftx, py-shifty))
        else:
            self.game.screen.blit(surf, (0,0))


class Text(Renderable):
    # default centered at x,y
    def __init__(self, game, layer, color, font, text, x, y, halign='c', valign='c'):
        super().__init__(game, layer)
        self.font, self.text, self.x, self.y, self.color, self.halign, self.valign = font, text, x, y, color, halign, valign
    def render(self):
        write(self.game.screen, self.font, self.text, *self.game.pixel(self.x, self.y), self.color, self.halign, self.valign)

class FixedText(Text):
    # text centered at pixel (x,y); fixed on screen. doesn't move with zoom/pan
    def render(self):
        write(self.game.screen, self.font, self.text, self.x, self.y, self.color, self.halign, self.valign)

class Rectangle(Renderable):
    def __init__(self, game, layer, color, x, y, dx, dy):
        super().__init__(game, layer)
        self.color, self.x, self.y, self.dx, self.dy = color, x, y, dx, dy
    def render(self):
        pygame.draw.rect(self.game.screen, self.color, pygame.Rect(*self.game.pixel(self.x, self.y), int(self.dx*self.game.scale), int(self.dy*self.game.scale)))

class FilledPolygon(Renderable):
    def __init__(self, game, layer, color, points):
        super().__init__(game, layer)
        self.color, self.points = color, points
    def render(self):
        drawPolygon(self.game, self.color, self.points)    

class Circle(Renderable):
    def __init__(self, game, layer, color, x, y, r, width=3):
        super().__init__(game, layer)
        self.color, self.x, self.y, self.r, self.width = color, x, y, r, width
        self.GETloc = lambda g: (self.x, self.y)
    def render(self):
        drawCircle(self.game, self.color, self.loc, self.r, self.width)

class Disk(Circle):
    def render(self):
        drawCircle(self.game, self.color, self.loc, self.r, 0)

class BorderDisk(Circle):
    def __init__(self, game, layer, fill_color, border_color, x, y, r, width=3):
        super().__init__(game, layer, None, x, y, r, width)
        self.fill_color, self.border_color = fill_color, border_color
    def render(self):
        drawCircle(self.game, self.fill_color, self.loc, self.r, 0)
        drawCircle(self.game, self.border_color, self.loc, self.r, self.width)


def write(screen, font, text, x, y, color, halign='c', valign='c'):
    # x and y are pixel values
    # halign is horizontal alignment:
    #   c -> centered around x
    #   l -> left edge at x
    #   r -> right edge at x
    # valign is vertical alignment:
    #   c -> centered around y
    #   t -> top edge at y
    #   b -> bottom edge at y
    text = str(text)
    written = font.render(text,True,color)
    width, height = font.size(text)
    if halign not in 'lcr' or valign not in 'tcb': raise ValueError
    shiftx = {'l':0,'c':width//2,'r':width}[halign]
    shifty = {'t':0,'c':height//2,'b':height}[valign]
    screen.blit(written, (x-shiftx, y-shifty))