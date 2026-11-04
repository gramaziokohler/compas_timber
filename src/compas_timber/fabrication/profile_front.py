import math

from compas.geometry import Line
from compas.geometry import Point
from compas.geometry import Scale
from compas.geometry import Transformation
from compas.geometry import Translation
from compas.tolerance import TOL
from compas_brep import Brep
from compas_brep.curves import NurbsCurve
from compas_brep.errors import BrepError

from .btlx import AttributeSpec
from .btlx import OrientationType
from .btlx import ParametricProcessing


class ArcShapeType(object):
    """Enum for the shape of an arc of a profile.

    Attributes
    ----------
    CONVEX : literal("convex")
        The arc bulges towards the reference side, the material is on the inside of the arc.
    CONCAVE : literal("concave")
        The arc bulges into the material.
    """

    CONVEX = "convex"
    CONCAVE = "concave"


class PremillType(object):
    """Enum for how a profile curve is connected to the reference side.

    Attributes
    ----------
    ROUND : literal("round")
        A wall perpendicular to the reference side.
    ANGULAR : literal("angular")
        A straight line normal to the profile curve.
    """

    ROUND = "round"
    ANGULAR = "angular"


def arc_curves(center, radius, start_angle, sweep):
    """Creates an exact circular arc in the XZ plane, with one rational Bezier curve per quadrant.

    Parameters
    ----------
    center : :class:`~compas.geometry.Point`
        The center of the arc.
    radius : float
        The radius of the arc.
    start_angle : float
        The angle of the start of the arc, in radians, from X towards Z.
    sweep : float
        The signed angle of the arc, in radians. Positive turns from X towards Z.

    Returns
    -------
    list(:class:`~compas_brep.curves.NurbsCurve`)
        The curves. Empty if the arc has no length.

    """
    if TOL.is_zero(radius * sweep):
        return []
    count = int(math.ceil(abs(sweep) / (math.pi / 2.0) - 1e-9))
    step = sweep / count
    weight = math.cos(step / 2.0)

    def on_arc(angle, distance):
        return Point(center.x + distance * math.cos(angle), 0.0, center.z + distance * math.sin(angle))

    curves = []
    for index in range(count):
        angle = start_angle + index * step
        points = [on_arc(angle, radius), on_arc(angle + step / 2.0, radius / weight), on_arc(angle + step, radius)]
        curves.append(NurbsCurve.from_parameters(points, [1.0, weight, 1.0], [0.0, 1.0], [3, 3], 2))
    return curves


def segment_curves(start, end, camber):
    """Creates the circular arc between two points in the XZ plane.

    Parameters
    ----------
    start : :class:`~compas.geometry.Point`
        The start of the arc.
    end : :class:`~compas.geometry.Point`
        The end of the arc.
    camber : float
        The height of the arc above its chord. Positive bulges to the left of the direction of travel, with X to the right and Z up.

    Returns
    -------
    list(:class:`~compas.geometry.Line` or :class:`~compas_brep.curves.NurbsCurve`)
        The curves. A line if there is no camber, and empty if the points coincide.

    """
    chord = start.distance_to_point(end)
    if TOL.is_zero(camber) or TOL.is_zero(chord):
        return polyline_curves([start, end])
    radius = (chord**2 / 4.0 + camber**2) / (2.0 * abs(camber))
    normal_x, normal_z = (start.z - end.z) / chord, (end.x - start.x) / chord
    offset = camber - math.copysign(radius, camber)
    center = Point((start.x + end.x) / 2.0 + offset * normal_x, 0.0, (start.z + end.z) / 2.0 + offset * normal_z)
    return arc_curves(center, radius, math.atan2(start.z - center.z, start.x - center.x), -4.0 * math.atan(2.0 * camber / chord))


def polyline_curves(points):
    """Creates the lines between consecutive points, leaving out those of no length."""
    return [Line(a, b) for a, b in zip(points, points[1:]) if not TOL.is_zero(a.distance_to_point(b))]


def exit_point(point, direction, height):
    """Returns the point at the given height of the straight line through ``point``. A horizontal direction becomes a vertical one, as it would never get there.

    Parameters
    ----------
    point : :class:`~compas.geometry.Point`
        The point in the XZ plane.
    direction : tuple(float, float)
        The X and Z components of the direction of the line.
    height : float
        The Z of the returned point.

    Returns
    -------
    :class:`~compas.geometry.Point`

    """
    x, z = direction
    if TOL.is_zero(z):
        return Point(point.x, 0.0, height)
    return Point(point.x + (height - point.z) * x / z, 0.0, height)


def element_size(element):
    """Returns a distance by which volumes clear the element, whichever way the reference side is facing."""
    return element.blank_length + element.width + element.height


def closed_towards_head(curves, start_x, element):
    """Closes a chain of curves around the side of the element's reference side and of the end the profile's orientation points to.

    Parameters
    ----------
    curves : list(:class:`~compas.geometry.Line` or :class:`~compas_brep.curves.NurbsCurve`)
        The chain of curves, running away from the head of the element.
    start_x : float
        The StartX of the processing.
    element : :class:`~compas_timber.base.TimberElement`
        The element the processing is applied to.

    Returns
    -------
    list(:class:`~compas.geometry.Line` or :class:`~compas_brep.curves.NurbsCurve`)
        The closed loop.

    """
    size = element_size(element)
    points = [point for curve in curves for point in (curve.points if isinstance(curve, NurbsCurve) else (curve.start, curve.end))]
    first, last = points[0], points[-1]
    top = max([0.0] + [point.z for point in points]) + size
    x = min(first.x, -abs(start_x) - 2.0 * size) - size
    return curves + polyline_curves([last, Point(last.x, 0.0, top), Point(x, 0.0, top), Point(x, 0.0, first.z), first])


def extruded_volume(curves, start_x, element, ref_side_index, orientation=OrientationType.START):
    """Extrudes a closed profile through the element.

    Parameters
    ----------
    curves : list(:class:`~compas.geometry.Line` or :class:`~compas_brep.curves.NurbsCurve`)
        The closed loop of curves in the XZ plane. Z is the normal of the reference side and X runs from `start_x` in the direction of the profile.
    start_x : float
        The StartX of the processing.
    element : :class:`~compas_timber.base.TimberElement`
        The element the processing is applied to.
    ref_side_index : int
        The index of the reference side.
    orientation : str, optional
        If `end`, the profile runs towards the start of the element.

    Returns
    -------
    :class:`~compas_brep.Brep`
        The volume, in model coordinates.

    """
    size = element_size(element)
    ref_side = element.ref_sides[ref_side_index]
    transformation = Transformation.from_frame(ref_side) * Translation.from_vector([start_x, -size, 0.0])
    if orientation == OrientationType.END:
        transformation = transformation * Scale.from_factors([-1.0, 1.0, 1.0])
    # shortcut: the Rhino backend of `from_extrusion` takes no BrepFace, the only exact curved profile OCC takes, upgrade when compas_brep has a common one
    try:
        face = Brep.from_curves([curve.transformed(transformation) for curve in curves]).faces[0]
        return Brep.from_extrusion(face, ref_side.yaxis * 3.0 * size)
    except BrepError as error:
        raise ValueError("The profile does not enclose a volume: {}".format(error))


class ProfileFront(ParametricProcessing):
    """Represents a Profile Front feature to be made on a beam: a profile of one or two tangent arcs, extruded across the reference side.

    The profile lies in the plane of the X-axis and the normal of the reference side, and is cut through the whole element.
    Everything between the profile and the end the orientation names, on the side of the reference side, is removed.

    Parameters
    ----------
    orientation : str
        The end of the element the profile faces. One of :class:`~compas_timber.fabrication.OrientationType`.
    start_x : float
        Distance from the start of the reference side to the point of the first arc's circle which is furthest towards the end of the element, along X.
    arc_shape : str
        `convex` if the first arc bulges towards the reference side and the second arc into the material, `concave` for the opposite.
    depth : float
        Distance from the reference side to the first arc's circle.
    start_rotation : float
        Angle, in degrees, on the first arc's circle between the point at `start_x` and the start of the arc.
        The profile continues from the start of the arc towards the end of the element along the radius of the circle.
    rotation1 : float
        Angle of the first arc, in degrees.
    radius1 : float
        Radius of the first arc.
    rotation2 : float
        Angle of the second arc, in degrees.
    radius2 : float
        Radius of the second arc. Without second arc the profile continues to the reference side along the radius of the first arc.

    """

    PROCESSING_NAME = "ProfileFront"  # type: ignore
    ATTRIBUTE_MAP = {
        "Orientation": AttributeSpec("orientation", str, OrientationType.START, choices=(OrientationType.START, OrientationType.END)),
        "StartX": AttributeSpec("start_x", float, 0.0, (-100000.0, 100000.0), scales=True),
        "ArcShape": AttributeSpec("arc_shape", str, ArcShapeType.CONVEX, choices=(ArcShapeType.CONVEX, ArcShapeType.CONCAVE)),
        "Depth": AttributeSpec("depth", float, 0.0, (0.0, 1000.0), scales=True),
        "StartRotation": AttributeSpec("start_rotation", float, 0.0, (-90.0, 90.0)),
        "Rotation1": AttributeSpec("rotation1", float, 90.0, (0.0, 180.0)),
        "Radius1": AttributeSpec("radius1", float, 250.0, (0.0, 1000.0), scales=True),
        "Rotation2": AttributeSpec("rotation2", float, 90.0, (0.0, 180.0)),
        "Radius2": AttributeSpec("radius2", float, 250.0, (0.0, 1000.0), scales=True),
    }

    def volumes_from_params_and_element(self, element):
        """The volume above the profile and towards the end of the element.

        The figures of the specification only show `convex`. `concave` swaps the curvature of both arcs and keeps the point at `start_x`
        and `depth`, as in the classical cyma reversa and recta: the first arc's center moves from beside this point to above it.

        Parameters
        ----------
        element : :class:`~compas_timber.base.TimberElement`
            The element this processing is applied to.

        Raises
        ------
        ValueError
            If the profile has no arc.

        Returns
        -------
        list(:class:`~compas_brep.Brep`)
            The volume, in model coordinates.

        """
        convex = self.arc_shape == ArcShapeType.CONVEX
        turn = -1.0 if convex else 1.0  # the sense of the first arc
        rotation1, rotation2 = math.radians(self.rotation1), math.radians(self.rotation2)

        z = -self.depth - self.radius1
        center1 = Point(self.radius1, 0.0, z) if convex else Point(0.0, 0.0, z + self.radius1)
        angle1 = (math.pi if convex else -math.pi / 2.0) + turn * math.radians(self.start_rotation)
        angle2 = angle1 + turn * rotation1
        angle3 = angle2 + math.pi - turn * rotation2

        def radial(angle):
            return math.cos(angle), math.sin(angle)

        def on_circle(center, radius, angle):
            return Point(center.x + radius * math.cos(angle), 0.0, center.z + radius * math.sin(angle))

        arc1 = arc_curves(center1, self.radius1, angle1, turn * rotation1)
        center2 = on_circle(center1, self.radius1 + self.radius2, angle2)
        arc2 = arc_curves(center2, self.radius2, angle2 + math.pi, -turn * rotation2)
        if not arc1 and not arc2:
            raise ValueError("The profile has no arc: both arcs have no radius or no rotation.")

        size = element_size(element)
        start = on_circle(center1, self.radius1, angle1)
        reach = 2.0 * (abs(self.start_x) + 2.0 * size - start.z)
        first = on_circle(center1, self.radius1 + reach, angle1)

        end, angle, sense = (on_circle(center2, self.radius2, angle3), angle3, -turn) if arc2 else (on_circle(center1, self.radius1, angle2), angle2, turn)
        # the figure continues along the radius, which would undercut an arc curving away from the material while it is rising
        direction = radial(angle)
        if sense > 0.0 and math.cos(angle) > 0.0:
            direction = (-math.sin(angle), math.cos(angle))
        outside = exit_point(end, direction, max(end.z, 0.0) + size)

        curves = polyline_curves([first, start]) + arc1 + arc2 + polyline_curves([end, outside])
        return [extruded_volume(closed_towards_head(curves, self.start_x, element), self.start_x, element, self.ref_side_index, self.orientation)]
