from compas.geometry import Box
from compas.geometry import Frame
from compas.geometry import Line
from compas.geometry import bounding_box
from compas.geometry.brep.brep import Brep

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
        data["width"] = self.width
        data["height"] = self.height
        data["length"] = self.length
        return data

    def __init__(self, length, width, height, frame=None, **kwargs):
        frame = frame or Frame.worldXY()
        super(Wall, self).__init__(frame=frame, **kwargs)
        self.length = length
        self.width = width
        self.height = height

    @property
    def is_wall(self):
        return True

    @property
    def shape(self):
        assert self.frame
        boxframe = self.frame.copy()
        origin = boxframe.point
        origin += boxframe.xaxis * self.length * 0.5
        origin += boxframe.yaxis * self.width * 0.5
        origin += boxframe.zaxis * self.height * 0.5
        return Box(self.length, self.width, self.height, frame=boxframe)

    @property
    def origin(self):
        assert self.frame
        return self.frame.point.copy()

    @property
    def baseline(self):
        # type: () -> Line
        assert self.frame
        start = self.frame.point
        end = self.frame.point + self.frame.xaxis * self.length
        return Line(start, end)

    def compute_geometry(self, _=False):
        return Brep.from_box(self.shape)

    def compute_aabb(self, inflate_by=0.0):
        vertices, _ = self.shape.to_vertices_and_faces()
        box = Box.from_bounding_box(bounding_box(vertices))
        box.xsize += inflate_by
        box.ysize += inflate_by
        box.zsize += inflate_by
        return box

    def compute_obb(self, inflate_by=0.0):
        obb = self.shape.copy()
        obb.xsize += inflate_by
        obb.ysize += inflate_by
        obb.zsize += inflate_by
        return obb

    def __repr__(self):
        return "Wall({}, {:.3f}, {:.3f}, {:.3f})".format(self.frame, self.length, self.width, self.height)

    @classmethod
    def from_box(cls, box):
        # type: (Box) -> Wall
        boxframe = box.frame.copy()
        origin = boxframe.point
        origin -= boxframe.xaxis * box.xsize * 0.5
        origin -= boxframe.yaxis * box.ysize * 0.5
        origin -= boxframe.zaxis * box.zsize * 0.5
        return cls(box.xsize, box.ysize, box.zsize, frame=boxframe)
