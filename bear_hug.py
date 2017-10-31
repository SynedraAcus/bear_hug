"""
An object-oriented bearlibterminal wrapper with the support for complex ASCII
art and widget-like behaviour.
"""

from bearlibterminal import terminal
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
    
                       'postformatting': 'output', 'vsync': 'output',
                       'tab-width': 'output',
                       
                       'file': 'log', 'level':'log', 'mode': 'log'
                       }
    
    def __init__(self, *args, **kwargs):
        if kwargs:
            if any(x not in self.accepted_kwargs for x in kwargs.keys()):
                raise BearException('Only bearlibterminal library settings accepted'
                                    +' as kwargs for BearTerminal')
            self.outstring = ';'.join('{}.{}={}'.format(self.accepted_kwargs[x], x,
                                                         str(kwargs[x]))
                                 for x in kwargs)+';'
        else:
            self.outstring = None
        self.drawable_locations = {}
        #  This will be one list of drawable pointers per layer. Lists are
        #  not actually allocated until at least one Drawable is added to layer
        #  Lists are created when adding the first Drawable and are never
        #  destroyed or resized.
        self._drawable_pointers = [None for x in range(256)]
        self.default_color = 'white'

    #  Methods that replicate or wraparound blt's functions

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
                     pos=(0, 0), layer=0, refresh=True):
        """
        Add a drawable to the terminal.
        Doesn't check for overlap and potentially overwrites any drawable_locations
        present in the area.
        :param drawable: a Drawable instance
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
        
    def remove_drawable(self, drawable, refresh=True):
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
                    [x][y] = None
        if refresh:
            self.refresh()
        del(self.drawable_locations[drawable])
        
    def move_drawable(self, drawable, pos):
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


#  A loop

class BearLoop:
    """
    A loop that passes event around every once in a while.
    Every 1/fps seconds, to be precise
    """
    def __init__(self, terminal, queue, fps=30):
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
        self.last_time = time.time()
        while not self.stopped:
            # All actual processes happen here
            self.run_iteration(time.time()-self.last_time)
            t = time.time() - self.last_time
            if t < self.frame_time:
                # If frame was finished early, wait for it
                time.sleep(self.frame_time - t)
               
    def stop(self):
        """
        Stop the loop.
        It would quit after finishing the current iteration
        :return:
        """
        self.stopped = True
    
    def run_iteration(self, time_since_last_tick):
        self.queue.add_event(BearEvent(event_type='tick',
                                       event_value=time_since_last_tick))
        self.queue.dispatch_events()
        self.terminal.refresh()
    
#  Widget classes


class Drawable:
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
        

class Label(Drawable):
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
        
    
class Widget(Drawable):
    def __init__(self):
        raise NotImplementedError('Widgets are yet to be implemented')


#  Service classes

class DrawableLocation:
    """
    Data class with position and layer of a Drawable
    """
    def __init__(self, pos, layer):
        self.pos = pos
        self.layer = layer
