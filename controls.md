# Controls

*These controls are designed with a Dvorak keyboard in mind. If you use QWERTY (or another layout), they won't make much sense but should still work. Controls are listed as the key to press, and the key which is in the same location on QWERTY&mdash;for instance, "`;`(z)" means you should press the semicolon key, which in Dvorak is in the same location as the z key in QWERTY (i.e. the leftmost key in the bottom row). Controls can be changed by changing the value of `game.keys.<name>`; see `https://www.pygame.org/docs/ref/key.html`.*

## Common to all games

These are defined in `continuousEngine.py`, and thus available in all games (though the meaning of undo/redo/restart is different in different games).

### View navigation

* Zoom: numpad `+`/`-` or scroll up/down
* Pan: `,`(w)/`a`(a)/`o`(s)/`e`(d) or right click and drag
* Reset view: `home`

### Game history

* Undo: `;`(z)
* Redo: `q`(x)
* Restart: `p`(r)

### Debug

* Print current state: backquote


## Chess

* Select piece: left click
* Move selected piece: left click
* Cancel selected piece: `esc`
* Toggle showing piece's range: middle click

## Sky

* Select square: left click
* Move selected square: arrow keys
* Enter number: `1`-`9` (top row or numpad)
* Delete number: backspace or `0`

- Run trial: left click (outside grid)
- Run many trials: middle click and drag
- Change trial colors: `j`(c)
- Clear trials: `esc`

* Toggle grid: `i`(g)

## Reversi & Go

* Place piece: left click
* Skip turn: `u`(f)

## Go (but not Reversi)

* Place ghost piece: space
* Clear ghost pieces: `esc`

## Jrap

* Make hole: left click
* Skip turn: `u`(f)