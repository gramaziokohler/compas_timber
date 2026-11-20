import math

from compas.geometry import Line
from compas.geometry import Plane
from compas.geometry import Point
from compas.geometry import Polyline
from compas.geometry import Transformation
from compas.geometry import Vector
from compas.geometry import intersection_line_plane
from compas.geometry import intersection_plane_plane_plane
from compas_brep.curves import NurbsCurve

from compas_timber.errors import BeamJoiningError
from compas_timber.fabrication import FreeContour
from compas_timber.fabrication import JackRafterCutProxy
from compas_timber.fabrication import NurbsContour
from compas_timber.fabrication import TenonShapeType
from compas_timber.utils import is_polyline_clockwise

from .joint import Joint
from .solver import JointTopology
from .utilities import beam_ref_side_incidence


class RotationalTenonProfile(object):
    """Enum for the profile of a :class:`TRotationalTenonMortiseJoint`.

    Attributes
    ----------
    PARALLEL : literal("parallel")
        Both flanks of the tenon are arcs around the rotation axis, so the tenon is equally wide all along.
    CONICAL : literal("conical")
        Both flanks are arcs of the same radii, but around centers moved off the rotation axis: the outer one's above
        it, the inner one's below. So the tenon narrows evenly on both sides of the circle around the axis, from
        `start_width` where it starts to `width` at its tip, and only seats at the end of the rotation.

    """

    PARALLEL = "parallel"
    CONICAL = "conical"


class EndMillType(object):
    """Enum for the end mill which cuts a :class:`TRotationalTenonMortiseJoint`.

    Attributes
    ----------
    FLAT : literal("flat")
        The walls of the tenon and the mortise are square to the shoulder. Nothing but the friction of the joint keeps
        the main beam from being pulled straight back along its axis.
    DOVETAIL : literal("dovetail")
        The walls are inclined by `tool_angle`, so the tenon widens towards its end and the mortise towards its bottom.
        The undercut keeps the main beam from being pulled straight back: turning it about the rotation axis is the
        only way in and out.

    """

    FLAT = "flat"
    DOVETAIL = "dovetail"


class TRotationalTenonMortiseJoint(Joint):
    """Represents a T-rotational-mortise-tenon joint: a hooked tenon on the end of the main beam, which is swung into a
    mortise in the side of the cross beam by turning the main beam about an axis along it.

    The rotation axis is square to the shoulder, the face of the cross beam the main beam butts against, so it runs
    along the main beam. The tenon lies in the main beam's cross section: it starts at one of the main beam's faces
    parallel to the plane of both beams (moved down by `start_depth`), and it hooks down and around the axis, both its
    flanks being arcs around it, its centerline at `rotation_radius`. `start_y` and `axis_offset` place the axis in the
    cross section, across and square to that face, and with it how the tenon curves through the main beam. Turning
    the main beam about the axis moves the tenon along its own arcs, and the mortise is the tenon's path out of the
    cross beam's face on the same side. So, like a dovetail, the joint goes together from that face, and the hook
    keeps the tenon from being pulled straight out of it: the only way out is turning it back about the same axis.

    The mortise is milled into the shoulder and the tenon out of the main beam's end, as
    :class:`~compas_timber.fabrication.FreeContour` processings whose curves are exact NURBS arcs.

    If the main beam meets the cross beam at an angle, the axis still runs along the main beam, so that the whole beam
    turns about it, and the tenon reaches out of the main beam's slanted end along it, to a square end. The main beam's
    end stays flush with the cross beam's face: the waste around the tenon is milled out of the main beam's end, down to
    the slanted shoulder, as a FreeContour of two contours. The mortise is the tenon's shape: its walls follow the main
    beam, as the sides of a pocket milled with a conical tool do, so they are tilted to the face they are milled from,
    and its bottom is the tenon's square end, tilted to the face too. It is milled from the face as a FreeContour of
    two contours as well, its arcs written as straight pieces. The axis lies on the side of the acute angle, and at or
    above the cross beam's face the mortise opens out of: swinging out, the slanted shoulder then moves away from the
    cross beam.

    This joint type is compatible with beams in T topology which lie in one plane with faces parallel to it.

    Please use `TRotationalTenonMortiseJoint.create()` to properly create an instance of this class and associate it
    with a model.

    Parameters
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The beam with the tenon.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The beam with the mortise.
    start_y : float, optional
        Position of the tenon across the main beam's face, from the main beam's centerline, away from the rotation axis:
        the axis lies at `start_y - rotation_radius`, so with `axis_offset` 0, `start_y` is where the tenon's centerline
        starts. Default is the middle of the positions which keep the tenon within the main beam: as it hooks towards
        the axis, a tenon on the main beam's centerline would reach out of its side.
    start_depth : float, optional
        Depth below the main beam's face at which the tenon starts. `axis_offset` is measured from there. Default is
        0.0: flush with the face.
    rotation : float, optional
        Rotation of the tenon about the main beam's axis, in degrees: 0 or 180, which picks the main beam's face the
        tenon starts from, of the two parallel to the plane of both beams. The mortise opens out of the cross beam's
        face on the same side, which is where the joint goes together. Default is the side on which the cross beam's
        face lies lowest relative to the tenon, so it comes out with the least turn; if both are alike, the side facing
        up (world Z), so that the joint goes together from above.
    length : float, optional
        How deep the tenon reaches into the cross beam, along the rotation axis. For a main beam at an angle, from where
        the main beam's centerline meets the cross beam's face: the tenon is longer on the side of the acute angle.
        Default reaches 3/4 of the cross beam's depth into it where it is deepest; for a dovetail end mill at most what
        keeps the tenon, which the inclined walls widen towards its end, within the main beam.
    width : float, optional
        Width of the tenon across its arcs, at its tip (all along for a parallel profile). Default is half the main
        beam's width.
    height : float, optional
        How far below its start the tenon reaches, to the bottom of its tip. Default hooks the tip 45 degrees around
        the axis (`rotation_radius * sin(45) + width / 2 - axis_offset`), but no more than 3/4 of the main beam below
        the start.
    tenon_shape : str, optional
        Shape of the tip. One of :class:`~compas_timber.fabrication.TenonShapeType`: ROUND (also AUTOMATIC and ROUNDED),
        a half circle; SQUARE, a straight end along the radius; RADIUS, a straight end with rounded corners. Default is
        ROUND.
    shape_radius : float, optional
        Radius of the rounded corners of a RADIUS tip, where its straight end meets the flanks (as `shape_radius` of
        :class:`~compas_timber.fabrication.Tenon`). Only used for a RADIUS tip. The corners of a milled mortise cannot
        be tighter than the end mill, so it must be at least half `tool_diameter`. Default is half `tool_diameter`, or
        a quarter of `width` without one.
    rotation_radius : float, optional
        Distance from the rotation axis to the centerline of the tenon. Default is the main beam's width.
    axis_offset : float, optional
        How far the rotation axis lies above the start of the tenon, square to the main beam's face: a positive offset
        raises it out of the main beam, a negative one lowers it into it. Together with `start_y`, it places the axis
        in the main beam's cross section. Raised, the tenon starts out already leaning around the axis; lowered, it
        first bulges away from the axis before it hooks back. Default is 0.0: level with the start, so that the tenon
        starts square to the face.
    profile : str, optional
        One of :class:`RotationalTenonProfile`. Default is PARALLEL.
    start_width : float, optional
        Width of a CONICAL tenon where it starts, split evenly on both sides of the circle around the axis. Default is
        1.5 times `width`. Not used for a PARALLEL tenon. The more a tenon tapers, the more it can also be pulled
        straight out of the mortise: with a strong taper, the hook no longer locks the joint.
    end_mill : str, optional
        One of :class:`EndMillType`. Default is FLAT.
    tool_angle : float, optional
        Angle of the dovetail end mill, in degrees: the inclination of the walls from the rotation axis. Default is
        15.0. Not used for a FLAT end mill.
    tool_diameter : float, optional
        Diameter of the end mill which cuts the mortise; for a dovetail end mill, where it enters the mortise, at the
        cross beam's face. The mortise must be at least as wide (`width`, where the tenon is narrowest), and the
        corners of its tip at least as round (`shape_radius`): a SQUARE tip cannot be milled at all. Default is None:
        not checked.

    Attributes
    ----------
    main_beam : :class:`~compas_timber.elements.Beam`
        The beam with the tenon.
    cross_beam : :class:`~compas_timber.elements.Beam`
        The beam with the mortise.
    rotation_axis : :class:`~compas.geometry.Line`
        The axis the main beam turns about, from the shoulder along the main beam. Its direction is such that turning
        the main beam by a positive angle about it (right-hand rule) swings the tenon out of the mortise: away from the
        cross beam, unless the joint is mirrored to put the axis on the side of the acute angle.
    release_angle : float
        The turn about `rotation_axis`, in degrees, which brings the tenon all the way out of the cross beam, or None
        if it cannot get out.
    return_angle : float
        The turn about `rotation_axis`, in degrees, at which the tenon, swung on past `release_angle`, comes round to
        the cross beam again, or None if it never does or cannot get out.

    """

    SUPPORTED_TOPOLOGY = JointTopology.TOPO_T

    # how far contours reach past the elements, so that no sliver is left at their edges: a fraction of the main beam's
    # smaller side (10 for one 120 wide), so that it scales with the model's units
    MARGIN = 1.0 / 12.0
    TESSELLATION_COUNT = 32  # straight segments per arc in the geometry; the BTLx keeps the exact arcs
    STUCK = (
        "The tenon cannot be swung out of the cross beam, which reaches too far above the rotation axis: "
        "use a smaller start_depth, a larger axis_offset or rotation_radius, or the other rotation."
    )

    @property
    def __data__(self):
        data = super(TRotationalTenonMortiseJoint, self).__data__
        data["start_y"] = self.start_y
        data["start_depth"] = self.start_depth
        data["rotation"] = self.rotation
        data["length"] = self.length
        data["width"] = self.width
        data["height"] = self.height
        data["tenon_shape"] = self.tenon_shape
        data["shape_radius"] = self.shape_radius
        data["rotation_radius"] = self.rotation_radius
        data["axis_offset"] = self.axis_offset
        data["profile"] = self.profile
        data["start_width"] = self.start_width
        data["end_mill"] = self.end_mill
        data["tool_angle"] = self.tool_angle
        data["tool_diameter"] = self.tool_diameter
        return data

    # fmt: off
    def __init__(
        self,
        main_beam=None,
        cross_beam=None,
        start_y=None,
        start_depth=None,
        rotation=None,
        length=None,
        width=None,
        height=None,
        tenon_shape=None,
        shape_radius=None,
        rotation_radius=None,
        axis_offset=None,
        profile=None,
        start_width=None,
        end_mill=None,
        tool_angle=None,
        tool_diameter=None,
        **kwargs
    ):
        super(TRotationalTenonMortiseJoint, self).__init__(elements=(main_beam, cross_beam), **kwargs)
        self.start_y = start_y
        self.start_depth = start_depth
        self.rotation = rotation
        self.length = length
        self.width = width
        self.height = height
        self.tenon_shape = tenon_shape
        self.shape_radius = shape_radius
        self.rotation_radius = rotation_radius
        self.axis_offset = axis_offset
        self.profile = profile
        self.start_width = start_width
        self.end_mill = end_mill
        self.tool_angle = tool_angle
        self.tool_diameter = tool_diameter

        if self.main_beam and self.cross_beam:
            self._set_unset_attributes()
    # fmt: on

    @property
    def main_beam(self):
        return self.element_a

    @property
    def cross_beam(self):
        return self.element_b

    def _set_unset_attributes(self):
        """Sets the parameters which were not given to defaults derived from the beams."""
        assert self.main_beam and self.cross_beam
        rotation_given = self.rotation is not None
        self.rotation = self.rotation or 0.0  # the dimensions below are the same for both sides
        try:
            ref_side = self.main_ref_side_index
            main_width, thickness = self.main_beam.get_dimensions_relative_to_side(ref_side)
            cross_depth = self.cross_beam.get_dimensions_relative_to_side(self.cross_face_index)[1]
        except BeamJoiningError:  # an incompatible layout is reported by process_joinery(), the defaults only need to exist
            main_width, thickness, cross_depth = self.main_beam.width, self.main_beam.height, self.cross_beam.width

        self.width = self.width or main_width / 2.0
        self.start_depth = self.start_depth or 0.0
        self.rotation_radius = self.rotation_radius or main_width
        self.axis_offset = self.axis_offset or 0.0
        hook = self.rotation_radius * math.sin(math.radians(45.0)) + self.width / 2.0 - self.axis_offset
        self.height = self.height or min(hook, 0.75 * (thickness - self.start_depth))
        self.tenon_shape = self.tenon_shape or TenonShapeType.ROUND
        self.shape_radius = self.shape_radius or (self.tool_diameter / 2.0 if self.tool_diameter else self.width / 4.0)
        self.profile = self.profile or RotationalTenonProfile.PARALLEL
        self.start_width = self.start_width or 1.5 * self.width
        self.end_mill = self.end_mill or EndMillType.FLAT
        self.tool_angle = self.tool_angle or 15.0
        self.length = self.length or self._default_length(main_width, thickness, cross_depth)
        if not rotation_given:
            self.rotation = self._lowest_rotation()
        if self.start_y is None:
            self.start_y = self._centered_start_y()

    def _default_length(self, main_width, thickness, cross_depth):
        """3/4 of the cross beam's depth deep into it, but no more than a dovetail tenon can have and still fit in the
        main beam.

        A dovetail end mill widens the tenon by `tan(tool_angle)` on each side for every unit of length, and its end
        must still fit in the main beam's cross section.

        """
        length = 0.75 * cross_depth
        try:
            # for a main beam at an angle: the mortise as deep into the cross beam where it is deepest, at the side of
            # the tenon nearest the acute angle
            frame = self._frame()
            u_min, u_max, _ = self._outline(0.0, start_y=0.0).bounds()
            near = -(u_max - u_min) / 2.0  # with the tenon centered
            length = max(length / frame["cosine"] + frame["slope"] * near, 0.25 * cross_depth)
        except BeamJoiningError:
            pass
        if self.end_mill != EndMillType.DOVETAIL:
            return length

        def fits(offset):
            try:
                u_min, u_max, v_max = self._outline(offset, start_y=0.0).bounds()
            except BeamJoiningError:
                return False
            return u_max - u_min <= main_width and v_max <= thickness - self.start_depth

        if not fits(0.0):
            return length
        low, high = 0.0, main_width  # the largest wall offset which still fits, by bisection
        for _ in range(40):
            middle = (low + high) / 2.0
            low, high = (middle, high) if fits(middle) else (low, middle)
        return min(length, 0.9 * low / math.tan(math.radians(self.tool_angle)))

    def _lowest_rotation(self):
        """0 or 180: the side on which the cross beam's face lies lowest relative to the tenon's start, so it comes out
        with the least turn. If both are alike, the side facing up (world Z), so that the joint goes together from above."""
        keys = {}
        for rotation in (0.0, 180.0):
            self.rotation = rotation
            try:
                up = self.main_beam.ref_sides[self.main_ref_side_index].normal
                keys[rotation] = (round(self._frame()["face_height"], 6), -up.z)
            except BeamJoiningError:
                keys[rotation] = (float("inf"), 0.0)
        return 180.0 if keys[180.0] < keys[0.0] else 0.0

    def _centered_start_y(self):
        """The `start_y` which leaves the tenon, at its widest, as much room within the main beam on both sides."""
        try:
            u_min, u_max, _ = self._outline(self._wall_offset(self.length), start_y=0.0).bounds()
        except BeamJoiningError:
            return 0.0
        return -(u_min + u_max) / 2.0

    ########################################################################
    # Faces and frame of the joint
    ########################################################################

    @property
    def main_ref_side_index(self):
        """The index of the main beam's side the tenon starts from: one of the two parallel to the plane of both beams,
        picked by `rotation`. `start_y` and `start_depth` are measured on it."""
        plane_normal = self.main_beam.centerline.direction.cross(self.cross_beam.centerline.direction)
        if plane_normal.length < 1e-9:
            raise BeamJoiningError(self.elements, self, debug_info="The beams are parallel, they do not span a plane.")
        plane_normal.unitize()
        candidates = [i for i in range(4) if abs(abs(self.main_beam.ref_sides[i].normal.dot(plane_normal)) - 1.0) < 1e-3]
        if not candidates:
            raise BeamJoiningError(self.elements, self, debug_info="No face of the main beam is parallel to the plane of both beams.")
        steps = self.rotation / 90.0
        if abs(steps - round(steps)) > 1e-6 or int(round(steps)) % 2:
            raise BeamJoiningError(self.elements, self, debug_info="The rotation must be 0 or 180 degrees: the tenon must start from a face parallel to the plane of both beams.")
        return (min(candidates) + int(round(steps))) % 4

    @property
    def main_end_side_index(self):
        """The index of the main beam's end the tenon is milled from: 4 (its start) or 5 (its end)."""
        shoulder_normal = self.cross_beam.ref_sides[self.cross_face_index].normal
        return 4 if self.main_beam.ref_sides[4].normal.dot(shoulder_normal) < 0 else 5

    @property
    def cross_face_index(self):
        """The index of the cross beam's side the main beam butts against: the shoulder, which the mortise is milled into."""
        incidence = beam_ref_side_incidence(self.main_beam, self.cross_beam, ignore_ends=True)
        return min(incidence, key=incidence.get)

    @property
    def cross_open_side_index(self):
        """The index of the cross beam's side the mortise opens out of, on the same side as the tenon's start: the
        joint goes together from there."""
        up = self.main_beam.ref_sides[self.main_ref_side_index].normal
        for index in range(4):
            if self.cross_beam.ref_sides[index].normal.dot(up) > 1.0 - 1e-3:
                return index
        raise BeamJoiningError(self.elements, self, debug_info="No face of the cross beam is parallel to the main beam's face the tenon starts from. Are the beams in one plane?")

    def _frame(self):
        """The frame of the joint, in model coordinates.

        Returns a dict with:
        `origin`, where the main beam's centerline meets the cross beam's face, moved to the start of the tenon: up to
        the main beam's face it starts from, then `start_depth` down;
        `u` across the main beam, `down` from that face into the main beam, and `into` the cross beam along the main
        beam, which the rotation axis runs along. u = down x into, so that the tenon hooks around the axis with angles
        increasing from `u` to `down`; for a main beam at an angle, flipped if needed, so that the axis (on the side of
        -u) lies on the side of the acute angle;
        `main_width` and `thickness`, the main beam's dimensions across and square to that face;
        `face_height`, how far the cross beam's face the mortise opens out of lies above the start of the tenon;
        `end_depth`, how far into the cross beam the main beam's blank ends;
        `slope`: the cross beam's face lies `slope * u` along `into` from `origin`, which is 0 for a main beam square to
        it, and further into the cross beam on the obtuse side (u > 0) otherwise;
        `cosine`, of the angle between `into` and the cross beam's face normal;
        `margin`, how far contours reach past the elements (see `MARGIN`).

        """
        ref_side = self.main_ref_side_index
        up = self.main_beam.ref_sides[ref_side].normal
        shoulder = self.cross_beam.ref_sides[self.cross_face_index]
        normal = shoulder.normal  # out of the cross beam
        into = self.main_beam.centerline.direction.unitized()
        if into.dot(normal) > 0:
            into = -into
        cosine = -into.dot(normal)
        if cosine < 1e-3:
            raise BeamJoiningError(self.elements, self, debug_info="The main beam runs along the cross beam's face, it does not meet it.")
        down = -up
        u = down.cross(into).unitized()
        slope = u.dot(normal) / cosine
        if slope < -1e-9:  # put the acute angle on the side of -u, where the axis lies
            u, slope = -u, -slope
        main_width, thickness = self.main_beam.get_dimensions_relative_to_side(ref_side)
        point = intersection_line_plane(self.main_beam.centerline, Plane(shoulder.point, normal))
        if point is None:
            raise BeamJoiningError(self.elements, self, debug_info="The main beam does not meet the cross beam's face.")
        origin = Point(*point) + up * (thickness / 2.0 - self.start_depth)
        open_face = self.cross_beam.ref_sides[self.cross_open_side_index]
        end_face = self.main_beam.ref_sides[self.main_end_side_index]
        return {
            "origin": origin,
            "u": u,
            "down": down,
            "into": into,
            "main_width": main_width,
            "thickness": thickness,
            "face_height": Vector.from_start_end(origin, open_face.point).dot(up),
            "end_depth": Vector.from_start_end(origin, end_face.point).dot(into),
            "slope": slope,
            "cosine": cosine,
            "margin": self.MARGIN * min(main_width, thickness),
        }

    @property
    def rotation_axis(self):
        frame = self._frame()
        point = _to_model(frame, self._axis(), 0.0)
        return Line(point, point + frame["down"].cross(frame["u"]))

    @property
    def release_angle(self):
        window = self._release_window(self._frame(), self._outline(self._wall_offset(self.length)))
        return None if window is None else math.degrees(window[0])

    @property
    def return_angle(self):
        window = self._release_window(self._frame(), self._outline(self._wall_offset(self.length)))
        return None if window is None or math.isinf(window[1]) else math.degrees(window[1])

    ########################################################################
    # Joint
    ########################################################################

    @classmethod
    def check_elements_compatibility(cls, elements, raise_error=False):
        """Checks that the beams lie in one plane which faces of both beams are parallel to.

        Parameters
        ----------
        elements : list(:class:`~compas_timber.elements.Beam`)
            The main beam and the cross beam.
        raise_error : bool, optional
            If True, raises a :class:`~compas_timber.errors.BeamJoiningError` instead of returning False.

        Returns
        -------
        bool
            True if the beams are compatible.

        """
        main_beam, cross_beam = elements
        main_direction = main_beam.centerline.direction.unitized()
        cross_direction = cross_beam.centerline.direction.unitized()
        normal = main_direction.cross(cross_direction)
        compatible = normal.length > 1e-9
        if compatible:
            normal.unitize()
            for beam in (main_beam, cross_beam):
                if not any(abs(abs(beam.ref_sides[i].normal.dot(normal)) - 1.0) < 1e-3 for i in range(4)):
                    compatible = False
        if not compatible and raise_error:
            raise BeamJoiningError(
                elements,
                cls,
                debug_info="The beams must lie in one plane with faces parallel to it: the tenon curls through the main beam, out of a face parallel to it.",
            )
        return compatible

    def add_extensions(self):
        """Extends the main beam to the end of the tenon.

        This method is called during `TimberModel.process_joinery()`, not when the joint is created.

        Raises
        ------
        BeamJoiningError
            If the joint cannot be built with its parameters.

        """
        assert self.main_beam and self.cross_beam
        self.check_elements_compatibility(self.elements, raise_error=True)
        frame = self._frame()
        try:
            start, end = self.main_beam.extension_to_plane(Plane(frame["origin"] + frame["into"] * self.length, frame["into"]))
        except Exception as ex:
            raise BeamJoiningError(self.elements, self, debug_info=str(ex))
        self.main_beam.add_blank_extension(start, end, self.guid)

    def add_features(self):
        """Adds the tenon to the main beam and the mortise to the cross beam, as FreeContour processings.

        This method is called during `TimberModel.process_joinery()`, not when the joint is created.

        """
        assert self.main_beam and self.cross_beam
        reason = self._unmillable()
        if reason:
            raise BeamJoiningError(self.elements, self, debug_info=reason)
        frame = self._frame()
        widest = self._outline(self._wall_offset(self.length))  # at the end of the tenon, for a dovetail end mill
        reason = self._outside_of_main_beam(frame, widest)
        if reason:
            raise BeamJoiningError(self.elements, self, debug_info=reason)
        if self._release_window(frame, widest) is None:
            raise BeamJoiningError(self.elements, self, debug_info=self.STUCK)
        if any(self._strays(outline) for outline in (self._outline(0.0), widest)):
            raise BeamJoiningError(
                self.elements,
                self,
                debug_info=(
                    "The tenon comes closer to the rotation axis, or reaches further from it, than where it starts, so it "
                    "cannot swing out: make start_width smaller or move the axis."
                ),
            )

        angled = frame["slope"] > 1e-9
        if angled and frame["face_height"] - self.axis_offset > 1e-6:
            raise BeamJoiningError(
                self.elements,
                self,
                debug_info=(
                    "For a main beam at an angle, the rotation axis must lie at or above the cross beam's face the mortise opens out of, or its slanted "
                    "end would swing into the cross beam: raise it by {:.1f} with axis_offset.".format(frame["face_height"] - self.axis_offset)
                ),
            )

        # the cross beam: the mortise, the tenon's path as it swings out, milled into the shoulder
        if angled:
            cross_features = [self._tilted_mortise_feature(frame, self._mortise_segments(frame, widest))]
        else:
            mortise = self._contour_feature(
                self._mortise_segments(frame, widest),
                frame,
                0.0,
                self.cross_beam,
                self.cross_face_index,
                depth=self.length,
                widening=lambda segment: True,
            )
            cross_features = [mortise]

        # the main beam: everything past the shoulder but the tenon, milled from the main beam's end, so that a
        # dovetail end mill leaves the tenon wider towards its end, as the mortise is towards its bottom
        end_depth = frame["end_depth"]
        if angled:
            features = self._tilted_tenon_features(frame)
        else:
            end_side = self.main_end_side_index
            region = self._region(frame, self._wall_offset(end_depth))
            tenon_cut = self._contour_feature(
                self._main_segments(self._outline(self._wall_offset(end_depth)), region, frame["margin"]),
                frame,
                end_depth,
                self.main_beam,
                end_side,
                depth=end_depth,
                widening=lambda segment: getattr(segment, "is_tenon", False),
            )
            features = [tenon_cut]
            if self.start_depth > 1e-6:  # the main beam's face down to the start of the tenon
                u_min, u_max, v_top, _ = region
                slab = [(u_min, v_top), (u_max, v_top), (u_max, 0.0), (u_min, 0.0)]
                features.append(self._rectangle_feature(slab, frame, end_depth, self.main_beam, end_side, end_depth))
        if end_depth - self.length > 1e-6:  # the main beam reaches past the end of the tenon
            plane = Plane(frame["origin"] + frame["into"] * self.length, frame["into"])
            features.insert(0, JackRafterCutProxy.from_plane_and_beam(plane, self.main_beam, self.main_ref_side_index))

        self.main_beam.add_features(features)
        self.cross_beam.add_features(cross_features)
        self.features = cross_features + features

    ########################################################################
    # Outline of the tenon
    ########################################################################

    def _wall_offset(self, z):
        """How far the walls are moved outwards at the depth `z` into the cross beam, from the shoulder."""
        if self.end_mill != EndMillType.DOVETAIL:
            return 0.0
        return z * math.tan(math.radians(self.tool_angle))

    def _axis(self, start_y=None):
        """The rotation axis in the main beam's cross section at the shoulder: (u, v)."""
        return (self.start_y if start_y is None else start_y) - self.rotation_radius, -self.axis_offset

    def _outline(self, offset, start_y=None):
        return _TenonOutline(
            axis=self._axis(start_y),
            radius=self.rotation_radius,
            width=self.width,
            start_width=self.start_width if self.profile == RotationalTenonProfile.CONICAL else self.width,
            height=self.height,
            tip=self.tenon_shape,
            corner_radius=self.shape_radius,
            offset=offset,
            joint=self,
        )

    def _outside_of_main_beam(self, frame, outline):
        """Why the tenon reaches out of the main beam's cross section, where it would be cut off unlike the mortise,
        or None."""
        u_min, u_max, v_max = outline.bounds()
        tolerance = 1e-4 * frame["margin"]
        half = frame["main_width"] / 2.0 + tolerance
        if u_min < -half or u_max > half:
            return "The tenon reaches out of the side of the main beam: make it narrower or less high, or move it with start_y or rotation_radius."
        if v_max > frame["thickness"] - self.start_depth + tolerance:
            return "The tenon reaches out of the main beam's opposite face: make start_depth or height smaller (the main beam is {:.1f} thick).".format(frame["thickness"])
        return None

    def _release_window(self, frame, outline):
        """The turns about the axis, in radians, between which the whole tenon is out over the cross beam's face, as
        (from, to), or None if there are none: the start of the tenon would come back down into the cross beam before
        its tip is out. `to` is infinite if the tenon never comes back."""
        center = self._axis()
        rise = frame["face_height"] - self.axis_offset  # of the cross beam's face above the axis
        lower, upper = 0.0, float("inf")
        for segment in outline.segments:
            for point in segment.sample(16):
                radius = _distance(center, point)
                if rise <= -radius:
                    continue  # over the face all the way around
                if rise >= radius:
                    return None
                # turned by t, the point lies at the height radius * sin(t - angle) above the axis
                angle, lift = _angle(center, point), math.asin(rise / radius)
                lower = max(lower, angle + lift)
                upper = min(upper, angle + math.pi - lift)
        return (lower, upper) if lower <= upper else None

    def _unmillable(self):
        """Why the mortise cannot be milled with an end mill of `tool_diameter`, or None."""
        if not self.tool_diameter:
            return None
        if self.width < self.tool_diameter - 1e-6:
            return "The mortise is narrower ({:.1f}) than the end mill (tool_diameter {:.1f}): make the tenon wider or use a smaller tool.".format(self.width, self.tool_diameter)
        if self.tenon_shape == TenonShapeType.SQUARE:
            return "The square corners of the tip cannot be milled: use a RADIUS tip, with a shape_radius of at least half the tool_diameter ({:.1f}).".format(
                self.tool_diameter / 2.0
            )
        if self.tenon_shape == TenonShapeType.RADIUS and self.shape_radius < self.tool_diameter / 2.0 - 1e-6:
            return "The corners of the tip (shape_radius {:.1f}) are tighter than the end mill can cut: make them at least half the tool_diameter ({:.1f}).".format(
                self.shape_radius, self.tool_diameter / 2.0
            )
        return None

    def _strays(self, outline):
        """True if a conical tenon's inner flank comes closer to the axis than where it starts, or its outer flank goes
        further: swinging out, that part would cut through the flank of the mortise, which follows the tenon there."""
        center = self._axis()
        outer, inner = (_distance(center, point) for point in outline.start_points)
        distances = [_distance(center, point) for segment in outline.segments for point in segment.sample(16)]
        return min(distances) < inner - 1e-6 or max(distances) > outer + 1e-6

    def _mortise_segments(self, frame, widest):
        """The closed contour of the mortise: the tenon, and its path around the axis until it is out of the cross
        beam, plus a margin. At the bottom of a dovetail mortise, the path's inner flank runs closest to the axis."""
        outline = self._outline(0.0)
        center = self._axis()
        rise = max(frame["face_height"] - self.axis_offset, 0.0) + frame["margin"]  # above the axis
        nearest = _distance(center, widest.start_points[1])
        if rise >= nearest:
            raise BeamJoiningError(self.elements, self, debug_info=self.STUCK)
        outer, inner = outline.start_points
        # on around the axis past the start of the tenon: out of the cross beam, and at least by the margin
        past_start = min(_angle(center, outer), _angle(center, inner)) - frame["margin"] / _distance(center, outer)
        end_angle = min(-math.asin(rise / nearest), past_start)
        out_outer = _add(center, _direction(end_angle), _distance(center, outer))
        out_inner = _add(center, _direction(end_angle), _distance(center, inner))
        segments = [_Segment.arc(center, out_outer, outer, counterclockwise=True)] + outline.segments
        segments += [_Segment.arc(center, inner, out_inner, counterclockwise=False), _Segment(out_inner, out_outer)]
        return _merged(segments)

    def _region(self, frame, offset):
        """The rectangle around the main beam's cross section, past the shoulder: (u_min, u_max, v_top, v_bottom).

        It also holds the outline of the tenon at the main beam's end, which a dovetail end mill may widen beyond the
        beam.

        """
        margin = frame["margin"]
        half = frame["main_width"] / 2.0 + margin + offset
        return -half, half, -self.start_depth - margin, frame["thickness"] - self.start_depth + margin + offset

    def _main_segments(self, outline, region, margin):
        """The closed contour of what is removed from the main beam past the shoulder: the region around its cross
        section, less the tenon. The tenon's flanks are continued along their tangents up out of the main beam, so
        that the contour goes around it, and walls inclined by a dovetail end mill meet smoothly."""
        u_min, u_max, v_top, v_bottom = region
        outer, inner = outline.start_points
        ups = [(outer, outline.segments[0].tangent_at_start(), -1.0), (inner, outline.segments[-1].tangent_at_end(), 1.0)]
        tops = []
        for point, tangent, sign in ups:
            direction = (tangent[0] * sign, tangent[1] * sign)  # on past the start of the tenon
            if direction[1] > -1e-6:
                raise BeamJoiningError(self.elements, self, debug_info="The tenon does not start out of the main beam's face: move the axis (axis_offset).")
            tops.append(_add(point, direction, v_top / direction[1]))
        outer_top, inner_top = tops
        if inner_top[0] >= outer_top[0]:
            raise BeamJoiningError(self.elements, self, debug_info="The flanks of the tenon cross above its start: move the axis (axis_offset).")
        u_min, u_max = min(u_min, inner_top[0] - margin), max(u_max, outer_top[0] + margin)

        tenon = [segment.reversed() for segment in reversed(outline.segments)]  # from the inner flank around to the outer
        tenon = [_Segment(inner_top, inner)] + tenon + [_Segment(outer, outer_top)]
        for segment in tenon:
            segment.is_tenon = True
        corners = [(u_max, v_top), (u_max, v_bottom), (u_min, v_bottom), (u_min, v_top)]
        return (
            [_Segment(corners[3], inner_top)]
            + tenon
            + [_Segment(outer_top, corners[0]), _Segment(corners[0], corners[1]), _Segment(corners[1], corners[2]), _Segment(corners[2], corners[3])]
        )

    ########################################################################
    # Processings
    ########################################################################

    def _contour_feature(self, segments, frame, z, element, ref_side_index, depth, widening):
        """A FreeContour removing the inside of `segments`, drawn at the depth `z` into the cross beam."""
        curves = [segment.to_model(frame, z) for segment in segments]
        polyline = NurbsContour(curves, depth=0.0, tessellation_count=self.TESSELLATION_COUNT).to_polyline()
        ref_side = element.ref_sides[ref_side_index]
        tool_position = FreeContour.parse_tool_position(polyline, ref_side, True)
        to_local = Transformation.from_frame(ref_side).inverse()
        local_curves = [curve.transformed(to_local) for curve in curves]

        inclination = [0.0]
        if self.end_mill == EndMillType.DOVETAIL:
            # a positive inclination leans the walls of a counterclockwise contour towards its inside (see Contour.to_brep)
            local_polyline = Polyline([point.transformed(to_local) for point in polyline.points])
            outwards = self.tool_angle if is_polyline_clockwise(local_polyline, Vector(0, 0, 1)) else -self.tool_angle
            inclination = [outwards if widening(segment) else 0.0 for segment in segments]
            if len(set(inclination)) == 1:
                inclination = inclination[:1]

        contour = NurbsContour(local_curves, depth=depth, inclination=inclination, tessellation_count=self.TESSELLATION_COUNT)
        return FreeContour(contour, counter_sink=True, tool_position=tool_position, ref_side_index=ref_side_index)

    ########################################################################
    # Tilted walls, for a main beam at an angle
    ########################################################################

    def _tessellate(self, segments, lean):
        """The points of a closed chain of segments, its arcs in straight pieces, and per piece the `lean` of its segment."""
        points, leans = [], []
        for segment in segments:
            for point in segment.sample(self.TESSELLATION_COUNT) if segment.center is not None else [segment.start, segment.end]:
                if points and _distance(points[-1], point) < 1e-9:
                    continue
                if points:
                    leans.append(lean(segment))
                points.append(point)
        if _distance(points[0], points[-1]) < 1e-9:
            points.pop()
        else:
            leans.append(lean(segments[-1]))
        return points, leans

    def _walls(self, frame, points, leans):
        """Planar walls through the pieces of a closed outline drawn at z = 0, which run along the main beam, each
        leaning out of the outline by its tangent in `leans` as it goes into the cross beam.

        Returns per piece: its start at z = 0, in model coordinates, the direction its wall runs in, and its normal.

        """
        count = len(points)
        area = sum(points[i][0] * points[(i + 1) % count][1] - points[(i + 1) % count][0] * points[i][1] for i in range(count))
        walls = []
        for i in range(count):
            a, b = points[i], points[(i + 1) % count]
            out = (b[1] - a[1], a[0] - b[0]) if area > 0 else (a[1] - b[1], b[0] - a[0])  # away from the inside
            norm = math.hypot(*out)
            along = frame["into"] + (frame["u"] * (out[0] / norm) + frame["down"] * (out[1] / norm)) * leans[i]
            start = _to_model(frame, a, 0.0)
            walls.append((start, along, (_to_model(frame, b, 0.0) - start).cross(along).unitized()))
        return walls

    def _sections(self, walls, planes, closing):
        """Where the walls cross each of the `planes`: the corners of the outline there, one per wall which remains.

        Walls leaning in towards a plane make a short piece next to a corner which sticks out turn over there. Like on
        an offset curve, it shrinks to a point where its neighbours' walls cross, on all planes, one at a time, the
        shortest first. Returns the indices of the walls which remain, and the corners on each plane.

        """
        count = len(walls)

        def meet(before, after, plane):
            direction = walls[before][2].cross(walls[after][2])
            if direction.length < 1e-9:  # in line: along their wall, from where they meet at z = 0
                point = walls[after][0]
                return Point(*intersection_line_plane(Line(point, point + walls[after][1]), plane))
            return Point(*intersection_plane_plane_plane(Plane(walls[before][0], walls[before][2]), Plane(walls[after][0], walls[after][2]), plane))

        def length(piece):
            return (walls[(piece + 1) % count][0] - walls[piece][0]).length

        remaining = list(range(count))
        while True:
            sections = [[meet(remaining[k - 1], remaining[k], plane) for k in range(len(remaining))] for plane in planes]
            turned = set()
            for corners in sections:
                for k, piece in enumerate(remaining):
                    edge = walls[(piece + 1) % count][0] - walls[piece][0]
                    if Vector.from_start_end(corners[k], corners[(k + 1) % len(remaining)]).dot(edge) <= 0:
                        turned.add(k)
            if not turned:
                return remaining, sections
            remaining.pop(min(turned, key=lambda k: length(remaining[k])))
            if len(remaining) < 3:
                raise BeamJoiningError(self.elements, self, debug_info=closing)

    def _tilted_mortise_feature(self, frame, segments):
        """The mortise for a main beam at an angle, as a FreeContour of two contours: the one on the cross beam's face,
        and the one at the end of the tenon.

        Its walls run along the main beam (for a dovetail end mill, leaning out by `tool_angle` from it), as the sides
        of a pocket milled with a conical tool, so they are tilted to the face. Its bottom is the tenon's square end,
        so it is deepest on the side of the acute angle, as the tenon is longest there, and holds nothing but the
        tenon and its path out.

        """
        shoulder = self.cross_beam.ref_sides[self.cross_face_index]
        planes = [Plane(shoulder.point, shoulder.normal), Plane(frame["origin"] + frame["into"] * self.length, frame["into"])]
        lean = math.tan(math.radians(self.tool_angle)) if self.end_mill == EndMillType.DOVETAIL else 0.0
        points, leans = self._tessellate(segments, lambda segment: lean)
        walls = self._walls(frame, points, leans)
        closing = "The walls of the dovetail mortise close up before they reach the cross beam's face: use a smaller tool_angle or a flat end mill."
        _, (top, bottom) = self._sections(walls, planes, closing)

        # the face lies further into the cross beam on the obtuse side, the end of the tenon must lie past it all along
        shortest = min(Vector.from_start_end(a, b).dot(frame["into"]) for a, b in zip(top, bottom))
        if shortest < 1e-4 * frame["margin"]:
            reason = "The tenon does not reach into the cross beam on the side of the obtuse angle: make length larger than {:.1f}.".format(self.length - shortest)
            if self.end_mill == EndMillType.DOVETAIL:
                reason += " A dovetail end mill widens the tenon towards its end, so it may then need a smaller tool_angle or start_width to stay within the main beam."
            raise BeamJoiningError(self.elements, self, debug_info=reason)
        return FreeContour.from_top_bottom_and_elements(
            Polyline(top + [top[0]]), Polyline(bottom + [bottom[0]]), self.cross_beam, interior=True, ref_side_index=self.cross_face_index
        )

    def _tilted_tenon_features(self, frame):
        """The waste around the tenon of a main beam at an angle: from the main beam's end down to its slanted shoulder,
        flush with the cross beam's face, as FreeContours of two contours, the one at the main beam's end and the one on
        the shoulder. The tenon's walls are the mortise's (for a dovetail end mill, leaning out of the tenon towards its
        end), the rest square to the main beam's end."""
        end_side = self.main_end_side_index
        end_face = self.main_beam.ref_sides[end_side]
        shoulder = self.cross_beam.ref_sides[self.cross_face_index]
        planes = [Plane(end_face.point, end_face.normal), Plane(shoulder.point, shoulder.normal)]
        lean = math.tan(math.radians(self.tool_angle)) if self.end_mill == EndMillType.DOVETAIL else 0.0
        region = self._region(frame, max(self._wall_offset(frame["end_depth"]), 0.0))
        u_min, u_max, v_top, _ = region
        chains = [self._main_segments(self._outline(0.0), region, frame["margin"])]
        if self.start_depth > 1e-6:  # the main beam's face down to the start of the tenon
            slab = [(u_min, v_top), (u_max, v_top), (u_max, 0.0), (u_min, 0.0)]
            chains.append([_Segment(a, b) for a, b in zip(slab, slab[1:] + slab[:1])])

        features = []
        for segments in chains:
            # the waste lies outside of the tenon, so a tenon wall leaning out of the tenon leans into it
            points, leans = self._tessellate(segments, lambda segment: -lean if getattr(segment, "is_tenon", False) else 0.0)
            walls = self._walls(frame, points, leans)
            closing = "The walls of the dovetail tenon close up before they reach the main beam's end: use a smaller tool_angle or a flat end mill."
            _, (top, bottom) = self._sections(walls, planes, closing)
            features.append(
                FreeContour.from_top_bottom_and_elements(Polyline(top + [top[0]]), Polyline(bottom + [bottom[0]]), self.main_beam, interior=True, ref_side_index=end_side)
            )
        return features

    def _rectangle_feature(self, corners, frame, z, element, ref_side_index, depth):
        points = [_to_model(frame, corner, z) for corner in corners]
        polyline = Polyline(points + [points[0]])
        return FreeContour.from_polyline_and_element(polyline, element, depth=depth, interior=True, ref_side_index=ref_side_index)


########################################################################
# Geometry of the outline, in the main beam's cross section at the shoulder
########################################################################
# A point of the outline is (u, v): u along the shoulder from the main beam's centerline, v down from the start of the
# tenon. Angles are measured around a center from +u towards +v, so the tenon hooks down with increasing angles around
# the rotation axis, and swings out with decreasing ones.


def _to_model(frame, point, z):
    u, v = point
    return frame["origin"] + frame["u"] * u + frame["down"] * v + frame["into"] * z


def _direction(angle):
    return math.cos(angle), math.sin(angle)


def _add(a, b, scale=1.0):
    return a[0] + b[0] * scale, a[1] + b[1] * scale


def _distance(a, b):
    return math.hypot(b[0] - a[0], b[1] - a[1])


def _angle(center, point):
    return math.atan2(point[1] - center[1], point[0] - center[0])


def _circle_circle(center_a, radius_a, center_b, radius_b):
    """The two points where two circles cross, or None."""
    d = _distance(center_a, center_b)
    if d < 1e-12 or d > radius_a + radius_b or d < abs(radius_a - radius_b):
        return None
    along = (radius_a**2 - radius_b**2 + d**2) / (2 * d)
    across = math.sqrt(max(radius_a**2 - along**2, 0.0))
    ex = ((center_b[0] - center_a[0]) / d, (center_b[1] - center_a[1]) / d)
    base = _add(center_a, ex, along)
    return _add(base, (-ex[1], ex[0]), across), _add(base, (ex[1], -ex[0]), across)


def _line_circle(point, direction, center, radius):
    """The parameters along a line (`point` + t * unit `direction`) where it crosses a circle, smallest first, or None."""
    rel = (point[0] - center[0], point[1] - center[1])
    b = rel[0] * direction[0] + rel[1] * direction[1]
    c = rel[0] ** 2 + rel[1] ** 2 - radius**2
    disc = b * b - c
    if disc < 0:
        return None
    root = math.sqrt(disc)
    return -b - root, -b + root


def _merged(segments):
    """The segments, with consecutive arcs on the same circle joined into one."""
    result = []
    for segment in segments:
        last = result[-1] if result else None
        if (
            last is not None
            and last.center is not None
            and segment.center is not None
            and _distance(last.center, segment.center) < 1e-9
            and abs(_distance(last.center, last.start) - _distance(segment.center, segment.start)) < 1e-9
            and last.sweep * segment.sweep > 0
        ):
            result[-1] = _Segment(last.start, segment.end, last.center, last.sweep + segment.sweep)
        else:
            result.append(segment)
    return result


class _Segment(object):
    """A straight line between two points, or an arc around `center` from `start` to `end` turning by `sweep` radians."""

    def __init__(self, start, end, center=None, sweep=0.0):
        self.start = start
        self.end = end
        self.center = center
        self.sweep = sweep

    @classmethod
    def arc(cls, center, start, end, counterclockwise):
        sweep = _angle(center, end) - _angle(center, start)
        if counterclockwise:
            sweep = sweep % (2 * math.pi)
        else:
            sweep = -((-sweep) % (2 * math.pi))
        return cls(start, end, center, sweep)

    def reversed(self):
        return _Segment(self.end, self.start, self.center, -self.sweep)

    def _tangent_at(self, point):
        """The unit direction of travel along the segment at one of its points."""
        if self.center is None:
            length = _distance(self.start, self.end)
            return (self.end[0] - self.start[0]) / length, (self.end[1] - self.start[1]) / length
        radius = _distance(self.center, point)
        radial = ((point[0] - self.center[0]) / radius, (point[1] - self.center[1]) / radius)
        return (-radial[1], radial[0]) if self.sweep > 0 else (radial[1], -radial[0])

    def tangent_at_start(self):
        return self._tangent_at(self.start)

    def tangent_at_end(self):
        return self._tangent_at(self.end)

    def sample(self, count):
        """Points along the segment, both ends included."""
        if self.center is None:
            return [self.start, self.end]
        radius = _distance(self.center, self.start)
        start_angle = _angle(self.center, self.start)
        return [_add(self.center, _direction(start_angle + self.sweep * i / count), radius) for i in range(count + 1)]

    def extremes(self):
        """The ends of the segment, and the points of an arc furthest along +-u and +-v."""
        points = [self.start, self.end]
        if self.center is not None:
            radius = _distance(self.center, self.start)
            start_angle = _angle(self.center, self.start)
            low, high = sorted((start_angle, start_angle + self.sweep))
            for quarter in range(-8, 9):
                if low <= quarter * math.pi / 2 <= high:
                    points.append(_add(self.center, _direction(quarter * math.pi / 2), radius))
        return points

    def to_model(self, frame, z):
        start, end = _to_model(frame, self.start, z), _to_model(frame, self.end, z)
        if self.center is None:
            return Line(start, end)
        # an exact circular arc: a rational quadratic NURBS with one span per quarter turn at most
        radius = _distance(self.center, self.start)
        start_angle = _angle(self.center, self.start)
        spans = max(1, int(math.ceil(abs(self.sweep) / (math.pi / 2) - 1e-9)))
        step = self.sweep / spans
        points, weights = [start], [1.0]
        for i in range(spans):
            middle = start_angle + step * (i + 0.5)
            reach = radius / math.cos(step / 2)
            points.append(_to_model(frame, _add(self.center, _direction(middle), reach), z))
            points.append(end if i == spans - 1 else _to_model(frame, _add(self.center, _direction(start_angle + step * (i + 1)), radius), z))
            weights += [math.cos(step / 2), 1.0]
        knots = [float(i) for i in range(spans + 1)]
        multiplicities = [3] + [2] * (spans - 1) + [3]
        return NurbsCurve.from_parameters(points, weights, knots, multiplicities, 2)


class _TenonOutline(object):
    """The outline of a rotational tenon in the main beam's cross section, as an open chain of segments from its start
    at its outer flank, along the outer flank, around the tip and back along the inner flank to its start.

    All its curves are arcs. With `offset`, every wall is moved outwards by that distance, which is the outline at some
    depth for a dovetail end mill: the arcs stay concentric and tangent to each other.

    """

    def __init__(self, axis, radius, width, start_width, height, tip, corner_radius, offset, joint):
        half = width / 2.0
        outer, inner = radius + half, radius - half
        center = axis
        error = None
        if inner <= 0:
            error = "The rotation radius ({:.1f}) must be larger than half the width of the tenon ({:.1f}).".format(radius, half)
        elif start_width < width - 1e-9:
            error = "The start width ({:.1f}) of a conical tenon must not be smaller than its width ({:.1f}).".format(start_width, width)
        elif abs(center[1]) >= inner:
            error = "The rotation axis lies too far from the start of the tenon (axis_offset {:.1f}): its inner flank, at {:.1f} from the axis, does not reach the start.".format(
                -center[1], inner
            )
        if error:
            raise BeamJoiningError(joint.elements, joint, debug_info=error)

        def start_on(circle_center, circle_radius):
            """Where a flank crosses the start of the tenon (v = 0), on the far side from its center."""
            return (circle_center[0] + math.sqrt(circle_radius**2 - circle_center[1] ** 2), 0.0)

        if tip in (TenonShapeType.SQUARE, TenonShapeType.RADIUS):
            reach = (height - center[1]) / outer
        else:
            tip = TenonShapeType.ROUND
            reach = (height - half - center[1]) / radius
        start_angle = _angle(center, start_on(center, radius))  # of the centerline
        if not -1.0 < reach <= 1.0 or math.asin(reach) <= start_angle + 1e-6:
            raise BeamJoiningError(joint.elements, joint, debug_info="The height ({:.1f}) must be more than the tip and at most a quarter turn around the axis.".format(height))
        tip_angle = math.asin(reach)

        tip_center = _add(center, _direction(tip_angle), radius)
        outer_center = inner_center = center
        if start_width > width + 1e-9:
            # conical: both flanks keep their radius, but their circles are moved off the axis, so that the tenon starts
            # wider by the same on both sides of the circle around the axis, and still meets the tip
            middle = start_on(center, radius)
            scale = start_width / width
            flanks = []
            for flank_radius in (outer, inner):
                parallel = start_on(center, flank_radius)  # where the flank of a parallel tenon starts
                start_point = (middle[0] + (parallel[0] - middle[0]) * scale, 0.0)
                candidates = _circle_circle(tip_center, radius, start_point, flank_radius)
                if candidates is None:
                    raise BeamJoiningError(joint.elements, joint, debug_info="The start width ({:.1f}) is too large for this tenon.".format(start_width))
                flanks.append(min(candidates, key=lambda c: _distance(c, center)))
            outer_center, inner_center = flanks

        o = offset
        outer_o, inner_o, half_o = outer + o, inner - o, half + o
        if inner_o <= abs(inner_center[1]) or outer_o <= abs(outer_center[1]) or half_o <= 0:
            raise BeamJoiningError(joint.elements, joint, debug_info="The walls of the tenon cannot be inclined this far.")
        radial, tangential = _direction(tip_angle), (-math.sin(tip_angle), math.cos(tip_angle))
        start_outer = start_on(outer_center, outer_o)
        start_inner = start_on(inner_center, inner_o)

        def towards(a, b, distance):
            """The point at `distance` from `a` towards `b`."""
            norm = _distance(a, b)
            return _add(a, ((b[0] - a[0]) / norm, (b[1] - a[1]) / norm), distance)

        segments = []
        if tip == TenonShapeType.ROUND:
            # both flanks touch the tip's circle, which is centered at the radius from the axis
            outer_end = towards(outer_center, tip_center, outer_o)
            inner_end = towards(tip_center, inner_center, half_o)
            segments.append(_Segment.arc(outer_center, start_outer, outer_end, counterclockwise=True))
            segments.append(_Segment.arc(tip_center, outer_end, inner_end, counterclockwise=True))
        else:
            # the end is the radial line at the tip angle, moved outwards by the offset
            end_line = _add(center, tangential, o)
            outer_t = _line_circle(end_line, radial, outer_center, outer_o)
            inner_t = _line_circle(end_line, radial, inner_center, inner_o)
            if outer_t is None or inner_t is None:
                raise BeamJoiningError(joint.elements, joint, debug_info="The end of the tenon misses its flanks.")
            outer_end = _add(end_line, radial, outer_t[1])
            inner_end = _add(end_line, radial, inner_t[1])
            fillet = corner_radius + o if tip == TenonShapeType.RADIUS else 0.0
            if fillet > 1e-9:
                if fillet >= half_o:
                    raise BeamJoiningError(joint.elements, joint, debug_info="The shape radius ({:.1f}) must be smaller than half the width of the tenon.".format(corner_radius))
                # the corners: circles touching the end, from behind it, and a flank, inside the outer and outside the inner
                offset_line = _add(center, tangential, o - fillet)
                outer_params = _line_circle(offset_line, radial, outer_center, outer_o - fillet)
                inner_params = _line_circle(offset_line, radial, inner_center, inner_o + fillet)
                if outer_params is None or inner_params is None:
                    raise BeamJoiningError(joint.elements, joint, debug_info="The shape radius ({:.1f}) does not fit this tenon.".format(corner_radius))
                outer_fillet_center = _add(offset_line, radial, outer_params[1])
                outer_tangent = towards(outer_center, outer_fillet_center, outer_o)
                outer_on_end = _add(outer_fillet_center, tangential, fillet)
                inner_fillet_center = _add(offset_line, radial, inner_params[1])
                inner_on_end = _add(inner_fillet_center, tangential, fillet)
                inner_end = towards(inner_fillet_center, inner_center, fillet)
                segments.append(_Segment.arc(outer_center, start_outer, outer_tangent, counterclockwise=True))
                segments.append(_Segment.arc(outer_fillet_center, outer_tangent, outer_on_end, counterclockwise=True))
                segments.append(_Segment(outer_on_end, inner_on_end))
                segments.append(_Segment.arc(inner_fillet_center, inner_on_end, inner_end, counterclockwise=True))
            else:
                segments.append(_Segment.arc(outer_center, start_outer, outer_end, counterclockwise=True))
                segments.append(_Segment(outer_end, inner_end))
        segments.append(_Segment.arc(inner_center, inner_end, start_inner, counterclockwise=False))

        self.segments = segments
        self.start_points = (start_outer, start_inner)
        self.flank_centers = (outer_center, inner_center)

    def bounds(self):
        """(u_min, u_max, v_max) of the outline."""
        points = [point for segment in self.segments for point in segment.extremes()]
        return min(p[0] for p in points), max(p[0] for p in points), max(p[1] for p in points)
