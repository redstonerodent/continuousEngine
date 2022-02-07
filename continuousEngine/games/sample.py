# this file contains annotated code for a very simple game,
# to guide you through creating continuous games

# of course we want to import this
from continuousEngine import *
# and I'll use pi a little bit later
from math import pi

# let's start by defining some constants that we'll use later
# I generally put these in separate classes, but it doesn't really matter
# in practice, you'll probably add to these as you need them

# these numbers tell continuous engine what order to render things in
# bigger numbers are rendered later (and thus in front)
# these don't have to be integers; anything that can be sorted will work
# except that layers defined elsewhere use numbers, so I don't recommend using strings
class Layers:
	PIECE = 1
	MOUSE = 2

# colors can be in any format pygame accepts
class Colors:
    PIECE = {'red':(255,0,00), 'blue':(0,0,255), 'green':(0,255,0), 'yellow':(255,255,0)}
    MOUSE = (255,0,255)
    OUTLINE = (0,0,0)

# this is for values the game uses to make them easy to tweak
class Constants:
	TEAMS = ['red', 'blue', 'green', 'yellow']
	# distances in game units
	PIECE_LENGTH = .5
	PIECE_WIDTH  = .3
	MOVE_DIST = 1
	START_RAD = 3

	# distances in pixels
	MOUSE_RAD = 15

# next, let's define some game objects as Renderables
# a Renderable is anything you want to show on the screen

# our game will have some moving triangles, which can inherit from FilledPolygon

class SamplePiece(FilledPolygon):
	def __init__(self, game, team, center, target):
		super().__init__(game, Layers.PIECE, Colors.PIECE[team], None)
		self.team, self.center, self.target = team, center, target

		# we want these triangles to move, so let's generate the coordinates
		# of their vertices dynamically
		# we want self.points to be the result of calling a function
		# continuousEngine lets you do this by defining self.GETpoints
		# to be a function which takes as argument a game
		# evaluating self.points will call this function on self.game
		# in this case, this will happen each time the piece is rendered

		# a FilledPolygon's points should be a list of Point objects
		# Points are defined in geometry.py, and are easy to do various operations to
		# let's make an isoceles triangle with base at self.center pointing towards self.target
		self.GETpoints = lambda g: [
			self.center+(self.target-self.center)@Constants.PIECE_LENGTH, # PIECE_LENGTH from center towards target
			self.center+~(self.target-self.center)@Constants.PIECE_WIDTH/2, # 1/2 PIECE_WIDTH perpendicular
			self.center-~(self.target-self.center)@Constants.PIECE_WIDTH/2 # and in the other direction
			]

# now we can define the actual game!
class Sample(Game):
	# we'll take a number of players, and pass everything else to the parent constructor
	def __init__(self, teams=2, **kwargs):
		self.team_count = int(teams) # since this is often a string from command line arguments

		# name sets the window title
		# see continuousEngine.py for more optional arguments
		super().__init__(name='yay triangles', **kwargs)
		# strictly speaking, we have a working game, it just doesn't do much
		# to test it, you need the code at the very end of this file
		# but it doesn't do much yet

		# let's add some objects to our game
		# just declaring a Renderable adds it to the game at the layer you pass to it

		# the mouse will be a disk; see continuousEngine.py for what all these arguments do
		# to make it follow the mouse, we'll have it compute its loc dynamically (and just pass None to the constructor)
		# g.mousePos() gives the current location of the mouse
		BorderDisk(self, Layers.MOUSE, Colors.MOUSE, Colors.OUTLINE, None, Constants.MOUSE_RAD, realRadius=False).GETloc = lambda g: g.mousePos()

		# now if we run the game, there's a magenta circle that follows the mouse around
		# that code was elegant but terse; let's see another way. first clear the relevant layer:
		self.clearLayer(Layers.MOUSE)

		# now let's bind the object to mouse_disk
		self.mouse_disk = BorderDisk(self, Layers.MOUSE, Colors.MOUSE, Colors.OUTLINE, None, Constants.MOUSE_RAD, realRadius=False)		
		# and then we can set its dynamic loc
		self.mouse_disk.GETloc = lambda g: g.mousePos()
		# this accomplishes the same thing, but now we can easily reference that renderable if we want
		# for instance: if you start the game with the mouse not on the window, it crashes
		# because it tries to render mouse_disk at location None
		# to fix this, let's make make_disk invisible if there's no mouse position
		self.mouse_disk.GETvisible = lambda g: g.mousePos() != None

		# now let's make those moving triangles I promised
		# first we want to specify how the game encodes its state
		# so I'll define load_state and save_state below
		# go read those, and then return here

		# -----

		# load_state, save_state, and make_initial_state are used by the engine, so you definitely want them
		# for anything to happen, we need to say this:
		self.reset_state()
		# now if we run the game, there are triangles arranged how we wanted

		# but the triangles still don't do anything
		# let's try to make it so that when you click, the triangle for the current turn
		# moves towards the mouse, and they take turns
		# to define a left click action, we need to set self.click[1]
		# (1 means left click, which can tell by the "unknown click: 1" messages that gets printed when you try)

		self.click[1] = lambda e: self.attemptMove({'player':self.turn, 'location':self.point(*e.pos).coords})
		# now's as good a time as any to explain the coordinate systems
		# there are two of them: pixels, which refer to your physical screen
		# and points, which are abstract locations in the game world
		# pixels are usually tuples; points are usually Points
		# we convert between them with self.point and self.pixel
		# the current window is encoded by scale, x_offset, and y_offset
		# both systems have x left to right and y top to bottom
		# here, we just converted the pixel of the click (e.pos) to a point with self.point

		# so clicking just attempts to make a move
		# attemptMove is a function the engine defines, which handles things like
		# incrementing the turn and updating time controls
		# the argument to attemptMove should encode the move and be jsonifiable
		# since it's how the move is sent to the server in network play
		# attemptMove also calls attemptGameMove, which we need to define to implement the game logic
		# so let's go do that

		# -----

		# to make it clearer whose turn it is, let's change the color of the circle at the mouse
		# we could do that in prep_turn, but let's do it my making the color dynamic:
		self.mouse_disk.GETfill_color = lambda g: Colors.PIECE[g.turn]

		# we have a basically working game!
		# to summarize, here are the things you should define:
		#	layers
		#	colors
		#	Renderables for game objects
		#	__init__ which creates some objects, defines actions, and calls reset_state()
		# 	load_state
		# 	save_state
		# 	make_initial_state
		# 	attemptGameMove
		#	optionally: prep_turn, process, resize, or viewChange (apparently my function naming isn't terribly consistent)

		# to make the game available from the continuous-game command
		# add an entry to continuousEngine.ALL_GAMES
		# pointing to the name of the class

		# to make the game available for network play
		# add it to network_games in bin/continuous-client
		# everything should just work
		# if you want there to be information hidden from some players
		# you should define get_state() which gives a state based on the team
		# (trans does this)

		# let's make our game work for battlecode
		# to do this, we need to define two funnctions: is_over and winner
		# our game is really just a sandbox so far
		# let's say the goal is to crash into another player
		# by having the tip of your triangle inside them
		# whoever does this first wins
		# let's go define is_over and winner to implement this

		# -----

		# last thing: we saw how to make clicks do something with self.click[n]
		# you can similarly make click-and-drag do something with self.drag[n]
		# n is a number encoding the mouse button (the number is different in click vs drag)
		# to make a keypress do something, you set self.keyPress[n]
		# so keys are customizable, you should
		#	add an entry to config.default (this will set self.keys.something)
		#	set self.keyPress[self.keys.something] to the relevant function



	def load_state(self, state):
		# first we should clear the current game state
		self.clearLayer(Layers.PIECE)
		
		# the state passed to load_state should be jsonifiable
		# let's have it be a tuple of
		#	the current turn,
		#	the lits of teams
		#	a list of tuples representing triangles
		self.turn, teams, pieces = state
		self.teams = teams.copy() # we don't want to accidentally modify a saved state
		# each tuple in pieces has the form (team, center, target)
		# where center and target are each a pair of numbers (floats), describing the position
		# to load this, we need to create a SamplePiece for each one
		for team, center, target in pieces:
			SamplePiece(self, team, Point(*center), Point(*target))
			# here Point(*center) just converts the tuple to a Point


	def save_state(self):
		# now we just need to do the reverse
		# self.layers[Layers.PIECE] contains all the pieces
		return (self.turn, self.teams.copy(), [(p.team, p.center.coords, p.target.coords) for p in self.layers[Layers.PIECE]])
		# yes, that could have been a lambda
	# before you go back to __init__, one more thing
	# we should define the initial state
	# let's have the triangles spread out in a circle, facing in
	# one triangle per team
	# we can pass 4 arguments to Point to use polar coordinates
	# this function returns the thing that gets passed to load_state
	make_initial_state = lambda self: ('red', Constants.TEAMS[:self.team_count], [(t, (0,0,Constants.START_RAD, i*2*pi/self.team_count), (0,0)) for i,t in enumerate(Constants.TEAMS[:self.team_count])])
	# okay, back to __init__

	def attemptGameMove(self, move):
		# this makes undo/redo work
		self.record_state()

		# the argument is a mouse click event, which has the position at e.pos
		delta = (Point(*move['location']) - self.current_piece.center)@Constants.MOVE_DIST

		# delta is the length-MOVE_DIST vector facing towards the click
		# let's move the piece by that much, and have it face that direction
		self.current_piece.center += delta
		self.current_piece.target = self.current_piece.center + delta
		# to indicate the move succeeded, we return True
		return True
		# this assumes we have something called self.current_piece
		# this should be updated each turn
		# so let's define prep_turn to do that
	def prep_turn(self):
		# this function is called (by attemptMove) before each turn
		# here we just want to set self.current_piece to the piece of the right team
		for p in self.layers[Layers.PIECE]:
			if p.team == self.turn:
				self.current_piece = p
	# now the triangles move around when we click!
	# you can also undo/redo (default z and x)
	# let's make it feel nicer by having the active triangle face the mouse
	# that means its target should be updated every time the game is rendered
	# we make that happen by defining process, which is called before each render
	def process(self):
		if self.mousePos():
			self.current_piece.target = self.mousePos()
		# the conditional is so it doesn't crash if you start with the mouse off the window
	# similar to prep_turn and process, you can define resize or viewChange
	# which are called when you'd expect from their names
	# now back to __init__

	def is_over(self):
		# the game is over if anyone's tip is inside anyone else
		return any(point_in_polygon(p1.center + (p1.target - p1.center)@Constants.PIECE_LENGTH, p2.points) for p1 in self.layers[Layers.PIECE] for p2 in self.layers[Layers.PIECE] if p1 != p2)
	def winner(self):
		# the winner is the team with the tip inside another
		# the game ends once this happens, so we don't need to worry about there being multiple
		return next(p1.team for p1 in self.layers[Layers.PIECE] for p2 in self.layers[Layers.PIECE] if p1 != p2 and point_in_polygon(p1.center + (p1.target - p1.center)@Constants.PIECE_LENGTH, p2.points))
		# observe that geometry.py has lots of useful functions like point_in_polygon
	# that's all it takes, in theory!
	# this is only checked after each turn, so you don't need to worry
	# about a piece being rotation to overlap another
	# to make your game accessible from continuous-battlecode
	# add it to battlecode_games in bin/continuous-battlecode
	# I haven't actually run battlecode bots against each other
	# so it's possible there's some issue here I haven't noticed
	# back to __init__ for one more thing


# to test the game, we need this:
if __name__=="__main__":
    pygame.init()
    run_local(Sample, sys.argv[1:])

# then we can run, e.g.
# python sample.py 3
# to get a game with 3 players
