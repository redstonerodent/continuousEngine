This is a project to implement continuous versions of discrete games in python.

So far it has:

* Chess: `chess.py`
* `sky.py` (Determining what it is is a fun puzzle so I won't spoil it here. The answer is a 4x4 Latin square; the contents of `sky.py` obviously have spoilers.)
* Reversi: `reversi.py`
* Go: `go.py`

`continuousEngine.py` is a module I wrote to help with this. The `Game` class implements view navigation (panning, zooming), undo/redo, and provides a more convenient interface for taking interactive input. The `Renderable` class should be used for game objects, and a handful of subclasses (roughly the ones which were useful for things I've already made) are available.

`chess_legacy.py` and `sky_legacy.py` are old versions made before `continuousEngine.py`. They may be missing features or bugfixes in the newer versions, and now serve mainly to demonstrate how the engine makes it easier.

### If you want to run or use this code

* Have fun. I'd like to hear about anything you make using this. Feel free to ask me about the code if you're confused what something does.
* You'll need [pygame](https://www.pygame.org/news) (which can be installed with pip).
* [`controls.md`](controls.md) lists the controls for all of the games.
* The key bindings are intended for Dvorak. If you uses QWERTY you probably want to change them (look at `game.keys` in `continuousEngine.py` and it's probably clear how).
* I use python 3. I don't know whether this all works in python 2. (Specifically, everything has been tested in python 3.6.9.)
* I don't have much formal training or experience with large coding projects, and my coding style involves a lot of functional programming. This all means my code is probably confusing and not up to your usual standards (see: modifying `__setattr__` and `__getattr__` of `Renderable`, using `lambda` more than `def`, extremely long lines/lambda expressions, list comprehensions with side effects instead of loops).
* Let me know if you notice any bugs, have ideas to improve existing games, or have ideas for new games I could make.