from continuousEngine import *
import random
import time
from math import atan2, pi

piece_rad = 1

board_rad = 10

## HELPER FUNCTIONS FOR GEOMETRY
## points are represented as tuples (x,y)

# squared distance
dist_sq = lambda p1,p2: (p1[0]-p2[0])**2+(p1[1]-p2[1])**2
# is this piece within the (circular) board?
on_board = lambda p: dist_sq(p,(0,0)) < (board_rad - piece_rad)**2
# is this point on the board?
on_board_pt = lambda p: dist_sq(p,(0,0)) < board_rad**2
# is x 'above' the line from p1 to p2; i.e. on your left when going from p1 to p2?
above_line = lambda p1, p2, x: (p2[0]-p1[0])*(x[1]-p1[1]) > (p2[1]-p1[1])*(x[0]-p1[0])
# do line segments a-b and x-y intersect?
intersect = lambda a,b,x,y: above_line(a,b,x) != above_line(a,b,y) and above_line(x,y,a) != above_line(x,y,b)
# is the segment from p1 to p2 at all on the board?
intersect_board = lambda p1, p2:(on_board_pt(p1) or on_board_pt(p2)
                        or (lambda nearest: on_board_pt(nearest) and (p1[0]-nearest[0])*(p2[0]-nearest[0]) <= 0 and (p1[1]-nearest[1])*(p2[1]-nearest[1]) <= 0 )(nearest_origin(p1,p2)))
# which pieces (among xs) are close enough to p1 and p2 to possibly get in the way?
# those which intersect a circle at the same distance as p1 from p2; i.e. within max_dist_sq**.5 of p2 (and symmetrically of p1)
chokepoints = lambda p1, p2, xs: (lambda max_dist_sq:{x for x in xs if dist_sq(p1,x) < max_dist_sq and dist_sq(p2,x) < max_dist_sq})((dist_sq(p1,p2)**0.5 + 2*piece_rad)**2)
# separate chokepoints into those above and below the line; gives tuple of sets (above line, below line)
split_chokepoints = lambda p1, p2, xs: (lambda cps: ({x for x in cps if above_line(p1,p2,x)},{x for x in cps if not above_line(p1,p2,x)}))(chokepoints(p1,p2,xs))
# can you locally slide from p1 to p2, without touching pieces at xs?
# assumes p1 and p2 are nearby (within 4r)
# the only way this fails is if there's a pair of chokepoints within 4r and between p1 and p2, in the sense that p1 and p2 are on opposite sides of the line
connected = lambda p1, p2, xs: (lambda tops, bots: not any(nearby(top,bot) and intersect(p1,p2,top,bot) for top in tops for bot in bots))(*split_chokepoints(p1,p2,xs))
# given {p} pieces, give {(p1,p2)} of pairs of points within 4r
weak_edges = lambda pieces: {(p1,p2) for p1 in pieces for p2 in pieces if p1 != p2 and nearby(p1,p2)}
# given [p] pieces, give {(p1,b)} of lines to the boundary which might prevent movement (i.e. less than 3r)
# it's fine for the line to extend past the boundary -- we double the coordinates for simplicity; this only works because board_rad is enough bigger than piece_rad
boundary_cuts = lambda pieces: {((x,y),(2*x,2*y)) for x,y in pieces if dist_sq((0,0),(x,y)) > (board_rad-3*piece_rad)**2}
# given {(p,p)} edges and {(p,p)} cuts, gives the set of edges which don't cross a cut
filter_edges = lambda edges, cuts: {edge for edge in edges if not any(intersect(*edge, *cut) for cut in cuts)}
# union: expects an iterator of sets
union = lambda ss: (lambda s: set() if s is None else s | union(ss))(next(ss,None))
# given {p} vertices and [(p1,p2)] edges, give the partition of vertices into connected components [{p}]
# requires edges to be a list
components = lambda vertices, edges, cmps=None: components(vertices, edges, [{p} for p in vertices]) if cmps==None else \
    (lambda e: components(vertices, edges[1:], [s for s in cmps if not s&e]+[union(s for s in cmps if s&e)]))(set(edges[0])) if edges else cmps
# do pieces centered at p1 and p2 overlap?
overlap = lambda p1, p2: dist_sq(p1,p2) < (2*piece_rad)**2
# are pieces centered at p1 p2 close enough to block movement between them?
nearby = lambda p1, p2: dist_sq(p1,p2) < (4*piece_rad)**2
# are pieces centered at p1 p2 close enough that they might block each others' movement?
sorta_nearby = lambda p1, p2: dist_sq(p1,p2) < (6*piece_rad)**2
# combat floating point errors. In particular, tangent circles shouldn't intersect
epsilon = 10**-10
# centers of circles tangent to both circles centered at p1 and p2
# (dx, dy) is the vector from the midpoint of p1 and p2 to one of the tangent circles
double_tangents = lambda p1, p2: (lambda d:
        (lambda dx, dy: ( ((p1[0]+p2[0])/2+dx*(1+epsilon),(p1[1]+p2[1])/2+dy*(1+epsilon)) , ((p1[0]+p2[0])/2-dx*(1+epsilon),(p1[1]+p2[1])/2-dy*(1+epsilon)) ))
        (((4*piece_rad**2-d/4))**.5*(p2[1]-p1[1])/d**.5,
         ((4*piece_rad**2-d/4))**.5*(p1[0]-p2[0])/d**.5 )
    if 0<d**.5 < 4*piece_rad else ())(dist_sq(p1,p2))
# point on line p1-p2 closest to origin
nearest_origin = lambda p1, p2: ((p2[1]-p1[1]) * (p1[0]*p2[1]-p1[1]*p2[0]) / dist_sq(p1,p2), (p1[0]-p2[0]) * (p1[0]*p2[1]-p1[1]*p2[0]) / dist_sq(p1,p2))
# the result of moving p1 towards p2 until it's on the board
snap_to_circle = lambda p1, p2: p1 if on_board_pt(p1) else (lambda nearest: (nearest[0] + (p1[0]-p2[0]) / dist_sq(p1,p2)**.5 * (board_rad**2 - dist_sq(nearest, (0,0)))**.5, nearest[1] + (p1[1]-p2[1]) / dist_sq(p1,p2)**.5 * (board_rad**2 - dist_sq(nearest, (0,0)))**.5))(nearest_origin(p1,p2))
# area of polygon with vertices pts
# assumes points are in the order stored in Voronoi (counterclockwise, I think)
polygon_area = lambda pts: sum((lambda a,b: a[0]*b[1]-a[1]*b[0])(pts[i], pts[(i+1)%len(pts)]) for i in range(len(pts))) / 2
# area of the region of the board on the side of chord a-b, assuming a -> b is counterclockwise
sliver_area = lambda a, b: (atan2(*b)-atan2(*a))%(2*pi) * board_rad**2 / 2 - polygon_area([(0,0), b, a])
# area of the intersection of the polygon with vertices pts and the board
cell_area = lambda pts: (lambda segments: polygon_area(sum(segments, [])) + sum(sliver_area(segments[(i+1)%len(segments)][0], segments[i][1]) for i in range(len(segments)) if segments[i][1] != segments[(i+1)%len(segments)][0]) or board_rad**2*pi)(
    [[snap_to_circle(pts[i], pts[(i+1)%len(pts)]), snap_to_circle(pts[(i+1)%len(pts)], pts[i])] for i in range(len(pts)) if intersect_board(pts[i], pts[(i+1)%len(pts)])])

## for computing voronoi diagrams
## by josh brunner

def circumcenter(p1,p2,p3):
    #rotate and sum helper function because you do it alot
    f = lambda g:g(p1,p2,p3)+g(p2,p3,p1)+g(p3,p1,p2)
    num = lambda i:f(lambda a,b,c: (a[1-i]-b[1-i])*a[1-i]*b[1-i] + a[1-i]*c[i]*c[i] - c[1-i]*a[i]*a[i])
    denom = lambda i:f(lambda a,b,c: 2 * (a[i]*b[1-i] - a[i]*c[1-i]))
    return (num(0)/denom(0), num(1)/denom(1))
class Voronoi:
    def __init__(self, p1, p2):
        """
        p1, p2 are points that define a bounding box which you guarentee that all of the points of your voronoi diagram lie within
        Behavior is undefined for inserted points outside this bounding box. """
        self.box = (p1,p2)
        center = ((p1[0]+p2[0])/2,(p1[1]+p2[1])/2)
        a,b = ((p1[0]-center[0])* 8+center[0],center[1]),(center[0],(p1[1]-center[1])* 8+center[1])
        c,d = ((p1[0]-center[0])*-8+center[0],center[1]),(center[0],(p1[1]-center[1])*-8+center[1])
        if (abs(p1[0]-p2[0])<abs(p1[1]-p2[1])):
            a,b,c,d = b,c,d,a
        #note: to be technically correct, we actually need to scale abc to be farther from the center.
        self.points = [a,b,c,d]
        #for each point, a list of points whose voronoi cells are adjacent.
        #This can be thought of as a cyclical list. The list is in clockwise order, but the start and end are arbitrary.
        self.contiguities = {a:[b,d,"inf"], b:[c,d,a,"inf"], c:[d,b,"inf"],d:[a,b,c,"inf"]}
        #for each point, the list of vertices which make up its voronoi cell.
        #This can be thought of as a cyclical list. The list is in clockwise order, but the start and end are arbitrary.
        #voronoi_vertices[a][n] is the circumcenter of the points a, contiguities[a][n], contiguities[a][n+1] (taking modulo as necessary to make the indicies work out)
        f = lambda x,y,i:((x[i]+y[i])/2-center[i])*10+center[i]
        lc = circumcenter(a,b,d)
        rc = circumcenter(b,c,d)
        inf_ab = (f(a,b,0),f(a,b,1))
        inf_bc = (f(b,c,0),f(b,c,1))
        inf_cd = (f(c,d,0),f(c,d,1))
        inf_da = (f(d,a,0),f(d,a,1))
        self.voronoi_vertices = {a:[lc,inf_da,inf_ab],b:[rc,lc,inf_ab,inf_bc],c:[rc,inf_bc,inf_cd],d:[lc,rc,inf_cd,inf_da]}
    def nearest(self, p):
        return min(self.points, key=lambda q:dist_sq(p,q))
    def add(self, p):
        """add a point to the voronoi diagram. The algorithm outline is at the top of the file."""
        self.contiguities[p] = []
        #This is a list of pairs. For entry in self.contiguities[p], we will have one entry in to_delete, which consists of two indices for which we need to remove the voronoi vertices bewteen.
        q_0 = self.nearest(p)
        q = q_0
        while True:
            i = 0
            k = len(self.contiguities[q])
            #this is the range of indices of q's contiguities that should be removed due to the addition of p
            #this range is exclusive: we want to keep both endpoints of the range in q's contiguities
            d = [0,0]
            while i<k:
                r = self.voronoi_vertices[q][i%k]
                i+=1
                s = self.voronoi_vertices[q][i%k]
                #the perpendicular bisector of pq crosses the segment rs in the r->s direction
                #in otherwords, the unique adjacent pair r,s with the property that r is closer to q and s is closer to p
                r_dist = ((p[0]-q[0])*(p[0]-r[0]) + (p[1]-q[1])*(p[1]-r[1]))/((p[0]-q[0])**2+(p[1]-q[1])**2)
                s_dist = ((p[0]-q[0])*(p[0]-s[0]) + (p[1]-q[1])*(p[1]-s[1]))/((p[0]-q[0])**2+(p[1]-q[1])**2)
                #print("p={}, q={}, r={}, s={}, r_dist={}, s_dist={}".format(p,q,r,s,r_dist,s_dist))
                if  r_dist > .5 >= s_dist:
                    d[0] = i%k
                    self.contiguities[p].append(self.contiguities[q][i%k])
                    q_next = self.contiguities[q][i%k]
                    #print("i="+str(i)+", q_next = "+str(q_next))
                    #now we check the other direction; i.e. r,s such that s is closer to q and r is closer to p
                elif r_dist < .5 <= s_dist:
                    d[1]=i%k
        #now we clean up q's edges that no longer should exist using d
            l = self.contiguities[q]
            r0 = l[d[0]]
            r1 = l[d[1]]
            self.contiguities[q] = l[0:d[0]+1]+[p]+l[d[1]:] if d[1]>d[0] else l[d[1]:d[0]+1]+[p]
            l = self.voronoi_vertices[q]
            self.voronoi_vertices[q] = l[0:d[0]]+[circumcenter(p,q,r0),circumcenter(p,q,r1)]+l[d[1]:] if d[1]>d[0] else l[d[1]:d[0]]+[circumcenter(p,q,r0),circumcenter(p,q,r1)]
            q = q_next
            if q_next == q_0:
                break
        #finally, we need to add p's voronoi vertices to the list
        l = self.contiguities[p]
        self.voronoi_vertices[p] = [circumcenter(p,l[i],l[(i+1)%len(l)]) for i in range(len(l))]
        self.points.append(p)
    def remove(self,p):
        """remove a point from the diagram. The algorithm outline is at the top of the file."""
        l = self.contiguities[p]
        #this function cleans up all the loose ends of a point b that used to neighbor p by joining the two broken edges of the voronoi diagram at the common point center
        def f(b, center):
            m = self.contiguities[b]
            i_p = m.index(p)
            self.contiguities[b] = m[:i_p]+m[i_p+1:]
            m = self.voronoi_vertices[b]
            if i_p > 0:
                self.voronoi_vertices[b] = m[:i_p-1] + [center] + m[i_p+1:]
            else:
                self.voronoi_vertices[b] = m[1:-1] + [center]
        while len(l) > 3:
            for i in range(len(l)):
                a,b,c = l[(i-1)%len(l)],l[(i+0)%len(l)],l[(i+1)%len(l)]
                center = circumcenter(a,b,c)
                r = dist_sq(center,a)
                #if no other point is in the circumcircle, so this is a valid triangle in the delaunay triagulation.
                v = (a[1]-c[1],c[0]-a[0])
                m = ((a[0]+c[0])/2,(a[1]+c[1])/2)
                flag = ((p[0]-m[0])*v[0] + (p[1]-m[1])*v[1])*((b[0]-m[0])*v[0] + (b[1]-m[1])*v[1]) < 0
                if all(q in {a,b,c} or dist_sq(q,center) >= r for q in l) and flag:
                    #fixing the first point in clockwise order of this triangle
                    m = self.contiguities[a]
                    i_p = m.index(p)
                    self.contiguities[a] = m[:i_p]+[c]+m[i_p:]
                    m = self.voronoi_vertices[a]
                    if i_p > 0:
                        self.voronoi_vertices[a] = m[:i_p-1] + [center] + m[i_p-1:]
                    else:
                        self.voronoi_vertices[a] = [m[-1]] + m[:-1] + [center]
                    #fixing the third point in clockwise order
                    m = self.contiguities[c]
                    i_p = m.index(p)
                    self.contiguities[c] = m[:i_p+1]+[a]+m[i_p+1:]
                    m = self.voronoi_vertices[c]
                    self.voronoi_vertices[c] = m[:i_p+1] + [center] + m[i_p+1:]
                    #fixing the middle point. Note that we have found all of the new contiguities of this point, so we clean it up with f.
                    f(b,center)

                    l = l[:i]+l[i+1:]
                    break
        #Now there are only three points left, so we just need to add the circumcenter and clean up the loose ends
        a,b,c = l[0],l[1],l[2]
        center = circumcenter(a,b,c)
        f(a,center)
        f(b,center)
        f(c,center)
        del self.contiguities[p]
        del self.voronoi_vertices[p]
        i_p = self.points.index(p)
        self.points = self.points[:i_p]+self.points[i_p+1:]

teams = ['WHITE', 'BLACK']
inc_turn = {'WHITE':'BLACK', 'BLACK':'WHITE'}

class Layers:
    BOUNDARY    = 1
    GUIDES      = 1.5
    PIECES      = {'WHITE':2, 'BLACK':2.1, 'GHOST':2.2, 'NEW':5}
    TERRITORY   = 3
    COUNT       = 10
    DEBUG       = 20

class Colors:
    fill        = {'WHITE': (205,205,205), 'BLACK': (50, 50, 50 )}
    guide       = {'WHITE': (225,225,225), 'BLACK': (30, 30, 30 )}
    border      = {'WHITE': (80, 80, 80 ), 'BLACK': (135,135,135)}
    newfill     = {'WHITE': (255,255,255), 'BLACK':(0,0,0)}
    legal       = (0,255,0)
    blocker     = (255,0,0)
    capture     = (0,180,255)
    background  = (212,154,61)
    text        = {'WHITE': (255,255,255), 'BLACK':(0,0,0), 'GAMEOVER':(230,20,128)}
    boundary    = (0,0,0)
    debug       = [(255,0,0),(0,255,0),(0,0,255)]
    ghost       = (128,128,128)
    territory   = (90,50,255)

font = pygame.font.Font(pygame.font.match_font('ubuntu-mono'),36)

class GoPiece(BorderDisk):
    def __init__(self, game, team, x, y):
        super().__init__(game, Layers.PIECES[team], None, None, x, y, piece_rad)
        self.team = team
        self.GETfill_color = lambda g: Colors.fill[self.team]
        self.GETborder_color = lambda g: Colors.blocker if self in g.blockers else Colors.capture if self.loc in g.captures else Colors.border[self.team]
        self.guide = GoPieceGuide(self)

class GoPieceGuide(Circle):
    def __init__(self, piece):
        super().__init__(piece.game, Layers.GUIDES, None, None, None, 2*piece_rad)
        self.piece = piece
        self.GETx = lambda _: self.piece.x
        self.GETy = lambda _: self.piece.y
        self.GETcolor = lambda _: Colors.guide[self.piece.team]
        self.GETvisible = lambda g: self.piece in g.guides

class GoVoronoi(Renderable):
    def render(self):
        ws, bs = [{p.loc for p in game.layers[Layers.PIECES[t]]} for t in teams]
        for p in ws:
            l = self.diagram.voronoi_vertices[p]
            for i in range(len(l)):
                p1, p2 = l[i], l[(i+1)%len(l)]
                if self.diagram.contiguities[p][(i+1)%len(l)] in bs and intersect_board(p1, p2):
                    drawSegment(self.game, Colors.territory, snap_to_circle(p1,p2), snap_to_circle(p2,p1))
                # drawSegment(self.game, (0,0,0), p1,p2)

class GoDebugger(Renderable):
    render = lambda self: (
        [(lambda col: [self.debugLine(col, *e) for e in self.game.edges[t] if set(e) <= cmp])([random.randint(0,255) for _ in '123']) for t in teams for cmp in self.game.components[t]],
        [self.debugLine(Colors.debug[0], p.loc, lib) for t in teams for p in self.game.layers[Layers.PIECES[t]] for lib in self.game.liberties[p.loc]]
        )

start_state = ('WHITE', {t:0 for t in teams}, {t:set() for t in teams})

game = Game(
    initialState=start_state,
    backgroundColor=Colors.background,
    scale=50
)

game.save_state = lambda: (game.turn, game.capturedCount.copy(), {team:[p.loc for p in game.layers[Layers.PIECES[team]]] for team in teams})
game.load_state = lambda x: (lambda turn, capCount, pieces: (
    game.clearLayer(Layers.GUIDES),
    game.add(game.nextPiece.guide, Layers.GUIDES),
    setattr(game.nextPiece.guide, 'visible', False),
    setattr(game.voronoi, 'diagram', Voronoi((-board_rad, -board_rad), (board_rad, board_rad))),
    [game.clearLayer(Layers.PIECES[team]) for team in teams+['GHOST']],
    [game.makePiece(team, *p) for team in teams for p in pieces[team]],
    setattr(game, 'turn', turn),
    setattr(game, 'capturedCount', capCount.copy()),
    setattr(game, 'guides', set()),
    updateLiberties(game),
    updateGraph(game),
    updateTerritory(game)
    ))(*x)

Circle(game, Layers.BOUNDARY, None, 0, 0, board_rad, 3).GETcolor = lambda g: Colors.boundary if game.rawMousePos == None or on_board(game.getMousePos()) else Colors.blocker

FixedText(game, Layers.COUNT, Colors.text['BLACK'], font, None, game.width-30,30, *'rt').GETtext = lambda g: '{} + {:5.1f} = {:5.1f}'.format(g.capturedCount['WHITE'], g.territory['BLACK'], g.capturedCount['WHITE'] + g.territory['BLACK'])
FixedText(game, Layers.COUNT, Colors.text['WHITE'], font, None, game.width-30,60, *'rt').GETtext = lambda g: '{} + {:5.1f} = {:5.1f}'.format(g.capturedCount['BLACK'], g.territory['WHITE'], g.capturedCount['BLACK'] + g.territory['WHITE'])
game.debugger = GoDebugger(game, Layers.DEBUG)
game.debugger.visible = False

game.rawMousePos = None
game.getMousePos = lambda: game.rawMousePos and game.point(*game.rawMousePos)

# debug
game.edges = {t:set() for t in teams}
game.components = {t:[] for t in teams}
game.captures = set()

# make a piece on team t at (x,y)
game.makePiece = lambda t,x,y: (GoPiece(game, t, x, y), game.voronoi.diagram.add((x,y)))

# remove pieces at {(x,y)} ps
game.removePieces = lambda ps: (lambda pcs: [(
    game.layers[Layers.PIECES[pc.team]].remove(pc), game.layers[Layers.GUIDES].remove(pc.guide),
    game.capturedCount.__setitem__(pc.team, game.capturedCount[pc.team]+1),
    game.voronoi.diagram.remove(pc.loc)
    ) for pc in pcs
    ])([pc for t in teams for pc in game.layers[Layers.PIECES[t]] if pc.loc in ps])

game.nextPiece = GoPiece(game, 'NEW', None, None)
game.nextPiece.GETteam = lambda g: g.turn
game.nextPiece.GETvisible = lambda g: g.getMousePos()
game.nextPiece.GETx = lambda g: g.getMousePos()[0]
game.nextPiece.GETy = lambda g: g.getMousePos()[1]
game.nextPiece.GETborder_color = lambda g: Colors.blocker if g.blockers or not on_board(game.getMousePos()) else Colors.capture if game.getMousePos() in game.captures else Colors.legal
game.nextPiece.GETfill_color = lambda g: Colors.newfill[g.turn]

game.voronoi = GoVoronoi(game, Layers.TERRITORY)

def attemptMove(game):
    updateMove(game)
    if game.blockers or not on_board(game.getMousePos()): return
    game.record_state()
    game.makePiece(game.turn, *game.getMousePos())
    game.removePieces(game.captures)
    game.turn = inc_turn[game.turn]
    [setattr(p.guide, 'visible', False) for t in teams for p in game.layers[Layers.PIECES[t]]]
    game.clearLayer(Layers.PIECES['GHOST'])
    game.nextPiece.guide.visible = False

    # times = []
    # times.append(time.perf_counter())
    updateLiberties(game)
    # times.append(time.perf_counter())
    updateGraph(game)
    updateTerritory(game)
    # times.append(time.perf_counter())
    # print(*[times[i]-times[i-1] for i in range(1,len(times))], sep='\n')
    # print()

updateLiberties = lambda game: setattr(game, 'liberties', {pc.loc: (lambda close_pcs, close_opps: {tan for pc2 in close_pcs for tan in double_tangents(pc.loc, pc2) if on_board(tan) and not any(overlap(tan, p) for p in close_pcs) and connected(pc.loc, tan, close_opps)})([pc2.loc for t2 in teams for pc2 in game.layers[Layers.PIECES[t2]] if pc2 != pc and sorta_nearby(pc2.loc,pc.loc)], [pc2.loc for pc2 in game.layers[Layers.PIECES[inc_turn[t]]] if sorta_nearby(pc2.loc, pc.loc)]) for t in teams for pc in game.layers[Layers.PIECES[t]]})

def updateMove(game, pos=None):
    if pos:
        game.rawMousePos = pos
    pos = game.getMousePos()
    if pos and on_board(pos):
        game.blockers = {p for p in sum((game.layers[Layers.PIECES[team]] for team in teams+['GHOST']),[]) if overlap(pos, p.loc)}

        opp = inc_turn[game.turn]
        pieces = {t:{p.loc for p in game.layers[Layers.PIECES[t]]} for t in teams}
        new_pc_w_es = {(pos,p) for p in pieces[game.turn] if nearby(pos,p)}
        pieces[game.turn].add(pos)
        all_pieces = union(iter(pieces.values()))

        # THE RULE: a piece is captured if there's no way to slide it continuously without bumping into opponent's pieces to an empty space
        # a 'liberty' is a location tangent to a piece which it can slide to, preventing capture
        # connected components of pieces that can slide to each others' locations are always captured together
        # when you place a piece, first any opponent's pieces are captured, and then your own
        # you're allowed to place a piece that gets immediately captured; this can even be useful because it might capture opponent's pieces first

        # figure out what we'll capture, starting with the opponent's pieces

        # graph of opponent's pieces accounting for new piece
        opp_edges = filter_edges(game.edges[opp], new_pc_w_es | boundary_cuts({pos}))

        # the pieces in the opponent's components we might capture (i.e. those with a piece within 6r), in components according to the new graph
        opp_cmps = components(union(cmp for cmp in game.components[opp] if any(sorta_nearby(pos, p) for p in cmp)), list(opp_edges))
        
        # an opponent's component is captured if...
        game.captures = union(cmp for cmp in opp_cmps if
                                # it's not an isolated piece with nothing nearby...
                                any(nearby(p, other) for p in cmp for other in all_pieces if p != other)
                                # and the new piece overlaps or blocks all the component's liberties...
                                and all(overlap(pos, lib) or not connected(p, lib, pieces[game.turn]) for p in cmp for lib in game.liberties[p])
                                # and none of the tangencies with the new piece are new liberties
                                and not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pc, tan, pieces[game.turn]) for pc in cmp for tan in double_tangents(pos,pc)))

        # after any opponent pieces are captured...
        pieces[opp] -= game.captures
        all_pieces = union(iter(pieces.values()))

        # we figure out which of our pieces get captured
        # some new edges are introduced, in two ways:
        # 1. edges with the new piece
        new_edges = filter_edges(new_pc_w_es, (lambda close_pcs: weak_edges(close_pcs) | boundary_cuts(close_pcs))({p for p in pieces[opp] if sorta_nearby(p, pos)}))
        # 2. edges which are de-broken by pieces being captured
        near_capture = {p for p in pieces[game.turn] if any(nearby(p,cap) for cap in game.captures)}
        new_edges |= filter_edges({e for e in game.potentialEdges[game.turn] if set(e)<=near_capture}, {e for e in game.potentialEdges[opp] if game.captures.isdisjoint(e)} | boundary_cuts(pieces[opp]))
        # some components are merged by the new edges
        my_cmps = components(None, list(new_edges), game.components[game.turn]+[{pos}])
        
        # one of our components is captured if...
        game.captures |= union(cmp for cmp in my_cmps if
                                # it's not an isolated piece with nothing nearby...
                                any(nearby(p, other) for p in cmp for other in all_pieces if p != other)
                                # and the new piece overlaps all the component's liberties (it can't block movement because it's on the same team)...
                                and all(overlap(pos, lib) for p in cmp-{pos} for lib in game.liberties[p])
                                # and none of the tangencies with the new piece are new liberties for an existing piece...
                                and not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pc, tan, pieces[opp]) for pc in cmp for tan in double_tangents(pos,pc))
                                # and, if this is the component of the new piece, none of its tangencies with any piece are new liberties
                                and (pos not in cmp or not any(on_board(tan) and not any(overlap(tan, p) for p in all_pieces) and connected(pos, tan, pieces[opp]) for pc in all_pieces for tan in double_tangents(pos,pc))))

    else: 
        game.blockers = set()
        game.captures = set()

def updateGraph(game):
    pieces = {t:[p.loc for p in game.layers[Layers.PIECES[t]]] for t in teams}
    w_es = {t:weak_edges(pieces[t]) for t in teams}
    game.edges = {t:filter_edges(w_es[t], w_es[inc_turn[t]] | boundary_cuts(pieces[inc_turn[t]])) for t in teams}
    game.potentialEdges = {t:w_es[t]-game.edges[t] for t in teams}
    game.components = {t:components(pieces[t], list(game.edges[t])) for t in teams}

def updateTerritory(game):
    game.territory = {t:sum(cell_area(game.voronoi.diagram.voronoi_vertices[pc.loc]) for pc in game.layers[Layers.PIECES[t]]) / pi * piece_rad**2 for t in teams}

piece_at = lambda pos, game: (lambda ps: ps[0] if ps else game.nextPiece)([p for t in teams for p in game.layers[Layers.PIECES[t]] if dist_sq(pos, p.loc) < piece_rad**2])

game.process = lambda: updateMove(game)

game.load_state(start_state)

# left click: place piece
game.click[1] = lambda e: attemptMove(game)
# middle click: toggle guide
game.click[2] = lambda e: (lambda g: setattr(g, 'visible', not g.visible))(piece_at(game.point(*e.pos), game).guide)
game.drag[-1] = lambda e: setattr(game, 'rawMousePos', e.pos)

game.keys.skipTurn = 117 # f
game.keys.placeGhost = 32 # space
game.keys.clearGhosts = 27 # escape

game.keyPress[game.keys.skipTurn] = lambda _: setattr(game, 'turn', inc_turn[game.turn])
game.keyPress[game.keys.placeGhost] = lambda _: None if game.blockers else (lambda ghost: setattr(ghost, 'GETcolor', lambda g: Colors.blocker if ghost in g.blockers else Colors.ghost))(Circle(game, Layers.PIECES['GHOST'], Colors.ghost, *game.getMousePos(), piece_rad))
game.keyPress[game.keys.clearGhosts] = lambda _: game.clearLayer(Layers.PIECES['GHOST'])

# debug tools
testGames = [
    ('BLACK', {'WHITE': 1, 'BLACK': 1}, {'WHITE': [(-7.220000000000001, 1.8399999999999999), (-6.2, 1.8599999999999994), (-4.849600000000001, 1.9071999999999996), (-3.838400000000001, 1.9328000000000003), (-2.5456000000000003, 1.984), (-1.5088000000000008, 1.984), (-0.1264000000000003, 2.0096), (0.9359999999999999, 1.9967999999999995), (2.3568000000000007, 2.0736000000000017), (3.4064000000000014, 2.150400000000001), (4.865600000000001, 2.1888000000000014), (5.876800000000001, 2.1888000000000014), (7.361600000000001, 2.201600000000001), (8.372800000000002, 2.2272000000000016), (7.3488000000000016, 0.08960000000000701), (8.411200000000001, 0.07680000000000664), (5.812800000000001, -0.06399999999999295), (4.776000000000002, 0.06400000000000716), (3.432000000000001, 0.06400000000000716), (2.420800000000001, 0.03840000000000732), (0.9513600000000011, -0.0844799999999939), (-0.062399999999999345, -0.09471999999999348), (-1.4038400000000024, -0.06399999999999917), (-2.438080000000003, -0.08447999999999878), (-3.810240000000003, -0.0742399999999992), (-4.813760000000003, -0.14591999999999894), (-6.1756800000000025, -0.17663999999999902), (-7.209920000000003, -0.2073599999999991), (-4.057120000000004, -7.641664000000003), (-3.071520000000004, -6.540864000000004), (-1.9451200000000037, -7.552064000000003), (-0.9467200000000044, -6.464064000000003), (0.11567999999999579, -7.526464000000003), (1.1652799999999957, -6.348864000000003), (2.1892799999999966, -7.372864000000003), (3.3028799999999983, -6.208064000000003), (4.262879999999997, -7.321664000000003), (5.402079999999998, -6.092864000000003), (-5.202520000000005, -6.606264000000012), (-6.758700000000008, 6.589665999999985), (-6.789420000000008, 5.565665999999985), (-5.888300000000008, 6.067425999999985), (-5.908780000000008, 5.012705999999985), (-4.997420000000008, 5.534945999999985), (-5.867820000000008, 7.070945999999985), (-4.966700000000008, 6.589665999999985), (-5.017900000000008, 7.603425999999985), (-6.820140000000008, 4.510945999999985), (-5.888300000000008, 3.927265999999985), (-4.976940000000008, 4.510945999999985), (-4.895020000000008, 3.476705999999985), (-4.034860000000008, 4.121825999999985), (-4.034860000000008, 5.135585999999985), (-4.024620000000008, 6.159585999999985), (-4.034860000000008, 7.183585999999985), (-3.1132600000000084, 6.6715859999999845), (-3.1337400000000075, 5.575905999999985), (-3.0927800000000083, 4.562145999999985), (-7.528716000000008, -2.784670000000016), (-6.2287160000000075, -4.344670000000017), (-3.128716000000008, -2.6846700000000165), (-0.2687160000000084, -3.964670000000017), (2.5712839999999932, -2.8246700000000162), (5.131283999999992, -3.744670000000016), (7.851283999999991, -3.464670000000017), (5.751283999999993, -2.3846700000000167), (-1.3487160000000085, -2.3846700000000167), (-8.388716000000008, -2.2646700000000166), (2.491283999999993, -1.7446700000000162), (-2.9687160000000077, -4.584670000000016), (-9.168716000000007, -1.4246700000000168), (4.311283999999993, 7.095329999999985), (7.2312839999999925, 4.875329999999984), (5.591283999999992, 7.195329999999984), (-2.0287160000000077, 9.115329999999984), (-1.5287160000000077, 7.815329999999985), (-3.588716000000008, 8.195329999999984), (-1.208716000000008, 3.995329999999985), (-0.08871600000000779, 3.5953299999999846), (4.911283999999992, 4.875329999999984), (8.871283999999992, 3.1953299999999842)], 'BLACK': [(-5.489599999999998, 0.9216000000000042), (-6.705599999999998, 0.8576000000000041), (-4.3375999999999975, 0.8960000000000035), (-3.147199999999998, 0.9984000000000046), (-1.9696000000000007, 0.947200000000004), (-0.8048000000000011, 1.1008000000000049), (0.3216000000000001, 0.9856000000000043), (1.7552000000000003, 1.0496000000000052), (2.984, 1.1648000000000058), (4.1616, 1.1904000000000048), (5.300800000000001, 1.1264000000000047), (6.683200000000001, 1.2800000000000074), (7.873600000000001, 1.2544000000000066), (6.670400000000001, -0.6783999999999937), (1.760320000000001, -0.7295999999999943), (4.064320000000002, -0.7603199999999957), (6.593600000000002, 2.9670400000000043), (4.0336000000000025, 2.9875200000000044), (1.5862400000000023, 2.8953600000000046), (-0.8099199999999991, 2.7929600000000026), (-3.2470399999999993, 2.7417600000000024), (-5.56128, 2.711040000000002), (-5.428160000000003, -0.9651199999999989), (-3.1241600000000025, -0.9139199999999992), (-0.7484800000000025, -0.842239999999999), (-4.133920000000004, -6.592064000000003), (-3.0203200000000043, -7.6544640000000035), (-2.009120000000004, -6.464064000000003), (-0.9211200000000037, -7.539264000000003), (0.10287999999999542, -6.4128640000000035), (1.178079999999996, -7.488064000000003), (2.266079999999995, -6.272064000000003), (3.238879999999998, -7.308864000000003), (4.326879999999997, -6.131264000000003), (5.338079999999998, -7.193664000000004), (-5.125720000000005, -7.707064000000012), (-0.39710000000000445, 5.312225999999986), (-0.3843000000000041, 6.323425999999985), (-0.39710000000000445, 7.360225999999986), (0.48251599999999595, 6.853857999999986), (0.5316679999999954, 5.731553999999986), (0.46613199999999555, 4.682977999999986), (0.48251599999999595, 7.869665999999986), (1.3099079999999956, 8.549601999999986), (1.400019999999996, 7.378145999999986), (1.400019999999996, 6.313185999999986), (1.4164039999999956, 5.174497999999986), (1.3672519999999961, 4.125921999999986), (2.3257159999999955, 4.5846739999999855), (2.3748679999999958, 5.772513999999986), (2.3666759999999956, 6.9603539999999855), (2.2929479999999955, 8.090849999999985), (3.259603999999996, 7.591137999999985), (3.2677959999999953, 6.386913999999985), (3.2514119999999957, 5.199073999999985), (-7.568716000000007, -3.9246700000000168), (-6.388716000000008, -3.124670000000016), (-4.488716000000007, -3.584670000000016), (-1.9887160000000073, -4.084670000000016), (1.2312839999999916, -2.8446700000000167), (3.871283999999992, -3.1846700000000165), (6.531283999999994, -3.8646700000000163), (6.911283999999993, -2.5246700000000164), (4.231283999999992, -2.2246700000000166), (-4.748716000000008, -2.3246700000000162), (0.11128399999999239, -2.0246700000000164), (2.1512839999999915, -3.9846700000000164), (-4.688716000000007, -4.784670000000016), (-7.008716000000008, -1.664670000000016), (4.831283999999992, 6.0153299999999845), (6.531283999999991, 5.995329999999985), (5.931283999999992, 4.195329999999984), (-0.42871600000000765, 9.175329999999985), (-1.768716000000008, 6.755329999999985), (-1.6287160000000078, 5.655329999999985), (3.9512839999999914, 4.235329999999985), (8.051283999999992, 3.955329999999984)]})
    ,
    ('BLACK', {'WHITE': 1, 'BLACK': 1}, {'WHITE': [(-3.430099999999997, -6.7109000000000005), (3.3316999999999997, -1.6439000000000092), (6.963699999999999, -1.6599000000000093), (5.1396999999999995, -4.61990000000001), (3.2996999999999996, 0.644099999999991), (5.1236999999999995, 2.1160999999999905), (7.075699999999999, 0.580099999999991), (-1.7483000000000066, 1.7200999999999929), (-2.068300000000007, 5.854499999999993), (0.46609999999999374, 4.024099999999994), (-3.962700000000007, 3.5760999999999927)], 'BLACK': [(-5.426899999999994, -4.12529999999999), (-1.5612999999999975, -4.099700000000001), (-5.593299999999996, -6.480500000000003), (-1.1132999999999953, -6.454900000000003), (-2.226899999999996, -8.554100000000004), (-5.094099999999997, -1.6037), (-1.9452999999999978, -1.5269000000000004), (2.499699999999999, -3.49990000000001), (7.491699999999998, -3.62790000000001), (3.7156999999999982, -6.13990000000001), (5.747699999999998, -6.55590000000001), (-3.924300000000007, 1.5024999999999928), (-4.205900000000007, 5.611299999999993), (-6.151500000000007, 3.371299999999993)]})
    ,
    ('WHITE', {'WHITE': 1, 'BLACK': 0}, {'WHITE': [], 'BLACK': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804), (-0.6803124999999728, -5.4562500000000265)]})
    ,
    ('BLACK', {'WHITE': 0, 'BLACK': 0}, {'WHITE': [(1.3331250000000239, -4.4271875000000165)], 'BLACK': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804)]})
    ,
    ('BLACK', {'BLACK': 1, 'WHITE': 0}, {'BLACK': [], 'WHITE': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804), (-0.6803124999999728, -5.4562500000000265)]})
    ,
    ('WHITE', {'BLACK': 0, 'WHITE': 0}, {'BLACK': [(1.3331250000000239, -4.4271875000000165)], 'WHITE': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804)]})
    ,
    ('WHITE', {'BLACK': 0, 'WHITE': 1}, {'WHITE': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804), (-2.0, 1.5999999999999996), (4.4399999999999995, 5.24), (-4.08, -3.2199999999999998), (-4.86, -5.58), (-4.744999999999996, 5.1650000000000045), (1.2050000000000036, 6.690000000000005), (5.155000000000003, -1.7849999999999966), (7.905000000000003, -2.1599999999999966), (-6.894999999999996, -4.009999999999996), (-0.2949999999999964, 0.31500000000000483), (4.555000000000005, 0.4150000000000045), (-3.6199999999999957, 7.765000000000004)], 'BLACK': [(1.3331250000000239, -4.4271875000000165), (-1.42, 5.619999999999999), (6.940000000000001, 0.8599999999999994), (-7.04, -1.5199999999999996), (-2.8600000000000003, -7.6), (-3.5599999999999996, -0.6799999999999997), (-6.744999999999996, 2.9650000000000034), (0.855000000000004, 4.115000000000004), (6.480000000000006, 4.7900000000000045), (5.880000000000004, -5.634999999999996), (3.0050000000000043, -7.934999999999996), (-5.994999999999996, 0.4650000000000034), (3.8300000000000036, 2.6650000000000045), (-1.269999999999996, 7.940000000000005), (-4.144999999999996, 2.765000000000004), (-8.48, 0.7799999999999994)]})
    ,
    ('WHITE', {'BLACK': 0, 'WHITE': 1}, {'WHITE': [(1.2159375000000239, -6.6146875000000165), (3.442500000000024, -5.6381250000000165), (3.364375000000024, -3.4115625000000165), (1.6456250000000239, -1.9271875000000165), (-0.5028124999999761, -2.5131250000000165), (1.9996875000000234, 0.7637499999999804), (-2.0, 1.5999999999999996), (4.4399999999999995, 5.24), (-4.08, -3.2199999999999998), (-4.86, -5.58), (-4.744999999999996, 5.1650000000000045), (1.2050000000000036, 6.690000000000005), (5.155000000000003, -1.7849999999999966), (7.905000000000003, -2.1599999999999966), (-6.894999999999996, -4.009999999999996), (-0.2949999999999964, 0.31500000000000483), (4.555000000000005, 0.4150000000000045), (-3.6199999999999957, 7.765000000000004)], 'BLACK': [(1.3331250000000239, -4.4271875000000165), (-1.42, 5.619999999999999), (6.940000000000001, 0.8599999999999994), (-7.04, -1.5199999999999996), (-2.8600000000000003, -7.6), (-3.5599999999999996, -0.6799999999999997), (-6.744999999999996, 2.9650000000000034), (0.855000000000004, 4.115000000000004), (6.480000000000006, 4.7900000000000045), (5.880000000000004, -5.634999999999996), (3.0050000000000043, -7.934999999999996), (-5.994999999999996, 0.4650000000000034), (3.8300000000000036, 2.6650000000000045), (-1.269999999999996, 7.940000000000005), (-4.144999999999996, 2.765000000000004)]})
    ,
]

game.numKey = lambda n: (game.record_state(), game.load_state(testGames[n])) if n<len(testGames) else print(str(n)+' not saved') # load presaved game for debugging

game.keys.printState = 13 # enter
game.keys.toggleDebug = 303 # right shift

game.keyPress[game.keys.printState] = lambda _: print(game.save_state())
game.keyPress[game.keys.toggleDebug] = lambda _: setattr(game.debugger, 'visible', not game.debugger.visible)

while 1: 
    game.update()
    # print(sum(cell_area(game.voronoi.diagram.voronoi_vertices[pc.loc]) for t in teams for pc in game.layers[Layers.PIECES[t]]))
    # print([cell_area( game.voronoi.diagram.voronoi_vertices[pc.loc]) for t in teams for pc in game.layers[Layers.PIECES[t]]] )