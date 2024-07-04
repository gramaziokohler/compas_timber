from __future__ import annotations

import math

import compas
from compas.geometry import Plane
from compas.geometry import Vector
from compas.geometry import Line
from compas.geometry import Brep
from compas.geometry import BrepTrimmingError
from compas.geometry import intersection_line_plane
from compas.geometry import distance_point_point
from compas.geometry import cross_vectors
from compas.geometry import angle_vectors_signed
from compas.tolerance import TOL

if not compas.IPY:
    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from compas_timber.elements import Beam


class BTLxProcess(object):
    def __init__(self, ref_side_index):
        self.ref_side_index = ref_side_index


class OrientationType(object):
    START = 0
    END = 1


class JackRafterCut(BTLxProcess):
    def __init__(self, orientation, start_x=0.0, start_y=0.0, start_depth=0.0, angle=90.0, inclination=90.0, **kwargs):
        super(JackRafterCut, self).__init__(**kwargs)
        self._orientation = None
        self._start_x = None
        self._start_y = None
        self._start_depth = None
        self._angle = None
        self._inclination = None

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination = inclination

    @property
    def orientation(self):
        return self._orientation

    @orientation.setter
    def orientation(self, orientation):
        if orientation not in [OrientationType.START, OrientationType.END]:
            raise ValueError("Orientation must be either OrientationType.START or OrientationType.END.")
        self._orientation = orientation

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, start_x):
        if start_x > 100000.0:
            raise ValueError("Start X must be less than 50000.0.")
        self._start_x = start_x

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, start_y):
        if start_y > 50000.0:
            raise ValueError("Start Y must be less than 50000.0.")
        self._start_y = start_y

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, start_depth):
        if start_depth > 50000.0:
            raise ValueError("Start Depth must be less than 50000.0.")
        self._start_depth = start_depth

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, angle):
        if angle > 179.9 or angle < 0.1:
            raise ValueError("Angle must be between 0.1 and 179.9.")
        self._angle = angle

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, inclination):
        if inclination > 179.9 or inclination < 0.1:
            raise ValueError("Inclination must be between 0.1 and 179.9.")
        self._inclination = inclination

    @classmethod
    def from_plane_and_beam(cls, plane, beam, ref_side_index=0):
        # type: (Plane, Beam, int) -> JackRafterCut
        start_y = 0.0
        start_depth = 0.0
        ref_side = beam.ref_sides[ref_side_index]  # TODO: is this arbitrary?
        ref_edge = Line.from_point_and_vector(ref_side.point, ref_side.xaxis)

        point_start_x = intersection_line_plane(ref_edge, plane)
        if point_start_x is None:
            raise ValueError("Plane does not intersect with beam.")

        start_x = distance_point_point(ref_edge.point, point_start_x)
        orientation = OrientationType.START if start_x < beam.length * 0.5 else OrientationType.END
        angle_direction = cross_vectors(ref_side.normal, plane.normal)
        angle = angle_vectors_signed(ref_side.xaxis, angle_direction, ref_side.zaxis) * 180 / math.pi
        angle = 90 - (abs(angle) - 90)  # TODO: why?

        inclination = angle_vectors_signed(ref_side.zaxis, plane.normal, angle_direction) * 180 / math.pi
        inclination = 90 - (abs(inclination) - 90)  # TODO: why?
        return cls(orientation, start_x, start_y, start_depth, angle, inclination, ref_side_index=ref_side_index)

    def apply(self, beam, geometry):
        # type: (Beam, Brep) -> Brep
        cutting_plane = self._plane_from_params(beam)
        try:
            return geometry.trimmed(cutting_plane, TOL.absolute)
        except BrepTrimmingError:
            raise Exception(
                # TODO: use FeatureApplicationError
                "The cutting plane does not intersect with beam geometry.",
            )

    def _plane_from_params(self, beam):
        # type: (Beam) -> Plane
        # calculates the cutting plane from the machining parameters and the beam
        ref_side = beam.ref_sides[self.ref_side_index]
