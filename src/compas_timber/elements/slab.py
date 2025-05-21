from compas.data import Data
from compas.geometry import Box
from compas.geometry import Point
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import bounding_box
from compas.geometry import distance_point_plane

from compas_timber.utils import classify_polyline_segments

from .timber import TimberElement


class OpeningType(object):
    DOOR = "door"
    WINDOW = "window"


class Opening(Data):
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
        self.polyline = _oriented_polyline(self.polyline, normal)


class Slab(TimberElement):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = super(Slab, self).__data__
        data["outline"] = self.outline
        data["openings"] = self.openings
        data["thickness"] = self.thickness
        data["attributes"] = self.attributes
        return data

    def __init__(self, outline_a, outline_b, openings=None, frame=None, name=None, **kwargs):
        # type: (compas.geometry.Polyline, float, list[compas.geometry.Polyline], Frame, dict) -> None
        super(Slab, self).__init__(frame=frame or Frame.worldXY(), name=name)
        self.outline_a = outline_a
        self.outline_b = outline_b
        self._thickness = None

        self.openings = openings or []
        self.attributes = {}
        self.attributes.update(kwargs)

        self._faces = None
        self._corners = None

        if not outline.is_closed:
            raise ValueError("Outline is not closed.")
        if len(self.outline) != 5:
            raise ValueError("Wall outline must have 4 segments.")

    @property
    def is_slab(self):
        return True

    @property
    def is_group_element(self):
        return True

    @property
    def origin(self):
        assert self.frame
        return self.frame.point.copy()

    @property
    def thickness(self):
        if self._thickness is None:
            self._thickness = distance_point_plane(self.outline_a[0], Plane.from_points(*self.outline_b[:3]))

    @property
    def centerline(self):
        # TODO: temp hack to make this compatible with `find_topology`.
        return self.baseline

    @property
    def frame(self):
        return Frame.from_points(self.outline[0], self.outline[1], self.outline[-2])

    @property
    def baseline(self):
        # type: () -> Line
        points = self.outline.points
        return Line(points[0], points[1])

    @property
    def width(self):
        return self.thickness

    @property
    def length(self):
        return self.baseline.length

    @property
    def height(self):
        return self.outline.points[0].distance_to_point(self.outline.points[3])

    def compute_geometry(self, _=False):
        assert self.frame

        extrusion_vector = self.frame.zaxis * self.thickness
        return Brep.from_extrusion(self.outline, extrusion_vector)

    def compute_aabb(self, inflate_by=0.1):
        obb = self.compute_obb(inflate_by)
        return Box.from_bounding_box(bounding_box(obb.points))

    def compute_obb(self):
        # type: (float | None) -> compas.geometry.Box
        """Computes the Oriented Bounding Box (OBB) of the element.

        Returns
        -------
        :class:`compas.geometry.Box`
            The OBB of the element.

        """
        vertices = self.outline_a.points + self.outline_b.points
        world_vertices = []
        for point in vertices:
            world_vertices.append(point.transformed(Transformation.from_frame_to_frame(self.frame, Frame.worldXY())))
        obb = Box.from_points(world_vertices)
        obb.xsize += inflate
        obb.ysize += inflate
        obb.zsize += inflate
        obb.transform(Transformation.from_frame_to_frame(Frame.worldXY(), self.frame))
        return obb

    def rotate(self):
        assert self.frame
        self.outline = Polyline(self.outline.points[1:] + [self.outline.points[1]])
        assert self.outline.is_closed
        self.frame = Slab._frame_from_polyline(self.outline, self.frame.normal)
        assert len(self.outline) == 5

    def __repr__(self):
        return "Slab(name={}, {}, {}, {:.3f})".format(self.name, self.frame, self.outline, self.thickness)

    @classmethod
    def from_boundary(cls, outline, thickness, vector = None, openings=None, **kwargs):
        """Creates a wall from a boundary outline and a thickness.

        Parameters
        ----------
        outline : :class:`compas.geometry.Polyline`
            The outline of the wall.
        thickness : float
            The thickness of the wall.
        vector : :class:`compas.geometry.Vector`
            The vector in which the wall is extruded.(optional)
        openings : list[:class:`compas_timber.elements.Opening`]
            The openings in the wall. (optional)
        kwargs : dict
            Additional keyword arguments.
            These are passed to the :class:`compas_timber.elements.Slab` constructor.
        """

        if TOL.is_zero(thickness):
            thickness = TOL.absolute
        thickness_vector = Frame.from_points(outline[0], outline[1], outline[-2]).normal
        if vector and thickness_vector.dot(vector) < 0:
            thickness_vector = -thickness_vector
        thickness_vector.unitize()
        thickness_vector *= thickness
        outline_b = Polyline(outline).translated(thickness_vector)
        return cls(outline, outline_b, openings, **kwargs)

    @classmethod
    def from_brep(cls, brep, thickness, vector = None, **kwargs):
        """Creates a wall from a brep with a single planar face.


        Parameters
        ----------
        brep : :class:`compas.geometry.Brep`
            The brep to create the wall from. must be as single planar face.
        thickness : float
            The thickness of the wall.
        vector : :class:`compas.geometry.Vector`
            The vector in which the wall is extruded.(optional)
        kwargs : dict
            Additional keyword arguments.
            These are passed to the :class:`compas_timber.elements.Slab` constructor.
        """

        if len(brep.faces) > 1:
            raise ValueError("Can only single-face breps to create a Wall. This brep has {}".format(len(brep.faces)))

        # trims are oriented consistently, depending on the face orientation
        face = brep.faces[0]
        trims = face.boundary.trims
        winding_direction = "cw" if face.is_reversed else "ccw"

        # separate the outline from the cutouts (concave)
        # these are still part of the boundary loop but we cound them as openings (doors)
        boundary = Polyline([t.start_vertex.point for t in trims] + [trims[-1].end_vertex.point])
        face_frame = face.frame_at(0, 0)
        outline_vertices, internal_groups = classify_polyline_segments(boundary, normal=face_frame.normal, direction=winding_direction)
        outline = Polyline([boundary[i] for i in outline_vertices])

        openings = []
        for group in internal_groups:
            points = [boundary[i] for i in group]
            openings.append(Opening(Polyline(points), OpeningType.DOOR))

        # internal cuts (windows) are not part of the outline and can be fetched from the loops that are not boundary
        for hole in face.holes:
            points = [t.start_vertex.point for t in hole.trims] + [hole.trims[-1].end_vertex.point]
            openings.append(Opening(Polyline(points), OpeningType.WINDOW))

        return cls.from_boundary(outline, face_frame.normal, thickness, openings, **kwargs)


def _oriented_polyline(polyline, normal):
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
