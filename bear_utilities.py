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
