"""
Various useful Widget and Listener classes
These widgets and listeners are usable outside the ECS and should be sufficient
for simpler games and apps. However, for the sake of clearer architecture,
entities are recommended.
"""


import inspect

from bear_hug.bear_hug import BearTerminal
from bear_hug.bear_utilities import shapes_equal, blit, copy_shape,\
    slice_nested, generate_box, \
    BearException, BearLayoutException, BearJSONException
from bear_hug.event import BearEvent

from collections import deque
from json import dumps, loads
from time import time


def deserialize_widget(serial, atlas=None):
    """
    Provided a JSON string, return a widget it encodes.

    Specifics of JSON format are described in the Widget class documentation.
    It is important to know, though, that the Widget subclass that a given JSON
    encodes should be imported to the code that attempts to call this function.

    :param serial: a JSON string or dict
    :returns: a Widget instance
    """

    if isinstance(serial, str):
        d = loads(serial)
    elif isinstance(serial, dict):
        d = serial
    else:
        raise BearJSONException(f'Attempting to deserialize {type(serial)} to Widget')
    for forbidden_key in ('name', 'owner', 'dispatcher'):
        if forbidden_key in d.keys():
            raise BearJSONException(f'Forbidden key {forbidden_key} in widget JSON')
    if 'class' not in d:
        raise BearJSONException('No class provided in component JSON')
    # Only builtins supported for converters. Although custom converters could
    # be provided like with classes, IMO this way is safer
    converters = {}
    for key in d:
        if '_type' in key:
            converters[key[:-5]] = globals()['__builtins__'][d[key]]
    types = [x for x in d if '_type' in x]
    for t in types:
        del(d[t])
    # Try to get the Widget subclass from where the function was imported, or
    # the importers of *that* frame. Without this, the function would only see
    # classes from this very file, or ones imported into it, and that would
    # break the deserialization of custom components.
    class_var = None
    for frame in inspect.getouterframes(inspect.currentframe()):
        if d['class'] in frame.frame.f_globals:
            class_var = frame.frame.f_globals[d['class']]
            break
    del frame
    if not class_var:
        raise BearJSONException(f"Class name {d['class']} not imported anywhere in frame stack")
    if not issubclass(class_var, Widget):
        raise BearJSONException(f"Class name {d['class']}mapped to something other than a Widget subclass")
    kwargs = {}
    for key in d:
        if key in {'class', 'chars', 'colors'}:
            continue
        elif key in converters:
            kwargs[key] = converters[key](d[key])
        elif key == 'animation':
            # animation deserializer will raise exception if atlas is not supplied
            kwargs['animation'] = deserialize_animation(d['animation'], atlas)
        else:
            kwargs[key] = d[key]
    if 'chars' in d:
        # Chars and colors are not kwargs
        return class_var(chars=[[char for char in x] for x in d['chars']],
                         colors=[x.split(',') for x in d['colors']],
                         **kwargs)
    else:
        # Some classes, eg animation widgets, do not dump chars and colors
        return class_var(**kwargs)


def deserialize_animation(serial, atlas=None):
    """

    Deserialize an animation from a JSON dump

    :param serial: A JSON string or a dict.

    :returns: an Animation instance.
    """
    d = loads(serial)
    if d['storage_type'] == 'atlas':
        if not atlas:
            raise BearJSONException('Animation storage type set to atlas, but atlas was not supplied')
        return Animation(frames=[atlas.get_element(x) for x in d['frame_ids']],
                         fps=d['fps'])
    elif d['storage_type'] == 'dump':
        return Animation(frames=[[[[char for char in x] for x in frame[0]],
                                  [x.split(',') for x in frame[1]]]
                                 for frame in d['frames']],
                         fps=d['fps'])
    else:
        raise BearJSONException(f"Incorrect Animation storage_type: {d['storage_type']}")


class Widget:
    """
    The base class for things that can be placed on the terminal.

    This class is inactive and is intended to be either inherited from or used
    for non-interactive non-animated objects. Event processing and animations
    are covered by its subclasses; while it has ``on_event()`` method, it does
    nothing. This allows Widgets to work without subscribing to the queue and
    saves some work on not redrawing them unless the Widget itself considers it
    necessary.

    Under the hood, this class does little more than store two 2-nested lists of
    ``chars`` and ``colors`` (for characters that comprise the image and their
    colors). These two should be exactly the same shape, otherwise a
    ``BearException`` is raised.
    
    Widgets can be serialized into JSON similarly to Components and Entities.
    `repr(widget)` is used for serialization and should generate a valid
    JSON-encoded dict. It should always include a ``class`` key which
    should equal the class name for that component and will be used by a
    deserializer to determine what to create. ``chars`` and ``colors` keys are
    also necessary. They should encode widget's chars and colors as arrays of
    strings and each of these strings should be a list of values for
    chars' and colors' inner lists (str-converted chars and str-converted
    `#ffffff`-type colors; comma-separated for colors).
    
    All other keys will be deserialized and treated as kwargs to a newly-created
    object. To define the deserialization protocol, JSON dict may also contain
    keys formatted as ``{kwarg_name}_type``'`` which should be a string and will
    be eval-ed during deserialization. Only Python's builtin converters (eg
    ``str``, ``int`` or ``float``) are safe; custom ones are currently
    unsupported.

    For example, the following is a valid JSON::

        {"class": "MyWidget",
        "chars": ["b,b,b", "a,b,a", "b,a,b"],
        "colors": ["#fff,#fff,#fff", "#000,#fff,#000", "#fff,#000,#fff"],
        "former_owners": ["asd", "zxc", "qwe"],
        "former_owners_type": "set"}

    Its deserialization is equivalent to the following call::

        x = MyWidget(chars=[['bbb'],
                            ['aba'],
                            ['bab']],
                     colors=[['#fff','#fff','#fff'],
                             ['#000','#fff','#000'],
                             ['#fff','#000','#fff']],
                     former_owners=set(['asd, 'zxc', 'qwe']))

    The following keys are forbidden: ``parent`` and ``terminal``. Kwarg
    validity is not controlled except by ``WidgetSubclass.__init__()``.

    :param chars: a 2-nested list of unicode characters

    :param colors: a 2-nested list of colors. Anything that is accepted by ``terminal.color()`` goes here (a color name or a 0xAARRGGBB/0xRRGGBB/0xRGB/0xARGB integer are fine, (r, g, b) tuples are unreliable).

    :param z_level: a Z-level to determine objects' overlap. Used by (Scrollable)ECSLayout. Not to be mixed up with a terminal layer, these are two independent systems.
    """
    #TODO: maybe support background colour after all?
    
    def __init__(self, chars, colors, z_level=0):
        if not isinstance(chars, list) or not isinstance(colors, list):
            raise BearException('Chars and colors should be lists')
        if not shapes_equal(chars, colors):
            raise BearException('Chars and colors should have the same shape')
        self.z_level = z_level
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
        
    @property
    def height(self):
        return len(self.chars)
    
    @property
    def width(self):
        return len(self.chars[0])
    
    @property
    def size(self):
        return len(self.chars[0]), len(self.chars)
        
    def flip(self, axis):
        """
        Flip a widget along one of the axes.
        
        Note that this method has **extremely** limited uses: first, it only
        affects chars and colors *as they are now*. If later the widget gets
        updated via animation, updating label text, Layout's children being
        redrawn, etc., it will be un-flipped again.

        Second, most ASCII-art just doesn't take it well. Unlike raster and
        vector graphics, there is no general way to flip an ASCII image
        programmatically (except, of course, flipping chars themselves which I
        find aesthetically unacceptable for my projects). It may work for random
        noisy tiles, like littered floors, grass and such, but for complex
        images it's better to provide both left and right versions.
        
        :param axis: An axis along which to flip. Either one of {'x', 'horizontal'} or one of {'y', 'vertical'}
        :return:
        """
        if axis in ('x', 'horizontal'):
            self.chars = [self.chars[x][::-1] for x in range(len(self.chars))]
            self.colors = [self.colors[x][::-1] for x in range(len(self.colors))]
        elif axis in ('y', 'vertical'):
            self.chars = self.chars[::-1]
            self.colors = self.colors[::-1]
            
    def __repr__(self):
        char_strings = [''.join(x) for x in self.chars]
        for string in char_strings:
            string.replace('\"', '\u0022"').replace('\\', '\u005c')
        d = {'class': self.__class__.__name__,
             'chars': char_strings,
             'colors': [','.join(x) for x in self.colors]}
        return dumps(d)


class SwitchingWidget(Widget):
    """
    A widget that can contain a collection of chars/colors pairs and switch
    them on command.

    These char/color pairs should all be the same shape. Does not do any
    transition animations.

    ``chars`` and ``colors`` args, although accepted during creation, are
    discarded. They do not affect the created widget in any way, nor are they
    shown at any moment.

    :param images_dict: a dict of {image_id: (chars, colors)}
    :param initial_image: an ID of the first image to show. Should be a key in ``images_dict``.
    """
    
    def __init__(self, chars=None, colors=None, images_dict=None, initial_image=None):
        # Chars and colors are not used anywhere; they are included simply for
        # the compatibility with serialization. Actual chars and colors of the
        # SwitchingWidget are set to `images_dict[initial_image]` upon creation
        test_shape = None
        for image in images_dict:
            # Checking if the image is from JSON (each line is a string) or a
            # correct list-of-lists. If it's former, converts
            if isinstance(images_dict[image][0][0], str):
                images_dict[image][0] = [[char for char in x]
                                         for x in images_dict[image][0]]
                images_dict[image][1] = [list(x.split(','))
                                         for x in images_dict[image][1]]
            if not shapes_equal(images_dict[image][0], images_dict[image][1]):
                raise BearException(
                    f'Chars and colors of different shape for image ID {image} in SwitchingWidget')
            if not test_shape:
                test_shape = (len(images_dict[image][0]),
                              len(images_dict[image][0][0]))
            elif len(images_dict[image][0]) != test_shape[0] or \
                    len(images_dict[image][0][0]) != test_shape[1]:
                raise BearException(
                    f'Image {image} in SwitchingWidget has incorrect size')
        if not initial_image:
            raise BearException('Initial image not set for SwitchingWidget')
        super().__init__(*images_dict[initial_image])
        self.images = images_dict
        self.current_image = initial_image
    
    def switch_to_image(self, image_id):
        """
        Switch to a given image ID

        The ID should be a key in the original ``image_dict``. Otherwise,
        BearException is raised.

        :param image_id: image ID, str.
        """
        if image_id != self.current_image:
            try:
                self.chars = self.images[image_id][0]
                self.colors = self.images[image_id][1]
                self.current_image = image_id
            except KeyError:
                raise BearException(
                    f'Attempting to switch to incorrect image ID {image_id}')
            
    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'initial_image': self.current_image}
        images = {}
        for image in self.images:
            images[image] = []
            # Seems to work without any complex workarounds for screening
            images[image].append([''.join(x)#.replace('"', '\u0022"').
                                            # replace('\\', '\u005c')
                                  for x in self.images[image][0]])
            images[image].append([','.join(x) for x in self.images[image][1]])
        d['images_dict'] = images
        return dumps(d)
        
        
class Layout(Widget):
    """
    A widget that can add others as its children.

    All children get drawn to its chars and colors, and are thus displayed
    within a single bearlibterminal layer. Therefore, if children overlap each
    other, the lower one is hidden completely. In the resolution of who covers
    whom, a newer child always wins. The layout does not explicitly pass events
    to its children, they are expected to subscribe to event queue by
    themselves.

    The Layout is initialized with a single child, which is given chars and
    colors provided at Layout creation. This child is available as
    ``l.children[0]`` or as ``l.background``. Its type is always ``Widget``.

    The Layout automatically redraws itself on `tick` event, whether its
    children have updated or not.
    
    Does not support JSON serialization

    :param chars: chars for layout BG.

    :param colors: colors for layout BG.
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
        self.need_redraw = False
    
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
        Add a widget as a child at a given position.

        The child has to be a Widget or a Widget subclass that haven't yet been
        added to this Layout and whose dimensions are less than or equal to the
        Layout's. The position is in the Layout coordinates, ie relative to its
        top left corner.

        :param child: A widget to add.

        :param pos: A widget position, (x, y) 2-tuple
        """
        if not isinstance(child, Widget):
            raise BearLayoutException('Cannot add non-Widget to a Layout')
        if child in self.children and not skip_checks:
            raise BearLayoutException('Cannot add the same widget to layout twice')
        if len(child.chars) > len(self._child_pointers) or \
                len(child.chars[0]) > len(self._child_pointers[0]):
            raise BearLayoutException('Cannot add child that is bigger than a Layout')
        if len(child.chars) + pos[1] > len(self._child_pointers) or \
                len(child.chars[0]) + pos[0] > len(self._child_pointers[0]):
            raise BearLayoutException('Child won\'t fit at this position')
        if child is self:
            raise BearLayoutException('Cannot add Layout as its own child')
        if not skip_checks:
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
        used and is included only to prevent ``self.move_child`` from messing
        with child order.
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
        """
        Remove the child and add it at a new position.

        :param child: A child Widget

        :param new_pos: An (x, y) 2-tuple within the layout.
        """
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
        """
        # TODO: Support needs_redraw like in ECSLayout
        chars = copy_shape(self.chars, ' ')
        colors = copy_shape(self.colors, None)
        for line in range(len(chars)):
            for char in range(len(chars[0])):
                highest_z = 0
                col = None
                c = ' '
                for child in self._child_pointers[line][char][::]:
                    # Select char and color from lowest widget (one with max y
                    # for bottom).
                    # If two widgets are equally low, pick newer one
                    if child.z_level >= highest_z:
                        tmp_c = child.chars \
                            [line - self.child_locations[child][1]] \
                            [char - self.child_locations[child][0]]
                        if c != ' ' and tmp_c == ' ':
                            continue
                        else:
                            highest_z = child.z_level
                            c = tmp_c
                            col = child.colors \
                                [line - self.child_locations[child][1]] \
                                [char - self.child_locations[child][0]]
                chars[line][char] = c
                colors[line][char] = col
        self.chars = chars
        self.colors = colors
    
    def on_event(self, event):
        """
        Redraw itself on every tick
        """
        if event.event_type == 'service' and event.event_value == 'tick_over':
            self._rebuild_self()
            if isinstance(self.parent, BearTerminal):
                self.terminal.update_widget(self)
    
    #Service
    def get_absolute_pos(self, relative_pos):
        """
        Get an absolute position (in terminal coordinates) for any location
        within self.

        :param relative_pos: An (x, y) 2-tuple in Layout coordinates

        :return: An (x, y) 2-tuple for the same point in terminal coordinates.
        """
        self_pos = self.terminal.widget_locations(self).pos
        return self_pos[0]+relative_pos[0], self_pos[1]+relative_pos[1]

    def get_child_on_pos(self, pos, return_bg=False):
        """
        Return the newest child on a given position.

        :param pos: Position in Layout coordinates

        :param return_bg: If True, return background widget when clicking outside any children. If False, return None in this case. Defaults to False

        :return: Widget instance or None
        """
        if len(self._child_pointers[pos[1]][pos[0]]) > 1:
            return self._child_pointers[pos[1]][pos[0]][-1]
        if return_bg:
            return self.background
        else:
            return None

    def __repr__(self):
        raise BearException('Layout does not support __repr__ serialization')


class ScrollBar(Widget):
    """
    A scrollbar to be used with ScrollableLayout.

    Does not accept input, does not support serialization.

    :param orientation: Scrolling direction. One of 'vertical' or 'horizontal'

    :param length: Scrollbar length, in chars.

    :param colors: A 2-tuple of (BG colour, moving thingy colour)
    """
    def __init__(self, orientation='vertical', length=10,
                 colors=('gray', 'white')):
        if orientation not in ('vertical', 'horizontal'):
            raise BearException(
                'Orientation must be either vertical or horizontal')
        if orientation == 'vertical':
            # TODO: custom chars in ScrollBar
            chars = [['#'] for _ in range(length)]
        else:
            chars = [['#' for _ in range(length)]]
        self.length = length
        self.orientation = orientation
        self.bg_color = colors[0]
        self.bar_color = colors[1]
        colors = copy_shape(chars, self.bg_color)
        super().__init__(chars, colors)
        
    def show_pos(self, position, percentage):
        """
        Move the scrollbar.

        :param position: Float. The position of the top (or left) side of the
        scrollbar, as part of its length

        :param percentage: Float. The lengths of the scrollbar, as part of the
        total bar length
        """
        # Not really effective, but still quicker than Layout would be
        # Single-widget bar gets redrawn only when called, while a Layout
        # would've redrawn every tick
        start = round(self.length*position)
        width = round(self.length*percentage)
        self.colors = copy_shape(self.chars, self.bg_color)
        if self.orientation == 'vertical':
            for i in range(start, start+width):
                self.colors[i][0] = self.bar_color
        else:
            for i in range(start, start+width):
                self.colors[0][i] = self.bar_color
                
    def __repr__(self):
        raise BearException('ScrollBar does not support __repr__ serialization')


class ScrollableLayout(Layout):
    """
    A Layout that can show only a part of its surface.
    
    Like a Layout, accepts `chars` and `colors` on creation, which should be the
    size of the entire layout, not the visible area. The latter is initialized
    by `view_pos` and `view_size` arguments.
    
    Does not support JSON serialization.

    :param chars: Layout BG chars.

    :param colors: Layout BG colors.

    :param view_pos: a 2-tuple (x,y) for the top left corner of visible area, in Layout coordinates.

    :param view_size: a 2-tuple (width, height) for the size of visible area.
    """
    def __init__(self, chars, colors,
                 view_pos=(0, 0), view_size=(10, 10)):
        super().__init__(chars, colors)
        if not 0 <= view_pos[0] <= self.width - view_size[0] \
                or not 0 <= view_pos[1] <= self.height - view_size[1]:
            raise BearLayoutException('Initial viewpoint outside ' +
                                      'ScrollableLayout')
        if not 0 < view_size[0] <= len(chars[0]) \
                or not 0 < view_size[1] <= len(chars):
            raise BearLayoutException('Invalid view field size')
        self.view_pos = view_pos[:]
        self.view_size = view_size[:]
        self._rebuild_self()
    
    def _rebuild_self(self):
        """
        Same as `Layout()._rebuild_self`, but all child positions are also
        offset by `view_pos`. Obviously, only `view_size[1]` lines
        `view_size[0]` long are set as `chars` and `colors`.
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
        Move field of view to ``pos``.
        
        Raises ``BearLayoutException`` on incorrect position

        :param pos: A 2-tuple of (x, y) in layout coordinates
        """
        if not (len(pos) == 2 and all((isinstance(x, int) for x in pos))):
            raise BearLayoutException('Field of view position should be 2 ints')
        if not 0 <= pos[0] <= len(self._child_pointers[0]) - self.view_size[0] \
                or not 0 <= pos[1] <= len(self._child_pointers)-self.view_size[1]:
            raise BearLayoutException('Scrolling to invalid position')
        self.view_pos = pos
    
    def scroll_by(self, shift):
        """
        Move field of view by ``shift[0]`` to the right and by ``shift[1]`` down.
        
        Raises ``BearLayoutException`` on incorrect position

        :param shift: A 2-tuple of (dx, dy) in layout coordinates
        """
        pos = (self.view_pos[0] + shift[0], self.view_pos[1] + shift[1])
        self.scroll_to(pos)
    
    def __repr__(self):
        raise BearException('ScrollableLayout does not support __repr__ serialization')
    

class InputScrollable(Layout):
    """
    A ScrollableLayout wrapper that accepts input events and supports the usual
    scrollable view bells and whistles. Like ScrollableLayout, accepts chars and
    colors the size of the *entire* layout and inits visible area using view_pos
    and view_size.
    
    If bottom_bar and/or right_bar is set to True, it will be made one char
    bigger than view_size in the corresponding dimension to add ScrollBar.
    
    Can be scrolled by arrow keys.
    
    Does not support JSON serialization
    """
    def __init__(self, chars, colors, view_pos=(0, 0), view_size=(10, 10),
                 bottom_bar=False, right_bar=False):
        # Scrollable is initalized before self to avoid damaging it by the
        # modified view_size (in case of scrollbars)
        scrollable = ScrollableLayout(chars, colors, view_pos, view_size)
        size = list(view_size)
        ch = slice_nested(chars, view_pos, size)
        co = slice_nested(colors, view_pos, size)
        # Is there something more reasonable to add as ScrollableLayout BG?
        # It shouldn't be shown anyway
        if bottom_bar:
            ch.append(copy_shape(ch[0], ch[0][0]))
            co.append(copy_shape(co[0], co[0][0]))
        if right_bar:
            for x in ch:
                x.append(' ')
            for x in co:
                x.append('white')
        # While True, can add children to self. Otherwise they are passed to
        # self.scrollable
        self.building_self = True
        super().__init__(ch, co)
        self.scrollable = scrollable
        self.add_child(self.scrollable, pos=(0, 0))
        # Need to rebuild now to let bars know the correct height and width
        self._rebuild_self()
        if right_bar:
            self.right_bar = ScrollBar(orientation='vertical',
                                       length=self.height)
            self.add_child(self.right_bar, pos=(self.width-1, 0))
        else:
            self.right_bar = None
        if bottom_bar:
            self.bottom_bar = ScrollBar(orientation='horizontal',
                                        length=self.width)
            self.add_child(self.bottom_bar, pos=(0, self.height-1))
        self.building_self = False
        
    def on_event(self, event):
        if event.event_type == 'key_down':
            scrolled = False
            if event.event_value == 'TK_DOWN' and \
              self.scrollable.view_pos[1] + self.scrollable.view_size[1]\
                    < len(self.scrollable._child_pointers):
                self.scrollable.scroll_by((0, 1))
                scrolled = True
            elif event.event_value == 'TK_UP' and \
             self.scrollable.view_pos[1] > 0:
                self.scrollable.scroll_by((0, -1))
                scrolled = True
            elif event.event_value == 'TK_RIGHT' and \
              self.scrollable.view_pos[0] + self.scrollable.view_size[0]\
                    < len(self.scrollable._child_pointers[0]):
                self.scrollable.scroll_by((1, 0))
                scrolled = True
            elif event.event_value == 'TK_LEFT' and \
              self.scrollable.view_pos[0] > 0:
                self.scrollable.scroll_by((-1, 0))
                scrolled = True
            elif event.event_type == 'TK_SPACE':
                self.scrollable.scroll_to((0, 0))
                scrolled = True
            if scrolled:
                if self.right_bar:
                    self.right_bar.show_pos(
                        self.scrollable.view_pos[1] /
                            len(self.scrollable._child_pointers),
                        self.scrollable.view_size[0] /
                            len(self.scrollable._child_pointers))
        super().on_event(event)

    def add_child(self, child, pos, skip_checks=False):
        if not self.building_self:
            self.scrollable.add_child(child, pos, skip_checks)
        else:
            super().add_child(child, pos, skip_checks)
            
    def __repr__(self):
        raise BearException('InputScrollable does not support __repr__ serialization')
            

# Animations and other complex decorative Widgets
class Animation:
    """
    A data class for animation, *ie* the sequence of the frames
    
    Animation can be serialized to JSON, preserving fps and either frame dumps
    (similarly to widget chars and colors) or frame image IDs. For the latter to
    work, these IDs should be provided during Animation creation via an optional
    ``frame_ids`` kwarg. The deserializer will then use them with whichever atlas
    is supplied to create the animation.
    
    Since this class has no idea of atlases and is unaware whether it was
    created with the same atlas as deserializer will use (which REALLY should be
    the same, doing otherwise is just asking for trouble), frame ID validity is
    not checked until deserialization and, if incorrect, are not guaranteed to
    work.

    :param frames: a list of (chars, colors) tuples

    :param fps: animation speed, in frames per second. If higher than terminal FPS, animation will be shown at terminal FPS.

    :param frame_ids: an optional list of frame names in atlas, to avoid dumping frames. Raises ``BearJSONException`` if its length isn't equal to that of frames.
    """
    def __init__(self, frames, fps, frame_ids=None):
        if not all((shapes_equal(x[0], frames[0][0]) for x in frames[1:])) \
                or not all(
                (shapes_equal(x[1], frames[0][1]) for x in frames[1:])):
            raise BearException('Frames should be equal size')
        if frame_ids:
            if len(frame_ids) != len(frames):
                raise BearJSONException('Incorrect frame_ids length during Animation creation')
            else:
                self.frame_ids = frame_ids
        self.frames = frames
        self.fps = fps # For deserialization
        self.frame_time = 1 / fps

    def __len__(self):
        return len(self.frames)
    
    def __repr__(self):
        d = {'fps': self.fps}
        if hasattr(self, 'frame_ids'):
            d['storage_type'] = 'atlas'
            d['frame_ids'] = 'frame_ids'
        else:
            frames_dump = []
            for frame in self.frames:
                char_strings = [''.join(x) for x in frame[0]]
                for string in char_strings:
                    string.replace('\"', '\u0022"').replace('\\', '\u005c')
                colors_dump = [','.join(x) for x in frame[1]]
                frames_dump.append([char_strings, colors_dump])
            d['frames'] = frames_dump
            d['storage_type'] = 'dump'
        return dumps(d)
        

class SimpleAnimationWidget(Widget):
    """
    A simple animated widget that cycles through the frames.

    :param frames: An iterable of (chars, colors) tuples. These should all be the same size.

    :param fps: Animation speed, in frames per second. If higher than terminal FPS, it will be slowed down.

    :param emit_ecs: If True, emit ecs_update events on every frame. Useless for widgets outside ECS, but those on ``ECSLayout`` are not redrawn unless this event is emitted or something else causes ECSLayout to redraw.
    """
    
    def __init__(self, animation, *args, emit_ecs=True, **kwargs):
        if not isinstance(animation, Animation):
            raise BearException(
                'Only Animation instance can be used in SimpleAnimationWidget')
        self.animation = animation
        super().__init__(*animation.frames[0], *args, **kwargs)
        self.running_index = 0
        self.have_waited = 0
        self.emit_ecs = emit_ecs
    
    def on_event(self, event):
        if event.event_type == 'tick':
            self.have_waited += event.event_value
            if self.have_waited >= self.animation.frame_time:
                self.running_index += 1
                if self.running_index >= len(self.animation):
                    self.running_index = 0
                self.chars = self.animation.frames[self.running_index][0]
                self.colors = self.animation.frames[self.running_index][1]
                self.have_waited = 0
                if self.emit_ecs:
                    return BearEvent(event_type='ecs_update')
        elif self.parent is self.terminal and event.event_type == 'service' \
                and event.event_value == 'tick_over':
            # This widget is connected to the terminal directly and must update
            # itself without a layout
            self.terminal.update_widget(self)

    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'animation': repr(self.animation),
             'emit_ecs': self.emit_ecs}
        return dumps(d)


class MultipleAnimationWidget(Widget):
    """
    A widget that is able to display multiple animations.

    Plays only one of the animations, unless ordered to change it by
    ``self.set_animation()``

    :param animations: A dict of ``{animation_id: Animation()}``

    :param initial_animation: the animation to start from.

    :param emit_ecs: If True, emit ecs_update events on every frame. Useless for widgets outside ECS, but those on ``ECSLayout`` are not redrawn unless this event is emitted or something else causes the layout to redraw.

    :param cycle: if True, cycles the animation indefinitely. Otherwise stops at the last frame.
    """
    def __init__(self, animations, initial_animation,
                 emit_ecs=True, cycle=False):
        # Check the animations' validity
        if not isinstance(animations, dict) or \
                any((not isinstance(x, Animation) for x in animations.values())):
            raise BearException(
                'Only dict of Animations acceptable for MultipleAnimationWidget')
        if any((not isinstance(x, str) for x in animations)):
            raise BearException('Animation names should be strings')
        if not initial_animation:
            raise BearException('Initial animation ID should be provided')
        if initial_animation not in animations:
            raise BearException('Incorrect initial animation ID')
        super().__init__(*animations[initial_animation].frames[0])
        self.animations = animations
        self.current_animation = initial_animation
        self.running_index = 0
        self.have_waited = 0
        self.emit_ecs = emit_ecs
        self.cycle = cycle
        self.am_running = True

    def on_event(self, event):
        # When self.am_running is False, this widget does not respond to any
        # events and acts like a regular passive Widget
        if self.am_running:
            if event.event_type == 'tick':
                self.have_waited += event.event_value
                if self.have_waited >= self.animation.frame_time:
                    self.running_index += 1
                    if self.running_index >= len(self.animation):
                        if self.cycle:
                            self.running_index = 0
                        else:
                            self.am_running = False
                    self.chars = self.animation.frames[self.running_index][0]
                    self.colors = self.animation.frames[self.running_index][1]
                    self.have_waited = 0
                    if self.emit_ecs:
                        return BearEvent(event_type='ecs_update')
            elif self.parent is self.terminal and event.event_type == 'service'\
                    and event.event_value == 'tick_over':
                # This widget is connected to the terminal directly and must
                # update itself without a layout
                self.terminal.update_widget(self)

    @property
    def animation(self):
        return self.animations[self.current_animation]

    def set_animation(self, anim_id, cycle=False):
        """
        Set the next animation to be played.

        :param anim_id: Animation ID. Should be present in self.animations

        :param cycle: Whether to cycle the animation. Default False.
        """
        if anim_id not in self.animations:
            raise BearException('Incorrect animation ID')
        self.current_animation = anim_id
        self.cycle = cycle
        self.am_running = True
        
    def __repr__(self):
        d = {'class': self.__class__.__name__,
             'animations': {x: repr(self.animations[x])
                            for x in self.animations},
             # Start from whichever animation was displayed during saving
             'initial_animation': self.current_animation,
             'emit_ecs': self.emit_ecs,
             'cycle': self.cycle}
        return dumps(d)


# Functional widgets. Please note that these include no decoration, BG, frame or
# anything else. Ie Label is just a chunk of text on the screen, FPSCounter and
# MousePosWidget are just the numbers that change. For the more complex visuals,
# embed these into a Layout with a preferred BG

class Label(Widget):
    """
    A widget that displays text.

    Accepts only a single string, whether single- or multiline (ie containing
    ``\n`` or not). Does not support any complex text markup. Label's text can be
    edited at any time by setting label.text property. Note that it overwrites
    any changes to ``self.chars`` and ``self.colors`` made after setting
    ``self.text`` the last time.

    Unlike text, Label's height and width cannot be changed. Set these to
    accomodate all possible inputs during Label creation. If a text is too big
    to fit into the Label, ValueError is raised.

    :param text: string to be displayed

    :param just: horizontal text justification, one of 'left', 'right'
    or 'center'. Default 'left'.

    :param color: bearlibterminal-compatible color. Default 'white'

    :param width: text area width. Defaults to the length of the longest ``\n``-delimited substring in ``text``.

    :param height: text area height. Defaults to the line count in `text`
    """
    
    def __init__(self, text, chars=None, colors=None,
                 just='left', color='white', width=None, height=None, **kwargs):
        # TODO: add input delay to Label
        # If chars and colors are not provided, generate them. If they are,
        # typically from JSON dump, no checks are performed. Thus, in theory
        # it's possible to break this by providing overly big text and changing
        # adjustment.
        if not chars:
            chars = Label._generate_chars(text, width, height, just)
        if not colors:
            colors = copy_shape(chars, color)
        super().__init__(chars, colors, **kwargs)
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
        # Checking that text will fit in a label
        l = value.split('\n')
        if self.chars and (len(l) > len(self.chars) or
                           any(len(x) > len(self.chars[0])
                               for x in l)):
            raise ValueError('Text doesn\'t fit in a Label')
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
            
    def __repr__(self):
        d = loads(super().__repr__())
        d['text'] = self.text
        d['just'] = self.just
        d['color'] = self.color
        return dumps(d)
            
            
class InputField(Label):
    """
    A single-line field for keyboard input.
    
    The length of the input line is limited by the InputField size. When the
    input is finished (by pressing ENTER), InputField emits a
    ``BearEvent(event_type='text_input', event_value=(field.name, field.text))``

    Since BLT has no support for system keyboard layouts, only supports QWERTY
    Latin. This also applies to non-letter symbols: for example, comma and
    period are considered to be different keys even in Russian layout, where
    they are on the same physical key.
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
    
    def __init__(self, name='Input field', accept_input=True, finishing=False,
                 **kwargs):
        if 'width' not in kwargs:
            raise BearException('InputField cannot be created without ' +
                                'either `width` or default text')
        super().__init__('', **kwargs)
        # The name will be used when the input is finished
        self.name = name
        self.shift_pressed = False
        # Set to True to return 'text_input' and stop accepting
        self.finishing = finishing
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
        opportunity. This opportunity will not present itself until the next
        event is passed to ``self.on_event``.
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
        
    def __repr__(self):
        d = loads(super().__repr__())
        d['name'] = self.name
        d['finishing'] = self.finishing
        d['accept_input'] = self.accept_input
        return dumps(d)


class MenuWidget(Layout):
    """
    A menu widget that includes multiple buttons.

    :param dispatcher: BearEventDispatcher instance to which the menu will subscribe

    :param items: an iterable of MenuItems

    :param background: A background widget for the menu. If not supplied, a default double-thickness box is used. If background widget needs to get events (ie for animation), it should be subscribed by the time it's passed here.

    :param color: A bearlibterminal-compatible color. Used for a menu frame and header text

    :param items_pos: A 2-tuple of ints. A position of top-left corner of the 1st MenuItem

    :param header: str or None. A menu header. This should not be longer than menu width, otherwise an exception is thrown. Header may look ugly with custom backgrounds, since it's only intended for non-custom menus.
    """
    def __init__(self, dispatcher, terminal=None, items=[], header=None,
                 color='white', items_pos=(2, 2),
                 background=None, **kwargs):
        self.items = []
        # Separate from self.heigh and self.width to avoid overwriting attrs
        self.h = 3
        self.w = 4
        self.color = color
        for item in items:
            self._add_item(item)
        if terminal and not isinstance(terminal, BearTerminal):
            raise TypeError(f'{type(terminal)} used as a terminal for MenuWidget instead of BearTerminal')
        # Set background, if supplied
        if not background:
            bg_chars = generate_box((self.w, self.h), 'double')
            bg_colors = copy_shape(bg_chars, self.color)
            for y in range(len(bg_chars) - 2):
                for x in range(len(bg_chars[0]) - 2):
                    bg_chars[y + 1][x + 1] = '\u2588'
                    bg_colors[y + 1][x + 1] = 'black'
            super().__init__(bg_chars, bg_colors)
        else:
            if background.width < self.w or background.height < self.h:
                raise BearLayoutException('Background for MenuWidget is too small')
            # Creating tmp BG widget instead of just taking BG chars and colors
            # because the background could be some complex widget, eg animation
            bg_chars = [[' ' for x in range(background.width)]
                        for y in range(background.height)]
            bg_colors = copy_shape(bg_chars, 'black')
            super().__init__(bg_chars, bg_colors)
            self.background = background
        # Adding header, if any
        if header:
            if not isinstance(header, str):
                raise TypeError(f'{type(header)} used instead of string for MenuWidget header')
            if len(header) > self.width - 2:
                raise BearLayoutException(f'MenuWidget header is too long')
            header_label = Label(header, color=self.color)
            x = round((self.width - header_label.width) / 2)
            self.add_child(header_label, (x, 0))
        # Adding buttons
        current_height = items_pos[1]
        for item in self.items:
            self.add_child(item, (items_pos[0], current_height))
            current_height += item.height + 1
        # Prevent scrolling multiple times when key is pressed
        self.input_delay = 0.2
        self.current_delay = self.input_delay
        self._current_highlight = 0
        self.items[self.current_highlight].highlight()

    def _add_item(self, item):
        """
        Add an item to the menu.

        This method may only be called from ``__init__``; there is no support
        for changing menu contents on the fly

        :param item: MenuItem instance
        """
        if not isinstance(item, MenuItem):
            raise TypeError(f'{type(item)} used instead of MenuItem for MenuWidget')
        self.items.append(item)
        self.h += item.height + 1
        if item.width > self.w - 4:
            self.w = item.width + 4

    @property
    def current_highlight(self):
        return self._current_highlight

    @current_highlight.setter
    def current_highlight(self, value):
        if not 0 <= value <= len(self.items) - 1:
            raise ValueError('current_highlight can only be set to a valid item index')
        self.items[self._current_highlight].unhighlight()
        self._current_highlight = value
        self.items[self._current_highlight].highlight()

    def on_event(self, event):
        r = None
        if event.event_type == 'tick' and self.current_delay <= self.input_delay:
            self.current_delay += event.event_value
        elif event.event_type == 'key_down' and self.current_delay >= self.input_delay:
            self.current_delay = 0
            if event.event_value in ('TK_SPACE', 'TK_ENTER'):
                r  = self.items[self.current_highlight].activate()
            elif event.event_value in ('TK_UP', 'TK_W') \
                    and self.current_highlight > 0:
                self.current_highlight -= 1
            elif event.event_value in ('TK_DOWN', 'TK_S') \
                    and self.current_highlight < len(self.items) - 1:
                self.current_highlight += 1
            elif event.event_value == 'TK_MOUSE_LEFT':
                if self.terminal:
                    # Silently ignore mouse input if terminal is not set
                    mouse_x = self.terminal.check_state('TK_MOUSE_X')
                    mouse_y = self.terminal.check_state('TK_MOUSE_Y')
                    x, y = self.terminal.widget_locations[self].pos
                    if x <= mouse_x <= x + self.width and y <= mouse_y <= y + self.height:
                        b = self.get_child_on_pos((mouse_x - x, mouse_y -y))
                        # self.current_highlight = self.items.index(b)
                        if isinstance(b, MenuItem):
                            r = self.items[self.current_highlight].activate()
        elif event.event_type == 'misc_input' and event.event_value == 'TK_MOUSE_MOVE':
            if self.terminal:
                # Silently ignore mouse input if terminal is not set
                mouse_x = self.terminal.check_state('TK_MOUSE_X')
                mouse_y = self.terminal.check_state('TK_MOUSE_Y')
                x, y = self.terminal.widget_locations[self].pos
                if x <= mouse_x < x + self.width and y <= mouse_y < y + self.height:
                    b = self.get_child_on_pos((mouse_x - x, mouse_y - y))
                    # Could be the menu header
                    if isinstance(b, MenuItem):
                        self.current_highlight = self.items.index(b)
        # Whatever type r was, convert it into a (possibly empty) list of BearEvents
        ret = []
        if r:
            if isinstance(r, BearEvent):
                ret = [r]
            else:
                for e in r:
                    if isinstance(e, BearEvent):
                        ret.append(e)
                    else:
                        raise TypeError(f'MenuItem action returned {type(e)} instead of a BearEvent')
        else:
            ret = []
        s = super().on_event(event)
        if s:
            if isinstance(s, BearEvent):
                ret.append(s)
            else:
                for e in s:
                    if isinstance(e, BearEvent):
                        ret.append(e)
                    else:
                        raise TypeError(
                            f'Layout on_event returned {type(e)} instead of a BearEvent')
        return ret


class MenuItem(Layout):
    """
    A button for use inside menus. Includes a label surrounded by a single-width
    box. Contains a single callable, ``self.action``, which will be called when
    this button is activated.

    MenuItem by itself does not handle any input. It provides ``self.activate``
    method which should be called by something (presumably a menu containing
    this button).

    :param text: str. A button label

    :param action: callable. An action that this MenuItem performs. This should return either None, BearEvent or an iterable of BearEvents

    :param color: a bearlibterminal-compatible color that this button has by
    default

    :param highlight_color: a bearlibterminal-compatible color that this button
    has when highlighted via keyboard menu choice or mouse hover.
    """
    def __init__(self, text='Test', action=lambda: print('Button pressed'),
                 color='white', highlight_color='green',
                 **kwargs):
        self.color = color
        self.highlight_color = highlight_color
        # Widget generation
        label = Label(text, color=self.color)
        bg_chars = generate_box((label.width+2, label.height+2),
                                'single')
        bg_colors = copy_shape(bg_chars, self.color)
        super().__init__(bg_chars, bg_colors)
        self.add_child(label, (1, 1))
        self._rebuild_self()
        if not hasattr(action, '__call__'):
            raise BearException('Action for a button should be callable')
        self.action = action

    def highlight(self):
        """
        Change button colors to show that it's highlighted
        """
        self.background.colors = copy_shape(self.background.colors,
                                            self.highlight_color)
        self._rebuild_self()

    def unhighlight(self):
        """
        Change button colors to show that it's no longer highlighted
        :return:
        """
        self.background.colors = copy_shape(self.background.colors,
                                            self.color)
        self._rebuild_self()

    def activate(self):
        """
        Perform the button's action
        """
        return self.action()


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
                self.terminal.update_widget(self, refresh=True)
                
    def __repr__(self):
        raise BearException('FPSCounter does not support __repr__ serialization')
        # This should only be used **OUTSIDE** the ECS system.
        # Some debug screen or something


class MousePosWidget(Label):
    """
    A simple widget that reports current mouse position.
    

    In order to work, it needs ``self.terminal`` to be set to the current
    terminal, which means it should either be added to the terminal directly
    (without any Layouts) or terminal should be set manually before
    MousePosWidget gets its first ``tick`` event. It is also important that this
    class uses ``misc_input``:``TK_MOUSE_MOVE`` events to determine mouse
    position, so it would report a default value of '000x000' until the mouse
    has moved at least once.
    """
    
    def __init__(self, **kwargs):
        super().__init__(text='000x000', **kwargs)
        
    def on_event(self, event):
        if event.event_type == 'misc_input' and \
                     event.event_value == 'TK_MOUSE_MOVE':
            self.text = self._get_mouse_line()
        if isinstance(self.parent, BearTerminal):
            self.terminal.update_widget(self)

    def _get_mouse_line(self):
        if not self.terminal:
            raise BearException('MousePosWidget is not connected to a terminal')
        x = str(self.terminal.check_state('TK_MOUSE_X')).rjust(3, '0')
        y = str(self.terminal.check_state('TK_MOUSE_Y')).rjust(3, '0')
        return x + 'x' + y

    def __repr__(self):
        raise BearException('MousePosWidget does not support __repr__ serialization')
    
# Listeners


class Listener:
    """
    A base class for the things that need to interact with the queue (and maybe
    the terminal), but aren't Widgets.

    :param terminal: BearTerminal instance
    """
    def __init__(self, terminal=None):
        if terminal is not None:
            self.register_terminal(terminal)
    
    def on_event(self, event):
        """
        The event callback. This should be overridden by child classes.

        :param event: BearEvent instance
        """
        raise NotImplementedError('Listener base class is doing nothing')
    
    def register_terminal(self, terminal):
        """
        Register a terminal with which this listener will interact

        :param terminal: A BearTerminal instance
        """
        if not isinstance(terminal, BearTerminal):
            raise TypeError('Only BearTerminal instances registered by Listener')
        self.terminal = terminal
        
    
class ClosingListener(Listener):
    """
    The listener that waits for a ``TK_CLOSE`` input event (Alt-F4 or closing
    window) and sends the shutdown service event to the queue when it gets one.

    All widgets are expected to listen to it and immediately save their data or
    do whatever they need to do about it. On the next tick ClosingListener
    closes both terminal and queue altogether.
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
    A listener that logs the events it gets.

    It just prints whatever events it gets to sys.stderr. The correct
    way to use this class is to subscribe an instance to the events of interest
    and watch the output. If logging non-builtin events, make sure that their
    ``event_value`` can be converted to a string. Converstion uses
    ``str(value)``, not ``repr(value)`` to avoid dumping entire JSON representations.
    """
    def __init__(self, handle):
        super().__init__()
        if not hasattr(handle, 'write'):
            raise BearException('The LoggingListener needs a writable object')
        self.handle = handle
        
    def on_event(self, event):
        self.handle.write('{0}: type {1}, '.format(str(time()), event.event_type) +
                          'value {}\n'.format(event.event_value))
