import numpy as np

from dogfight import Plane
from utils import ARENA_HEIGHT, ARENA_WIDTH, ULX, ULY, LRX


# === starting coordinates ===
START_COORDS_Y = np.float64(ULY + (ARENA_HEIGHT // 2))
START_COORDS_ONE = np.array((START_COORDS_Y, ULX + (ARENA_WIDTH // 4)))
START_COORDS_TWO = np.array((START_COORDS_Y, LRX - (ARENA_WIDTH // 4)))
START_ANGLE_ONE = np.pi * -1/2
START_ANGLE_TWO = np.pi * 1/2


P51 = Plane(
    coordinates=START_COORDS_ONE,
    angle_of_attack=START_ANGLE_ONE,
    color=1,
    color_pair=1,
    speed=0.5,
    turning_circle=(np.pi * 1/8),
)


BF109 = Plane(
    coordinates=START_COORDS_TWO,
    angle_of_attack=START_ANGLE_TWO,
    color=3,
    color_pair=2,
    speed=0.5,
    turning_circle=(np.pi * 1/8),
)
