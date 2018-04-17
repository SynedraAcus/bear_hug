# Tests for bear_utilities

from bear_hug.bear_utilities import *


def test_shapes():
    l = [[1, 1], [2, 2], [3, 3, 3]]
    l2 = copy_shape(l, None)
    assert l2 == [[None, None], [None, None], [None, None, None]]
    assert shapes_equal(l, l2)


def test_collision():
    assert rectangles_collide((5, 5), (2, 2), (5, 6), (1, 1))
    assert rectangles_collide((5, 5), (2, 2), (1, 1), (5, 10))
    assert not rectangles_collide((5, 5), (1, 1), (6, 6), (1, 1))
