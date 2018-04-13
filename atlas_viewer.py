#! /usr/bin/python3.6

from bear_hug import BearTerminal, BearLoop
from bear_utilities import copy_shape
from event import BearEventDispatcher
from widgets import ScrollableLayout, ClosingListener, Listener, Layout,\
    Label, Widget
from resources import Atlas

class ElementBox(Layout):
    """
    A box for a given widget.
    
    Consists of widget itself, two lines of empty space around it and a '#'-box
    around *that*. The upper border of the box also includes a title.
    """
    def __init__(self, widget, name='Widget', color='white'):
        super.__init__(*self.generate_box(widget.width, widget.height, color))
        self.add_child(widget, pos=(1, 1))
        self.add_child(Label(name), pos=(1,0))
    
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
        
    
t = BearTerminal(size='50x45', title='Atlas',
                 filter=['keyboard', 'mouse'])
dispatcher = BearEventDispatcher()
loop = BearLoop(t, dispatcher)
dispatcher.register_listener(ClosingListener(), ['misc_input', 'tick'])

w = Widget([['1', '2'], ['3', '4']], [['red', 'red'], ['red', 'red']])
t.add_widget(ElementBox(widget=w, name='N'), pos=(1, 1), refresh=True)
