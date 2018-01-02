#  Widget and Listener classes

from bear_hug import BearTerminal
from bear_utilities import shapes_equal, copy_shape, BearException
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
