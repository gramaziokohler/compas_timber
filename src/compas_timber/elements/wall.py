from compas.geometry import Box
from compas.geometry import Brep
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import Polyline
from compas.geometry import bounding_box

from .timber import TimberElement


class Wall(TimberElement):
    """Represents a single timber wall element.
    Serves as container for beams joints and other related elements and groups them together to form a wall.

    Wall is often a single unit of prefabricated timber wall element.
    It is often refered to as an enveloping body.

    TODO: complete this docstring

    """

    @property
    def __data__(self):
        data = super(Wall, self).__data__
        data["outline"] = self.outline
        data["openings"] = self.openings
        data["thickness"] = self.thickness
        return data

    def __init__(self, outline, thickness, openings=None, frame=None, **kwargs):
        # type: (compas.geometry.Polyline, float, list[compas.geometry.Polyline], Frame, dict) -> None
        super(Wall, self).__init__(frame=frame or Frame.worldXY(), **kwargs)
        self.outline = outline
        self.thickness = thickness
        self.openings = openings or []

        self._faces = None
        self._corners = None

        if not outline.is_closed:
            raise ValueError("Outline is not closed.")
        if len(self.outline) != 5:
            raise ValueError("Wall outline must have 4 segments.")

    @property
    def is_wall(self):
        return True

    @property
    def is_group_element(self):
        return True

    @property
    def origin(self):
        assert self.frame
        return self.frame.point.copy()

    @property
    def centerline(self):
        # TODO: temp hack to make this compatible with `find_topology`.
        return self.baseline

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
    def corners(self):
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
        return self.faces[-2:]

    @property
    def envelope_faces(self):
        return self.faces[:4]

    def compute_geometry(self, _=False):
        assert self.frame

        extrusion_vector = self.frame.zaxis * self.thickness
        return Brep.from_extrusion(self.outline, extrusion_vector)

    def compute_aabb(self, inflate_by=0.1):
        obb = self.compute_obb(inflate_by)
        return Box.from_bounding_box(bounding_box(obb.points))

    def compute_obb(self, inflate_by=0.0):
        assert self.frame
        # TODO: this is more like obb than aabb
        box = Box.from_bounding_box(self.corners)
        box.xsize += inflate_by
        box.ysize += inflate_by
        box.zsize += inflate_by
        return box

    def __repr__(self):
        return "Wall(name={}, {}, {:.3f}, {:.3f}, {:.3f})".format(
            self.name, self.frame, self.outline, self.thickness, self.openings
        )

    @staticmethod
    def _frame_from_polyline(polyline, normal):
        points = polyline.points
        xaxis = points[1] - points[0]
        xaxis.unitize()
        yaxis = normal.cross(xaxis)
        return Frame(points[0], xaxis, yaxis)

    @staticmethod
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

    @classmethod
    def from_polyline(cls, polyline, normal, thickness, openings=None, **kwargs):
        """Use this to make sure the polyline is oriented correctly."""
        oriented_polyline = cls._oriented_polyline(polyline, normal)
        wall_frame = cls._frame_from_polyline(oriented_polyline, normal)
        return cls(oriented_polyline, thickness, openings, wall_frame, **kwargs)

    @classmethod
    def from_brep(cls, brep, thickness, **kwargs):
        """Creates a wall from a brep with a single planar face."""
        # TODO: grab normal, outline and openings from brep
        # orient polylines
        # return cls.from_polyline(outline, normal, thickness, **kwargs)
        raise NotImplementedError
