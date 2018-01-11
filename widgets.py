#  Widget and Listener classes

from bear_hug import BearTerminal
from bear_utilities import shapes_equal, copy_shape, BearException, \
    BearLayoutException
from collections import deque
from event import BearEvent


class Widget:
    """
    The base class for things that can be placed on the terminal.
    This class is inactive and is intended for purely decorative non-animated
    objects. Event processing and animations are covered by its subclasses.

    Accepted parameters:
    `chars`: a list of unicode characters
    `colors`: a list of colors. Anything that is accepted by terminal.color()
    goes here (a color name or an 0xAARRGGBB integer).

    These two list should be exactly the same shape, otherwise the BearException
    is raised.
    """
    
    def __init__(self, chars, colors):
        if not isinstance(chars, list) or not isinstance(colors, list):
            raise BearException('Chars and colors should be lists')
        if not shapes_equal(chars, colors):
            raise BearException('Chars and colors should have the same shape')
        self.chars = chars
        self.colors = colors
        # A widget may want to know about the terminal it's attached to
        self.terminal = None
    
    def on_event(self, event):
        pass


class Layout(Widget):
    """
    A widget that can add others as its children.
    All children get drawn to its `chars` and are thus displayed on a single
    bearlibterminal layer. The layout does not explicitly pass events to its
    children, they are expected to subscribe to event queue by themselves.
    Children are allowed to overlap, but in that case the most recent one's char
    is actually drawn.
    The Layout is initialized with a single child, which is given chars and
    colors provided at Layout creation. This child is available as l.children[0]
    or as l.background
    The Layout automatically redraws itself on `tick` event, whether its
    children have updated or not. Due to the order events are emitted, any
    changes that happened in children's chars or colors in current frame (except
    as a direct response to input events) will be drawn on the *next* frame.
    """
    def __init__(self, chars, colors):
        super().__init__(chars, colors)
        self.children = []
        # For every position, remember all the widgets that may want to place
        # characters in it, but draw only the latest one
        self._child_pointers = copy_shape(self.chars, None)
        # copy_shape does not work with lists correctly, so.
        for line in range(len(self._child_pointers)):
            for char in range(len(self._child_pointers[0])):
                self._child_pointers[line][char] = []
        self.child_locations = {}
        # The widget with Layout's chars and colors is created and added to the
        # Layout as the first child. It is done even if both are empty, just in
        # case someone wants to add background later
        w = Widget(self.chars, self.colors)
        self.add_child(w, pos=(0, 0))
        
    # Operations on children
    def add_child(self, child, pos):
        """
        Add a widget as a child at a given (relative) position.
        The child has to be a Widget or a Widget subclass that haven't yet been
        added to this Layout and whose dimensions are less than or equal to the
        Layout's
        :param child:
        :return:
        """
        if not isinstance(child, Widget):
            raise BearLayoutException('Cannot add non-Widget to a Layout')
        if child in self.children:
            raise BearLayoutException('Cannot add the same widget to layout twice')
        if len(child.chars) > len(self.chars) or \
                len(child.chars[0]) > len(self.chars[0]):
            raise BearLayoutException('Cannot add child that is bigger than a Layout')
        if len(child.chars) + pos[0] > len(self.chars) or \
                len(child.chars[0]) + pos[1] > len(self.chars[0]):
            raise BearLayoutException('Child won\'t fit at this position')
        if child is self:
            raise BearLayoutException('Cannot add Layout as its own child')
        self.children.append(child)
        self.child_locations[child] = pos
        for y in range(len(child.chars)):
            for x in range(len(child.chars[0])):
                self._child_pointers[pos[1] + y][pos[0] + x].append(child)

    def remove_child(self, child, remove_completely=True):
        """
        Remove a child from a Layout.
        :param child: the child to remove
        :param remove_completely: if False, the child is only removed from the
        screen, but remains in the children list. This is not intended to be
        used and is included only to prevent self.move_child from messing with
        child order.
        :return:
        """
        if child not in self.children:
            raise BearLayoutException('Layout can only remove its child')
        # process pointers
        for y in range(len(child.chars)):
            for x in range(len(child.chars[0])):
                self._child_pointers[self.child_locations[child][1] + y] \
                        [self.child_locations[child][0] + x].remove(child)
        if remove_completely:
            del(self.child_locations[child])
            self.children.remove(child)
    
    def move_child(self, child, new_pos):
        self.remove_child(child, remove_completely=False)
        self.add_child(child, pos=new_pos)
    
    # BG's chars and colors are not meant to be set directly
    @property
    def background(self):
        return self.children[0]
    
    @background.setter
    def background(self, value):
        if not isinstance(value, Widget):
            raise BearLayoutException('Only Widget can be added as background')
        if not shapes_equal(self.chars, value.chars):
            # chars and colors are always the same size
            raise BearLayoutException('Wrong Layout background size')
        for row in range(len(self.chars)):
            for column in range(len(self.chars)):
                self._child_pointers[row][column][0] = value
                # self.colors[row][column][0] = value
        del self.child_locations[self.children[0]]
        self.child_locations[value] = (0, 0)
        self.children[0] = value
        
    def _rebuild_self(self):
        """
        Build fresh chars and colors for self
        :return:
        """
        chars = copy_shape(self.chars, ' ')
        colors = copy_shape(self.colors, None)
        for line in range(len(chars)):
            for char in range(len(chars[0])):
                for child in self._child_pointers[line][char][::-1]:
                    # Addressing the correct child position
                    c = child.chars[line-self.child_locations[child][1]] \
                        [char - self.child_locations[child][0]]
                    if c != ' ':
                        # Spacebars are used as empty space and are transparent
                        chars[line][char] = c
                        break
                colors[line][char] = \
                    child.colors[line - self.child_locations[child][1]] \
                    [char - self.child_locations[child][0]]
        self.chars = chars
        self.colors = colors
    
    def on_event(self, event):
        """
        The Layout redraws itself on every frame
        :return:
        """
        if event.event_type == 'tick':
            self._rebuild_self()
            self.terminal.update_widget(self)
    
    #Service
    def get_absolute_pos(self, relative_pos):
        """
        Get an absolute position (in terminal coordinates) for any location
        within self.
        :param relative_pos:
        :return:
        """
        self_pos = self.terminal.widget_locations(self).pos
        return self_pos[0]+relative_pos[0], self_pos[1]+relative_pos[1]
        
        
class Label(Widget):
    """
    A widget that displays text.
    Accepts only a single string, whether single- or multiline.
    Does not (yet) support complex text markup used by bearlibterminal
    :param text: string to be displayed
    :param just: horizontal text justification, one of 'left', 'right'
    or 'center'. Default 'left'.
    :param color: bearlibterminal-compatible color. Default 'white'
    :param width: text area width. Defaults to the length of the longest
    substring in `text`
    """
    
    def __init__(self, text,
                 just='left', color='white', width=None):
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
                    lj = width - int((width - len(line)) / 2)
                    return line.ljust(lj).rjust(width)
                else:
                    raise BearException(
                        'Justification should be \'left\', \'right\' or \'center\'')
            else:
                return line
        
        lines = text.split('\n')
        if not width:
            width = max(len(x) for x in lines)
        return [list(justify(x, width, just)) for x in lines]


class FPSCounter(Widget):
    """
    A simple widget that measures FPS.
    Actually just prints 1/(average runtime over the last 100 ticks, in seconds)
    Updates every frame
    """
    def __init__(self, *args, **kwargs):
        self.samples_deque = deque(maxlen=100)
        # Something to be dispayed on th 1st frame
        chars = [list(str(30))]
        color = copy_shape(chars, 'white')
        super().__init__(chars, color, *args, **kwargs)
    
    def _update_self(self):
        self.chars = [
            list(str(round(len(self.samples_deque) / sum(self.samples_deque))))]
        self.colors = copy_shape(self.chars, 'white')
    
    def on_event(self, event):
        # Update FPS estimate
        if event.event_type == 'tick':
            self.samples_deque.append(event.event_value)
            self._update_self()
            if self.terminal:
                self.terminal.update_widget(self)
        elif event.event_type == 'input':
            print(event.event_value)


# Listeners
class Listener:
    """
    A base class for the things that need to know about terminal and receive
    events from the queue, but are not displayed on screen.
    """
    def __init__(self):
        self.terminal = None
    
    def on_event(self, event):
        raise NotImplementedError('Listener base class is doing nothing')
    
    def register_terminal(self, terminal):
        """
        Register a terminal with which this listener will interact
        :param terminal: A BearTerminal instance
        :return:
        """
        if not isinstance(terminal, BearTerminal):
            raise TypeError('Only BearTerminal instances registered by Listener')
        self.terminal = terminal
        
    
class ClosingListener(Listener):
    """
    The listener that waits for TK_CLOSE input event (Alt-F4 or closing window)
    and sends the shutdown service event to the queue. All widgets are expected
    to listen to it and immediately save their data or whatever they need to do.
    On the next tick ClosingListener closes the terminal and queue altogether.
    """
    def __init__(self):
        super().__init__()
        self.countdown = 2
        self.counting = False
        
    def on_event(self, event):
        if event.event_type == 'misc_input' and event.event_value == 'TK_CLOSE':
            self.counting = True
            return BearEvent(event_type='service', event_value='shutdown_ready')
        if event.event_type == 'tick':
            if self.counting:
                self.countdown -= 1
                if self.countdown == 0:
                    return BearEvent(event_type='service',
                                     event_value='shutdown')
