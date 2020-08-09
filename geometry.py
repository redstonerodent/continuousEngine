# points are tuples (x,y)

# adding, subtracting, and scaling vectors
add = lambda p1, p2: tuple(p1[i]+p2[i] for i in range(2))
sub = lambda p1, p2: tuple(p1[i]-p2[i] for i in range(2))
scale = lambda p, c: tuple(p[i]*c for i in range(2))
# determinant of [p1 p2], useful for area
det = lambda p1, p2: p1.x*p2.y - p1.y*p2.x


def intersectHalfPlane(polygon, axis, sign, position):
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
                (position,)*(1-axis)+(polygon[i][1-axis] + sub(polygon[j],polygon[i])[1-axis] * (position-polygon[i][axis]) / sub(polygon[j],polygon[i])[axis],)+(position,)*axis
                for j in [i-1,(i+1)%len(polygon)] if half_plane(polygon[j]))
    return [vertices[i] for i in range(len(vertices)) if vertices[i-1] != vertices[i]]


# square distance between p1 and p2
dist_sq = lambda p1,p2: sum(x**2 for x in sub(p1,p2))
# signed distance x is above the line p1-p2 ('above' means on the left when moving from p1 to p2)
dist_above_line = lambda x, p1, p2: (p1[0]*p2[1]+p2[0]*x[1]+x[0]*p1[1]-p1[1]*p2[0]-p2[1]*x[0]-x[1]*p1[0]) / dist_sq(p1,p2)**.5


# point on line p1-p2 closest to p
nearest_on_line = lambda p, p1, p2: ((p[0]*(p2[0]-p1[0])**2+p1[0]*(p2[1]-p1[1])**2+(p[1]-p1[1])*(p2[0]-p1[0])*(p2[1]-p1[1])) / dist_sq(p1,p2) , (p[1]*(p2[1]-p1[1])**2+p1[1]*(p2[0]-p1[0])**2+(p[0]-p1[0])*(p2[0]-p1[0])*(p2[1]-p1[1])) / dist_sq(p1,p2))
