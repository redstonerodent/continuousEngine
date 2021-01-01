This is a project to implement continuous versions of discrete games in python.


## Contents

### Core

* ` continuousEngine.py` handles graphics and user input for continuous games. The `Game` class implements view navigation (panning, zooming), undo/redo, and provides a more convenient interface for taking interactive input. The `Renderable` class should be used for game objects, and a handful of subclasses (roughly the ones which have been useful) are available.
* `geometry.py` has a lot of useful geometric functions. It defines, and the rest of the package uses, a `Point` class which uses Python's special function syntax to make formulas involving `Point`s easier to read.

### Games

* Chess: `chess.py`
* `sky.py` (Determining what it is is a fun puzzle so I won't spoil it here. The answer is a 4x4 Latin square; the contents of `sky.py` obviously have spoilers.)
* Reversi: `reversi.py`
* Go: `go.py`
* Penguin Jrap: `jrap.py` (inspired by [Penguin Trap](https://boardgamegeek.com/boardgame/225981/penguin-trap))

### Network

* `client.py` and `server.py` implement playing multiplayer games remotely.

### Battlecode

* Inspired by (and name borrowed from) [Battlecode](https://battlecode.org/), an annual programming competition at MIT.
* The `Player` class in `player.py` is the skeleton of an AI for continuous games.
* `run.py` runs AIs against each other.
* `watch.py` watches saved games output by `run.py`.
* `example<game>player.py` is an AI for `<game>` which plays randomly, as a template.

### Other

* `config.default` lists controls, and is copied to `config` the first time any game is run. You can edit `config` to change key bindings (but not mouse bindings).
* `chess_legacy.py` and `sky_legacy.py` are old versions made before `continuousEngine.py`. They may be missing features or bugfixes in the newer versions, and now serve mainly to demonstrate how the engine makes it easier.
* `bin` contains scripts (see 'Usage' below).
* `screenshots` contains screenshots.
* `Sprites` contains images used for some games, such as `chess` and `jrap`.
* `setup.py` is used for installation (see below).


## Installation

You will need Python 3.7 or later (for async) and pygame 2.0.0 or later. Everything has been tested in Python 3.8.5 and pygame 2.0.1. The instructions below may not work if your system is different enough from mine (Ubuntu 18.04).

### Python

You can get Python 3.8 from [Python's website](https://www.python.org/), or, if you're on Linux, probably with your package manager (on Ubuntu using apt, `sudo apt install python3.8`). I suggest making 3.8 the default Python version, which (at least on Ubuntu) you can do with `update-alternatives`; otherwise, replace `python` with `python3.8` in all the following commands.

### Pygame

Can be installed with pip: `pip install pygame`. If you don't have pip installed, try `python -m pip install pygame`. If you have an older version of `pygame`, use `pip install --upgrade pygame`.

### ContinuousEngine

* Clone this repo: `git clone https://github.com/redstonerodent/continuousEngine.git` or click the download button above.
* In the root directory, run `sudo python setup.py develop`

To update, run `git pull`. If the update adds a command, you need to run `setup.py` again. If the update adds new key bindings you want to change, you should copy the relevant portion of `config.default` to `config`. (If you don't want to change key bindings, continuousEngine will use the default.)


## Usage

### To run a game locally

`continuous game [-g game] [args ...]`

In all commands, `args` is passed to the game class. Currently the only use is to specify the number of players in `jrap`.

### To start a server

`continuous-server [ip]`

`ip` defaults to localhost. The server will save it state (and load state on startup) as `serverstate` in the directory the command is run.

### To connect to a server

`continuous-client [-h] -g game [-ip IP] [-id GAME_ID]
                        [-t TEAM] [-u USERNAME] [-n] [args]`

Arguments:

* `-h`, `--help`: show help message and exit.
* `-g`, `--game`: type of game to play.
* `-ip`: ip address of server, default `localhost`.
* `-id`: identifier of specific game to join or create. if blank, will join some existing game or make a new one with a random id.
* `-t`, `--team`: team to play as. if blank, will attempt to pick an available team. `spectator` can be used to watch games.
* `-u`, `--user`: username to use, defaults to `anonymous`.
* `-n`, `--new`: force creating a new game rather than joining an existing one

Any additional arguments are passed to the constructor for the game that gets created. For instance, `python client.py -g jrap -n -t silver 4` will create a new 4-player jrap game with a random id, and put you on team `silver`.

Currently `chess`, `go`, `jrap`, and `reversi` have network play.

### To play AIs against each other

`continuous-battlecode run -g game player_files [player_files ...] [-a args ...]`


Each entry in `player_files` should be a file in the current directory with a subclass of `PlayerTemplate` named `Player`. This class must implement `make_move`, which returns a move as a dictionary, and may implement `on_move`, which is called after each move. Each move also updates `Player.game`. I suggest starting from a copy of `battlecode/example<game>player.py`.

`player_files` are assigned teams in the order they're listed. This typically means the turn order is the order they're listed.

This will save the game in a `saves` subdirectory of the current directory, and will print the name of the saved file.

### To watch a saved game

`continuous-battlecode watch file`

This opens the game saved by `continuous-battlecode run`. To step through it, repeatedly press `redo` (default `x`).

Note that `file` should include `saves/`, if run from the same directory as `continuous-battlecode run`.


## Other things

* I'd like to hear about anything you make using this. Feel free to ask me about the code if you're confused what something does.
* I don't have much formal training or experience with large coding projects, and my coding style is inspired by functional programming. This all means my code is probably confusing and not up to your usual standards (see: modifying `__setattr__` and `__getattr__` of `Renderable`, using `lambda` more than `def`, extremely long lines/lambda expressions, list comprehensions with side effects instead of loops).
* Let me know if you notice any bugs, have ideas to improve existing games, or have ideas for new games I could make.
