import unittest

import numpy as np

from context import dogfight

PI = np.pi


class TestMovePlane(unittest.TestCase):

    def setUp(self):

        self.plane = dogfight.Plane(
            coordinates=np.array([0., 0.]),
            angle_of_attack=(PI * 1/2),
            speed=1.,
            turning_circle=(PI * 1/8)
        )

    def test_move_plane_right(self):

        dogfight.move_plane(self.plane)

        self.assertEqual(list(self.plane.coordinates), [0, 1])

    def test_move_plane_right_double_speed(self):

        self.plane.speed = 2.
        dogfight.move_plane(self.plane)

        self.assertEqual(list(self.plane.coordinates), [0, 2])

    def test_move_plane_right_half_speed(self):

        self.plane.speed = 0.5
        dogfight.move_plane(self.plane)

        self.assertEqual(list(self.plane.coordinates), [0, 0.5])

    def test_move_plane_up_right(self):

        self.plane.angle_of_attack = (PI * 1/4)
        dogfight.move_plane(self.plane)

        self.assertEqual(
            np.round(np.sum(self.plane.coordinates ** 2), 2),
            1 ** 2
        )

    def test_move_plane_up_right_triple_speed(self):

        self.plane.angle_of_attack = (PI * 1/4)
        self.plane.speed = 3.
        dogfight.move_plane(self.plane)

        self.assertEqual(
            np.round(np.sum(self.plane.coordinates ** 2), 2),
            3 ** 2
        )


@unittest.skip
class TestChangePitch(unittest.TestCase):

    def setUp(self):

        self.plane = dogfight.Plane(
            coordinates=np.array([0., 0.]),
            angle_of_attack=(PI * 3/2),
            speed=1.,
            turning_circle=(PI * 1/8)
        )

    def test_change_pitch_up(self):

        dogfight.change_pitch(self.plane, up=True)

        self.assertEqual(list(self.plane.angle_of_attack), 0.0)

    def test_change_pitch_up_four_keys(self):

        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)

        self.assertEqual(list(self.plane.direction), [-4/8, 4/8])

    def test_change_pitch_180_degrees(self):

        self.plane.turning_circle = 4

        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)
        dogfight.change_pitch(self.plane, up=True)

        self.assertEqual(list(self.plane.direction), [0/4, -4/4])


if __name__ == '__main__':
    unittest.main(verbosity=3)
