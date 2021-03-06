"""
Two Layouts designed specifically for the ECS system.
"""

from bear_hug.bear_utilities import BearECSException, BearLayoutException, \
    copy_shape
from bear_hug.ecs import Entity
from bear_hug.event import BearEvent
from bear_hug.widgets import Layout, Widget


# TODO: Make sure ECSLayout supports all the stuff from ScrollableECSLayout
class ECSLayout(Layout):
    """
    A Layout of entities.
    
    This layout, besides visualization, provides collision detection. It is
    controlled entirely by events. Although Layout methods  ``add_child`` and
    ``move_child`` are not overloaded, their use is discouraged. Just like
    a regular Layout, ECSLayout resides within a single bearlibterminal layer
    and therefore does not provide character overlap for overlapping entities.
    Who hides whom is currently determined by the order of widget addition, with
    newer entities on top of older ones (Z-levels are to be implemented in a
    future release).
    
    Event conventions are as following:

    ``BearEvent(event_type='ecs_create', event_value=entity_object)``

    Announces that a new Entity has been created and needs to be registered for
    ECSLayout. Does not cause it to be placed on screen. The same event tells
    the EntityTracker about any newly-created Entities. It should not be emitted
    until the Entity has at least an ID and a WidgetComponent.
    
    ``BearEvent(event_type='ecs_add', event_value=(entity, x, y))``.

    Announces that the widget of the entity in question should be added to the
    ECSLayout at (x;y). This event should not be emitted before both entity and
    its widget have been created, and 'ecs_create' event has been emitted.

    ``BearEvent(event_type='ecs_move', event_value=(entity, x, y))``

    Announces that the widget of the entity in question should be moved
    to (x; y). If the widget collides into the widget of another Entity (or
    multiple widgets), emits ``BearEvent('ecs_collide', other_entity_id)`` for
    each Entity that was collided into. If the widget touches Layout edges,
    emits ``BearEvent('ecs_collide', None)`` instead. In either case, collision
    does not automatically prevent movement.

    ``BearEvent(event_type='ecs_remove', event_value=entity)``

    Announces that the widget of a given entity should be removed from
    the ECSLayout, but does not cause or imply the its destruction. It is to be
    used when the Entity currently on screen needs to be hidden, but is
    expected to be shown again later.

    ``BearEvent(event_type='ecs_destroy', event_value=entity)``

    Announces that the widget of a given entity should be removed from
    the ECSLayout, as well as from its entities and widgets lists. This event is
    emitted when the entity is destroyed (eg by DestructorComponent) and used by
    EntityTracker to know which Entities no longer exist.

    ``BearEvent(event_type='ecs_redraw')``

    Announces that the layout needs to be redrawn this tick, even if none of the
    events above have been emitted. This is useful if some widget (eg animation)
    has changed its chars or colors, but was not moved, added or deleted.

    If at least one of these events was sent to the ECSLayout, it will redraw
    itself on 'tick_over'.

    :param chars: Layout BG chars

    :param colors: Layout BG colors
    """
    def __init__(self, chars, colors):
        super().__init__(chars, colors)
        self.entities = {}
        self.widgets = {}
        self.need_redraw = False
    
    def add_entity(self, entity):
        """
        Register the entity to be displayed.

        Assumes that the entity has a widget already. The widget is not actually
        shown until the `'ecs_add'` event with its entity ID is emitted.

        :param entity: Entity instance
        """
        if not isinstance(entity, Entity):
            raise BearECSException('Cannot add non-Entity to ECSLayout')
        self.entities[entity.id] = entity
        self.widgets[entity.id] = entity.widget.widget
    
    def remove_entity(self, entity_id):
        """
        Forget about the registered entity and its widget.

        Does not imply or cause the destruction of Entity object itself or any
        of its Component objects. Making sure that the entity is removed cleanly
        is not the Layout's job.

        :param entity_id: Entity ID
        """
        if entity_id not in self.entities:
            raise BearECSException('Attempting to remove nonexistent entity {} from ESCLayout'.
                                   format(entity_id))
        self.remove_child(self.entities[entity_id].widget.widget)
        del self.entities[entity_id]
        
    def on_event(self, event):
        """
        See class documentation

        :param event: BearEvent instance
        """
        r = []
        if event.event_type == 'ecs_move':
            entity_id, x, y = event.event_value
            if entity_id not in self.entities:
                # Silently ignore attempts to move nonexistent children
                # Some entities may not be shown right now, but still have a
                # PositionComponent that moves and emits events
                return
            # Checking if collision events need to be emitted
            # Check for collisions with border
            if x < 0 or x + self.entities[entity_id].widget.size[0]\
                 > len(self.chars[0]) or y < 0 or \
                 y + self.entities[entity_id].widget.size[1] > len(self.chars):
                r.append(BearEvent(event_type='ecs_collision',
                                   event_value=(entity_id, None)))
            else:
                # Apparently no collision with a border, can safely move
                self.move_child(self.widgets[entity_id], (x, y))
                self.need_redraw = True
                # collided = set()
                # for y_offset in range(self.entities[entity_id].widget.size[1]):
                #     for x_offset in range(self.entities[entity_id].widget.size[0]):
                #         for other_widget in self._child_pointers[y+y_offset] \
                #             [x+x_offset]:
                #             # Child_pointers is ECS-agnostic and stores pointers
                #             # to the actual widgets
                #                 collided.add(other_widget)
                # collided_ent_ids = set()
                # for child in self.entities:
                #     if child != entity_id and \
                #             self.entities[child].widget.widget in collided:
                #         collided_ent_ids.add(child)
                # for child in collided_ent_ids:
                #     r.append(BearEvent('ecs_collision', (entity_id, child)))
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
    A ECSLayout that can show only a part of its surface.

    Like a ScrollableLayout, accepts ``chars`` and ``colors`` on creation, which
    should be the size of the entire layout, not just the visible area.
    The latter is initialized by ``view_pos`` and ``view_size`` arguments.
    
    This class supports all 'ecs_*' events described in the docs for ECSLayout.
    In addition, it supports the following two two event types:
    
    ``BearEvent(event_type='ecs_scroll_by', event_value=(x, y))``

    Shifts visible area by x chars horizontally and by y chars vertically.
    
    ``BearEvent(event_type='ecs_scroll_to', event_value=(x, y)``

    Moves visible area to (x, y).

    Both events cause BearLayoutException if event values require visible area
    to move beyond Layout borders.

    :param chars: Layout BG chars.

    :param colors: Layout BG colors.

    :param view_pos: Top left corner of the initial visible area, 2-tuple (x, y).

    :param view_size: The size of the visible area, 2-tuple (x, y).
    """

    # This class is basically a copypaste of pieces from
    # widgets.ScrollableLayout and ecs_widgets.ECSLayout. These classes were not
    # merged or inherited from each other or something because they both can be
    # useful without each other's capabilities (and overhead). And multiple
    # inheritance is plain evil.
    def __init__(self, chars, colors,
                 view_pos=(0, 0), view_size=(10, 10)):
        self.entities = {}
        self.widgets = {}
        self.widget_to_entity = {} # A dict from id(widget) to entity
        self.z_values = copy_shape(chars, None)
        # copy_shape does not work with lists correctly, so.
        for line in range(len(self.z_values)):
            for char in range(len(self.z_values[0])):
                self.z_values[line][char] = []
        super().__init__(chars, colors)
        self.view_pos = view_pos[:]
        self.view_size = view_size[:]
        if not 0 <= view_pos[0] <= self.width - view_size[0] \
                or not 0 <= view_pos[1] <= self.height - view_size[1]:
            raise BearLayoutException('Initial viewpoint outside ' +
                                      'ScrollableLayout')
        if not 0 < view_size[0] <= len(chars[0]) \
                or not 0 < view_size[1] <= len(chars):
            raise BearLayoutException('Invalid view field size')

        self._rebuild_self()

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
                z = child.z_level
                if id(child) in self.widget_to_entity:
                    # Checking that the child belongs to the entity and that
                    # this entity has CollisionComponent. with face. If so,
                    # Z-levels are corrected to account for depth
                    child_entity = self.widget_to_entity[id(child)]
                    if hasattr(child_entity, 'collision') and child_entity.collision.face_size != (0, 0):
                        if not (child_entity.collision.face_position[0] <= x <=
                                child_entity.collision.face_position[0] +
                                child_entity.collision.face_size[0]) or \
                                not (child_entity.collision.face_position[
                                         1] <= y <=
                                     child_entity.collision.face_position[1] +
                                     child_entity.collision.face_size[1]):
                            # Outside child's face, Z correction applies
                            # TODO: do not assume z_shift=(1, -1)
                            y_offset = child_entity.collision.face_position[1] - y
                            x_offset = x - child_entity.collision.face_size[0] + \
                                       child_entity.collision.face_position[0]
                            if y_offset > 0 and x_offset <= 0:
                                z -= y_offset
                            elif x_offset > 0 and y_offset <= 0:
                                z -= x_offset
                            else:
                                z -= max(x_offset, y_offset)
                # Order of children:
                # 1. Children with Z-levels, sorted from lowest to highest
                # 2. Children without Z-levels
                # All ties are broken by newer child being placed after the old
                # When drawing, the last child should be addressed.

                # Items with Z-level are added before the first item that either
                # has higher Z-level than this child, or has no Z-level at all
                have_added = False
                if z:
                    for index, other_z in enumerate(self.z_values[pos[1] + y][pos[0] + x]):
                        if not other_z or other_z > z:
                            self.z_values[pos[1] + y][pos[0] + x].insert(index, z)
                            self._child_pointers[pos[1] + y][pos[0] + x].insert(index, child)
                            have_added = True
                            break
                # If no such child was encountered (eg this is the highest item,
                # or no Z-levelled items are present in child_pointers), or the
                # child has no Z-level, it is added to the end
                #
                if not have_added:
                    self.z_values[pos[1] + y][pos[0] + x].append(None)
                    self._child_pointers[pos[1] + y][pos[0] + x].append(child)
                assert len(self.z_values[pos[1] + y][pos[0] + x]) == len(self._child_pointers[pos[1] + y][pos[0] + x])

    def remove_child(self, child, remove_completely=True):
        for y in range(len(child.chars)):
            for x in range(len(child.chars[0])):
                try:
                    # TODO: avoid rebuilding z list
                    index = self._child_pointers[self.child_locations[child][1] + y][self.child_locations[child][0] + x].index(child)
                    del self.z_values[self.child_locations[child][1] + y]  \
                                     [self.child_locations[child][0] + x][index]
                except KeyError:
                    pass
        super().remove_child(child, remove_completely)

    def _rebuild_self(self):
        """
        Same as `Layout()._rebuild_self`, but all child positions are also
        offset by `view_pos`. Obviously, only `view_size[1]` lines
        `view_size[0]` long are set as `chars` and `colors`.
        :return:
        """
        chars = [[' ' for x in range(self.view_size[0])] \
                 for y in range(self.view_size[1])]
        colors = copy_shape(chars, 'white')
        for line in range(self.view_size[1]):
            for char in range(self.view_size[0]):
                for child in self._child_pointers[self.view_pos[1] + line] \
                                     [self.view_pos[0] + char][::-1]:
                    c_x = self.view_pos[0] + char - self.child_locations[child][
                        0]
                    c_y = self.view_pos[1] + line - self.child_locations[child][1]
                    if child.chars[c_y][c_x] not in (' ', None, 32):
                        # Skip all possible values for transparent empty char
                        chars[line][char] = child.chars[c_y][c_x]
                        colors[line][char] = child.colors[c_y][c_x]
                        break
        self.chars = chars
        self.colors = colors

    def resize_view(self, new_size):
        """
        Currently not implemented.
        :param new_size:
        :return:
        """
        # TODO: support resizing view.
        # This will require updating the pointers in terminal or parent layout
        raise NotImplementedError
    
    def scroll_to(self, pos):
        """
        Move field of view to `pos`.

        Raises `BearLayoutException` on incorrect position

        :param pos: 2-tuple (x, y)
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

        Raises `BearLayoutException` on incorrect position.

        :param shift: 2-tuple (dx, dy)
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
        self.widget_to_entity[id(entity.widget.widget)] = entity

    def remove_entity(self, entity_id):
        """
        Forget about the registered entity and its widget.
        Does not imply or cause the destruction of Entity object or any of its
        Component objects (except if this was the last reference). Making sure
        that the entity is removed cleanly is someone else's job.

        :param entity_id: ID of the removed entity.

        """
        if entity_id not in self.entities:
            raise BearECSException(
                'Attempting to remove nonexistent entity {} from ESCLayout'.
                format(entity_id))
        try:
            self.remove_child(self.entities[entity_id].widget.widget)
            del self.widget_to_entity[id(self.entities[entity_id].widget.widget)]
        except BearLayoutException:
            # Silently ignore any attempt to remove entities which weren't ever
            # actually placed on the layout (such as eg hands which were never
            # used during the whole level)
            pass
        del self.entities[entity_id]

    def on_event(self, event):
        """
        See class documentation.

        :param event: BearEvent instance.
        """
        # React to the events
        r = []
        if event.event_type == 'ecs_move':
            entity_id, x, y = event.event_value
            if entity_id not in self.entities or entity_id not in self.widgets:
                # Silently ignore attempts to move nonexistent children
                # Some entities may not be shown right now, but still have a
                # PositionComponent that moves and emits events
                return
            # Checking if collision events need to be emitted
            # Check for collisions with border
            try:
                if x < 0 or x + self.widgets[entity_id].width \
                        > len(self._child_pointers[0]) or y < 0 or \
                        y + self.widgets[entity_id].height > len(
                        self._child_pointers):
                    r.append(BearEvent(event_type='ecs_collision',
                                       event_value=(entity_id, None)))
                else:
                    # Apparently no collision with a border, can safely move
                    try:
                        self.move_child(self.widgets[entity_id], (x, y))
                    except:
                        pass
                    self.need_redraw = True
            except KeyError:
                # In some weird cases 'ecs_move' events can be emitted after the
                # entity got destroyed
                return
        elif event.event_type == 'ecs_create':
            self.add_entity(event.event_value)
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
