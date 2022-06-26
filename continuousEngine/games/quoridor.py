from continuousEngine import *

class Layers:
	BOARD = 1
	WALLS = 8
	PAWNS = 4
	GHOSTS = 6
	GUIDE = 3

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
	def __init__(self, game, p1, p2, layer = Layers.WALLS):
		super().__init__(game, layer, None, p1, p2)
		self.GETcolor = lambda g: Colors.WRONG if self in g.blockers else Colors.WALLS

class Pawn(BorderDisk):
	def __init__(self, game, team, loc):
		super().__init__(game, Layers.PAWNS, Colors.PAWN[team], None, loc, Constants.PAWN_RAD)
		self.team = team
		self.GETborder_color = lambda g: \
			Colors.SELECTED if g.current_pawn == self and self in g.blockers and g.state == 'start' else \
			Colors.WRONG if self in g.blockers else \
			Colors.TURN if g.current_pawn == self else \
			Colors.PAWN[self.team]

class Quoridor(Game):
	def __init__(self, teams=2, **kwargs):
		self.team_count = int(teams)
		super().__init__(backgroundColor=Colors.BACKGROUND, name='continuous quoridor', spread=Constants.BOARD_RAD, **kwargs)

		self.border = Circle(self, Layers.BOARD, Colors.BOARD, Point(0,0), Constants.BOARD_RAD)
		# self.border.GETcolor = lambda g: [Colors.BOARD, Colors.WRONG][g.border in g.blockers]

		wall_ghost = Wall(self, None, None, Layers.GHOSTS)
		wall_ghost.GETvisible = lambda g: g.state == 'wall'
		wall_ghost.GETcolor = lambda g: Colors.WRONG if g.blockers else Colors.SELECTED
		wall_ghost.GETp1 = lambda g: g.selected
		wall_ghost.GETp2 = lambda g: g.wall_end(g.selected, g.mousePos())

		pawn_ghost = BorderDisk(self, Layers.GHOSTS, None, None, None, Constants.PAWN_RAD)
		pawn_ghost.GETvisible = lambda g: g.state == 'pawn'
		pawn_ghost.GETfill_color = lambda g: Colors.PAWN[g.turn]
		pawn_ghost.GETborder_color = lambda g: Colors.WRONG if g.blockers else Colors.SELECTED
		pawn_ghost.GETloc = lambda g: g.pawn_target(g.selected.loc, g.mousePos())

		move_guide = FilledPolygon(self, Layers.GUIDE, None, None)
		move_guide.GETvisible = lambda g: g.state == 'pawn'
		move_guide.GETcolor = lambda g: Colors.PAWN[g.turn]
		move_guide.GETpoints = lambda g: self.move_rect(g.selected.loc, g.mousePos())

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

	wall_end = lambda self, p1, p2: p1 + (p2 - p1) @ Constants.WALL_LEN
	pawn_target = lambda self, p1, p2: nearest_on_disk(p2, p1, Constants.MOVE_DIST)
	def move_rect(self, p1, p2):
		p2 = self.pawn_target(p1, p2)
		delta = ~(p2-p1) @ Constants.PAWN_RAD
		return [p1+delta, p1-delta, p2-delta, p2+delta]

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
			target = self.pawn_target(self.current_pawn.loc, Point(*move['location']))
			if self.find_blockers('pawn', self.current_pawn, Point(*move['location'])): return
			self.record_state()
			self.current_pawn.loc = target
		elif move['type'] == 'wall':
			p1 = Point(*move['p1'])
			p2 = Point(*move['p2'])
			if self.find_blockers('wall', p1, p2): return
			if p1 == p2: return
			self.record_state()
			Wall(self, p1, self.wall_end(p1, p2))
		return True

	def prep_turn(self):
		self.state = 'start'
		self.selected = None
		self.blockers = []
		self.current_pawn = next(p for p in self.layers[Layers.PAWNS] if p.team == self.turn)

	def find_blockers(self, state, selected, mouse):
		if self.state == 'start':
			return [p for p in self.layers[Layers.PAWNS] if p.loc >> mouse < Constants.PAWN_RAD**2] + \
				[self.border] * (Point(0,0) >> mouse > Constants.BOARD_RAD**2)
		if self.state == 'pawn':
			target = self.pawn_target(selected.loc, mouse)
			rect = self.move_rect(selected.loc, mouse)
			return [p for p in self.layers[Layers.PAWNS] if p != selected and (p.loc >> target < (2*Constants.PAWN_RAD)**2 or intersect_circle_conv_polygon(p.loc, Constants.PAWN_RAD, rect))] + \
				[w for w in self.layers[Layers.WALLS] if intersect_segment_disk(w.p1, w.p2, target, Constants.PAWN_RAD) or intersect_segment_conv_polygon(w.p1, w.p2, rect)] + \
				[self.border] * (Point(0,0) >> target > (Constants.BOARD_RAD - Constants.PAWN_RAD)**2)
		if self.state == 'wall':
			p2 = self.wall_end(selected, mouse)
			return [p for p in self.layers[Layers.PAWNS] if intersect_segment_disk(selected, p2, p.loc, Constants.PAWN_RAD)] + \
				[w for w in self.layers[Layers.WALLS] if intersect_segments(selected, p2, w.p1, w.p2)] + \
				[self.border] * (Point(0,0) >> selected > Constants.BOARD_RAD**2 or Point(0,0) >> p2 > Constants.BOARD_RAD**2)

	def process(self):
		self.blockers = self.find_blockers(self.state, self.selected, self.mousePos())

if __name__=='__main__':
    pygame.init()
    run_local(Quoridor, sys.argv[1:])