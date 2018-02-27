## Bear hug

### What is it?
A bearlibterminal wrapper for building ASCII games (and other apps, if
you want to reinvent Norton Commander for some reason) in python3.
Although based on the roguelike libraries like bearlibterminal, it is
centered mostly on multi-character widgets, not lonely `@`s and `d`s of
the roguelike tradition.

### What it is not?
Curses analogue. `Bearlibterminal`, which is `bear_hug`'s backend, does
not rely on the user console, instead building its own SDL window. It
means the end result looks the same whether the player of
`bearlibterminal`/`bear_hug` game runs it on any Linux flavor, MacOS or
Windows. In addition, you get some cool tricks from `bearlibterminal`
like overlapping characters (some other cool tricks, like shifting
character within its cell, are not supported by `bear_hug` and won't be
unless pull-requested).

But it also means that any system that cannot run SDL cannot run
`bearlibterminal` games.

### What's there now?
A loop and event system, ECS support, a bunch of Widget prototypes,
object-oriented Widget API, parsers for txt and `.xp` (REXPaint) formats.

### What's planned?
A scene manager, better animation, more widgets, more file formats,
better settings API, useful components for your gamedev needs, proper
font support.

### Where's the documentation?
Not ready yet. Meanwhile, docstrings are pretty thorough.

### What are the dependencies?
Bearlibterminal and Python3.6

### What's the license?
MIT, copyright 2018, A. A. Morozov.
