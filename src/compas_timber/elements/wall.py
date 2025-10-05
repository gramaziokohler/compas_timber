from compas.data import Data
from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import bounding_box

from .slab import Slab


class OpeningType(object):
    """Constants for different types of openings in walls.

    Attributes
    ----------
    DOOR : str
        Constant for door openings.
    WINDOW : str
        Constant for window openings.
    """

    DOOR = "door"
    WINDOW = "window"


class Opening(Data):
    """Represents an opening in a wall (door, window, etc.).

    Parameters
    ----------
    polyline : :class:`~compas.geometry.Polyline`
        The polyline defining the boundary of the opening.
    opening_type : str
        The type of opening (e.g., "door", "window").
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    polyline : :class:`~compas.geometry.Polyline`
        The polyline defining the boundary of the opening.
    opening_type : str
        The type of opening.
    """

    @property
    def __data__(self):
        return {
            "polyline": self.polyline,
            "opening_type": self.opening_type,
        }

    def __init__(self, polyline, opening_type, **kwargs):
        super(Opening, self).__init__(**kwargs)
        self.polyline = polyline
        self.opening_type = opening_type

    def __repr__(self):
        return "Opening(type={})".format(self.opening_type)

    def orient_polyline(self, normal):
        """Orient the polyline consistently with the given normal vector.

        Parameters
        ----------
        normal : :class:`~compas.geometry.Vector`
            The normal vector to orient the polyline with.
        """
        self.polyline = _oriented_polyline(self.polyline, normal)


class Wall(Slab):
    """Represents a single timber wall element.

    Serves as container for beams, joints and other related elements and groups them together to form a wall.
    Wall is often a single unit of prefabricated timber wall element.
    It is often referred to as an enveloping body.

    Parameters
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this wall.
    length : float
        Length of the wall.
    width : float
        Width of the wall.
    thickness : float
        Thickness of the wall.
    outline_a : :class:`~compas.geometry.Polyline`, optional
        A polyline representing the principal outline of this wall.
    outline_b : :class:`~compas.geometry.Polyline`, optional
        A polyline representing the associated outline of this wall.
    openings : list[:class:`~compas_timber.elements.Opening`], optional
        A list of Opening objects representing openings in this wall.
    name : str, optional
        Name of the wall. Defaults to "Wall".
    **kwargs : dict, optional
        Additional keyword arguments.

    Attributes
    ----------
    frame : :class:`~compas.geometry.Frame`
        The coordinate system (frame) of this wall.
    outline : :class:`~compas.geometry.Polyline`
        The outline of the wall (same as outline_a).
    thickness : float
        Thickness of the wall.
    name : str
        Name of the wall.
    attributes : dict
        Dictionary of additional attributes.
    is_wall : bool
        Always True for walls.
    origin : :class:`~compas.geometry.Point`
        The origin point of the wall frame.
    centerline : :class:`~compas.geometry.Line`
        The centerline of the wall (alias for baseline).
    baseline : :class:`~compas.geometry.Line`
        The baseline of the wall from first to second point of outline.
    corners : tuple[:class:`~compas.geometry.Point`, ...]
        The 8 corner points of the wall bounding box.
    faces : tuple[:class:`~compas.geometry.Frame`, ...]
        The 6 faces of the wall as frames (bottom, left, top, right, back, front).
    end_faces : tuple[:class:`~compas.geometry.Frame`, :class:`~compas.geometry.Frame`]
        The back and front faces of the wall.
    envelope_faces : tuple[:class:`~compas.geometry.Frame`, ...]
        The envelope faces of the wall (bottom, left, top, right).

    """

    @property
    def __data__(self):
        data = super(Wall, self).__data__
        data["outline"] = self.outline
        data["openings"] = self.openings
        data["thickness"] = self.thickness
        data["attributes"] = self.attributes
        return data

    def __init__(self, frame, length, width, thickness, outline_a=None, outline_b=None, openings=None, name=None, **kwargs):
        print("args", frame, length, width, thickness)
        super(Wall, self).__init__(frame, length, width, thickness, outline_a, outline_b, openings, **kwargs)
        self.outline = outline_a
        self.attributes = {}
        self.attributes.update(kwargs)
        self.name = name or "Wall"
        self._faces = None
        self._corners = None

        if len(self.outline) != 5:
            raise ValueError("Wall outline must have 4 segments.")

    def __repr__(self):
        return "Wall(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline, self.thickness)

    @property
    def is_wall(self):
        """Check if this element is a wall.

        Returns
        -------
        bool
            Always True for walls.
        """
        return True

    @property
    def origin(self):
        """The origin point of the wall frame.

        Returns
        -------
        :class:`~compas.geometry.Point`
            The origin point of the wall frame.
        """
        assert self.frame
        return self.frame.point.copy()

    @property
    def centerline(self):
        """The centerline of the wall.

        This is an alias for baseline to maintain compatibility with topology finding algorithms.

        Returns
        -------
        :class:`~compas.geometry.Line`
            The centerline of the wall.
        """
        # TODO: temp hack to make this compatible with `find_topology`.
        return self.baseline

    @property
    def baseline(self):
        """The baseline of the wall from first to second point of outline.

        Returns
        -------
        :class:`~compas.geometry.Line`
            The baseline of the wall.
        """
        # type: () -> Line
        points = self.outline.points
        return Line(points[0], points[1])

    @property
    def corners(self):
        """The 8 corner points of the wall bounding box.

        Returns
        -------
        tuple[:class:`~compas.geometry.Point`, ...]
            The 8 corner points in order consistent with Box.from_bounding_box requirements.
        """
        assert self.frame
        if not self._corners:
            points = self.outline.points
            self._corners = (
                points[0],
                points[1],
                points[1] + self.frame.zaxis * self.thickness,
                points[0] + self.frame.zaxis * self.thickness,
                points[3],
                points[2],
                points[2] + self.frame.zaxis * self.thickness,
                points[3] + self.frame.zaxis * self.thickness,
            )  # this order is consistent with what's required by `Box.from_bounding_box`
        return self._corners

    @property
    def faces(self):
        """The 6 faces of the wall as frames.

        Returns
        -------
        tuple[:class:`~compas.geometry.Frame`, ...]
            The 6 faces as frames in BTLx ref-side system order: (bottom, left, top, right, back, front).
        """
        if not self._faces:
            corners = self.corners
            bottom_face = Frame.from_points(corners[0], corners[1], corners[3])
            left_face = Frame.from_points(corners[4], corners[5], corners[0])
            top_face = Frame.from_points(corners[7], corners[6], corners[4])
            right_face = Frame.from_points(corners[3], corners[2], corners[7])
            back_face = Frame.from_points(corners[0], corners[3], corners[4])
            front_face = Frame.from_points(corners[5], corners[6], corners[1])
            # this order is consistent with BTLx ref-side system
            self._faces = (bottom_face, left_face, top_face, right_face, back_face, front_face)
        return self._faces

    @property
    def end_faces(self):
        """The back and front faces of the wall.

        Returns
        -------
        tuple[:class:`~compas.geometry.Frame`, :class:`~compas.geometry.Frame`]
            The back and front faces of the wall.
        """
        return self.faces[-2:]

    @property
    def envelope_faces(self):
        """The envelope faces of the wall (bottom, left, top, right).

        Returns
        -------
        tuple[:class:`~compas.geometry.Frame`, ...]
            The envelope faces of the wall.
        """
        return self.faces[:4]

    def compute_geometry(self, _=False):
        """Compute the geometry of the wall.

        Parameters
        ----------
        _ : bool, optional
            Unused parameter for compatibility. Defaults to False.

        Returns
        -------
        :class:`~compas.geometry.Brep`
            The geometry of the wall as a Brep.
        """
        assert self.frame

        extrusion_vector = self.frame.zaxis * self.thickness
        return Brep.from_extrusion(self.outline, extrusion_vector)

    def compute_aabb(self, inflate_by=0.1):
        """Compute the Axis Aligned Bounding Box (AABB) of the wall.

        Parameters
        ----------
        inflate_by : float, optional
            Amount to inflate the bounding box by. Defaults to 0.1.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The AABB of the wall.
        """
        obb = self.compute_obb(inflate_by)
        return Box.from_bounding_box(bounding_box(obb.points))

    def compute_obb(self, inflate_by=0.0):
        """Compute the Oriented Bounding Box (OBB) of the wall.

        Parameters
        ----------
        inflate_by : float, optional
            Amount to inflate the bounding box by. Defaults to 0.0.

        Returns
        -------
        :class:`~compas.geometry.Box`
            The OBB of the wall.
        """
        assert self.frame
        # TODO: this is more like obb than aabb
        box = Box.from_bounding_box(self.corners)
        box.xsize += inflate_by
        box.ysize += inflate_by
        box.zsize += inflate_by
        return box

    def rotate(self):
        """Rotate the wall by shifting the outline points and updating the frame.

        This method rotates the wall outline by one position and updates the frame accordingly.
        """
        assert self.frame
        self.outline = Polyline(self.outline.points[1:] + [self.outline.points[1]])
        assert self.outline.is_closed
        self.frame = self._frame_from_polyline(self.outline, self.frame.normal)
        assert len(self.outline) == 5

    @staticmethod
    def _frame_from_polyline(polyline, normal):
        """Create a frame from a polyline and normal vector.

        Parameters
        ----------
        polyline : :class:`~compas.geometry.Polyline`
            The polyline to create the frame from.
        normal : :class:`~compas.geometry.Vector`
            The normal vector for the frame.

        Returns
        -------
        :class:`~compas.geometry.Frame`
            A frame with origin at the first point of the polyline.
        """
        points = polyline.points
        xaxis = points[1] - points[0]
        xaxis.unitize()
        yaxis = normal.cross(xaxis)
        return Frame(points[0], xaxis, yaxis)


def _oriented_polyline(polyline, normal):
    """Return a polyline that is oriented consistently counterclockwise around the normal.

    Parameters
    ----------
    polyline : :class:`~compas.geometry.Polyline`
        The input polyline to orient.
    normal : :class:`~compas.geometry.Vector`
        The normal vector to orient around.

    Returns
    -------
    :class:`~compas.geometry.Polyline`
        A polyline oriented counterclockwise around the normal.

    Notes
    -----
    The function assumes a specific orientation:

    .. code-block:: text

        ^  3 ---- 2
        |  |      |
        z  0 ---- 1
           x -->
    """
    # returns a polyline that is oriented consistently ccw around the normal
    # ^  3 ---- 2
    # |  |      |
    # z  0 ---- 1
    #    x -->
    sorted_points = sorted(polyline.points[:4], key=lambda pt: pt.z)
    bottom_points = sorted_points[:2]
    top_points = sorted_points[2:]

    # Ensure counterclockwise order
    if normal.cross(bottom_points[1] - bottom_points[0]).z < 0:
        bottom_points.reverse()

    if normal.cross(top_points[1] - top_points[0]).z > 0:
        top_points.reverse()

    return Polyline(bottom_points + top_points + [bottom_points[0]])
