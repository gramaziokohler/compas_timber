"""Birdsmouth BTLx processing implementation.

Implements parameters from BTLx 2.1.0 (page 28 table). This module provides
an implementation that maps those parameters to two cutting planes and
serializes the BTLx parameters via `BirdsmouthParams`.
"""

import math
from collections import OrderedDict

from compas.geometry import Frame, Plane, Point, Rotation, Transformation, closest_point_on_line, dot_vectors
from compas.geometry import Vector
from compas.geometry import Line
from compas.geometry import angle_vectors
from compas.geometry import intersection_plane_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import intersection_line_beam_param, planar_surface_point_at

from .btlx import BTLxProcessing, BTLxProcessingParams, OrientationType


class Birdsmouth(BTLxProcessing):
    """Birdsmouth machining processing.

    Parameters correspond exactly to the BTLx table on page 28.
    """

    PROCESSING_NAME = "Birdsmouth"  # type: ignore

    def __init__(
        self,
        orientation=OrientationType.START,
        start_x=0.0,
        start_y=0.0,
        start_depth=20.0,
        angle=90.0,
        inclination1=45.0,
        inclination2=135.0,
        depth=20.0,
        width=0.0,
        width_counterpart_limited=False,
        width_counterpart=120.0,
        height_counterpart_limited=False,
        height_counterpart=120.0,
        face_limited_front=False,
        face_limited_back=False,
        lead_angle_parallel=True,
        lead_angle=90.0,
        lead_inclination_parallel=True,
        lead_inclination=90.0,
        rafter_nail_hole=False,
        **kwargs,
    ):
        super(Birdsmouth, self).__init__(**kwargs)

        self.orientation = orientation
        self.start_x = start_x
        self.start_y = start_y
        self.start_depth = start_depth
        self.angle = angle
        self.inclination1 = inclination1
        self.inclination2 = inclination2
        self.depth = depth
        self.width = width

        self.width_counterpart_limited = width_counterpart_limited
        self.width_counterpart = width_counterpart
        self.height_counterpart_limited = height_counterpart_limited
        self.height_counterpart = height_counterpart
        self.face_limited_front = face_limited_front
        self.face_limited_back = face_limited_back
        self.lead_angle_parallel = lead_angle_parallel
        self.lead_angle = lead_angle
        self.lead_inclination_parallel = lead_inclination_parallel
        self.lead_inclination = lead_inclination
        self.rafter_nail_hole = rafter_nail_hole

    @property
    def params(self):
        return BirdsmouthParams(self)

    @property
    def __data__(self):
        data = super(Birdsmouth, self).__data__
        data.update(
            {
                "orientation": self.orientation,
                "start_x": self.start_x,
                "start_y": self.start_y,
                "start_depth": self.start_depth,
                "angle": self.angle,
                "inclination1": self.inclination1,
                "inclination2": self.inclination2,
                "depth": self.depth,
                "width": self.width,
            }
        )
        return data

    # simple validation for numeric ranges
    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, v):
        if v > 100000.0 or v < -100000.0:
            raise ValueError("StartX out of range")
        self._start_x = v

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, v):
        if v > 50000.0 or v < -50000.0:
            raise ValueError("StartY out of range")
        self._start_y = v

    @property
    def start_depth(self):
        return self._start_depth

    @start_depth.setter
    def start_depth(self, v):
        if v < 0.0 or v > 50000.0:
            raise ValueError("StartDepth out of range")
        self._start_depth = v

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, v):
        if v < 0.1 or v > 179.9:
            raise ValueError("Angle out of range")
        self._angle = v

    @property
    def inclination1(self):
        return self._inclination1

    @inclination1.setter
    def inclination1(self, v):
        if v < 0.0 or v > 180.0:
            raise ValueError("Inclination1 out of range")
        self._inclination1 = v

    @property
    def inclination2(self):
        return self._inclination2

    @inclination2.setter
    def inclination2(self, v):
        if v < 0.0 or v > 180.0:
            raise ValueError("Inclination2 out of range")
        self._inclination2 = v

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, v):
        if v < 0.0 or v > 50000.0:
            raise ValueError("Depth out of range")
        self._depth = v

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, v):
        if v < 0.0 or v > 50000.0:
            raise ValueError("Width out of range")
        self._width = v

    @classmethod
    def from_planes_and_beam(cls, planes, beam, ref_side_index=None, **kwargs):
        """Create a Birdsmouth instance from two cutting planes and the beam.

        This maps the detected geometry to Birdsmouth parameters.
        """
        if len(planes) != 2:
            raise ValueError("Exactly two cutting planes are required to create a Birdsmouth instance.")

        # ensure Plane instances
        planes = [Plane.from_frame(p) if not hasattr(p, "normal") else p for p in planes]

        ln = intersection_plane_plane(planes[0], planes[1])
        if not ln:
            raise ValueError("The two cutting planes are parallel")

        line = Line(Point(*ln[0]), Point(*ln[1]))
        face_intersections = intersection_line_beam_param(line, beam)
        if not face_intersections:
            raise ValueError("Planes do not intersect with beam.")


        if not ref_side_index:
            face_indices = face_intersections.keys()
            if not abs(face_indices[0]-face_indices[1])==2:
                raise ValueError("the planes' intersection line must pass through opposite faces of the beam")
            for rsi in range(4):
                if rsi in face_indices:
                    continue 
                ref_face_normal = beam.ref_sides[rsi].normal
                for plane in planes:
                    cp = closest_point_on_line(plane.point, line)
                    if dot_vectors(ref_face_normal, Vector.from_start_end(cp, plane.point)) <0:
                        break
                else: #both dot vectors positive
                    ref_side_index = rsi

        if not ref_side_index:
            raise ValueError("ref_side_index could not be identified")

        ref_side = beam.ref_sides[ref_side_index]
        planes = cls._reorder_planes(planes, beam)
        orientation = OrientationType.START
        
        start_x, start_y = cls._calculate_start_x_y(ref_side, face_intersections[ref_side_index])
        angle_1, angle_2 = cls._calculate_angle(ref_side, planes, orientation)
        incl_1, incl_2 = cls._calculate_inclination(ref_side, planes)

        # map detected geometry to Birdsmouth params
        angle = (angle_1 + angle_2) / 2.0
        inclination1 = incl_1
        inclination2 = incl_2

        start_depth = 0.0
        return cls(
            orientation,
            start_x,
            start_y,
            start_depth,
            angle,
            inclination1,
            inclination2,
            ref_side_index=ref_side_index,
            **kwargs,
        )

    @staticmethod
    def _reorder_planes(planes, intersection_line, ref_side):
        lines = [Line.from_point_and_vector(plane.point, intersection_line.direction) for plane in planes]
        points = [Point(*intersection_plane_plane(line, Plane.from_frame(ref_side))) for line in lines]
        dots = []
        for point in points:
            if hasattr(point, "x"):
                dots.append(point.x * ref_side.yaxis[0] + point.y * ref_side.yaxis[1] + point.z * ref_side.yaxis[2])
            else:
                dots.append(0)
        if dots[0] > dots[1]:
            return [planes[1], planes[0]]
        else:
            return planes

    @staticmethod
    def _calculate_orientation(beam, cutting_planes):
        s = cutting_planes[0].normal + cutting_planes[1].normal
        if Vector.dot(beam.centerline.direction, s) > 0:
            return OrientationType.START
        else:
            return OrientationType.END

    @staticmethod
    def _calculate_start_x_y(ref_side, point_start_xy):
        pt_xy = point_start_xy.transformed(Transformation.from_frame_to_frame(ref_side, Frame.worldXY()))
        return pt_xy.x, pt_xy.y

    @staticmethod
    def _calculate_angle(ref_side, planes, orientation):
        angles = []
        for plane in planes:
            angle_vector = Vector.cross(ref_side.zaxis, plane.normal)
            if Vector.dot(angle_vector, ref_side.yaxis) < 0:
                angle_vector = -angle_vector
            if orientation == OrientationType.START:
                angle = angle_vectors(ref_side.xaxis, angle_vector, deg=True)
            else:
                angle = angle_vectors(ref_side.xaxis, -angle_vector, deg=True)
            angles.append(angle)
        return angles

    @staticmethod
    def _calculate_inclination(ref_side, planes):
        inclinations = []
        for plane in planes:
            inclination = angle_vectors(ref_side.normal, plane.normal, deg=True)
            inclinations.append(inclination)
        return inclinations

    def planes_from_params_and_beam(self, beam):
        ref_side = beam.side_as_surface(self.ref_side_index)
        p_origin = planar_surface_point_at(ref_side, self.start_x, self.start_y)
        ref_frame = Frame(p_origin, ref_side.frame.xaxis, ref_side.frame.yaxis)

        if self.orientation == OrientationType.END:
            ref_frame.xaxis = -ref_frame.xaxis

        origin = Point(
            p_origin.x - ref_frame.xaxis[0] * self.start_depth,
            p_origin.y - ref_frame.xaxis[1] * self.start_depth,
            p_origin.z - ref_frame.xaxis[2] * self.start_depth,
        )

        horiz = Rotation.from_axis_and_angle(ref_frame.zaxis, math.radians(self.angle), point=origin)

        f1 = ref_frame.copy()
        f1.transform(horiz)
        f1.transform(Rotation.from_axis_and_angle(f1.xaxis, math.radians(self.inclination1), point=origin))

        f2 = ref_frame.copy()
        f2.transform(horiz)
        f2.transform(Rotation.from_axis_and_angle(f2.xaxis, math.radians(self.inclination2), point=origin))

        return [Plane(origin, f1.xaxis), Plane(origin, f2.xaxis)]

    def apply(self, geometry, beam):
        try:
            planes = self.planes_from_params_and_beam(beam)
        except Exception as e:
            raise FeatureApplicationError(None, geometry, f"Failed to generate cutting planes: {e}")

        planes = [p.transformed(beam.transformation_to_local()) for p in planes]

        trim_volume = geometry.copy()
        for p in planes:
            trim_volume.trim(p)
        return geometry - trim_volume


class BirdsmouthParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(BirdsmouthParams, self).__init__(instance)

    def as_dict(self):
        inst = self._instance
        result = OrderedDict()
        result["Orientation"] = inst.orientation
        result["StartX"] = "{:.{prec}f}".format(float(inst.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(inst.start_y), prec=TOL.precision)
        result["StartDepth"] = "{:.{prec}f}".format(float(inst.start_depth), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(inst.angle), prec=TOL.precision)
        result["Inclination1"] = "{:.{prec}f}".format(float(inst.inclination1), prec=TOL.precision)
        result["Inclination2"] = "{:.{prec}f}".format(float(inst.inclination2), prec=TOL.precision)
        result["Depth"] = "{:.{prec}f}".format(float(inst.depth), prec=TOL.precision)
        result["Width"] = "{:.{prec}f}".format(float(inst.width), prec=TOL.precision)
        result["WidthCounterPartLimited"] = {"Value": "yes" if inst.width_counterpart_limited else "no"}
        result["WidthCounterPart"] = "{:.{prec}f}".format(float(inst.width_counterpart), prec=TOL.precision)
        result["HeightCounterPartLimited"] = {"Value": "yes" if inst.height_counterpart_limited else "no"}
        result["HeightCounterPart"] = "{:.{prec}f}".format(float(inst.height_counterpart), prec=TOL.precision)
        result["FaceLimitedFront"] = {"Value": "yes" if inst.face_limited_front else "no"}
        result["FaceLimitedBack"] = {"Value": "yes" if inst.face_limited_back else "no"}
        result["LeadAngleParallel"] = {"Value": "yes" if inst.lead_angle_parallel else "no"}
        result["LeadAngle"] = "{:.{prec}f}".format(float(inst.lead_angle), prec=TOL.precision)
        result["LeadInclinationParallel"] = {"Value": "yes" if inst.lead_inclination_parallel else "no"}
        result["LeadInclination"] = "{:.{prec}f}".format(float(inst.lead_inclination), prec=TOL.precision)
        result["RafterNailHole"] = {"Value": "yes" if inst.rafter_nail_hole else "no"}
        return result


class BirdsmouthProxy(object):
    def __init__(self, planes, element, ref_side_index=None):
        self.planes = [plane.transformed(element.transformation_to_local()) for plane in planes]
        self.element = element
        self.ref_side_index = ref_side_index
        self._processing = None

    def unproxified(self):
        if not self._processing:
            planes = [plane.transformed(self.element.modeltransformation) for plane in self.planes]
            self._processing = Birdsmouth.from_planes_and_beam(planes, self.element, self.ref_side_index)
        return self._processing

    @classmethod
    def from_planes_and_beam(cls, planes, beam, ref_side_index=None):
        if len(planes) != 2:
            raise ValueError("Exactly two cutting planes are required to create a BirdsmouthProxy instance.")
        return cls(planes, beam, ref_side_index)

    @classmethod
    def from_shapes_and_element(cls, plane_a, plane_b, element, **kwargs):
        return cls.from_planes_and_beam([plane_a, plane_b], element, **kwargs)

    def apply(self, geometry, beam):
        return self.unproxified().apply(geometry, beam)
