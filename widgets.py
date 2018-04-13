"""
Various useful Widget and Listener classes
These widgets and listeners are usable outside the ECS and should be sufficient
for simpler games and apps. However, for the sake of clearer architecture,
entities are recommended.
"""

from bear_hug import BearTerminal
from bear_utilities import shapes_equal, blit, copy_shape, BearException, \
    BearLayoutException
from collections import deque
from event import BearEvent
from time import time


class Widget:
    """
    The base class for things that can be placed on the terminal.
    This class is inactive and is intended to be either inherited from or used
    for purely decorative non-animated objects. Event processing and animations
    are covered by its subclasses; while it has `on_event()` method, it does
    nothing. This allows Widgets to work without subscribing to the queue and
    saves some tacts on not redrawing them unless the Widget itself considers it
    necessary.

    Accepted parameters:
    `chars`: a list of unicode characters
    `colors`: a list of colors. Anything that is accepted by terminal.color()
    goes here (a color name or a 0xAARRGGBB/0xRRGGBB/0xRGB/0xARGB integer).

    `chars` and `colors` should be exactly the same shape, otherwise the
    BearException is raised.
    """
    
    def __init__(self, chars, colors):
        if not isinstance(chars, list) or not isinstance(colors, list):
            raise BearException('Chars and colors should be lists')
        if not shapes_equal(chars, colors):
            raise BearException('Chars and colors should have the same shape')
        self.chars = chars
        self.colors = colors
        # A widget may want to know about the terminal it's attached to
        self._terminal = None
        # Or a parent
        self._parent = None
        
    def on_event(self, event):
        # Root widget does not raise anything here, because Widget() can be
        # erroneously subscribed to a queue. While useless, that's not really a
        # fatal error.
        pass
    
    @property
    def terminal(self):
        return self._terminal
    
    @terminal.setter
    def terminal(self, value):
        if value and not isinstance(value, BearTerminal):
            raise BearException('Only a BearTerminal can be set as ' +
                                'Widget.terminal')
        self._terminal = value
        
    @property
    def parent(self):
        return self._parent
    
    @parent.setter
    def parent(self, value):
        if value and not isinstance(value, (Widget, BearTerminal)):
            raise BearException(
                'Only a widget or terminal can be a widget\'s parent')
        self._parent = value
        
    def flip(self, axis):
        """
        Flip a widget along one of the axes.
        
        Rotates chars and colors either horizontally ('x' or 'horizontal') or
        vertically ('y' or 'vertical'). Note that this method has **extremely**
        limited uses: first, it only affects chars and colors *as they are now*.
        If later the widget gets updated via animation, updating label text,
        Layout's children being redrawn, etc., it will be un-flipped again.
        Second, most ASCII-art does not take it well. You're probably safe with
        something almost symmetrical, like background garbage and such, but for
        complex images it's better to provide both left and right versions.
        
        Unlike raster and vector graphics, there is no general way to flip an
        ASCII image programmatically. Except, of course, flipping tiles
        themselves which I find aesthetically unacceptable for my projects.
        
        :param axis:
        :return:
        """
        if axis in ('x', 'horizontal'):
            self.chars = [self.chars[x][::-1] for x in range(len(self.chars))]
            self.colors = [self.colors[x][::-1] for x in range(len(self.colors))]
        elif axis in ('y', 'vertical'):
            self.chars = self.chars[::-1]
            self.colors = self.colors[::-1]


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
    children have updated or not.
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
    
    @property
    def terminal(self):
        return self._terminal
    
    # This setter propagates the terminal value to all the Layout's children.
    # It's necessary because some of them may be added before placing Layout on
    # the screen and thus end up terminal-less.
    @terminal.setter
    def terminal(self, value):
        if value and not isinstance(value, BearTerminal):
            raise BearException('Only BearTerminal can be added as terminal')
        self._terminal = value
        for child in self.children:
            child.terminal = value
        
    # Operations on children
    def add_child(self, child, pos, skip_checks = False):
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
        if len(child.chars) > len(self._child_pointers) or \
                len(child.chars[0]) > len(self._child_pointers[0]):
            raise BearLayoutException('Cannot add child that is bigger than a Layout')
        if len(child.chars) + pos[1] > len(self._child_pointers) or \
                len(child.chars[0]) + pos[0] > len(self._child_pointers[0]):
            raise BearLayoutException('Child won\'t fit at this position')
        if child is self:
            raise BearLayoutException('Cannot add Layout as its own child')
        self.children.append(child)
        self.child_locations[child] = pos
        child.terminal = self.terminal
        child.parent = self
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
            child.terminal = None
            child.parent = None
    
    def move_child(self, child, new_pos):
        self.remove_child(child, remove_completely=False)
        self.add_child(child, pos=new_pos, skip_checks=True)
    
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
            for column in range(len(self.chars[0])):
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
        if event.event_type == 'service' and event.event_value == 'tick_over':
            self._rebuild_self()
            # print(type(self.parent))
            if isinstance(self.parent, BearTerminal):
                # print('Updating')
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


class ScrollableLayout(Layout):
    """
    A Layout that can show only a part of its surface.
    
    Like a Layout, accepts `chars` and `colors` on creation, which should be the
    size of the entire layout, not the visible area. The latter is initialized
    by `view_pos` and `view_size` arguments.
    
    Works by overloading _rebuild_self to only show a part of child_pointers
    """
    def __init__(self, chars, colors,
                 view_pos=(0,0), view_size=(10, 10)):
        super().__init__(chars, colors)
        if not 0 <= view_pos[0] <= len(chars[0]) - view_size[0] \
                or not 0 <= view_pos[1] <= len(chars) - view_size[1]:
            raise BearLayoutException('Initial viewpoint outside ' +
                                      'ScrollableLayout')
        if not 0 < view_size[0] <= len(chars[0]) \
                or not 0 < view_size[1] <= len(chars):
            raise BearLayoutException('Invalid view field size')
        self.view_pos = view_pos
        self.view_size = view_size
        self._rebuild_self()
    
    def _rebuild_self(self):
        """
        Same as `Layout()._rebuild_self`, but all child positions are also
        offset by `view_pos`. Obviously, only `view_size[1]` lines
        `view_size[0]` long are set as `chars` and `colors`.
        :return:
        """
        chars = [[' ' for x in range(self.view_size[0])] \
                 for y in range(self.view_size[1])]
        colors = copy_shape(chars, None)
        for line in range(self.view_size[1]):
            for char in range(self.view_size[0]):
                for child in self._child_pointers[self.view_pos[1]+line] \
                                     [self.view_pos[0] + char][::-1]:
                    # Addressing the correct child position
                    c = child.chars[self.view_pos[1] + line-self.child_locations[child][1]] \
                        [self.view_pos[0] + char-self.child_locations[child][0]]
                    if c != ' ':
                        # Spacebars are used as empty space and are transparent
                        chars[line][char] = c
                        break
                colors[line][char] = \
                    child.colors[self.view_pos[1] + line - self.child_locations[child][1]] \
                    [self.view_pos[0] + char - self.child_locations[child][0]]
        self.chars = chars
        self.colors = colors
    
    def resize_view(self, new_size):
        # TODO: support resizing view.
        # This will require updating the pointers in terminal or parent layout
        pass
    
    def scroll_to(self, pos):
        """
        Move field of view to `pos`.
        
        Raises `BearLayoutException` on incorrect position
        :param pos: tuple of ints
        :return:
        """
        if not (len(pos) == 2 and all((isinstance(x, int) for x in pos))):
            raise BearLayoutException('Field of view position should be 2 ints')
        if not 0 <= pos[0] <= len(self._child_pointers[0]) - self.view_size[0] \
                or not 0 <= pos[1] <= len(self._child_pointers)-self.view_size[1]:
            raise BearLayoutException('Scrolling to invalid position')
        self.view_pos = pos
    
    def scroll_by(self, shift):
        """
        Move field of view by `shift[0]` to the right and by `shift[1]` down.
        
        Raises `BearLayoutException` on incorrect position
        :param shift: tuple of ints
        :return:
        """
        pos = (self.view_pos[0] + shift[0], self.view_pos[1] + shift[1])
        self.scroll_to(pos)
    
    
# Animations and other complex decorative Widgets
class SimpleAnimationWidget(Widget):
    """
    A simple animated widget that cycles through the frames.

    Accepts two parameters on creation:
    `frames` an iterable of (chars, colors) tuples. These should all be
    the same size
    `fps` frames per second.
    `emit_ecs`: whether to emit ecs_update events on every frame. Useless for
    widgets outside ecs system, but those on ECSLayout are not redrawn unless
    this event is emitted or something else causes ECSLayout to redraw
    """
    
    def __init__(self, frames, fps, emit_ecs = False):
        super().__init__(*frames[0])
        if not all((shapes_equal(x[0], frames[0][0]) for x in frames[1:])) \
                or not all(
            (shapes_equal(x[1], frames[0][1]) for x in frames[1:])):
            raise BearException('Frames should be equal size')
        self.frames = frames
        self.frame_time = 1 / fps
        self.running_index = 0
        self.have_waited = 0
        self.emit_ecs = emit_ecs
    
    def on_event(self, event):
        if event.event_type == 'tick':
            self.have_waited += event.event_value
            if self.have_waited >= self.frame_time:
                self.running_index += 1
                if self.running_index >= len(self.frames):
                    self.running_index = 0
                self.chars = self.frames[self.running_index][0]
                self.colors = self.frames[self.running_index][1]
                self.have_waited = 0
                if self.emit_ecs:
                    return BearEvent(event_type='ecs_update')
        elif self.parent is self.terminal and event.event_type == 'service' \
                and event.event_value == 'tick_over':
            # This widget is connected to the terminal directly and must update
            # itself without a layout
            self.terminal.update_widget(self)
            

# Functional widgets. Please note that these include no decoration, BG, frame or
# anything else. Ie Label is just a chunk of text on the screen, FPSCounter and
# MousePosWidget are just the numbers that change. For the more complex visuals,
# embed these into a Layout with a preferred BG

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
    substring in `text`.
    :param height: text area height. Defaults to the line count in `text`

    Label's text can be edited at any time by setting label.text property. Note
    that it overwrites any changes to `self.chars` and `self.colors` made after
    setting `self.text` the last time.
    
    Unlike text, Label's height and width cannot be changed. Set its height and
    width to accomodate all possible inputs during Label creation.
    """
    
    def __init__(self, text,
                 just='left', color='white', width=None, height=None):
        chars = Label._generate_chars(text, width, height, just)
        colors = copy_shape(chars, color)
        super().__init__(chars, colors)
        self.color = color
        # Bypassing setter, because I need to actually create fields
        self._just = just
        self._text = text
    
    @staticmethod
    def _generate_chars(text, width, height, just):
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
        r = [list(justify(x, width, just)) for x in lines]
        if height and len(r) < height:
            for x in range(height - len(r)):
                r.append([' ' for j in range(len(r[0]))])
        return r

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, value):
        if not self._text:
            self._text = value
        chars = copy_shape(self.chars, ' ')
        self.chars = blit(chars, self._generate_chars(value,
                                                      len(self.chars[0]),
                                                      len(self.chars),
                                                      self.just),
                          0, 0)
        self._text = value
        # MousePosWidgets (a child of Label) may have self.terminal set
        # despite not being connected to the terminal directly
        if self.terminal and self in self.terminal._widget_pointers:
            self.terminal.update_widget(self)

    @property
    def just(self):
        return self._just
    
    @just.setter
    def just(self, value):
        self.chars = Label._generate_chars(self.text, len(self.chars[0]),
                                           len(self.chars), just=value)
        if self.terminal:
            self.terminal.update_widget(self)
            
            
class InputField(Label):
    """
    A single-line field for keyboard input.
    
    The length of the input line is limited by the InputField size. When the
    input is finished (by pressing ENTER), InputField emits a
    `BearEvent(event_type='text_input', event_value=(field.name, field.text))`
    Since BLT has no support for system keyboard layouts, only supports Latin.
    This also applies to non-letter symbols: for example, comma and period are
    considered to be on different keys even in Russian layout, where they are
    on the same one.
    """
    charcodes = {'SPACE': ' ', 'MINUS': '-', 'EQUALS': '=',
                 'LBRACKET': '[', 'RBRACKET': ']', 'BACKSLASH': '\\',
                 'SEMICOLON': ';', 'APOSTROPHE': '\'', 'GRAVE': '`',
                 'COMMA': ',', 'PERIOD': '.', 'SLASH': '/',
                 'KP_DIVIDE': '/', 'KP_MULTIPLY': '*', 'KP_MINUS': '-',
                 'KP_PLUS': '+', 'KP_1': '1', 'KP_2': '2', 'KP_3': '3',
                 'KP_4': '4', 'KP_5': '5', 'KP_6': 6, 'KP_7': 7,
                 'KP_8': 8, 'KP_9': 9, 'KP_0': 0, 'KP_PERIOD': '.'
                 }
    
    # Charcodes for non-letter characters used via Shift button
    shift_charcodes = {'MINUS': '_', 'EQUALS': '+', 'LBRACKET': '{',
                       'RBRACKET': '}', 'BACKSLASH': '|', 'SEMICOLON': ':',
                       'APOSTROPHE': '\"', 'GRAVE': '~', 'COMMA': '<',
                       'PERIOD': '>', 'SLASH': '?', '1': '!', '2': '@',
                       '3': '#', '4': '$', '5': '%', '6': '^', '7': '&',
                       '8': '*', '9': '(', '0': ')'}
    
    def __init__(self, name='Input field', accept_input=True, **kwargs):
        if 'width' not in kwargs:
            raise BearException('InputField cannot be created without ' +
                                'either `width` or default text')
        super().__init__('', **kwargs)
        # The name will be used when the input is finished
        self.name = name
        self.shift_pressed = False
        # Set to True to return 'text_input' and
        self.finishing = False
        self.accept_input = accept_input
        
    def on_event(self, event):
        #TODO Reactivate InputField on mouse click, if inactive
        # Requires it to have terminal for state.
        if self.finishing:
            # If finishing, the event will be ignored
            return BearEvent(event_type='text_input',
                             event_value=(self.name, self.text))
        if self.accept_input and event.event_type == 'key_down':
            # Stripping 'TK_' part
            symbol = event.event_value[3:]
            # Todo: skip the non-\w keys
            if symbol == 'BACKSPACE':
                self.text = self.text[:-1]
            elif symbol == 'SHIFT':
                self.shift_pressed = True
            # TK_ENTER is presumed to be the end of input
            elif symbol == 'ENTER':
                self.accept_input = False
                # returns immediately, unlike self.finish which sets it to
                # return on the *next* event
                return BearEvent(event_type='text_input',
                                 event_value=(self.name, self.text))
            elif len(self.text) < len(self.chars[0]):
                self.text += self._get_char(symbol)
            if self.terminal:
                self.terminal.update_widget(self)
        elif event.event_type == 'key_up':
            if event.event_value == 'TK_SHIFT':
                self.shift_pressed = False

    def finish(self):
        """
        Finish accepting the input and emit the 'text_input' event at the next
        opportunity.
        
        The event will not be actually emitted until the next event is passed
        to on_event.
        :return:
        """
        self.accept_input = False
        self.finishing = True
        
    def _get_char(self, symbol):
        """
        Return the char corresponding to a TK_* code.
        
        Considers the shift state
        :param symbol:
        :return:
        """
        if len(symbol) == 1:
            if self.shift_pressed:
                if symbol in '1234567890':
                    return self.shift_charcodes[symbol]
                else:
                    return symbol
            else:
                return symbol.lower()
        elif symbol in self.charcodes:
            if self.shift_pressed and symbol in self.shift_charcodes:
                return self.shift_charcodes[symbol]
            else:
                return self.charcodes[symbol]
        else:
            return ''


class FPSCounter(Label):
    """
    A simple widget that measures FPS.
    Actually just prints 1/(average runtime over the last 100 ticks in seconds),
    so it takes 100 ticks to get an accurate reading. Not relevant except on the
    first several seconds of the program run or after FPS has changed, but if it
    seems like the game takes a second or two to reach the target FPS -- it just
    seems that way.
    """
    def __init__(self, **kwargs):
        self.samples_deque = deque(maxlen=100)
        super().__init__('030', **kwargs)
    
    def _update_self(self):
        fps = str(round(len(self.samples_deque) /
                            sum(self.samples_deque)))
        fps = fps.rjust(3, '0')
        self.text = fps
    
    def on_event(self, event):
        # Update FPS estimate
        if event.event_type == 'tick':
            self.samples_deque.append(event.event_value)
            self._update_self()
            if self.parent is self.terminal:
                self.terminal.update_widget(self)


class MousePosWidget(Label):
    """
    A simple widget akin to FPSCounter that listens to TK_MOUSE_MOVE events.
    
    In order to work, it needs `self.terminal` to be set to the current
    terminal, which means it should either be added to the terminal directly
    (without any Layouts) or it should be set manually before MousePosWidget
    gets its first `tick` event.
    """
    
    def __init__(self, **kwargs):
        super().__init__(text='000x000', **kwargs)
        
    def on_event(self, event):
        if event.event_type == 'misc_input' and \
                     event.event_value == 'TK_MOUSE_MOVE':
            self.text = self.get_mouse_line()
        if isinstance(self.parent, BearTerminal):
            self.terminal.update_widget(self)

    def get_mouse_line(self):
        if not self.terminal:
            print(self.parent, self.terminal)
            raise BearException('MousePosWidget is not connected to a terminal')
        x = str(self.terminal.check_state('TK_MOUSE_X')).rjust(3, '0')
        y = str(self.terminal.check_state('TK_MOUSE_Y')).rjust(3, '0')
        return x + 'x' + y
  
    
# Listeners
class Listener:
    """
    A base class for the things that need to interact with the queue (and maybe
    the terminal), but aren't widgets.
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


class LoggingListener(Listener):
    """
    A listener that logs the events it accepts
    """
    def __init__(self, handle):
        super().__init__()
        if not hasattr(handle, 'write'):
            raise BearException('The LoggingListener needs a writable object')
        self.handle = handle
        
    def on_event(self, event):
        self.handle.write('{0}: type {1}, '.format(str(time()), event.event_type) +
                          'value {}\n'.format(event.event_value))
