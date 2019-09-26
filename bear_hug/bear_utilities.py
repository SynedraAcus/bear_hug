"""
A collection of random stuff for bear_hug that wouldn't fit into other submodules.

Includes a series of useful functions and all bear_hug exception classes.
"""

from copy import deepcopy


def shapes_equal(a, b):
    """
    Tests if two nested lists are of the same shape

    :param a: list

    :param b: list

    :returns: True if lists are indeed of the same shape, False otherwise
    """
    if len(a) != len(b):
        return False
    if any(isinstance(x, list) and isinstance(y, list) and len(x) != len(y)
           for x, y in zip(a, b)):
        return False
    return True


def copy_shape(l, value=None):
    """
    Takes a nested list and returns the new list of the same shape, completely
    filled with the same value.

    May cause bugs when the value is mutable (for example, a list) because it
    fills the returned list with (pointers to) the same element, not independent
    copies. Since in practice this function is used to create ``colors`` for a
    widget with known ``chars``, or otherwise to mess around with chars/colors
    data (which are normally replaced entirely, not edited), it is left for the
    callers to make sure their values are OK.

    :param l: initial list

    :param value: value to fill the list with
    """
    r = []
    for i in l:
        if isinstance(i, list):
            r.append(copy_shape(i, value))
        else:
            r.append(value)
    return r


def slice_nested(l, slice_pos, slice_size):
    """
    Slice the nested list

    :param l: a nested list

    :param slice_pos: a 2-tuple (x, y) of slice start

    :param slice_size: a 2-tuple (width, height) of slice size
    """
    r = []
    for y in range(slice_pos[1], slice_pos[1] + slice_size[1]):
        line = []
        for x in range(slice_pos[0], slice_pos[0] + slice_size[0]):
            line.append(l[y][x])
        r.append(line)
    return r


def rotate_list(l):
    """
    Take a nested list of (x, y) dimensions, return an (y, x) list.

    :param l: a 2-nested list
    """
    # Without loss of generality, presume list is row-first and we need it
    # column-first
    r = [[None for x in range(len(l))] for x in range(len(l[0]))]
    for row_index, row in enumerate(l):
        for column_index, column_value in enumerate(row):
            r[column_index][row_index] = column_value
    return r
    

def rectangles_collide(pos1, size1, pos2, size2):
    """
    Return True if the rectangles collide

    Rectangles are supplied in [x,y], [xsize, ysize] form with the left corner
    and size. Assumes positions and sizes to be sorted

    :param pos1: top left corner of the first rectangle, as (x, y) 2-tuple

    :param size1: size of the first rectangle, as (width, height) 2-tuple

    :param pos2: top left corner of the second rectangle, as (x, y) 2-tuple

    :param size2: size of the second rectangle, as (width, height) 2-tuple
    """
    # X overlap
    if pos1[0] <= pos2[0]+size2[0]-1 and pos2[0] <= pos1[0]+size1[0]-1:
        # Y overlap
        if pos1[1] <= pos2[1]+size2[1]-1 and pos2[1] <= pos1[1]+size1[1]-1:
            return True
    return False


def has_values(l):
    """
    Returns True if a 2-nested list contains at least one truthy value.

    :param l: a nested list

    :return:
    """
    for row in l:
        for value in row:
            if value:
                return True
    return False


def blit(l1, l2, x, y):
    """
    Blits ``l2`` to ``l1`` at a given pos, overwriting the original values.

    This method does not actually affect ``l1``; instead, it copies it to a new
    variable, sets whatever values need to be set, and returns the modified
    copy.

    :param l1: A 2-nested list.

    :param l2: A 2-nested list.

    :param x, y: A top left corner of ``l2`` relative to ``l1``.
    :return:
    """
    if x + len(l2[0]) > len(l1[0]) or y + len(l2) > len(l1):
        raise ValueError('Cannot blit the list where it won\'t fit')
    r = deepcopy(l1)
    for y_offset in range(len(l2)):
        for x_offset in range(len(l2[0])):
            r[y+y_offset][x+x_offset] = l2[y_offset][x_offset]
    return r


#  Exceptions were moved here to avoid circular imports
class BearException(Exception):
    """
    A base class for all bear_hug exceptions
    """
    pass


class BearLoopException(BearException):
    """
    Something wrong with the loop or event system.
    """
    pass


class BearLayoutException(BearException):
    """
    Something wrong with adding/drawing/removing a Widget on a Layout
    """
    pass


class BearECSException(BearException):
    """
    Something wrong with Entity-Component System.
    """
    pass


class BearSoundException(BearException):
    """
    Something wrong with the sound.
    """
    pass


class BearJSONException(BearException):
    """
    Something wrong with JSON (de)serialization of widgets or entities.
    """
    pass
