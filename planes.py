from functools import partial

import numpy as np

from base import Plane


# === plane partial classes ===
# the planes are pre-configured `Plane` objects
# they are not initialised because they need to be
# provided with a unique plane_id at the time of creation
# which must occur AFTER `curses.wrapper` has been called

P51 = partial(
    Plane,
    color=1,
    speed=0.3,
    turning_circle=(np.pi * 1/8),
)


BF109 = partial(
    Plane,
    color=3,
    speed=0.3,
    turning_circle=(np.pi * 1/8),
)
