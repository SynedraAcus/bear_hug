"""
A collection of Widgets and Listeners designed specifically for the ECS system.
"""

from bear_hug.bear_utilities import BearECSException, BearLayoutException, \
    copy_shape
from bear_hug.ecs import Entity
from bear_hug.event import BearEvent
from bear_hug.widgets import Layout


class ECSLayout(Layout):
    """
    A Layout of entities.
    
    It is controlled entirely by events. Although Layour methods like
    `add_child` and `move_child` are not overloaded, their use is discouraged.
    
    In all events, entity IDs, not the actual Entity objects, are passed. Event
    conventions are as following:
    
    `BearEvent(event_type='ecs_move', event_value=(entity, x, y))`.
    Announces that the widget of the entity in question should be moved
    to (x; y). Behaviour for widgets trying to leave map edges is left to
    be determined by ECSLayout or its children.
    
    `BearEvent(event_type='ecs_remove', event_value=entity)`.
    Announces that the widget of the entity in question should be removed from
    the ECSLayout. Does not cause or imply the destruction of entity object.
    
    `BearEvent(event_type='ecs_add', event_value=(entity, x, y))`.
    Announces that the widget of the entity in question should be added to the
    ECSLayout at (x;y). The emission of this event implies the existence of the
    entity and its widget.
    
    This widget also provides the collision detection for all widgets within it.
    If a widget attempts to move into the position occupied by some other
    widget, the movement is not blocked, but the 'ecs_collision' event(s) get
    emitted. The event follows the following convention:
    
    `BearEvent(event_type='ecs_collision', event_value=(widget_moved.id,
                                                    widget_collided_into.id))`
    If the widget enters the screen border (ie will go outside it the next time
    it moves, assuming it keeps the direction), the event takes the following
    form:
    `BearEvent(event_type='ecs_collision', event_value=(widget_moved.id,
                                                        None))`
    """
    
    def __init__(self, chars, colors):
        super().__init__(chars, colors)
        self.entities = {}
        self.widgets = {}
        self.need_redraw = False
    
    def add_entity(self, entity):
        """
        Register the entity to be displayed. Assumes that the entity has a
        widget already.
        
        The entity is not actually shown until the `'ecs_add'` event is emitted
        :return:
        """
        if not isinstance(entity, Entity):
            raise BearECSException('Cannot add non-Entity to ECSLayout')
        self.entities[entity.id] = entity
        self.widgets[entity.id] = entity.widget.widget
    
    def remove_entity(self, entity_id):
        """
        Forget about the registered entity and its widget.
        Does not imply or cause the destruction of Entity object or any of its
        Component objects (except if this was the last reference). Making sure
        that the entity is removed cleanly is someone else's job.
        :param entity_id:
        :return:
        """
        if entity_id not in self.entities:
            raise BearECSException('Attempting to remove nonexistent entity {} from ESCLayout'.
                                   format(entity_id))
        self.remove_child(self.entities[entity_id].widget.widget)
        del self.entities[entity_id]
        
    def on_event(self, event):
        # React to the events
        r = []
        if event.event_type == 'ecs_move':
            entity_id, x, y = event.event_value
            # Checking if collision events need to be emitted
            # Check for collisions with border
            if x < 0 or x+self.entities[entity_id].widget.size[0]\
                 > len(self.chars[0]) or y < 0 or \
                 y + self.entities[entity_id].widget.size[1] > len(self.chars):
                r.append(BearEvent(event_type='ecs_collision',
                                   event_value=(entity_id, None)))
            else:
                # Apparently no collision with a border, can safely move
                self.move_child(self.widgets[entity_id], (x, y))
                self.need_redraw = True
                collided = set()
                for y_offset in range(self.entities[entity_id].widget.size[1]):
                    for x_offset in range(self.entities[entity_id].widget.size[0]):
                        for other_widget in self._child_pointers[y+y_offset]\
                            [x+x_offset]:
                            # Child_pointers is ECS-agnostic and stores pointers
                            # to the actual widgets
                                collided.add(other_widget)
                collided_ent_ids = set()
                for child in self.entities:
                    if child != entity_id and \
                            self.entities[child].widget.widget in collided:
                        collided_ent_ids.add(child)
                for child in collided_ent_ids:
                    r.append(BearEvent('ecs_collision', (entity_id, child)))
        elif event.event_type == 'ecs_create':
            self.add_entity(event.event_value)
            self.need_redraw = True
        elif event.event_type == 'ecs_destroy':
            self.remove_entity(event.event_value)
            self.need_redraw = True
        elif event.event_type == 'ecs_remove':
            self.remove_child(self.entities[event.event_value].widget.widget)
            self.need_redraw = True
        elif event.event_type == 'ecs_add':
            entity_id, x, y = event.event_value
            self.add_child(self.widgets[entity_id], (x, y))
            self.need_redraw = True
        elif event.event_type == 'ecs_update':
            # Some widget has decided it's time to redraw itself
            self.need_redraw = True
        elif event.event_type == 'service' and event.event_value == 'tick_over'\
                and self.need_redraw:
            self._rebuild_self()
            self.terminal.update_widget(self)
            self.need_redraw = False
        if r:
            return r
        
    def __repr__(self):
        # It's unlikely that repr(layout) is ever gonna be necessary.
        # And it's very bad to try and serialize them. Widget serialization is
        # only intended for use with the Widgets that can be part of a
        # WidgetComponent. Layouts are sorta frontend for the entire ECS system,
        # not a part of it.
        raise BearECSException('ECSLayout and its children are not meant to be stored via repr')


class ScrollableECSLayout(Layout):
    """
    A Layout that can show only a part of its surface and supports ECS system.

    Like a ScrollableLayout, accepts `chars` and `colors` on creation, which
    should be the size of the entire layout, not just the visible area.
    The latter is initialized by `view_pos` and `view_size` arguments.
    
    Like an ECSLayout, supports all 'ecs_*' events. Unlike it, this class also
    supports two event types:
    
    `BearEvent(event_type='ecs_scroll_by', event_value=(x, y)). Shifts visible
    area by x chars horizontally and by y chars vertically.
    
    `BearEvent(event_type='ecs_scroll_to', event_value=(x, y). Moves visible
    area to (x, y).
    
    If incorrect value is provided to either of these events, it is silently
    ignored.
    """

    # This class is basically a copypaste of pieces from
    # widgets.ScrollableLayout and ecs_widgets.ECSLayout. These classes were not
    # merged or inherited from each other or something because they both can be
    # useful without each other's capabilities (and overhead). And multiple
    # inheritance is plain evil.
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
        self.entities = {}
        self.widgets = {}
        self.view_pos = view_pos[:]
        self.view_size = view_size[:]
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
                for child in self._child_pointers[self.view_pos[1] + line] \
                                     [self.view_pos[0] + char][::-1]:
                    # Addressing the correct child position
                    c = child.chars[
                        self.view_pos[1] + line - self.child_locations[child][
                            1]] \
                        [self.view_pos[0] + char - self.child_locations[child][
                            0]]
                    if c != ' ':
                        # Spacebars are used as empty space and are transparent
                        chars[line][char] = c
                        break
                colors[line][char] = \
                    child.colors[
                        self.view_pos[1] + line - self.child_locations[child][
                            1]] \
                        [self.view_pos[0] + char - self.child_locations[child][
                        0]]
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
                or not 0 <= pos[1] <= len(self._child_pointers) - \
                       self.view_size[1]:
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

    def add_entity(self, entity):
        """
        Register the entity to be displayed. Assumes that the entity has a
        widget already.

        The entity is not actually shown until the `'ecs_add'` event is emitted
        :return:
        """
        if not isinstance(entity, Entity):
            raise BearECSException('Cannot add non-Entity to ECSLayout')
        self.entities[entity.id] = entity
        self.widgets[entity.id] = entity.widget.widget

    def remove_entity(self, entity_id):
        """
        Forget about the registered entity and its widget.
        Does not imply or cause the destruction of Entity object or any of its
        Component objects (except if this was the last reference). Making sure
        that the entity is removed cleanly is someone else's job.
        :param entity_id:
        :return:
        """
        if entity_id not in self.entities:
            raise BearECSException(
                'Attempting to remove nonexistent entity {} from ESCLayout'.
                format(entity_id))
        self.remove_child(self.entities[entity_id].widget.widget)
        del self.entities[entity_id]

    def on_event(self, event):
        # React to the events
        r = []
        if event.event_type == 'ecs_move':
            entity_id, x, y = event.event_value
            # Checking if collision events need to be emitted
            # Check for collisions with border
            try:
                if x < 0 or x + self.entities[entity_id].widget.size[0] \
                        > len(self._child_pointers[0]) or y < 0 or \
                        y + self.entities[entity_id].widget.size[1] > len(
                        self._child_pointers):
                    r.append(BearEvent(event_type='ecs_collision',
                                       event_value=(entity_id, None)))
                else:
                    # Apparently no collision with a border, can safely move
                    self.move_child(self.widgets[entity_id], (x, y))
                    self.need_redraw = True
                    collided = set()
                    for y_offset in range(
                            self.entities[entity_id].widget.size[1]):
                        for x_offset in range(
                                self.entities[entity_id].widget.size[0]):
                            for other_widget in \
                            self._child_pointers[y + y_offset] \
                                    [x + x_offset]:
                                # Child_pointers is ECS-agnostic and stores pointers
                                # to the actual widgets
                                collided.add(other_widget)
                    # TODO: optimize to avoid checking all entities in collision detector
                    # Probably just storing all entity ids along with child pointers
                    collided_ent_ids = set()
                    for child in self.entities:
                        if child != entity_id and \
                                self.entities[child].widget.widget in collided:
                            collided_ent_ids.add(child)
                    for child in collided_ent_ids:
                        r.append(BearEvent('ecs_collision', (entity_id, child)))
            except KeyError:
                # In some weird cases 'ecs_move' events can be emitted after the
                # entity got destroyed
                return
        elif event.event_type == 'ecs_create':
            self.add_entity(event.event_value)
            self.need_redraw = True
        elif event.event_type == 'ecs_destroy':
            self.remove_entity(event.event_value)
            self.need_redraw = True
        elif event.event_type == 'ecs_remove':
            self.remove_child(
                self.entities[event.event_value].widget.widget)
            self.need_redraw = True
        elif event.event_type == 'ecs_add':
            entity_id, x, y = event.event_value
            self.add_child(self.widgets[entity_id], (x, y))
            self.need_redraw = True
        elif event.event_type == 'ecs_scroll_to':
            try:
                self.scroll_to(event.event_value)
                self.need_redraw = True
            except BearLayoutException:
                pass
        elif event.event_type == 'ecs_scroll_by':
            try:
                self.scroll_by(event.event_value)
                self.need_redraw = True
            except BearLayoutException:
                pass
        elif event.event_type == 'ecs_update':
            # Some widget has decided it's time to redraw itself
            self.need_redraw = True
        elif event.event_type == 'service' and event.event_value == 'tick_over' \
                and self.need_redraw:
            self._rebuild_self()
            self.terminal.update_widget(self)
            self.need_redraw = False
        
        if r:
            return r

    def __repr__(self):
        # It's unlikely that repr(layout) is ever gonna be necessary.
        # And it's very bad to try and serialize them. Widget serialization is
        # only intended for use with the Widgets that can be part of a
        # WidgetComponent. Layouts are sorta frontend for the entire ECS system,
        # not a part of it.
        raise BearECSException(
            'ECSLayout and its children are not meant to be stored via repr')
