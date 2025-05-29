import math
from collections import OrderedDict

from compas.geometry import Brep
from compas.geometry import Cylinder
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import angle_vectors_signed
from compas.geometry import distance_point_plane
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_segment_plane
from compas.geometry import is_point_behind_plane
from compas.geometry import is_point_in_polyhedron
from compas.geometry import project_point_plane
from compas.tolerance import TOL

from compas_timber.errors import FeatureApplicationError

from .btlx import BTLxProcessing
from .btlx import BTLxProcessingParams


class Drilling(BTLxProcessing):
    """Represents a drilling processing.

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

    PROCESSING_NAME = "Drilling"  # type: ignore

    def __init__(self, start_x=0.0, start_y=0.0, angle=0.0, inclination=90.0, depth_limited=False, depth=50.0, diameter=20.0, **kwargs):
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
    def params(self):
        return DrillingParams(self)

    @property
    def start_x(self):
        return self._start_x

    @start_x.setter
    def start_x(self, value):
        if -100000 <= value <= 100000:
            self._start_x = value
        else:
            raise ValueError("Start x-coordinate should be between -100000 and 100000. Got: {}".format(value))

    @property
    def start_y(self):
        return self._start_y

    @start_y.setter
    def start_y(self, value):
        if -50000 <= value <= 50000:
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
        if 0.0 <= value <= 50000.0:
            self._depth = value
        else:
            raise ValueError("Depth should be between 0 and 50000. Got: {}".format(value))

    @property
    def diameter(self):
        return self._diameter

    @diameter.setter
    def diameter(self, value):
        if 0.0 <= value <= 50000.0:
            self._diameter = value
        else:
            raise ValueError("Diameter should be between 0 and 50000. Got: {}".format(value))

    ########################################################################
    # Alternative constructors
    ########################################################################

    @classmethod
    def from_line_and_element(cls, line, element, diameter):
        """Construct a drilling process from a line and diameter.

        # TODO: change this to point + vector instead of line. line is too fragile, it can be flipped and cause issues.
        # TODO: make a from point alt. constructor that takes a point and a reference side and makes a straight drilling through.

        Parameters
        ----------
        line : :class:`compas.geometry.Line`
            The line on which the drilling is to be made.
        element : :class:`compas_timber.elements.Element`
            The element to drill.
        diameter : float
            The diameter of the drilling.

        Returns
        -------
        :class:`compas_timber.fabrication.Drilling`
            The constructed drilling processing.

        """
        ref_side_index, xy_point = cls._calculate_ref_side_index(line, element)
        line = cls._flip_line_if_start_inside(line, element, ref_side_index)
        depth_limited = cls._is_depth_limited(line, element)
        ref_surface = element.side_as_surface(ref_side_index)
        depth = cls._calculate_depth(line, ref_surface) if depth_limited else 0.0
        x_start, y_start = cls._xy_to_ref_side_space(xy_point, ref_surface)
        angle = cls._calculate_angle(ref_surface, line, xy_point)
        inclination = cls._calculate_inclination(ref_surface.frame, line, angle, xy_point)
        try:
            return cls(x_start, y_start, angle, inclination, depth_limited, depth, diameter, ref_side_index=ref_side_index)
        except ValueError as e:
            raise FeatureApplicationError(
                message=str(e),
                feature_geometry=line,
                element_geometry=element.blank,
            )

    @classmethod
    def from_shapes_and_element(cls, line, element, diameter, **kwargs):
        """Construct a drilling process from a line, element and diameter.

        Parameters
        ----------
        line : :class:`compas.geometry.Line`
            The line on which the drilling is to be made.
        element : :class:`compas_timber.elements.Element`
            The element to drill.
        diameter : float
            The diameter of the drilling.

        Returns
        -------
        :class:`compas_timber.fabrication.Drilling`
            The constructed drilling process.

        """
        if isinstance(line, list):
            line = line[0]
        return cls.from_line_and_element(line, element, float(diameter), **kwargs)

    @staticmethod
    def _flip_line_if_start_inside(line, element, ref_side_index):
        side_plane = element.side_as_surface(ref_side_index).to_plane()
        if is_point_behind_plane(line.start, side_plane):
            return Line(line.end, line.start)  # TODO: use line.flip() instead
        return line

    @staticmethod
    def _calculate_ref_side_index(line, element):
        # TODO: this can also be done with compas_timber.utils.intersection_line_box_param() instead
        # TODO: upstream this to compas.geometry
        def is_point_on_surface(point, surface):
            point = Point(*point)
            local_point = point.transformed(Transformation.from_change_of_basis(Frame.worldXY(), surface.frame))
            return 0.0 <= local_point.x <= surface.xsize and 0.0 <= local_point.y <= surface.ysize

        intersections = {}
        for index, side in enumerate(element.ref_sides):
            intersection = intersection_segment_plane(line, Plane.from_frame(side))
            if intersection is not None and is_point_on_surface(intersection, element.side_as_surface(index)):
                intersections[index] = Point(*intersection)

        if not intersections:
            raise FeatureApplicationError(
                message="The drill line must intersect with at lease one of the element's reference sides.",
                feature_geometry=line,
                element_geometry=element.blank,
            )

        ref_side_index = min(intersections, key=lambda i: intersections[i].distance_to_point(line.start))
        return ref_side_index, intersections[ref_side_index]

    @staticmethod
    def _is_depth_limited(line, element):
        # check if the end point of the line is within the element
        # if it is, return True
        # otherwise, return False
        return is_point_in_polyhedron(line.end, element.blank.to_polyhedron())

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
    def _calculate_inclination(ref_side, line, angle, xy_point):
        # type: (Frame, Line, float, Point) -> float
        # inclination is the rotation around `ref_side.yaxis` between the `ref_side.xaxis` and the line vector
        # we need a reference frame because the rotation axis is not the standard y-axis, but the one rotated by the angle
        ref_frame = Frame(xy_point, -ref_side.xaxis, -ref_side.yaxis)
        ref_frame.rotate(math.radians(angle), -ref_side.zaxis, point=xy_point)
        return angle_vectors_signed(ref_frame.xaxis, line.vector, ref_frame.yaxis, deg=True)

    @staticmethod
    def _calculate_depth(line, ref_surface):
        return distance_point_plane(line.end, Plane.from_frame(ref_surface.frame))

    ########################################################################
    # Methods
    ########################################################################

    def apply(self, geometry, element):
        """Apply the feature to the element geometry.

        Raises
        ------
        :class:`compas_timber.errors.FeatureApplicationError`
            If the cutting plane does not intersect with the element geometry.

        Returns
        -------
        :class:`compas.geometry.Brep`
            The resulting geometry after processing.

        """
        drill_geometry = Brep.from_cylinder(self.cylinder_from_params_and_element(element))
        try:
            return geometry - drill_geometry
        except IndexError:
            raise FeatureApplicationError(
                drill_geometry,
                geometry,
                "The drill geometry does not intersect with element geometry.",
            )

    def cylinder_from_params_and_element(self, element):
        """Construct the geometry of the drilling using the parameters in this instance and the element object.

        Parameters
        ----------
        element : :class:`compas_timber.elements.Element`
            The element to drill.

        Returns
        -------
        :class:`compas.geometry.Cylinder`
            The constructed cylinder.

        """
        assert self.diameter is not None
        assert self.angle is not None
        assert self.inclination is not None
        assert self.depth is not None

        ref_surface = element.side_as_surface(self.ref_side_index)
        xy_world = ref_surface.point_at(self.start_x, self.start_y)

        # x and y flipped because we want z pointting down into the element, that'll be the cylinder long direction
        cylinder_frame = Frame(xy_world, ref_surface.zaxis, -ref_surface.yaxis)
        cylinder_frame.rotate(math.radians(self.angle), -ref_surface.zaxis, point=xy_world)
        cylinder_frame.rotate(math.radians(self.inclination), cylinder_frame.yaxis, point=xy_world)

        drill_line = self._calculate_drill_line(element, xy_world, cylinder_frame)

        # scale both ends so is protrudes nicely from the surface
        # TODO: this is a best-effort solution. this can be done more accurately taking the angle into account. consider doing that in the future.
        drill_line = self._scaled_line_by_factor(drill_line, 1.2)
        return Cylinder.from_line_and_radius(drill_line, self.diameter * 0.5)

    def _scaled_line_by_factor(self, line, factor):
        direction = line.vector.unitized()
        scale_factor = line.length * 0.5 * factor
        start = line.midpoint - direction * scale_factor
        end = line.midpoint + direction * scale_factor
        return Line(start, end)

    def _calculate_drill_line(self, element, xy_world, cylinder_frame):
        drill_line_direction = Line.from_point_and_vector(xy_world, cylinder_frame.zaxis)
        if self.depth_limited:
            drill_bottom_plane = element.side_as_surface(self.ref_side_index).to_plane()
            drill_bottom_plane.point -= drill_bottom_plane.normal * self.depth
        else:
            # this is not always the correct plane, but it's good enough for now, btlx viewer seems to be using the same method..
            # TODO: this is a best-effort solution. consider calculating intersection with other sides to always find the right one.
            drill_bottom_plane = Plane.from_frame(element.opp_side(self.ref_side_index))

        intersection_point = intersection_line_plane(drill_line_direction, drill_bottom_plane)
        assert intersection_point  # if this fails, it means space and time as we know it has collapsed
        return Line(xy_world, intersection_point)


class DrillingParams(BTLxProcessingParams):
    def __init__(self, instance):
        super(DrillingParams, self).__init__(instance)

    def as_dict(self):
        result = OrderedDict()
        result["StartX"] = "{:.{prec}f}".format(float(self._instance.start_x), prec=TOL.precision)
        result["StartY"] = "{:.{prec}f}".format(float(self._instance.start_y), prec=TOL.precision)
        result["Angle"] = "{:.{prec}f}".format(float(self._instance.angle), prec=TOL.precision)
        result["Inclination"] = "{:.{prec}f}".format(float(self._instance.inclination), prec=TOL.precision)
        result["DepthLimited"] = "yes" if self._instance.depth_limited else "no"
        result["Depth"] = "{:.{prec}f}".format(float(self._instance.depth), prec=TOL.precision)
        result["Diameter"] = "{:.{prec}f}".format(float(self._instance.diameter), prec=TOL.precision)
        return result
