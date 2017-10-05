#! /usr/bin/env python3

# Manual test for bearhug. Shows some basic stuff using bear_hug library

import random
from bear_hug import BearTerminal, Drawable, Label

t = BearTerminal(size='30x30', title='Test window')
t.start()
texts = [x for x in range(10)]
colors = ['red', 'green', 'blue']
for x in texts:
    t.add_drawable(Label(str(x), color=random.choice(colors)), pos=(x, x))
l = Label('Quick fox\nJumped over\nThe lazy dog', just='center', color='yellow')
t.add_drawable(l, pos=(11, 11), layer=5)
l2 = Label('Lorem ipsum\ndolor sit amet')
t.add_drawable(l2, pos=(11, 11), layer=10)
assert t.get_drawable_by_pos((12, 11)) == l2
assert t.get_drawable_by_pos((12, 11), layer=5) == l
assert t.get_drawable_by_pos((14, 10)) is None
t.clear()
t.add_drawable(Label('Stuff cleared'), pos=(10, 10))
t.close()
