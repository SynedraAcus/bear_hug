"""
A collection of random functions useful for bear_hug
"""


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
    filled with the same value
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
