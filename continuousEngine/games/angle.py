from continuousEngine import *

class Layers:
    EDGES = 2
    CLUES = 4

class Colors:
    CLUE = {3:(200,0,0), 4:(0,200,0), 5:(0,0,200)}
    CLUE_BORDER = (0,0,0)

class Constants:
    CLUE_RAD = 20
    CLUE_BORDER = 3

class Clue(PolygonIcon):
    def __init__(self, game, loc, sides):
        # 3=acute, 4=right, 5=obtuse
        super().__init__(game, Layers.CLUES, loc, sides,
                Colors.CLUE[sides], Colors.CLUE_BORDER, Constants.CLUE_RAD, Constants.CLUE_BORDER)

class Angle(Game):
    def __init__(self, **kwargs):
        super().__init__(name='angle loop', **kwargs)

        Clue(self, Point(0,0), 3)
        Clue(self, Point(0,1), 4)
        Clue(self, Point(1,1), 5)

if __name__=="__main__":
    pygame.init()
    run_local(Angle, sys.argv[1:])
