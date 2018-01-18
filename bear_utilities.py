"""
A collection of random functions useful for bear_hug
"""

from copy import copy

def shapes_equal(a, b):
    """
    Tests if two nested lists are of the same shape
    :param a: list
    :param b: list
    :return: bool
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
    Works incorrectly with mutable types (particularly containers) because it
    fills the returned list with (pointers to) the same list, not independent
    copies and adding to either of them would affect all. Since this function
    gets called pretty often with primitives, eg None, and almost never with
    lists, it is left as is and callers are to be made sure their lists are OK.
    :param l: initial list
    :param value: value to fill the list with
    :return:
    """
    r = []
    for i in l:
        if isinstance(i, list):
            r.append(copy_shape(i, value))
        else:
            r.append(value)
    return r


def rotate_list(l):
    """
    Take a nested list of (x, y) dimensions, return an (y, x) list
    :param l:
    :return:
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
    :param pos1: 
    :param size1:
    :param pos2:
    :param size2:
    :return: 
    """
    # X overlap
    if pos1[0] <= pos2[0]+size2[0]-1 and pos2[0] <= pos1[0]+size1[0]-1:
        # Y overlap
        if pos1[1] <= pos2[1]+size2[1]-1 and pos2[1] <= pos1[1]+size1[1]-1:
            return True
    return False


def has_values(l):
    """
    Returns True if a nested list contains at least one non-None value
    :param l:
    :return:
    """
    for row in l:
        for value in row:
            if value:
                return True
    return False


#  Exceptions were moved here to avoid circular imports
class BearException(Exception):
    pass


class BearLoopException(BearException):
    pass


class BearLayoutException(BearException):
    pass
