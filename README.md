This is a project to implement continuous versions of discrete games in python.


## Contents

### Infrastructure

* ` continuousEngine.py` handles graphics and user input for continuous games. The `Game` class implements view navigation (panning, zooming), undo/redo, and provides a more convenient interface for taking interactive input. The `Renderable` class should be used for game objects, and a handful of subclasses (roughly the ones which have been useful) are available.
* `geometry.py` has a lot of useful geometric functions. It defines, and the rest of the repo uses, a `Point` class which uses Python's special function syntax to make formulas involving `Point`s easier to read.
* `client.py` and `server.py` can be used to play multiplayer games remotely.


### Games

* Chess: `chess.py`
* `sky.py` (Determining what it is is a fun puzzle so I won't spoil it here. The answer is a 4x4 Latin square; the contents of `sky.py` obviously have spoilers.)
* Reversi: `reversi.py`
* Go: `go.py`
* Penguin Jrap: `jrap.py` (inspired by [Penguin Trap](https://boardgamegeek.com/boardgame/225981/penguin-trap))

### Other

* [`controls.md`](controls.md) lists controls for all games.
* `chess_legacy.py` and `sky_legacy.py` are old versions made before `continuousEngine.py`. They may be missing features or bugfixes in the newer versions, and now serve mainly to demonstrate how the engine makes it easier.


## Installation

You will need Python 3.7 or later (for async) and pygame. Everything has been tested in Python 3.8.5 and pygame 2.0.0dev10.

### Python

You can get Python 3.8 from [Python's website](https://www.python.org/), or, if you're on Linux, probably with your package manager (on Ubuntu using apt, `sudo apt install python3.8`). I suggest making 3.8 the default Python version, which (at least on Ubuntu) you can do with `update-alternatives`.

### Pygame

Can be installed with pip: `pip install pygame==2.0.0dev10`.

### ContinuousEngine

Clone this repo: `git clone https://github.com/redstonerodent/continuousEngine.git` or click the download button above.


## Usage

Open a terminal in the cloned directory.

### To run a game locally

Just run the file with python, e.g. `python sky.py`.

### To start a server

Run `python server.py [<ip>]`. The ip defaults to localhost, and in most cases you can leave it blank.

### To connect to a server

Run `python client.py <game> [<game_id> [<team> [<username> [<ip>]]]]` [this may change]. All arguments after `game` are optional, but must be given in order (e.g. if you specify a `username` you have to specify a `game_id` and `team`).

* `game`: the type of game to play, one of `chess`, `reversi`, `go`, and `jrap`. (`sky` is single-player, and doesn't work for network play.)
* `game_id`: an identifier for the specific game/room. If the game doesn't exist, a new game is created. If not specified, the client will join some game with an empty slot, or do nothing if there is none.
* `team`: the team you want to play as, e.g. `white` or `black` for Chess. If not specified, the first available team will be selected.
* `username`: an identifying string, defaulting to `anonymous`.
* `ip`: ip address of the server to connect to, defaulting to localhost.


## Other things

* I'd like to hear about anything you make using this. Feel free to ask me about the code if you're confused what something does.
* The key bindings are intended for Dvorak. If you use QWERTY you probably want to change them (look at `game.keys` in `continuousEngine.py` and it's probably clear how) (I'm intending to make this better sometime soon).
* I don't have much formal training or experience with large coding projects, and my coding style is inspired by functional programming. This all means my code is probably confusing and not up to your usual standards (see: modifying `__setattr__` and `__getattr__` of `Renderable`, using `lambda` more than `def`, extremely long lines/lambda expressions, list comprehensions with side effects instead of loops).
* Let me know if you notice any bugs, have ideas to improve existing games, or have ideas for new games I could make.
