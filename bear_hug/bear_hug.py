"""
An object-oriented bearlibterminal wrapper with the support for complex ASCII
art and widget-like behaviour.
"""

from bearlibterminal import terminal
from bear_hug.bear_utilities import BearException,\
    BearLoopException
from bear_hug.event import BearEvent

import inspect
import os
import time
from copy import copy
from collections import namedtuple


WidgetLocation = namedtuple('WidgetLocation', ('pos', 'layer'))


class BearTerminal:
    """
    A main terminal class.

    This class corresponds to a single window and is responsible for drawing
    whatever widgets get added to this window, as well as processing any input.

    Accepts `bearlibterminal library configuration options
    <http://foo.wyrd.name/en:bearlibterminal:reference:configuration>`_ as
    kwargs to ``self.__init__``. Currently only library settings are supported
    and there is no support for changing them on the fly.
    """
    # TODO: wrap bearlibterminal parameters in @property
    # TODO: change bearlibterminal parameters on the fly
    # kwargs to init are passed to bearlibterminal.terminal.set()
    # Currently only library settings are supported
    _accepted_kwargs = {'encoding': 'terminal', 'size': 'window',
                       'cellsize': 'window', 'title': 'window', 'icon': 'window',
                       'resizeable': 'window', 'fullscreen': 'window',
                       
                       'filter': 'input', 'precise-mouse': 'input',
                       'mouse-cursor': 'input', 'cursor-symbol': 'input',
                       'cursor-blink-rate': 'input', 'alt-functions': 'input',
    
                       'postformatting': 'output', 'vsync': 'output',
                        'tab-width': 'output',

                        'file': 'log', 'level': 'log', 'mode': 'log'
                        }
    
    # Bearlibterminal's input codes and terminal state codes are converted to
    # constants before emitting events, so that downstream widgets could process
    # them without asking the terminal to explain what the fuck 0x50 is.
    
    # These are codes for keys and mouse buttons going down
    _down_codes = {0x04: 'TK_A', 0x05: 'TK_B', 0x06: 'TK_C', 0x07: 'TK_D',
                   0x08: 'TK_E', 0x09: 'TK_F', 0x0A: 'TK_G', 0x0B: 'TK_H', 0x0C: 'TK_I',
                   0x0D: 'TK_J', 0x0E: 'TK_K', 0x0F: 'TK_L', 0x10: 'TK_M', 0x11: 'TK_N',
                   0x12: 'TK_O', 0x13: 'TK_P', 0x14: 'TK_Q', 0x15: 'TK_R', 0x16: 'TK_S',
                   0x17: 'TK_T', 0x18: 'TK_U', 0x19: 'TK_V', 0x1A: 'TK_W', 0x1B: 'TK_X',
                   0x1C: 'TK_Y', 0x1D: 'TK_Z',
                   0x1E: 'TK_1', 0x1F: 'TK_2', 0x20: 'TK_3',
                   0x21: 'TK_4', 0x22: 'TK_5', 0x23: 'TK_6', 0x24: 'TK_7', 0x25: 'TK_8',
                   0x26: 'TK_9', 0x27: 'TK_0',
                   0x28: 'TK_ENTER', 0x29: 'TK_ESCAPE', 0x2A: 'TK_BACKSPACE',
                   0x2B: 'TK_TAB', 0x2C: 'TK_SPACE', 0x2D: 'TK_MINUS', 0x2E: 'TK_EQUALS',
                   0x2F: 'TK_LBRACKET', 0x30: 'TK_RBRACKET', 0x31: 'TK_BACKSLASH',
                   0x33: 'TK_SEMICOLON', 0x34: 'TK_APOSTROPHE', 0x35: 'TK_GRAVE',
                   0x36: 'TK_COMMA', 0x37: 'TK_PERIOD', 0x38: 'TK_SLASH',
                   0x3A: 'TK_F1', 0x3B: 'TK_F2', 0x3C: 'TK_F3', 0x3D: 'TK_F4',
                   0x3E: 'TK_F5', 0x3F: 'TK_F6', 0x40: 'TK_F7', 0x41: 'TK_F8', 0x42: 'TK_F9',
                   0x43: 'TK_F10', 0x44: 'TK_F11', 0x45: 'TK_F12',
                   0x48: 'TK_PAUSE', 0x49: 'TK_INSERT', 0x4A: 'TK_HOME',
                   0x4B: 'TK_PAGEUP', 0x4C: 'TK_DELETE', 0x4D: 'TK_END', 0x4E: 'TK_PAGEDOWN',
                   0x4F: 'TK_RIGHT', 0x50: 'TK_LEFT', 0x51: 'TK_DOWN', 0x52: 'TK_UP',
                   0x54: 'TK_KP_DIVIDE', 0x55: 'TK_KP_MULTIPLY',
                   0x56: 'TK_KP_MINUS', 0x57: 'TK_KP_PLUS', 0x58: 'TK_KP_ENTER',
                   0x59: 'TK_KP_1', 0x5A: 'TK_KP_2', 0x5B: 'TK_KP_3', 0x5C: 'TK_KP_4',
                   0x5D: 'TK_KP_5', 0x5E: 'TK_KP_6', 0x5F: 'TK_KP_7', 0x60: 'TK_KP_8',
                   0x61: 'TK_KP_9', 0x62: 'TK_KP_0', 0x63: 'TK_KP_PERIOD',
                   0x70: 'TK_SHIFT', 0x71: 'TK_CONTROL', 0x72: 'TK_ALT',
                   0x80: 'TK_MOUSE_LEFT', 0x81: 'TK_MOUSE_RIGHT',
                   0x82: 'TK_MOUSE_MIDDLE'}
    
    # The same buttons going up.
    # BLT OR's key code with TK_KEY_RELEASED, which is not reversible except by
    # bruteforcing all the keys. Thus, a second dict.
    _up_codes = {260: 'TK_A', 261: 'TK_B', 262: 'TK_C', 263: 'TK_D', 264: 'TK_E',
                 265: 'TK_F', 266: 'TK_G', 267: 'TK_H', 268: 'TK_I', 269: 'TK_J',
                 270: 'TK_K', 271: 'TK_L', 272: 'TK_M', 273: 'TK_N', 274: 'TK_O',
                 275: 'TK_P', 276: 'TK_Q', 277: 'TK_R', 278: 'TK_S', 279: 'TK_T',
                 280: 'TK_U', 281: 'TK_V', 282: 'TK_W', 283: 'TK_X', 284: 'TK_Y',
                 285: 'TK_Z', 286: 'TK_1', 287: 'TK_2', 288: 'TK_3', 289: 'TK_4',
                 290: 'TK_5', 291: 'TK_6', 292: 'TK_7', 293: 'TK_8', 294: 'TK_9',
                 295: 'TK_0', 296: 'TK_ENTER', 297: 'TK_ESCAPE',
                 298: 'TK_BACKSPACE', 299: 'TK_TAB', 300: 'TK_SPACE',
                 301: 'TK_MINUS', 302: 'TK_EQUALS', 303: 'TK_LBRACKET',
                 304: 'TK_RBRACKET', 305: 'TK_BACKSLASH', 307: 'TK_SEMICOLON',
                 308: 'TK_APOSTROPHE', 309: 'TK_GRAVE', 310: 'TK_COMMA',
                 311: 'TK_PERIOD', 312: 'TK_SLASH', 314: 'TK_F1', 315: 'TK_F2',
                 316: 'TK_F3', 317: 'TK_F4', 318: 'TK_F5', 319: 'TK_F6',
                 320: 'TK_F7', 321: 'TK_F8', 322: 'TK_F9', 323: 'TK_F10',
                 324: 'TK_F11', 325: 'TK_F12', 328: 'TK_PAUSE', 329: 'TK_INSERT',
                 30: 'TK_HOME', 331: 'TK_PAGEUP', 332: 'TK_DELETE',
                 333: 'TK_END', 334: 'TK_PAGEDOWN', 335: 'TK_RIGHT',
                 336: 'TK_LEFT', 337: 'TK_DOWN', 338: 'TK_UP',
                 340: 'TK_KP_DIVIDE', 341: 'TK_KP_MULTIPLY', 342: 'TK_KP_MINUS',
                 343: 'TK_KP_PLUS', 344: 'TK_KP_ENTER', 345: 'TK_KP_1',
                 346: 'TK_KP_2', 347: 'TK_KP_3', 348: 'TK_KP_4', 349: 'TK_KP_5',
                 350: 'TK_KP_6', 351: 'TK_KP_7', 352: 'TK_KP_8', 353: 'TK_KP_9',
                 354: 'TK_KP_0', 355: 'TK_KP_PERIOD', 368: 'TK_SHIFT',
                 369: 'TK_CONTROL', 370: 'TK_ALT', 384: 'TK_MOUSE_LEFT',
                 385: 'TK_MOUSE_RIGHT', 386: 'TK_MOUSE_MIDDLE'}
    
    # This is misc input and state codes
    misc_input = {0x83: 'TK_MOUSE_X1', 0x84: 'TK_MOUSE_X2',
    0x85: 'TK_MOUSE_MOVE', 0x86: 'TK_MOUSE_SCROLL',
                   0x87: 'TK_MOUSE_X', 0x88: 'TK_MOUSE_Y',
    0x89: 'TK_MOUSE_PIXEL_X', 0x8A: 'TK_MOUSE_PIXEL_Y', 0x8B: 'TK_MOUSE_WHEEL',
    0x8C: 'TK_MOUSE_CLICKS',
                   0xC0: 'TK_WIDTH', 0xC1: 'TK_HEIGHT', 0xC2: 'TK_CELL_WIDTH',
    0xC3: 'TK_CELL_HEIGHT', 0xC4: 'TK_COLOR', 0xC5: 'TK_BKCOLOR',
    0xC6: 'TK_LAYER', 0xC7: 'TK_COMPOSITION', 0xC8: 'TK_CHAR',
    0xC9: 'TK_WCHAR', 0xCA: 'TK_EVENT', 0xCB: 'TK_FULLSCREEN',
                   0xE0: 'TK_CLOSE', 0xE1: 'TK_RESIZED'}
    
    # This is the name-to-number mapping, as in bearlibterminal/terminal.py
    # The purpose of this dict is, again, to let bear_hug users work with strs
    # and avoid thinking about constants
    _state_constants = {'TK_BACKSLASH': 49, 'TK_KP_1': 89,
        'TK_KEY_RELEASED': 256, 'TK_Q': 20, 'TK_4': 33, 'TK_N': 17,
        'TK_ALIGN_TOP': 4, 'TK_RESIZED': 225, 'TK_ALIGN_RIGHT': 2,
        'TK_H': 11, 'TK_MOUSE_MIDDLE': 130, 'TK_CELL_WIDTH': 194, 'TK_3': 32,
        'TK_F10': 67, 'TK_RIGHT': 79, 'TK_ESCAPE': 41, 'TK_KP_6': 94,
        'TK_COMMA': 54, 'TK_GRAVE': 53, 'TK_PERIOD': 55, 'TK_MOUSE_CLICKS': 140,
        'TK_KP_3': 91, 'TK_MOUSE_MOVE': 133, 'TK_KP_2': 90,
        'TK_INPUT_CANCELLED': -1, 'TK_EVENT': 202, 'TK_KP_0': 98,
                        'TK_DELETE': 76, 'TK_DOWN': 81, 'TK_CLOSE': 224, 'TK_R': 21,
                        'TK_F9': 66, 'TK_M': 16, 'TK_ALIGN_MIDDLE': 12, 'TK_1': 30, 'TK_5': 34,
                        'TK_WIDTH': 192, 'TK_F': 9, 'TK_G': 10, 'TK_SLASH': 56,
                        'TK_PAGEDOWN': 78, 'TK_MOUSE_X2': 132, 'TK_KP_PLUS': 87,
                        'TK_MOUSE_X1': 131, 'TK_HOME': 74, 'TK_W': 26, 'TK_F1': 58,
                        'TK_MOUSE_X': 135, 'TK_ALIGN_LEFT': 1, 'TK_ALIGN_BOTTOM': 8,
                        'TK_FULLSCREEN': 203, 'TK_C': 6, 'TK_CONTROL': 113,
                        'TK_MOUSE_PIXEL_Y': 138, 'TK_COLOR': 196, 'TK_PAGEUP': 75,
                        'TK_RBRACKET': 48, 'TK_F11': 68, 'TK_MOUSE_SCROLL': 134,
                        'TK_KP_MULTIPLY': 85, 'TK_F8': 65, 'TK_MINUS': 45, 'TK_ENTER': 40,
                        'TK_ALT': 114, 'TK_O': 18, 'TK_Z': 29, 'TK_COMPOSITION': 199,
                        'TK_F2': 59, 'TK_T': 23, 'TK_EQUALS': 46, 'TK_ALIGN_CENTER': 3,
                        'TK_Y': 28, 'TK_BACKSPACE': 42, 'TK_SHIFT': 112, 'TK_S': 22,
                        'TK_SPACE': 44, 'TK_MOUSE_RIGHT': 129, 'TK_KP_5': 93, 'TK_KP_ENTER': 88,
                        'TK_9': 38, 'TK_MOUSE_Y': 136, 'TK_6': 35, 'TK_UP': 82,
                        'TK_BKCOLOR': 197, 'TK_2': 31, 'TK_KP_4': 92, 'TK_MOUSE_LEFT': 128,
                        'TK_F7': 64, 'TK_HEIGHT': 193, 'TK_X': 27, 'TK_V': 25, 'TK_P': 19,
                        'TK_D': 7, 'TK_KP_9': 97, 'TK_PAUSE': 72, 'TK_F6': 63, 'TK_WCHAR': 201,
                        'TK_U': 24, 'TK_KP_7': 95, 'TK_APOSTROPHE': 52, 'TK_F5': 62,
                        'TK_LBRACKET': 47, 'TK_7': 36, 'TK_8': 37, 'TK_TAB': 43, 'TK_0': 39,
                        'TK_MOUSE_PIXEL_X': 137, 'TK_CHAR': 200, 'TK_KP_DIVIDE': 84,
                        'TK_LAYER': 198, 'TK_KP_8': 96, 'TK_B': 5, 'TK_ALIGN_DEFAULT': 0,
                        'TK_K': 14, 'TK_KP_MINUS': 86, 'TK_LEFT': 80, 'TK_CELL_HEIGHT': 195,
                        'TK_SEMICOLON': 51, 'TK_INSERT': 73, 'TK_END': 77, 'TK_F12': 69,
                        'TK_MOUSE_WHEEL': 139, 'TK_F3': 60, 'TK_L': 15, 'TK_KP_PERIOD': 99,
                        'TK_J': 13, 'TK_F4': 61}
    
    def __init__(self, font_path='../demo_assets/cp437_12x12.png',
                 **kwargs):
        if kwargs:
            if any(x not in self._accepted_kwargs for x in kwargs.keys()):
                raise BearException('Only bearlibterminal library settings '
                                    +' accepted as kwargs for BearTerminal')
            self.outstring = ';'.join('{}.{}={}'.format(self._accepted_kwargs[x],
                                                        x, str(kwargs[x]))
                                 for x in kwargs)+';'
        else:
            self.outstring = None
        self.widget_locations = {}
        #  This will be one list of drawable pointers per layer. Lists are
        #  not actually allocated until at least one Widget is added to layer
        #  Lists are created when adding the first Widget and are never
        #  destroyed or resized.
        self._widget_pointers = [None for x in range(256)]
        self.default_color = 'white'
        # TODO: make font_path system independent via os.path
        self.font_path = font_path
        # Buttons currently pressed (see check_input docstring)
        self.currently_pressed = set()

    #  Methods that replicate or wrap around blt's functions

    def start(self):
        """
        Open a terminal and place it on the screen.

        Library settings that were passed as kwargs to `self.__init__()` get
        actually applied during when this method is executed.
        """
        terminal.open()
        terminal.set(
            'font: {}, size=12x12, codepage=437'.format(self.font_path))
        if self.outstring:
            terminal.set(self.outstring)
        self.refresh()
        
    def clear(self):
        """
        Remove all widgets from this terminal, but do not close it.
        """
        drawables = copy(self.widget_locations)
        for drawable in drawables:
            self.remove_widget(drawable, refresh=False)
        self.refresh()

    def refresh(self):
        """
        Refresh a terminal.

        Actually draws whatever changes were made by ``*_widget`` methods.
        """
        terminal.refresh()

    def close(self):
        """
        Close a terminal.

        Does not destroy Widget objects or call any other cleanup routine.
        """
        terminal.close()

    #  Drawing and removing stuff

    def add_widget(self, widget,
                   pos=(0, 0), layer=0, refresh=False):
        """
        Add a widget to the terminal and set `widget.terminal` to `self`.

        No two widgets are allowed to overlap within a layer and no widget can
        be added twice.

        :param widget: a Widget instance

        :param pos: top left corner of the widget

        :param layer: layer to place the widget on

        :param refresh: whether to refresh terminal after adding the widget. If False, the widget will not be actually shown until the next ``terminal.refresh()`` call
        """
        if widget in self.widget_locations.keys():
            raise BearException('Cannot add the same widget twice')
        for y in range(widget.height):
            for x in range(widget.width):
                if self._widget_pointers[layer] and \
                        self._widget_pointers[layer][pos[0] + x][pos[1] + y]:
                    raise BearException('Widgets cannot collide within a layer')
        widget.terminal = self
        widget.parent = self
        self.widget_locations[widget] = WidgetLocation(pos=pos, layer=layer)
        terminal.layer(layer)
        if not self._widget_pointers[layer]:
            size = terminal.get('window.size')
            width, height = (int(x) for x in size.split('x'))
            self._widget_pointers[layer] = [[None for y in range(height)]
                                            for x in range(width)]
        self.update_widget(widget, refresh)
    
    def remove_widget(self, widget, refresh=False):
        """
        Remove widget from the terminal.

        This method does not cause or imply the destruction of Widget object; it
        merely removes it from the terminal.

        :param widget: A widget to be removed

        :param refresh: whether to refresh the terminal after removing a widget. If False, the widget will be visible until the next ``terminal.refresh()`` call
        """
        corner = self.widget_locations[widget].pos
        terminal.layer(self.widget_locations[widget].layer)
        terminal.clear_area(*corner, widget.width, widget.height)
        for y in range(len(widget.chars)):
            for x in range(len(widget.chars[0])):
                self._widget_pointers[self.widget_locations[widget].layer]\
                    [corner[0] + x][corner[1] + y] = None
        if refresh:
            self.refresh()
        del(self.widget_locations[widget])
        widget.terminal = None
        widget.parent = None
        
    def move_widget(self, widget, pos, refresh=False):
        """
        Move widget to a new position.

        Widgets can only be moved within the layer. If it is necessary to move
        a widget from one layer to another, it should be removed and added anew.

        :param widget: A widget to be moved

        :param pos: :param refresh: whether to refresh the terminal after removing a widget. If False, the widget won't move on screen until the next ``terminal.refresh()`` call
        """
        layer = self.widget_locations[widget].layer
        self.remove_widget(widget)
        self.add_widget(widget, pos=pos, layer=layer)
        if refresh:
            self.refresh()

    def update_widget(self, widget, refresh=False):
        """
        Actually draw widget chars on screen.

        If ``widget.chars`` or ``widget.colors`` have changed, this method will
        make these changes visible. It is also called by ``self.add_widget()``
        and other methods that have a ``refresh`` argument.

        :param widget: A widget to be updated.
        """
        if widget not in self.widget_locations:
            raise BearException('Cannot update non-added Widgets')
        pos = self.widget_locations[widget].pos
        layer = self.widget_locations[widget].layer
        terminal.layer(layer)
        terminal.clear_area(*self.widget_locations[widget].pos, widget.width, widget.height)
        running_color = self.default_color
        for y in range(widget.height):
            for x in range(widget.width):
                # Widget can have None as color for its empty cells
                if widget.colors[y][x] and widget.colors[y][x] != running_color:
                    running_color = widget.colors[y][x]
                    terminal.color(running_color)
                terminal.put(pos[0] + x, pos[1] + y, widget.chars[y][x])
                self._widget_pointers[layer][pos[0] + x][pos[1] + y] = widget
        if running_color != self.default_color:
            terminal.color(self.default_color)
        if refresh:
            self.refresh()
    
    #  Getting terminal info

    def get_widget_by_pos(self, pos, layer=None):
        """
        Return the widget currently placed at the given position.

        :param pos: Position (a 2-tuple of ints)

        :param layer: A layer to look at. If this is set to valid layer number, returns the widget (if any) from that layer. If not set, return the widget from highest layer where a given cell is non-empty.
        """
        if layer:
            return self._widget_pointers[layer][pos[0]][pos[1]]
        else:
            for layer_list in reversed(self._widget_pointers):
                if layer_list and layer_list[pos[0]][pos[1]]:
                    return layer_list[pos[0]][pos[1]]
            return None
        
    # Input
    def check_input(self):
        """
        Check if terminal has input. If so, yield corresponding ``BearEvent``.

        This method returns an iterator because it's possible there would be
        more than one event in a single tick, eg when two buttons are pressed
        simultaneously.

        This method mostly just wraps bearlibterminal's input behaviour in
        `events<foo.wyrd.name/en:bearlibterminal:reference:input>`_, with
        a single exception: in bearlibterminal, when a key is pressed and held
        for more than a single tick, it first emits key_down, then waits for
        0.5 seconds. Then, if the key is not released, it assumes the key is
        indeed held and starts spamming events every tick. This makes sense to
        avoid messing up the typing (where a slow typist would get char
        sequences like tthiisss).

        Bearlibterminal, on the other hand, is meant mostly for games that
        require more precise input timing. Therefore, it starts spamming
        ``key_down`` events immediately after the button is pressed and expects
        widgets and listeners to mind their input cooldowns themselves.

        :yields: BearEvent instances with ``event_type`` set to ``misc_input``, ``key_up`` or ``key_down``.
        """
        while terminal.has_input():
            # Process the input event
            in_event = terminal.read()
            if in_event in self.misc_input:
                yield BearEvent('misc_input', self.misc_input[in_event])
            elif in_event in self._down_codes:
                self.currently_pressed.add(self._down_codes[in_event])
            elif in_event in self._up_codes:
                try:
                    self.currently_pressed.remove(self._up_codes[in_event])
                except KeyError:
                    # It's possible that the button was pressed before launching
                    # the bear_hug app, and released now. Then it obviously
                    # couldn't be in self.currently_pressed, causing exception
                    pass
                yield BearEvent('key_up', self._up_codes[in_event])
            else:
                raise BearException('Unknown input code {}'.format(in_event))
        for key in self.currently_pressed:
            yield BearEvent('key_down', key)
    
    def check_state(self, query):
        """
        Wrap BLT `state <http://foo.wyrd.name/en:bearlibterminal:reference#state>`_

        Accepts any of the ``TK_*`` strings and returns whatever ``terminal.state`` has
        to say about it.

        :param query: query string
        """
        return terminal.state(self._state_constants[query])


#  A loop

class BearLoop:
    """
    A loop that passes events around every 1/fps seconds.

    Every tick, the loop calls its ``run_iteration()`` method, adding
    tick-related and input-related events to the queue, and then forcing it to
    start passing all events to the correct subscribers.

    There are two tick-related events. In the beginning of the tick it's
    ``tick``-type event whose value is time since the last similar event (in
    seconds). This is guaranteed to be emitted before any other events from this
    tick, since the queue wouldn't finish the previous one until it was empty.

    In the end of the tick it's a ``service``-type event with the value
    'tick_over', which is emitted after the entire queue has been processed.
    It is meant to let subscribers know that the tick is over and nothing is
    going to happen until the next one. This is, for example, a perfect moment
    for a Layout to redraw itself, or for a logger to write everything down.

    If any events are emitted in response to this event, they will be passed
    around before the next ``tick``. This is a great source of bugs, so it is
    not advised to respond to ``tick_over`` unless absolutely necessary.

    The loop cannot be started until it has a valid terminal. When the loop is
    stopped, this terminal is shut down.

    :param terminal: a BearTerminal instance to collect input from.

    :param queue: a bear_hug.event.BearEventDispatcher instance to send events to.

    :param fps: a number of times per second this loop should process events.
    """

    def __init__(self, terminal, queue, fps=30):
        # Assumes terminal to be running
        self.terminal = terminal
        self.queue = queue
        # The loop listens for service events so that it knows when to shutdown
        self.queue.register_listener(self, 'service')
        self.frame_time = 1/fps
        self.stopped = False
        self.last_time = 0
        
    def run(self):
        """
        Start a loop.

        It would run until stopped with ``self.stop()``
        """
        # An imaginary "zeroth" tick to give the first tick correct timing
        self.last_time = time.time() - self.frame_time
        while not self.stopped:
            # All actual processes happen here
            # Sends time since last tick *started*
            t = time.time() - self.last_time
            self.last_time = time.time()
            self._run_iteration(t)
            sleep_time = self.frame_time - time.time() + self.last_time
            if sleep_time > 0.05*self.frame_time:
                # If frame was finished early, wait for it
                # But only if there is enough spare time to make it worthwhile.
                # Otherwise, on a laggy system sleep_time may be positive when
                # the `if` check runs, but negative by the time `sleep` is
                # called, causing a crash.
                time.sleep(self.frame_time - time.time() + self.last_time)
        # When the loop stops, it closes the terminal. Everyone is expected to
        # have caught the shutdown service event
        self.terminal.close()
               
    def stop(self):
        """
        Order the loop to stop.

        It would not actually do it until the current tick is processed.
        """
        self.stopped = True
    
    def _run_iteration(self, time_since_last_tick):
        # Get input events, if any
        for event in self.terminal.check_input():
            self.queue.add_event(event)
        self.queue.add_event(BearEvent(event_type='tick',
                                       event_value=time_since_last_tick))
        self.queue.dispatch_events()
        # Sending "Tick over" event, reminding widgets to update themselves
        self.queue.add_event(BearEvent(event_type='service',
                                       event_value='tick_over'))
        self.queue.dispatch_events()
        self.terminal.refresh()
        
    def on_event(self, event):
        if event.event_value == 'shutdown':
            self.stopped = True
            
    @property
    def fps(self):
        return round(1/self.frame_time)
    
    @fps.setter
    def fps(self, value):
        if not isinstance(value, int):
            raise BearLoopException('Only int acceptable as FPS')
        self.frame_time = 1/value
        
    
#  Misc classes
