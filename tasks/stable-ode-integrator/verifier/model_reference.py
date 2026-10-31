"""Reaction model definition.

DO NOT MODIFY THIS FILE. The grader verifies it byte for byte and treats the
right-hand side below as the definition of the problem.

    dy/dt = -k*y*(1 - y) + 0.1*sin(5t),    y(0) = 0.5
"""

import math

Y0 = 0.5


def rhs(t, y, k):
    """Right-hand side of the reaction ODE."""
    return -k * y * (1.0 - y) + 0.1 * math.sin(5.0 * t)
