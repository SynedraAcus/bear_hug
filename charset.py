#! /usr/bin/env python3.6

from bear_hug import BearTerminal, BearLoop
from widgets import Widget
from resources import XpLoader
from event import BearEventDispatcher

terminal = BearTerminal(size='18x18', title='Charset issue',
                        filter=['keyboard', 'mouse'])
terminal.start()
loop = BearLoop(terminal, BearEventDispatcher())
loader = XpLoader(filename='charlist.xp')
w = Widget(*loader.get_image())
for line in w.chars:
    for char in line:
        print(char, end=',')
    print('')
terminal.add_widget(w, refresh=True)
loop.run()
