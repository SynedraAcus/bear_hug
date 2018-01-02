"""
An object-oriented bearlibterminal wrapper with the support for complex ASCII
art and widget-like behaviour.
"""

from bearlibterminal import terminal
import bearlibterminal
from bear_utilities import shapes_equal, copy_shape, BearException
from event import BearEvent

import time
from copy import copy


class BearTerminal:
    """
    A main terminal class.
    Accepts bearlibterminal library configuration options as kwargs.
    """
    # kwargs to init are passed to bearlibterminal.terminal.set()
    # Currently only library settings are supported
    accepted_kwargs = {'encoding': 'terminal', 'size': 'window',
                       'cellsize': 'window', 'title': 'window', 'icon':'window',
                       'resizeable': 'window', 'fullscreen': 'window',
                       
                       'filter': 'input', 'precise-mouse': 'input',
                       'mouse-cursor': 'input', 'cursor-symbol': 'input',
                       'cursor-blink-rate': 'input', 'alt-functions': 'input',
                       'filter': 'input',
    
                       'postformatting': 'output', 'vsync': 'output',
                       'tab-width': 'output',
                       
                       'file': 'log', 'level': 'log', 'mode': 'log'
                       }
    
    # Bearlibterminal's input codes and terminal state codes are converted to
    # constants before emitting events, so that downstream widgets could process
    # them without asking the terminal to explain what the fuck 0x50 is.
    
    # These are codes for keys and mouse buttons going down
    down_codes = {0x04: 'TK_A', 0x05: 'TK_B', 0x06: 'TK_C', 0x07: 'TK_D',
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
    up_codes = {260: 'TK_A', 261: 'TK_B', 262: 'TK_C', 263: 'TK_D', 264: 'TK_E',
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
    state_constants = {'TK_BACKSLASH': 49, 'TK_KP_1': 89,
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
    
    def __init__(self, *args, **kwargs):
        if kwargs:
            if any(x not in self.accepted_kwargs for x in kwargs.keys()):
                raise BearException('Only bearlibterminal library settings accepted'
                                    +' as kwargs for BearTerminal')
            self.outstring = ';'.join('{}.{}={}'.format(self.accepted_kwargs[x],
                                                        x, str(kwargs[x]))
                                 for x in kwargs)+';'
        else:
            self.outstring = None
        self.drawable_locations = {}
        #  This will be one list of drawable pointers per layer. Lists are
        #  not actually allocated until at least one Widget is added to layer
        #  Lists are created when adding the first Widget and are never
        #  destroyed or resized.
        self._drawable_pointers = [None for x in range(256)]
        self.default_color = 'white'

    #  Methods that replicate or wrap around blt's functions

    def start(self):
        """
        Open a terminal and place it on the screen.
        :return:
        """
        terminal.open()
        if self.outstring:
            terminal.set(self.outstring)
        self.refresh()
        
    def clear(self):
        """
        Remove all drawable_locations from this terminal
        :return:
        """
        drawables = copy(self.drawable_locations)
        for drawable in drawables:
            self.remove_drawable(drawable, refresh=False)
        self.refresh()

    def refresh(self):
        terminal.refresh()

    def close(self):
        terminal.close()

    #  Drawing and removing stuff

    def add_drawable(self, drawable,
                     pos=(0, 0), layer=0, refresh=False):
        """
        Add a drawable to the terminal.
        Sets drawable.terminal to self
        :param drawable: a Widget instance
        :param pos: top left corner of the drawable
        :param layer: layer to place the drawable on
        :param refresh: whether to refresh terminal after adding the drawable.
        If this is False, the drawable will be invisible until the next
        `terminal.refresh()` call
        :return:
        """
        if drawable in self.drawable_locations.keys():
            raise BearException('Cannot add the same drawable twice')
        for y in range(len(drawable.chars)):
            for x in range(len(drawable.chars[0])):
                if self._drawable_pointers[layer] and \
                        self._drawable_pointers[layer][pos[0]+x][pos[1]+y]:
                    raise BearException('Drawables cannot collide within a layer')
        drawable.terminal = self
        self.drawable_locations[drawable] = DrawableLocation(pos=pos, layer=layer)
        terminal.layer(layer)
        running_color = 'white'
        if not self._drawable_pointers[layer]:
            size = terminal.get('window.size')
            width, height = (int(x) for x in size.split('x'))
            self._drawable_pointers[layer] = [[None for y in range(height)]
                                              for x in range(width)]

        for y in range(len(drawable.chars)):
            for x in range(len(drawable.chars[y])):
                if drawable.colors[y][x] != running_color:
                    running_color = drawable.colors[y][x]
                    terminal.color(running_color)
                terminal.put(pos[0]+x, pos[1]+y, drawable.chars[y][x])
                self._drawable_pointers[layer][pos[0]+x][pos[1]+y] = drawable
        if running_color != self.default_color:
            terminal.color(self.default_color)
        if refresh:
            self.refresh()
    
    def remove_drawable(self, drawable, refresh=False):
        """
        Remove drawable from the terminal
        #TODO: check for other drawables that can become visible once
        this one is destroyed
        :param drawable:
        :param refresh: whether to refresh the terminal after removing drawable.
        If this is False, the drawable will be visible until the next
        `terminal.refresh()` call
        :return:
        """
        corner = self.drawable_locations[drawable].pos
        terminal.layer(self.drawable_locations[drawable].layer)
        terminal.clear_area(*corner, len(drawable.chars[0]), len(drawable.chars))
        for y in range(len(drawable.chars)):
            for x in range(len(drawable.chars[0])):
                self._drawable_pointers[self.drawable_locations[drawable].layer]\
                    [corner[0] + x][corner[1] + y] = None
        if refresh:
            self.refresh()
        del(self.drawable_locations[drawable])
        
    def move_drawable(self, drawable, pos, refresh=False):
        """
        Move drawable to a new position.
        Does not change the layer.
        :param drawable:
        :param pos:
        :return:
        """
        layer = self.drawable_locations[drawable].layer
        self.remove_drawable(drawable)
        self.add_drawable(drawable, pos=pos, layer=layer)
        if refresh:
            self.refresh()

    def update_drawable(self, drawable, refresh=False):
        """
        Reload the drawable on the screen.
        Works by removing it and adding it again on its current position
        :param drawable:
        :return:
        """
        layer = self.drawable_locations[drawable].layer
        pos = self.drawable_locations[drawable].pos
        self.remove_drawable(drawable)
        self.add_drawable(drawable, pos=pos, layer=layer)
        if refresh:
            self.refresh()
    
    #  Getting terminal info

    def get_drawable_by_pos(self, pos, layer=None):
        """
        Returns the drawable currently placed at the given position.
        If layer is set, checks only that layer. Otherwise returns the drawable
        at the highest layer.
        :param pos: 
        :param layer: 
        :return: 
        """
        if layer:
            return self._drawable_pointers[layer][pos[0]][pos[1]]
        else:
            for layer_list in reversed(self._drawable_pointers):
                if layer_list and layer_list[pos[0]][pos[1]]:
                    return layer_list[pos[0]][pos[1]]
            return None
        
    # Input
    def check_input(self):
        """
        Check if terminal has input. If so, yield corresponding `BearEvent`(s)
        This method returns an iterator because it's possible there would be
        more than one event in a single tick
        :param self:
        :return:
        """
        while terminal.has_input():
            # Process the input event
            in_event = terminal.read()
            if in_event in self.misc_input:
                yield BearEvent('misc_input', self.misc_input[in_event])
            elif in_event in self.down_codes:
                yield BearEvent('key_down', self.down_codes[in_event])
            elif in_event in self.up_codes:
                yield BearEvent('key_up', self.up_codes[in_event])
            else:
                raise BearException('Unknown input code {}'.format(in_event))
    
    def check_state(self, query):
        """
        A wrapper around BLT `state` function
        Accepts any of the TK_* strings and returns whatever terminal.state has
        to say about it.
        :param query:
        :return:
        """
        return terminal.state(self.state_constants[query])


#  A loop

class BearLoop:
    """
    A loop that passes event around every once in a while.
    Every 1/fps seconds, to be precise
    """
    def __init__(self, terminal, queue, fps=30):
        # Assumes terminal to be running
        self.terminal = terminal
        self.queue = queue
        self.frame_time = 1/fps
        self.stopped = False
        self.last_time = 0
        
    def run(self):
        """
        Start a loop.
        It would run indefinitely and can be stopped with `self.stop`
        :return:
        """
        # An imaginary "zeroth" tick to give the first tick correct timing
        self.last_time = time.time() - self.frame_time
        while not self.stopped:
            # All actual processes happen here
            # Sends time since last tick *started*
            t = time.time() - self.last_time
            self.last_time = time.time()
            self.run_iteration(t)
            if time.time() - self.last_time < self.frame_time:
                # If frame was finished early, wait for it
                time.sleep(self.frame_time - time.time() + self.last_time)
               
    def stop(self):
        """
        Stop the loop.
        It would quit after finishing the current iteration
        :return:
        """
        self.stopped = True
    
    def run_iteration(self, time_since_last_tick):
        # Get input events, if any
        for event in self.terminal.check_input():
            self.queue.add_event(event)
        self.queue.add_event(BearEvent(event_type='tick',
                                       event_value=time_since_last_tick))
        self.queue.dispatch_events()
        self.terminal.refresh()
    
#  Widget classes


class Widget:
    """
    The base class for things that can be placed on the terminal.
    This class is inactive and is intended for purely decorative non-animated
    objects. Event processing and animations are covered by its subclasses.
    
    Accepted parameters:
    `chars`: a list of unicode characters
    `colors`: a list of colors. Anything that is accepted by terminal.color()
    goes here (a color name or an 0xAARRGGBB integer)
    """
    def __init__(self, chars, colors):
        if not isinstance(chars, list) or not isinstance(colors, list):
            raise BearException('Chars and colors should be lists')
        if not shapes_equal(chars, colors):
            raise BearException('Chars and colors should have the same shape')
        self.chars = chars
        self.colors = colors
        # A drawable may want to know about the terminal it's attached to
        self.terminal = None
        
    def on_event(self, event):
        pass
        

class Label(Widget):
    """
    A drawable that displays text.
    Accepts only a single string, whether single- or multiline.
    Does not (yet) support complex text markup used by bearlibterminal
    :param text: string to be displayed
    :param just: one of 'left', 'right' or 'center'. Default 'left'
    :param color: bearlibterminal-compatible color. Default 'white'
    :param width: text area width. Defaults to the length of the longest
    substring in `text`
    """
    def __init__(self, text,
                 just='left', color='white', width = None):
        chars = Label._generate_chars(text, width, just)
        colors = copy_shape(chars, color)
        super().__init__(chars, colors)
    
    @classmethod
    def _generate_chars(cls, text, width, just):
        """
        Internal method that generates a justified char list for the Label
        :param text:
        :param just:
        :return:
        """
        
        def justify(line, width, just_type):
            if len(line) < width:
                if just_type == 'left':
                    return line.ljust(width)
                elif just_type == 'right':
                    return line.rjust(width)
                elif just_type == 'center':
                    lj = width - int((width-len(line))/2)
                    return line.ljust(lj).rjust(width)
                else:
                    raise BearException('Justification should be \'left\', \'right\' or \'center\'')
            else:
                return line
        
        lines = text.split('\n')
        if not width:
            width = max(len(x) for x in lines)
        return [list(justify(x, width, just)) for x in lines]
        
    
#  Misc classes

class DrawableLocation:
    """
    Data class with position and layer of a Widget
    """
    def __init__(self, pos, layer):
        self.pos = pos
        self.layer = layer
