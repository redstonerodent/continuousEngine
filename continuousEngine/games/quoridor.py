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
	def __init__(self, game, team, loc, layer = Layers.PAWNS):
		super().__init__(game, layer, team and Colors.PAWN[team], None, loc, Constants.PAWN_RAD, borderGrowth=0)
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

		wall_ghost = Wall(self, None, None, Layers.GHOSTS)
		wall_ghost.GETvisible = lambda g: g.state == 'wall'
		wall_ghost.GETcolor = lambda g: Colors.WRONG if g.blockers else Colors.SELECTED
		wall_ghost.GETp1 = lambda g: g.selected
		wall_ghost.GETp2 = lambda g: g.wall_end(g.selected, g.mousePos())

		pawn_ghost = Pawn(self, None, None, Layers.GHOSTS)
		pawn_ghost.GETvisible = lambda g: g.state == 'pawn'
		pawn_ghost.GETfill_color = lambda g: Colors.PAWN[g.turn]
		pawn_ghost.border_color = Colors.SELECTED
		pawn_ghost.GETloc = lambda g: g.curr_target

		move_guide = FilledPolygon(self, Layers.GUIDE, None, None)
		move_guide.GETvisible = lambda g: g.state == 'pawn'
		move_guide.GETcolor = lambda g: Colors.PAWN[g.turn]
		move_guide.GETpoints = lambda g: g.move_rect(g.selected, g.curr_target)

		if 1:
			a = Segment(self, 100, (255,0,0), None, None)
			a.GETvisible = lambda g: g.state == 'pawn'
			a.GETp1 = lambda g: g.selected.loc
			a.GETp2 = lambda g: g.mousePos()

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

	def pawn_target(self, pawn, end):
		# player attempts to move the pawn to end
		# where does it actually go?
		end = nearest_on_disk(end, pawn.loc, Constants.MOVE_DIST) # first cap at MOVE_DIST
		last = []
		while (b := next(iter(self.find_pawn_blockers(pawn, end)), None)): # if blocked, back up to be tangent to the blocker
			print('dodging', b)
			if b == self.border:
				print('border')
				end = slide_to_circle(end, pawn.loc, Point(0,0), Constants.BOARD_RAD - Constants.PAWN_RAD)
			elif isinstance(b, Wall):
				print('wall')
				# slide end to the oval around the wall
				delta = (~(b.p1-b.p2) @ Constants.PAWN_RAD)*(-1)**above_line(pawn.loc, b.p1, b.p2)
				if intersect_segments(pawn.loc, end, b.p1+delta, b.p2+delta):
					end = intersect_lines(pawn.loc, end, b.p1 + delta, b.p2 + delta)
				else:
					end = min(sum((intersect_segment_circle(pawn.loc, end, p, Constants.PAWN_RAD) for p in [b.p1, b.p2]),()), key=lambda p: pawn.loc >> p)
			elif isinstance(b, Pawn):
				print('pawn')
				end = slide_to_circle(end, pawn.loc, b.loc, 2*Constants.PAWN_RAD)
			print('dodged')
			last = [b]
			end -= (end - pawn.loc) @ epsilon # avoid floating point issues
		return end, last


	def move_rect(self, pawn, end):
		delta = ~(end-pawn.loc) @ Constants.PAWN_RAD
		return [end-delta, end+delta, pawn.loc+delta, pawn.loc-delta]

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
			target, _ = self.pawn_target(self.current_pawn, Point(*move['location']))
			if self.find_pawn_blockers(self.current_pawn, target): return
			self.record_state()
			self.current_pawn.loc = target
		elif move['type'] == 'wall':
			p1 = Point(*move['p1'])
			p2 = self.wall_end(p1, Point(*move['p2']))
			if self.find_wall_blockers(p1, p2): return
			if p1 == p2: return
			self.record_state()
			Wall(self, p1, self.wall_end(p1, p2))
		return True

	def prep_turn(self):
		self.state = 'start'
		self.selected = None
		self.blockers = []
		self.current_pawn = next(p for p in self.layers[Layers.PAWNS] if p.team == self.turn)

	def find_pawn_blockers(self, pawn, end):
		rect = self.move_rect(pawn, end)
		return [p for p in self.layers[Layers.PAWNS] if p != pawn and (p.loc >> end < (2*Constants.PAWN_RAD)**2 or intersect_circle_conv_polygon(p.loc, Constants.PAWN_RAD, rect))] + \
			[w for w in self.layers[Layers.WALLS] if intersect_segment_disk(w.p1, w.p2, end, Constants.PAWN_RAD) or intersect_segment_conv_polygon(w.p1, w.p2, rect)] + \
			[self.border] * (Point(0,0) >> end > (Constants.BOARD_RAD - Constants.PAWN_RAD)**2)

	def find_wall_blockers(self, start, end):
		return [p for p in self.layers[Layers.PAWNS] if intersect_segment_disk(start, end, p.loc, Constants.PAWN_RAD)] + \
			[w for w in self.layers[Layers.WALLS] if intersect_segments(start, end, w.p1, w.p2)] + \
			[self.border] * (Point(0,0) >> start > Constants.BOARD_RAD**2 or Point(0,0) >> end > Constants.BOARD_RAD**2)

	def pawns_under(self, pt):
		return [p for p in self.layers[Layers.PAWNS] if p.loc >> pt < Constants.PAWN_RAD**2]

	def process(self):
		if self.mousePos():
			if self.state == 'start':
				self.blockers = self.pawns_under(self.mousePos())
			elif self.state == 'pawn':
				self.curr_target, self.blockers = self.pawn_target(self.selected, self.mousePos())
			elif self.state == 'wall':
				self.blockers = self.find_wall_blockers(self.selected, self.wall_end(self.selected, self.mousePos()))

if __name__=='__main__':
    pygame.init()
    run_local(Quoridor, sys.argv[1:])