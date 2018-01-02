#! /usr/bin/env python3.6

# Manual test for bearhug. Shows some basic stuff using bear_hug library

import random
from collections import deque

from bear_hug import BearTerminal, Drawable, Label, BearLoop
from bear_utilities import copy_shape
from event import BearEventDispatcher


class FPSCounter(Drawable):
    def __init__(self, *args, **kwargs):
        # Initial values for averaging stream
        self.samples_deque = deque(maxlen=100)
        chars = [list(str(30))]
        color = copy_shape(chars, 'white')
        super().__init__(chars, color, *args, **kwargs)
    
    def _update_self(self):
        self.chars = list(str(round(len(self.samples_deque)/sum(self.samples_deque))))
        self.colors = copy_shape(self.chars, 'white')
        
    def on_event(self, event):
        # Update FPS estimate
        if event.event_type == 'tick':
            self.samples_deque.append(event.event_value)
            self._update_self()
            self.terminal.update_drawable(self)
        elif event.event_type == 'input':
            print(event.event_value)

        
class Firework(Drawable):
    """
    Draws a size*size square with two asterisks in it
    Moves asterisks and changes colours every freq seconds
    """
    def __init__(self, size=3, freq=10, **kwargs):
        self.asterisks=[(random.randint(0, size-1), random.randint(0, size-1))\
                        for x in range(size)]
        chars = [[' ' for x in range(size)] for x in range(size)]
        colors = copy_shape(chars, 'white')
        for asterisk in self.asterisks:
            chars[asterisk[0]][asterisk[1]] = '*'
            colors[asterisk[0]][asterisk[1]] = random.choice(('red', 'blue', 'white'))
        super().__init__(chars, colors, **kwargs)
        self.ticks_to_wait = freq
        self.ticks_skipped = 0
        self.size = size
    
    def on_event(self, event):
        if event.event_type == 'tick':
            self.ticks_skipped += 1
            if self.ticks_skipped >= self.ticks_to_wait:
                index = random.randint(0, len(self.asterisks)-1)
                self.chars[self.asterisks[index][0]][self.asterisks[index][1]] = ' '
                self.asterisks[index] = (random.randint(0, self.size-1),
                                         random.randint(0, self.size-1))
                self.chars[self.asterisks[index][0]][self.asterisks[index][1]] = '*'
                self.colors[self.asterisks[index][0]][self.asterisks[index][1]] = \
                        random.choice(('red', 'blue', 'white'))
                self.terminal.update_drawable(self)
                self.ticks_skipped = 0
            

t = BearTerminal(size='30x30', title='Test window', filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
counter = FPSCounter()
dispatcher.register_listener(counter, ['tick', 'input'])
fireworks = [Firework(freq=1) for x in range(4)]
t.start()
t.add_drawable(counter, pos=(1, 1), layer=0)
layer = 1
for f in fireworks:
    dispatcher.register_listener(f, ['tick'])
    t.add_drawable(f, pos=(random.randint(0, 26), random.randint(0, 26)),
                   layer=layer)
    layer += 1 # To avoid collisions
loop.run()

# exts = [x for x in range(10)]
# colors = ['red', 'green', 'blue']
# for x in texts:
#     t.add_drawable(Label(str(x), color=random.choice(colors)), pos=(x, x))
# l = Label('Quick fox\nJumped over\nThe lazy dog', just='center', color='yellow')
# t.add_drawable(l, pos=(11, 11), layer=5)
# l2 = Label('Lorem ipsum\ndolor sit amet')
# t.add_drawable(l2, pos=(11, 11), layer=10)
# assert t.get_drawable_by_pos((12, 11)) == l2
# assert t.get_drawable_by_pos((12, 11), layer=5) == l
# assert t.get_drawable_by_pos((14, 10)) is None
# t.clear()
# t.add_drawable(Label('Stuff cleared'), pos=(10, 10))
# t.close()
