from math import atan2, pi, cos, sin

# for debugging
trace = lambda x, *y: (print(x), print(*y),x)[2]
tracefn = lambda f: lambda *args: trace(f(*args), *args)

class Point:
    def __init__(self, x, y, r=0, theta=0):
        self.x = x + r * cos(theta)
        self.y = y + r * sin(theta)
        self.coords = (self.x,self.y)
    __iter__ = lambda self: iter(self.coords)
    __getitem__ = lambda self, v: self.coords[v]
    __repr__ = lambda self: "Point{}".format(self.coords)
    __eq__ = lambda self, other: isinstance(other, Point) and self.coords == other.coords
    __ne__ = lambda self, other: not self == other
    __hash__ = lambda self: hash(self.coords)
    __bool__ = lambda self: True
    # adding, subtracting, and scaling vectors
    __add__ = lambda p1, p2: Point(*(p1[i]+p2[i] for i in range(2)))
    __sub__ = lambda p1, p2: Point(*(p1[i]-p2[i] for i in range(2)))
    __mul__ = lambda p, c: Point(*(p[i]*c for i in range(2)))
    __rmul__ = lambda p, c: Point(*(c*p[i] for i in range(2)))
    __truediv__ = lambda p, c: Point(*(p[i]/c for i in range(2)))
    # +p: square length of p
    __pos__ = lambda p: sum(x**2 for x in p)
    # p @ l: vector in the direction of p with length l
    __matmul__ = lambda p, l: Point(*(l*x/(+p)**.5 for x in p)) if p != Point(0,0) else Point(0,0)
    # ~p: p rotated tau/4 clockwise
    __invert__ = lambda p: Point(p.y, -p.x)
    # p1 % p2: midpoint of p1 and p2
    __mod__ = lambda p1, p2: (p1 + p2)/2
    # p1 ^ p2: determinant  of [p1 p2] (note: the coordinate system is left-handed, so this is negative what you might expect)
    __xor__ = lambda p1, p2: p1.x*p2.y - p1.y*p2.x
    # p1 >> p2: square distance from p1 to p2
    __rshift__ = lambda p1, p2: +(p1-p2)
    # p1 & p2: dot product of p1 and p2
    __and__ = lambda p1, p2: sum(p1[i]*p2[i] for i in range(2))


# area of polygon with vertices pts, counterclockwise
polygon_area = lambda pts: sum(pts[i] ^ pts[(i+1)%len(pts)] for i in range(len(pts))) / 2

# is x 'above' the line from p1 to p2; i.e. on your left when going from p1 to p2?
above_line = lambda x, p1, p2: (p2-p1)^(x-p1) < 0
# do line segments a-b and x-y intersect?
intersect_segments = lambda a,b,x,y: above_line(a,b,x) != above_line(a,b,y) and above_line(x,y,a) != above_line(x,y,b)

# is b between a and c, assuming all three are colinear?
between = lambda a, b, c: (a.x-b.x)*(b.x-c.x) >= 0 and (a.y-b.y)*(b.y-c.y) >= 0
# signed distance x is above the line p1-p2 ('above' means on the left when moving from p1 to p2)
dist_above_line = lambda x, p1, p2: (x-p1)^(p2-p1) / (p1 >> p2)**.5 if p1 != p2 else (x>>p1)**.5
# signed distance from p1 to the projection of x onto the line p1-p2. dist_above_line and dist_along_line give x in an orthonormal basis with origin p1.
dist_along_line = lambda x, p1, p2: (x-p1) & ((p2-p1) @ 1)
# unsigned distanced x is from the line p1-p2
dist_to_line = lambda x, p1, p2: abs(dist_above_line(x,p1,p2))
# distance from x to the line segment p1-p2
dist_to_segment = lambda x, p1, p2: dist_to_line(x,p1,p2) if 0 < dist_along_line(x, p1, p2) < (p1>>p2)**.5 else min(x>>p1,x>>p2)**.5
# distance from x to the ray from p in dir
dist_to_ray = lambda x, p, dir: dist_to_line(x,p,p+dir) if 0 < dist_along_line(x, p, p+dir) else (x>>p)**.5
# distance from x to the circle with centered r centered at p
dist_to_circle = lambda x, p, r: abs((x>>p)**.5 - r)
# point on line p1-p2 closest to x
nearest_on_line = lambda x, p1, p2: x - (~(p2-p1) @ dist_above_line(x,p1,p2))
# point on line segment p1-p2 closest to x
nearest_on_segment = lambda x, p1, p2: nearest_on_line(x, p1, p2) if 0 < dist_along_line(x, p1, p2) < (p1>>p2)**.5 else min(p1, p2, key = lambda p: x>>p)
# point on circle with radius r centered at p closest to x
nearest_on_circle = lambda x, p, r: p + ((x-p) @ r) if x != p else p + Point(r,0)
# point on disk with radius r centered at p closest to x; if x is in the circle it's x (up to floating point)
nearest_on_disk = lambda x, p, r: p + ((x-p) @ min(r, (x >> p)**.5))

# the result of moving p1 towards p2 until it's on the circle of radius r centered at p
slide_to_circle = lambda p1, p2, p, r: p1 if p1>>p < r**2 else (lambda nearest: nearest + ((p1-p2) @ (r**2 - (nearest>>p))**.5))(nearest_on_line(p,p1,p2))
# area of the portion of the circle of radius r centered at p on the side of chord a-b, assuming a -> b is counterclockwise
sliver_area = lambda a, b, p, r: (atan2(*(b-p))-atan2(*(a-p)))%(2*pi) * r**2 / 2 - polygon_area([p, b, a])
# the list of line segments in the intersection of the disk of radius r centered at the origin and the polygon with points pts
intersect_polygon_circle_segments = lambda pts, p, r: [[slide_to_circle(pts[i], pts[(i+1)%len(pts)], p, r), slide_to_circle(pts[(i+1)%len(pts)], pts[i], p, r)] for i in range(len(pts)) if pts[i]>>p < r**2 or pts[(i+1)%len(pts)]>>p < r**2 or (lambda nearest: between(pts[i], nearest, pts[(i+1)%len(pts)]) and nearest>>p < r**2)(nearest_on_line(p, pts[i], pts[(i+1)%len(pts)]))]
# area of the intersection of the disk of radius r centered at p and the polygon with vertices pts
intersect_polygon_circle_area = lambda pts, p, r: (lambda segments: polygon_area(sum(segments, [])) + sum(sliver_area(segments[(i+1)%len(segments)][0], segments[i][1], p, r) for i in range(len(segments)) if segments[i][1] != segments[(i+1)%len(segments)][0]) or r**2*pi)(intersect_polygon_circle_segments(pts, p, r))

# combat floating point errors. In particular, tangent circles shouldn't intersect
epsilon = 10**-10
# intersections of circles of radius r1 and r2 centered at p1 or p2. a tuple with either 0 or 2 elements. if r2 is not given, both circles have radius r1
# order: given (a,b) where (a,p2,b) is counterclockwise around p1
intersect_circles = lambda p1, p2, r1, r2=None: (lambda r2, dsq: (lambda m: (lambda d: (m-d, m+d)
            )(~(p2-p1) @ ((r1**2-(p1>>m) + epsilon)**.5))
        )(p1 + (p2-p1)@((r1**2-r2**2+dsq) / 2 / (dsq**.5))) if abs(r1-r2) < dsq**.5 < r1+r2 else ()
    )(r2 or r1, p1>>p2)
# intersections of line a-b and circle of radius r centered at p. a tuple with either 0 or 2 elements.
intersect_line_circle = lambda a, b, p, r: (lambda dist: (lambda m,d: (m+d,m-d))(nearest_on_line(p,a,b), (b-a) @ ((r**2-dist**2)**.5 + epsilon)) if dist<r else ()
    )(dist_to_line(p,a,b))
# intersections of segment a-b and circle of radius r centered at p. a tuple with 0 to 2 elements.
intersect_segment_circle = lambda a, b, p, r: tuple(x for x in intersect_line_circle(a,b,p,r) if between(a,x,b))

# intersection of the line p1-p2 and the line Z=postion, where Z={0:x,1:y}[axis]. Usually this is the border of the screen
intersect_line_border = lambda p1, p2, axis, position: Point(*((position,)*(1-axis)+(p1[1-axis] + (p2-p1)[1-axis] * (position-p1[axis]) / (p2-p1)[axis],)+(position,)*axis))

# is point p in the convex polygon with vertices poly, in counterclockwise order?
point_in_polygon = lambda p, poly: all(above_line(p, poly[i-1], poly[i]) for i in range(len(poly)))

def intersect_polygon_halfplane(polygon, axis, sign, position):
    # the intersection of the polygon (list of points) with the half-plane described by axis, sign, position
    # the equation for the half-plane is <Z><rel>position, where Z={0:x,1:y}[axis] and rel={1:>,-1:<}[sign]
    # e.g. (_, 1, -1, 3) means the half-plane is given by y<3
    half_plane = lambda p: (p[axis] - position)*sign > 0
    vertices = []
    for i in range(len(polygon)):
        if half_plane(polygon[i]):
            vertices.append(polygon[i])
        else:
            vertices.extend(intersect_line_border(polygon[i], polygon[j], axis, position) for j in [i-1,(i+1)%len(polygon)] if half_plane(polygon[j]))
    return [vertices[i] for i in range(len(vertices)) if vertices[i-1] != vertices[i]]

def convex_hull(points):
    # a list of points on the convex hull, in counterclockwise order (increasing angle)
    if points==[]: return []
    topmost = min(points, key=lambda p:p.y)
    ans = [topmost]
    for p in sorted(set(points)-{topmost}, key=lambda p:atan2(*(p-topmost))):
        while len(ans)>1 and above_line(p, *ans[-1:-3:-1]):
            ans.pop()
        ans.append(p)
    return ans

# do the intervals xs cover interval? intervals are tuples of endpoints and are closed; assumes xs is sorted
interval_cover_sorted = lambda xs, interval: xs[0][0] <= interval[0] and interval_cover(xs[1:], (max(interval[0], xs[0][1]), interval[1])) if xs else interval[0] >= interval[1]
# do the intervals xs cover interval? doesn't assume xs is sorted
interval_cover = lambda xs, interval: interval_cover_sorted(sorted(xs), interval)
# do the intervals xs cover all angles (0 to tau)? endpoints are taken mod tau, and assumed to be given in counterclockwise (increasing) direction
interval_cover_circle = lambda xs: interval_cover([interval for a,b in xs for interval in ([(a%(2*pi), b%(2*pi))] if b%(2*pi) > a%(2*pi) else [(a%(2*pi), 2*pi),(0, b%(2*pi))])], (0,2*pi))

def intersect_polygon_circle_arcs(pts, p, r):
    # list of angular intervals of arcs of the circle of radius r centered at p contained in the polygon with vertices pts
    # assumes pts are in counterclockwise order; otherwise it's the arcs not in the polygon
    starts, ends = [], []
    for i in range(len(pts)):
        if pts[i]>>p >= r**2:
            if nearest_on_segment(p, pts[i], pts[(i+1)%len(pts)])>>p < r**2:
                ends.append(atan2(*(slide_to_circle(pts[i], pts[(i+1)%len(pts)], p, r) - p)))
            if nearest_on_segment(p, pts[i], pts[i-1])>>p < r**2:
                starts.append(atan2(*(slide_to_circle(pts[i], pts[i-1], p, r) - p)))

    return [(s, min(ends, key=lambda e: (e-s)%(2*pi))) for s in starts]

## for computing voronoi diagrams
## by josh brunner
def circumcenter(p1,p2,p3):
    #rotate and sum helper function because you do it alot
    f = lambda g:g(p1,p2,p3)+g(p2,p3,p1)+g(p3,p1,p2)
    num = lambda i:f(lambda a,b,c: (a[1-i]-b[1-i])*a[1-i]*b[1-i] + a[1-i]*c[i]*c[i] - c[1-i]*a[i]*a[i])
    denom = lambda i:f(lambda a,b,c: 2 * (a[i]*b[1-i] - a[i]*c[1-i]))
    return Point(num(0)/denom(0), num(1)/denom(1))
class Voronoi:
    def __init__(self, p1, p2):
        """
        p1, p2 are points that define a bounding box which you guarentee that all of the points of your voronoi diagram lie within
        Behavior is undefined for inserted points outside this bounding box. """
        self.box = (p1,p2)
        center = ((p1[0]+p2[0])/2,(p1[1]+p2[1])/2)
        a,b = Point((p1[0]-center[0])* 8+center[0],center[1]),Point(center[0],(p1[1]-center[1])* 8+center[1])
        c,d = Point((p1[0]-center[0])*-8+center[0],center[1]),Point(center[0],(p1[1]-center[1])*-8+center[1])
        if (abs(p1[0]-p2[0])<abs(p1[1]-p2[1])):
            a,b,c,d = b,c,d,a
        #note: to be technically correct, we actually need to scale abc to be farther from the center.
        self.points = [a,b,c,d]
        #for each point, a list of points whose voronoi cells are adjacent.
        #This can be thought of as a cyclical list. The list is in clockwise (decreasing angle) order, but the start and end are arbitrary.
        self.contiguities = {a:[b,d,"inf"], b:[c,d,a,"inf"], c:[d,b,"inf"],d:[a,b,c,"inf"]}
        #for each point, the list of vertices which make up its voronoi cell.
        #This can be thought of as a cyclical list. The list is in clockwise (decreasing angle) order, but the start and end are arbitrary.
        #voronoi_vertices[a][n] is the circumcenter of the points a, contiguities[a][n], contiguities[a][n+1] (taking modulo as necessary to make the indicies work out)
        f = lambda x,y,i:((x[i]+y[i])/2-center[i])*10+center[i]
        lc = circumcenter(a,b,d)
        rc = circumcenter(b,c,d)
        inf_ab = Point(f(a,b,0),f(a,b,1))
        inf_bc = Point(f(b,c,0),f(b,c,1))
        inf_cd = Point(f(c,d,0),f(c,d,1))
        inf_da = Point(f(d,a,0),f(d,a,1))
        self.voronoi_vertices = {a:[lc,inf_da,inf_ab],b:[rc,lc,inf_ab,inf_bc],c:[rc,inf_bc,inf_cd],d:[lc,rc,inf_cd,inf_da]}
    def nearest(self, p):
        return min(self.points, key=lambda q:p>>q)
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
                if  r_dist > .5 >= s_dist:
                    d[0] = i%k
                    self.contiguities[p].append(self.contiguities[q][i%k])
                    q_next = self.contiguities[q][i%k]
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
                r = center>>a
                #if no other point is in the circumcircle, so this is a valid triangle in the delaunay triagulation.
                v = (a[1]-c[1],c[0]-a[0])
                m = ((a[0]+c[0])/2,(a[1]+c[1])/2)
                flag = ((p[0]-m[0])*v[0] + (p[1]-m[1])*v[1])*((b[0]-m[0])*v[0] + (b[1]-m[1])*v[1]) < 0
                if all(q in {a,b,c} or q>>center >= r for q in l) and flag:
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

# returns list of edges in MST
def minimum_spanning_tree(points):
    components = {p:{p} for p in points}
    ans = []
    for p,q in sorted([(p,q) for i,p in enumerate(points) for q in points[:i]], key = lambda e: Point.__rshift__(*e)):
        if components[p] != components[q]:
            ans.append((p,q))
        new = components[p] | components[q]
        for x in new: components[x] = new
    return ans
minimum_spanning_tree_size = lambda points: sum((p>>q)**.5 for p,q in minimum_spanning_tree(points))