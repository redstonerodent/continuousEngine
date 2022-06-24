from continuousEngine import *

class Layers:
	BOARD = 1
	WALLS = 6
	PAWNS = 5
	GHOSTS = 3

class Colors:
	BACKGROUND = (181, 108, 53)
	BOARD = (0,0,0)
	WALLS = (219, 159, 75)
	PAWN = {'white':(255,255,255), 'brown':(105, 63, 24), 'black':(0,0,0), 'red':(201, 26, 6)}
	SELECTED = (0,255,0)
	WRONG = (255,0,0)
	TURN = (0,200,200)

class Constants:
	TEAMS = ['white', 'brown', 'black', 'red']
	# game units
	PAWN_RAD = .5
	WALL_LEN = 2
	BOARD_RAD = 5
	PAWN_START = 4
	MOVE_DIST = 1

class Wall(Segment):
	def __init__(self, game, p1, p2, layer = Layers.WALLS, color = Colors.WALLS):
		super().__init__(game, layer, color, p1, p2)

class Pawn(BorderDisk):
	def __init__(self, game, team, loc):
		super().__init__(game, Layers.PAWNS, Colors.PAWN[team], None, loc, Constants.PAWN_RAD)
		self.team = team
		self.GETborder_color = lambda g: \
			Colors.SELECTED if g.selected == self or g.current_pawn == self and self in g.blockers else \
			Colors.WRONG if self in g.blockers else \
			Colors.TURN if g.current_pawn == self else \
			Colors.PAWN[self.team]

class Quoridor(Game):
	def __init__(self, teams=2, **kwargs):
		self.team_count = int(teams)
		super().__init__(backgroundColor=Colors.BACKGROUND, name='continuous quoridor', spread=Constants.BOARD_RAD, **kwargs)

		Circle(self, Layers.BOARD, Colors.BOARD, Point(0,0), Constants.BOARD_RAD)

		self.wall_ghost = Wall(self, None, None, Layers.GHOSTS, Colors.SELECTED)
		self.wall_ghost.GETvisible = lambda g: g.state == 'wall'
		self.wall_ghost.GETp1 = lambda g: g.selected
		self.wall_ghost.GETp2 = lambda g: g.selected + (g.mousePos() - g.selected) @ Constants.WALL_LEN

		self.pawn_ghost = Disk(self, Layers.GHOSTS, None, None, Constants.PAWN_RAD)
		self.pawn_ghost.GETvisible = lambda g: g.state == 'pawn'
		self.pawn_ghost.GETcolor = lambda g: Colors.PAWN[g.turn]
		self.pawn_ghost.GETloc = lambda g: nearest_on_disk(g.mousePos(), g.selected.loc, Constants.MOVE_DIST)

		self.reset_state()

		self.click[1] = lambda e: self.on_click(self.point(*e.pos))

	def load_state(self, state):
		for l in [Layers.WALLS, Layers.PAWNS]: self.clearLayer(l)
		self.turn, teams, walls, pawns = state
		self.teams = teams.copy()
		[Wall(self, Point(*p1), Point(*p2)) for p1, p2 in walls]
		[Pawn(self, team, Point(*loc)) for team,loc in pawns]
		self.prep_turn()

	save_state = lambda self: (self.turn, self.teams.copy(), [(w.p1.coords, w.p2.coords) for w in self.layers[Layers.WALLS]], [(p.team, p.loc.coords) for p in self.layers[Layers.PAWNS]])

	def make_initial_state(self):
		teams = Constants.TEAMS[:self.team_count]
		return (teams[0], teams, [], [(t, Point(0,0,Constants.PAWN_START,2*pi*i/len(teams)).coords) for i,t in enumerate(teams)])

	def on_click(self, loc):
		if self.state == 'start':
			if Point(0,0) >> loc > Constants.BOARD_RAD**2: return
			on_pawns = [p for p in self.layers[Layers.PAWNS] if p.loc >> loc < Constants.PAWN_RAD**2]
			if len(on_pawns)>1: raise ValueError
			if on_pawns:
				if on_pawns[0].team == self.turn:
					self.state = 'pawn'
					self.selected = on_pawns[0]
			else:
				self.state = 'wall'
				self.selected = loc
		elif self.state == 'pawn':
			self.attemptMove({'player':self.turn, 'type':'pawn', 'location':loc.coords})
		elif self.state == 'wall':
			self.attemptMove({'player':self.turn, 'type':'wall', 'p1':self.selected.coords, 'p2':loc.coords})

	def attemptGameMove(self, move):
		if move['type'] == 'pawn':
			start = self.current_pawn.loc
			end = Point(*move['location'])
			end = nearest_on_disk(end, start, Constants.MOVE_DIST)
			if Point(0,0) >> end > (Constants.BOARD_RAD - Constants.PAWN_RAD)**2: return
			self.record_state()
			self.current_pawn.loc = end
		elif move['type'] == 'wall':
			p1 = Point(*move['p1'])
			p2 = Point(*move['p2'])
			p2 = p1 + (p2-p1) @ Constants.WALL_LEN
			if Point(0,0) >> p1 > Constants.BOARD_RAD**2: return
			if Point(0,0) >> p2 > Constants.BOARD_RAD**2: return
			self.record_state()
			Wall(self, p1, p2)
		return True

	def prep_turn(self):
		self.state = 'start'
		self.selected = None
		self.blockers = []
		self.current_pawn = next(p for p in self.layers[Layers.PAWNS] if p.team == self.turn)

	def process(self):
		if self.state == 'start':
			blockers = [p for p in self.layers[Layers.PAWNS] if p.loc >> self.mousePos() < Constants.PAWN_RAD**2]
		if self.state == 'pawn':
			blockers = [p for p in self.layers[Layers.PAWNS] if p != self.selected and p.loc >> self.pawn_ghost.loc < (2*Constants.PAWN_RAD)**2] + \
				[w for w in self.layers[Layers.WALLS] if intersect_segment_disk(w.p1, w.p2, self.pawn_ghost.loc, Constants.PAWN_RAD)]
		if self.state == 'wall':
			blockers = [p for p in self.layers[Layers.PAWNS] if intersect_segment_disk(self.wall_gost.p1, self.wall_ghost.p2, p.loc, Constants.PAWN_RAD)] + \
				[w for w in self.layers[Layers.WALLS] if intersect_segments(self.wall_gost.p1, self.wall_ghost.p2, w.p1, w.p2)]

if __name__=='__main__':
    pygame.init()
    run_local(Quoridor, sys.argv[1:])