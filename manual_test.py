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
t.add_drawable(Label('Quick fox\nJumped over\nThe lazy dog',
                     just='center', color='yellow'),
               pos=(11, 11))
t.clear()
t.add_drawable(Label('Stuff cleared'), pos=(10, 10))
t.close()
