#! /usr/bin/env python3.6

from bear_hug import BearTerminal, BearLoop
from bear_utilities import copy_shape
from event import BearEventDispatcher
from widgets import InputScrollable, ClosingListener, Layout,\
    Label, Widget, FPSCounter
from resources import XpLoader, Atlas

import os

class ElementBox(Layout):
    """
    A box for a given widget.
    
    Consists of widget itself, two lines of empty space around it and a '#'-box
    around *that*. The upper border of the box also includes a title.
    """
    def __init__(self, widget, name='Widget', color='#ff999999'):
        if widget.width + 4 >= len(name) + 1:
            box = self.generate_box(widget.width+2, widget.height+2,
                                                color)
        else:
            box = self.generate_box(len(name), widget.height+2, color)
        super().__init__(*box)
        self.add_child(widget, pos=(2, 2))
        self.add_child(Label(name, color='green'), pos=(1, 0))
        self._rebuild_self()
    
    @staticmethod
    def generate_box(width, height, color):
        """
        Return a #-bound box of a given (internal) size
        :param width:
        :param height:
        :return:
        """
        chars = []
        chars.append(['#' for x in range(width+2)])
        for y in range(height):
            chars.append(['#'] + [' ' for x in range(width)] + ['#'])
        chars.append(['#' for x in range(width+2)])
        colors = copy_shape(chars, color)
        return chars, colors

    
t = BearTerminal(size='46x52', title='Atlas',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])
t.start()


atlas = Atlas(XpLoader(os.path.dirname(__file__)+'/demo_assets/test_atlas.xp'),
              os.path.dirname(__file__)+'/demo_assets/test_atlas.json')
elements = []
positions = []
names = []
x = 1
y = 1
y_step = 0
for element in sorted(atlas.elements.keys()):
    w = ElementBox(Widget(*atlas.get_element(element)), name=element)
    elements.append(w)
    if x + w.width > 45:
        y += y_step
        x = 1
        y_step = 0
    positions.append((x, y))
    x += w.width + 1
    if w.height + 1 >= y_step:
        y_step = w.height + 1
view_height = y+y_step if y+y_step > 50 else 50
chars = [[' ' for _ in range(45)] for _ in range(view_height)]
colors = copy_shape(chars, 'white')
element_view = InputScrollable(chars, colors, view_pos=(0, 0),
                               view_size=(45, 50), right_bar=True)
for index, widget in enumerate(elements):
    element_view.add_child(widget, positions[index])
dispatcher.register_listener(element_view, ['tick', 'key_down', 'service'])
dispatcher.register_listener(element_view.scrollable,
                             ['tick', 'service'])
t.add_widget(element_view, pos=(0, 0))
t.add_widget(FPSCounter(), pos=(0, 51))
loop.run()
