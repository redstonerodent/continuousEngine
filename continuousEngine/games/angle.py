from continuousEngine import *

class Layers:
    NEWEDGE = 1
    EDGE = 2
    CLUE = 4
class Colors:
    CLUE = {3:(200,0,0), 4:(0,200,0), 5:(0,0,200)}
    CLUE_BORDER = (30,30,30)
    EDGE = (0,0,0)
    NEWEDGE = (0,0,255)

class Constants:
    CLUE_RAD = 20
    CLUE_BORDER = 3

class Clue(PolygonIcon):
    def __init__(self, game, center, sides):
        # 3=acute, 4=right, 5=obtuse
        super().__init__(game, Layers.CLUE, center, sides,
                Colors.CLUE[sides], Colors.CLUE_BORDER, Constants.CLUE_RAD, Constants.CLUE_BORDER)

class Edges(Renderable):
    def __init__(self, game, segments):
        super().__init__(game, Layers.EDGE)
        self.segments = segments
    def render(self):
        for e in self.segments:
            drawSegment(self.game, Colors.EDGE, *e)


class Angle(Game):
    def __init__(self, **kwargs):
        self.puzzle = [
            ((0,0), 3),
            ((0,1), 4),
            ((1,1), 5),
        ]

        super().__init__(name='angle loop', **kwargs)

        newedge = Segment(self, Layers.NEWEDGE, Colors.NEWEDGE, None, None)
        newedge.GETp2 = lambda g: g.mousePos()
        newedge.GETvisible = lambda g: newedge.p1 and newedge.p2

        self.reset_state()

        nearest_clue = lambda p: min(self.layers[Layers.CLUE], key=lambda c: p >> c.center)

        self.click[1] = lambda e: setattr(newedge, 'p1', nearest_clue(self.point(*e.pos)).center)

        def mouseup(e):
            if e.button != 1: return
            self.record_state()
            p = nearest_clue(self.point(*e.pos)).center
            if p == newedge.p1:
                pass
            elif {newedge.p1, p} in self.edges.segments:
                self.edges.segments.remove({newedge.p1, p})
            else:
                self.edges.segments.append({newedge.p1, p})
            newedge.p1 = None
            print(self.edges.segments)

        self.handlers[pygame.MOUSEBUTTONUP] = mouseup

    def load_state(self, state):
        clues, segments = state
        for l in [Layers.CLUE, Layers.EDGE]: self.clearLayer(l)
        for c, s in clues: Clue(self, Point(*c), s)
        self.edges = Edges(self, [{Point(*p1), Point(*p2)} for p1, p2 in segments])

    def save_state(self):
        return ([(clue.center.coords, clue.sides) for clue in self.layers[Layers.CLUE]],
                [(p1.coords, p2.coords) for p1, p2 in self.edges.segments])

    def make_initial_state(self):
        return (self.puzzle, [])



if __name__=="__main__":
    pygame.init()
    run_local(Angle, sys.argv[1:])
