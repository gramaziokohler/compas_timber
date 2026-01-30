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
from compas.geometry import cross_vectors
from compas.geometry import intersection_plane_plane
from compas.geometry import intersection_line_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError
from compas_timber.utils import intersection_line_beam_param, planar_surface_point_at

from .btlx import BTLxProcessing, BTLxProcessingParams, OrientationType


class Birdsmouth(BTLxProcessing):
    """Birdsmouth machining processing.

    Parameters correspond exactly to the BTLx table on page 28.
    """

    PROCESSING_NAME = "BirdsMouth"  # type: ignore

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
                "width_counterpart_limited": self.width_counterpart_limited,
                "width_counterpart": self.width_counterpart,
                "height_counterpart_limited": self.height_counterpart_limited,
                "height_counterpart": self.height_counterpart,
                "face_limited_front": self.face_limited_front,
                "face_limited_back": self.face_limited_back,
                "lead_angle_parallel": self.lead_angle_parallel,
                "lead_angle": self.lead_angle,
                "lead_inclination_parallel": self.lead_inclination_parallel,
                "lead_inclination": self.lead_inclination,
                "rafter_nail_hole": self.rafter_nail_hole,
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
    def from_planes_and_beam(cls, planes, beam, **kwargs):
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

        line = Line(*ln)
        _, face_intersections = intersection_line_beam_param(line, beam)
        if not len(face_intersections) == 2:
            raise ValueError("Planes do not intersect with beam.")
        print(f"face_intersections = {face_intersections}")

        face_indices = list(face_intersections.keys())
        if not all([i < 4 for i in face_indices]):
            raise ValueError("the planes' intersection line must not pass through end faces of the beam")
        if not abs(face_indices[0]-face_indices[1])==2:
            raise ValueError(f"the planes' intersection line must pass through opposite faces of the beam. intersection params are {face_intersections}")
        for rsi in range(4):  # find the ref_side between intersected faces
            if rsi in face_indices: # face is one of intersected faces, skip
                continue 
            ref_face_normal = beam.ref_sides[rsi].normal
            for plane in planes:
                cp = closest_point_on_line(plane.point, line)
                # use the position of the plane.point relative to intersection line. point should be towards the ref_face
                if dot_vectors(ref_face_normal, Vector.from_start_end(cp, plane.point)) < 0:
                    #plane.point on the wrong side of line, go to next ref_side
                    break
            else: #both dot vectors positive
                print(f"found rsi of {rsi}")
                ref_side_index = rsi
                break

        if ref_side_index is None:
            raise ValueError("ref_side_index could not be identified")

        ref_side = beam.ref_sides[ref_side_index]


        for plane in planes:
            if dot_vectors(plane.normal,ref_side.normal) < 0:
                plane = Plane(plane.point, -plane.normal)

        if dot_vectors(line.direction, ref_side.yaxis)<0:
            line=Line(line[1],line[0])


        planes = cls._reorder_planes(planes, beam.ref_edges[ref_side_index])        
        start_x = face_intersections[(ref_side_index + 1) % 4][0]
        start_depth = beam.get_dimensions_relative_to_side(ref_side_index)[0] - face_intersections[(ref_side_index + 1) % 4][1]
        depth = face_intersections[(ref_side_index - 1) % 4][1]
        angle = cls._calculate_angle(ref_side, line)
        incl_1, incl_2 = cls._calculate_inclination(planes, line, beam.frame.xaxis)

        print(f"START_DEPTH = {start_depth}")
        return cls(
            ref_side_index = ref_side_index,
            orientation=OrientationType.START,
            start_x=start_x,
            start_y=0.0,
            start_depth=start_depth,
            angle=angle,
            inclination1=incl_1,
            inclination2=incl_2,
            depth=depth,
            width=beam.get_dimensions_relative_to_side(ref_side_index)[1],
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
        )

    @staticmethod
    def _reorder_planes(planes, ref_edge):
        # Stable sort by the projection of each plane's point onto the beam x axis
        def keyfn(plane):
            pt = intersection_line_plane(ref_edge, plane)
            vec = Vector.from_start_end(ref_edge.end, pt)
            return dot_vectors(-ref_edge.direction, vec)

        return sorted(planes, key=keyfn)

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
    def _calculate_angle(ref_side, intersection_line):
        line = intersection_line.transformed(Transformation.from_frame(ref_side).inverse())
        #project to XY by setting z value to 0
        line[0][2] = 0.0
        line[1][2] = 0.0
        return angle_vectors(-Vector(1,0,0),line.direction, deg=True) 

    @staticmethod
    def _calculate_inclination(planes, plane_intersection, xaxis):
        inclinations = []
        ref_vector = cross_vectors(plane_intersection.direction,xaxis)
        for plane in planes:
            inclination = angle_vectors(ref_vector, plane.normal, deg=True)
            inclinations.append(inclination)
        inclinations[1] = 180.0 - inclinations[1]
        return inclinations

    def planes_from_params_and_beam(self, beam):
        ref_side = beam.ref_sides[self.ref_side_index]
        ref_srf = beam.side_as_surface(self.ref_side_index)
        start_pt = planar_surface_point_at(ref_srf, self.start_x,self.start_y)
        vector = beam.centerline.direction
        vector.transform(Rotation.from_axis_and_angle(ref_side.normal, (180-self.angle)*math.pi/180, point=start_pt))
        distance = self.width/math.sin(self.angle)
        end_pt = start_pt + (vector*distance)
        start_pt += -ref_side.normal*self.start_depth
        end_pt += -ref_side.normal*self.depth
        base_plane = Plane(start_pt, cross_vectors(end_pt-start_pt, beam.centerline.direction))
        plane_a = base_plane.transformed(Rotation.from_axis_and_angle(end_pt-start_pt, (180-self.inclination1)*math.pi/180, point=start_pt))
        plane_b = base_plane.transformed(Rotation.from_axis_and_angle(end_pt-start_pt, (180-self.inclination2)*math.pi/180, point=start_pt))
        plane_a = Plane(plane_a.point, -plane_a.normal)
        print(self.__data__)

        print(f"pts = {[start_pt,end_pt]}")
        return start_pt, end_pt, [plane_a,plane_b]

    

    def apply(self, geometry, beam):
        try:
            _,_,planes = self.planes_from_params_and_beam(beam)
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
        result["WidthCounterPartLimited"] = "yes" if inst.width_counterpart_limited else "no"
        result["WidthCounterPart"] = "{:.{prec}f}".format(float(inst.width_counterpart), prec=TOL.precision)
        result["HeightCounterPartLimited"] ="yes" if inst.height_counterpart_limited else "no"
        result["HeightCounterPart"] = "{:.{prec}f}".format(float(inst.height_counterpart), prec=TOL.precision)
        result["FaceLimitedFront"] = "yes" if inst.face_limited_front else "no"
        result["FaceLimitedBack"] = "yes" if inst.face_limited_back else "no"
        result["LeadAngleParallel"] = "yes" if inst.lead_angle_parallel else "no"
        result["LeadAngle"] = "{:.{prec}f}".format(float(inst.lead_angle), prec=TOL.precision)
        result["LeadInclinationParallel"] = "yes" if inst.lead_inclination_parallel else "no"
        result["LeadInclination"] = "{:.{prec}f}".format(float(inst.lead_inclination), prec=TOL.precision)
        result["RafterNailHole"] = "yes" if inst.rafter_nail_hole else "no"
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
            self._processing = Birdsmouth.from_planes_and_beam(planes, self.element)
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
