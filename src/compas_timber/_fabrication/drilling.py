from compas.geometry import intersection_segment_plane
from compas.geometry import is_point_in_polyhedron
from compas.geometry import distance_point_plane
from compas.geometry import angle_vectors_signed
from compas.geometry import project_point_plane
from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Plane
from compas.geometry import PlanarSurface
from compas.geometry import Point
from compas.geometry import Line
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.tolerance import TOL

from compas_timber.elements import FeatureApplicationError

from .btlx_process import BTLxProcess
from .btlx_process import BTLxProcessParams


class Drilling(BTLxProcess):
    """Represents a drilling process.

    Parameters
    ----------
    start_x : float
        The x-coordinate of the start point of the drilling. In the local coordinate system of the reference side.
    start_y : float
        The y-coordinate of the start point of the drilling. In the local coordinate system of the reference side.
    angle : float
        The rotation angle of the drilling. In degrees. Around the z-axis of the reference side.
    inclination : float
        The inclination angle of the drilling. In degrees. Around the y-axis of the reference side.
    depth_limited : bool, default True
        If True, the drilling depth is limited to `depth`. Otherwise, drilling will go through the element.
    depth : float, default 50.0
        The depth of the drilling. In mm.
    diameter : float, default 20.0
        The diameter of the drilling. In mm.
    """

    # TODO: add __data__

    PROCESS_NAME = "Drilling"  # type: ignore

    def __init__(
        self,
        start_x=0.0,
        start_y=0.0,
        angle=0.0,
        inclination=90.0,
        depth_limited=False,
        depth=50.0,
        diameter=20.0,
        **kwargs,
    ):
        super(Drilling, self).__init__(**kwargs)
        self._start_x = None
        self._start_y = None
        self._angle = None
        self._inclination = None
        self._depth_limited = None
        self._depth = None
        self._diameter = None

        self.start_x = start_x
        self.start_y = start_y
        self.angle = angle
        self.inclination = inclination
        self.depth_limited = depth_limited
        self.depth = depth
        self.diameter = diameter

    ########################################################################
    # Properties
    ########################################################################

    @property
    def params_dict(self):
        return DrillingParams(self).as_dict()

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, value):
        if -100_000 <= value <= 100_000:
            self._start_x = value
        else:
            raise ValueError("Start x-coordinate should be between -100000 and 100000. Got: {}".format(value))

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, value):
        if -50_000 <= value <= 50_000:
            self._start_y = value
        else:
            raise ValueError("Start y-coordinate should be between -50000 and 50000. Got: {}".format(value))

    @property
    def angle(self):
        return self._angle

    @angle.setter
    def angle(self, value):
        if 0.0 <= value <= 360.0:
            self._angle = value
        else:
            raise ValueError("Angle should be between 0 and 360. Got: {}".format(value))

    @property
    def inclination(self):
        return self._inclination

    @inclination.setter
    def inclination(self, value):
        if 0.1 <= value <= 179.0:
            self._inclination = value
        else:
            raise ValueError("Inclination should be between 0 and 180. Got: {}".format(value))

    @property
    def depth_limited(self):
        return self._depth_limited

    @depth_limited.setter
    def depth_limited(self, value):
        self._depth_limited = value

    @property
    def depth(self):
        return self._depth

    @depth.setter
    def depth(self, value):
        if 0.0 <= value <= 50_000.0:
            self._depth = value
        else:
            raise ValueError("Depth should be between 0 and 50000. Got: {}".format(value))

    @property
    def diameter(self):
        return self._diameter

    @diameter.setter
    def diameter(self, value):
        if 0.0 <= value <= 50_000.0:
            self._diameter = value
        else:
            raise ValueError("Diameter should be between 0 and 50000. Got: {}".format(value))

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_line_and_beam(cls, line, diameter, beam):
        """Construct a drilling process from a line and diameter.

        # TODO: change this to point + vector instead of line. line is too fragile, it can be flipped and cause issues.
        # TODO: make a from point alt. constructor that takes a point and a reference side and makes a straight drilling through.

        Parameters
        ----------
        line : :class:`compas.geometry.Line`
            The line on which the drilling is to be made.
        diameter : float
            The diameter of the drilling.
        length : float
            The length (depth?) of the drilling.
        beam : :class:`compas_timber.elements.Beam`
            The beam to drill.

        Returns
        -------
        :class:`compas_timber.fabrication.Drilling`
            The constructed drilling process.

        """
        # find intersection point between line and beam
        # if there are several, take the closest one to the start point of the line
        # calculate the reference side index based on the closest intersection point
        # check if the end point of the line is within the beam
        # if it is, the drilling is depth limited otherwise it is not
        # calculate the x and y coordinates of the start point of the drilling
        # based on the intersection point and the reference side index
        # create frame using the intersection point and the reference side axes
        # calculate the angle and inclination of the drilling using the frame and line
        # create the drilling process using the calculated parameters
        ref_side_index, xy_point = cls._calculate_ref_side_index(line, beam)
        print(f"ref_side_index: {ref_side_index}, xy_point: {xy_point}")
        depth_limited = cls._is_depth_limited(line, beam)
        ref_surface = beam.side_as_surface(ref_side_index)
        depth = cls._calculate_depth(line, ref_surface) if depth_limited else 0.0
        x_start, y_start = cls._xy_to_ref_side_space(xy_point, ref_surface)
        angle = cls._calculate_angle(ref_surface, line, xy_point)
        inclination = cls._calculate_inclination(ref_surface.frame, line)
        return cls(x_start, y_start, angle, inclination, depth_limited, depth, diameter, ref_side_index=ref_side_index)

    @staticmethod
    def _calculate_ref_side_index(line, beam):
        # calculate the reference side index based on the closest intersection point between the line and the beam
        # IDEA: calculate intersection point between line and each of the reference sides of the beam
        # take the one with the smallest distance to the start point of the line
        # return the index of the reference side
        def is_point_on_surface(point, surface):
            point = Point(*point)
            local_point = point.transformed(Transformation.from_change_of_basis(Frame.worldXY(), surface.frame))
            return 0.0 <= local_point.x <= surface.xsize and 0.0 <= local_point.y <= surface.ysize

        intersections = {}
        for index, side in enumerate(beam.ref_sides):
            intersection = intersection_segment_plane(line, Plane.from_frame(side))
            if intersection is not None and is_point_on_surface(intersection, beam.side_as_surface(index)):
                print(f"intersection found: {intersection}")
                intersections[index] = Point(*intersection)

        if not intersections:
            raise ValueError("The line does not intersect with the beam geometry.")

        ref_side_index = min(intersections, key=lambda i: intersections[i].distance_to_point(line.start))
        return ref_side_index, intersections[ref_side_index]

    @staticmethod
    def _is_depth_limited(line, beam):
        # check if the end point of the line is within the beam
        # if it is, return True
        # otherwise, return False
        return is_point_in_polyhedron(line.end, beam.blank.to_polyhedron())

    @staticmethod
    def _xy_to_ref_side_space(point, ref_surface):
        # type: (Point, PlanSurface) -> Tuple[float, float]
        # calculate the x and y coordinates of the start point of the drilling
        # based on the intersection point and the reference side index
        vec_to_intersection = Vector.from_start_end(ref_surface.frame.point, point)

        # from global to surface local space
        vec_to_intersection.transform(Transformation.from_change_of_basis(Frame.worldXY(), ref_surface.frame))
        return vec_to_intersection.x, vec_to_intersection.y

    @staticmethod
    def _calculate_angle(ref_surface, line, intersection):
        # type: (PlanarSurface, Line, Point) -> float
        # this the angle between the direction projected by the drill line onto the reference plane and the reference side x-axis
        vector_end_point = project_point_plane(line.end, ref_surface.to_plane())
        drill_horizontal_vector = Vector.from_start_end(intersection, vector_end_point)
        reference_vector = -ref_surface.xaxis  # angle = 0 when the drill is parallel to -x axis
        measurement_axis = -ref_surface.zaxis  # measure clockwise around the z-axis (sign flips the direction)
        angle = angle_vectors_signed(reference_vector, drill_horizontal_vector, measurement_axis, deg=True)

        # angle goes between -180 and 180 but we need it between 0 and 360
        if angle < 0:
            angle += 360

        return angle

    @staticmethod
    def _calculate_inclination(ref_side, line):
        # type: (Frame, Line) -> float
        # inclination is the rotation around `ref_side.yaxis` between the `ref_side.xaxis` and the line vector
        angle = angle_vectors_signed(ref_side.xaxis, line.vector, ref_side.yaxis, deg=True)
        return 180 - abs(angle)

    @staticmethod
    def _calculate_depth(line, ref_surface):
        return distance_point_plane(line.end, Plane.from_frame(ref_surface.frame))

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, beam):
        """Apply the feature to the beam geometry.

        Raises
        ------
        :class:`compas_timber.elements.FeatureApplicationError`
            If the cutting plane does not intersect with the beam geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        drill_geometry = Brep.from_cylinder(self.cylinder_from_params_and_beam(beam))
        try:
            return geometry - drill_geometry
        except IndexError:
            raise FeatureApplicationError(
                drill_geometry,
                geometry,
                "The drill geometry does not intersect with beam geometry.",
            )

    def cylinder_from_params_and_beam(self, beam):
        """Construct the geometry of the drilling using the parameters in this instance and the beam object.

        Parameters
        ----------
        beam : :class:`compas_timber.elements.Beam`
            The beam to drill.

        Returns
        -------
        :class:`compas.geometry.Cylinder`
            The constructed cylinder.

        """
        # convert xy to global space
        # create frame using the start point and the reference side axes
        # rotate the frame around the z-axis by the angle
        # rotate the frame around the y-axis by the inclination
        # create the cylinder using the frame and the diameter and depth
        assert self.diameter is not None

        ref_surface = beam.side_as_surface(self.ref_side_index)
        xy_world = ref_surface.point_at(self.start_x, self.start_y)
        frame = Frame(xy_world, ref_surface.frame.xaxis, ref_surface.frame.yaxis)
        frame.rotate(self.angle, frame.zaxis)
        frame.rotate(self.inclination, frame.yaxis)
        return Cylinder(frame=frame, radius=self.diameter / 2.0, height=self.depth)


class DrillingParams(BTLxProcessParams):
    def __init__(self, instance):
        super(DrillingParams, self).__init__(instance)

    def as_dict(self):
        result = super(DrillingParams, self).as_dict()
        result["StartX"] = "{:.{prec}f}".format(self._instance.start_x, prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(self._instance.start_y, prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(self._instance.angle, prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(self._instance.inclination, prec=TOL.precision)
        result["DepthLimited"] = "yes" if self._instance.depth_limited else "no"
        result["Depth"] = "{:.{prec}f}".format(self._instance.depth, prec=TOL.precision)
        result["Diameter"] = "{:.{prec}f}".format(self._instance.diameter, prec=TOL.precision)
        return result
